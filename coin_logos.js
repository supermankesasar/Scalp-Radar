'use strict';
/* Read-only coin logos; never infer investment identity from the artwork. */
(()=>{
 const CDN='https://cdn.jsdelivr.net/gh/spothq/cryptocurrency-icons@master/32/color/';
 const failed=new Set();
 const aliases=Object.freeze({XBT:'BTC',BCC:'BCH'});
 function baseSymbol(symbol){
   if(typeof symbol!=='string')return null;
   const found=/^([A-Z0-9]{2,30})USDT$/.exec(symbol);
   if(!found)return null;
   let base=found[1];
   // Futures quantity-prefix contracts such as 1000SHIBUSDT.
   if(base.startsWith('1000')&&base.length>6)base=base.slice(4);
   return aliases[base]||base;
 }
 function element(symbol,size='normal'){
   const base=baseSymbol(symbol);
   const logo=document.createElement('span');
   logo.className='coin-logo'+(size==='large'?' coin-logo--large':size==='small'?' coin-logo--small':'');
   logo.setAttribute('aria-hidden','true');
   const fallback=document.createElement('span');
   fallback.className='coin-logo__fallback';
   fallback.textContent=(base||'?').slice(0,3);
   logo.append(fallback);
   // Never build external URLs from arbitrary unvalidated user input.
   if(!base||failed.has(base))return logo;
   const img=document.createElement('img');
   img.className='coin-logo__image';
   img.alt='';
   img.width=32;img.height=32;
   img.loading='lazy';img.decoding='async';
   img.referrerPolicy='no-referrer';
   img.addEventListener('error',()=>{
     failed.add(base);
     img.remove(); // Keep the initials visible.
   },{once:true});
   img.src=CDN+encodeURIComponent(base.toLowerCase())+'.png';
   logo.append(img);
   return logo;
 }
 globalThis.CoinLogos=Object.freeze({baseSymbol,element});
})();
