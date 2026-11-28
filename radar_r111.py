"""R11.1 cache-only challenger, coverage diagnostics and movement audit.
No new REST calls in decision path. Separate SQLite versioned tables.
"""
import json,sqlite3,time,threading,math
from contextlib import contextmanager
from collections import Counter
from filters import r11,r111,r10
from impulse_radar import ImpulseRadar
import os
from research_r10 import entry_time,simulate
from stream_engine import close_at
STEP=60000
FRESH=15000
MOVE=1.0  # exploratory event definition: rolling 15m close return
def ms():return int(time.time()*1000)
def pack(obj):return json.dumps(obj,separators=(',',':'),allow_nan=False)

def restore_minutes(archive,engine,symbols,now):
    """Warm existing local history; never create fake WS receipts."""
    wanted=set(symbols)
    if not wanted:return 0
    cut=close_at(now,STEP)
    grouped={}
    with archive.db() as db:
        rows=db.execute("SELECT symbol,payload FROM market_observations WHERE kind='kline_1m' AND source_ts>=? AND source_ts<=? AND received_at<=?",
                        (cut-99*STEP,cut,now)).fetchall()
    for row in rows:
        if row['symbol'] not in wanted:continue
        try:
            raw=json.loads(row['payload'])
            if int(raw[6])<now:grouped.setdefault(row['symbol'],[]).append(raw)
        except (ValueError,TypeError,IndexError,KeyError):continue
    for s,rows in grouped.items():engine.seed(s,'1m',rows,now)
    return len(grouped)

def movement(rows,cut):
    if len(rows)!=17 or any(int(r[6])!=cut-(16-i)*STEP for i,r in enumerate(rows)):return None
    try:
        p=[float(r[4]) for r in rows]
        if min(p)<=0 or not all(math.isfinite(x) for x in p):return None
        current=100*(p[-1]/p[1]-1);prior=100*(p[-2]/p[0]-1)
        return (current,prior)
    except (ValueError,TypeError,IndexError,ZeroDivisionError):return None

