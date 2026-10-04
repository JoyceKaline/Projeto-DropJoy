const API = (location.hostname === '127.0.0.1' || location.hostname === 'localhost') ? 'http://127.0.0.1:8000' : '';
const ACCESS_KEY = 'dropjoy_access_token';
const REFRESH_KEY = 'dropjoy_refresh_token';
let currentUser = null;
let productsCache = [];
let marketplaceCache = {accounts: [], listings: []};

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));
const brl = (n) => new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL'}).format(Number(n || 0));
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

function apiErrorMessage(data, fallback){
  const detail = data && data.detail;
  if(Array.isArray(detail)){
    return detail.map(item => item && (item.msg || item.message) ? (item.msg || item.message) : JSON.stringify(item)).join(' · ');
  }
  if(detail && typeof detail === 'object'){
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  return detail || fallback;
}

function saveSession(data){
  sessionStorage.setItem(ACCESS_KEY, data.access_token);
  sessionStorage.setItem(REFRESH_KEY, data.refresh_token);
  currentUser = data.user;
}
function clearSession(){
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  currentUser = null;
}
function accessToken(){ return sessionStorage.getItem(ACCESS_KEY); }
function refreshToken(){ return sessionStorage.getItem(REFRESH_KEY); }

async function refreshSession(){
  const rt = refreshToken();
  if(!rt) return false;
  const r = await fetch(API + '/api/auth/refresh', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({refresh_token:rt})
  });
  if(!r.ok){ clearSession(); return false; }
  const data = await r.json();
  saveSession(data);
  return true;
}

async function api(path, options, retry){
  options = options || {};
  retry = retry !== false;
  const headers = Object.assign({'Content-Type':'application/json'}, options.headers || {});
  if(accessToken()) headers.Authorization = 'Bearer ' + accessToken();
  const r = await fetch(API + path, Object.assign({}, options, {headers}));
  if(r.status === 401 && retry && refreshToken()){
    const ok = await refreshSession();
    if(ok) return api(path, options, false);
  }
  let data = null;
  try{ data = await r.json(); }catch(_){}
  if(!r.ok) throw new Error(apiErrorMessage(data, 'HTTP ' + r.status));
  return data;
}

async function apiUpload(path, formData, retry){
  retry = retry !== false;
  const headers = {};
  if(accessToken()) headers.Authorization = 'Bearer ' + accessToken();
  const r = await fetch(API + path, {method:'POST',headers,body:formData});
  if(r.status === 401 && retry && refreshToken()){
    const ok = await refreshSession();
    if(ok) return apiUpload(path, formData, false);
  }
  let data = null;
  try{ data = await r.json(); }catch(_){}
  if(!r.ok) throw new Error(apiErrorMessage(data, 'HTTP ' + r.status));
  return data;
}

function toast(message){
  const el = $('#toast');
  el.textContent = message;
  el.classList.remove('hidden');
  setTimeout(() => el.classList.add('hidden'), 3200);
}

function showAuth(){
  $('#appView').classList.add('hidden');
  $('#loginView').classList.remove('hidden');
}
function showApp(user){
  currentUser = user;
  $('#loginView').classList.add('hidden');
  $('#resetView').classList.add('hidden');
  $('#appView').classList.remove('hidden');
  $('#profileName').textContent = user.name;
  $('#profileEmail').textContent = user.email;
  $('#profileRole').textContent = user.role;
  $$('.admin-only').forEach(el => el.classList.toggle('hidden', !['owner','admin'].includes(user.role)));
}

const viewMeta = {
  radar:['Radar de Oportunidades','Priorize produtos por margem, estoque, prazo e confiabilidade.'],
  products:['Produtos','Explore o catálogo disponível nos fornecedores ativos.'],
  ai:['DropJoy AI','Crie uma primeira versão de anúncio sem inventar especificações.'],
  suppliers:['Fornecedores','Gerencie quais fornecedores entram no seu Radar.'],
  marketplaces:['Marketplaces','Crie contas, rascunhos e acompanhe a publicação.'],
  finance:['Financeiro','Veja margem e lucro estimados a partir das premissas configuradas.'],
  users:['Usuários','Gerencie o acesso da sua equipe.'],
  audit:['Auditoria','Acompanhe ações relevantes da conta.']
};

