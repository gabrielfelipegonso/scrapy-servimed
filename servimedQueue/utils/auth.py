import logging
import os
import threading
import time
from typing import Optional, Dict

import requests

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


class AuthError(Exception):
    pass


class AuthClient:
    """
    Uso:
        auth = AuthClient()
        token = auth.get_token()          # sempre retorna um token válido
        headers = auth.auth_header()      # {"Authorization": "Bearer <token>"}
    """

    def __init__(
        self,
        token_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scope: Optional[str] = "",
        timeout: int = os.getenv("TIMEOUT") or 30,
        expiry_skew: int = os.getenv("EXPIRE_TOKEN_TIME") or 20,
        session: Optional[requests.Session] = None,
    ):

        self.token_url = token_url or os.getenv("API_TOKEN_URL")
        self.username = username or os.getenv("API_USERNAME_COTE")
        self.password = password or os.getenv("API_PASSWORD_COTE")
        self.client_id = client_id or os.getenv("API_CLIENT_ID_COTE", "")
        self.client_secret = client_secret or os.getenv(
            "API_CLIENT_SECRET_COTE", "None"
        )
        self.scope = scope if scope is not None else os.getenv("API_SCOPE_COTE", "")
        self.timeout = timeout
        self.expiry_skew = expiry_skew
        self.session = session or requests.Session()
        self._token_type: str = "Bearer"
        self._access_token: Optional[str] = None
        self._exp_ts: float = 0.0
        self._lock = threading.RLock()

        missing = [
            k
            for k, v in {
                "API_TOKEN_URL": self.token_url,
                "API_USERNAME": self.username,
                "API_PASSWORD": self.password,
            }.items()
            if not v
        ]
        if missing:
            msg = f"Config de auth ausente: {', '.join(missing)}"
            logger.error(msg)
            raise AuthError(msg)

    def get_token(self) -> str:
        """Garante e retorna um access_token válido (renova se expirado)."""
        with self._lock:
            if not self._is_token_valid():
                self._password_grant()
            return self._access_token

    def auth_header(self) -> Dict[str, str]:
        """Header Authorization pronto."""
        with self._lock:
            if not self._is_token_valid():
                self._password_grant()
            return {"Authorization": f"{self._token_type} {self._access_token}"}

    def _is_token_valid(self) -> bool:
        return bool(self._access_token) and time.time() < (
            self._exp_ts - self.expiry_skew
        )

    def _password_grant(self) -> None:
        payload = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": self.scope or "",
        }
        try:
            logger.info("Solicitando access_token (password grant)")
            r = self.session.post(
                self.token_url,
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self.timeout,
            )
        except requests.RequestException as e:
            logger.error("Erro de rede ao obter token: %s", e, exc_info=True)
            raise AuthError(f"Falha na requisição de token: {e}") from e

        if r.status_code >= 400:
            body = r.text[:500]
            logger.error("Auth falhou (%s): %s", r.status_code, body)
            raise AuthError(f"Erro ao obter token: {r.status_code} {body}")

        try:
            data = r.json()
        except ValueError:
            logger.error("Resposta não-JSON do servidor de auth: %s", r.text[:400])
            raise AuthError("Resposta não-JSON do servidor de auth")

        access = data.get("access_token")
        if not access:
            logger.error("Resposta sem access_token: %s", data)
            raise AuthError("Resposta sem access_token")

        token_type = (data.get("token_type") or "Bearer").strip()
        try:
            expires_in = int(data.get("expires_in", 300))
        except (TypeError, ValueError):
            expires_in = 300

        self._token_type = token_type or "Bearer"
        self._access_token = access
        self._exp_ts = time.time() + max(expires_in, 60)

        logger.info("Token obtido (%s); expira em %ss", self._token_type, expires_in)
