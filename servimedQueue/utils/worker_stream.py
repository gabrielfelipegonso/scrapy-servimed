import os
import sys
import json
import time
import subprocess
from pathlib import Path
from threading import Thread
import logging
import re
import gzip

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from servimedQueue.utils.auth import AuthClient

PY = sys.executable

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

HEARTBEAT_TICK_SECS = float(os.getenv("RABBIT_HEARTBEAT_TICK", "1.0"))


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


API_CONNECT_TIMEOUT = _env_int("API_CONNECT_TIMEOUT", 10)
API_READ_TIMEOUT = _env_int("API_READ_TIMEOUT", 300)
API_RETRY_TOTAL = _env_int("API_RETRY_TOTAL", 1)
API_RETRY_CONNECT = _env_int("API_RETRY_CONNECT", 2)
API_RETRY_READ = _env_int("API_RETRY_READ", 1)
API_POOL_CONN = _env_int("API_POOL_CONN", 10)
API_POOL_MAX = _env_int("API_POOL_MAX", 20)
API_POST_GZIP = _env_bool("API_POST_GZIP", True)


def _drain_stderr(proc):
    _LEVEL_RE = re.compile(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b:")
    if not proc.stderr:
        return
    level_fn = logger.info
    for raw in proc.stderr:
        line = raw.rstrip()
        m = _LEVEL_RE.search(line)
        if m:
            lvl = m.group(1)
            if lvl == "DEBUG":
                level_fn = logger.debug
            elif lvl == "INFO":
                level_fn = logger.info
            elif lvl == "WARNING":
                level_fn = logger.warning
            elif lvl == "ERROR":
                level_fn = logger.error
            elif lvl == "CRITICAL":
                level_fn = logger.critical
        level_fn(line)


def _make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=API_RETRY_TOTAL,
        connect=API_RETRY_CONNECT,
        read=API_RETRY_READ,
        backoff_factor=0.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods={"POST"},
        raise_on_status=False,
    )
    adapter = HTTPAdapter(
        max_retries=retry, pool_connections=API_POOL_CONN, pool_maxsize=API_POOL_MAX
    )
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


SESSION = _make_session()


def _safe_ack(ch, tag):
    try:
        ch.basic_ack(delivery_tag=tag)
    except Exception as e:
        logger.warning("ACK falhou (canal fechado?): %s", e)


def _safe_nack(ch, tag, requeue):
    try:
        ch.basic_nack(delivery_tag=tag, requeue=requeue)
    except Exception as e:
        logger.warning("NACK falhou (canal fechado?): %s", e)


def _post_all(items, api_url: str, auth: AuthClient) -> tuple[bool, bool]:
    """
    Retorna (ok, requeue):
      ok=True                 -> ACK
      ok=False & requeue=True -> NACK requeue (erro temporário)
      ok=False & requeue=False-> NACK sem requeue (erro definitivo 4xx)
    """
    if not items:
        logger.info("Nenhum produto coletado; nada a enviar.")
        return True, False
    if not api_url:
        logger.error("API_PRODUCTS_URL não configurada.")
        return False, False

    headers = {"Content-Type": "application/json"}
    headers.update(auth.auth_header())

    logger.info("POSTando %d itens para %s ...", len(items), api_url)

    try:
        t0 = time.time()
        if API_POST_GZIP:
            payload = json.dumps(items, ensure_ascii=False).encode("utf-8")
            gz = gzip.compress(payload)
            headers["Content-Encoding"] = "gzip"
            resp = SESSION.post(
                api_url,
                data=gz,
                headers=headers,
                timeout=(API_CONNECT_TIMEOUT, API_READ_TIMEOUT),
            )
            dt = time.time() - t0
            logger.info(
                "POST gzip concluído em %.1fs (status=%s, req-bytes≈%s)",
                dt,
                resp.status_code,
                len(gz),
            )
        else:
            resp = SESSION.post(
                api_url,
                json=items,
                headers=headers,
                timeout=(API_CONNECT_TIMEOUT, API_READ_TIMEOUT),
            )
            dt = time.time() - t0
            size = len(resp.request.body) if resp.request and resp.request.body else "?"
            logger.info(
                "POST concluído em %.1fs (status=%s, req-bytes≈%s)",
                dt,
                resp.status_code,
                size,
            )

    except (
        requests.exceptions.Timeout,
        requests.exceptions.ConnectionError,
        requests.exceptions.SSLError,
    ) as e:
        logger.warning("Erro de rede no POST: %s -> requeue", e)
        return False, True

    if resp.status_code in (408, 429, 500, 502, 503, 504):
        logger.warning("HTTP %s do endpoint; requeue.", resp.status_code)
        return False, True

    if 400 <= resp.status_code < 500:
        if resp.status_code == 422:
            try:
                data = resp.json()
                errs = data.get("detail", [])
                sample = [
                    (e.get("loc"), e.get("msg"), e.get("input")) for e in errs[:10]
                ]
                logger.error("422 detalhes (amostra): %s", sample)
            except Exception:
                logger.error("422 body: %s", resp.text[:800])
        else:
            logger.error(
                "HTTP %s definitivo; body[:800]=%s", resp.status_code, resp.text[:800]
            )
        return False, False

    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logger.error("HTTPError inesperado: %s (body[:800]=%s)", e, resp.text[:800])
        return False, False

    return True, False


