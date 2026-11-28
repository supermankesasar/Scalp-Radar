"""Integrated cache-only impulse challenger. Reuses R11.1 evaluated features and book.
Separate prospective paired control and confirmed-entry cohorts; no orders."""
import json
from filters import r112
from research_r10 import entry_time,simulate
STEP=60000

def pack(x):return json.dumps(x,separators=(',',':'),allow_nan=False)

class ImpulseRadar:
    def __init__(self,db):
        self.states={};self.prior={};self.results={};self.last_impulse={};self.cut=None
        db.executescript("""
        CREATE TABLE IF NOT EXISTS r112_events(symbol TEXT,cutoff INTEGER,decision INTEGER,state TEXT,direction TEXT,
          impulse_cutoff INTEGER,payload TEXT,version TEXT,PRIMARY KEY(symbol,cutoff));
        CREATE TABLE IF NOT EXISTS r112_entries(symbol TEXT,cutoff INTEGER,cohort TEXT,direction TEXT,decision INTEGER,entry_at INTEGER,
          atr REAL,payload TEXT,complete INTEGER DEFAULT 0,PRIMARY KEY(symbol,cutoff,cohort));
        CREATE INDEX IF NOT EXISTS r112_pending ON r112_entries(entry_at) WHERE complete=0;
        CREATE TABLE IF NOT EXISTS r112_outcomes(symbol TEXT,cutoff INTEGER,cohort TEXT,horizon INTEGER,policy TEXT,state TEXT,
          gross_pct REAL,mfe REAL,mae REAL,exit_at INTEGER,PRIMARY KEY(symbol,cutoff,cohort,horizon,policy));
        CREATE TABLE IF NOT EXISTS r112_cycles(cutoff INTEGER PRIMARY KEY,eligible INTEGER,universe INTEGER);
        """)
        for s,c in db.execute("SELECT symbol,MAX(cutoff) FROM r112_entries WHERE cohort='INVERSE_CONTROL' GROUP BY symbol"):
            self.last_impulse[s]=c
    def begin(self,cut):
        self.cut=cut;self.prior=dict(self.states);self.results={}
    def pending(self,s):
        return s not in self.results or (self.results[s] is not None and self.results[s]['reason']=='BOOK_UNKNOWN')
    def process(self,s,f,rows,cut,decision,market):
        if not self.pending(s):return
        p=self.prior.get(s)
        if p is None and cut-self.last_impulse.get(s,-10**15)<r112.COOLDOWN:
            self.results[s]=None;return
        di=p['direction'] if p else r112.impulse(f)
        quote,spread,_=market(s,decision,di) if di else (None,None,None)
        result=r112.assess(p,f,rows,cut,decision,quote,spread)
        self.results[s]=result
    def persist(self,db,engine,cut,universe):
        for s,r in self.results.items():
            if r is None:
                self.states.pop(s,None);continue
            self.states[s]=r
            old=self.prior.get(s)
            if old is None or any(r.get(k)!=old.get(k) for k in ('state','reason')):
                db.execute("INSERT OR IGNORE INTO r112_events VALUES(?,?,?,?,?,?,?,?)",
                           (s,cut,r['decisionAt'],r['state'],r['direction'],r['impulseCutoff'],pack(r),r112.VERSION))
            if r['impulseCutoff']==cut:
                self.last_impulse[s]=cut
                opposite='DOWN' if r['direction']=='UP' else 'UP'
                for cohort,di in [('INVERSE_CONTROL',r['direction']),('MOMENTUM_CONTROL',opposite)]:
                    self.insert(db,s,cut,cohort,di,r['decisionAt'],r['impulseFeatures']['atr1mPct'],r)
            if r['state']=='READY':self.insert(db,s,cut,'CONFIRMED',r['direction'],r['decisionAt'],r['readyAtr'],r)
        self.states={s:r for s,r in self.states.items() if cut-r['cutoff']<=STEP and cut-r['impulseCutoff']<=20*STEP}
        self.last_impulse={s:t for s,t in self.last_impulse.items() if cut-t<r112.COOLDOWN}
        db.execute("INSERT OR IGNORE INTO r112_cycles VALUES(?,?,?)",(cut,len(self.results),universe))
        self.settle(db,engine,cut)
    def insert(self,db,s,cut,cohort,di,decision,atr,payload):
        db.execute("INSERT OR IGNORE INTO r112_entries(symbol,cutoff,cohort,direction,decision,entry_at,atr,payload) VALUES(?,?,?,?,?,?,?,?)",
                   (s,cut,cohort,di,decision,entry_time(decision),atr,pack(payload)))
    def settle(self,db,engine,cut):
        cache={}
        for e in db.execute("SELECT * FROM r112_entries WHERE complete=0 AND entry_at+5*60000-1<=? ORDER BY entry_at LIMIT 2000",(cut,)).fetchall():
            s=e['symbol']
            if s not in cache:cache[s]={int(r[6]):r for r in (engine.candles(s,'1m',100,cut+1,require=False) or [])}
            done={(r[0],r[1]) for r in db.execute("SELECT horizon,policy FROM r112_outcomes WHERE symbol=? AND cutoff=? AND cohort=?",(s,e['cutoff'],e['cohort']))}
            for h,policy in ((5,'ENDPOINT'),(15,'ENDPOINT'),(15,'FIXED')):
                if (h,policy) in done:continue
                end=e['entry_at']+h*STEP-1
                if end>cut:continue
                seq=[cache[s].get(e['entry_at']+i*STEP-1) for i in range(1,h+1)]
                if all(seq):
                    base=float(seq[0][1]);sign=1 if e['direction']=='UP' else -1
                    def ret(p):return sign*100*(float(p)/base-1)
                    gross=ret(seq[-1][4]);state='ENDPOINT';exit_at=end
                    if policy=='FIXED':state,_,gross,exit_at,_,_=simulate(seq,e['direction'],e['atr'],h,'FIXED')
                    mfe=max(0.,*(ret(r[2 if sign==1 else 3]) for r in seq))
                    mae=min(0.,*(ret(r[3 if sign==1 else 2]) for r in seq))
                elif cut>end+15*STEP:state,gross,mfe,mae,exit_at='UNOBSERVED',None,None,None,None
                else:continue
                db.execute("INSERT OR IGNORE INTO r112_outcomes VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (s,e['cutoff'],e['cohort'],h,policy,state,gross,mfe,mae,exit_at))
                done.add((h,policy))
            if len(done)==3:db.execute("UPDATE r112_entries SET complete=1 WHERE symbol=? AND cutoff=? AND cohort=?",(s,e['cutoff'],e['cohort']))
    def report(self,db):
        result=[dict(r) for r in db.execute("""SELECT e.cohort,e.direction,o.horizon,o.policy,COUNT(*) n,COUNT(o.gross_pct) observed,
          SUM(o.state='UNOBSERVED') unobserved,AVG(o.gross_pct) gross,AVG(o.gross_pct)-.10 net010,AVG(o.gross_pct)-.20 net020,
          AVG(o.gross_pct)-.35 net035,AVG(o.mfe) mfe,AVG(o.mae) mae
          FROM r112_entries e JOIN r112_outcomes o USING(symbol,cutoff,cohort) GROUP BY 1,2,3,4""")]
        return {'version':r112.VERSION,'comparison':result,'note':'Controls are paired theoretical endpoints at impulse; confirmed entries are delayed selected cohort. Not a matched causal comparison or real fills.'}
