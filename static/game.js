// Échappe les caractères HTML pour éviter les injections XSS lors de l'insertion via innerHTML
function esc(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

let ws, myPid, gs;

const PROPS = {
  1:{n:"Méditerranée",c:"brown",p:60},  3:{n:"Baltic",c:"brown",p:60},
  6:{n:"Oriental",c:"cyan",p:100},      8:{n:"Vermont",c:"cyan",p:100},   9:{n:"Connecticut",c:"cyan",p:120},
  11:{n:"St-Charles",c:"pink",p:140},   13:{n:"États",c:"pink",p:140},    14:{n:"Virginia",c:"pink",p:160},
  16:{n:"St-James",c:"orange",p:180},   18:{n:"Tennessee",c:"orange",p:180}, 19:{n:"New York",c:"orange",p:200},
  21:{n:"Kentucky",c:"red",p:220},      23:{n:"Indiana",c:"red",p:220},   24:{n:"Illinois",c:"red",p:240},
  26:{n:"Atlantic",c:"yellow",p:260},   27:{n:"Ventnor",c:"yellow",p:260}, 29:{n:"Marvin",c:"yellow",p:280},
  31:{n:"Pacific",c:"green",p:300},     32:{n:"Caroline N.",c:"green",p:300}, 34:{n:"Pennsylvanie",c:"green",p:320},
  37:{n:"Park",c:"darkblue",p:350},     39:{n:"Boulevard",c:"darkblue",p:400},
  5:{n:"Gare 1",c:"station",p:200},    15:{n:"Gare 2",c:"station",p:200},
  25:{n:"Gare 3",c:"station",p:200},   35:{n:"Gare 4",c:"station",p:200},
  12:{n:"Cie Électrique",c:"utility",p:150}, 28:{n:"Cie des Eaux",c:"utility",p:150},
};
const SPEC = {0:"DÉPART",2:"Caisse",4:"Taxes",7:"Chance",8:"Vermont",10:"Prison",
              12:"Cie Électrique",13:"États",17:"Caisse",18:"Tennessee",20:"Parc",
              22:"Chance",23:"Indiana",27:"Ventnor",28:"Cie des Eaux",
              30:"→Prison",32:"Caroline N.",33:"Caisse",36:"Chance",38:"Luxe"};

// Grid positions: (col, row) 1-indexed
const POS = {};
for(let i=0;i<=10;i++)  POS[i]=[i+1, 1];
for(let i=11;i<=20;i++) POS[i]=[11, i-10+1];
for(let i=21;i<=30;i++) POS[i]=[11-(i-20), 11];
for(let i=31;i<=39;i++) POS[i]=[1, 11-(i-30)];

// Génère la grille 11x11 du plateau avec les cases, barres de couleur et libellés
function buildBoard() {
  const b = document.getElementById('board');
  b.innerHTML = '';
  const cells = {};
  for(let r=1;r<=11;r++) for(let c=1;c<=11;c++){
    const d = document.createElement('div');
    d.style.gridColumn = c; d.style.gridRow = r;
    b.appendChild(d); cells[`${c},${r}`] = d;
  }
  // Center
  const cc = cells['2,2'];
  cc.className = 'center-cell';
  cc.style.gridColumn = '2/11'; cc.style.gridRow = '2/11';
  cc.textContent = 'MONOPOLY';
  for(let r=2;r<=10;r++) for(let c=2;c<=10;c++)
    if(!(c===2&&r===2)) cells[`${c},${r}`]?.remove();

  for(let i=0;i<=39;i++){
    const [c,r] = POS[i]; const sq = cells[`${c},${r}`];
    if(!sq) continue;
    sq.className = 'sq' + ([0,10,20,30].includes(i)?' corner':'');
    sq.dataset.i = i;
    let bar='', label='';
    if(PROPS[i]){ bar=`<div class="color-bar ${PROPS[i].c}"></div>`; label=PROPS[i].n; }
    else { label = SPEC[i]||`#${i}`; }
    sq.innerHTML = bar + `<div class="sq-label">${label}</div><div class="pions" id="p${i}"></div>`;
  }
}

// Applique l'état reçu du serveur à l'interface : joueurs, boutons, pions, propriétés, maisons, hypothèques
function render(s){
  gs = s;
  const isMyTurn = s.turn === myPid;
  // Players
  const pc = document.getElementById('players');
  pc.innerHTML = s.players.map(p =>
    `<div class="pcard${p.id===s.turn?' active-turn':''}${p.bankrupt?' bankrupt':''}">
      ${p.icon} ${esc(p.name)}${p.id===myPid?' (vous)':''}
      <span class="pmoney"> — ${p.money}$</span>
      <span style="color:#888;font-size:.75rem"> case ${p.pos}${p.in_jail?' 🚔 prison ('+p.jail_turns+'/3)':''}${p.goojf?'  🎫×'+p.goojf:''}${p.bankrupt?' 💀 en faillite':''}</span>
    </div>`
  ).join('');
  // Écran de victoire
  if (s.game_over && s.winner) {
    const winner = s.players.find(p => p.id === s.winner);
    document.getElementById('win-msg').textContent = `${winner?.icon} ${winner?.name} remporte la partie!`;
    document.getElementById('win-overlay').classList.add('open');
  }
  // Buttons
  const canBuy = s.pending_buy === myPid;
  const hasTax = s.pending_tax === myPid;
  const me = s.players.find(p => p.id === myPid);
  const myPos = me?.pos;
  const propPrice = canBuy && myPos != null ? (PROPS[myPos]?.price ?? 0) : 0;
  const canAfford = me && me.money >= propPrice;
  const amInJail   = me?.in_jail && isMyTurn;
  const hasGoojf   = (me?.goojf ?? 0) > 0;
  const extraRoll  = s.extra_roll === myPid;
  document.getElementById('btn-start').disabled   = s.started || s.players.length < 2;
  document.getElementById('btn-roll').disabled    = !s.started || (!isMyTurn && !extraRoll) || canBuy || hasTax;
  document.getElementById('btn-buy').disabled     = !canBuy || !canAfford;
  document.getElementById('btn-skip').disabled    = !canBuy;
  const jailSection = document.getElementById('jail-section');
  jailSection.style.display = amInJail ? 'flex' : 'none';
  document.getElementById('btn-goojf').disabled   = !hasGoojf;
  document.getElementById('btn-payjail').disabled = (me?.money < 50);
  const hasOtherPlayers = s.players.filter(p=>p.id!==myPid&&!p.bankrupt).length > 0;
  document.getElementById('btn-trade').disabled = !s.started || !hasOtherPlayers || (!!me?.in_jail && !isMyTurn);
  const myOwned = Object.entries(s.owned||{}).filter(([,o])=>o===myPid).map(([k])=>parseInt(k));
  const hasMonopoly = Object.keys(GROUP_MEMBERS).some(grp=>GROUP_MEMBERS[grp].every(p=>s.owned[p]===myPid));
  document.getElementById('btn-build').disabled = !s.started || !hasMonopoly;
  // Popup taxe sur le revenu : calcule les avoirs et affiche le modal si c'est notre tour
  if(hasTax && me) {
    let wealth = me.money;
    Object.entries(s.owned||{}).forEach(([k, owner]) => {
      if(owner === myPid) {
        const price = PROPS[parseInt(k)]?.p || 0;
        wealth += (s.mortgaged && s.mortgaged[k]) ? Math.floor(price/2) : price;
      }
    });
    Object.entries(s.houses||{}).forEach(([k, n]) => {
      const grp = COLOR_GROUPS[parseInt(k)];
      if(grp && (s.owned||{})[k] === myPid) wealth += n * (HOUSE_PRICE[grp]||0);
    });
    const pct = Math.max(1, Math.floor(wealth / 10));
    document.getElementById('tax-info').textContent = `Avoirs estimés : ${wealth}$ — choisissez votre mode de paiement`;
    document.getElementById('tax-pct-amount').textContent = pct + '$';
    document.getElementById('tax-overlay').classList.add('open');
  } else {
    document.getElementById('tax-overlay').classList.remove('open');
  }
  renderIncomingTrade(s.pending_trade, s.players);
  renderAuction(s.pending_auction, s.players);
  // Pions
  document.querySelectorAll('.pions').forEach(e=>e.textContent='');
  s.players.forEach(p=>{ const el=document.getElementById(`p${p.pos}`); if(el) el.textContent+=p.icon; });
  // Owned
  document.querySelectorAll('.sq').forEach(e=>e.classList.remove('owned'));
  Object.keys(s.owned).forEach(k=>{ const sq=document.querySelector(`[data-i="${k}"]`); if(sq) sq.classList.add('owned'); });
  // Houses
  document.querySelectorAll('.houses-display').forEach(e=>e.remove());
  Object.entries(s.houses||{}).forEach(([k,n])=>{
    const sq=document.querySelector(`[data-i="${k}"]`); if(!sq) return;
    const el=document.createElement('div'); el.className='houses-display';
    el.textContent = n===5 ? '🏨' : '🏠'.repeat(n);
    sq.appendChild(el);
  });
  // Mortgaged indicator
  document.querySelectorAll('.sq').forEach(e=>e.classList.remove('mortgaged-sq'));
  document.querySelectorAll('.mortgage-badge').forEach(e=>e.remove());
  Object.entries(s.mortgaged||{}).forEach(([k,v])=>{
    if(!v) return;
    const sq=document.querySelector(`[data-i="${k}"]`); if(!sq) return;
    sq.classList.add('mortgaged-sq');
    const badge=document.createElement('div'); badge.className='mortgage-badge'; badge.textContent='🏦';
    sq.appendChild(badge);
  });
}

// Ajoute un message au journal de jeu et fait défiler vers le bas automatiquement
function log(msg){
  const l=document.getElementById('log');
  const div=document.createElement('div');
  div.textContent=msg;
  l.appendChild(div);
  l.scrollTop=l.scrollHeight;
}

// Envoie une commande simple sans paramètres via WebSocket
function send(cmd){ ws?.send(JSON.stringify({cmd})); }

// Lit le champ de saisie et envoie le message de chat au serveur
function chat(){ const i=document.getElementById('chat-in'); if(!i.value.trim()) return; ws?.send(JSON.stringify({cmd:'chat',text:i.value})); i.value=''; }

const PROP_NAMES = {};
Object.entries(PROPS).forEach(([k,v])=> PROP_NAMES[k]=v.n);

const COLOR_GROUPS = {
  1:"brown",3:"brown",
  6:"cyan",8:"cyan",9:"cyan",
  11:"pink",13:"pink",14:"pink",
  16:"orange",18:"orange",19:"orange",
  21:"red",23:"red",24:"red",
  26:"yellow",27:"yellow",29:"yellow",
  31:"green",32:"green",34:"green",
  37:"dblue",39:"dblue"
};
const GROUP_MEMBERS = {};
for(const [pos,grp] of Object.entries(COLOR_GROUPS)){
  if(!GROUP_MEMBERS[grp]) GROUP_MEMBERS[grp]=[];
  GROUP_MEMBERS[grp].push(parseInt(pos));
}
const HOUSE_PRICE = {brown:50,cyan:50,pink:100,orange:100,red:150,yellow:150,green:200,dblue:200};
const GROUP_LABEL = {brown:"Marron",cyan:"Bleu clair",pink:"Rose",orange:"Orange",red:"Rouge",yellow:"Jaune",green:"Vert",dblue:"Bleu foncé"};

// Retourne l'icône représentant les maisons ou l'hôtel pour une case donnée
function houseLabel(n){ return n===5?"🏨 Hôtel":"🏠".repeat(n)||"—"; }

// Ouvre le modal de construction et liste les monopoles possédés avec leurs maisons actuelles
function openBuild(){
  if(!gs) return;
  const myOwned = Object.entries(gs.owned).filter(([,o])=>o===myPid).map(([k])=>parseInt(k));
  const myGroups = [...new Set(myOwned.map(p=>COLOR_GROUPS[p]).filter(Boolean))]
    .filter(grp => GROUP_MEMBERS[grp].every(p => gs.owned[p]===myPid));

  const container = document.getElementById('build-groups');
  if(!myGroups.length){
    container.innerHTML = '<p style="color:#888;font-size:.85rem">Vous ne possédez aucun monopole complet.</p>';
  } else {
    container.innerHTML = myGroups.map(grp => {
      const price = HOUSE_PRICE[grp];
      const rows = GROUP_MEMBERS[grp].map(pos => {
        const n = parseInt(gs.houses[pos]||0);
        return `<div class="build-row">
          <span class="prop-name">${PROP_NAMES[pos]}</span>
          <span class="house-count">${houseLabel(n)}</span>
          <div class="build-btns">
            <button class="sell" onclick="ws?.send(JSON.stringify({cmd:'sell_house',pos:${pos}}));setTimeout(refreshBuild,200)">-</button>
            <button class="buy"  onclick="ws?.send(JSON.stringify({cmd:'build_house',pos:${pos}}));setTimeout(refreshBuild,200)">+ ${price}$</button>
          </div>
        </div>`;
      }).join('');
      return `<div class="build-group"><h3>${GROUP_LABEL[grp]}</h3>${rows}</div>`;
    }).join('');
  }
  document.getElementById('build-overlay').classList.add('open');
}

// Recharge le contenu du modal de construction depuis l'état courant
function refreshBuild(){ if(gs) openBuild(); }

// Ferme le modal de construction
function closeBuild(){ document.getElementById('build-overlay').classList.remove('open'); }

// Ouvre le modal d'inventaire : propriétés groupées par couleur avec statut hypothèque et boutons d'action
function openInventory(){
  if(!gs) return;
  const myOwned = Object.entries(gs.owned).filter(([,o])=>o===myPid).map(([k])=>parseInt(k));
  const goojfCount = gs.players.find(p=>p.id===myPid)?.goojf||0;
  const SWATCH = {brown:'#955436',cyan:'#00aeef',pink:'#d93a96',orange:'#f7941d',red:'#ed1b24',yellow:'#fef200',green:'#1fb25a',dblue:'#0050a0'};
  let html = '';
  if(goojfCount > 0) html += `<p style="margin-bottom:10px">🎫 Cartes Sortie de Prison : <strong>${goojfCount}</strong></p>`;
  if(myOwned.length === 0 && goojfCount === 0){
    html = '<em style="color:#aaa">Vous ne possédez aucune propriété.</em>';
  } else {
    Object.entries(GROUP_MEMBERS).forEach(([grp, members])=>{
      const mine = members.filter(p=>myOwned.includes(p));
      if(!mine.length) return;
      const monopole = members.every(p=>myOwned.includes(p));
      const swatch = SWATCH[grp]||'#888';
      html += `<div class="inv-group">`;
      html += `<h3><span class="inv-swatch" style="background:${swatch}"></span>${GROUP_LABEL[grp]||grp}${monopole?' ✅':''}</h3>`;
      const groupHasHouses = GROUP_MEMBERS[grp].some(p=>(gs.houses[p]||0)>0);
      html += `<div class="inv-row header"><span>Terrain</span><span>Maisons</span><span>Action</span></div>`;
      mine.forEach(p=>{
        const h = gs.houses[p]||0;
        const name = PROPS[p]?.n||('#'+p);
        const isMort = !!(gs.mortgaged && gs.mortgaged[p]);
        const mortValue = Math.floor((PROPS[p]?.p||0)/2);
        const unmortCost = Math.ceil((PROPS[p]?.p||0)*0.55);
        let action;
        if(isMort){
          action = `<button style="font-size:.7rem;padding:2px 6px;cursor:pointer" onclick="ws?.send(JSON.stringify({cmd:'unmortgage',pos:${p}}));setTimeout(openInventory,200)">Lever (${unmortCost}$)</button>`;
        } else if(!groupHasHouses){
          action = `<button style="font-size:.7rem;padding:2px 6px;cursor:pointer" onclick="ws?.send(JSON.stringify({cmd:'mortgage',pos:${p}}));setTimeout(openInventory,200)">Hypothéquer (+${mortValue}$)</button>`;
        } else {
          action = `<span style="color:#aaa;font-size:.7rem">Vendez maisons</span>`;
        }
        html += `<div class="inv-row"${isMort?' style="opacity:.6;text-decoration:line-through"':''}><span>${name}${isMort?' 🏦':''}</span><span>${houseLabel(h)}</span><span>${action}</span></div>`;
      });
      html += `</div>`;
    });
    const allGroupProps = Object.values(GROUP_MEMBERS).flat();
    const special = myOwned.filter(p=>!allGroupProps.includes(p));
    if(special.length){
      html += `<div class="inv-group"><h3>Gares & Services publics</h3>`;
      html += `<div class="inv-row header"><span>Terrain</span><span></span><span>Action</span></div>`;
      special.forEach(p=>{
        const name = PROPS[p]?.n||('#'+p);
        const isMort2 = !!(gs.mortgaged && gs.mortgaged[p]);
        const mortValue2 = Math.floor((PROPS[p]?.p||0)/2);
        const unmortCost2 = Math.ceil((PROPS[p]?.p||0)*0.55);
        let action2;
        if(isMort2){
          action2 = `<button style="font-size:.7rem;padding:2px 6px;cursor:pointer" onclick="ws?.send(JSON.stringify({cmd:'unmortgage',pos:${p}}));setTimeout(openInventory,200)">Lever (${unmortCost2}$)</button>`;
        } else {
          action2 = `<button style="font-size:.7rem;padding:2px 6px;cursor:pointer" onclick="ws?.send(JSON.stringify({cmd:'mortgage',pos:${p}}));setTimeout(openInventory,200)">Hypothéquer (+${mortValue2}$)</button>`;
        }
        html += `<div class="inv-row"${isMort2?' style="opacity:.6"':''}><span>${name}${isMort2?' 🏦':''}</span><span></span><span>${action2}</span></div>`;
      });
      html += `</div>`;
    }
  }
  document.getElementById('inventory-content').innerHTML = html;
  document.getElementById('inventory-overlay').classList.add('open');
}

let auctionInterval = null;

// Affiche le panneau d'enchère avec le timer, les mises en attente et le formulaire de mise
function renderAuction(a, players) {
  const panel = document.getElementById('auction-panel');
  if (!a) {
    panel.classList.remove('open');
    if (auctionInterval) { clearInterval(auctionInterval); auctionInterval = null; }
    return;
  }
  panel.classList.add('open');
  document.getElementById('auction-prop').textContent = a.pos_name;

  // Timer
  if (auctionInterval) clearInterval(auctionInterval);
  auctionInterval = setInterval(() => {
    const secs = Math.max(0, Math.round(a.deadline - Date.now() / 1000));
    document.getElementById('auction-timer').textContent = secs;
    if (secs === 0) { clearInterval(auctionInterval); auctionInterval = null; }
  }, 500);

  const iAmEligible = a.eligible.includes(myPid);
  const iAlreadyBid = a.submitted.includes(myPid);
  const bidRow = document.getElementById('auction-bid-row');
  const submitted = document.getElementById('auction-submitted');
  const waiting = document.getElementById('auction-waiting');

  // Who hasn't bid yet
  const pending = a.eligible.filter(p => !a.submitted.includes(p))
    .map(p => { const pl = players.find(x => x.id === p); return pl ? `${pl.icon} ${esc(pl.name)}` : p; });

  if (!iAmEligible) {
    bidRow.style.display = 'none';
    submitted.textContent = '';
    waiting.textContent = pending.length ? `En attente de : ${pending.join(', ')}` : 'Toutes les mises reçues…';
  } else if (iAlreadyBid) {
    bidRow.style.display = 'none';
    submitted.textContent = '✅ Mise soumise — en attente des autres.';
    waiting.textContent = pending.length ? `En attente de : ${pending.join(', ')}` : 'Toutes les mises reçues…';
  } else {
    bidRow.style.display = 'flex';
    submitted.textContent = '';
    waiting.textContent = pending.length > 1 ? `En attente aussi de : ${pending.filter(p=>p!==myPid).join(', ')}` : '';
  }
}

// Soumet la mise d'enchère au serveur (passer forced=0 pour sauter sans miser)
function submitBid(forced) {
  const amount = forced === 0 ? 0 : Math.max(0, parseInt(document.getElementById('auction-amount').value) || 0);
  ws?.send(JSON.stringify({ cmd: 'bid', amount }));
  document.getElementById('auction-bid-row').style.display = 'none';
  document.getElementById('auction-submitted').textContent = amount === 0 ? '✅ Vous avez passé.' : `✅ Mise de ${amount}$ soumise.`;
}

// Ouvre le modal d'échange et peuple la liste des joueurs, des propriétés offertes et demandées
function openTrade(){
  if(!gs) return;
  const sel = document.getElementById('trade-target');
  sel.innerHTML = gs.players.filter(p=>p.id!==myPid && !p.bankrupt)
    .map(p=>`<option value="${esc(p.id)}">${p.icon} ${esc(p.name)}</option>`).join('');

  // My properties
  const myProps = Object.entries(gs.owned).filter(([,owner])=>owner===myPid).map(([k])=>k);
  document.getElementById('trade-offer-props').innerHTML = myProps.length
    ? myProps.map(k=>`<label><input type="checkbox" value="${k}"> ${PROP_NAMES[k]||'#'+k}</label>`).join('')
    : '<em style="color:#aaa;font-size:.8rem">Aucune propriété</em>';

  document.getElementById('trade-offer-money').value = 0;
  document.getElementById('trade-req-money').value = 0;
  renderReqProps();
  sel.onchange = renderReqProps;
  document.getElementById('trade-overlay').classList.add('open');
}

// Met à jour la colonne "Je demande" selon le joueur cible sélectionné dans le modal d'échange
function renderReqProps(){
  const targetId = document.getElementById('trade-target').value;
  if(!targetId || !gs) return;
  const theirProps = Object.entries(gs.owned).filter(([,owner])=>owner===targetId).map(([k])=>k);
  document.getElementById('trade-req-props').innerHTML = theirProps.length
    ? theirProps.map(k=>`<label><input type="checkbox" value="${k}"> ${PROP_NAMES[k]||'#'+k}</label>`).join('')
    : '<em style="color:#aaa;font-size:.8rem">Aucune propriété</em>';
}

// Ferme le modal d'échange
function closeTrade(){ document.getElementById('trade-overlay').classList.remove('open'); }

// Collecte les données du formulaire d'échange et envoie l'offre au serveur
function submitTrade(){
  const to = document.getElementById('trade-target').value;
  const offerMoney = parseInt(document.getElementById('trade-offer-money').value)||0;
  const reqMoney   = parseInt(document.getElementById('trade-req-money').value)||0;
  const offerProps = [...document.querySelectorAll('#trade-offer-props input:checked')].map(i=>parseInt(i.value));
  const reqProps   = [...document.querySelectorAll('#trade-req-props input:checked')].map(i=>parseInt(i.value));
  const offerGoojf = document.getElementById('trade-offer-goojf').checked ? 1 : 0;
  const reqGoojf   = document.getElementById('trade-req-goojf').checked ? 1 : 0;
  ws?.send(JSON.stringify({cmd:'trade_offer', to, offer_money:offerMoney, offer_props:offerProps, offer_goojf:offerGoojf, req_money:reqMoney, req_props:reqProps, req_goojf:reqGoojf}));
  closeTrade();
}

// Affiche la bannière d'échange entrant si le joueur courant est le destinataire de l'offre
function renderIncomingTrade(trade, players){
  const el = document.getElementById('trade-incoming');
  if(!trade || trade.to !== myPid){ el.classList.remove('open'); return; }
  const from = players.find(p=>p.id===trade.from);
  const propName = k => PROP_NAMES[k]||'#'+k;
  let html = `<strong>${from?.icon} ${esc(from?.name ?? '')}</strong> vous propose :<br>`;
  if(trade.offer_money) html += `💵 Offre ${trade.offer_money}$<br>`;
  if(trade.offer_props.length) html += `🏠 Offre : ${trade.offer_props.map(propName).join(', ')}<br>`;
  if(trade.offer_goojf) html += `🎫 Offre une Carte Sortie de Prison<br>`;
  if(trade.req_money) html += `💵 Demande ${trade.req_money}$<br>`;
  if(trade.req_props.length) html += `🏠 Demande : ${trade.req_props.map(propName).join(', ')}<br>`;
  if(trade.req_goojf) html += `🎫 Demande une Carte Sortie de Prison<br>`;
  document.getElementById('ti-details').innerHTML = html;
  el.classList.add('open');
}

// Connecte le joueur au serveur WebSocket et s'abonne aux événements de la partie
function join(){
  const name=document.getElementById('inp-name').value.trim();
  const room=document.getElementById('inp-room').value.trim();
  if(!name||!room){ alert('Remplissez les deux champs.'); return; }
  ws = new WebSocket(`ws://${location.host}/ws/${encodeURIComponent(room)}/${encodeURIComponent(name)}`);
  ws.onmessage = e => {
    const m = JSON.parse(e.data);
    if(m.event==='joined'){
      myPid=m.pid;
      document.getElementById('join').style.display='none';
      document.getElementById('game').classList.add('active');
      buildBoard();
    } else if(m.event==='state'){ render(m); }
    else if(m.event==='chat'){ log(m.msg); }
  };
  ws.onclose=()=>log('🔌 Déconnecté.');
}
