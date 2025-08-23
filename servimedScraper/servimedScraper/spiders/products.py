import scrapy
import json
from http.cookies import SimpleCookie
import logging
from servimedScraper.utils.jwt import decode_jwt
from servimedScraper.utils.requests import req_login, req_clientIds, req_products

logger = logging.getLogger(__name__)


class ProductsSpider(scrapy.Spider):
    name = "products"
    allowed_domains = ["pedidoeletronico.servimed.com.br", "peapi.servimed.com.br"]
    start_urls = ["https://pedidoeletronico.servimed.com.br/login"]

    api_base = "https://peapi.servimed.com.br"

    def __init__(self, usuario: str, senha: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.senha = senha
        self.state = {
            "access_token": None,
            "cookie_access_token": None,
            "user_code": None,
            "external_code": None,
            "users": [],
        }

    async def start(self):
        if not self.usuario or not self.senha:
            self.logger.error(
                "Credenciais ausentes: passe --usuario e --senha ou use as variáveis de ambiente."
            )
            return
        yield req_login(
            self.api_base,
            self.usuario,
            self.senha,
            callback=self.after_login,
            errback=self.on_login_error,
        )

    def after_login(self, response):
        try:
            data = response.json()

        except Exception:
            data = json.loads(response.text or "{}")
        try:
            self.state["external_code"] = data["usuario"]["codigoExterno"]

        except Exception:
            self.logger.error(f"Erro ao encontrar código externo: {Exception!r}")
        try:
            self.state["users"] = data["usuario"]["users"]

        except Exception:
            self.logger.error(f"Erro ao encontrar users: {Exception!r}")

        set_cookie_header = response.headers.get("set-cookie")
        if not set_cookie_header:
            self.logger.warning("Sem Set-Cookie no login; tentando token do corpo.")
        else:
            set_cookie_header = set_cookie_header.decode()

        cookie = SimpleCookie()
        if set_cookie_header:
            cookie.load(set_cookie_header)

        if "accesstoken" in cookie:
            self.state["cookie_access_token"] = cookie["accesstoken"].value
            payload = decode_jwt(self.state["cookie_access_token"])

            if payload:
                self.state["user_code"] = payload.get("codigoUsuario") or 0

                self.state["access_token"] = (
                    payload.get("token") or self.state["access_token"]
                )

        if not self.state["access_token"]:
            self.state["access_token"] = (
                data.get("access_token") or data.get("token") or ""
            )

        if not (self.state["cookie_access_token"] or self.state["access_token"]):
            self.logger.error("Não consegui obter token/cookie após login.")
            return

        page = 1
        yield req_clientIds(
            self.api_base,
            self.state,
            page,
            callback=self.find_valid_clientId,
            errback=self.on_client_error,
        )

    def find_valid_clientId(self, response, page):
        try:
            data = response.json()

        except Exception:
            data = json.loads(response.text or "{}")
        lista = data.get("lista", [])

        if not lista:
            self.logger.warning("Nenhum clientId ativo encontrado em nenhuma página.")
            return
        found_active = False
        for item in lista:
            if item["situacao"] != "INATIVO":
                page = 1
                found_active = True

                yield req_products(
                    self.api_base,
                    self.state,
                    page,
                    item,
                    callback=self.parse_products,
                    errback=self.on_client_error,
                )
                break

        if not found_active:
            next_page = page + 1
            yield req_clientIds(
                self.api_base,
                self.state,
                next_page,
                callback=self.find_valid_clientId,
                errback=self.on_client_error,
            )

    def parse_products(self, response, page, clientID, item):
        products = response.json()["lista"]
        if not products:
            return
        page = page + 1
        for product in products:
            yield {
                "gtin": product["codigoBarras"],
                "codigo": product["codigoExterno"],
                "descricao": product["descricao"],
                "preco_fabrica": product["precoVenda"],
                "estoque": product["quantidadeEstoque"],
            }

        yield req_products(
            self.api_base,
            self.state,
            page,
            item,
            callback=self.parse_products,
            errback=self.on_client_error,
        )

    def on_login_error(self, failure):
        self.logger.error(f"Erro no login: {failure!r}")

    def on_client_error(self, failure):
        self.logger.error(f"Erro ao chamar carrinho/oculto: {failure!r}")
