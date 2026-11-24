#!/usr/bin/env node
// Optional standalone research runner; Node 18+. Does not import or change the Python production scanner.
const fs=require('node:fs/promises');
const path=require('node:path');
const crypto=require('node:crypto');
const {technicalReplay,summarizeTechnical}=require('./technical_replay.cjs');
const DEFAULT=['BTC','ETH','SOL','BNB','XRP','DOGE','ADA','LINK','AVAX','LTC','BCH','TRX','DOT','SUI','APT','NEAR','ATOM','INJ','UNI','AAVE','ARB','OP','FIL','ETC','WLD','ENA','SEI','TIA'].map(s=>s+'USDT');
const DEFAULT_WINDOWS=[['explore','2026-11-23T04:00:00Z'],['anchor','2026-11-23T08:00:00Z'],['explore','2026-11-23T12:00:00Z'],['explore','2026-11-23T16:00:00Z'],['explore','2026-11-23T20:00:00Z'],['timecheck','2026-11-24T00:00:00Z'],['timecheck','2026-11-24T04:00:00Z'],['anchor','2026-11-24T08:00:00Z']];
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
async function market(endpoint,query){
  const u=new URL('https://fapi.binance.com'+endpoint);
  Object.entries(query).forEach(([k,v])=>u.searchParams.set(k,String(v)));
  const r=await fetch(u,{signal:AbortSignal.timeout(30000),headers:{Accept:'application/json'}});
  if(!r.ok){const err=new Error('Binance HTTP '+r.status+' '+(await r.text()).slice(0,200));err.status=r.status;throw err}
  const a=await r.json();if(!Array.isArray(a))throw Error('Expected array: '+endpoint);return a;
}
async function main(){
 const config=process.argv[2]?JSON.parse(await fs.readFile(process.argv[2],'utf8')):{};
 const end=Date.parse(config.end??'2026-11-24T08:00:00Z');
 const windows=config.windows??DEFAULT_WINDOWS, symbols=[...new Set(config.symbols??DEFAULT)];
 if(!Number.isFinite(end)||end>Date.now()||end%300000!==0||!Array.isArray(windows)||!windows.length||!symbols.length||symbols.some(s=>!/^([A-Z0-9]{2,24})USDT$/.test(s)))throw Error('Invalid end/windows/symbols');
 const times=windows.map(([p,t])=>{if(!['explore','timecheck','anchor'].includes(p)||!Number.isFinite(Date.parse(t))||Date.parse(t)>end||Date.parse(t)%300000!==0)throw Error('Invalid window');return Date.parse(t)});
 if(new Set(times).size!==times.length)throw Error('Duplicate windows');
 const warmup5=229*900000+2*3600000;
 if(Math.min(...times)-warmup5<end-1500*300000)throw Error('Window outside 1500-bar 5m warmup; use multiple run configs');
 const id=config.runId??new Date().toISOString().replace(/[:.]/g,'-');
 if(!/^[A-Za-z0-9_-]+$/.test(id))throw Error('Invalid runId');
 const root=path.resolve(config.outputDir??'data/research-runs');await fs.mkdir(root,{recursive:true});
 const out=path.join(root,id);await fs.mkdir(out); // no silent overwrite
 await fs.mkdir(path.join(out,'raw'));
 const settings={schemaVersion:1,engineSha256:sha(await fs.readFile(path.join(__dirname,'technical_replay.cjs'))),end:new Date(end).toISOString(),symbols,windows,source:'Binance USD-M public REST',feePct:0.20,baseline:'v0.5',createdAt:new Date().toISOString()};
 await fs.writeFile(path.join(out,'config.json'),JSON.stringify(settings,null,2));
 const rows=[],manifest=[];
 for(const symbol of symbols){
   try{
    const k5=await market('/fapi/v1/klines',{symbol,interval:'5m',limit:1500,endTime:end-1});
    const k1h=await market('/fapi/v1/klines',{symbol,interval:'1h',limit:1050,endTime:end-1});
    let ratio=[],ratioError=null;try{ratio=await market('/futures/data/globalLongShortAccountRatio',{symbol,period:'5m',limit:500,endTime:end})}catch(e){if([418,429,403,451].includes(e.status))throw e;ratioError=String(e)}
    const raw=JSON.stringify({symbol,k5,k1h,ratio,ratioError}),file='raw/'+symbol+'.json';
    await fs.writeFile(path.join(out,file),raw);manifest.push({symbol,file,sha256:sha(raw),k5:k5.length,k1h:k1h.length,ratio:ratio.length,ratioError});
    const row=technicalReplay({symbol,k5,k1h,ratio},{end,windows});rows.push(row);
    await fs.appendFile(path.join(out,'candidates.jsonl'),row.records.map(r=>JSON.stringify(r)).join('\n')+(row.records.length?'\n':''));
    console.log(symbol,row.coverage.reduce((a,b)=>a+b.valid,0),'screen points',row.records.length,'candidate rows');
   }catch(e){rows.push({symbol,error:String(e)});console.error(symbol,String(e));if([418,429,403,451].includes(e.status)){console.error('Stopped: access or rate limit; no bypass.');break}}
   await new Promise(r=>setTimeout(r,300));
 }
 const summary={manifest,coverage:rows.map(r=>({symbol:r.symbol,coverage:r.coverage,error:r.error})),unprocessed:symbols.filter(s=>!rows.some(r=>r.symbol===s)),summary:summarizeTechnical(rows)};
 await fs.writeFile(path.join(out,'summary.json'),JSON.stringify(summary,null,2));console.log('Saved',out);
 if(summary.unprocessed.length||rows.some(r=>r.error||r.coverage?.some(x=>x.valid!==12)))process.exitCode=2;
}
main().catch(e=>{console.error(e);process.exitCode=1});
