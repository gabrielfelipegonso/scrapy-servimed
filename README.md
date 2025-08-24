# 📦 Scrapy Servimed

Crawler desenvolvido com [Scrapy](https://scrapy.org/) para fazer login no portal **Servimed**, buscar um id de cliente ativo e coletar informações de produtos gerando dinamicamente um .

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
git clone https://github.com/gabrielfelipegonso/scrapy-servimed
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
$env:SERVIMED_SALE_TYPE= '1' ou "2" 
```

---

## 🕷️ Executando o Spider

Após ativar o ambiente virtual e acessar no seu terminal a pasta que contém o script run_spider.py (servimedScraper\servimedScraper)

### Opção A – Usando a CLI do Scrapy
```bash
scrapy crawl products -a usuario="meu@email.com" -a senha="minha_senha" -o produtos.jsonl -t jsonlines
```

### Opção B – Usando o script `run_spider.py`
```bash
python run_spider.py   --usuario "meu@email.com"   --senha "minha_senha"   --output produtos.jsonl   --format jsonlines   --loglevel INFO
```

---

## 📊 Saída dos dadoss

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
## ⚙️ Parâmetros do run_spider.py

O script run_spider.py permite executar o spider diretamente, sem precisar usar o comando scrapy crawl. Ele aceita diversos parâmetros para configurar a execução:

| Parâmetro       | Atalho | Default         | Descrição                                                                                                                      |
| --------------- | ------ | ---------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `--usuario`     | `-u`   | `SERVIMED_USER`  | Usuário de login. Pode ser passado na CLI ou via variável de ambiente.                                                         |
| `--senha`       | `-p`   | `SERVIMED_PASS`  | Senha de login. Pode ser passada na CLI ou via variável de ambiente.                                                           |
| `--output`      | `-o`   | `produtos.jsonl` | Caminho do arquivo de saída. Aceita qualquer extensão suportada (`.json`, `.jsonl`, `.csv`).                                   |
| `--format`      | `-f`   | `jsonlines`      | Formato do output (`json`, `jsonlines`, `csv`).                                                                                |
| `--loglevel`    |        | `INFO`           | Nível de log do Scrapy (`DEBUG`, `INFO`, `WARNING`, `ERROR`).                                                                  |
| `--concurrency` |        | `8`              | Número máximo de requisições concorrentes (`CONCURRENT_REQUESTS`).                                                             |
| `--delay`       |        | `0.1`            | Atraso (em segundos) entre requisições (`DOWNLOAD_DELAY`).                                                                     |
| `--saleType`    | `-s`   | `1`              | Tipo de venda para as requisições de produtos: `0` (à vista) ou `1` (a prazo). Pode ser definido via env `SERVIMED_SALE_TYPE`. |

## 🌍 Variáveis de Ambiente

Além dos parâmetros na linha de comando, você pode configurar o spider através de variáveis de ambiente:

| Variável             | Equivalente CLI | Descrição                                     |
| -------------------- | --------------- | --------------------------------------------- |
| `SERVIMED_USER`      | `--usuario`     | Usuário de login do portal Servimed.         |
| `SERVIMED_PASS`      | `--senha`       | Senha de login do portal Servimed.                               |
| `SERVIMED_SALE_TYPE` | `--saleType`    | Tipo de venda (`0` = à vista, `1` = a prazo). |

## 📝 Exemplos completos de execução
### 1. Executando com credenciais direto na CLI

```bash
  python run_spider.py -u meu.email@dominio.com -p MinhaSenha
```
### 2. Alterando o formato de saída
#### Salvando em JSON
```bash
  python run_spider.py -u meu.email@dominio.com -p MinhaSenha -o produtos.json -f json
```
#### Salvando em CSV
```bash
  python run_spider.py -u meu.email@dominio.com -p MinhaSenha -o produtos.csv -f csv
```

### 3;Usando variáveis de ambiente (sem passar --usuario/--senha)



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


