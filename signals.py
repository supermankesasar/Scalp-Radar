"""Durable signal journeys; never infer reached status from market movers without a prior signal.
All prices come from CLOSED Binance futures 5m candles. SQLite stores events and last snapshots.
"""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

PENDING_MS = 12 * 3600_000
REACHED_MS = 24 * 3600_000
RECENT_COOLDOWN_MS = 24 * 3600_000
MAX_ARCHIVE_MS = 30 * 24 * 3600_000
MAX_ROWS_AGE_MS = 36 * 3600_000

class SignalStore:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self._conn() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                direction TEXT NOT NULL CHECK(direction IN ('UP','DOWN')),
                status TEXT NOT NULL CHECK(status IN ('PENDING','REACHED','EXPIRED')),
                started_at INTEGER NOT NULL,
                baseline_time INTEGER NOT NULL,
                baseline_price REAL NOT NULL,
                trigger_pct REAL NOT NULL,
                initial_score INTEGER NOT NULL,
                confirmed_at INTEGER,
                last_price REAL NOT NULL,
                last_seen INTEGER NOT NULL,
                peak_close_pct REAL NOT NULL DEFAULT 0,
                peak_wick_pct REAL NOT NULL DEFAULT 0,
                last_score INTEGER NOT NULL,
                setup_active INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol,direction,started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_status ON events(status,started_at);
            CREATE TABLE IF NOT EXISTS last_rows(
                symbol TEXT PRIMARY KEY,
                updated_at INTEGER NOT NULL,
                data TEXT NOT NULL
            );
            ''')

    @contextmanager
    def _conn(self):
        conn=sqlite3.connect(self.path, timeout=15)
        conn.row_factory=sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def _direction_change(direction, base, current):
        return 100 * ((current/base) - 1) * (1 if direction=='UP' else -1)

    @staticmethod
    def _public(event):
        e=dict(event)
        delta=SignalStore._direction_change(e['direction'],e['baseline_price'],e['last_price'])
        return {
            'id':e['id'],'direction':e['direction'],'status':e['status'],
            'startedAt':e['started_at'],'confirmedAt':e['confirmed_at'],
            'baselineTime':e['baseline_time'], 'baselinePrice':e['baseline_price'],
            'lastPrice':e['last_price'],'lastSeen':e['last_seen'],
            'currentPct':round(delta,4),
            'currentMarketPct':round(100*(e['last_price']/e['baseline_price']-1),4),
            'peakMarketPct':round(e['peak_close_pct']*(1 if e['direction']=='UP' else -1),4),
            'peakClosePct':round(e['peak_close_pct'],4),
            'peakWickPct':round(e['peak_wick_pct'],4),
            'triggerPct':round(e['trigger_pct'],4),'initialScore':e['initial_score'],
            'lastScore':e['last_score'],'setupActive':bool(e['setup_active'])
        }

    def _live_events(self, db, symbol, now_ms):
        return db.execute('''SELECT * FROM events WHERE symbol=? AND (
            (status='PENDING' AND started_at>=?) OR
            (status='REACHED' AND confirmed_at>=?)) ORDER BY started_at DESC''',
            (symbol,now_ms-PENDING_MS,now_ms-REACHED_MS)).fetchall()

    def _categories(self, events):
        found=[]
        for e in events:
            if e['status']=='PENDING':
                cat='POTENSI_NAIK' if e['direction']=='UP' else 'POTENSI_TURUN'
            elif e['status']=='REACHED':
                cat='SUDAH_NAIK' if e['direction']=='UP' else 'SUDAH_TURUN'
            else:continue
            if cat not in found:found.append(cat)
        return found

    def active_symbols(self, now_ms=None):
        now_ms=now_ms or int(time.time()*1000)
        with self.lock,self._conn() as db:
            return {r[0] for r in db.execute('''SELECT DISTINCT symbol FROM events WHERE
                (status='PENDING' AND started_at>=?) OR
                (status='REACHED' AND confirmed_at>=?)''',
                (now_ms-PENDING_MS,now_ms-REACHED_MS))}

    def refresh(self, row, candles, now_ms=None):
        """Progress previous events, optionally create new potential events, return row with multiple categories.

        `candles` must be closed chronological 5m candles, each with closeTime, close, high, low.
        Events can be reached only by subsequent CLOSED candle CLOSEs, never by a wick alone.
        """
        now_ms=now_ms or int(time.time()*1000)
        symbol=row['symbol']
        last_close=row['price']
        last_bar_time=row['lastClosed5m']
        if not candles or candles[-1]['closeTime']!=last_bar_time:
            raise ValueError('Perjalanan sinyal harus memakai candle 5m tertutup yang cocok')
        with self.lock,self._conn() as db:
            db.execute("UPDATE events SET status='EXPIRED' WHERE status='PENDING' AND started_at<?",(now_ms-PENDING_MS,))
            # Re-evaluate open and recently confirmed events even when today's technical signal has reversed.
            for e in self._live_events(db,symbol,now_ms):
                future=[c for c in candles if c['closeTime']>e['baseline_time']]
                direction=e['direction'];base=e['baseline_price']
                def sign_pct(p):return self._direction_change(direction,base,p)
                peak_close=max([e['peak_close_pct']]+[sign_pct(c['close']) for c in future])
                peak_wick=max([e['peak_wick_pct']]+[sign_pct(c['high' if direction=='UP' else 'low']) for c in future])
                confirmed=e['confirmed_at']
                status=e['status']
                if status=='PENDING':
                    for c in future:
                        if sign_pct(c['close'])>=e['trigger_pct']:
                            # Only outcomes within the active 12h signal lifetime count.
                            if c['closeTime']<=e['started_at']+PENDING_MS:
                                confirmed=c['closeTime'];status='REACHED'
                            break
                active=bool(row['potentialUp'] if direction=='UP' else row['potentialDown'])
                score=row['longScore'] if direction=='UP' else row['shortScore']
                db.execute('''UPDATE events SET status=?,confirmed_at=?,last_price=?,last_seen=?,
                    peak_close_pct=?,peak_wick_pct=?,last_score=?,setup_active=? WHERE id=?''',
                    (status,confirmed,last_close,now_ms,peak_close,peak_wick,score,int(active),e['id']))
            # New signal starts at the latest closed candle; no same-candle movement can count as outcome.
            # One fresh event per direction per 24h prevents repeated alert spam.
            for direction,valid in [('UP',row['potentialUp']),('DOWN',row['potentialDown'])]:
                if not valid:continue
                prior=db.execute('''SELECT id FROM events WHERE symbol=? AND direction=? AND started_at>=?
                                   ORDER BY started_at DESC LIMIT 1''',
                                (symbol,direction,now_ms-RECENT_COOLDOWN_MS)).fetchone()
                if prior:continue
                score=row['longScore'] if direction=='UP' else row['shortScore']
                trigger=max(0.65,1.5*row['atr5mPct'])
                db.execute('''INSERT INTO events(symbol,direction,status,started_at,baseline_time,
                    baseline_price,trigger_pct,initial_score,last_price,last_seen,last_score,setup_active)
                    VALUES(?,?, 'PENDING',?,?,?,?,?,?,?,?,1)''',
                    (symbol,direction,now_ms,last_bar_time,last_close,trigger,int(score),last_close,now_ms,int(score)))
            entries=[self._public(e) for e in self._live_events(db,symbol,now_ms)]
            row=dict(row)
            row.pop('_recent5m',None)
            row['journeys']=entries
            row['categories']=self._categories(entries)
            row['category']=row['categories'][0] if row['categories'] else 'NETRAL'
            row['score']=max([row['longScore'],row['shortScore']]+[e['initialScore'] for e in entries])
            row['updatedAt']=now_ms
            db.execute('INSERT OR REPLACE INTO last_rows(symbol,updated_at,data) VALUES(?,?,?)',
                       (symbol,now_ms,json.dumps(row,allow_nan=False)))
            # Garbage-collect old records while retaining 30 days for audit/debug.
            db.execute('DELETE FROM events WHERE started_at<?',(now_ms-MAX_ARCHIVE_MS,))
            db.execute('DELETE FROM last_rows WHERE updated_at<?',(now_ms-MAX_ROWS_AGE_MS,))
        return row

    def latest_rows(self, age_ms=MAX_ROWS_AGE_MS, now_ms=None):
        now_ms=now_ms or int(time.time()*1000)
        with self.lock,self._conn() as db:
            db.execute("UPDATE events SET status='EXPIRED' WHERE status='PENDING' AND started_at<?",(now_ms-PENDING_MS,))
            results=db.execute('SELECT data FROM last_rows WHERE updated_at>=?',(now_ms-age_ms,)).fetchall()
            out=[]
            for record in results:
                row=json.loads(record[0])
                events=[self._public(e) for e in self._live_events(db,row['symbol'],now_ms)]
                row['journeys']=events
                row['categories']=self._categories(events)
                row['category']=row['categories'][0] if row['categories'] else 'NETRAL'
                out.append(row)
            return out

    def audit_events(self, limit=100):
        with self.lock,self._conn() as db:
            return [self._public(r) for r in db.execute('SELECT * FROM events ORDER BY started_at DESC LIMIT ?', (limit,))]