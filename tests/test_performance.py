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
    def test_spawn_worker_math_parity_and_cpu_limits(self):
        import multiprocessing
        from concurrent.futures import ProcessPoolExecutor
        from scan_math import compute_scan_math
        from test_app import fake_candles
        import time
        now=int(time.time()*1000)
        sets={tf:fake_candles(tf,count=310) for tf in ('5m','15m','1h','4h')}
        raw=fake_candles('1m',count=100)
        expected=compute_scan_math(sets,raw,now,True)
        with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
            actual=pool.submit(compute_scan_math,sets,raw,now,True).result(timeout=30)
        self.assertGreaterEqual(actual.pop('calcMs'),0)
        expected.pop('calcMs')
        self.assertEqual(actual,expected)
        self.assertEqual(app.cpu_workers(None,16),16)
        self.assertEqual(app.cpu_workers('99',24),24)
        self.assertEqual(app.cpu_workers('bad',2),2)
        self.assertEqual(app.cpu_workers('4',8),4)
    def test_all_cached_calculations_finish_before_single_publish(self):
        from signals import SignalStore
        from test_v05 import event_row,candle
        from unittest.mock import Mock
        import time
        with tempfile.TemporaryDirectory() as d:
            store=SignalStore(Path(d)/'db.sqlite')
            hist=ResearchHistory(store.path,store.lock)
            now=int(time.time()*1000);cut=now-60000
            tickers=[{'symbol':f'C{i}USDT','turnover24h':100000000,'change24h':0} for i in range(42)]
            stream=Mock()
            stream.candles.side_effect=lambda s,*a,**kw:None if s=='C41USDT' else [1]
            stream.prices.side_effect=lambda symbols,at:{s:100.1 for s in symbols}
            seen=set()
            def math(t,*args):
                sym=t['symbol'];seen.add(sym)
                row=event_row(sym,70+int(sym[1:-4]),bar=cut)
                row['_recent5m']=[candle(when=cut)]
                return row
            original=store.refresh_ranked_batch
            def publish(records,*args):
                self.assertEqual(len(seen),41)
                self.assertEqual(len(records),41)
                return original(records,*args)
            with patch.object(app,'STREAM',stream),patch.object(app,'STORE',store),patch.object(app,'HISTORY',hist),patch.object(app,'RUNTIME',None),patch.object(app,'scan_symbol',side_effect=math),patch.object(store,'refresh_ranked_batch',side_effect=publish) as batch,patch.dict(app.SCAN_STATE,{'generation':909,'rows':[],'errors':[],'processed':0}):
                app.scan_cached_universe(909,tickers,set(),now)
                self.assertEqual(batch.call_count,1)
                self.assertEqual(app.SCAN_STATE['computed'],41)
                self.assertEqual(app.SCAN_STATE['cacheSkipped'],1)
                self.assertEqual(app.SCAN_STATE['processed'],42)
                self.assertEqual(len(app.SCAN_STATE['rows']),41)
                self.assertEqual(len(store.active_pending()),10)
                self.assertEqual(sorted(x['initialScore'] for x in store.active_pending()),list(range(101,111)))
                self.assertEqual(len(hist.queued_scan(100)),41)
    def test_wal_dashboard_reads_while_writer_lock_held(self):
        from signals import SignalStore
        from test_v05 import event_row,candle
        import time
        with tempfile.TemporaryDirectory() as d:
            store=SignalStore(Path(d)/'db.sqlite')
            now=int(time.time()*1000)
            row=event_row('AAAUSDT',bar=now-1000)
            store.refresh(row,[candle(when=now-1000)],now_ms=now)
            result=[];done=threading.Event()
            def read():
                result.extend(store.dashboard_snapshot(now)[1]);done.set()
            with store.lock:
                t=threading.Thread(target=read);t.start()
                ok=done.wait(2)
            t.join(3)
            self.assertTrue(ok);self.assertEqual(len(result),1)
    def test_parallel_local_warmup_all_timeframes(self):
        from unittest.mock import Mock
        from stream_engine import LIMIT,TF,close_at
        import time
        now=1800000000000+16000
        e=StreamEngine();e.set_symbols({'AAA','BBB'})
        a=Mock()
        def local(s,tf,n,asof):
            end=close_at(asof,TF[tf])
            return [[0,100,101,99,100,0,end-(n-1-i)*TF[tf],0,0,0,0,0] for i in range(n)]
        a.cached_rows.side_effect=local
        with patch.object(app,'STREAM',e),patch.object(app,'ARCHIVE',a),patch.object(app,'request_market',side_effect=AssertionError('no REST')):
            count,errors=app.local_seed_pass(['AAA','BBB'],now)
        self.assertEqual(count,10);self.assertEqual(errors,[])
        for s in ('AAA','BBB'):
            for tf,n in LIMIT.items():self.assertIsNotNone(e.candles(s,tf,n-1,now-15000))
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
