# DropJoy V4

**Encontre. Analise. Venda.**

A V4 transforma o MVP em uma base mais próxima da arquitetura definitiva do repositório `Projeto-DropJoy`: backend modular, isolamento por tenant e camada de conectores de fornecedores.

## O que entrou na V4

- FastAPI modularizado em routers/services/connectors/core.
- SQLAlchemy 2 com SQLite no modo demo e PostgreSQL configurável.
- Estrutura multi-tenant inicial (`Tenant`, `User` e vínculo tenant-fornecedor).
- Catálogo multi-fornecedor, comparação de ofertas, lucro/margem e DropJoy Score.
- Histórico de preço/estoque persistido.
- Sincronização demo que cria novos snapshots de custo/estoque.
- Registro de integrações e status por fornecedor.
- Adapter `DropifyConnector` seguro: prepara HTTP/configuração sem inventar endpoints ou schema.
- `.env.example` sem segredos.
- Frontend responsivo mostrando Radar, detalhe do produto e status das integrações.
- Teste unitário básico do motor financeiro/score.

## Estrutura

```text
Projeto-DropJoy/
├─ backend/
│  ├─ app/
│  │  ├─ connectors/
│  │  │  ├─ base.py
│  │  │  ├─ demo.py
│  │  │  ├─ dropify.py
│  │  │  └─ registry.py
│  │  ├─ core/
│  │  │  ├─ config.py
│  │  │  └─ tenant.py
│  │  ├─ routers/
│  │  │  ├─ dashboard.py
│  │  │  ├─ integrations.py
│  │  │  ├─ products.py
│  │  │  └─ suppliers.py
│  │  ├─ services/
│  │  │  ├─ scoring.py
│  │  │  └─ sync.py
│  │  ├─ db.py
│  │  ├─ models.py
│  │  ├─ seed.py
│  │  └─ main.py
│  ├─ tests/
│  │  └─ test_scoring.py
│  ├─ .env.example
│  └─ requirements.txt
├─ frontend/
│  └─ index.html
├─ .gitignore
└─ README.md
```

## Rodar no Windows

### 1. Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000`
Swagger: `http://127.0.0.1:8000/docs`

### 2. Frontend

Em outro terminal:

```powershell
cd frontend
python -m http.server 5500
```

Abra `http://127.0.0.1:5500`.

## Tenant demo

O frontend envia `X-Tenant-Slug: joyce-demo`. Esse cabeçalho é a primeira camada de isolamento de contas; **não substitui autenticação**. Login/JWT/OAuth entra no próximo marco antes de qualquer uso público.

## Dropify

A Dropify divulga oficialmente uma API JSON/REST capaz de trabalhar com produtos/categorias, preço e estoque por usuário, pedidos, frete, notas fiscais, etiquetas e webhooks. O acesso depende de cadastro/homologação e credenciais.

Por isso a V4 **não inventa endpoints, autenticação nem formato de resposta**. O `DropifyConnector` fica desativado até que existam credenciais e o schema real da conta homologada possa ser mapeado.

Variáveis reservadas:

```env
DROPIFY_ENABLED=false
DROPIFY_BASE_URL=
DROPIFY_API_TOKEN=
DROPIFY_PRODUCTS_PATH=
DROPIFY_STOCK_PATH=
```

Nunca coloque tokens no GitHub.

## Taxas do marketplace

Os valores `20% + R$4` continuam apenas como **premissas demonstrativas configuráveis**. Não são apresentadas como tarifas oficiais atuais da Shopee.

## Próximos marcos

1. Autenticação real e autorização por tenant.
2. Alembic para migrations.
3. Homologação/credenciais Dropify e mapeamento do payload real.
4. Sync real de catálogo/preço/estoque + webhooks.
5. Conector DSLite.
6. DropJoy AI para título, descrição e análise de anúncio.
7. Integração autorizada com Shopee e demais marketplaces.
