// Research only; not imported by production. Node >=18. Baseline Scalp Radar v0.5.
function technicalReplay(input, options={}) {
  const STEP=300000, HOUR=3600000, DAY=86400000;
  const end=options.end??Date.parse('2026-11-24T08:00:00Z');
  const windows=options.windows??[
    ['explore','2026-11-23T04:00:00Z'],['anchor','2026-11-23T08:00:00Z'],
    ['explore','2026-11-23T12:00:00Z'],['explore','2026-11-23T16:00:00Z'],
    ['explore','2026-11-23T20:00:00Z'],['timecheck','2026-11-24T00:00:00Z'],
    ['timecheck','2026-11-24T04:00:00Z'],['anchor','2026-11-24T08:00:00Z']
  ];
  const avg=a=>a.reduce((s,v)=>s+v,0)/a.length;
  const parse=a=>a.map(x=>({t:+x[0],e:+x[6]+1,o:+x[1],h:+x[2],l:+x[3],c:+x[4],v:+x[5],q:+x[7]})).filter(x=>x.e<=end).sort((a,b)=>a.t-b.t);
  const a=parse(input.k5), b=parse(input.k1h);
  function agg(a,ms,n){let m=new Map();for(let x of a){let t=Math.floor(x.t/ms)*ms;if(!m.has(t))m.set(t,[]);m.get(t).push(x)}return [...m].filter(([t,x])=>x.length===n&&x.every((v,i)=>v.t===t+i*ms/n&&v.e===t+(i+1)*ms/n)).map(([t,x])=>({t,e:t+ms,o:x[0].o,c:x.at(-1).c,h:Math.max(...x.map(v=>v.h)),l:Math.min(...x.map(v=>v.l)),v:x.reduce((s,v)=>s+v.v,0),q:x.reduce((s,v)=>s+v.q,0)}))}
  const d=agg(a,900000,3),c=agg(b,14400000,4);
  function es(x,n){let v=avg(x.slice(0,n)),o=Array(n-1).fill(null).concat(v);for(let z of x.slice(n)){v+=2/(n+1)*(z-v);o.push(v)}return o}
  function rsi(x){let d=x.slice(1).map((z,i)=>z-x[i]),g=avg(d.slice(0,14).map(z=>Math.max(z,0))),l=avg(d.slice(0,14).map(z=>Math.max(-z,0)));for(let z of d.slice(14)){g=(13*g+Math.max(z,0))/14;l=(13*l+Math.max(-z,0))/14}return l?100-100/(1+g/l):g?100:50}
  function atr(x){let d=x.slice(1).map((z,i)=>Math.max(z.h-z.l,Math.abs(z.h-x[i].c),Math.abs(z.l-x[i].c))),v=avg(d.slice(0,14));for(let z of d.slice(14))v=(13*v+z)/14;return v}
  function mac(x){let p=es(x,12),q=es(x,26),d=q.map((z,i)=>z===null?null:p[i]-z).filter(z=>z!==null),sig=es(d,9);return [d.at(-1)-sig.at(-1),d.at(-2)-sig.at(-2)]}
  function regime(x,n){let z=x.map(v=>v.c),e=es(z,n);return z.at(-1)>e.at(-1)&&e.at(-1)>e.at(-7)?1:z.at(-1)<e.at(-1)&&e.at(-1)<e.at(-7)?-1:0}
  function vwap(a){let k=a.filter(x=>Math.floor(x.t/DAY)===Math.floor(a.at(-1).t/DAY));return k.reduce((s,x)=>s+(x.h+x.l+x.c)/3*x.v,0)/k.reduce((s,x)=>s+x.v,0)}
  function outcome(f,px,at,sg,h){let q=f.slice(0,h/5),entry=q[0].o,tg=Math.max(.65,1.5*at),sl=Math.max(.4,at),exit=q.at(-1).c,status=0;for(let x of q){let m=sg*100*(x.c/px-1);if(m>=tg||m<=-sl){status=m>=tg?1:-1;exit=x.c;break}}return {status,net:sg*100*(exit/entry-1)-.2,gross:sg*100*(q.at(-1).c/entry-1),mfe:Math.max(0,...q.map(x=>sg*100*((sg===1?x.h:x.l)/entry-1))),mae:Math.min(0,...q.map(x=>sg*100*((sg===1?x.l:x.h)/entry-1))),chase:sg*100*(entry/px-1)>.3||sg*100*(entry/px-1)<-sl}}
  const ratios=(input.ratio??[]).map(x=>({t:+x.timestamp,p:+x.longAccount})).filter(x=>Number.isFinite(x.p)).sort((a,b)=>a.t-b.t);
  const records=[],coverage=[];
  for(let [phase,date] of windows){let E=Date.parse(date),prev=new Set(),valid=0,liquid=0;for(let t=E-2*HOUR+STEP;t<=E-HOUR;t+=STEP){
    let aa=a.filter(x=>x.e<=t).slice(-309),dd=d.filter(x=>x.e<=t).slice(-229),bb=b.filter(x=>x.e<=t).slice(-229),cc=c.filter(x=>x.e<=t).slice(-229),f=a.filter(x=>x.e>t&&x.e<=t+HOUR);
    if(Math.min(aa.length,dd.length,bb.length,cc.length)<220||aa.at(-1).e!==t||f.length!==12||!f.every((x,i)=>x.t===t+i*STEP&&x.e===t+(i+1)*STEP)){prev.clear();continue}
    valid++;const turn=a.filter(x=>x.e<=t&&x.e>t-DAY);if(turn.length!==288||turn.reduce((s,x)=>s+x.q,0)<1e7){prev.clear();continue}liquid++;
    const x=aa.map(v=>v.c),y=dd.map(v=>v.c),px=x.at(-1),py=y.at(-1),at=100*atr(aa)/px,ret=100*(px/x.at(-4)-1),r=rsi(y),rp=rsi(y.slice(0,-1)),[m,mp]=mac(x),vr=aa.at(-1).q/avg(aa.slice(-21,-1).map(v=>v.q)),vw=vwap(aa),vp=vwap(aa.slice(0,-1)),t1=regime(bb,200),t50=regime(bb,50),t21=regime(bb,21),t4=regime(cc,200),e5={9:es(x,9),21:es(x,21)},e15={9:es(y,9).at(-1),21:es(y,21).at(-1)},last=aa.at(-1),rs=ratios.filter(x=>x.t<=t-STEP),ls=rs.at(-1),lp=rs.filter(x=>x.t<=t-4*STEP).at(-1),ratioOK=ls&&t-ls.t<=2*STEP;
    const current=new Set();
    for(let sg of [1,-1]){
      const rok=sg===1?r>=47&&r<=70:r>=30&&r<=53,mok=sg*m>0,vok=sg*(px-vw)>0,volpts=vr>=1.1?11:vr>=.85?6:0,gate4=t4!==-sg,retOK=sg*ret>=-.4&&sg*ret<=Math.max(.4,1.3*at);
      function qualify({p5=21,p15=21,g15=p15,trend=t1,gate=trend===sg,omitTrend=false,omitMom=false}={}){
        let ds=sg*100*(py/e15[g15]-1),anti=ds>=0&&ds<=Math.max(.75,1.4*at)&&retOK;
        let score=(omitTrend?0:trend===sg?24:0)+(t4===sg?12:t4===0?5:0)+(sg*(py-e15[p15])>0?14:0)+(sg*(px-e5[p5].at(-1))>0?11:0)+(omitMom?0:(rok?10:0)+(mok?10:0))+volpts+(vok?8:0);
        score=score*100/(100-(omitTrend?24:0)-(omitMom?20:0));return {pass:gate&&gate4&&anti&&score>=68,score}
      }
      let base=qualify(),fast=qualify({p5:9,p15:9}),names=[];
      const add=(name,ok)=>{if(ok)names.push(name)};
      add('B21',base.pass);add('E9_21',qualify({p5:9}).pass);add('E9_9',fast.pass);add('E21_9',qualify({p15:9}).pass);
      add('E15_SCORE9_ONLY',qualify({p15:9,g15:21}).pass);add('E15_GATE9_ONLY',qualify({g15:9}).pass);
      add('T1_SCORE_ONLY',qualify({gate:true}).pass);add('T1_RELAX_MIXED',qualify({gate:t1!==-sg}).pass);
      add('T1_REMOVE',qualify({gate:true,omitTrend:true}).pass);add('T1_EMA50',qualify({trend:t50,gate:t50===sg}).pass);add('T1_EMA21',qualify({trend:t21,gate:t21===sg}).pass);
      add('T1_EMA50_GATE_ONLY',qualify({gate:t50===sg}).pass);
      add('MOM_REMOVE_BOTH',qualify({omitMom:true}).pass);add('MOM_BOTH',base.pass&&rok&&mok);add('MOM_EITHER',base.pass&&(rok||mok));add('MOM_BOTH_ACCEL',base.pass&&rok&&mok&&sg*(r-rp)>0&&sg*(m-mp)>0);
      for(let [name,p] of [['E9',9],['E21',21]]){
        let z=e5[p],cur=z.at(-1),old=z.at(-2),cross=sg*(px-cur)>0&&sg*(x.at(-2)-old)<=0;
        let touch=last.l<=old&&last.h>=old&&sg*(px-cur)>0&&sg*(x.at(-2)-old)>0;
        add('FAST_'+name+'_CROSS',fast.pass&&cross);add('FAST_'+name+'_TOUCH',fast.pass&&touch);add('FAST_'+name+'_CROSS_OR_TOUCH',fast.pass&&(cross||touch))
      }
      if(base.pass){
        add('VOL_LT085',vr<.85);add('VOL_085_110',vr>=.85&&vr<1.1);add('VOL_110_150',vr>=1.1&&vr<1.5);add('VOL_GE150',vr>=1.5);add('VOL_GE110',vr>=1.1);
        let vd=sg*100*(px/vw-1)/at;
        add('VW_OPPOSED',vd<=0);add('VW_NEAR',vd>0&&vd<=1);add('VW_MED',vd>1&&vd<=3);add('VW_FAR',vd>3);add('VW_ALIGNED',vd>0);add('VW_RECLAIM',vd>0&&sg*(x.at(-2)-vp)<=0);add('VOL_VW',vr>=1.1&&vd>0);
        if(ratioOK){let signed=sg*(ls.p-.5);add('LS_COVERED',true);add('LS_ALIGNED',signed>0);add('LS_OPPOSED',signed<0);add('LS_CROWDED_ALIGN',signed>=.15);add('LS_CROWDED_OPPOSE',signed<=-.15);add('LS_BALANCED',Math.abs(signed)<.05);if(lp&&ls.t-lp.t<=4*STEP){add('LS_CHANGE_ALIGNED',sg*(ls.p-lp.p)>0);add('LS_CHANGE_OPPOSED',sg*(ls.p-lp.p)<0)}}
      }
      if(!names.length)continue;
      let res=[15,30,60].map(h=>outcome(f,px,at,sg,h));const first=names.filter(n=>!prev.has(n+':'+sg));for(let n of names)current.add(n+':'+sg);
      records.push({symbol:input.symbol,phase,window:date,t,sg,names,first,score:base.score,fastScore:fast.score,features:{px,atrPct:at,ret15:ret,rsi:r,rsiPrev:rp,macd:m,macdPrev:mp,relVolume:vr,vwap:vw,ema5_9:e5[9].at(-1),ema5_21:e5[21].at(-1),ema15_9:e15[9],ema15_21:e15[21],trend1h:t1,trend1h50:t50,trend1h21:t21,trend4h:t4,longAccount:ratioOK?ls.p:null,ratioTime:ratioOK?ls.t:null},outcomes:res})
    }
    prev=current;
  }coverage.push({phase,window:date,valid,liquid})}
  return {symbol:input.symbol,coverage,records};
}
function summarizeTechnical(rows){
 const phases=['explore','timecheck','anchor','all'],out={};
 for(let phase of phases){let m={};for(let row of rows)for(let e of row.records??[]){if(phase!=='all'&&phase!==e.phase)continue;for(let name of e.names){let a=m[name]??(m[name]={all:[0,0,0,0,0,0,0],first:[0,0,0,0,0,0,0]});let q=e.outcomes[1];for(let k of ['all','first']){if(k==='first'&&!e.first.includes(name))continue;let z=a[k];z[0]++;z[1]+=q.status===1;z[2]+=q.status===-1;z[3]+=q.gross>0;z[4]+=q.net;z[5]+=q.gross;z[6]+=q.chase}}}out[phase]=m}return out;
}
module.exports={technicalReplay,summarizeTechnical};
