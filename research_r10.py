"""R10 additive research ledger. Entry is a future minute OPEN proxy, not a fill."""
import json,sqlite3,time
from contextlib import contextmanager
from filters import r10
STEP=60000
HORIZONS=(15,30,60)
POLICIES=('FIXED','ATR_WIDE','ATR_TRAIL')
COSTS=(.10,.20,.35)
def entry_time(decision):
    return (decision//STEP+1)*STEP

def simulate(bars,direction,a,h,policy):
    """Full contiguous window required; exits at observed CLOSE, not ideal threshold."""
    if len(bars)!=h:return None
    base=float(bars[0][1]);sign=1 if direction=='UP' else -1
    if base<=0:return None
    target,stop=(max(.65,1.5*a),max(.4,a)) if policy=='FIXED' else (max(.8,2*a),max(.45,1.25*a))
    if policy=='ATR_TRAIL':target,stop=max(1.,3*a),max(.4,a)
    peak=0.;state='TIMEOUT'
    for bar in bars:
        ret=sign*100*(float(bar[4])/base-1)
        limit=-stop
        if policy=='ATR_TRAIL' and peak>=max(.5,a):limit=max(limit,peak-max(.25,.75*a))
        if ret<=limit:
            state='TRAIL' if limit>-stop else 'STOP';break
        if ret>=target:state='TARGET';break
        peak=max(peak,ret)
    return (state,base,ret,int(bar[6]),target,stop)

class ResearchR10:
    def __init__(self,path,lock):
        self.path,self.lock=str(path),lock
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS r10_meta(key TEXT PRIMARY KEY,value INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS r10_cycles(cutoff INTEGER PRIMARY KEY,decision INTEGER,universe INTEGER,observed INTEGER,fresh INTEGER,atr_ready INTEGER,regime TEXT,coverage REAL);
            CREATE TABLE IF NOT EXISTS r10_setups(id INTEGER PRIMARY KEY,symbol TEXT,source TEXT,cutoff INTEGER,decision INTEGER,entry_at INTEGER,direction TEXT,atr_pct REAL,regime TEXT,context TEXT,tags TEXT,UNIQUE(symbol,source,cutoff,direction));
            CREATE INDEX IF NOT EXISTS r10_setups_entry ON r10_setups(entry_at);
            CREATE TABLE IF NOT EXISTS r10_outcomes(setup_id INTEGER,horizon INTEGER,policy TEXT,state TEXT,entry REAL,gross_pct REAL,exit_at INTEGER,target_pct REAL,stop_pct REAL,PRIMARY KEY(setup_id,horizon,policy));
            """)
            db.execute("INSERT OR IGNORE INTO r10_meta VALUES('holdout_start',?)",(int(time.time()*1000)+7*86400000,))
    @contextmanager
    def db(self):
        with self.lock:
            db=sqlite3.connect(self.path,timeout=30);db.row_factory=sqlite3.Row
            try:yield db;db.commit()
            except Exception:db.rollback();raise
            finally:db.close()
    def insert(self,db,s,source,cut,decision,a,ctx,tags):
        if not a or a<=0:return
        for direction in ('UP','DOWN'):
            unique={(t['id'],t.get('version','unknown')):t for t in tags if t['direction']==direction}
            if unique:
                db.execute("INSERT OR IGNORE INTO r10_setups(symbol,source,cutoff,decision,entry_at,direction,atr_pct,regime,context,tags) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  (s,source,cut,decision,entry_time(decision),direction,a,ctx['regime'],json.dumps(ctx,allow_nan=False),json.dumps([{'id':i,'version':v} for i,v in sorted(unique)])))
    def record5(self,row,decision):
        cut=int(row['lastClosed5m'])
        if not 0<=decision-cut<=300000:return
        b=(row.get('researchFeatures') or {}).get('breadth') or {}
        up=b.get('upShare');btc=b.get('btcRet15')
        label='UNKNOWN' if up is None or btc is None else 'BULL' if up>=.65 and btc>=.15 else 'BEAR' if up<=.35 and btc<=-.15 else 'MIXED'
        ctx={'regime':label,'coverage':b.get('sampleCount',0)/max(1,b.get('universeSize',0)),'upShare':up,'btcRet15':btc,'lagMs':decision-cut}
        with self.db() as db:self.insert(db,row['symbol'],'5m',cut,decision,row['atr5mPct'],ctx,row.get('researchCandidates',[])+r10.tags5(row))
    def minute(self,records,engine,cutoff,observed):
        # Final actual timestamp AFTER features and cross-sectional inputs were collected.
        returns={}
        for s,rows,m,tags,base,a in records:
            if len(rows)>=16 and int(rows[-16][6])==cutoff-15*STEP and m.get('candleReceiptMs') is not None and m['candleReceiptMs']<=observed:
                returns[s]=100*(base/float(rows[-16][4])-1)
        with engine.lock:universe=len(engine.symbols)
        context=r10.regime(returns,universe)
        prepared=[]
        for s,rows,m,tags,base,a in records:
            if a and m.get('candleReceiptMs') is not None and m['candleReceiptMs']<=observed:
                extra=r10.tags1(m,engine.minute(s,cutoff-STEP,observed),rows,a,context)
                ctx=dict(context,relativeBTC=returns.get(s)-context['btcRet15'] if s in returns and 'btcRet15' in context else None)
                prepared.append((s,a,ctx,[dict(t,version=t.get('version','r09-ws-micro-v1')) for t in tags]+extra))
        decision=int(time.time()*1000)
        with self.db() as db:
            db.execute("INSERT OR IGNORE INTO r10_cycles VALUES(?,?,?,?,?,?,?,?)",(cutoff,decision,universe,len(records),len(returns),sum(bool(r[-1]) for r in records),context['regime'],context['coverage']))
            if 0<=decision-cutoff<=15000:
                for s,a,ctx,tags in prepared:self.insert(db,s,'1m',cutoff,decision,a,ctx,tags)
            self.settle(db,{r[0]:r[1] for r in records},cutoff)
    def settle(self,db,rows_by_symbol,cutoff):
        pending=db.execute("""SELECT * FROM r10_setups s WHERE entry_at<=? AND
          (SELECT COUNT(*) FROM r10_outcomes o WHERE o.setup_id=s.id)<9""",(cutoff,)).fetchall()
        for c in pending:
            bars={int(r[6]):r for r in rows_by_symbol.get(c['symbol'],[])}
            done={(x[0],x[1]) for x in db.execute('SELECT horizon,policy FROM r10_outcomes WHERE setup_id=?',(c['id'],))}
            for h in HORIZONS:
                end=c['entry_at']+h*STEP-1
                if end>cutoff:continue
                seq=[bars.get(c['entry_at']+i*STEP-1) for i in range(1,h+1)]
                for policy in POLICIES:
                    if (h,policy) in done:continue
                    if all(seq):
                        out=simulate(seq,c['direction'],c['atr_pct'],h,policy)
                    elif cutoff>end+15*STEP:out=('UNOBSERVED',None,None,None,None,None)
                    else:continue
                    if out:db.execute('INSERT OR IGNORE INTO r10_outcomes VALUES(?,?,?,?,?,?,?,?,?)',(c['id'],h,policy,*out))
    def status(self):
        with self.db() as db:
            cycle=db.execute('SELECT * FROM r10_cycles ORDER BY cutoff DESC LIMIT 1').fetchone()
            return {'enabled':True,'latestCycle':dict(cycle) if cycle else None,'setups':db.execute('SELECT COUNT(*) FROM r10_setups').fetchone()[0],'outcomes':db.execute('SELECT COUNT(*) FROM r10_outcomes').fetchone()[0],'holdoutStart':db.execute("SELECT value FROM r10_meta WHERE key='holdout_start'").fetchone()[0],'note':'Shadow only; future minute open proxy; close exits; no orders.'}
