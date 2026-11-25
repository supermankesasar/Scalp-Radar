"""Separate minute research ledger. Batch writes, exact close-time outcomes, no trades."""
import json,sqlite3,threading,time
from contextlib import contextmanager
from filters import microstructure
from stream_engine import TF,close_at
HORIZONS=(15,30,60)
class StreamResearch:
    def __init__(self,path,lock):
        self.path,self.lock=str(path),lock
        with self.db() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS ws_minute_snapshots(
              symbol TEXT,candle_time INTEGER,observed_at INTEGER,payload TEXT,
              PRIMARY KEY(symbol,candle_time));
            CREATE TABLE IF NOT EXISTS ws_candidates(
              id INTEGER PRIMARY KEY,symbol TEXT,candle_time INTEGER,observed_at INTEGER,
              filter_id TEXT,version TEXT,direction TEXT,baseline REAL,target REAL,stop REAL,score REAL,
              UNIQUE(symbol,candle_time,filter_id,version,direction));
            CREATE INDEX IF NOT EXISTS ws_pending ON ws_candidates(symbol,candle_time);
            CREATE TABLE IF NOT EXISTS ws_outcomes(
              candidate_id INTEGER,horizon INTEGER,state TEXT,endpoint_pct REAL,mfe REAL,mae REAL,evaluated_at INTEGER,
              PRIMARY KEY(candidate_id,horizon));
            """)
    @contextmanager
    def db(self):
        with self.lock:
            db=sqlite3.connect(self.path,timeout=20)
            db.row_factory=sqlite3.Row
            try:yield db;db.commit()
            except Exception:db.rollback();raise
            finally:db.close()
    def process(self,engine,cutoff,now,ema,atr,parse):
        with engine.lock:symbols=sorted(engine.symbols)
        records=[]
        for s in symbols:
            rows=engine.candles(s,'1m',100,cutoff+1,require=False)
            if not rows or int(rows[-1][6])!=cutoff:continue
            # Candles after a gap are not silently stitched for indicators.
            tail=rows[-61:]
            contiguous=len(tail)>=61 and all(int(b[6])-int(a[6])==60000 for a,b in zip(tail,tail[1:]))
            m=engine.minute(s,cutoff,now)
            a=atr(parse(tail,cutoff+1)) if contiguous else None
            tags=microstructure.evaluate(m,tail,ema) if a and 0<=now-cutoff<=15000 else []
            base=float(rows[-1][4]);atrpct=100*a/base if a else None
            records.append((s,rows,m,tags,base,atrpct))
        with self.db() as db:
            # Reuse central raw archive when enabled. No fabricated data.
            archive=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='market_observations'").fetchone()
            for s,rows,m,tags,base,a in records:
                if archive:
                    db.executemany("INSERT OR IGNORE INTO market_observations VALUES(?,?,?,?,?)",
                        [('kline_1m',s,int(r[6]),now,json.dumps(r,separators=(',',':'))) for r in rows[-3:]])
                    # Keep exact synchronized 5m candles available for breadth.
                    r5=engine.candles(s,'5m',1,cutoff+1,require=False)
                    if r5:db.execute("INSERT OR IGNORE INTO market_observations VALUES(?,?,?,?,?)",('kline_5m',s,int(r5[-1][6]),now,json.dumps(r5[-1],separators=(',',':'))))
                frozen={'micro':m,'tags':tags,'close':base,'atr1mPct':a,'lagMs':now-cutoff}
                cur=db.execute("INSERT OR IGNORE INTO ws_minute_snapshots VALUES(?,?,?,?)",(s,cutoff,now,json.dumps(frozen,allow_nan=False,separators=(',',':'))))
                if cur.rowcount and a:
                    db.executemany("INSERT OR IGNORE INTO ws_candidates(symbol,candle_time,observed_at,filter_id,version,direction,baseline,target,stop,score) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      [(s,cutoff,now,t['id'],microstructure.VERSION,t['direction'],base,max(.65,1.5*a),max(.4,a),t.get('score')) for t in tags])
                candles={int(r[6]):r for r in rows}
                pending=db.execute("""SELECT c.*,h.horizon FROM ws_candidates c CROSS JOIN
                   (SELECT 15 horizon UNION ALL SELECT 30 UNION ALL SELECT 60) h
                   WHERE c.symbol=? AND c.candle_time>=? AND c.candle_time+h.horizon*60000<=?
                   AND NOT EXISTS(SELECT 1 FROM ws_outcomes o WHERE o.candidate_id=c.id AND o.horizon=h.horizon)""",
                   (s,cutoff-75*60000,cutoff)).fetchall()
                for c in pending:
                    h=c['horizon'];end=c['candle_time']+h*60000
                    seq=[candles.get(t) for t in range(c['candle_time']+60000,end+1,60000)]
                    if not all(seq):continue
                    sign=1 if c['direction']=='UP' else -1
                    def ret(p):return sign*100*(float(p)/c['baseline']-1)
                    state='TIMEOUT'
                    for r in seq:
                        v=ret(r[4])
                        if v>=c['target']:state='TARGET';break
                        if v<=-c['stop']:state='STOP';break
                    mfe=max(0.,*(ret(r[2 if sign==1 else 3]) for r in seq))
                    mae=min(0.,*(ret(r[3 if sign==1 else 2]) for r in seq))
                    db.execute("INSERT OR IGNORE INTO ws_outcomes VALUES(?,?,?,?,?,?,?)",(c['id'],h,state,ret(seq[-1][4]),mfe,mae,now))
            for h in HORIZONS:
                db.execute("""INSERT OR IGNORE INTO ws_outcomes(candidate_id,horizon,state,evaluated_at)
                  SELECT id,?,'UNOBSERVED',? FROM ws_candidates WHERE candle_time<=?""",(h,now,cutoff-(h+15)*60000))
        return len(records)
    def summary(self):
        with self.db() as db:
            rows=db.execute("""SELECT c.filter_id,c.version,c.direction,o.horizon,COUNT(*) n,
              SUM(o.state='TARGET') targets,SUM(o.state='STOP') stops,SUM(o.state='TIMEOUT') timeouts,
              SUM(o.state='UNOBSERVED') unobserved,
              AVG(CASE o.state WHEN 'TARGET' THEN c.target-.20 WHEN 'STOP' THEN -c.stop-.20 WHEN 'TIMEOUT' THEN o.endpoint_pct-.20 END) net_proxy_pct,
              AVG((c.observed_at-c.candle_time)/1000.) latency_seconds
              FROM ws_candidates c JOIN ws_outcomes o ON c.id=o.candidate_id GROUP BY 1,2,3,4""").fetchall()
            return {'snapshots':db.execute('SELECT COUNT(*) FROM ws_minute_snapshots').fetchone()[0],
              'candidates':db.execute('SELECT COUNT(*) FROM ws_candidates').fetchone()[0],
              'comparison':[dict(r) for r in rows],
              'note':'1m candle-close simulation, not executable return. Missing outcomes are unobserved.'}
