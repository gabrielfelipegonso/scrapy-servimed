# run_spider.py
import os
import sys
import argparse
import json
from pathlib import Path
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from scrapy import signals
from servimedScraper.spiders.products import ProductsSpider
from dotenv import load_dotenv

load_dotenv()


def parse_args():
    p = argparse.ArgumentParser(
        description="Executa o spider de produtos (login + listagem + extração)."
    )
    p.add_argument("--usuario", "-u", help="Usuário de login", default=None)
    p.add_argument("--senha", "-p", help="Senha de login", default=None)
    p.add_argument(
        "--output",
        "-o",
        help="Arquivo de saída (default: produtos.jsonl)",
        default="produtos.jsonl",
    )
    p.add_argument(
        "--format",
        "-f",
        help="Formato de saída (json, jsonlines, csv)",
        default="jsonlines",
    )
    p.add_argument("--loglevel", default="INFO")
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--delay", type=float, default=0.1)
    p.add_argument(
        "--saleType",
        "-s",
        type=int,
        choices=[1, 2],
        default=int(os.getenv("SERVIMED_SALE_TYPE", 1)),
        help="Tipo de venda: 1=a prazo, 2=à vista",
    )
    p.add_argument(
        "--mode",
        "-m",
        choices=["file", "stream"],
        default="file",
        help="Modo de saída: file (escreve em arquivo) ou stream (imprime itens no stdout).",
    )
    return p.parse_args()


def main():
    args = parse_args()

    usuario = args.usuario or os.getenv("SERVIMED_USER")
    senha = args.senha or os.getenv("SERVIMED_PASS")
    sale_type = args.saleType

    if not usuario or not senha:
        print(
            "Erro: informe credenciais (--usuario/--senha ou env SERVIMED_USER/SERVIMED_PASS)",
            file=sys.stderr,
        )
        sys.exit(2)

    settings = get_project_settings()
    settings.set("LOG_LEVEL", args.loglevel, priority="cmdline")
    settings.set("CONCURRENT_REQUESTS", args.concurrency, priority="cmdline")
    settings.set("DOWNLOAD_DELAY", args.delay, priority="cmdline")
    settings.set("AUTOTHROTTLE_ENABLED", True, priority="cmdline")

    if args.mode == "file":
        out_path = Path(args.output).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
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
    else:
        settings.set("FEEDS", {}, priority="cmdline")

    process = CrawlerProcess(settings)

    if args.mode == "stream":

        def on_item_scraped(item, response, spider):
            print(json.dumps(dict(item), ensure_ascii=False), flush=True)

        crawler = process.create_crawler(ProductsSpider)
        crawler.signals.connect(on_item_scraped, signal=signals.item_scraped)
        process.crawl(crawler, usuario=usuario, senha=senha, sale_type=sale_type)
    else:
        process.crawl(ProductsSpider, usuario=usuario, senha=senha, sale_type=sale_type)

    try:
        process.start()
        if args.mode == "file":
            print(f"\n✅ Concluído. Saída em: {args.output}")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Falha: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