async function switchView(name){
  $$('.view').forEach(v => v.classList.add('hidden'));
  $('#view-' + name).classList.remove('hidden');
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === name));
  $('#pageTitle').textContent = viewMeta[name][0];
  $('#pageSubtitle').textContent = viewMeta[name][1];
  try{
    if(name === 'radar') await loadRadar();
    if(name === 'products') await loadProducts();
    if(name === 'ai') await prepareAi();
    if(name === 'suppliers') await loadSuppliers();
    if(name === 'marketplaces') await loadMarketplaces();
    if(name === 'finance') await loadFinance();
    if(name === 'users') await loadUsers();
    if(name === 'audit') await loadAudit();
  }catch(e){ toast(e.message); }
}

async function login(ev){
  ev.preventDefault();
  $('#loginMessage').textContent = '';
  try{
    const r = await fetch(API + '/api/auth/login',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email:$('#loginEmail').value,password:$('#loginPassword').value})
    });
    const data = await r.json();
    if(!r.ok) throw new Error(apiErrorMessage(data, 'Não foi possível entrar.'));
    saveSession(data);
    showApp(data.user);
    await switchView('radar');
  }catch(e){ $('#loginMessage').textContent = e.message; }
}

async function logout(){
  try{
    if(accessToken() && refreshToken()){
      await api('/api/auth/logout',{method:'POST',body:JSON.stringify({refresh_token:refreshToken()})});
    }
  }catch(_){}
  clearSession();
  showAuth();
}

async function forgotPassword(){
  const email = prompt('Informe o e-mail da conta:', $('#loginEmail').value || '');
  if(!email) return;
  try{
    const data = await fetch(API + '/api/auth/forgot-password',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({email})
    }).then(async r => {
      const d = await r.json();
      if(!r.ok) throw new Error(apiErrorMessage(d, 'Falha na recuperação.'));
      return d;
    });
    $('#loginMessage').textContent = data.message;
    if(data.development_reset_token){
      location.href = location.pathname + '?reset_token=' + encodeURIComponent(data.development_reset_token);
    }
  }catch(e){ $('#loginMessage').textContent = e.message; }
}

async function resetPassword(ev){
  ev.preventDefault();
  const token = new URLSearchParams(location.search).get('reset_token');
  if(!token) return;
  try{
    await fetch(API + '/api/auth/reset-password',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({token:token,new_password:$('#resetPassword').value})
    }).then(async r => {
      const d = await r.json();
      if(!r.ok) throw new Error(apiErrorMessage(d, 'Falha ao redefinir.'));
      return d;
    });
    history.replaceState({},'',location.pathname);
    $('#resetMessage').textContent = 'Senha atualizada. Você já pode entrar.';
    setTimeout(() => { $('#resetView').classList.add('hidden'); $('#loginView').classList.remove('hidden'); }, 900);
  }catch(e){ $('#resetMessage').textContent = e.message; }
}

