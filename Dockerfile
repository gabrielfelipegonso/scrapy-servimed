FROM python:3.12-slim AS base
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN apt-get update -y && apt-get install -y --no-install-recommends \
      tini ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*
ENV TZ=America/Sao_Paulo
RUN useradd -ms /bin/bash appuser
WORKDIR /app

FROM base AS deps
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip wheel \
 && pip install --no-cache-dir -r /app/requirements.txt

FROM base AS runtime
COPY --from=deps /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=deps /usr/local/bin /usr/local/bin

COPY servimedQueue/   /app/servimedQueue/
COPY servimedScraper/ /app/servimedScraper/
COPY orderQueue/      /app/orderQueue/
COPY shared/          /app/shared/



RUN chown -R appuser:appuser /app
USER appuser

ENV PYTHONPATH=/app

ENV AUTOTHROTTLE=true \
    CONCURRENT_REQUESTS=8 \
    CONCURRENT_REQUESTS_PER_DOMAIN=100 \
    DOWNLOAD_DELAY=0.1 \
    DOWNLOAD_TIMEOUT=60 \
    RETRY_ENABLED=true \
    RETRY_TIMES=3 \
    FEED_EXPORT_ENCODING=utf-8 \
    ROBOTSTXT_OBEY=0 \
    SCRAPY_SETTINGS_MODULE=servimedScraper.settings \
    API_CONNECT_TIMEOUT=10 \
    API_READ_TIMEOUT=300 \
    API_RETRY_TOTAL=1 \
    API_RETRY_CONNECT=2 \
    API_RETRY_READ=1 \
    API_POOL_CONN=10 \
    API_POOL_MAX=20 \
    API_POST_GZIP=false \
    RABBIT_HEARTBEAT_TICK=1.0 \
    LOG_LEVEL=INFO

ENTRYPOINT ["/usr/bin/tini","--"]


CMD ["python", "-m", "servimedQueue.run_scraper_consumer"]
