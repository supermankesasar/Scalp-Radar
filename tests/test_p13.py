import tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import app
from market_archive import crypto_universe,MarketArchive
from scan_worker import compute_full_scan
from stream_engine import StreamEngine,close_at
from signals import SignalStore
from research_history import ResearchHistory
from test_v05 import event_row,candle
from test_app import fake_candles

class P13Tests(unittest.TestCase):
    def test_expanded_universe(self):
        def sym(name,typ='PERPETUAL',status='TRADING',quote='USDT',margin='USDT'):
            return dict(symbol=name,contractType=typ,status=status,quoteAsset=quote,marginAsset=margin)
        info={'symbols':[sym('BTCUSDT'),sym('PAXGUSDT'),sym('XAUUSDT','TRADIFI_PERPETUAL'),sym('TSLAUSDT','TRADIFI_PERPETUAL'),sym('BTCDOMUSDT'),sym('FUTURE','CURRENT_QUARTER'),sym('CLOSED',status='SETTLING'),sym('BTCUSDC',quote='USDC',margin='USDC')]}
        self.assertEqual(crypto_universe(info),{'BTCUSDT','PAXGUSDT','XAUUSDT','TSLAUSDT','BTCDOMUSDT'})
    def test_major_freshness(self):
        e=StreamEngine();e.set_symbols({'BTCUSDT'})
        now=1800000076000;cut=close_at(now-15000,60000)
        e.seed('BTCUSDT','1m',[[0,100,100,100,100,1,cut-60000],[0,100,101,100,101,1,cut]],now)
        e.quotes['BTCUSDT']=(101,now-100)
        d=e.major_status(('BTCUSDT','XAUUSDT'),now)
        self.assertEqual(d['rows'][0]['price'],101)
        self.assertAlmostEqual(d['rows'][0]['returns']['1m'],1)
        self.assertFalse(d['rows'][1]['listed'])
        self.assertIsNone(e.major_status(('BTCUSDT',),now+11000)['rows'][0]['price'])
    def test_rejection_reasons(self):
        now=int(time.time()*1000);cut=now-1000
        rows=[event_row('NOQUOTE',80,bar=cut),event_row('STALE',80,bar=now-900000),event_row('CHASE',80,bar=cut),event_row('GOOD',80,bar=cut)]
        counts={};result=app.promotion_candidates(rows,now,{'STALE':100,'CHASE':101,'GOOD':100},diagnostics=counts)
        self.assertEqual([r[3]['symbol'] for r in result],['GOOD'])
        self.assertEqual(counts['NO_FRESH_QUOTE'],1);self.assertEqual(counts['STALE_CANDLE'],1);self.assertEqual(counts['CHASE'],1)
        self.assertEqual(rows[0]['promotionReasons']['UP'],'NO_FRESH_QUOTE')
    def test_early_publish_does_not_wait_for_slow_symbol(self):
        with tempfile.TemporaryDirectory() as d:
            store=SignalStore(Path(d)/'db.sqlite')
            hist=ResearchHistory(store.path,store.lock)
            now=int(time.time()*1000);cut=now-1000
            tickers=[{'symbol':s,'turnover24h':100000000,'change24h':0} for s in ('FAST','SLOW')]
            stream=Mock()
            stream.candles.return_value=[1]
            stream.prices.side_effect=lambda symbols,at:{s:100 for s in symbols}
            published=threading.Event()
            def math(t,*args):
                if t['symbol']=='SLOW':
                    self.assertTrue(published.wait(8),'fast candidate not published')
                row=event_row(t['symbol'],80,bar=cut)
                row['_recent5m']=[candle(when=cut)]
                return row
            original=store.refresh_ranked_batch
            def publish(records,*args):
                result=original(records,*args)
                if records[0]['symbol']=='FAST':
                    self.assertEqual(len(store.active_pending()),1)
                    published.set()
                return result
            with patch.object(app,'STREAM',stream),patch.object(app,'STORE',store),patch.object(app,'HISTORY',hist),patch.object(app,'RUNTIME',None),patch.object(app,'scan_symbol',side_effect=math),patch.object(app,'PUBLISH_WINDOW_SECONDS',.01),patch.object(store,'refresh_ranked_batch',side_effect=publish),patch.dict(app.SCAN_STATE,{'generation':901,'rows':[],'errors':[],'processed':0}):
                app.scan_cached_universe(901,tickers,set(),now)
                self.assertEqual(app.SCAN_STATE['phaseMetrics']['publishBatches'],2)
                self.assertEqual(app.SCAN_STATE['phaseMetrics']['promotion']['PROMOTED'],2)
                self.assertEqual(app.SCAN_STATE['promotionCoinReasons']['FAST']['UP'],'PROMOTED')
    def test_full_worker_spawn_parity_with_readonly_db(self):
        now=int(time.time()*1000)
        sets={tf:fake_candles(tf,count=310) for tf in ('5m','15m','1h','4h')}
        raw=fake_candles('1m',count=100)
        with tempfile.TemporaryDirectory() as d:
            a=MarketArchive(Path(d)/'db.sqlite',threading.RLock())
            args=(sets,raw,now,True,None,'AAAUSDT',1,a.path,{},None,'R08_MULTI_CORE',{'sampleCount':0,'universeSize':1})
            expected=compute_full_scan(*args)
            with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
                actual=pool.submit(compute_full_scan,*args).result(timeout=30)
            self.assertIsNone(actual[4])
            actual[0].pop('calcMs');expected[0].pop('calcMs')
            self.assertEqual(actual[:4],expected[:4])
if __name__=='__main__':unittest.main()
