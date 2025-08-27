# orderQueue/run_order_consumer.py
from orderQueue.consumers.order_consumer import ProductPosterConsumer

if __name__ == "__main__":
    ProductPosterConsumer().start()
