"""Central additive SQLite ledger, independent of UI ranking and production events.
No network I/O; append-only snapshots/outcomes; missing data is not a failed signal.
"""
import json
import sqlite3
from contextlib import contextmanager

STEP = 300000
HORIZONS = (15, 30, 60)
CONFIRM = (5, 15)
MAX_RETRY = 24 * 3600000

class ResearchHistory:
    def __init__(self, path, lock):
        self.path, self.lock = str(path), lock
        with self.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS research_snapshots (
              symbol TEXT NOT NULL, candle_time INTEGER NOT NULL,
              recorded_at INTEGER NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(symbol,candle_time));
            CREATE TABLE IF NOT EXISTS research_candidates (
              id INTEGER PRIMARY KEY, symbol TEXT NOT NULL, candle_time INTEGER NOT NULL,
              filter_id TEXT NOT NULL, version TEXT NOT NULL, direction TEXT NOT NULL,
              baseline REAL NOT NULL, target REAL NOT NULL, stop REAL NOT NULL, score REAL,
              UNIQUE(symbol,candle_time,filter_id,version,direction));
            CREATE INDEX IF NOT EXISTS research_by_symbol ON research_candidates(symbol,candle_time);
            CREATE TABLE IF NOT EXISTS research_outcomes (
              candidate_id INTEGER NOT NULL, horizon INTEGER NOT NULL, confirm INTEGER NOT NULL,
              state TEXT NOT NULL, target_time INTEGER, stop_time INTEGER,
              endpoint_pct REAL, mfe REAL, mae REAL, evaluated_at INTEGER NOT NULL,
              PRIMARY KEY(candidate_id,horizon,confirm));
            CREATE TABLE IF NOT EXISTS research_archive (
              run_id TEXT NOT NULL, batch TEXT NOT NULL, symbol TEXT NOT NULL,
              candle_time INTEGER NOT NULL, direction TEXT NOT NULL, payload TEXT NOT NULL,
              PRIMARY KEY(run_id,batch,symbol,candle_time,direction));
            """)
            if 'observed_at' not in {r['name'] for r in db.execute('PRAGMA table_info(research_candidates)')}:
                db.execute('ALTER TABLE research_candidates ADD COLUMN observed_at INTEGER')
            if 'complete' not in {r['name'] for r in db.execute('PRAGMA table_info(research_candidates)')}:
                db.execute('ALTER TABLE research_candidates ADD COLUMN complete INTEGER NOT NULL DEFAULT 0')
                db.execute('UPDATE research_candidates SET complete=1 WHERE (SELECT COUNT(*) FROM research_outcomes WHERE candidate_id=research_candidates.id)=6')
            db.execute('CREATE INDEX IF NOT EXISTS research_pending_age ON research_candidates(candle_time) WHERE complete=0')
            db.execute('CREATE INDEX IF NOT EXISTS research_pending_symbol ON research_candidates(symbol,candle_time) WHERE complete=0')
    @contextmanager
    def connection(self):
        with self.lock:
            db = sqlite3.connect(self.path, timeout=15)
            db.row_factory = sqlite3.Row
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally:
                db.close()

    def pending_symbols(self, now):
        with self.connection() as db:
            # Finalize aged missing evaluations explicitly; never count them as stop.
            expired=[r[0] for r in db.execute('SELECT id FROM research_candidates WHERE complete=0 AND candle_time<? ORDER BY candle_time LIMIT 1000',(now-MAX_RETRY,))]
            db.executemany("INSERT OR IGNORE INTO research_outcomes(candidate_id,horizon,confirm,state,evaluated_at) VALUES(?,?,?,'UNOBSERVED',?)",((i,h,tf,now) for i in expired for h in HORIZONS for tf in CONFIRM))
            db.executemany('UPDATE research_candidates SET complete=1 WHERE id=?',((i,) for i in expired))
            return {r[0] for r in db.execute('SELECT DISTINCT symbol FROM research_candidates WHERE complete=0 AND candle_time>=?',(now-MAX_RETRY,))}
    def record_and_evaluate(self, row, candles, now):
        sym, t = row['symbol'], int(row['lastClosed5m'])
        tags = row.get('researchCandidates', [])
        with self.connection() as db:
            frozen = {k:v for k,v in row.items() if not k.startswith('_')}
            frozen['schemaVersion'] = 3
            db.execute('INSERT OR IGNORE INTO research_snapshots VALUES(?,?,?,?)',
                       (sym,t,now,json.dumps(frozen,allow_nan=False,separators=(',',':'))))
            if tags:
                atr = row['atr5mPct']
                for tag in tags:
                    db.execute("""INSERT OR IGNORE INTO research_candidates
                      (symbol,candle_time,filter_id,version,direction,baseline,target,stop,score,observed_at)
                      VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      (sym,t,tag['id'],tag['version'],tag['direction'],row['price'],
                       max(.65,1.5*atr),max(.4,atr),tag.get('score'),now))
            bars = {int(c['closeTime']):c for c in candles if int(c['closeTime']) < now}
            if not bars:
                return
            last = max(bars)
            for c in db.execute("""SELECT * FROM research_candidates c WHERE complete=0 AND symbol=? AND candle_time<?""",(sym,last)).fetchall():
                sign = 1 if c['direction']=='UP' else -1
                base = c['baseline']
                signed = lambda p: sign*100*(p/base-1)
                for h in HORIZONS:
                    n = h//5
                    times = [c['candle_time']+i*STEP for i in range(1,n+1)]
                    if times[-1] > last or not all(x in bars for x in times):
                        continue
                    seq = [bars[x] for x in times]
                    endpoint = signed(seq[-1]['close'])
                    mfe = max(0.,*(signed(x['high'] if sign==1 else x['low']) for x in seq))
                    mae = min(0.,*(signed(x['low'] if sign==1 else x['high']) for x in seq))
                    for tf in CONFIRM:
                        state, target_t, stop_t = 'TIMEOUT', None, None
                        for bt,bar in zip(times,seq):
                            if (bt+1) % (tf*60000):
                                continue
                            ret = signed(bar['close'])
                            if ret >= c['target']:
                                state,target_t = 'TARGET',bt
                                break
                            if ret <= -c['stop']:
                                state,stop_t = 'STOP',bt
                                break
                        db.execute("""INSERT OR IGNORE INTO research_outcomes
                            VALUES(?,?,?,?,?,?,?,?,?,?)""",(c['id'],h,tf,state,target_t,stop_t,endpoint,mfe,mae,now))
                db.execute('UPDATE research_candidates SET complete=1 WHERE id=? AND (SELECT COUNT(*) FROM research_outcomes WHERE candidate_id=?)=6',(c['id'],c['id']))
    def summary(self):
        with self.connection() as db:
            rows = db.execute("""SELECT c.filter_id,c.version,o.horizon,o.confirm,o.state,COUNT(*) AS n
                      FROM research_candidates c JOIN research_outcomes o ON c.id=o.candidate_id
                      GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4,5""").fetchall()
            counts = db.execute("SELECT filter_id,version,COUNT(*) n FROM research_candidates GROUP BY 1,2").fetchall()
            comparison=db.execute("""SELECT c.filter_id,c.version,c.direction,o.horizon,o.confirm,COUNT(*) n,
                 SUM(o.state='TARGET') targets,SUM(o.state='STOP') stops,SUM(o.state='TIMEOUT') timeouts,
                 AVG(CASE o.state WHEN 'TARGET' THEN c.target-.20 WHEN 'STOP' THEN -c.stop-.20 WHEN 'TIMEOUT' THEN o.endpoint_pct-.20 END) net_proxy_pct,
                 AVG((c.observed_at-c.candle_time)/1000.0) latency_seconds
                 FROM research_candidates c JOIN research_outcomes o ON o.candidate_id=c.id GROUP BY 1,2,3,4,5""").fetchall()
            return {'candidates':[dict(r) for r in counts], 'outcomes':[dict(r) for r in rows], 'comparison':[dict(r) for r in comparison],
                    'archiveRows':db.execute('SELECT COUNT(*) FROM research_archive').fetchone()[0],
                    'note':'All candidates, not top five. Candle-close outcomes, not real execution.'}
