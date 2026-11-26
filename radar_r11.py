"""R11 independent preview: cache only, minute events, bounded 15m outcomes.
Existing R08 dashboard and R09/R10 ledgers remain unchanged.
"""
import json,sqlite3,threading,time
from contextlib import contextmanager
from filters import r11
from stream_engine import close_at
from research_r10 import entry_time,simulate

def now_ms():return int(time.time()*1000)

class RadarR11:
    def __init__(self,path,db_lock,engine):
        self.path,self.db_lock,self.engine=str(path),db_lock,engine
        self.lock=threading.RLock()
        self.states={}
        self.cutoff=None;self.done=set();self.finalized=False;self.latest={}
        self.last_error=None
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS r11_events(symbol TEXT,cutoff INTEGER,decision INTEGER,
              state TEXT,direction TEXT,version TEXT,payload TEXT,PRIMARY KEY(symbol,cutoff,state));
            CREATE TABLE IF NOT EXISTS r11_cycles(cutoff INTEGER PRIMARY KEY,finished INTEGER,
              universe INTEGER,eligible INTEGER,eligible_symbols TEXT);
            CREATE TABLE IF NOT EXISTS r11_ready(symbol TEXT,cutoff INTEGER,decision INTEGER,
              direction TEXT,entry_at INTEGER,atr REAL,complete INTEGER DEFAULT 0,
              PRIMARY KEY(symbol,cutoff));
            CREATE INDEX IF NOT EXISTS r11_pending ON r11_ready(entry_at) WHERE complete=0;
            CREATE TABLE IF NOT EXISTS r11_outcomes(symbol TEXT,cutoff INTEGER,state TEXT,
              entry REAL,gross_pct REAL,exit_at INTEGER,mfe REAL,mae REAL,
              PRIMARY KEY(symbol,cutoff));
            """)
    @contextmanager
    def db(self):
        with self.db_lock:
            db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row
            try:yield db;db.commit()
            except Exception:db.rollback();raise
            finally:db.close()
    def market(self,s,now):
        # Single cache snapshot; no extra REST or subscription.
        with self.engine.lock:
            q,t=self.engine.quotes.get(s,(None,0))
            quote=q if 0<=now-t<=10000 else None
            buckets=[self.engine.buckets.get((s,now//r11.STEP*r11.STEP-i*r11.STEP),{}) for i in (0,1)]
            depth=max(buckets,key=lambda b:b.get('depthTs') or 0)
            ts=depth.get('depthTs')
            spread=depth.get('spreadLast') if ts is not None and 0<=now-ts<=5000 and self.engine.connected.get((s,'depth'),now+1)<=ts else None
        return quote,spread
    def persist(self,db,s,old,result,cut,decision):
        if result is None:
            if old is not None:
                db.execute('INSERT OR IGNORE INTO r11_events VALUES(?,?,?,?,?,?,?)',
                           (s,cut,decision,'ENDED',old.get('direction'),r11.VERSION,'{}'))
            return
        changed=not old or any(result.get(k)!=old.get(k) for k in ('state','direction','setup','reason'))
        if changed or result['state']=='READY':
            db.execute('INSERT OR IGNORE INTO r11_events VALUES(?,?,?,?,?,?,?)',
                      (s,cut,decision,result['state'],result['direction'],r11.VERSION,json.dumps(result,allow_nan=False)))
        if result['state']=='READY':
            db.execute('INSERT OR IGNORE INTO r11_ready(symbol,cutoff,decision,direction,entry_at,atr) VALUES(?,?,?,?,?,?)',
                      (s,cut,decision,result['direction'],entry_time(decision),result['readyAtr']))
    def settle(self,db,cut):
        for e in db.execute('SELECT * FROM r11_ready WHERE complete=0 AND entry_at+900000-1<=?',(cut,)).fetchall():
            rows=self.engine.candles(e['symbol'],'1m',100,cut+1,require=False) or []
            by={int(r[6]):r for r in rows}
            seq=[by.get(e['entry_at']+i*r11.STEP-1) for i in range(1,16)]
            if all(seq):
                out=simulate(seq,e['direction'],e['atr'],15,'FIXED')
                if not out:continue
                state,entry,gross,exit_at,_,_=out
                s=1 if e['direction']=='UP' else -1
                def ret(p):return s*100*(float(p)/entry-1)
                mfe=max(0.,*(ret(r[2 if s==1 else 3]) for r in seq))
                mae=min(0.,*(ret(r[3 if s==1 else 2]) for r in seq))
            elif cut>e['entry_at']+30*r11.STEP-1:
                state,entry,gross,exit_at,mfe,mae='UNOBSERVED',None,None,None,None,None
            else:continue
            db.execute('INSERT OR IGNORE INTO r11_outcomes VALUES(?,?,?,?,?,?,?,?)',
                      (e['symbol'],e['cutoff'],state,entry,gross,exit_at,mfe,mae))
            db.execute('UPDATE r11_ready SET complete=1 WHERE symbol=? AND cutoff=?',(e['symbol'],e['cutoff']))
    def finish(self,cut):
        with self.engine.lock:universe=len(self.engine.symbols)
        with self.db() as db:
            db.execute('INSERT OR IGNORE INTO r11_cycles VALUES(?,?,?,?,?)',
                      (cut,now_ms(),universe,len(self.done),json.dumps(sorted(self.done))))
            self.settle(db,cut)
        with self.lock:self.latest={'cutoff':cut,'universe':universe,'eligible':len(self.done)}
        self.finalized=True
    def tick(self):
        now=now_ms();cut=close_at(now,r11.STEP)
        if self.cutoff!=cut:
            if self.cutoff is not None and not self.finalized:self.finish(self.cutoff)
            self.cutoff=cut;self.done=set();self.finalized=False
        if self.finalized:return
        if now-cut>r11.FRESH_MS:
            self.finish(cut);return
        if now-cut<2000:return
        with self.engine.lock:symbols=sorted(self.engine.symbols)
        prepared=[]
        for s in symbols:
            if s in self.done:continue
            receipt=self.engine.receipt(s,'1m',cut)
            if receipt is None or receipt>now:continue
            rows=self.engine.candles(s,'1m',61,cut+1)
            f=r11.features(rows or [],cut)
            if f is not None:prepared.append((s,f))
        if not prepared:return
        updates={}
        # Shared DB lock: recheck actual decision time after waiting, never label delayed data fresh.
        with self.db() as db:
            for s,f in prepared:
                decision=now_ms()
                if decision-cut>r11.FRESH_MS:break
                quote,spread=self.market(s,decision)
                with self.lock:old=self.states.get(s)
                result=r11.advance(old,f,cut,decision,quote,spread)
                self.persist(db,s,old,result,cut,decision)
                updates[s]=result
        with self.lock:
            for s,result in updates.items():
                if result is None:self.states.pop(s,None)
                else:self.states[s]=result
                self.done.add(s)
            self.states={s:v for s,v in self.states.items() if cut-v['cutoff']<=r11.WATCH_MS}
    def run(self,heartbeat=lambda:None):
        while not self.engine.stop.is_set():
            try:self.tick();self.last_error=None
            except Exception as e:self.last_error=str(e)[:200];print('R11:',self.last_error,flush=True)
            heartbeat()
            self.engine.stop.wait(1)
    def status(self):
        now=now_ms()
        with self.lock:rows=[dict(v,symbol=s) for s,v in self.states.items()];latest=dict(self.latest)
        for row in rows:
            quote,spread=self.market(row['symbol'],now)
            row['currentPrice']=quote;row['currentSpreadPct']=spread
            row['ageMs']=now-row['decisionAt']
            row['displayState']=row['state']
            if row['ageMs']>70000 or quote is None:
                row['displayState']='STALE'
            elif row['state']=='READY':
                s=1 if row['direction']=='UP' else -1
                chase=s*100*(quote/row['features']['price']-1)
                if chase>.30:row['displayState']='LATE'
                elif chase<-.15 or spread is None or spread>r11.SPREAD_CAP:row['displayState']='WAIT'
            if row.get('readyPrice') and quote is not None:
                row['movePct']=(1 if row['direction']=='UP' else -1)*100*(quote/row['readyPrice']-1)
        rows.sort(key=lambda r:({'READY':0,'MONITOR':1,'PREPARE':2,'LATE':3}.get(r['displayState'],4),-r['decisionAt'],r['symbol']))
        return {'enabled':True,'version':r11.VERSION,'preview':True,'latestCycle':latest,
                'states':rows,'lastError':self.last_error,'note':'Experimental manual watch only; R08 dashboard unchanged.'}
