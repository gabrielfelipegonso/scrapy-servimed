import json


def postProduct(product, count):
    print(f"📦 {count}: {json.dumps(product, ensure_ascii=False)}")
    pass
