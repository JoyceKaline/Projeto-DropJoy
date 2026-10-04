# DropJoy V5

**Encontre. Analise. Venda.**

A V5 adiciona a primeira camada real de identidade e segurança do DropJoy: autenticação por e-mail/senha, senhas com hash Argon2, JWT e autorização do tenant pelo usuário autenticado.

## Destaques da V5

- Login via `POST /api/auth/login`.
- JWT com expiração configurável.
- Senhas armazenadas com hash Argon2 via `pwdlib`.
- `/api/auth/me` para sessão atual.
- O tenant não é mais escolhido pelo navegador através de `X-Tenant-Slug`; ele é obtido do usuário autenticado.
- Proteção dos endpoints de Dashboard, Produtos, Fornecedores e Integrações.
- Alembic configurado com migration inicial.
- Bloqueio de chave JWT padrão fora de desenvolvimento/teste.
- Frontend com tela de login, sessão em `sessionStorage` e logout.
- GitHub Actions executando os testes do backend em push/PR.

## Rodar localmente no Windows

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`

### Frontend

Em outro terminal:

```powershell
cd frontend
python -m http.server 5500
```

Abra `http://127.0.0.1:5500`.

### Login demo

Com os valores padrão de desenvolvimento do `.env.example`:

- E-mail: `joyce@demo.local`
- Senha: `dropjoy-demo`

Essas credenciais existem apenas para desenvolvimento local. Em qualquer ambiente publicado, desative `SEED_DEMO_DATA` e configure usuários reais.

## Migração da V4 local para V5

A V4 criava o SQLite diretamente, sem controle de migrations. Como esse banco continha apenas dados demo, a migração local mais segura é:

1. Pare o backend.
2. Exclua o arquivo local `backend/dropjoy.db`, caso exista.
3. Suba novamente a V5 para recriar os dados demo; ou use Alembic em um banco limpo.

Não faça isso em banco com dados reais.

## Alembic

Para usar migrations como fonte do schema:

```powershell
cd backend
copy .env.example .env
```

No `.env`, ajuste:

```env
AUTO_CREATE_SCHEMA=false
SEED_DEMO_DATA=false
```

Depois:

```powershell
alembic upgrade head
```

Em produção, migrations devem ser executadas antes da aplicação.

## Segurança de produção

Nunca publique o `.env`. Configure uma `JWT_SECRET_KEY` longa e aleatória. O backend se recusa a iniciar fora de `development/test` se a chave continuar como `dev-only-change-me`.

A V5 usa access token. Refresh tokens, recuperação de senha, verificação de e-mail e MFA ficam para uma etapa posterior, antes de abrir cadastro público.

## Dropify

O conector continua propositalmente sem endpoints inventados. Ele só será ativado depois que tivermos credenciais/documentação homologada da Dropify.

## Próximos marcos

1. Cadastro/admin de usuários e papéis.
2. Refresh token + recuperação de senha.
3. Isolamento tenant-aware dos dados privados futuros.
4. Homologação da Dropify e sync real.
5. Conector DSLite.
6. DropJoy AI.
7. Integração autorizada com Shopee.
