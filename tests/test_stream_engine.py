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
        e.candle_received[('AAAUSDT','1m')]={cut:cut+100}
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
    def test_event_shapes_and_no_open_candles(self):
        e=StreamEngine();e.set_symbols({'AAAUSDT'});start=1800000000000;cut=start+59999
        e.connection('depth',['AAAUSDT'],True,start-1)
        e.connection('liquidations',['AAAUSDT'],True,start-1)
        k={'i':'1m','t':start,'T':cut,'o':'100','h':'102','l':'99','c':'101','v':'10','q':'1000','n':5,'V':'5','Q':'500','x':False}
        e.ingest({'e':'kline','s':'AAAUSDT','k':k},cut+1)
        self.assertIsNone(e.candles('AAAUSDT','1m',1,cut+1))
        k['x']=True;e.ingest({'data':{'e':'kline','s':'AAAUSDT','k':k}},cut+2)
        self.assertEqual(e.receipt('AAAUSDT','1m',cut),cut+2)
        for i in range(3):
            t=cut-2000+i*500
            e.ingest({'e':'depthUpdate','s':'AAAUSDT','T':t,'u':i+1,'b':[['100','10']],'a':[['101','1']]},t+10)
        event={'e':'forceOrder','o':{'s':'AAAUSDT','S':'BUY','ap':'100','z':'200','T':cut-100}}
        e.ingest(event,cut+5);e.ingest(event,cut+6)
        m=e.minute('AAAUSDT',cut,cut+5000)
        self.assertGreater(m['imbalance'],.5)
        self.assertEqual(m['liqBuy'],20000)
        self.assertEqual(m['liqCount'],1)
        self.assertIsNone(m['flow'])
    def test_hybrid_requires_independent_coverage(self):
        self.assertIsNone(microstructure.hybrid({},100,1,True)['score'])
        self.assertTrue(microstructure.hybrid({'flow':.5,'imbalance':.5},80,1,True)['potential'])
        self.assertFalse(microstructure.hybrid({'flow':.5,'imbalance':-.5},100,1,True)['potential'])
if __name__=='__main__':unittest.main()
