from consumers.consumer_post_product import ProductPosterConsumer
from dotenv import load_dotenv

load_dotenv()

consumer_post_products = ProductPosterConsumer()

consumer_post_products.start()
