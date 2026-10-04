# Deploy do DropJoy

## Pré-requisitos

- Servidor com Docker e Docker Compose.
- DNS do subdomínio apontando para o servidor.
- HTTPS na borda (Cloudflare, Caddy, Traefik ou proxy da hospedagem).

Sugestão de endereço: `app.joycekalinesilva.online`.

## 1. Configurar ambiente

```bash
cp .env.production.example .env
```

Troque obrigatoriamente:

- `POSTGRES_PASSWORD`
- `JWT_SECRET_KEY`
- `BOOTSTRAP_OWNER_EMAIL`
- `BOOTSTRAP_OWNER_PASSWORD`

A senha inicial do owner precisa ter pelo menos 12 caracteres.

## 2. Subir

```bash
docker compose up -d --build
```

O backend executa migrations e o bootstrap do primeiro owner antes de iniciar.

## 3. Verificar

```bash
curl http://localhost:8080/health
```

Deve retornar `status: ok` e versão `1.0.0`.

## 4. DNS/HTTPS

A aplicação expõe por padrão a porta `8080`. Configure seu proxy HTTPS para enviar tráfego de `app.joycekalinesilva.online` para essa porta. Depois disso, altere `APP_HOST` no `.env` para o domínio real e recrie os containers.

## 5. Integrações externas

### OpenAI

Defina `OPENAI_API_KEY`. Se ficar vazio, o DropJoy AI usa o gerador local.

### SMTP

Preencha as variáveis `SMTP_*` para recuperação de senha por e-mail.

### Dropify / DSLite / Shopee

Não habilite `*_ENABLED=true` até possuir credenciais e documentação da sua conta. O projeto não inclui tokens reais no repositório.

## Backup

O volume `dropjoy_pgdata` guarda o PostgreSQL. Em produção, configure backup regular com `pg_dump` e cópia para armazenamento externo.
