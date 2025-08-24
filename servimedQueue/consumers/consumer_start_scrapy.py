import os
import pika
from dotenv import load_dotenv
from servimedQueue.utils import stream_client_worker


load_dotenv()


class ConsumerServimed:
    def __init__(self, callback) -> None:
        self.host = os.getenv("RABBIT_HOST", "localhost")
        self.port = int(os.getenv("RABBIT_PORT", "5672"))
        self.user = os.getenv("RABBIT_USER", "guest")
        self.password = os.getenv("RABBIT_PASS", "guest")
        self.queue = os.getenv("RABBIT_QUEUE", "servimed")
        self.callback = callback
        self.channel = self._create_channel()
        self._setup_consumer()

    def _create_channel(self):
        params = pika.ConnectionParameters(
            host=self.host,
            port=self.port,
            credentials=pika.PlainCredentials(self.user, self.password),
        )
        connection = pika.BlockingConnection(params)
        return connection.channel()

    def _setup_consumer(self):

        self.channel.queue_declare(queue=self.queue, durable=True)

        self.channel.basic_consume(
            queue=self.queue,
            auto_ack=True,
            on_message_callback=self.callback,
        )

    def start(self):
        print(f"[✓] Consumindo fila '{self.queue}' em {self.host}:{self.port} ...")
        self.channel.start_consuming()


consumer = ConsumerServimed(stream_client_worker.main)
consumer.start()
