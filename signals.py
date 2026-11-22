"""Scalp Radar v0.5 signal journey engine.

Five active opportunities maximum, across both directions. A result is confirmed only
by a subsequent CLOSED 5m candle. Live price is for freshness, not target execution.
Existing v0.4 SQLite files are migrated in place without losing events.
"""
import json
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path

PENDING_MS = 15 * 60_000
REACHED_MS = 6 * 3_600_000
RECENT_COOLDOWN_MS = 60 * 60_000
MAX_ARCHIVE_MS = 30 * 24 * 3_600_000
MAX_ROWS_AGE_MS = 36 * 3_600_000
ACTIVE_LIMIT = 5
ROTATION_MARGIN = 1


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
                setup_active INTEGER NOT NULL DEFAULT 1,
                stop_pct REAL NOT NULL DEFAULT 0.40,
                ended_at INTEGER,
                end_reason TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_events_symbol ON events(symbol,direction,started_at DESC);
            CREATE INDEX IF NOT EXISTS idx_events_status ON events(status,started_at);
            CREATE TABLE IF NOT EXISTS last_rows(
                symbol TEXT PRIMARY KEY,
                updated_at INTEGER NOT NULL,
                data TEXT NOT NULL
            );
            ''')
            fields = {r['name'] for r in db.execute('PRAGMA table_info(events)')}
            for name, definition in (
                ('stop_pct', 'REAL NOT NULL DEFAULT 0.40'),
                ('ended_at', 'INTEGER'),
                ('end_reason', 'TEXT'),
            ):
                if name not in fields:
                    db.execute('ALTER TABLE events ADD COLUMN %s %s' % (name, definition))
            # An existing v0.4 DB may contain more than five pending events.
            # Preserve all as audit, retain only five active by ranking.
            now = int(time.time()*1000)
            live = db.execute('''SELECT id FROM events WHERE status='PENDING'
                     AND started_at>=? ORDER BY last_score DESC,started_at DESC''',
                     (now-PENDING_MS,)).fetchall()
            for old in live[ACTIVE_LIMIT:]:
                db.execute('''UPDATE events SET status='EXPIRED', ended_at=?,
                            end_reason='MIGRATION_TOP5' WHERE id=?''',
                           (now,old['id']))

    @contextmanager
    def _conn(self):
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

    @staticmethod
    def _signed(direction, base, price):
        return (price / base - 1) * 100 * (1 if direction == 'UP' else -1)

    @staticmethod
    def _public(entry):
        e = dict(entry)
        signed = SignalStore._signed(e['direction'], e['baseline_price'], e['last_price'])
        sign = 1 if e['direction'] == 'UP' else -1
        return {
            'id': e['id'], 'direction': e['direction'], 'status': e['status'],
            'startedAt': e['started_at'], 'baselineTime': e['baseline_time'],
            'confirmedAt': e['confirmed_at'], 'endedAt': e['ended_at'],
            'endReason': e['end_reason'], 'baselinePrice': e['baseline_price'],
            'lastPrice': e['last_price'], 'lastSeen': e['last_seen'],
            'currentPct': round(signed, 4), 'currentMarketPct': round(signed * sign, 4),
            'peakMarketPct': round(e['peak_close_pct'] * sign, 4),
            'peakClosePct': round(e['peak_close_pct'], 4),
            'peakWickPct': round(e['peak_wick_pct'], 4),
            'triggerPct': round(e['trigger_pct'], 4),
            'stopPct': round(e['stop_pct'], 4),
            'initialScore': e['initial_score'], 'lastScore': e['last_score'],
            'setupActive': bool(e['setup_active']),
            'symbol': e['symbol'],
        }

    @staticmethod
    def _categories(events):
        result = []
        for e in events:
            category = ('POTENSI_' if e['status'] == 'PENDING' else 'SUDAH_') + ('NAIK' if e['direction'] == 'UP' else 'TURUN')
            if e['status'] not in ('PENDING', 'REACHED'):
                continue
            if category not in result:
                result.append(category)
        return result

    def _expire_unobserved(self, db, now):
        # If no fresh candles were observed, mark TIMEOUT (not an assumed loss).
        db.execute("""UPDATE events SET status='EXPIRED', ended_at=?, end_reason='TIMEOUT_UNOBSERVED'
                      WHERE status='PENDING' AND started_at<?""", (now, now - PENDING_MS))

    def _live_events(self, db, symbol, now):
        return db.execute('''SELECT * FROM events WHERE symbol=? AND (
            (status='PENDING' AND started_at>=?) OR
            (status='REACHED' AND confirmed_at>=?)) ORDER BY started_at DESC''',
            (symbol, now-PENDING_MS, now-REACHED_MS)).fetchall()

    def active_symbols(self, now_ms=None):
        now = int(time.time()*1000) if now_ms is None else now_ms
        with self.lock, self._conn() as db:
            self._expire_unobserved(db, now)
            return {r[0] for r in db.execute('''SELECT DISTINCT symbol FROM events WHERE
               (status='PENDING' AND started_at>=?) OR
               (status='REACHED' AND confirmed_at>=?)''',
               (now-PENDING_MS, now-REACHED_MS))}

    def watch_symbols(self, max_symbols=20, now_ms=None):
        """Prioritize active (max 5) plus recently reached for light quote monitoring."""
        now = int(time.time()*1000) if now_ms is None else now_ms
        with self.lock, self._conn() as db:
            self._expire_unobserved(db, now)
            pending = [r[0] for r in db.execute('''SELECT DISTINCT symbol FROM events
                WHERE status='PENDING' AND started_at>=?
                ORDER BY started_at DESC''',(now-PENDING_MS,))]
            reached = [r[0] for r in db.execute('''SELECT symbol FROM events WHERE
                status='REACHED' AND confirmed_at>=? ORDER BY confirmed_at DESC''',
                (now-REACHED_MS,))]
            return list(dict.fromkeys(pending+reached))[:max_symbols]

    def active_pending(self, now_ms=None):
        now = int(time.time()*1000) if now_ms is None else now_ms
        with self.lock, self._conn() as db:
            self._expire_unobserved(db, now)
            return [self._public(r) for r in db.execute('''SELECT * FROM events WHERE status='PENDING'
                     AND started_at>=? ORDER BY last_score DESC, started_at DESC''', (now-PENDING_MS,))]

    def _progress(self, db, symbol, candles, price, now, current=None):
        """Progress pending/reached events, using closed candles only for outcomes.

        If there is a data gap, we cannot invent an outcome. A TIMEOUT_UNOBSERVED
        is explicitly distinct from a failure and remains available in the audit.
        """
        for e in db.execute("""SELECT * FROM events WHERE symbol=? AND (status='PENDING' OR
                              (status='REACHED' AND confirmed_at>=?)) ORDER BY started_at""",
                            (symbol, now-REACHED_MS)).fetchall():
            status = e['status']
            future = [c for c in candles if c['closeTime'] > e['baseline_time']]
            change = lambda px: self._signed(e['direction'], e['baseline_price'], px)
            peak_close = max([e['peak_close_pct']]+[change(c['close']) for c in future])
            peak_wick = max([e['peak_wick_pct']]+[change(c['high'] if e['direction']=='UP' else c['low']) for c in future])
            confirmed_at, ended_at, end_reason = e['confirmed_at'], e['ended_at'], e['end_reason']
            if status == 'PENDING':
                for c in future:
                    if c['closeTime'] > e['started_at'] + PENDING_MS:
                        break
                    delta = change(c['close'])
                    if delta >= e['trigger_pct']:
                        status, confirmed_at, end_reason = 'REACHED', c['closeTime'], 'TARGET_REACHED'
                        break
                    if delta <= -e['stop_pct']:
                        status, ended_at, end_reason = 'EXPIRED', c['closeTime'], 'STOP_HIT'
                        break
                if status == 'PENDING' and now >= e['started_at'] + PENDING_MS:
                    status, ended_at, end_reason = 'EXPIRED', now, 'TIMEOUT'
            active = e['setup_active'] if not current else (current['potentialUp'] if e['direction']=='UP' else current['potentialDown'])
            score = e['last_score'] if not current else (current['longScore'] if e['direction']=='UP' else current['shortScore'])
            db.execute('''UPDATE events SET status=?,confirmed_at=?,ended_at=?,end_reason=?,
                last_price=?,last_seen=?,peak_close_pct=?,peak_wick_pct=?,last_score=?,setup_active=? WHERE id=?''',
                (status,confirmed_at,ended_at,end_reason,price,now,peak_close,peak_wick,int(score),int(bool(active)),e['id']))

    def _refresh_payload(self, db, row, now, preserve_technical=False):
        events = [self._public(e) for e in self._live_events(db, row['symbol'], now)]
        row = dict(row)
        row.pop('_recent5m', None)
        row['journeys'] = events
        row['categories'] = self._categories(events)
        row['category'] = row['categories'][0] if row['categories'] else 'NETRAL'
        row['score'] = max([row.get('longScore',0), row.get('shortScore',0)] + [e['initialScore'] for e in events])
        if not preserve_technical:
            row['updatedAt'] = now
            db.execute('''INSERT OR REPLACE INTO last_rows(symbol,updated_at,data) VALUES(?,?,?)''',
                       (row['symbol'],now,json.dumps(row,allow_nan=False)))
        else:
            db.execute('UPDATE last_rows SET data=? WHERE symbol=?', (json.dumps(row,allow_nan=False), row['symbol']))
        return row

    def refresh(self, row, candles, now_ms=None, allow_new=True):
        """Refresh candle outcomes; allow_new=False performs observation only."""
        now = int(time.time()*1000) if now_ms is None else now_ms
        row = dict(row)
        if not candles or candles[-1]['closeTime'] != row['lastClosed5m']:
            raise ValueError('Data harus memakai candle 5m tertutup yang cocok')
        with self.lock, self._conn() as db:
            self._progress(db, row['symbol'], candles, row['price'], now, row)
            if allow_new:
                self._create_events(db, row, now)
            self._expire_unobserved(db, now)
            payload = self._refresh_payload(db, row, now)
            db.execute('DELETE FROM events WHERE started_at<?',(now-MAX_ARCHIVE_MS,))
            db.execute('DELETE FROM last_rows WHERE updated_at<?',(now-MAX_ROWS_AGE_MS,))
            return payload

    def _create_events(self, db, row, now):
        pending = db.execute("SELECT COUNT(*) FROM events WHERE status='PENDING' AND started_at>=?", (now-PENDING_MS,)).fetchone()[0]
        for direction, valid in (('UP',row.get('potentialUp')),('DOWN',row.get('potentialDown'))):
            if not valid or pending >= ACTIVE_LIMIT:
                continue
            prior = db.execute('''SELECT id FROM events WHERE symbol=? AND direction=? AND started_at>=?
                                  LIMIT 1''',(row['symbol'],direction,now-RECENT_COOLDOWN_MS)).fetchone()
            if prior:continue
            score = row['longScore'] if direction=='UP' else row['shortScore']
            atrpct = row['atr5mPct']
            trigger = max(0.65, 1.5*atrpct)
            stop = max(0.40, atrpct)
            db.execute('''INSERT INTO events(symbol,direction,status,started_at,baseline_time,baseline_price,
                   trigger_pct,stop_pct,initial_score,last_price,last_seen,last_score,setup_active)
                   VALUES(?,?,'PENDING',?,?,?,?,?,?,?,?,?,1)''',
                   (row['symbol'],direction,now,row['lastClosed5m'],row['price'],trigger,stop,
                    int(score),row['price'],now,int(score)))
            pending += 1

    def activate_top_candidate(self, row, candles, direction, now_ms=None):
        """Promote one pre-ranked fresh potential; replace old weakest if 8-point better.

        The caller is responsible for freshness, liquidity, and chase safeguards.
        """
        now = int(time.time()*1000) if now_ms is None else now_ms
        is_up = direction == 'UP'
        if not row.get('potentialUp' if is_up else 'potentialDown'):
            return False
        score = int(row['longScore'] if is_up else row['shortScore'])
        with self.lock:
            with self._conn() as db:
                self._expire_unobserved(db, now)
                recent = db.execute('''SELECT 1 FROM events WHERE symbol=? AND direction=? AND started_at>=? LIMIT 1''',
                                    (row['symbol'],direction,now-RECENT_COOLDOWN_MS)).fetchone()
                if recent:
                    return False
                active = db.execute("SELECT id,last_score FROM events WHERE status='PENDING' ORDER BY last_score ASC,started_at ASC").fetchall()
                if len(active) >= ACTIVE_LIMIT:
                    weakest = active[0]
                    if score < weakest['last_score'] + ROTATION_MARGIN:
                        return False
                    db.execute('''UPDATE events SET status='EXPIRED', ended_at=?, end_reason='RANK_REPLACED'
                                  WHERE id=? AND status='PENDING' ''',(now, weakest['id']))
            # refresh runs under the same re-entrant lock; creates one new event.
            row_copy = dict(row)
            row_copy['potentialUp'] = is_up
            row_copy['potentialDown'] = not is_up
            self.refresh(row_copy, candles, now_ms=now, allow_new=True)
            return True

    def fast_update(self, symbol, candles, live_price, now_ms=None):
        """Cheap 5m close/quote check for watchlist. It does not create new signals.

        Live quotes update drift; TARGET/STOP is only evaluated on closed 5m bars.
        """
        now = int(time.time()*1000) if now_ms is None else now_ms
        if not candles or not (live_price > 0):
            return None
        with self.lock, self._conn() as db:
            self._progress(db, symbol, candles, live_price, now)
            self._expire_unobserved(db, now)
            record = db.execute('SELECT data FROM last_rows WHERE symbol=?',(symbol,)).fetchone()
            if record is None:
                return None
            row = json.loads(record[0])
            row['livePrice'] = live_price
            row['quoteAt'] = now
            row['liveDriftPct'] = 100*(live_price/row['price']-1) if row.get('price') else None
            row['fastClosed5m'] = candles[-1]['closeTime']
            return self._refresh_payload(db,row,now,preserve_technical=True)

    def latest_rows(self, age_ms=MAX_ROWS_AGE_MS, now_ms=None):
        now = int(time.time()*1000) if now_ms is None else now_ms
        with self.lock, self._conn() as db:
            self._expire_unobserved(db, now)
            out=[]
            for entry in db.execute('SELECT data FROM last_rows WHERE updated_at>=?',(now-age_ms,)).fetchall():
                row = json.loads(entry['data'])
                events = [self._public(e) for e in self._live_events(db,row['symbol'],now)]
                row['journeys'] = events
                row['categories'] = self._categories(events)
                row['category'] = row['categories'][0] if row['categories'] else 'NETRAL'
                out.append(row)
            return out

    def audit_events(self, limit=200):
        with self.lock,self._conn() as db:
            return [self._public(e) for e in db.execute('SELECT * FROM events ORDER BY started_at DESC LIMIT ?', (limit,))]