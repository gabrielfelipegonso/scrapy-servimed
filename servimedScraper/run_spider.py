# run_spider.py (na raiz do projeto)
import os
import sys
import argparse
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings


from servimedScraper.spiders.products import ProductsSpider


def parse_args():
    p = argparse.ArgumentParser(
        description="Executa o spider de produtos (login + listagem + extração) e salva em arquivo local."
    )
    p.add_argument(
        "--usuario",
        "-u",
        help="Usuário de login (pode usar SERVIMED_USER)",
        default=None,
    )
    p.add_argument(
        "--senha", "-p", help="Senha de login (pode usar SERVIMED_PASS)", default=None
    )
    p.add_argument(
        "--output",
        "-o",
        help="Arquivo de saída (default: produtos.jsonl)",
        default="produtos.jsonl",
    )
    p.add_argument(
        "--format",
        "-f",
        help="Formato: json, jsonlines, csv (default: jsonlines)",
        default="jsonlines",
    )
    p.add_argument(
        "--loglevel", help="Nível de log Scrapy (INFO, DEBUG, WARNING)", default="INFO"
    )
    p.add_argument(
        "--concurrency", type=int, default=8, help="CONCURRENT_REQUESTS (default 8)"
    )
    p.add_argument(
        "--delay",
        type=float,
        default=0.1,
        help="DOWNLOAD_DELAY em segundos (default 0.1)",
    )
    return p.parse_args()


def main():
    args = parse_args()

    usuario = args.usuario or os.getenv("SERVIMED_USER")
    senha = args.senha or os.getenv("SERVIMED_PASS")

    if not usuario or not senha:
        print(
            "Erro: informe credenciais com --usuario/--senha ou via env SERVIMED_USER/SERVIMED_PASS",
            file=sys.stderr,
        )
        sys.exit(2)

    out_path = Path(args.output).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    settings = get_project_settings()

    settings.set(
        "FEEDS",
        {
            str(out_path): {
                "format": args.format,
                "encoding": "utf8",
                "overwrite": True,
            }
        },
        priority="cmdline",
    )

    settings.set("LOG_LEVEL", args.loglevel, priority="cmdline")
    settings.set("CONCURRENT_REQUESTS", args.concurrency, priority="cmdline")
    settings.set("DOWNLOAD_DELAY", args.delay, priority="cmdline")
    settings.set("AUTOTHROTTLE_ENABLED", True, priority="cmdline")
    settings.set("RETRY_ENABLED", True, priority="cmdline")
    settings.set("RETRY_TIMES", 3, priority="cmdline")

    process = CrawlerProcess(settings)

    process.crawl(ProductsSpider, usuario=usuario, senha=senha)

    try:
        process.start()
        print(f"\n✅ Concluído. Saída em: {out_path}")
        sys.exit(0)
    except SystemExit as e:
        raise
    except Exception as e:
        print(f"❌ Falha na execução: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
