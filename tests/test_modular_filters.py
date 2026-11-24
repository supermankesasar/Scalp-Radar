import unittest
from filters.registry import evaluate
from filters import ema9_cross, ema21_pullback

def original(c, sign):
    trend = 'BULLISH' if sign == 1 else 'BEARISH'
    opposite = 'BEARISH' if sign == 1 else 'BULLISH'
    score = (24 if c['trend1h']==trend else 0) + (12 if c['trend4h']==trend else 5 if c['trend4h']=='MIXED' else 0)
    score += 14 if sign*(c['close15']-c['ema21_15'])>0 else 0
    score += 11 if sign*(c['close5']-c['ema21_5'])>0 else 0
    score += 10 if sign*c['macd5']>0 else 0
    score += 10 if (47<=c['rsi15']<=70 if sign==1 else 30<=c['rsi15']<=53) else 0
    score += 11 if c['rvol5']>=1.1 else 6 if c['rvol5']>=.85 else 0
    score += 8 if c['vwap'] is not None and sign*(c['close5']-c['vwap'])>0 else 0
    ok = c['trend1h']==trend and c['trend4h']!=opposite and score>=68 and 0<=sign*c['dist_ema15']<=max(.75,1.4*c['atr_pct']) and -.4<=sign*c['ret15']<=max(.4,1.3*c['atr_pct'])
    return score,ok

class ModularFilterTests(unittest.TestCase):
    def fixture(self):
        return dict(trend1h='BULLISH',trend4h='MIXED',close5=100.2,close15=100.2,ema21_5=100,ema21_15=100,
            ema9_5=100.1,prev_ema9_5=100.2,prev_ema21_5=99.9,prev_close5=100.0,low5=99.8,high5=100.5,
            close1h=101,ema21_1h=100,ema21_1h_prev6=99,rsi15=60,macd5=.1,rvol5=1.1,vwap=100,
            atr_pct=.3,ret15=.2,dist_ema15=.2)
    def test_baseline_parity_and_shadow_isolation(self):
        c=self.fixture()
        for t1 in ('BULLISH','BEARISH','MIXED'):
            for t4 in ('BULLISH','BEARISH','MIXED'):
                for r in (30,47,53,70,71):
                    for vol in (.84,.85,1.09,1.1):
                        for dist in (-.75,0,.75,.76):
                            v=dict(c,trend1h=t1,trend4h=t4,rsi15=r,rvol5=vol,dist_ema15=dist)
                            a=evaluate(v,shadow=False);b=evaluate(v,shadow=True)
                            self.assertEqual(a['baseline'],b['baseline'])
                            for sign,d in ((1,'UP'),(-1,'DOWN')):
                                self.assertEqual((a['baseline'][d]['score'],a['baseline'][d]['potential']),original(v,sign))
    def test_independent_timing(self):
        c=self.fixture()
        self.assertTrue(ema9_cross.detect(c,1))
        self.assertTrue(ema21_pullback.detect(c,1))
        self.assertFalse(ema9_cross.detect(dict(c,prev_close5=100.3),1))
        self.assertTrue(ema21_pullback.detect(dict(c,prev_close5=100.3),1))
if __name__=='__main__':unittest.main()