async function loadRadar(){
  const d = await api('/api/dashboard');
  $('#metrics').innerHTML = [
    ['Produtos',d.metrics.products],
    ['Oportunidades',d.metrics.opportunities],
    ['Fornecedores',d.metrics.suppliers],
    ['Margem média',d.metrics.average_margin + '%']
  ].map(x => '<div class="metric-card"><span class="muted small">'+esc(x[0])+'</span><strong>'+esc(x[1])+'</strong></div>').join('');

  $('#opportunities').innerHTML = d.opportunities.length ? d.opportunities.map(o =>
    '<div class="opportunity">' +
      '<div class="score">'+esc(o.score)+'</div>' +
      '<div><h3>'+esc(o.product)+'</h3><div class="muted small">'+esc(o.category)+' · melhor: '+esc(o.supplier)+' · '+esc(o.offers_count)+' ofertas</div>' +
      '<button class="btn secondary small" data-detail="'+o.product_id+'">Comparar</button></div>' +
      '<div class="money"><strong>'+brl(o.profit)+'</strong><span class="muted small">'+esc(o.margin)+'% margem</span></div>' +
    '</div>'
  ).join('') : '<p class="muted">Nenhuma oportunidade disponível com os fornecedores ativos.</p>';

  $$('[data-detail]').forEach(b => b.onclick = () => loadProductDetail(Number(b.dataset.detail)));
}

async function loadProductDetail(id){
  const p = await api('/api/products/' + id);
  const offers = p.offers.map((o,i) =>
    '<div class="detail-offer '+(i===0?'best':'')+'">' +
      '<div class="row"><strong>'+esc(o.supplier)+'</strong><strong>Score '+esc(o.score)+'</strong></div>' +
      '<div class="row small"><span>Custo '+brl(o.cost)+'</span><span>Estoque '+esc(o.stock)+'</span></div>' +
      '<div class="row small"><span>Lucro '+brl(o.profit)+'</span><span>'+esc(o.margin)+'%</span></div>' +
      '<div class="history">Histórico: '+o.history.map(h => new Date(h.captured_at).toLocaleDateString('pt-BR')+' '+brl(h.cost)+' / '+h.stock+' un.').join(' → ')+'</div>' +
    '</div>'
  ).join('');
  $('#productDetail').innerHTML =
    '<h3>'+esc(p.name)+'</h3><p class="muted small">Venda sugerida: '+brl(p.sale_price)+' · concorrência '+esc(p.competition_score)+'/100</p>' +
    '<p><strong>Recomendação: '+esc(p.recommendation || '—')+'</strong></p>' + offers +
    '<div class="warning-box">Taxas da demo: '+esc(p.fee_assumption.percent)+'% + '+brl(p.fee_assumption.fixed)+'. Valide tarifas reais antes da publicação.</div>';
}

async function loadProducts(){
  productsCache = await api('/api/products');
  renderProducts(productsCache);
}
function renderProducts(list){
  $('#productTable').innerHTML = list.map(p =>
    '<div class="product-row"><div class="row"><div><strong>'+esc(p.name)+'</strong><div class="muted small">'+esc(p.category)+' · '+esc(p.offers)+' ofertas</div></div>' +
    '<div><span class="pill good">Score '+esc(p.best_score)+'</span> <button class="btn secondary" data-open-product="'+p.id+'">Detalhes</button></div></div></div>'
  ).join('') || '<p class="muted">Nenhum produto.</p>';
  $$('[data-open-product]').forEach(b => b.onclick = async () => { await switchView('radar'); await loadProductDetail(Number(b.dataset.openProduct)); });
}

async function prepareAi(){
  if(!productsCache.length) productsCache = await api('/api/products');
  $('#aiProduct').innerHTML = productsCache.map(p => '<option value="'+p.id+'">'+esc(p.name)+'</option>').join('');
}
async function generateAi(){
  const id = Number($('#aiProduct').value);
  if(!id) return;
  $('#aiResult').textContent = 'Gerando...';
  try{
    const d = await api('/api/ai/listing',{method:'POST',body:JSON.stringify({product_id:id,notes:$('#aiNotes').value || null})});
    if(d.provider === 'openai') $('#aiResult').textContent = d.content;
    else $('#aiResult').textContent = 'TÍTULO:\n'+d.title+'\n\nDESCRIÇÃO:\n'+d.description+'\n\nPALAVRAS-CHAVE:\n'+d.keywords.join(', ')+'\n\nGerador: local';
  }catch(e){ $('#aiResult').textContent = e.message; }
}

