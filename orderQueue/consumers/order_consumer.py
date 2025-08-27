# servimedQueue/consumers/consumer_post_products.py
import json
import logging
import os
from typing import Optional, Dict, Any, List, Tuple

import pika
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from shared.auth import (
    AuthClient,
    AuthError,
)

log = logging.getLogger(__name__)
if not log.handlers:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

JSONItem = Dict[str, Any]


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


class ProductPosterConsumer:

    def __init__(
        self,
        queue: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        api_url: Optional[str] = None,
        auth: Optional[AuthClient] = None,
    ):

        self.queue = queue or os.getenv("RABBIT_QUEUE_PRODUCTS", "queue.products")
        params = pika.ConnectionParameters(
            host=host or os.getenv("RABBIT_HOST", "localhost"),
            port=int(port or os.getenv("RABBIT_PORT", "5672")),
            credentials=pika.PlainCredentials(
                user or os.getenv("RABBIT_USER", "guest"),
                password or os.getenv("RABBIT_PASS", "guest"),
            ),
            heartbeat=_env_int("RABBIT_HEARTBEAT", 60),
            blocked_connection_timeout=_env_int("RABBIT_BLOCKED_CONN_TIMEOUT", 300),
        )
        self._conn = pika.BlockingConnection(params)
        self._ch = self._conn.channel()
        self._ch.queue_declare(queue=self.queue, durable=True)
        self._ch.basic_qos(prefetch_count=_env_int("RABBIT_PREFETCH", 8))

        self.api_url = api_url or os.getenv("API_ORDER_URL")
        if not self.api_url:
            raise RuntimeError("API_ORDER_URL ausente")

        retry = Retry(
            total=_env_int("API_RETRY_TOTAL", 2),
            connect=_env_int("API_RETRY_CONNECT", 2),
            read=_env_int("API_RETRY_READ", 2),
            backoff_factor=float(os.getenv("API_BACKOFF_FACTOR", "0.5")),
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"POST"},
            raise_on_status=False,
        )
        adapter = HTTPAdapter(
            max_retries=retry,
            pool_connections=_env_int("API_POOL_CONN", 10),
            pool_maxsize=_env_int("API_POOL_MAX", 20),
        )
        self._session = requests.Session()
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        self._api_connect_timeout = _env_int("API_CONNECT_TIMEOUT", 10)
        self._api_read_timeout = _env_int("API_READ_TIMEOUT", 60)

        self._auth = auth or AuthClient()

    @staticmethod
    def _validate_envelope(msg: Any) -> Tuple[str, str, List[JSONItem]]:
        errs: List[str] = []

        if not isinstance(msg, dict):
            raise ValueError("Envelope deve ser um objeto JSON (dict).")

        usuario = msg.get("usuario")
        senha = msg.get("senha")
        if not isinstance(usuario, str) or not usuario.strip():
            errs.append("Campo 'usuario' ausente ou inválido.")
        if not isinstance(senha, str) or not senha.strip():
            errs.append("Campo 'senha' ausente ou inválido.")

        produtos = msg.get("produtos")
        if not isinstance(produtos, list) or not produtos:
            errs.append("Campo 'produtos' deve ser uma lista não vazia.")

        if errs:
            raise ValueError("; ".join(errs))

        cleaned: List[JSONItem] = []
        for i, it in enumerate(produtos, start=1):
            if not isinstance(it, dict):
                log.error("Produto #%d inválido: deve ser objeto.", i)
                continue

            gtin = it.get("gtin")
            codigo = it.get("codigo")
            quantidade = it.get("quantidade")

            ok = True

            if isinstance(gtin, (int, float)):
                gtin = str(int(gtin))
            if not isinstance(gtin, str) or not gtin.strip():
                log.error("Produto #%d: 'gtin' ausente/inválido.", i)
                ok = False

            if not isinstance(codigo, str) or not codigo.strip():
                log.error("Produto #%d: 'codigo' ausente/inválido.", i)
                ok = False

            try:
                quantidade = int(quantidade)
            except (TypeError, ValueError):
                log.error("Produto #%d: 'quantidade' deve ser inteiro.", i)
                ok = False
            else:
                if quantidade <= 0:
                    log.error("Produto #%d: 'quantidade' deve ser > 0.", i)
                    ok = False

            if ok:
                cleaned.append(
                    {
                        "gtin": gtin.strip(),
                        "codigo": codigo.strip(),
                        "quantidade": quantidade,
                    }
                )

        if not cleaned:
            raise ValueError("Nenhum item válido em 'produtos'.")

        return usuario.strip(), senha.strip(), cleaned

    def _send_to_api(
        self, produtos: List[JSONItem], usuario: str, senha: str
    ) -> requests.Response:

        try:
            headers = self._auth.auth_header(username=usuario, password=senha)
        except TypeError:

            headers = AuthClient(username=usuario, password=senha).auth_header()
        except AuthError as e:

            raise requests.RequestException(f"Auth local falhou: {e}") from e

        headers["Content-Type"] = "application/json"
        return self._session.post(
            self.api_url,
            json=produtos,
            headers=headers,
            timeout=(self._api_connect_timeout, self._api_read_timeout),
        )

    def _on_message(self, ch, method, properties, body: bytes):

        try:
            msg = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            log.error("Mensagem inválida (JSON malformado); descartando.")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        try:
            usuario, senha, produtos = self._validate_envelope(msg)
        except ValueError as e:
            log.error("Envelope inválido: %s — descartando.", e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        size = len(produtos)
        log.info("Postando %d produtos para API…", size)

        try:
            resp = self._send_to_api(produtos, usuario, senha)
        except (
            requests.Timeout,
            requests.ConnectionError,
            requests.exceptions.SSLError,
            requests.RequestException,
        ) as e:
            log.warning("Falha de rede ao enviar (size=%s): %s; NACK requeue", size, e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        if resp.status_code in (429, 500, 502, 503, 504):
            log.warning("HTTP %s do endpoint; NACK requeue.", resp.status_code)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        if 400 <= resp.status_code < 500:
            log.error(
                "HTTP %s definitivo; NACK descarta. Body[:400]=%s",
                resp.status_code,
                resp.text[:400],
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            log.error("Erro inesperado no POST: %s; NACK descarta.", e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        log.info("Enviado com sucesso (status=%s, size=%s)", resp.status_code, size)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def start(self) -> None:
        log.info("[✓] Consumindo fila '%s' para postar produtos…", self.queue)
        self._ch.basic_consume(
            queue=self.queue, on_message_callback=self._on_message, auto_ack=False
        )
        try:
            self._ch.start_consuming()
        except KeyboardInterrupt:
            log.info("Interrompido (Ctrl+C). Encerrando…")
        finally:
            self.close()

    def close(self) -> None:
        try:
            if self._ch.is_open:
                self._ch.close()
        finally:
            if self._conn.is_open:
                self._conn.close()


if __name__ == "__main__":
    ProductPosterConsumer().start()
