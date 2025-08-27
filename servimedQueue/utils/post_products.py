import json
from producers.post_product_producer import ProductProducer
import logging


def postProduct(products, count, producer_product: ProductProducer):
    publish_product(products)
    logging.info(f"📦 {count}: {json.dumps(product, ensure_ascii=False)}")
    pass


def publish_product(self, products) -> None:
    """
    Publica um produto (dict) como JSON UTF-8.
    Lança exceção se a mensagem não puder ser roteada (UnroutableError) ou NACK do broker (NackError).
    """
    body = json.dumps(products, ensure_ascii=False).encode("utf-8")
    props = pika.BasicProperties(
        delivery_mode=2,  # persistente
        content_type="application/json",
        content_encoding="utf-8",
    )
    try:

        self._ch.basic_publish(
            exchange="",
            routing_key=self.queue,
            body=body,
            properties=props,
            mandatory=True,
        )

        log.info(
            "Produto publicado na fila '%s'%s",
            self.queue,
            " (com confirms)" if self._confirms else "",
        )

    except UnroutableError as e:
        log.error(
            "Mensagem não roteada para a fila '%s' (fila inexistente ou binding incorreto)",
            self.queue,
        )
        raise
    except NackError as e:
        log.error("Broker NACKou a publicação para '%s'", self.queue)
        raise
    except (ChannelClosedByBroker, ConnectionClosed, StreamLostError) as e:
        log.exception("Falha de canal/conexão ao publicar")
        raise
