const assert=require('node:assert/strict');
const {technicalReplay,summarizeTechnical}=require('./technical_replay.cjs');
const end=Date.parse('2026-11-24T08:00:00Z'), H=3600000,S=300000;
function bars(n,step,start,base,slope){return Array.from({length:n},(_,i)=>{let t=start+i*step,p=base+slope*i;return [t,p,p+0.3,p-0.3,p+0.05,10000,t+step-1,1000000,100,5000,500000,0]})}
const k5=bars(1500,S,end-1500*S,100,0.004);
const k1h=bars(1050,H,end-1050*H,100,0.004);
const windows=[['anchor','2026-11-24T08:00:00Z']];
const r=technicalReplay({symbol:'TESTUSDT',k5,k1h},{end,windows});
assert.equal(r.coverage[0].valid,12);assert.equal(r.coverage[0].liquid,12);
const altered=k5.map(x=>x.slice());let mid=end-H;
for(const x of altered)if(x[0]>=mid){x[1]*=2;x[2]*=2;x[3]*=2;x[4]*=2;}
const q=technicalReplay({symbol:'TESTUSDT',k5:altered,k1h},{end,windows});
const frozen=x=>x.records.map(v=>[v.t,v.sg,v.names,v.features,v.score,v.fastScore]);
assert.deepEqual(frozen(q),frozen(r),'future prices must not alter prior eligibility/features');
assert.deepEqual(summarizeTechnical([]),{explore:{},timecheck:{},anchor:{},all:{}});
console.log('PASS: coverage, liquidity, future-data isolation, empty aggregation');
