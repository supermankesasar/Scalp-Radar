// Pure replay. Five independent modules consume a shared immutable snapshot.
const filters=['oi','order_flow','positioning','composite','technical_ema'].map(n=>require('./filters/'+n+'.cjs'));
const STEP=300000,HOUR=3600000;
const WINDOWS=['2026-11-23T04:00:00Z','2026-11-23T08:00:00Z','2026-11-23T12:00:00Z','2026-11-23T16:00:00Z','2026-11-23T20:00:00Z','2026-11-24T00:00:00Z','2026-11-24T04:00:00Z','2026-11-24T08:00:00Z'];
const mean=a=>a.reduce((s,x)=>s+x,0)/a.length;
function ema(a,n){let x=mean(a.slice(0,n)),o=Array(n-1).fill(null).concat(x);for(let p of a.slice(n)){x+=2/(n+1)*(p-x);o.push(x)}return o}
function atr(a){let x=a.slice(1).map((r,i)=>Math.max(r.h-r.l,Math.abs(r.h-a[i].c),Math.abs(r.l-a[i].c))),v=mean(x.slice(0,14));for(let p of x.slice(14))v=(13*v+p)/14;return v}
function replay(input,windows=WINDOWS){
 let bars=input.k.map(r=>({t:+r[0],e:+r[6]+1,o:+r[1],h:+r[2],l:+r[3],c:+r[4],q:+r[7],buy:+r[10]})).sort((a,b)=>a.t-b.t);
 let oi=new Map(input.oi.map(x=>[+x.timestamp,+x.sumOpenInterest])),ls=new Map(input.ls.map(x=>[+x.timestamp,+x.longAccount])),fund=input.funding.map(x=>({t:+x.fundingTime,v:+x.fundingRate})).sort((a,b)=>a.t-b.t);
 let e9=ema(bars.map(x=>x.c),9),e21=ema(bars.map(x=>x.c),21),records=[],coverage=[];
 for(let date of windows){let end=Date.parse(date),prev=new Set(),cov={window:date,scans:0,oi:0,ls:0,funding:0};
 for(let t=end-2*HOUR+STEP;t<=end-HOUR;t+=STEP){let i=bars.findIndex(x=>x.e===t);if(i<30)continue;let f=bars.slice(i+1,i+13),hist=bars.slice(Math.max(0,i-288),i+1);if(f.length!==12||!f.every((x,j)=>x.t===t+j*STEP&&x.e===t+(j+1)*STEP)||!hist.every((x,j)=>j===0||hist[j-1].e===x.t)){prev.clear();continue}
 let a=bars[i],last3=bars.slice(i-2,i+1),q=last3.reduce((s,x)=>s+x.q,0),lag=t-STEP,old=lag-3*STEP,ov=oi.get(lag),op=oi.get(old),l=ls.get(lag),lp=ls.get(old),fr=fund.filter(x=>x.t<t).at(-1),at=100*atr(hist)/a.c;
 let c=Object.freeze({t,price:a.c,prevPrice:bars[i-1].c,low:a.l,high:a.h,price15:100*(a.c/bars[i-3].c-1),oi15:ov>0&&op>0?100*(ov/op-1):null,longShare:Number.isFinite(l)?l:null,longDelta:Number.isFinite(l)&&Number.isFinite(lp)?l-lp:null,funding:fr?fr.v:null,fundingTime:fr?fr.t:null,taker15:q>0?last3.reduce((s,x)=>s+x.buy,0)/q:null,rvol:a.q/mean(bars.slice(i-20,i).map(x=>x.q)),atrPct:at,ema9:e9[i],prevEma9:e9[i-1],ema21:e21[i],prevEma21:e21[i-1]});
 cov.scans++;cov.oi+=Number.isFinite(c.oi15);cov.ls+=Number.isFinite(c.longDelta);cov.funding+=Number.isFinite(c.funding);
 let tags=filters.flatMap(fn=>fn(c)),next=new Set(tags.map(x=>x.id+':'+x.dir));
 for(let dir of [1,-1]){let names=tags.filter(x=>x.dir===dir).map(x=>x.id);if(!names.length)continue;
 let outcomes=[15,30,60].map(h=>{let g=f.slice(0,h/5),entry=g[0].o,target=Math.max(.65,1.5*at),stop=Math.max(.4,at),ex=g.at(-1).c,status=0;for(let x of g){let z=dir*100*(x.c/a.c-1);if(z>=target||z<=-stop){status=z>=target?1:-1;ex=x.c;break}}return {h,status,gross:dir*100*(g.at(-1).c/entry-1),net:dir*100*(ex/entry-1)-.2,mfe:Math.max(0,...g.map(x=>dir*100*((dir>0?x.h:x.l)/entry-1))),mae:Math.min(0,...g.map(x=>dir*100*((dir>0?x.l:x.h)/entry-1)))}});
 records.push({symbol:input.symbol,window:date,t,dir,names,first:names.filter(n=>!prev.has(n+':'+dir)),features:c,outcomes});
 }prev=next;
 }coverage.push(cov)}
 return {symbol:input.symbol,coverage,records};
}
module.exports={replay,WINDOWS};
