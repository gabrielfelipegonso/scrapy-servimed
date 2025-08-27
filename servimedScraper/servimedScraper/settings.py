from dotenv import load_dotenv
import os

load_dotenv()


def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _env_float(name: str, default: float) -> float:
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _env_bool_any(names: list[str], default: bool) -> bool:
    """Lê a primeira env existente em names, útil para compat ('AUTOTHROTTLE' vs 'AUTOTHROTTLE_ENABLED')."""
    for n in names:
        if os.getenv(n) is not None:
            return _env_bool(n, default)
    return default


BOT_NAME = "servimedScraper"
SPIDER_MODULES = ["servimedScraper.spiders"]
NEWSPIDER_MODULE = "servimedScraper.spiders"
ADDONS = {}
ROBOTSTXT_OBEY = _env_bool("OBEY_ROBOTS", True)
CONCURRENT_REQUESTS = _env_int("CONCURRENT_REQUESTS", 300)
CONCURRENT_REQUESTS_PER_DOMAIN = _env_int("CONCURRENT_REQUESTS_PER_DOMAIN", 300)
DOWNLOAD_DELAY = _env_float("DOWNLOAD_DELAY", 0.1)
AUTOTHROTTLE_ENABLED = _env_bool_any(["AUTOTHROTTLE_ENABLED", "AUTOTHROTTLE"], True)
RETRY_ENABLED = _env_bool("RETRY_ENABLED", True)
RETRY_TIMES = _env_int("RETRY_TIMES", 1)
DOWNLOAD_TIMEOUT = _env_int("DOWNLOAD_TIMEOUT", 30)
REDIRECT_ENABLED = _env_bool("REDIRECT_ENABLED", True)
DOWNLOADER_MIDDLEWARES = {
    "servimedScraper.middlewares.ServimedscraperDownloaderMiddleware": 540,
}
API_POST_GZIP = "false"
FEED_EXPORT_ENCODING = os.getenv("FEED_EXPORT_ENCODING", "utf-8")
LOG_LEVEL = os.getenv("SCRAPY_LOG_LEVEL", "INFO")
