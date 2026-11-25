import unittest
from filters import multifactor as m
from filters.registry import evaluate
from test_modular_filters import ModularFilterTests
from test_app import fake_candles
import app

class MultiTests(unittest.TestCase):
    def test_features_and_gap(self):
        bars=app.parse_klines(fake_candles('5m'),10**15)
        x=m.extract(bars,app.rsi,app.atr)
        self.assertIsNotNone(x)
        self.assertIsNotNone(x['tradeZ'])
        self.assertIsNone(m.extract(bars[:-2]+bars[-1:],app.rsi,app.atr))
    def test_absorption_not_whale(self):
        c=ModularFilterTests().fixture()
        c.update(rsi5=60,minute=None,derivatives={},breadth={})
        bars=app.parse_klines(fake_candles('5m'),10**15)
        x=m.extract(bars,app.rsi,app.atr)
        x.update(rvol=4.44,flow5=-.40,bodyATR=.1,lowerWick=.6,sweepDown=False)
        c['multi']=x
        a=m.evaluate(c,1)
        self.assertIn('R08_ABSORPTION',a['tags'])
        self.assertIsNone(a['full'])
        self.assertNotIn('R08_MULTI_FULL',a['tags'])
        self.assertEqual(evaluate(c,shadow=True)['baseline'],evaluate(c,shadow=False)['baseline'])
    def test_full_requires_coverage(self):
        c=ModularFilterTests().fixture()
        c.update(rsi5=60,minute=None,derivatives={'oiDelta15':1,'oiPriceRet15':1,'topPositionDeltaPP':1,'fundingSnapshot':0},breadth={'upShare':.7,'relativeBTC':1})
        c['multi']=m.extract(app.parse_klines(fake_candles('5m'),10**15),app.rsi,app.atr)
        r=m.evaluate(c,1)
        self.assertIsNotNone(r['full'])
        self.assertTrue(0<=r['core']<=100)
        self.assertTrue(0<=r['full']<=100)
    def test_scan(self):
        from unittest.mock import patch
        from test_app import fake_market
        with patch.object(app,'LIVE_FILTER','R08_MULTI_CORE'),patch.object(app,'request_market',side_effect=fake_market):
            row=app.scan_symbol({'symbol':'AAAUSDT','turnover24h':100000000,'change24h':.1})
        self.assertEqual(row['liveFilter'],'R08_MULTI_CORE')
        self.assertEqual(row['longScore'],row['r08Breakdown']['UP']['core'])
if __name__=='__main__':unittest.main()
