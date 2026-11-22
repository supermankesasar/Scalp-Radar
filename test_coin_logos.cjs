'use strict';
const assert=require('node:assert/strict');
require('./coin_logos.js');
const {baseSymbol,element}=globalThis.CoinLogos;
assert.equal(baseSymbol('BTCUSDT'),'BTC');
assert.equal(baseSymbol('ETHUSDT'),'ETH');
assert.equal(baseSymbol('1000PEPEUSDT'),'PEPE');
assert.equal(baseSymbol('XBTUSDT'),'BTC');
assert.equal(baseSymbol('SOLUSDC'),null);
assert.equal(baseSymbol('../USDT'),null);
assert.equal(baseSymbol('BTCUSDT?url=http'),null);
const made=[];
globalThis.document={
  createElement(tag){
    const item={tag,children:[],attributes:{},handlers:{},className:'',src:'',
      append(...kids){this.children.push(...kids);for(const c of kids)c.parent=this},
      remove(){if(this.parent)this.parent.children=this.parent.children.filter(x=>x!==this)},
      setAttribute(k,v){this.attributes[k]=v},
      addEventListener(k,callback){this.handlers[k]=callback}};
    made.push(item);return item;
  }
};
const icon=element('BTCUSDT');
assert.equal(icon.attributes['aria-hidden'],'true');
assert.equal(icon.children.length,2);
assert.equal(icon.children[0].textContent,'BTC');
assert.match(icon.children[1].src,/\/btc\.png$/);
assert.equal(icon.children[1].loading,'lazy');
assert.equal(icon.children[1].referrerPolicy,'no-referrer');
const missing=element('VERYRAREALTCOINUSDT','small');
assert.equal(missing.children[1].src.endsWith('/veryrarealtcoin.png'),true);
missing.children[1].handlers.error();
assert.equal(missing.children.length,1,'fallback remains after image 404');
const missingAgain=element('VERYRAREALTCOINUSDT');
assert.equal(missingAgain.children.length,1,'do not request failed symbol again');
assert.equal(missingAgain.children[0].textContent,'VER');
const invalid=element('<script>USDT');
assert.equal(invalid.children.length,1);
assert.equal(invalid.children[0].textContent,'?');
console.log('Coin logo fallback and symbol tests passed');