async function loadSuppliers(){
  const list = await api('/api/suppliers');
  const canEdit = currentUser && ['owner','admin'].includes(currentUser.role);
  $('#supplierGrid').innerHTML = list.map(s =>
    '<div class="supplier-card"><div class="row"><h3>'+esc(s.name)+'</h3><span class="pill '+(s.enabled?'good':'warn')+'">'+(s.enabled?'ativo':'inativo')+'</span></div>' +
    '<div class="muted small">Confiabilidade: '+esc(s.reliability)+'% · modo '+esc(s.mode)+'</div>' +
    '<button class="btn secondary wide" data-toggle-supplier="'+s.id+'" data-enabled="'+String(s.enabled)+'" '+(canEdit?'':'disabled')+'>'+(s.enabled?'Desativar':'Ativar')+'</button></div>'
  ).join('');
  const importSelect = $('#supplierImportSupplier');
  if(importSelect) importSelect.innerHTML = list.map(s => '<option value="'+s.id+'">'+esc(s.name)+'</option>').join('');
  $('[data-toggle-supplier]').forEach(b => b.onclick = async () => {
    const enabled = b.dataset.enabled !== 'true';
    await api('/api/suppliers/'+b.dataset.toggleSupplier,{method:'PATCH',body:JSON.stringify({enabled})});
    toast(enabled ? 'Fornecedor ativado.' : 'Fornecedor desativado.');
    await loadSuppliers();
  });
}

async function importSupplierFile(ev){
  ev.preventDefault();
  const supplierId = Number($('#supplierImportSupplier').value);
  const file = $('#supplierImportFile').files[0];
  const result = $('#supplierImportResult');
  if(!supplierId || !file) return;
  result.textContent = 'Importando...';
  const form = new FormData();
  form.append('file', file);
  try{
    const data = await apiUpload('/api/imports/supplier/'+supplierId, form);
    result.textContent = data.imported_rows+' linhas importadas · '+data.created_products+' produtos novos · '+data.updated_offers+' ofertas atualizadas' + (data.rejected_rows ? ' · '+data.rejected_rows+' rejeitadas' : '');
    toast('Catálogo importado com sucesso.');
    productsCache = [];
    await loadSuppliers();
  }catch(e){
    result.textContent = e.message;
  }
}

