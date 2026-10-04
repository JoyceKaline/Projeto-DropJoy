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

O fluxo real de **User Products** está implementado para o site brasileiro (MLB):

- sugestão de categoria por `/sites/MLB/domain_discovery/search`;
- regras da categoria por `/categories/{category_id}`;
- atributos por `/categories/{category_id}/attributes`, incluindo `required` e `new_required`, e validação condicional;
- tipos de anúncio disponíveis para o seller;
- pré-validação oficial por `POST /items/validate` para o fluxo padrão;
- publicação por `POST /items` com `family_name`, condição do item via `ITEM_CONDITION` quando disponível, imagens, estoque e atributos;
- detecção de sellers com `warehouse_management` e publicação por `POST /items/multiwarehouse` com `stock_locations`;
- descrição em texto simples após a criação do item.

O formulário aceita imagens por URL pública. Para produção, use URLs HTTPS estáveis e siga os requisitos de resolução e qualidade do Mercado Livre.

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

## 6. Criar e publicar um User Product

1. Escolha a conta Mercado Livre conectada e um produto do DropJoy.
2. Use **Sugerir categoria** ou informe uma categoria final `MLB...`.
3. Carregue as regras oficiais da categoria.
4. Preencha os atributos obrigatórios exibidos, a condição, o tipo de anúncio, o estoque e ao menos uma imagem pública.
   Para sellers multi-origem, o formulário carrega os depósitos oficiais e exige a quantidade por `store_id`/`network_node_id`.
5. Crie o rascunho e publique.

Antes de enviar o item, o backend consulta novamente categoria, atributos obrigatórios, atributos condicionais e tipos de anúncio disponíveis. As chamadas usam sempre o token da conta vinculada ao mesmo tenant.

## Segurança

- O Client Secret permanece somente no backend.
- Access e refresh tokens nunca são enviados ao frontend.
- Tokens ficam criptografados no banco.
- O parâmetro `state` é validado e expira em 10 minutos.
- O PKCE verifier também fica criptografado durante o fluxo.
- O refresh token do Mercado Livre é de uso único; o DropJoy salva o novo token devolvido em cada renovação.



### Condição do produto

Para novas integrações, o DropJoy prefere o atributo `ITEM_CONDITION` retornado pela própria categoria. O campo legado `condition` só permanece como fallback quando a categoria não expõe esse atributo. Os IDs não são inventados nem fixados no código: o valor é resolvido a partir dos valores permitidos pela categoria.

### Gate de validação

Antes do `POST /items` padrão, o DropJoy chama `POST /items/validate`. HTTP 204 é tratado como payload válido; qualquer rejeição impede a publicação e a mensagem do Mercado Livre fica disponível na listagem.

Para sellers com `warehouse_management`, a criação ocorre por `POST /items/multiwarehouse`. Como a documentação pública não define um `/items/validate` equivalente específico para esse contrato, o DropJoy mantém as validações de categoria, atributos condicionais, tipo de anúncio e depósitos e deixa a API de criação fazer a validação final do estoque multi-origem.
