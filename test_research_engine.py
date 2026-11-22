"""Offline safety and regression checks for read-only research engine."""
import tempfile,unittest,sqlite3
from pathlib import Path
from unittest.mock import patch
import research_engine as r

def bar(t,o=100,h=101,l=99,c=100):
    return [t,str(o),str(h),str(l),str(c),'10',t+r.STEP-1,'1000',0,0,0]

class ResearchTests(unittest.TestCase):
    def test_valid_candle_and_invalid_ohlc(self):
        self.assertEqual(r.parse(bar(0))[0],0)
        with self.assertRaises(ValueError):
            r.parse(bar(0,100,99,101,100))
    def test_archive_dedup_and_skip_already_complete(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(r,'DB',Path(d)/'candles.sqlite3'):
                con=r.connect()
                try:
                    fetch=lambda sym,a,b:[bar(t) for t in range(a,b,r.STEP)]
                    first=r.sync(con,'BTCUSDT',0,3*r.STEP,fetch)
                    second=r.sync(con,'BTCUSDT',0,3*r.STEP,lambda *args:self.fail('should not fetch complete archive'))
                    self.assertEqual(first['bars'],3)
                    self.assertEqual(second['inserted'],0)
                finally:con.close()
    def test_gap_is_not_fabricated(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(r,'DB',Path(d)/'candles.sqlite3'):
                con=r.connect()
                try:
                    result=r.sync(con,'BTCUSDT',0,3*r.STEP,lambda *a:[bar(0),bar(2*r.STEP)])
                    self.assertEqual(result['gaps'],1)
                    self.assertEqual(result['coverage_pct'],66.67)
                finally:con.close()
    def test_no_signals_does_not_claim_profit(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(r,'DB',Path(d)/'candles.sqlite3'):
                con=r.connect()
                try:
                    result=r.replay(con,[],0,3*r.STEP)
                    self.assertIsNone(result['metrics']['win_rate_pct'])
                    self.assertFalse(result['audit']['historical_full_strategy_backtest'])
                finally:con.close()
    def test_long_stop_first_on_ambiguous_candle(self):
        with tempfile.TemporaryDirectory() as d:
            with patch.object(r,'DB',Path(d)/'candles.sqlite3'):
                con=r.connect()
                try:
                    for t in (r.STEP,2*r.STEP,3*r.STEP):
                        row=r.parse(bar(t,100,102,98,100))
                        con.execute('INSERT INTO bars VALUES(?,?,?,?,?,?,?,?,?,?)',('BTCUSDT',*row,0))
                    con.commit()
                    result=r.replay(con,[('BTCUSDT','UP',r.STEP-1,90)],0,5*r.STEP)
                    self.assertEqual(result['trades'][0]['reason'],'STOP')
                    self.assertLess(result['metrics']['mean_net_pct'],0)
                finally:con.close()

if __name__=='__main__':unittest.main()
