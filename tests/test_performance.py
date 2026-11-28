import tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from market_archive import MarketArchive
from stream_engine import StreamEngine
from rest_guard import RestGuard
from research_history import ResearchHistory
from stream_research import StreamResearch
import app

class PerformanceTests(unittest.TestCase):
    def test_archive_reuses_complete_cache_but_not_gap(self):
        with tempfile.TemporaryDirectory() as d:
            h=MarketArchive(Path(d)/'db.sqlite',threading.RLock())
            s='AAA';cut=1800000299999;now=cut+1
            e=StreamEngine();e.set_symbols({s});h.stream=e
            bars=[[0,100,101,99,100,0,cut-i*300000,0,0,0,0,0] for i in range(3)]
            h.put('kline_5m',s,[(bars[2][6],bars[2])],now)
            e.seed(s,'5m',bars[:1],now)
            self.assertFalse(h.cached_5m(s,3,now))
            e.seed(s,'5m',bars[1:2],now)
            self.assertTrue(h.cached_5m(s,3,now))
            h.stream=None
            self.assertTrue(h.cached_5m(s,3,now))
            self.assertFalse(h.cached_5m(s,3,now+300000))
    def test_cache_only_scanner_does_not_fetch_missing_history(self):
        e=StreamEngine();e.set_symbols({'AAAUSDT'})
        ticker={'symbol':'AAAUSDT','turnover24h':100000000,'change24h':0}
        with patch.object(app,'STREAM',e),patch.object(app,'request_market',side_effect=AssertionError('no REST')):
            with self.assertRaisesRegex(ValueError,'CACHE_GAP'):
                app.scan_symbol(ticker,cache_only=True,scan_now=1800000000000)
    def test_research_queue_survives_reopen_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'db.sqlite';lock=threading.RLock()
            h=ResearchHistory(path,lock)
            row={'symbol':'AAA','lastClosed5m':299999,'_recent5m':[{'closeTime':299999,'close':100}]}
            h.stage_scan([(row,300123),(row,300999)])
            q=ResearchHistory(path,lock).queued_scan()
            self.assertEqual(len(q),1);self.assertEqual(q[0]['observed_at'],300123)
            h.ack_scan('AAA',299999);self.assertEqual(h.queued_scan(),[])
    def test_extra_indicators_bounded(self):
        rows=[{'close':100+i,'high':101+i,'low':99+i,'volume':10} for i in range(60)]
        e=app.extra_indicators(rows)
        self.assertAlmostEqual(e['adx14'],100)
        self.assertEqual(e['mfi14'],100)
        self.assertEqual(e['obvFlow20'],1)
        self.assertGreater(e['roc5Pct'],0)
        self.assertTrue(0<=e['stochRsi14K3']<=100)
    def test_budget_is_shared_and_bounded(self):
        g=RestGuard();g.history_cap=2
        self.assertEqual(g.history_delay('/futures/data/openInterestHist'),0)
        self.assertEqual(g.history_delay('/futures/data/topLongShortPositionRatio'),0)
        self.assertGreater(g.history_delay('/futures/data/globalLongShortAccountRatio'),0)
        self.assertEqual(g.history_delay('/fapi/v1/klines'),0)
    def test_old_history_migration_and_expiry(self):
        with tempfile.TemporaryDirectory() as d:
            h=ResearchHistory(Path(d)/'db.sqlite',threading.RLock())
            with h.connection() as db:
                db.execute("INSERT INTO research_candidates(symbol,candle_time,filter_id,version,direction,baseline,target,stop) VALUES('A',1,'F','V','UP',100,1,1)")
                db.execute("INSERT INTO research_outcomes(candidate_id,horizon,confirm,state,evaluated_at) VALUES(1,15,5,'TARGET',100)")
            h.pending_symbols(25*3600000)
            with h.connection() as db:
                self.assertEqual(db.execute('SELECT complete FROM research_candidates').fetchone()[0],1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM research_outcomes WHERE state='TARGET'").fetchone()[0],1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM research_outcomes').fetchone()[0],6)
    def test_ws_expiry_preserves_completed_result(self):
        with tempfile.TemporaryDirectory() as d:
            h=StreamResearch(Path(d)/'db.sqlite',threading.RLock())
            with h.db() as db:
                db.execute("INSERT INTO ws_candidates(symbol,candle_time,observed_at,filter_id,version,direction,baseline,target,stop) VALUES('A',59999,60001,'F','V','UP',100,1,1)")
                db.execute("INSERT INTO ws_outcomes(candidate_id,horizon,state,evaluated_at) VALUES(1,15,'TARGET',1000000)")
            e=StreamEngine();cut=100*60000-1
            h.process(e,cut,cut+5000,app.ema,app.atr,app.parse_klines)
            with h.db() as db:
                self.assertEqual(db.execute('SELECT complete FROM ws_candidates').fetchone()[0],1)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM ws_outcomes WHERE state='TARGET'").fetchone()[0],1)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM ws_outcomes').fetchone()[0],3)
    def test_scheduler_no_database_read_when_already_running(self):
        with patch.dict(app.SCAN_STATE,{'running':True}),patch.object(app.STORE,'latest_rows',side_effect=AssertionError('scheduler should not read UI rows')):
            state,_,_,_=app.schedule_scan()
            self.assertTrue(state['running'])
if __name__=='__main__':unittest.main()
