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
            for h in HORIZONS:
                for tf in CONFIRM:
                    db.execute("""INSERT OR IGNORE INTO research_outcomes
                       (candidate_id,horizon,confirm,state,evaluated_at)
                       SELECT id,?,?,'UNOBSERVED',? FROM research_candidates
                       WHERE candle_time < ?""", (h,tf,now,now-MAX_RETRY))
            return {r[0] for r in db.execute("""SELECT DISTINCT c.symbol FROM research_candidates c
                       WHERE c.candle_time>=? AND
                       (SELECT COUNT(*) FROM research_outcomes o WHERE o.candidate_id=c.id) < 6""",(now-MAX_RETRY,))}
    def record_and_evaluate(self, row, candles, now):
        sym, t = row['symbol'], int(row['lastClosed5m'])
        tags = row.get('researchCandidates', [])
        with self.connection() as db:
            if tags:
                frozen = {k:v for k,v in row.items() if not k.startswith('_')}
                frozen['schemaVersion'] = 1
                db.execute('INSERT OR IGNORE INTO research_snapshots VALUES(?,?,?,?)',
                           (sym,t,now,json.dumps(frozen,allow_nan=False,separators=(',',':'))))
                atr = row['atr5mPct']
                for tag in tags:
                    db.execute("""INSERT OR IGNORE INTO research_candidates
                      (symbol,candle_time,filter_id,version,direction,baseline,target,stop,score)
                      VALUES(?,?,?,?,?,?,?,?,?)""",
                      (sym,t,tag['id'],tag['version'],tag['direction'],row['price'],
                       max(.65,1.5*atr),max(.4,atr),tag.get('score')))
            bars = {int(c['closeTime']):c for c in candles if int(c['closeTime']) < now}
            if not bars:
                return
            last = max(bars)
            for c in db.execute("""SELECT * FROM research_candidates c WHERE symbol=? AND candle_time<?
                         AND (SELECT COUNT(*) FROM research_outcomes o WHERE o.candidate_id=c.id)<6""",(sym,last)).fetchall():
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
    def summary(self):
        with self.connection() as db:
            rows = db.execute("""SELECT c.filter_id,c.version,o.horizon,o.confirm,o.state,COUNT(*) AS n
                      FROM research_candidates c JOIN research_outcomes o ON c.id=o.candidate_id
                      GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4,5""").fetchall()
            counts = db.execute("SELECT filter_id,version,COUNT(*) n FROM research_candidates GROUP BY 1,2").fetchall()
            return {'candidates':[dict(r) for r in counts], 'outcomes':[dict(r) for r in rows],
                    'archiveRows':db.execute('SELECT COUNT(*) FROM research_archive').fetchone()[0],
                    'note':'All candidates, not top five. Candle-close outcomes, not real execution.'}
