# worker_stream.py
import os
import sys
import json
import time
import subprocess
from pathlib import Path
from threading import Thread
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import re
from servimedQueue.utils.auth import AuthClient

PY = sys.executable

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

HEARTBEAT_TICK_SECS = float(os.getenv("RABBIT_HEARTBEAT_TICK", "1.0"))


def _drain_stderr(proc):
    _LEVEL_RE = re.compile(r"\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b:")
    if not proc.stderr:
        return
    level_fn = logger.info  # nível default para linhas de continuação
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
        total=2,
        connect=2,
        read=2,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods={"POST"},
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    return s


SESSION = _make_session()


def _post_all(items, api_url: str, auth: AuthClient) -> tuple[bool, bool]:
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
        resp = SESSION.post(api_url, json=items, headers=headers, timeout=(5, 30))
    except (requests.Timeout, requests.ConnectionError, requests.SSLError) as e:
        logger.warning("Erro de rede no POST: %s -> requeue", e)
        return False, True

    if resp.status_code in (429, 500, 502, 503, 504):
        logger.warning("HTTP %s do endpoint; requeue.", resp.status_code)
        return False, True
    if 400 <= resp.status_code < 500:
        logger.error(
            "HTTP %s definitivo; descarta. Body[:400]=%s",
            resp.status_code,
            resp.text[:400],
        )
        return False, False
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        logger.error("Erro inesperado no POST: %s; descarta.", e)
        return False, False

    logger.info("POST concluído (status=%s).", resp.status_code)
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
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
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
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
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
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        logger.info("Spider finalizado. Total de itens: %d", len(items))

        api_url = os.getenv("API_PRODUCTS_URL")
        auth = AuthClient()
        ok, requeue = _post_all(items, api_url, auth)

        if ok:
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info("Mensagem ACK (POST OK).")
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=requeue)
            logger.info("Mensagem NACK (requeue=%s).", requeue)

    except json.JSONDecodeError:
        logger.exception("Mensagem inválida (JSON); NACK descarta.")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception:
        logger.exception("Erro inesperado; NACK requeue.")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


if __name__ == "__main__":
    logger.info("Callback de consumer RabbitMQ (basic_consume).")