def _tick_heartbeat(ch):
    """Processa eventos/heartbeats do pika sem liberar o callback."""
    try:
        ch.connection.process_data_events(time_limit=0)
    except Exception as e:
        logger.debug("tick heartbeat falhou: %s", e)


def start_scrap(ch, method, properties, body: bytes):
    try:
        LOG_EACH_ITEM = os.getenv("LOG_EACH_ITEM", "0").lower() in ("1", "true", "yes")
        LOG_EVERY_N = int(os.getenv("LOG_EVERY_N", "0"))
        msg = json.loads(body.decode("utf-8"))
        usuario = msg.get("usuario")
        senha = msg.get("senha")
        sale_type = msg.get("tipo de venda", int(os.getenv("SERVIMED_SALE_TYPE", "1")))
        mode = "stream"

        logger.info("Mensagem recebida: usuario=%s tipo_venda=%s", usuario, sale_type)

        here = Path(__file__).resolve().parent
        repo_root = here.parent.parent
        candidates = [
            repo_root / "run_spider.py",
            repo_root / "servimedScraper" / "run_spider.py",
        ]
        run_path = next((c.resolve() for c in candidates if c.exists()), None)
        if not run_path:
            logger.error(
                "run_spider.py não encontrado na raiz nem em servimedScraper/."
            )
            _safe_nack(ch, method.delivery_tag, requeue=True)
            return

        cmd = [
            PY,
            "-u",
            str(run_path),
            "-u",
            str(usuario or ""),
            "-p",
            str(senha or ""),
            "-s",
            str(sale_type),
            "-m",
            mode,
            "--loglevel",
            "INFO",
        ]

        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        env.setdefault("SCRAPY_SETTINGS_MODULE", "servimedScraper.settings")

        proc = subprocess.Popen(
            cmd,
            cwd=str(repo_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            encoding="utf-8",
            env=env,
        )
        if not proc.stdout:
            logger.error("stdout do subprocesso indisponível.")
            _safe_nack(ch, method.delivery_tag, requeue=True)
            return

        t_err = Thread(target=_drain_stderr, args=(proc,), daemon=True)
        t_err.start()

        items: list[dict] = []
        last_tick = time.monotonic()

        for line in proc.stdout:
            line = line.strip()
            if not line:
                if time.monotonic() - last_tick >= HEARTBEAT_TICK_SECS:
                    _tick_heartbeat(ch)
                    last_tick = time.monotonic()
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Linha não é JSON válido: %s", line)
            else:
                items.append(item)
                count = len(items)
                if LOG_EACH_ITEM:
                    logger.info(
                        "📦 %d: %s", count, json.dumps(item, ensure_ascii=False)
                    )
                elif LOG_EVERY_N and count % LOG_EVERY_N == 0:
                    logger.info(
                        "📦 [%d] último item: %s",
                        count,
                        json.dumps(item, ensure_ascii=False)[:300],
                    )

            if time.monotonic() - last_tick >= HEARTBEAT_TICK_SECS:
                _tick_heartbeat(ch)
                last_tick = time.monotonic()

        while True:
            rc = proc.poll()
            if rc is not None:
                break
            _tick_heartbeat(ch)
            time.sleep(min(HEARTBEAT_TICK_SECS, 0.5))

        if rc not in (0, None):
            logger.error("run_spider.py saiu com código %s; requeue.", rc)
            _safe_nack(ch, method.delivery_tag, requeue=True)
            return

        logger.info("Spider finalizado. Total de itens: %d", len(items))

        api_url = os.getenv("API_PRODUCTS_URL")
        auth = AuthClient()
        ok, requeue = _post_all(items, api_url, auth)

        if ok:
            _safe_ack(ch, method.delivery_tag)
            logger.info("Mensagem ACK (POST OK).")
        else:
            _safe_nack(ch, method.delivery_tag, requeue=requeue)
            logger.info("Mensagem NACK (requeue=%s).", requeue)

    except json.JSONDecodeError:
        logger.exception("Mensagem inválida (JSON); NACK descarta.")
        _safe_nack(ch, method.delivery_tag, requeue=False)
    except Exception:
        logger.exception("Erro inesperado; NACK requeue.")
        _safe_nack(ch, method.delivery_tag, requeue=True)


if __name__ == "__main__":
    logger.info("Callback de consumer RabbitMQ (basic_consume).")
