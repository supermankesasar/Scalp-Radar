import unittest
from filters import scalp_v2
from filters.registry import evaluate
from test_modular_filters import ModularFilterTests

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
if __name__=='__main__': unittest.main()
