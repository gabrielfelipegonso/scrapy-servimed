# worker_stream.py
import os
import sys
import json
import subprocess
from pathlib import Path
from threading import Thread
import logging
from servimedQueue.utils import postProduct

PY = sys.executable


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _drain_stderr(proc):
    if not proc.stderr:
        return
    for line in proc.stderr:
        logger.error(line.strip())


def main(ch, method, properties, body):
    try:
        message = json.loads(body.decode("utf-8"))
        usuario = message.get("usuario")
        senha = message.get("senha")
        sale_type = message.get(
            "tipo de venda", int(os.getenv("SERVIMED_SALE_TYPE", "1"))
        )
        mode = "stream"

        logger.info(
            "Mensagem recebida para usuário=%s tipo_venda=%s", usuario, sale_type
        )

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
            usuario,
            "-p",
            senha,
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

        count = 0
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Linha não é JSON válido: %s", line)
                continue
            count += 1
            postProduct.postProduct(item, count)

        rc = proc.wait()
        if rc not in (0, None):
            logger.error("[worker] run_spider.py saiu com código %s", rc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            return

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info("Mensagem processada e confirmada (ack).")

    except Exception:
        logger.exception("Erro inesperado ao processar mensagem")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


if __name__ == "__main__":
    logger.info(
        "Este módulo é um consumer RabbitMQ e deve ser chamado pelo channel.basic_consume."
    )
