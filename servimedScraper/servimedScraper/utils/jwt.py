import base64, json, logging

logger = logging.getLogger(__name__)


def decode_jwt(token: str) -> dict | None:
    try:
        parts = token.split(".")
        if len(parts) != 3:
            logger.error("JWT inválido")
            return None
        payload = parts[1]
        padding = "=" * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload + padding)
        return json.loads(decoded)
    except Exception as e:
        logger.error(f"Erro ao decodificar JWT: {e}")
        return None
