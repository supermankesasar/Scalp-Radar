import unittest,tempfile,threading
from pathlib import Path
from stream_engine import StreamEngine,stream_groups
from stream_research import StreamResearch
from filters import microstructure
import app
from test_app import fake_candles
class StreamTests(unittest.TestCase):
    def test_groups(self):
        groups=stream_groups({'X%dUSDT'%i for i in range(516)})
        self.assertTrue(all(len(g[3])<=1024 for g in groups))
        self.assertTrue(all(g[0]=='public' for g in groups if g[1]=='depth'))
        self.assertEqual(sum(len(g[3]) for g in groups if g[1]=='candles'),516*5)
    def test_cache_continuity(self):
        e=StreamEngine();e.set_symbols({'AAAUSDT'})
        rows=fake_candles('1m',count=105)
        now=int(rows[-1][6])+1
        e.seed('AAAUSDT','1m',rows,now)
        self.assertEqual(len(e.candles('AAAUSDT','1m',99,now)),99)
        self.assertIsNone(e.candles('AAAUSDT','1m',99,now+60000))
        e.bars[('AAAUSDT','1m')].pop(int(rows[-5][6]))
        self.assertIsNone(e.candles('AAAUSDT','1m',99,now))
    def test_micro_gap_and_coverage(self):
        e=StreamEngine();e.set_symbols({'AAAUSDT'});start=1800000000000
        e.connection('trades',['AAAUSDT'],True,start-60000)
        def trade(a,m):return {'e':'aggTrade','s':'AAAUSDT','a':a,'p':'100','q':'2','m':m,'T':start+1000}
        e.ingest(trade(1,False),start+1001);e.ingest(trade(1,False),start+1002)
        e.ingest(trade(2,True),start+1003)
        x=e.minute('AAAUSDT',start+59999,start+65000)
        self.assertEqual(x['tradeCount'],2);self.assertEqual(x['cvdQuote'],0)
        self.assertIsNone(x['imbalance'])
        e.ingest(trade(4,False),start+1004)
        self.assertIsNone(e.minute('AAAUSDT',start+59999,start+65000)['flow'])
        e.connection('trades',['AAAUSDT'],False,start+66000)
        self.assertIsNone(e.minute('AAAUSDT',start+59999,start+67000)['flow'])
    def test_ledger_dedup_and_outcome(self):
        e=StreamEngine();e.set_symbols({'AAAUSDT'})
        rows=fake_candles('1m',count=105)
        cut=int(rows[-16][6]);e.seed('AAAUSDT','1m',rows,cut+1)
        with tempfile.TemporaryDirectory() as d:
            h=StreamResearch(Path(d)/'test.db',threading.RLock())
            from unittest.mock import patch
            with patch.object(microstructure,'evaluate',return_value=[{'id':'R09_TEST','direction':'UP','score':65}]):
                h.process(e,cut,cut+5000,app.ema,app.atr,app.parse_klines)
                h.process(e,cut,cut+6000,app.ema,app.atr,app.parse_klines)
            self.assertEqual(h.summary()['candidates'],1)
            self.assertEqual(h.summary()['snapshots'],1)
            end=int(rows[-1][6]);e.seed('AAAUSDT','1m',rows,end+1)
            h.process(e,end,end+5000,app.ema,app.atr,app.parse_klines)
            self.assertTrue(any(x['filter_id']=='R09_TEST' and x['horizon']==15 for x in h.summary()['comparison']))
if __name__=='__main__':unittest.main()
