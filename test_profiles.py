"""Offline profile rules and event database isolation. No Binance calls."""
import tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import scalp_engine,swing_engine,app
from scalp_runtime import ScalpRuntime

class ProfileTimeframeTests(unittest.TestCase):
    def test_scalp_uses_exactly_requested_four_timeframes(self):
        self.assertEqual(scalp_engine.TIMEFRAMES,('1m','5m','15m','1h'))
        self.assertEqual([x[0] for x in scalp_engine.CANDLE_REQUESTS],list(scalp_engine.TIMEFRAMES))
        self.assertFalse('3m' in scalp_engine.TIMEFRAMES)
        self.assertFalse('4h' in scalp_engine.TIMEFRAMES)
    def test_swing_uses_exactly_requested_six_timeframes(self):
        self.assertEqual(swing_engine.TIMEFRAMES,('15m','1h','4h','8h','1d','1w'))
        self.assertEqual([x[0] for x in swing_engine.CANDLE_REQUESTS],list(swing_engine.TIMEFRAMES))
    def test_weekly_trend_requires_closed_history(self):
        bars=[{'close':100+i} for i in range(40)]
        self.assertEqual(swing_engine.weekly_regime(bars,app.ema),'BULLISH')
        self.assertEqual(swing_engine.weekly_regime([{'close':1}]*10,app.ema),'MIXED')
    def test_independent_event_databases_and_timing(self):
        with tempfile.TemporaryDirectory() as d:
            def settings():
                return {'revision':0,'values':{'max_chase_pct':.3}}
            args=(lambda *a: ([],{}),lambda *a:None,lambda *a:{},lambda *a:[],settings)
            scalp=ScalpRuntime(Path(d)/'scalping.sqlite3',*args,strategy='scalping')
            swing=ScalpRuntime(Path(d)/'swing.sqlite3',*args,strategy='swing')
            self.assertEqual(scalp.store.bar_time_key,'lastClosed1m')
            self.assertEqual(swing.store.bar_time_key,'lastClosed1h')
            self.assertEqual(scalp.store.pending_ms,15*60_000)
            self.assertEqual(swing.store.pending_ms,3*24*60*60_000)
            self.assertNotEqual(scalp.store.path,swing.store.path)
            self.assertEqual(scalp.state['mode'],'top80')
            self.assertEqual(swing.state['mode'],'top80')

if __name__=='__main__':unittest.main()