async function downloadSupplierTemplate(){
  try{
    const r = await fetch(API + '/api/imports/supplier-template.csv',{headers:{Authorization:'Bearer '+accessToken()}});
    if(!r.ok){
      let data=null; try{data=await r.json()}catch(_){}
      throw new Error(apiErrorMessage(data,'Falha ao baixar o modelo.'));
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'dropjoy-modelo-fornecedor.csv';
    a.click();
    URL.revokeObjectURL(url);
  }catch(e){ toast(e.message); }
}

function marketplaceAccountActions(a){
  if(a.provider !== 'mercadolivre') return '';
  if(!a.app_configured){
    return '<div class="warning-box">Configure a aplicação Mercado Livre no backend para habilitar o OAuth.</div>';
  }
  if(!a.oauth_connected){
    return '<button class="btn primary wide" data-connect-meli="'+a.id+'">Conectar Mercado Livre</button>';
  }
  const expiry = a.token_expires_at ? new Date(a.token_expires_at).toLocaleString('pt-BR') : '—';
  return '<div class="muted small">OAuth conectado · token expira: '+esc(expiry)+'</div>' +
    '<div class="row" style="margin-top:8px"><button class="btn secondary" data-refresh-meli="'+a.id+'">Renovar token</button>' +
    '<button class="btn secondary" data-disconnect-meli="'+a.id+'">Desconectar</button></div>';
}

async function loadMarketplaces(){
  if(!productsCache.length) productsCache = await api('/api/products');
  marketplaceCache = await api('/api/marketplaces');
  $('#marketplaceAccounts').innerHTML = marketplaceCache.accounts.map(a =>
    '<div class="account-card"><div class="row"><strong>'+esc(a.display_name)+'</strong><span class="pill '+(a.connector_configured?'good':'warn')+'">'+esc(a.status)+'</span></div>' +
    '<div class="muted small">'+esc(a.provider)+' · '+esc(a.external_account_id)+'</div>' +
    marketplaceAccountActions(a) + '</div>'
  ).join('') || '<p class="muted small">Nenhuma conta cadastrada.</p>';

  $('#listingAccount').innerHTML = marketplaceCache.accounts.map(a => '<option value="'+a.id+'">'+esc(a.display_name)+' ('+esc(a.provider)+')</option>').join('');
  $('#listingProduct').innerHTML = productsCache.map(p => '<option value="'+p.id+'">'+esc(p.name)+'</option>').join('');
  updateListingForm();
  $('#marketplaceListings').innerHTML = marketplaceCache.listings.map(l =>
    '<div class="listing-card"><div class="row"><strong>Listagem #'+l.id+'</strong><span class="pill '+(['published','active'].includes(l.status)?'good':'warn')+'">'+esc(l.status)+'</span></div>' +
    '<div class="muted small">Produto #'+l.product_id+' · '+brl(l.price)+(l.category_id?' · '+esc(l.category_id):'')+'</div>' +
    (l.status==='draft' ? '<button class="btn secondary" data-publish="'+l.id+'">Publicar</button>' : '<div class="muted small">ID externo: '+esc(l.external_listing_id || '—')+'</div>') +
    (l.user_product_id ? '<div class="muted small">User Product: '+esc(l.user_product_id)+'</div>' : '') +
    (l.publication_error ? '<div class="warning-box">'+esc(l.publication_error)+'</div>' : '') +
    '</div>'
  ).join('') || '<p class="muted small">Nenhuma listagem.</p>';

  $('[data-publish]').forEach(b => b.onclick = async () => {
    try{ await api('/api/marketplaces/listings/'+b.dataset.publish+'/publish',{method:'POST'}); toast('Listagem publicada.'); await loadMarketplaces(); }
    catch(e){ toast(e.message); }
  });
  $('[data-connect-meli]').forEach(b => b.onclick = () => connectMercadoLivre(Number(b.dataset.connectMeli)));
  $('[data-refresh-meli]').forEach(b => b.onclick = () => refreshMercadoLivre(Number(b.dataset.refreshMeli)));
  $('[data-disconnect-meli]').forEach(b => b.onclick = () => disconnectMercadoLivre(Number(b.dataset.disconnectMeli)));
}

function updateMarketplaceForm(){
  const isMeli = $('#marketplaceProvider').value === 'mercadolivre';
  const input = $('#marketplaceExternalId');
  input.required = !isMeli;
  input.disabled = isMeli;
  input.placeholder = isMeli ? 'Preenchido automaticamente após o OAuth' : 'ID da conta/loja';
  if(isMeli) input.value = '';
}

function selectedMarketplaceAccount(){
  const id = Number($('#listingAccount').value);
  return marketplaceCache.accounts.find(a => a.id === id);
}

function updateListingForm(){
  const account = selectedMarketplaceAccount();
  const isMeli = account && account.provider === 'mercadolivre';
  $('#listingMeliFields').classList.toggle('hidden', !isMeli);
  $('#listingStock').disabled = false;
  $('#listingStockLocationsLabel').classList.add('hidden');
  ['listingCategory','listingFamilyName','listingCondition','listingType','listingStock','listingPictures','listingAttributes'].forEach(id => {
    $('#'+id).required = Boolean(isMeli);
  });
  if(isMeli && !$('#listingFamilyName').value){
    const product = productsCache.find(p => p.id === Number($('#listingProduct').value));
    if(product) $('#listingFamilyName').value = product.name;
  }
}

async function predictMeliCategory(){
  const account = selectedMarketplaceAccount();
  const product = productsCache.find(p => p.id === Number($('#listingProduct').value));
  if(!account || !product) return;
  try{
    const data = await api('/api/marketplaces/mercadolivre/accounts/'+account.id+'/categories/predict?q='+encodeURIComponent(product.name));
    if(!data.results.length) throw new Error('Nenhuma categoria sugerida pelo Mercado Livre.');
    const best = data.results[0];
    $('#listingCategory').value = best.category_id;
    $('#listingRequirements').textContent = 'Sugestão: '+best.category_name+' ('+best.category_id+'). Carregando regras...';
    await loadMeliCategoryRequirements();
  }catch(e){ toast(e.message); }
}

async function loadMeliCategoryRequirements(){
  const account = selectedMarketplaceAccount();
  const categoryId = $('#listingCategory').value.trim();
  if(!account || !categoryId) return toast('Informe uma categoria MLB.');
  try{
    const data = await api('/api/marketplaces/mercadolivre/accounts/'+account.id+'/categories/'+encodeURIComponent(categoryId));
    const selectedCondition = $('#listingCondition').value;
    const required = data.attributes.filter(a =>
      a.tags && (a.tags.required || (selectedCondition === 'new' && a.tags.new_required))
    );
    $('#listingRequirements').innerHTML = '<strong>'+esc(data.category.name)+'</strong><br>Atributos obrigatórios: '+(required.map(a => esc(a.id)+' — '+esc(a.name)).join(', ') || 'nenhum marcado') + '<br>Condições: '+esc((data.category.settings.item_conditions || []).join(', '));
    if(!data.user_product_seller){
      $('#listingRequirements').innerHTML += '<br><strong>Atenção:</strong> esta conta ainda não possui a tag user_product_seller.';
    }
    $('#listingType').innerHTML = data.listing_types.map(t => '<option value="'+esc(t.id)+'">'+esc(t.name)+' ('+esc(t.id)+')</option>').join('');
    $('#listingStockLocationsLabel').classList.toggle('hidden', !data.warehouse_management);
    $('#listingStock').disabled = Boolean(data.warehouse_management);
    if(data.warehouse_management){
      const locations = data.stock_locations.map(location => ({
        store_id:String(location.id || location.store_id || ''),
        network_node_id:String(location.network_node_id || ''),
        quantity:0
      }));
      $('#listingStockLocations').value = JSON.stringify(locations,null,2);
      $('#listingRequirements').innerHTML += '<br><strong>Estoque multi-origem:</strong> preencha a quantidade nos depósitos listados.';
    }else{
      $('#listingStockLocations').value = '';
    }
    const current = (() => { try{return JSON.parse($('#listingAttributes').value || '[]')}catch(_){return []} })();
    const currentIds = new Set(current.map(a => a.id));
    required.forEach(a => { if(!currentIds.has(a.id)) current.push({id:a.id,value_name:''}); });

    // Para novas integrações o Mercado Livre recomenda ITEM_CONDITION em attributes.
    if(!currentIds.has('ITEM_CONDITION')){
      const conditionAttr = data.attributes.find(a => a.id === 'ITEM_CONDITION');
      const targets = {
        new:['novo','new','nuevo'],
        used:['usado','used'],
        not_specified:['nao especificado','not specified','no especificado']
      }[selectedCondition] || [];
      const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().trim();
      const match = conditionAttr && (conditionAttr.values || []).find(v => targets.includes(normalize(v.name)));
      if(match && match.id) current.push({id:'ITEM_CONDITION',value_id:String(match.id)});
    }
    $('#listingAttributes').value = JSON.stringify(current,null,2);
  }catch(e){ toast(e.message); }
}

async function connectMercadoLivre(accountId){
  try{
    const data = await api('/api/marketplaces/mercadolivre/accounts/'+accountId+'/connect',{method:'POST'});
    if(!data.authorization_url) throw new Error('URL de autorização não retornada.');
    location.href = data.authorization_url;
  }catch(e){ toast(e.message); }
}

async function refreshMercadoLivre(accountId){
  try{
    await api('/api/marketplaces/mercadolivre/accounts/'+accountId+'/refresh',{method:'POST'});
    toast('Token do Mercado Livre renovado.');
    await loadMarketplaces();
  }catch(e){ toast(e.message); }
}

async function disconnectMercadoLivre(accountId){
  if(!confirm('Desconectar esta conta do Mercado Livre?')) return;
  try{
    await api('/api/marketplaces/mercadolivre/accounts/'+accountId+'/disconnect',{method:'POST'});
    toast('Mercado Livre desconectado.');
    await loadMarketplaces();
  }catch(e){ toast(e.message); }
}

async function createMarketplaceAccount(ev){
  ev.preventDefault();
  try{
    const provider = $('#marketplaceProvider').value;
    await api('/api/marketplaces/accounts',{method:'POST',body:JSON.stringify({
      provider:provider,
      external_account_id:provider === 'mercadolivre' ? null : $('#marketplaceExternalId').value,
      display_name:$('#marketplaceName').value
    })});
    ev.target.reset();
    updateMarketplaceForm();
    toast('Conta adicionada.');
    await loadMarketplaces();
  }catch(e){ toast(e.message); }
}

async function createListing(ev){
  ev.preventDefault();
  try{
    const account = selectedMarketplaceAccount();
    const payload = {
      account_id:Number($('#listingAccount').value),
      product_id:Number($('#listingProduct').value),
      price:Number($('#listingPrice').value)
    };
    if(account && account.provider === 'mercadolivre'){
      let attributes;
      try{ attributes = JSON.parse($('#listingAttributes').value); }
      catch(_){ throw new Error('O JSON de atributos é inválido.'); }
      let stockLocations = [];
      if($('#listingStockLocations').value.trim()){
        try{ stockLocations = JSON.parse($('#listingStockLocations').value); }
        catch(_){ throw new Error('O JSON de estoque por depósito é inválido.'); }
      }
      payload.category_id = $('#listingCategory').value.trim();
      payload.family_name = $('#listingFamilyName').value.trim();
      payload.condition = $('#listingCondition').value;
      payload.currency_id = 'BRL';
      payload.listing_type_id = $('#listingType').value;
      payload.available_quantity = Number($('#listingStock').value);
      payload.pictures = $('#listingPictures').value.split(/\r?\n/).map(x => x.trim()).filter(Boolean);
      payload.attributes = attributes;
      payload.stock_locations = stockLocations;
    }
    await api('/api/marketplaces/listings',{method:'POST',body:JSON.stringify(payload)});
    toast('Rascunho criado.'); await loadMarketplaces();
  }catch(e){ toast(e.message); }
}

async function loadFinance(){
  const d = await api('/api/dashboard');
  $('#financeCards').innerHTML = [
    ['Margem média',d.metrics.average_margin+'%'],
    ['Oportunidades',d.metrics.opportunities],
    ['Produtos ativos',d.metrics.products],
    ['Estoque baixo',d.metrics.low_stock]
  ].map(x => '<div class="metric-card"><span class="muted small">'+esc(x[0])+'</span><strong>'+esc(x[1])+'</strong></div>').join('');
}

async function loadUsers(){
  if(!currentUser || !['owner','admin'].includes(currentUser.role)) return;
  const users = await api('/api/users');
  $('#userList').innerHTML = users.map(u =>
    '<div class="user-row"><div class="row"><div><strong>'+esc(u.name)+'</strong><div class="muted small">'+esc(u.email)+'</div></div><div><span class="pill">'+esc(u.role)+'</span> <span class="pill '+(u.active?'good':'danger')+'">'+(u.active?'ativo':'inativo')+'</span></div></div></div>'
  ).join('');
}
async function createUser(ev){
  ev.preventDefault();
  try{
    await api('/api/users',{method:'POST',body:JSON.stringify({
      name:$('#newUserName').value,
      email:$('#newUserEmail').value,
      password:$('#newUserPassword').value,
      role:$('#newUserRole').value
    })});
    ev.target.reset(); toast('Usuário criado.'); await loadUsers();
  }catch(e){ toast(e.message); }
}

async function loadAudit(){
  if(!currentUser || !['owner','admin'].includes(currentUser.role)) return;
  const rows = await api('/api/audit?limit=100');
  $('#auditList').innerHTML = rows.map(r =>
    '<div class="audit-row"><div class="row"><strong>'+esc(r.action)+'</strong><span class="muted small">'+new Date(r.created_at).toLocaleString('pt-BR')+'</span></div><div class="muted small">Usuário #'+esc(r.user_id || '—')+' · '+esc(r.entity_type || '—')+' '+esc(r.entity_id || '')+'</div></div>'
  ).join('') || '<p class="muted">Nenhum evento.</p>';
}

async function syncDemo(){
  try{
    const r = await api('/api/integrations/demo/sync',{method:'POST'});
    toast(r.offers_updated + ' ofertas atualizadas.');
    await loadRadar();
  }catch(e){ toast(e.message); }
}

async function boot(){
  $('#apiStatus').textContent = 'API conectando';
  const params = new URLSearchParams(location.search);
  const reset = params.get('reset_token');
  if(reset){
    $('#loginView').classList.add('hidden');
    $('#resetView').classList.remove('hidden');
    return;
  }
  if(!accessToken() && refreshToken()) await refreshSession();
  if(!accessToken()){ showAuth(); return; }
  try{
    const me = await api('/api/auth/me');
    showApp(me);
    $('#apiStatus').textContent = 'API online';
    const returnedFromMeli = params.get('marketplace') === 'mercadolivre';
    await switchView(returnedFromMeli ? 'marketplaces' : 'radar');
    if(returnedFromMeli){
      if(params.get('connected') === '1') toast('Mercado Livre conectado com sucesso.');
      if(params.get('oauth_error')) toast('Falha ao conectar Mercado Livre: '+params.get('oauth_error'));
      history.replaceState({},'',location.pathname);
    }
  }catch(e){
    clearSession(); showAuth(); $('#loginMessage').textContent = e.message;
  }
}

$('#loginForm').addEventListener('submit',login);
$('#forgotBtn').addEventListener('click',forgotPassword);
$('#resetForm').addEventListener('submit',resetPassword);
$('#logoutBtn').addEventListener('click',logout);
$('#syncDemoBtn').addEventListener('click',syncDemo);
$('#generateAiBtn').addEventListener('click',generateAi);
$('#marketplaceAccountForm').addEventListener('submit',createMarketplaceAccount);
$('#marketplaceProvider').addEventListener('change',updateMarketplaceForm);
$('#listingForm').addEventListener('submit',createListing);
$('#listingAccount').addEventListener('change',updateListingForm);
$('#listingProduct').addEventListener('change',updateListingForm);
$('#meliPredictCategory').addEventListener('click',predictMeliCategory);
$('#meliLoadCategory').addEventListener('click',loadMeliCategoryRequirements);
$('#userForm').addEventListener('submit',createUser);
$('#supplierImportForm').addEventListener('submit',importSupplierFile);
$('#supplierTemplateBtn').addEventListener('click',downloadSupplierTemplate);
$('#productSearch').addEventListener('input',() => {
  const q = $('#productSearch').value.toLowerCase().trim();
  renderProducts(productsCache.filter(p => p.name.toLowerCase().includes(q) || p.category.toLowerCase().includes(q)));
});
$$('.nav-item').forEach(b => b.addEventListener('click',() => switchView(b.dataset.view)));

updateMarketplaceForm();
boot();

