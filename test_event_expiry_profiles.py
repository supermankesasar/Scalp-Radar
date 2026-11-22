"""Event retention checks for profile-specific expiry, offline and deterministic."""
import tempfile,time,unittest
from pathlib import Path
from signals import SignalStore

class EventExpiryTests(unittest.TestCase):
    def test_swing_pending_not_expired_after_two_hours_without_candles(self):
        with tempfile.TemporaryDirectory() as d:
            now=int(time.time()*1000)
            store=SignalStore(Path(d)/'swing.sqlite3',bar_time_key='lastClosed1h',
                              pending_ms=3*24*60*60_000)
            with store._conn() as db:
                db.execute("""INSERT INTO events(
                    symbol,direction,status,started_at,baseline_time,baseline_price,
                    trigger_pct,initial_score,last_price,last_seen,last_score,setup_active)
                    VALUES('BTCUSDT','UP','PENDING',?,?,?,?,?,?,?,?,1)""",
                    (now-2*60*60_000,now-2*60*60_000,100,2,81,100,now,81))
            self.assertIn('BTCUSDT',store.active_symbols(now_ms=now))
            self.assertEqual(store.audit_events(1)[0]['status'],'PENDING')
            self.assertNotIn('BTCUSDT',store.active_symbols(now_ms=now+4*24*60*60_000))
            event=store.audit_events(1)[0]
            self.assertEqual(event['status'],'EXPIRED')
            self.assertEqual(event['endReason'],'TIMEOUT_UNOBSERVED')

    def test_scalp_still_expires_after_fifteen_minutes(self):
        with tempfile.TemporaryDirectory() as d:
            now=int(time.time()*1000)
            store=SignalStore(Path(d)/'scalp.sqlite3',bar_time_key='lastClosed1m',
                              pending_ms=15*60_000)
            with store._conn() as db:
                db.execute("""INSERT INTO events(
                    symbol,direction,status,started_at,baseline_time,baseline_price,
                    trigger_pct,initial_score,last_price,last_seen,last_score,setup_active)
                    VALUES('ETHUSDT','DOWN','PENDING',?,?,?,?,?,?,?,?,1)""",
                    (now-20*60_000,now-20*60_000,100,.65,73,100,now,73))
            self.assertNotIn('ETHUSDT',store.active_symbols(now_ms=now))
            self.assertEqual(store.audit_events(1)[0]['endReason'],'TIMEOUT_UNOBSERVED')

if __name__=='__main__':unittest.main()
