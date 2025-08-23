from scrapy import signals
import json

class ServimedscraperSpiderMiddleware:

    @classmethod
    def from_crawler(cls, crawler):
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):

        return None

    def process_spider_output(self, response, result, spider):

        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):

        pass

    async def process_start(self, start):

        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class ServimedscraperDownloaderMiddleware:
    @classmethod
    def from_crawler(cls, crawler):

        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):
        request.headers.setdefault("Content-Type", "application/json")
        request.headers.setdefault("Accept", "application/json")
        request.headers.setdefault("User-Agent", "Mozilla/5.0")

        if not request.meta.get("needs_auth"):
            return None

        state = getattr(spider, "state", {}) or {}
        access_token = state.get("access_token")
        user_code = state.get("user_code")
        cookie_access_token = state.get("cookie_access_token")
        users = state.get("users")

        if user_code:
            request.headers.setdefault("loggeduser", str(user_code))
        if access_token:
            request.headers.setdefault("accesstoken", str(access_token))
        if users:
            request.cookies.setdefault("users", json.dumps(users))
        if cookie_access_token:
            request.cookies.setdefault("accesstoken", str(cookie_access_token))

        return None

    def process_response(self, request, response, spider):

        return response

    def process_exception(self, request, exception, spider):
   
        pass

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)
