'use strict';
const $=id=>document.getElementById(id);
const LABEL={POTENSI_NAIK:'Potensi naik',SUDAH_NAIK:'Sudah naik',POTENSI_TURUN:'Potensi turun',SUDAH_TURUN:'Sudah turun',NETRAL:'Netral'};
const keys=['POTENSI_NAIK','SUDAH_NAIK','POTENSI_TURUN','SUDAH_TURUN'];
const nm=(v,d=2)=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const pc=(v,d=2)=>typeof v==='number'&&Number.isFinite(v)?(v>0?'+':'')+nm(v,d)+'%':'—';
const px=v=>typeof v==='number'&&Number.isFinite(v)?nm(v,v>=100?2:v>=1?4:v>=.01?5:8):'—';
const tm=t=>t?new Date(t).toLocaleString('id-ID',{timeZone:'Asia/Jakarta',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'}):'—';
const relTime=t=>{if(!t)return '—';const min=Math.max(0,Math.floor((Date.now()-t)/60000));return min<60?min+'m lalu':min<1440?Math.floor(min/60)+'j '+min%60+'m lalu':Math.floor(min/1440)+'h lalu'};
const dir=v=>!Number.isFinite(v)?'flat':v>0?'up':v<0?'down':'flat';
let active='ALL', state=null, busy=false, detailToken=0, detailId=null;
let strategyMode='scalping';
function strategyRows(rows){return visibleRows(rows)}
function setStrategy(mode){
 if(mode!=='scalping'&&mode!=='swing')return;
 if(strategyMode===mode && state)return;
 strategyMode=mode;document.body.dataset.strategy=mode;
 document.querySelectorAll('.strategy-switch button').forEach(el=>
   el.setAttribute('aria-selected',String(el.dataset.strategy===mode)));
 $('strategyNote').textContent=mode==='scalping'
  ?'Scalping: 1m · 5m · 15m · 1H. Sinyal dan hasil memakai candle 1m; tanpa pergerakan harga 24H.'
  :'Swing: 15m · 1H · 4H · 8H · 1D · 1W. Filter arah 24H aktif; event dinilai pada candle 1H dengan horizon 3 hari.';
 state=null;active='ALL';$('rows').replaceChildren();
 if($('mode').value==='all')$('mode').value='top80';
 poll();
}
const modeLabel=m=>({all:'ALL PAIRS',liquid:'LIQUID',top80:'TOP 80'}[m]||m);
const visibleRows=rows=>rows.filter(r=>(r.turnover24h||0)>=Number($('minDisplay').value));
function updateModeUI(){$('turnover').hidden=$('mode').value!=='liquid'}
function el(tag,txt,cls){const z=document.createElement(tag);if(txt!==undefined)z.textContent=txt;if(cls)z.className=cls;return z}
function err(id,msg){const x=$(id);x.style.display=msg?'block':'none';x.textContent=msg||''}
function selectedEvent(row){const e=row.journeys||[];if(keys.includes(active))return e.find(j=>j.direction===(active.includes('NAIK')?'UP':'DOWN')&&j.status===(active.startsWith('SUDAH')?'REACHED':'PENDING'))||null;return e.find(j=>j.status==='REACHED')||e[0]||null}
function categorySwitch(c){active=c;document.querySelectorAll('[data-category]').forEach(z=>z.classList.toggle('active',z.dataset.category===c));$('allBtn').classList.toggle('active',c==='ALL');$('neutralBtn').classList.toggle('active',c==='UNIVERSE');renderRows()}
function addCell(tr,label,value,cls){const td=el('td',value,cls);td.dataset.label=label;tr.append(td);return td}
function countPanels(rows){for(const [k,n,t] of [['POTENSI_NAIK','countPN','topPN'],['SUDAH_NAIK','countSN','topSN'],['POTENSI_TURUN','countPT','topPT'],['SUDAH_TURUN','countST','topST']]){const list=rows.filter(r=>r.categories?.includes(k));$(n).textContent=list.length;$(t).textContent=list.length?list.slice(0,3).map(r=>r.symbol.replace('USDT','')).join(' · '):k.startsWith('SUDAH')?'Belum ada yang mencapai target':'Belum ada sinyal'}}
function hotMovers(rows){const hot=[...rows].filter(r=>!r.stale&&Date.now()-(r.lastClosed5m||0)<15*60000&&Number.isFinite(r.pct60m)&&Math.abs(r.pct60m)>=2).sort((a,b)=>Math.abs(b.pct60m)-Math.abs(a.pct60m)).slice(0,6);const node=$('movers');node.replaceChildren();if(!hot.length){node.append(el('span','Tidak ada pair dengan perubahan ≥ 2% dalam 1H','tiny'));return}for(const c of hot){const chip=el('div',c.symbol.replace('USDT',''),'mover');chip.append(el('span',pc(c.pct60m),dir(c.pct60m)));chip.title='Pergerakan 1H (tidak otomatis masuk kategori Sudah)';chip.role='button';chip.tabIndex=0;chip.addEventListener('click',()=>openDetail(c.symbol));chip.addEventListener('keydown',e=>{if(e.key==='Enter')openDetail(c.symbol)});node.append(chip)}}
function renderRows(){const rows=strategyRows(state?.rows||[]);const term=$('search').value.trim().toUpperCase();let filtered=rows.filter(r=>(active==='UNIVERSE'||(active==='ALL'?((r.categories||[]).length||r.rsiReversalWatch):r.categories?.includes(active)))&&r.symbol.includes(term));const metric=r=>{if($('sort').value==='newest')return selectedEvent(r)?.startedAt||0;if($('sort').value==='score')return selectedEvent(r)?.initialScore||r.score||0;if($('sort').value==='change')return Math.abs(selectedEvent(r)?.currentPct||0);return Math.abs(r[$('sort').value]||0)};filtered.sort((a,b)=>metric(b)-metric(a));const body=$('rows');body.replaceChildren();if(!filtered.length){const r=el('tr');const td=addCell(r,'','Belum ada hasil di kategori ini. Scanner perlu mencatat sinyal dan menunggu candle berikutnya.','empty');td.colSpan=12;body.append(r)}for(const r of filtered){const tr=el('tr');tr.tabIndex=0;tr.title='Lihat analisis '+r.symbol;const first=addCell(tr,'Coin',r.symbol.replace('USDT',''),'ticker');first.append(el('div',r.stale?'Data tersimpan · '+relTime(r.updatedAt):'$ USDT · '+relTime(r.lastClosed5m),'subline'));const td=addCell(tr,'Sinyal');const badges=el('div',undefined,'cats');for(const c of r.categories||[])badges.append(el('span',LABEL[c],`chip ${c}`));if(strategyMode==='intraday'&&(r.categories||[]).length)badges.append(el('span','24H sekarang searah','chip INTRADAY'));if(r.rsiReversalWatch)badges.append(el('span','RSI '+(r.rsiWatchTimeframe||'')+' ≥'+(r.rsiWatchThreshold??70)+' ↘ Watch','chip RSIWATCH'));if(!r.categories?.length&&!r.rsiReversalWatch)badges.append(el('span','Netral','chip NETRAL'));td.append(badges);
 const ev=selectedEvent(r);const ch=ev?(ev.currentMarketPct??(ev.direction==='DOWN'?-ev.currentPct:ev.currentPct)):null;
 const quoteFresh=Number.isFinite(r.quoteAt)&&Date.now()-r.quoteAt<=90000;
 const drift=ev&&quoteFresh&&Number.isFinite(r.livePrice)?100*(r.livePrice/ev.baselinePrice-1)*(ev.direction==='UP'?1:-1):null;
 const ageMin=ev?(Date.now()-ev.startedAt)/60000:0;
 const lifecycle=ev?.status==='PENDING'?(ageMin>=8?'Sudah tua untuk entry':drift!==null&&drift>.30?'Jangan kejar · harga sudah lari':drift!==null&&drift<-(ev.stopPct||.4)?'Bergerak melawan setup':'Pantau · bukan perintah entry'):(ev?'Target historis tercapai':'');const v=addCell(tr,'Sejak sinyal',ev?pc(ch):'—',`delta ${dir(ch)} ${Number.isFinite(ch)&&Math.abs(ch)>=2?'super':''}`);if(ev)v.append(el('div',lifecycle+' · '+relTime(ev.startedAt)+(quoteFresh?' · quote baru':' · quote tidak live'),'subline'));else v.append(el('div','Belum ada sinyal','subline'));
 const peak=addCell(tr,'Terbaik sejak sinyal',ev?pc(ev.peakMarketPct??(ev.direction==='DOWN'?-ev.peakClosePct:ev.peakClosePct)):'—',ev?'weight':'flat');if(ev)peak.append(el('div','target '+pc(ev.direction==='DOWN'?-ev.triggerPct:ev.triggerPct),'subline'));
 for(const [label,key,hot] of [['15m','pct15m',2],['1H','pct60m',4],['24H','pct24h',8]]){const v=r[key];addCell(tr,label,pc(v),`${dir(v)} ${Number.isFinite(v)&&Math.abs(v)>=hot?'delta super':''}`)}
 addCell(tr,strategyMode==='scalping'?'Vol 1m':'Vol 15m',Number.isFinite(strategyMode==='scalping'?r.relVolume1m:r.relVolume15m)?nm(strategyMode==='scalping'?r.relVolume1m:r.relVolume15m,2)+'×':'—','weight');addCell(tr,'OI 15m',pc(r.oi15mPct),dir(r.oi15mPct));addCell(tr,'Tren',strategyMode==='scalping'?`${r.trend15m?.slice(0,4)||'?'} / ${r.trend1h?.slice(0,4)||'?'}`:`${r.trend1d?.slice(0,4)||'?'} / ${r.trend1w?.slice(0,4)||'?'}`,'weight');const score=addCell(tr,'Skor');score.append(el('span',String(ev?ev.initialScore:r.score),'score'));addCell(tr,'','Detail ↗','view');tr.addEventListener('click',()=>openDetail(r.symbol));tr.addEventListener('keydown',e=>{if(e.key==='Enter')openDetail(r.symbol)});body.append(tr)}$('countNote').textContent=filtered.length+' tampil · '+rows.length+' pair berhasil dipantau'}
function render(st){
 state=st;
 const done=st.processed||0, total=st.total||0;
 const pctDone=total?Math.min(100,Math.round(done/total*100)):0;
 $('progress').style.width=pctDone+'%';
 const activeMode=modeLabel(st.mode);
 $('message').textContent=st.configPending?`Scan ${activeMode} berjalan. Mode pilihan akan dimulai sesudahnya.`:st.message;
 $('scanDetails').textContent=`${strategyMode==='scalping'?'1m/5m/15m/1H':'15m/1H/4H/8H/1D/1W'} · Top ${st.activeSignals||0}/${st.activeLimit||5} aktif · ${done}/${total||'…'} pair · ${st.successful||0} sukses · ${st.failed||0} gagal`;
 $('scanStats').replaceChildren();
 for(const [name,value] of [['Pair aktif',st.universe||'…'],['Sesuai mode',st.eligible||'…'],['Dalam antrean',total||'…'],['Tanpa ticker',st.missingTicker||0]]){
   const b=el('span',undefined,'stat-item');b.append(el('b',String(value)),el('span',name));$('scanStats').append(b);
 }
 $('time').textContent=tm(st.completedAt||st.startedAt);
 $('live').textContent=st.running?`${activeMode} · ${pctDone}%`:`${activeMode} · siklus selesai`;
 $('dot').className='dot '+(st.running?'busy':st.errorCount&&st.processed===0?'bad':'');
 const filtered=strategyRows(st.rows||[]);
 countPanels(filtered);hotMovers(filtered);renderRows();
 err('error',st.errors?.length?'Error Binance ('+st.errorCount+'): '+st.errors.slice(0,2).join(' | '):'');
}

async function poll(force=false){if(busy)return;busy=true;try{const profile=strategyMode;const url=`/api/scan?strategy=${profile}&mode=${encodeURIComponent($('mode').value)}&min_turnover=${$('turnover').value}${force?'&force=1':''}`;const ctl=new AbortController();const t=setTimeout(()=>ctl.abort(),18000);let r;try{r=await fetch(url,{signal:ctl.signal,cache:'no-store'})}finally{clearTimeout(t)}const d=await r.json();if(!r.ok)throw Error(d.error||'Server error');if(profile===strategyMode)render(d)}catch(e){$('dot').className='dot bad';$('live').textContent='Offline';err('error','Tidak tersambung ke server scanner: '+e.message)}finally{busy=false}}
function plot(points){const svg=$('chart');svg.replaceChildren();if(!points?.length)return;const vals=points.map(x=>x.close),min=Math.min(...vals),max=Math.max(...vals),range=Math.max((max-min)*1.16,max*.0001);const x=i=>48+(i/(vals.length-1))*665,y=v=>220-(v-(min-range*.07))/range*185;const ns='http://www.w3.org/2000/svg';const node=(tag,attrs={})=>{const e=document.createElementNS(ns,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e};for(let i=0;i<5;i++){svg.append(node('line',{x1:45,x2:718,y1:25+i*47,y2:25+i*47,stroke:'#2a3b50','stroke-width':1}));const txt=node('text',{x:4,y:29+i*47,fill:'#879bb5','font-size':10});txt.textContent=px(max+range*.07-i*range*.25);svg.append(txt)}const path=node('path',{d:vals.map((v,i)=>(i?'L':'M')+x(i).toFixed(2)+','+y(v).toFixed(2)).join(' '),stroke:'#6cded1','stroke-width':2.6,fill:'none'});svg.append(path);svg.append(node('circle',{cx:x(vals.length-1),cy:y(vals.at(-1)),r:4.5,fill:'#8bf3d5'}));for(const i of [0,Math.floor(vals.length/2),vals.length-1]){const n=node('text',{x:x(i),y:249,fill:'#92a4bc','text-anchor':'middle','font-size':11});n.textContent=new Date(points[i].t).toLocaleTimeString('id-ID',{timeZone:'Asia/Jakarta',hour:'2-digit',minute:'2-digit'});svg.append(n)}}
function renderProfileDetail(d){
 const x=d.metrics||{},s=d.strategy;
 $('detailTime').textContent='Analisis '+(s==='scalping'?'Scalping':'Swing')+' · '+(d.timeframes||[]).join(' / ');
 $('priceDetail').textContent=px(x.price)+' USDT';
 $('statusDetail').textContent=d.status+' · skor LONG '+x.longScore+'/100, SHORT '+x.shortScore+'/100';
 const ul=$('reasons');ul.replaceChildren();
 const reasons=[
   'Profile '+s+' menggunakan '+(d.timeframes||[]).join(', ')+' saja',
   'Tren: '+(s==='scalping'?'15m '+x.trend15m+' / 1H '+x.trend1h:
      '1D '+x.trend1d+' / 1W '+x.trend1w),
   'Skor hanyalah kecocokan indikator, bukan peluang profit',
   'Status berdasarkan candle selesai, bukan order atau profit aktual'
 ];
 if(s==='swing')reasons.push('Filter perubahan harga 24H searah wajib untuk kandidat Swing');
 for(const line of reasons)ul.append(el('li',line));
 $('levels').textContent=s==='swing'
  ?'Target '+pc(x.triggerPct)+' · Stop '+pc(x.stopPct)+' indikatif; evaluasi maksimum 3 hari. Belum termasuk biaya.'
  :'Scalping: target/stop berbasis ATR 5m, konfirmasi candle 1m, pemantauan maksimum 15 menit. Belum termasuk biaya.';
 $('issues').textContent='Riset read-only; konfigurasi baru belum dibuktikan melalui full historical backtest.';
 const b=$('detailData');b.replaceChildren();
 const fields=[
  ['Timeframes',(d.timeframes||[]).join(' · ')],
  ['Skor LONG',x.longScore+'/100'],['Skor SHORT',x.shortScore+'/100'],
  ['RSI '+(x.rsiWatchTimeframe||'—'),nm(s==='scalping'?x.rsi5m:x.rsi1h,1)],
  ['Volume relatif',nm(s==='scalping'?x.relVolume1m:x.relVolume15m,2)+'×'],
  ['Momentum 15m',pc(x.pct15m)],['Momentum 1H',pc(x.pct60m)]
 ];
 if(s==='swing')fields.push(['Perubahan 24H',pc(x.pct24h)]);
 for(const [label,value] of fields){const box=el('div',undefined,'mini-stat');
   box.append(el('span',label),el('strong',value));b.append(box)}
 plot([]);
}
function renderDetail(d){$('detailTime').textContent='Candle terakhir '+tm(d.indicators['5m'].time)+' WIB';$('priceDetail').textContent=px(d.lastPrice)+' USDT';$('statusDetail').textContent=d.analysis.status+' · '+d.analysis.marketRegime;const ul=$('reasons');ul.replaceChildren();for(const line of d.analysis.reasons)ul.append(el('li',line));const risk=d.analysis.riskIllustration;$('levels').textContent=risk?`Ilustrasi level, bukan order · SL ${px(risk.stopCandidate)} · TP ${px(risk.targetCandidate)} · R:R ${nm(risk.rr,1)}. Belum termasuk biaya.`:'Belum ada setup lengkap untuk ilustrasi TP/SL.';$('issues').textContent=d.issues?.length?'Catatan API: '+d.issues.join(' | '):'Data read-only. Belum divalidasi backtest.';const oi=d.openInterest;const fields=[['OI 5m',oi.available?pc(oi.delta5mPct,3):'N/A'],['OI 15m',oi.available?pc(oi.delta15mPct,3):'N/A'],['OI 60m',oi.available?pc(oi.delta60mPct,3):'N/A'],['Funding',pc(d.fundingRatePct,4)],['EMA 200 · 1H',px(d.indicators['1h'].ema200)],['EMA 200 · 4H',px(d.indicators['4h'].ema200)],['EMA 21 · 15m',px(d.indicators['15m'].ema21)],['RSI 15m',nm(d.indicators['15m'].rsi14,1)],['VWAP UTC',px(d.vwap.value)],['MACD hist 5m',nm(d.indicators['5m'].macdHistogram,6)],['Rel. Volume 5m',nm(d.indicators['5m'].volumeRatio)+'×'],['ATR 5m',px(d.indicators['5m'].atr14)],['Taker buy share',pc(d.indicators['5m'].takerBuySharePct,1)],['Regime',d.analysis.trend1h+'/'+d.analysis.trend4h],['Mark price',px(d.markPrice)],['Open interest value',oi.available?('$'+nm((oi.notionalUSDT||0)/1e6,1)+'M'):'N/A']];const box=$('detailData');box.replaceChildren();for(const [label,val] of fields){const b=el('div',undefined,'mini-stat');b.append(el('span',label),el('strong',val));box.append(b)}plot(d.chart5m)}
async function openDetail(symbol){detailId=symbol;const token=++detailToken;$('detail').classList.add('open');$('detailSymbol').textContent=symbol+' · loading…';err('detailError','');$('detail').scrollIntoView({behavior:'smooth',block:'start'});try{const r=await fetch('/api/snapshot?symbol='+encodeURIComponent(symbol)+'&strategy='+encodeURIComponent(strategyMode),{cache:'no-store'});const data=await r.json();if(!r.ok)throw Error(data.error||'Gagal mengambil detail');if(token===detailToken){$('detailSymbol').textContent=symbol;if(data.strategy)renderProfileDetail(data);else renderDetail(data)}}catch(e){if(token===detailToken){$('detailSymbol').textContent=symbol;err('detailError',e.message)}}}
async function loadHistory(){const box=$('historyRows');if(!box)return;box.textContent='Mengambil riwayat…';try{const resp=await fetch('/api/events?strategy='+encodeURIComponent(strategyMode),{cache:'no-store'});if(!resp.ok)throw Error('API error');const data=await resp.json();const events=(data.events||[]).slice(0,30);box.replaceChildren();if(!events.length){box.textContent='Belum ada event tersimpan.';return}for(const e of events){const reason=e.status==='REACHED'?'Target tercapai':e.endReason==='STOP_HIT'?'Stop indikatif tersentuh':e.endReason==='RANK_REPLACED'?'Tergeser skor lain':e.endReason?.startsWith('TIMEOUT')?'Waktu habis':e.status==='PENDING'?'Sedang dipantau':e.endReason||'Selesai';const d=el('div',undefined,'history-item');d.append(el('strong',e.symbol+' · '+(e.direction==='UP'?'NAIK':'TURUN')),el('span',e.status+' · '+reason+' · '+relTime(e.startedAt)));box.append(d)}}catch(e){box.textContent='Gagal memuat riwayat: '+e.message}}
document.querySelectorAll('.strategy-switch [data-strategy]').forEach(b=>b.addEventListener('click',()=>setStrategy(b.dataset.strategy)));
$('historyToggle')?.addEventListener('click',()=>{const box=$('historyRows');const open=box.hidden;box.hidden=!open;if(open)loadHistory()});
document.querySelectorAll('[data-category]').forEach(b=>b.addEventListener('click',()=>categorySwitch(b.dataset.category)));
$('allBtn').addEventListener('click',()=>categorySwitch('ALL'));$('neutralBtn').addEventListener('click',()=>categorySwitch('UNIVERSE'));$('search').addEventListener('input',renderRows);$('sort').addEventListener('change',renderRows);$('refresh').addEventListener('click',()=>poll(true));$('mode').addEventListener('change',()=>{updateModeUI();poll()});$('turnover').addEventListener('change',()=>poll());$('minDisplay').addEventListener('change',()=>{if(state){const rows=strategyRows(state.rows||[]);countPanels(rows);hotMovers(rows);renderRows()}});updateModeUI();$('closeDetail').addEventListener('click',()=>{$('detail').classList.remove('open');detailToken++;detailId=null});poll();setInterval(()=>poll(),5000);
if('serviceWorker' in navigator&&location.protocol==='https:')navigator.serviceWorker.register('/sw.js').catch(()=>{});