BOT_NAME = "servimedScraper"
SPIDER_MODULES = ["servimedScraper.spiders"]
NEWSPIDER_MODULE = "servimedScraper.spiders"
ADDONS = {}
ROBOTSTXT_OBEY = True
CONCURRENT_REQUESTS_PER_DOMAIN = 1
DOWNLOAD_DELAY = 0.5
AUTOTHROTTLE_ENABLED = True
CONCURRENT_REQUESTS: 10
RETRY_ENABLED: True
RETRY_TIMES: 3
DOWNLOADER_MIDDLEWARES = {
    "servimedScraper.middlewares.ServimedscraperDownloaderMiddleware": 540,
}
FEED_EXPORT_ENCODING = "utf-8"