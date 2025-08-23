import hmac
import hashlib
import json
from typing import Any, Optional, Union


def generate_x_cart(
    timestamp: Union[int, str], chave_secreta: str = "MINHA_CHAVE_SECRETA"
) -> str:
    ts_str = str(timestamp)
    msg = ts_str.encode("utf-8")
    return hmac.new(chave_secreta.encode("utf-8"), msg, hashlib.sha256).hexdigest()
