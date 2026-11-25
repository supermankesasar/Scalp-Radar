#!/usr/bin/env node
// Node >=18; source modules are independent. Read-only public futures endpoints.
const fs=require('node:fs/promises'), path=require('node:path'), crypto=require('node:crypto');
const {replay,WINDOWS}=require('./r06_replay.cjs');
const cohort=require('./cohorts/r06_30.json');
const STEP=300000;
const sha=s=>crypto.createHash('sha256').update(s).digest('hex');
async function fetchArray(endpoint,params){
 const u=new URL('https://fapi.binance.com'+endpoint);
 for(const [k,v] of Object.entries(params))u.searchParams.set(k,String(v));
 const r=await fetch(u,{signal:AbortSignal.timeout(30000),headers:{Accept:'application/json'}});
 if(!r.ok){let e=Error('Binance HTTP '+r.status+' '+(await r.text()).slice(0,200));e.status=r.status;throw e}
 const a=await r.json();if(!Array.isArray(a))throw Error('Unexpected response');return a;
}
async function main(){
 let cfg=process.argv[2]?JSON.parse(await fs.readFile(process.argv[2],'utf8')):{};
 let symbols=[...new Set(cfg.symbols??cohort.chosen.map(x=>x.symbol))],windows=cfg.windows??WINDOWS;
 let times=windows.map(Date.parse),end=Math.max(...times),earliest=Math.min(...times);
 if(!windows.length||!times.every(t=>Number.isFinite(t)&&t%900000===0&&t<=Date.now())||new Set(times).size!==times.length)throw Error('Invalid windows');
 if(!symbols.length||symbols.some(s=>!/^([A-Z0-9]{2,24})USDT$/.test(s)))throw Error('Invalid symbols');
 // OI/ratio endpoint maximum 500 five-minute records. Keep one immutable run within coverage.
 if(end-earliest+3*3600000>499*STEP)throw Error('Windows exceed OI/ratio coverage: split into separate runs');
 const id=cfg.runId??new Date().toISOString().replace(/[:.]/g,'-');
 if(!/^[A-Za-z0-9_-]+$/.test(id))throw Error('Invalid runId');
 const base=path.resolve(cfg.outputDir??'data/research-runs');await fs.mkdir(base,{recursive:true});const out=path.join(base,id);await fs.mkdir(out);await fs.mkdir(path.join(out,'raw'));
 const modules=['oi','order_flow','positioning','composite','technical_ema'];
 let hashes={};for(let n of modules)hashes[n]=sha(await fs.readFile(path.join(__dirname,'filters',n+'.cjs')));
 const manifest={schema:1,runId:id,symbols,windows,source:'Binance USD-M Futures public REST',feePct:.2,engineHash:sha(await fs.readFile(path.join(__dirname,'r06_replay.cjs'))),filterHashes:hashes,coverage:[],raw:[],errors:[]};
 await fs.writeFile(path.join(out,'config.json'),JSON.stringify(manifest,null,2));
 let records=[];
 for(let symbol of symbols){try{
  let k=await fetchArray('/fapi/v1/klines',{symbol,interval:'5m',limit:600,endTime:end-1});
  let oi=await fetchArray('/futures/data/openInterestHist',{symbol,period:'5m',limit:500,endTime:end});
  let ls=await fetchArray('/futures/data/globalLongShortAccountRatio',{symbol,period:'5m',limit:500,endTime:end});
  let funding=await fetchArray('/fapi/v1/fundingRate',{symbol,startTime:end-3*86400000,endTime:end,limit:100});
  const payload={symbol,k,oi,ls,funding},raw=JSON.stringify(payload),file='raw/'+symbol+'.json';
  await fs.writeFile(path.join(out,file),raw);manifest.raw.push({symbol,file,sha256:sha(raw)});
  let row=replay(payload,windows);records.push(...row.records);manifest.coverage.push({symbol,windows:row.coverage});
  await fs.appendFile(path.join(out,'candidates.jsonl'),row.records.map(x=>JSON.stringify(x)).join('\n')+(row.records.length?'\n':''));
  console.log(symbol,row.records.length);
 }catch(e){manifest.errors.push({symbol,error:String(e)});console.error(symbol,String(e));if([403,451,418,429].includes(e.status))break}
 await new Promise(r=>setTimeout(r,350));
 }
 const summary={};for(let r of records)for(let name of r.names){let a=summary[name]??(summary[name]={all:0,first:0,net30Sum:0,firstNet30Sum:0});a.all++;a.net30Sum+=r.outcomes[1].net;if(r.first.includes(name)){a.first++;a.firstNet30Sum+=r.outcomes[1].net}}
 manifest.unprocessed=symbols.filter(s=>!manifest.coverage.some(c=>c.symbol===s)&&!manifest.errors.some(c=>c.symbol===s));
 await fs.writeFile(path.join(out,'result.json'),JSON.stringify({runId:id,batch:id,coverage:manifest.coverage,records,summary,manifest},null,2));
 console.log('Saved',out);
 if(manifest.errors.length||manifest.unprocessed.length||manifest.coverage.some(c=>c.windows.some(w=>w.scans!==12||w.oi!==12||w.ls!==12||w.funding!==12)))process.exitCode=2;
}
main().catch(e=>{console.error(e);process.exitCode=1});
