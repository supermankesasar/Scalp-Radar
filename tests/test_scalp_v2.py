import unittest
from filters import scalp_v2
from filters.registry import evaluate
from test_modular_filters import ModularFilterTests
from unittest.mock import patch
from test_app import fake_market
import app

def ema(values,p):
    a=sum(values[:p])/p
    out=[None]*(p-1)+[a]
    for v in values[p:]:
        a=v*2/(p+1)+a*(1-2/(p+1))
        out.append(a)
    return out

class V2Tests(unittest.TestCase):
    def fixture(self):
        c=ModularFilterTests().fixture()
        c.update(trend1h='BEARISH',trend4h='BEARISH',ema9_5=100.15,
                 ema14_5=100.1,ema10_5=100.15,prev_ema10_5=100.2,
                 prev_ema14_5=100.1,rsi5=60,ret5=.1)
        c['minute']={'series':{str(p):{'close':[99.,99.,100.1,100.2],
                           'ema':[100.,100.,100.,100.]} for p in (9,10,14)}}
        return c
    def test_v2_without_large_trend_gate(self):
        c=self.fixture()
        r=evaluate(c,shadow=True)
        self.assertFalse(r['baseline']['UP']['potential'])
        self.assertTrue(r['v2']['UP']['potential'])
        self.assertIn('SCALP_V2',[x['id'] for x in r['candidates']])
        self.assertFalse(r['v2']['DOWN']['potential'])
    def test_missing_and_chase(self):
        c=self.fixture()
        self.assertFalse(scalp_v2.evaluate(dict(c,minute=None),1)['potential'])
        self.assertFalse(scalp_v2.evaluate(dict(c,ret5=3),1)['potential'])
        self.assertFalse(scalp_v2.evaluate(dict(c,rvol5=.84),1)['potential'])
    def test_cutoff_and_gap(self):
        rows=[{'closeTime':(i+1)*60000-1,'close':100+i*.01} for i in range(65)]
        cutoff=rows[59]['closeTime']
        self.assertEqual(scalp_v2.minute_features(rows,cutoff,ema),scalp_v2.minute_features(rows[:60],cutoff,ema))
        self.assertIsNone(scalp_v2.minute_features(rows[:30]+rows[31:],cutoff,ema))
        self.assertIsNone(scalp_v2.minute_features(rows,cutoff+1,ema))
    def test_scan_symbol_v2_integration(self):
        with patch.object(app,'LIVE_FILTER','SCALP_V2'), patch.object(app,'request_market',side_effect=fake_market):
            row=app.scan_symbol({'symbol':'AAAUSDT','turnover24h':100000000,'change24h':.1})
        self.assertEqual(row['liveFilter'],'SCALP_V2')
        self.assertIsNone(row['minuteError'])
        self.assertEqual(row['researchFeatures']['minute']['cutoff'],row['lastClosed5m'])
        self.assertEqual(row['longScore'],row['v2Breakdown']['UP']['score'])
    def test_live_filter_saved_on_event(self):
        import tempfile
        from pathlib import Path
        from signals import SignalStore
        with tempfile.TemporaryDirectory() as d:
            store=SignalStore(Path(d)/'test.sqlite3')
            t=1795503599999
            row={'symbol':'TESTUSDT','lastClosed5m':t,'price':100.,'atr5mPct':.2,
                 'potentialUp':True,'potentialDown':False,'longScore':85,'shortScore':5,
                 'liveFilter':'SCALP_V2'}
            store.refresh(row,[{'closeTime':t,'close':100.,'high':100.1,'low':99.9}],now_ms=t+1)
            self.assertEqual(store.audit_events()[0]['filterId'],'SCALP_V2')
if __name__=='__main__': unittest.main()
