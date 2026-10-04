# DropJoy 1.1

**Encontre. Analise. Venda.**

DropJoy é uma plataforma web para comparar fornecedores, identificar oportunidades, estimar margem/lucro, gerar anúncios e preparar a operação com marketplaces.

## Estado do projeto

**MVP 1.1 concluído e publicável.** O núcleo funciona sem serviços pagos usando dados demo e gerador local de anúncios. Integrações externas reais ficam condicionadas às credenciais/documentação de cada conta.

| Área | Estado |
|---|---|
| Login, JWT e refresh token | ✅ |
| Recuperação de senha | ✅ SMTP opcional |
| Multi-tenant e RBAC | ✅ |
| Gestão de usuários | ✅ |
| Auditoria | ✅ |
| Radar / DropJoy Score | ✅ |
| Comparação de fornecedores | ✅ |
| Importação CSV/XLSX de fornecedor | ✅ |
| Histórico de preço/estoque | ✅ |
| Dropify | 🟡 adapter pronto, schema/credenciais pendentes |
| DSLite | 🟡 adapter pronto, schema/credenciais pendentes |
| DropJoy AI local | ✅ |
| DropJoy AI com OpenAI | ✅ configurável |
| Marketplaces / rascunhos | ✅ |
| Marketplace Demo | ✅ publicação simulada |
| Shopee | 🟡 fluxo pronto, contrato/autorização oficial pendente |
| PostgreSQL + Alembic | ✅ |
| Docker + Nginx | ✅ |
| CI GitHub Actions | ✅ |

## Executar rapidamente em modo local

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

Em outro terminal:

```powershell
cd frontend
python -m http.server 5500
```

Abra `http://127.0.0.1:5500`.

Login demo padrão:

- `joyce@example.com`
- `dropjoy-demo`

Use apenas em desenvolvimento.

## Produção com Docker

```bash
cp .env.production.example .env
# edite o .env com segredos reais
docker compose up -d --build
```

Acesse a porta definida em `APP_PORT` (padrão `8080`). Veja `docs/DEPLOYMENT.md`.

## Estrutura

```text
Projeto-DropJoy/
├─ backend/                 FastAPI, SQLAlchemy, Alembic
│  ├─ app/core/             configuração, JWT, RBAC
│  ├─ app/connectors/       Dropify, DSLite e adapters
│  ├─ app/marketplaces/     adapters de marketplace
│  ├─ app/routers/          API
│  ├─ app/services/         score, IA, e-mail, tokens, auditoria
│  └─ migrations/           schema versionado
├─ frontend/                SPA estática responsiva
├─ docs/                    arquitetura e deploy
├─ docker-compose.yml       PostgreSQL + API + Nginx
├─ SECURITY.md
└─ README.md
```

## Primeiro usuário em produção

Defina as variáveis `BOOTSTRAP_*` no `.env`. O container executa:

```bash
python -m app.cli bootstrap
```

O comando é idempotente e não recria um owner já existente.

## Integrações

### DropJoy AI

Sem `OPENAI_API_KEY`, o gerador local permanece funcional. Com uma chave, o backend usa a Responses API da OpenAI e o modelo indicado em `OPENAI_MODEL`.

### Fornecedores

Dropify e DSLite possuem adapters isolados. Eles propositalmente não inventam endpoints/schema: após a homologação, basta mapear a resposta real para `SupplierItem`.

### Shopee

O DropJoy já mantém contas, rascunhos e estado das listagens por tenant. A publicação real permanece bloqueada até haver acesso ao contrato/autenticação oficial da conta Shopee.

## Testes

```bash
cd backend
pytest -q
```

O CI também valida migrations, sintaxe Python, sintaxe JavaScript e Docker Compose.

## Segurança

Leia `SECURITY.md`. Nunca coloque chaves ou senhas no GitHub.

## Próxima etapa fora do código

Para transformar o MVP em operação real: obter credenciais de fornecedor/marketplace, configurar OpenAI/SMTP se desejado e publicar o stack no servidor apontado pelo domínio.


## Importar catálogo de fornecedor

Na tela **Fornecedores**, usuários `owner/admin` podem importar arquivos `.csv` ou `.xlsx`.

O importador reconhece nomes comuns de colunas. Campos obrigatórios:

- SKU/código
- Produto/nome
- Custo/preço atacado
- Estoque
- Preço de venda/varejo

Campos opcionais:

- GTIN/EAN — quando presente, permite que ofertas de fornecedores diferentes sejam relacionadas ao mesmo produto.
- Categoria
- Prazo em horas

A importação atualiza ofertas existentes e adiciona um snapshot ao histórico de preço/estoque. O limite atual é 10 MB e 5.000 linhas por arquivo.
