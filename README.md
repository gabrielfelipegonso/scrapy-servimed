# 📦 Scrapy Servimed

Crawler desenvolvido com [Scrapy](https://scrapy.org/) para fazer login no portal **Servimed**, buscar um id de cliente ativo e coletar informações de produtos gerando dinamicamente um .

## Quais são os projetos

Dentro da cada pasta há uma etapa do desafio:

1) ServimedScraper -> abriga o scraper
2) servimedQueue -> abria a fila que recebe o usuário e senha da servimed e faz o scraper no usuário da cote que estiver no env.
3) coteFacilQueue -> Vai receber o pedido e registrar.

## 🔍 Observações acerca do teste

Agradeço a oportunidade de participar do processo seletivo, a prova foi muito bem feita e detalhada e gostei do processo de construir este projeto.

Fiz as requisições 1 a 1 no scraper até encontrar uma com lista vazia pois isso tornou mais robusto, no primeiro teste que fiz direto à API da servimed o cálculo deles de quantidade total de produtos não batia com a quantidade de páginas máxima.

Sugiro adicionar que o gtin precisa ter pelo menos 8 caracteres e como completar em caso de haver menos. o produto com gtin 450619 tem um código de barras menor do que 8 caracteres.Para entregar a prova eu apenas completei com zeros a esquerda na function  parse_products do spider.

## Um resumo para rodar rapidamente COM DOCKER
Na raiz do projeto rode:
```bash
docker compose up --build -d

```

## Um resumo para rodar rapidamente SEM DOCKER
Se certifique de ter o poetry instalado, então clone o projeto:

```bash
git clone https://github.com/gabrielfelipegonso/scrapy-servimed
cd scrapy-servimed
poetry install
```
Existem outras variáveis de ambiente mas inicialmente configure as qe estão abaixo e funcionará:
```env
RABBIT_HOST=localhost
RABBIT_PORT=5672
RABBIT_USER=guest
RABBIT_PASS=guest
RABBIT_QUEUE_SCRAPER=servimed
API_TOKEN_URL= "https://desafio.cotefacil.net/oauth/token"
API_USERNAME_COTE= "seu_usuario"
API_PASSWORD_COTE= "sua_senha"
RABBIT_QUEUE_PRODUCTS=post_products_cote_facil
API_PRODUCTS_URL="https://desafio.cotefacil.net/produto"
LOG_EVERY_N= 1
LOG_EACH_ITEM = 1
RABBIT_HEARTBEAT=300
RABBIT_BLOCKED_TIMEOUT=600
RABBIT_PREFETCH=1
RABBIT_CONN_ATTEMPTS=5
RABBIT_RETRY_DELAY=5
RABBIT_HEARTBEAT_TICK=1.0
```

Ative seu ambiente virtual, é só rodar o comando abaixo, copiar a saída e colar em seu terminal:

```bash
poetry env activate
```
No ambiente ativo você pode rodar os dois projetos, há um arquivo dentro da pasta servimedScraper que serve para rodar apenas o scraper e dá a possibilidade de você rodar e salvar em um jsonl os arquivos, pra rodar o scraper separadamente é só rodar:

```bash
python run_spider.py   --usuario "meu@email.com"   --senha "minha_senha"   --output produtos.jsonl   --format jsonlines   --loglevel INFO
```
E isso vai gerar um arquivo produtos.jsonl na raiz do scraper, mas você pode passar outro endereço caso queira.

Na segunda etapa do desafio é solicitado que rode-se uma fila que espera um usuário e uma senha para começar a receber os produtos. para rodar essa fila é só rodar  o script que esta em servimedQueue e chama run_scraper_consumer.py:


```bash
python run_scraper_consumer.py
```


---
# 🕷️ Primeira etapa - Scraper - servimedScraper

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


# 📨 Segunda etapa: Mensageria (RabbitMQ) - servimedQueue

Integra o scraper a um fluxo de mensageria para execução sob demanda e envio do resultado em um único POST (array JSON).

## 🎯 Objetivo

Disparar o scraping por mensagem em fila.

Aguardar o spider concluir.

Enviar todos os itens de uma vez para o endpoint (API_PRODUCTS_URL).

Tratar retries/NACK quando a API estiver indisponível.

## 🧩 Componentes
servimedQueue/
├── consumers/
│   └── consumer_start_scrapy.py   # Conecta no RabbitMQ e escuta a fila de start
└── utils/
    ├── worker_stream.py           # Callback: roda o spider e faz um POST único
    └── auth.py                    # AuthClient (password grant) para obter o token


O consumer_start_scrapy usa worker_stream.start_scrap, que:

