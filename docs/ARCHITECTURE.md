# Arquitetura DropJoy 1.0

## Visão geral

O DropJoy é um SaaS multi-tenant para descoberta de oportunidades, comparação de fornecedores, geração de anúncios e orquestração de publicação em marketplaces.

```text
Navegador
   |
Nginx (frontend + reverse proxy)
   |
FastAPI
   |-- Auth/RBAC/Auditoria
   |-- Radar + Score
   |-- DropJoy AI
   |-- Conectores de fornecedores
   |-- Conectores de marketplaces
   |
PostgreSQL
```

## Backend

- FastAPI para HTTP/API.
- SQLAlchemy 2 para persistência.
- Alembic para migrations.
- JWT curto + refresh token opaco e hasheado.
- Argon2 para senhas.
- RBAC: `owner`, `admin`, `member`.
- Auditoria por tenant.

## Multi-tenant

Dados de conta, usuários, fornecedores habilitados, contas de marketplace, listagens e auditoria possuem escopo de tenant. O catálogo e as ofertas dos fornecedores são compartilháveis, mas o Radar filtra apenas fornecedores habilitados para o tenant autenticado.

## Conectores

Cada fornecedor/marketplace fica atrás de um adapter. O código não assume contratos que não foram confirmados. O catálogo CrossDocking da DSLite usa o contrato público oficial (header `Token`, paginação e coleção `produtos`), mas permanece desativado até o token e o fornecedor da conta serem informados no ambiente. Dropify e Shopee continuam bloqueados para operação real até credenciais e schemas oficiais estarem disponíveis.

## DropJoy AI

Sem chave externa, existe um gerador local seguro que cria uma base de anúncio sem inventar ficha técnica. Com `OPENAI_API_KEY`, o serviço usa a Responses API e modelo configurável por `OPENAI_MODEL`.

## Deploy

Em produção, Nginx serve o frontend e encaminha `/api/*` ao FastAPI. O Docker Compose inclui PostgreSQL persistente. O backend executa `alembic upgrade head` antes de iniciar.