class RadarR111:
    def __init__(self,path,lock,engine):
        self.path,self.db_lock,self.engine=str(path),lock,engine
        self.lock=threading.RLock();self.states={};self.latest={};self.last_error=None
        self.cut=None;self.universe=[];self.prior={};self.results={};self.reasons={};self.frozen={};self.receipts={};self.finished=False
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS r111_cycles(cutoff INTEGER PRIMARY KEY,finished INTEGER,universe INTEGER,
              eligible INTEGER,eligible_symbols TEXT,reasons TEXT,regime TEXT,move_paths INTEGER);
            CREATE TABLE IF NOT EXISTS r111_events(symbol TEXT,cutoff INTEGER,decision INTEGER,state TEXT,direction TEXT,
              version TEXT,payload TEXT,PRIMARY KEY(symbol,cutoff,state));
            CREATE TABLE IF NOT EXISTS r111_ready(symbol TEXT,cutoff INTEGER,decision INTEGER,direction TEXT,entry_at INTEGER,
              atr REAL,setup TEXT,variant TEXT,complete INTEGER DEFAULT 0,PRIMARY KEY(symbol,cutoff));
            CREATE INDEX IF NOT EXISTS r111_pending ON r111_ready(entry_at) WHERE complete=0;
            CREATE TABLE IF NOT EXISTS r111_outcomes(symbol TEXT,cutoff INTEGER,state TEXT,entry REAL,gross_pct REAL,
              exit_at INTEGER,mfe REAL,mae REAL,PRIMARY KEY(symbol,cutoff));
            CREATE TABLE IF NOT EXISTS r111_moves(symbol TEXT,cutoff INTEGER,direction TEXT,ret15 REAL,window_start INTEGER,
              v1_class TEXT,v2_class TEXT,v1_lead_ms INTEGER,v2_lead_ms INTEGER,v1_coverage INTEGER,v2_coverage INTEGER,
              PRIMARY KEY(symbol,cutoff,direction));
            """)
            self.impulse=ImpulseRadar(db) if os.getenv("SCANNER_R112","0")=="1" else None
    @contextmanager
    def db(self):
        with self.db_lock:
            db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row
            try:yield db;db.commit()
            except Exception:db.rollback();raise
            finally:db.close()
    def regime(self,cut,deadline):
        returns={}
        for s in self.universe:
            receipt=self.engine.receipt(s,'1m',cut)
            if receipt is None or not 0<=receipt-cut<=FRESH or receipt>deadline:continue
            rows=self.engine.candles(s,'1m',16,cut+1)
            if not rows:continue
            try:
                a,b=float(rows[0][4]),float(rows[-1][4])
                if a>0 and b>0 and math.isfinite(a) and math.isfinite(b):returns[s]=100*(b/a-1)
            except (ValueError,TypeError,IndexError):continue
        primary=r10.regime(returns,len(self.universe))
        # Independently labelled fallback on the latest completed native 15m bar.
        # Never present it as the live rolling 15m regime.
        native={}
        for s in self.universe:
            bars=self.engine.candles(s,'15m',2,cut+1)
            if not bars:continue
            try:
                a,b=float(bars[0][4]),float(bars[1][4])
                if a>0 and b>0 and math.isfinite(a) and math.isfinite(b):native[s]=100*(b/a-1)
            except (ValueError,TypeError,IndexError):continue
        native_cut=(cut+1)//900000*900000-1
        fallback=dict(r10.regime(native,len(self.universe)),source='NATIVE_CLOSED_15M',cutoff=native_cut,ageMs=cut-native_cut)
        return dict(primary,source='ROLLING_15M_WS',cutoff=cut,nativeContext=fallback)
    def market(self,s,now,direction):
        # Side-specific best bid/ask, not a simulated fill, from existing partial depth.
        with self.engine.lock:
            book=self.engine.best_book.get(s)
            connected=self.engine.connected.get((s,'depth'))
        if book is None:return None,None,'BOOK_MISSING'
        bid,ask,ts,received=book
        if connected is None or connected>received:return None,None,'BOOK_DISCONNECTED'
        if not 0<=now-ts<=5000 or not 0<=now-received<=5000:return None,None,'BOOK_STALE'
        if not (0<bid<=ask and math.isfinite(bid) and math.isfinite(ask)):return None,None,'BOOK_INVALID'
        return (ask if direction=='UP' else bid),100*(ask-bid)/((ask+bid)/2),'BOOK_OK'
    def new_cycle(self,cut):
        self.cut=cut
        with self.engine.lock:self.universe=sorted(self.engine.symbols)
        with self.lock:self.prior=dict(self.states)
        self.results={};self.reasons={};self.frozen={};self.receipts={};self.finished=False
        if self.impulse:self.impulse.begin(cut)
    def tick(self):
        now=ms();cut=close_at(now,STEP)
        if self.cut!=cut:
            if self.cut is not None and not self.finished:self.finish()
            self.new_cycle(cut)
        if self.finished:return
        if now-cut>FRESH:self.finish();return
        if now-cut<1000:return
        if not self.universe:
            with self.engine.lock:self.universe=sorted(self.engine.symbols)
        # Only pending symbols, allow late (but still fresh) close and book retries.
        for s in self.universe:
            r111_pending=s not in self.results or self.reasons.get(s) in ('BOOK_MISSING','BOOK_DISCONNECTED','BOOK_STALE','BOOK_INVALID','NATIVE15_UNKNOWN')
            if not r111_pending and not (self.impulse and self.impulse.pending(s)):continue
            if ms()-cut>FRESH:break
            receipt=self.engine.receipt(s,'1m',cut)
            if receipt is None:self.reasons[s]='NO_WS_CLOSE';continue
            if receipt-cut>FRESH:self.reasons[s]='LATE_WS_CLOSE';continue
            if receipt>ms():self.reasons[s]='NO_WS_CLOSE';continue
            self.receipts[s]=receipt
            rows=self.engine.candles(s,'1m',61,cut+1)
            if not rows:self.reasons[s]='SEED_OR_GAP';continue
            f=self.frozen.get(s)
            if f is None or f.get('native') is None:
                base=r11.features(rows,cut)
                if base is None:self.reasons[s]='FEATURE_INVALID';continue
                ctx=r111.native_context(self.engine.candles(s,'15m',4,cut+1),
                                         self.engine.candles(s,'1h',2,cut+1),cut)
                f=r111.enrich(base,rows,ctx);self.frozen[s]=f
            decision=ms()
            if not 0<=decision-cut<=FRESH:self.reasons[s]='PROCESSING_DEADLINE';break
            if self.impulse:self.impulse.process(s,f,rows,cut,decision,self.market)
            if not r111_pending:continue
            decision=ms()
            if not 0<=decision-cut<=FRESH:break
            quote,spread,book_reason=self.market(s,decision,f['direction'])
            result=r111.advance(self.prior.get(s),f,cut,decision,quote,spread)
            # Keep the specific book reason, not a combined mystery state.
            reason=result['reason'] if result else 'NO_SETUP'
            if reason=='QUOTE_OR_SPREAD_UNKNOWN':reason=book_reason
            if result:
                result=dict(result,reason=reason,receiptMs=receipt,entryQuote=quote,spreadPct=spread)
                # An as-of contextual diagnostic is attached at cycle finish, not used as future input.
            self.results[s]=result;self.reasons[s]=reason
            with self.lock:
                if result:self.states[s]=result
                else:self.states.pop(s,None)
    def compare(self,db,table,s,di,start,cut,coverage):
        # Alert known before threshold-close; distinguish before baseline vs during window.
        row=db.execute(f"SELECT MIN(decision) FROM {table} WHERE symbol=? AND direction=? AND cutoff>=? AND cutoff<=? AND decision>=? AND decision<=?",
                       (s,di,start-15*STEP,cut,start-15*STEP,cut)).fetchone()
        d=row[0]
        if d is not None:return ('BEFORE_WINDOW' if d<=start else 'DURING_WINDOW',cut-d)
        return ('NO_READY_WITH_DATA' if coverage==15 else 'COVERAGE_GAP',None)
    def movement_audit(self,db,cut,symbols):
        start=cut-15*STEP
        def coverage(table,col):
            result=Counter()
            for row in db.execute(f"SELECT {col} FROM {table} WHERE cutoff>? AND cutoff<=?",(start,cut)):
                try:result.update(set(json.loads(row[0])))
                except (ValueError,TypeError):pass
            return result
        has_v1=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='r11_cycles'").fetchone() is not None
        c1=coverage('r11_cycles','eligible_symbols') if has_v1 else Counter()
        c2=coverage('r111_cycles','eligible_symbols')
        paths=0
        for s in symbols:
            values=movement(self.engine.candles(s,'1m',17,cut+1) or [],cut)
            if values is None:continue
            paths+=1;current,prior=values
            di='UP' if current>=MOVE and prior<MOVE else 'DOWN' if current<=-MOVE and prior>-MOVE else None
            if di is None:continue
            if db.execute("SELECT 1 FROM r111_moves WHERE symbol=? AND direction=? AND cutoff>? AND cutoff<=?",(s,di,start,cut)).fetchone():continue
            a,al=self.compare(db,'r11_ready',s,di,start,cut,c1[s]) if has_v1 else ('COVERAGE_GAP',None)
            b,bl=self.compare(db,'r111_ready',s,di,start,cut,c2[s])
            db.execute("INSERT OR IGNORE INTO r111_moves VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (s,cut,di,current,start,a,b,al,bl,c1[s],c2[s]))
        return paths
    def settle(self,db,cut):
        for e in db.execute("SELECT * FROM r111_ready WHERE complete=0 AND entry_at+900000-1<=?",(cut,)).fetchall():
            rows=self.engine.candles(e['symbol'],'1m',100,cut+1,require=False) or []
            by={int(r[6]):r for r in rows}
            seq=[by.get(e['entry_at']+i*STEP-1) for i in range(1,16)]
            if all(seq):
                out=simulate(seq,e['direction'],e['atr'],15,'FIXED')
                if not out:continue
                state,entry,gross,exit_at,_,_=out
                sign=1 if e['direction']=='UP' else -1
                def ret(x):return sign*100*(float(x)/entry-1)
                mfe=max(0.,*(ret(r[2 if sign==1 else 3]) for r in seq))
                mae=min(0.,*(ret(r[3 if sign==1 else 2]) for r in seq))
            elif cut>e['entry_at']+30*STEP-1:state,entry,gross,exit_at,mfe,mae='UNOBSERVED',None,None,None,None,None
            else:continue
            db.execute("INSERT OR IGNORE INTO r111_outcomes VALUES(?,?,?,?,?,?,?,?)",
                       (e['symbol'],e['cutoff'],state,entry,gross,exit_at,mfe,mae))
            db.execute("UPDATE r111_ready SET complete=1 WHERE symbol=? AND cutoff=?",(e['symbol'],e['cutoff']))
    def finish(self):
        cut=self.cut
        # Decisions frozen before deadline; storage and movement audit happen after.
        eligible=sorted(self.results)
        diagnostics={}
        for s in self.universe:
            reason=self.reasons.get(s,'PROCESSING_DEADLINE')
            # Reclassify previously absent late receipts, but do not turn them into decisions.
            receipt=self.engine.receipt(s,'1m',cut)
            if reason=='NO_WS_CLOSE' and receipt is not None:reason='LATE_WS_CLOSE' if receipt-cut>FRESH else 'PROCESSING_DEADLINE'
            diagnostics.setdefault(reason,[]).append(s)
        regime=self.regime(cut,cut+FRESH)
        with self.db() as db:
            for s,result in self.results.items():
                old=self.prior.get(s)
                if not result:
                    if old:db.execute("INSERT OR IGNORE INTO r111_events VALUES(?,?,?,?,?,?,?)",(s,cut,cut+FRESH,'ENDED',old.get('direction'),r111.VERSION,'{}'))
                    continue
                if result['state']=='READY' or not old or any(old.get(k)!=result.get(k) for k in ('state','direction','setup','reason')):
                    db.execute("INSERT OR IGNORE INTO r111_events VALUES(?,?,?,?,?,?,?)",
                               (s,cut,result['decisionAt'],result['state'],result['direction'],r111.VERSION,pack(result)))
                if result['state']=='READY':
                    db.execute("INSERT OR IGNORE INTO r111_ready(symbol,cutoff,decision,direction,entry_at,atr,setup,variant) VALUES(?,?,?,?,?,?,?,?)",
                               (s,cut,result['decisionAt'],result['direction'],entry_time(result['decisionAt']),result['readyAtr'],result['setup'],result['features']['entryVariant']))
            db.execute("INSERT OR IGNORE INTO r111_cycles VALUES(?,?,?,?,?,?,?,?)",
                       (cut,ms(),len(self.universe),len(eligible),pack(eligible),pack(diagnostics),pack(regime),None))
            # Give v1 one full minute to commit its same-cutoff coverage/results.
            # Audit previous frozen universe(s), not today's changed symbol set.
            last_audit=None
            pending=db.execute("SELECT cutoff,reasons FROM r111_cycles WHERE move_paths IS NULL AND cutoff<? ORDER BY cutoff LIMIT 3",(cut,)).fetchall()
            for cycle in pending:
                old_cut=cycle['cutoff'];old_symbols=sorted({s for group in json.loads(cycle['reasons']).values() for s in group})
                paths=self.movement_audit(db,old_cut,old_symbols)
                db.execute("UPDATE r111_cycles SET move_paths=? WHERE cutoff=?",(paths,old_cut))
                last_audit={'cutoff':old_cut,'paths':paths,'universe':len(old_symbols)}
            self.settle(db,cut)
            if self.impulse:self.impulse.persist(db,self.engine,cut,len(self.universe))
        with self.lock:
            self.states={s:v for s,v in self.states.items() if cut-v['cutoff']<=r11.WATCH_MS}
            self.latest={'cutoff':cut,'universe':len(self.universe),'eligible':len(eligible),
                         'reasons':{k:len(v) for k,v in diagnostics.items()},'regime':regime,'lastMovementAudit':last_audit}
        self.finished=True
    def run(self,heartbeat=lambda:None):
        while not self.engine.stop.is_set():
            try:self.tick();self.last_error=None
            except Exception as e:self.last_error=str(e)[:200];print('R11.1:',self.last_error,flush=True)
            heartbeat()
            self.engine.stop.wait(.5)
    def status(self):
        now=ms()
        with self.lock:rows=[dict(v,symbol=s) for s,v in self.states.items()];latest=dict(self.latest)
        for row in rows:
            quote,spread,reason=self.market(row['symbol'],now,row.get('direction'))
            row['currentEntryQuote']=quote;row['currentSpreadPct']=spread;row['ageMs']=now-row['decisionAt']
            row['displayState']=row['state']
            if row['ageMs']>70000:row['displayState']='STALE'
            elif row['state']=='READY':
                if quote is None:row['displayState']='WAIT'
                else:
                    sign=1 if row['direction']=='UP' else -1
                    chase=sign*100*(quote/row['features']['price']-1)
                    if chase>.30 or sign*100*(quote/row['anchor']-1)>max(.30,1.5*row['readyAtr']):row['displayState']='LATE'
                    elif chase<-.15 or spread>r11.SPREAD_CAP:row['displayState']='WAIT'
        rows.sort(key=lambda r:({'READY':0,'MONITOR':1,'PREPARE':2,'LATE':3}.get(r['displayState'],4),-r['decisionAt'],r['symbol']))
        return {'enabled':True,'version':r111.VERSION,'preview':True,'latestCycle':latest,'states':rows,'lastError':self.last_error}
    def impulse_status(self):
        return self.impulse.status(ms(),self.market) if self.impulse else {'enabled':False}
    def impulse_report(self):
        if not self.impulse:return {'enabled':False}
        with self.db() as db:return dict(self.impulse.report(db),enabled=True)
    def report(self):
        with self.db() as db:
            outcomes=[dict(r) for r in db.execute("""SELECT r.setup,r.variant,COUNT(*) ready,
              SUM(o.state IS NOT NULL) settled,SUM(o.state='UNOBSERVED') unobserved,
              SUM(o.state='TARGET') targets,SUM(o.state='STOP') stops,AVG(o.gross_pct) gross,
              AVG(o.gross_pct-.10) net010,AVG(o.gross_pct-.20) net020,AVG(o.gross_pct-.35) net035
              FROM r111_ready r LEFT JOIN r111_outcomes o USING(symbol,cutoff) GROUP BY 1,2""")]
            moves=[dict(r) for r in db.execute("SELECT v1_class,v2_class,COUNT(*) n,AVG(v1_lead_ms) v1LeadMs,AVG(v2_lead_ms) v2LeadMs FROM r111_moves GROUP BY 1,2")]
            coverage=dict(db.execute("SELECT COUNT(*) cycles,COUNT(move_paths) auditedCycles,AVG(1.0*eligible/NULLIF(universe,0)) eligibleShare,AVG(1.0*move_paths/NULLIF(universe,0)) movePathShare FROM r111_cycles").fetchone())
        return {'version':r111.VERSION,'coverage':coverage,'outcomes':outcomes,'movementComparison':moves,
                'note':'Rolling 15m threshold crossings, not independent trades or known onset. Lead to threshold close; missing paths excluded; v1/v2 data definitions differ.'}
