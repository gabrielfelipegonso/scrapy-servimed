import logging
import os
import threading
import time
from typing import Optional, Dict

import requests

_LOG_LEVEL_NAME = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_LEVEL = getattr(logging, _LOG_LEVEL_NAME, logging.INFO)

logger = logging.getLogger(__name__)
if not logger.handlers:
    logging.basicConfig(
        level=_LOG_LEVEL,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


class AuthError(Exception):
    pass


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


class AuthClient:

    def __init__(
        self,
        token_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        scope: Optional[str] = "",
        timeout: Optional[int] = None,
        expiry_skew: Optional[int] = None,
        session: Optional[requests.Session] = None,
    ):

        self.username = (
            username if username is not None else os.getenv("API_USERNAME_COTE")
        )
        self.password = (
            password if password is not None else os.getenv("API_PASSWORD_COTE")
        )

        self.token_url = token_url or os.getenv("API_TOKEN_URL")
        self.client_id = (
            client_id if client_id is not None else os.getenv("API_CLIENT_ID_COTE", "")
        )
        self.client_secret = (
            client_secret
            if client_secret is not None
            else os.getenv("API_CLIENT_SECRET_COTE", "None")
        )
        self.scope = scope if scope is not None else os.getenv("API_SCOPE_COTE", "")

        self.timeout = int(timeout) if timeout is not None else _env_int("TIMEOUT", 30)
        self.expiry_skew = (
            int(expiry_skew)
            if expiry_skew is not None
            else _env_int("EXPIRE_TOKEN_TIME", 20)
        )

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

    def set_credentials(self, username: str, password: str) -> None:

        with self._lock:
            self.username = username
            self.password = password
            self._invalidate_token_unlocked()

    def get_token(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> str:

        with self._lock:
            self._apply_call_overrides_unlocked(username, password)
            if not self._is_token_valid_unlocked():
                self._password_grant_unlocked()
            return self._access_token

    def auth_header(
        self, username: Optional[str] = None, password: Optional[str] = None
    ) -> Dict[str, str]:

        with self._lock:
            self._apply_call_overrides_unlocked(username, password)
            if not self._is_token_valid_unlocked():
                self._password_grant_unlocked()
            return {"Authorization": f"{self._token_type} {self._access_token}"}

    def _apply_call_overrides_unlocked(
        self, username: Optional[str], password: Optional[str]
    ) -> None:

        changed = False
        if username is not None and username != self.username:
            self.username = username
            changed = True
        if password is not None and password != self.password:
            self.password = password
            changed = True
        if changed:
            self._invalidate_token_unlocked()

    def _invalidate_token_unlocked(self) -> None:
        self._access_token = None
        self._exp_ts = 0.0
        self._token_type = "Bearer"

    def _is_token_valid_unlocked(self) -> bool:
        return bool(self._access_token) and time.time() < (
            self._exp_ts - self.expiry_skew
        )

    def _password_grant_unlocked(self) -> None:
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
            expires_in = int(data.get("expires_in", 0))
        except (TypeError, ValueError):
            expires_in = 0
        if expires_in <= 0:
            expires_in = _env_int("DEFAULT_TOKEN_TTL", 300)

        self._token_type = token_type or "Bearer"
        self._access_token = access
        self._exp_ts = time.time() + max(expires_in, self.expiry_skew + 1)

        logger.info("Token obtido (%s); expires_in=%ss", self._token_type, expires_in)
