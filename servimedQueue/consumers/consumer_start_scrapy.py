import os
import pika
from dotenv import load_dotenv
from servimedQueue.utils import worker_stream  # callback

load_dotenv()


def _int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


class ConsumerServimed:
    def __init__(self, callback) -> None:
        self.host = os.getenv("RABBIT_HOST")
        self.port = _int("RABBIT_PORT", 5672)
        self.user = os.getenv("RABBIT_USER", "guest")
        self.password = os.getenv("RABBIT_PASS", "guest")
        self.queue = os.getenv("RABBIT_QUEUE_SCRAPER", "queue.start_scrapy")
        self.callback = callback
        self.channel = self._create_channel()
        self._setup_consumer()

    def _create_channel(self):
        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=pika.PlainCredentials(self.user, self.password),
            heartbeat=_int("RABBIT_HEARTBEAT", 300),  # ex: 300s
            blocked_connection_timeout=_int("RABBIT_BLOCKED_TIMEOUT", 600),  # ex: 600s
            connection_attempts=_int("RABBIT_CONN_ATTEMPTS", 5),
            retry_delay=_int("RABBIT_RETRY_DELAY", 5),
        )
        connection = pika.BlockingConnection(params)
        return connection.channel()

    def _setup_consumer(self):
        self.channel.queue_declare(queue=self.queue, durable=True)
        self.channel.basic_qos(prefetch_count=_int("RABBIT_PREFETCH", 1))
        self.channel.basic_consume(
            queue=self.queue,
            auto_ack=False,
            on_message_callback=self.callback,
        )

    def start(self):
        print(f"[✓] Consumindo fila '{self.queue}' em {self.host}:{self.port} ...")
        self.channel.start_consuming()


if __name__ == "__main__":
    c = ConsumerServimed(callback=worker_stream.start_scrap)
    c.start()
