# DropJoy 1.4

**Encontre. Analise. Venda.**

DropJoy é uma plataforma web para comparar fornecedores, identificar oportunidades, estimar margem/lucro, gerar anúncios e preparar a operação com marketplaces.

## Estado do projeto

**MVP 1.4 concluído e publicável.** O núcleo funciona sem serviços pagos usando dados demo e gerador local de anúncios. Integrações externas reais ficam condicionadas às credenciais/documentação de cada conta.

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
| Mercado Livre | ✅ OAuth/PKCE, refresh e publicação User Products com validação oficial |
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


### Mercado Livre

O Mercado Livre está disponível como provider `mercadolivre` no DropJoy.

A integração segue a documentação oficial atual:
- OAuth 2.0 Authorization Code para autorização do seller.
- Tokens enviados no header `Authorization: Bearer ...`.
- Access token com renovação via refresh token.
- Novos fluxos de publicação devem considerar **User Products**.

O adapter possui:
- configuração de aplicação (`MELI_CLIENT_ID`, `MELI_CLIENT_SECRET`, `MELI_REDIRECT_URI`);
- suporte a status de configuração;
- geração segura da URL de autorização quando o fluxo OAuth for habilitado;
- validação da conta por `/users/me`;
- sugestão de categoria, leitura das regras e tipos de anúncio disponíveis;
- validação de atributos obrigatórios e condicionais;
- publicação User Products com condição, imagens por URL, estoque e descrição.

Nunca publique `MELI_CLIENT_SECRET`, access token ou refresh token no GitHub.


## Conectar Mercado Livre

A V1.3 implementa o fluxo real de autorização Mercado Livre:

1. Crie uma aplicação no DevCenter do Mercado Livre.
2. Cadastre uma Redirect URI HTTPS exatamente igual à configurada em `MELI_REDIRECT_URI`.
3. Habilite PKCE na aplicação; o DropJoy usa `S256`.
4. Configure as permissões necessárias para leitura/escrita e acesso offline conforme o uso da aplicação.
5. Preencha `MELI_CLIENT_ID`, `MELI_CLIENT_SECRET`, `MELI_REDIRECT_URI` e `MARKETPLACE_CREDENTIAL_KEY`.
6. No DropJoy, crie uma conta do tipo **Mercado Livre** e clique em **Conectar Mercado Livre**.

Access token e refresh token são armazenados criptografados no banco. O refresh token é substituído a cada renovação.

Veja `docs/MERCADO_LIVRE.md`.



### Validação antes de publicar no Mercado Livre

No fluxo padrão de User Products, o DropJoy executa o validador oficial `POST /items/validate` antes do `POST /items`. A publicação é interrompida quando o Mercado Livre retornar qualquer erro de validação. Para sellers com estoque multi-origem, o DropJoy usa o fluxo `/items/multiwarehouse` e as validações específicas de categoria, atributos e depósitos, sem inventar um endpoint de validação que não esteja documentado.