1) executa run_spider.py,
2) acumula itens emitidos via stdout (JSONL), 
3) realiza um POST com o array completo.

🔄 Fluxo

Publica-se uma mensagem JSON na fila RABBIT_QUEUE_SCRAPER:

```json
{ "usuario": "email@dominio.com", "senha": "secret", "tipo de venda": 1 }
```

O consumer se inicia e chama o worker

O worker executa o spider e coleta cada linha JSON.

Ao finalizar, o worker POSTA um array para API_PRODUCTS_URL usando AuthClient (Bearer token).

ACK só após POST bem-sucedido.

HTTP 429/5xx → NACK requeue

HTTP 4xx → NACK sem requeue

⚙️ Variáveis de ambiente (mensageria)
# RabbitMQ
RABBIT_HOST=localhost
RABBIT_PORT=5672
RABBIT_USER=guest
RABBIT_PASS=guest
RABBIT_QUEUE_SCRAPER=queue.start_scrapy
RABBIT_PREFETCH=1

# Timeouts/heartbeats (útil para scrapes longos)
RABBIT_HEARTBEAT=300
RABBIT_BLOCKED_TIMEOUT=600
RABBIT_CONN_ATTEMPTS=5
RABBIT_RETRY_DELAY=5
RABBIT_HEARTBEAT_TICK=1.0  # frequência (s) do "tick" de heartbeat no worker

# API destino (POST único com array)
API_PRODUCTS_URL=https://sua.api.exemplo/produtos

# Auth (password grant) usados por utils/auth.py
API_TOKEN_URL=https://sso.exemplo/oauth/token
API_USERNAME_COTE=usuario
API_PASSWORD_COTE=senha
API_CLIENT_ID_COTE=
API_CLIENT_SECRET_COTE=
API_SCOPE_COTE=

# Scraper
SERVIMED_SALE_TYPE=1
LOG_LEVEL=INFO

# Logs do worker (opcionais)
LOG_EACH_ITEM=false     # true = loga cada item (verboso)
LOG_EVERY_N=0           # >0 = loga a cada N itens

## ▶️ Como rodar o consumer
### opção A
python servimedQueue/consumers/consumer_start_scrapy.py

### opção B (módulo)
python -m servimedQueue.consumers.consumer_start_scrapy

## 📨 Publicando uma mensagem de teste

```python
import json, os, pika

conn = pika.BlockingConnection(pika.ConnectionParameters(
    host=os.getenv("RABBIT_HOST","localhost"),
    port=int(os.getenv("RABBIT_PORT","5672")),
    credentials=pika.PlainCredentials(
        os.getenv("RABBIT_USER","guest"),
        os.getenv("RABBIT_PASS","guest")
    )
))
ch = conn.channel()
q = os.getenv("RABBIT_QUEUE_SCRAPER","queue.start_scrapy")
ch.queue_declare(queue=q, durable=True)

body = json.dumps({
    "usuario":"meu@email.com",
    "senha":"minha_senha",
    "tipo de venda":1
})
ch.basic_publish(
    exchange="",
    routing_key=q,
    body=body,
    properties=pika.BasicProperties(delivery_mode=2) # persistente
)
conn.close()
print("mensagem publicada")
```


## 🧠 Heartbeats e conexões longas

Scrapes demorados podem derrubar a conexão se heartbeats não forem processados.

No consumer, aumente RABBIT_HEARTBEAT e RABBIT_BLOCKED_TIMEOUT.

No worker, há um tick periódico (process_data_events) controlado por RABBIT_HEARTBEAT_TICK para manter a conexão viva durante a execução do spider.

## 🪵 Logs do Scrapy aparecendo como ERROR

O Scrapy loga (INFO/WARNING/…) em stderr. O worker_stream reencaminha preservando o nível para não marcar tudo como ERROR.


# 📨 TErceira etapa: Mensageria (RabbitMQ) - servimedQueue

Cria pedidos na api cote facil.



## 🧩 Componentes
orderQueue/
├── consumers/
│   └── run_order_consumer.py   # Conecta no RabbitMQ e escuta a fila de pedidos
├── run_prder_consumer.py # Roda o consumer

O run_order_onsumer:

1) Lê e valida a mensagem
2) Autentica na api usando a lib compartilhada 
3) realiza um POST com o pedido.

🔄 Fluxo

Publica-se uma mensagem JSON na fila RABBIT_QUEUE_PRODUCTS:

```json
{
"usuario": "fornecedor_user",
"senha": "fornecedor_pass",
"id_pedido": "1234",
"produtos": [
{
"gtin": "1234567890123",
"codigo": "A123",
"quantidade": 1,
}
```

O consumer se inicia, faz as validações, emite os logs e posta o pedido.
