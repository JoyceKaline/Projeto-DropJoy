# Integração Mercado Livre

## O que já está implementado

- OAuth 2.0 Authorization Code server-side.
- `state` aleatório de uso único.
- PKCE com método `S256`.
- Troca de authorization code por access/refresh token.
- Refresh token.
- Tokens criptografados em repouso.
- Vínculo do seller ao tenant correto.
- Validação de conta por `/users/me`.
- Botões Conectar, Renovar token e Desconectar.

A publicação real de produtos continua bloqueada até o DropJoy concluir o fluxo **User Products**, incluindo categoria, atributos obrigatórios, condição, imagens e estoque.

## 1. Criar a aplicação

Crie uma aplicação no portal de desenvolvedores do Mercado Livre.

A Redirect URI precisa usar HTTPS e deve ser idêntica ao valor usado pelo DropJoy. Em produção:

```text
https://app.joycekalinesilva.online/api/marketplaces/mercadolivre/callback
```

Se o DropJoy ainda não estiver publicado em HTTPS, use temporariamente uma URL HTTPS pública que encaminhe para o backend local. O Mercado Livre exige HTTPS para o cadastro da Redirect URI.

Habilite PKCE e use as permissões mínimas necessárias. Para uma integração que publica e mantém anúncios em nome do seller, configure as permissões de leitura/escrita e acesso offline conforme o DevCenter.

## 2. Gerar a chave de criptografia

No ambiente Python do backend:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copie o resultado para:

```env
MARKETPLACE_CREDENTIAL_KEY=COLE_A_CHAVE_AQUI
```

Nunca publique essa chave.

## 3. Configurar o .env

```env
MELI_ENABLED=true
MELI_CLIENT_ID=SEU_APP_ID
MELI_CLIENT_SECRET=SEU_CLIENT_SECRET
MELI_REDIRECT_URI=https://app.joycekalinesilva.online/api/marketplaces/mercadolivre/callback
MARKETPLACE_CREDENTIAL_KEY=SUA_CHAVE_FERNET
FRONTEND_BASE_URL=https://app.joycekalinesilva.online
```

Em desenvolvimento, `FRONTEND_BASE_URL` pode continuar como `http://127.0.0.1:5500`, mas a Redirect URI cadastrada no Mercado Livre ainda precisa ser uma URL HTTPS acessível.

## 4. Aplicar a migration

```powershell
cd backend
alembic upgrade head
```

No modo local com `AUTO_CREATE_SCHEMA=true`, as tabelas também são criadas pelo SQLAlchemy; ainda assim, mantenha as migrations aplicadas em ambientes persistentes.

## 5. Conectar

No DropJoy:

1. Entre em **Marketplaces**.
2. Adicione uma conta **Mercado Livre**.
3. O ID da conta é preenchido automaticamente após o OAuth.
4. Clique em **Conectar Mercado Livre**.
5. Autorize o DropJoy na conta principal do seller.
6. O Mercado Livre volta para o callback e o DropJoy retorna para a tela de Marketplaces já conectado.

## Segurança

- O Client Secret permanece somente no backend.
- Access e refresh tokens nunca são enviados ao frontend.
- Tokens ficam criptografados no banco.
- O parâmetro `state` é validado e expira em 10 minutos.
- O PKCE verifier também fica criptografado durante o fluxo.
- O refresh token do Mercado Livre é de uso único; o DropJoy salva o novo token devolvido em cada renovação.
