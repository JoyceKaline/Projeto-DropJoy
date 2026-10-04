# Segurança

## Segredos

Nunca faça commit de `.env`, tokens de fornecedor, chaves OpenAI, credenciais SMTP, senhas ou tokens de marketplace.

## Controles existentes

- Hash Argon2 para senhas.
- JWT de curta duração.
- Refresh tokens opacos armazenados somente como SHA-256.
- Rotação e revogação de refresh tokens.
- Recuperação de senha com token de uso único.
- RBAC por tenant.
- Auditoria de ações relevantes.
- Bloqueio da chave JWT padrão fora de desenvolvimento/teste.
- Credenciais de integrações externas fornecidas por ambiente, não pelo frontend.

## Antes de exposição pública

- Ative HTTPS obrigatório.
- Gere `JWT_SECRET_KEY` aleatória e longa.
- Desative `SEED_DEMO_DATA` e `EXPOSE_RESET_TOKENS_IN_DEV`.
- Use PostgreSQL com backup.
- Configure rate limiting/WAF no proxy de borda.
- Restrinja acesso administrativo.
- Revise logs sem registrar segredos.

## Relato de vulnerabilidade

Enquanto o projeto for privado/pessoal, registre achados como issue privada ou trate fora do repositório público para evitar divulgar detalhes exploráveis antes da correção.


## Credenciais de marketplaces

Tokens OAuth de marketplaces são criptografados em repouso. Em produção, configure uma `MARKETPLACE_CREDENTIAL_KEY` Fernet exclusiva e mantenha-a fora do GitHub. A perda dessa chave impede a descriptografia dos tokens já salvos.
