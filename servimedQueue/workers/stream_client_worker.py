# worker_stream.py
import os
import sys
import json
import subprocess
from pathlib import Path
from threading import Thread
import logging
from servimedQueue.requests import postProduct

PY = sys.executable


def _drain_stderr(proc):
    if not proc.stderr:
        return
    for line in proc.stderr:
        sys.stderr.write(line)


def main():

    usuario = os.getenv("SERVIMED_USER") or "juliano@farmaprevonline.com.br"
    senha = os.getenv("SERVIMED_PASS") or "a007299A"
    sale_type = int(os.getenv("SERVIMED_SALE_TYPE", "1"))
    mode = "stream"
    here = Path(__file__).resolve().parent
    repo_root = here
    candidates = [
        repo_root / "run_spider.py",
        repo_root / "servimedScraper" / "run_spider.py",
    ]
    run_path = next((c.resolve() for c in candidates if c.exists()), None)
    if not run_path:
        print(
            "run_spider.py não encontrado na raiz nem em servimedScraper/.",
            file=sys.stderr,
        )
        sys.exit(2)

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
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        encoding="utf-8",
        env=env,
    )

    if not proc.stdout:
        print("stdout do subprocesso indisponível.", file=sys.stderr)
        sys.exit(2)

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

            print(line, file=sys.stderr)
            continue
        count += 1
        postProduct()

    rc = proc.wait()
    if rc not in (0, None):
        logging.info(f"[worker] run_spider.py saiu com código {rc}", file=sys.stderr)


if __name__ == "__main__":
    main()
