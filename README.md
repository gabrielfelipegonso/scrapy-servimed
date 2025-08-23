# 📦 Scrapy Servimed

Crawler desenvolvido com [Scrapy](https://scrapy.org/) para autenticar no portal **Servimed**, buscar clientes ativos e coletar informações de produtos.

---

## ✨ Funcionalidades
- Login com usuário e senha.  
- Descoberta automática do **Client ID** válido.  
- Paginação automática na API de produtos.  
- Extração de informações de cada produto:
  - **GTIN (EAN)**  
  - **Código**  
  - **Descrição**  
  - **Preço de fábrica**  
  - **Estoque**  
- Exportação dos dados em **JSON**, **JSONLines** ou **CSV**.

---

## 🗂 Estrutura do projeto

```
scrapy_servimed/
├── scrapy.cfg                  # Configuração Scrapy (CLI)
├── run_spider.py               # Script de execução standalone
├── servimedScraper/
│   ├── settings.py             # Configurações do projeto Scrapy
│   ├── middlewares.py          # Middleware custom (auth headers/cookies)
│   ├── utils/
│   │   ├── jwt.py              # Função para decodificação JWT
│   │   └── requests.py         # Builders de JsonRequest (login, clientes, produtos)
│   └── spiders/
│       └── products.py         # Spider principal
└── tests/                      # Implementar os testes
```

---

## ⚙️ Requisitos

- Python 3.12+  
- [Poetry](https://python-poetry.org/) (recomendado) ou `pip`  
- Scrapy >= 2.13  

---

## 🚀 Instalação

Clone o repositório e instale as dependências:

```bash
git clone https://github.com/gabrielfelipeso/scrapy-servimed.git
cd scrapy-servimed
poetry install
```

Ou, sem Poetry:

```bash
pip install -r requirements.txt
```

---

## 🔑 Configuração de credenciais

As credenciais podem ser fornecidas de duas formas:

### 1. Via linha de comando
```bash
python run_spider.py --usuario "meu@email.com" --senha "minha_senha"
```

### 2. Via variáveis de ambiente
```bash
# Linux/macOS
export SERVIMED_USER="meu@email.com"
export SERVIMED_PASS="minha_senha"

# Windows (PowerShell)
$env:SERVIMED_USER="meu@email.com"
$env:SERVIMED_PASS="minha_senha"
```

---

## 🕷️ Executando o Spider

### Opção A – Usando a CLI do Scrapy
```bash
scrapy crawl products -a usuario="meu@email.com" -a senha="minha_senha" -o produtos.jsonl -t jsonlines
```

### Opção B – Usando o script `run_spider.py`
```bash
python run_spider.py   --usuario "meu@email.com"   --senha "minha_senha"   --output produtos.jsonl   --format jsonlines   --loglevel INFO
```

---

## 📊 Saída dos dados

Por padrão, os produtos são exportados em **JSONLines** (`.jsonl`), com um objeto por linha:

```json
{"gtin": "7891234567890", "codigo": "12345", "descricao": "Produto X", "preco_fabrica": 10.5, "estoque": 50}
{"gtin": "7899876543210", "codigo": "67890", "descricao": "Produto Y", "preco_fabrica": 8.0, "estoque": 0}
```

Também é possível exportar em JSON único ou CSV:
```bash
python run_spider.py -o produtos.json -f json
python run_spider.py -o produtos.csv -f csv
```

---

## 🛠 Boas práticas implementadas

- **Separação de responsabilidades**:
  - Spider cuida apenas do fluxo de scraping.
  - Middleware injeta headers/cookies de autenticação.
  - Utils centralizam a criação de requests (login, clientes, produtos).
- **Uso de `JsonRequest`** para evitar erros de serialização.  
- **State centralizado** (`self.state`) para guardar tokens, cookies e IDs.  
- **Script standalone (`run_spider.py`)** para execução automatizada e integração.  
- **Exportação configurável** (formato/arquivo via parâmetros).  
- **Compatível com Scrapy 2.13+** (`async def start`).  

---


