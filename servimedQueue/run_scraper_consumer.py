from servimedQueue.consumers.consumer_start_scrapy import ConsumerServimed
from servimedQueue.utils.worker_stream import start_scrap

consumerScraper = ConsumerServimed(start_scrap)
consumerScraper.start()
