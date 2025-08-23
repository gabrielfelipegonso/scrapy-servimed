from scrapy.http import JsonRequest
import scrapy


def req_login(api_base: str, usuario: str, senha: str, *, callback, errback):
    return JsonRequest(
        url=f"{api_base}/api/usuario/login",
        data={"usuario": usuario, "senha": senha},
        callback=callback,
        errback=errback,
        dont_filter=True,
        priority=1000,
    )


def req_clientIds(api_base: str, state: dict, page: int, *, callback, errback):
    return JsonRequest(
        url=f"{api_base}/api/cliente/findByFilter",
        data={
            "filtro": "",
            "pagina": page,
            "registrosPorPagina": 20,
            "codigoExterno": state["external_code"],
            "codigoUsuario": state["user_code"],
            "users": state["users"],
            "list": True,
        },
        callback=callback,
        errback=errback,
        meta={"needs_auth": True},
        cb_kwargs={"page": page},
    )


def req_timestamp(api_base: str, *, callback, errback):
    return scrapy.Request(
        url=f"{api_base}/api/Produto/get-timestamp",
        method="GET",
        callback=callback,
        errback=errback,
        meta={"needs_auth": True},
    )


def req_products(
    api_base: str, state: dict, page: int, item: dict, *, callback, errback
):
    return JsonRequest(
        url=f"{api_base}/api/carrinho/oculto?siteVersion=4.0.27",
        data={
            "filtro": "",
            "pagina": page,
            "registrosPorPagina": 20,
            "ordenarDecrescente": False,
            "colunaOrdenacao": "nenhuma",
            "clienteId": item["codigo"],
            "tipoVendaId": 1,
            "pIIdFiltro": 0,
            "cestaPPFiltro": False,
            "codigoExterno": 0,
            "codigoUsuario": state["user_code"],
            "promocaoSelecionada": "",
            "indicadorTipoUsuario": "CLI",
            "kindUser": 0,
            "xlsx": [],
            "principioAtivo": "",
            "master": False,
            "kindSeller": 0,
            "grupoEconomico": "",
            "list": True,
        },
        headers={
            "x-peperone": str(state["timestamp"]),
            "x-cart": str(state["x-cart"]),
        },
        meta={"needs_auth": True},
        cb_kwargs={"page": page, "clientID": item["codigo"], "item": item},
        callback=callback,
        errback=errback,
    )
