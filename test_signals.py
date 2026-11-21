import tempfile
import unittest
from pathlib import Path
from signals import SignalStore

T=1_900_000_000_000
FIVE=300_000

def candle(offset,close,high=None,low=None):
    return {'closeTime':T+offset*FIVE, 'close':close,
            'high':close if high is None else high,'low':close if low is None else low}

def row(close=100,bar=0,up=False,down=False):
    return {'symbol':'COINAUSDT','price':close,'lastClosed5m':T+bar*FIVE,
            'potentialUp':up,'potentialDown':down,'longScore':83 if up else 35,
            'shortScore':81 if down else 30,'score':0,'atr5mPct':0.30,
            'pct15m':0,'pct60m':0,'pct24h':0,'relVolume5m':1.7,
            'trend1h':'BULLISH','trend4h':'MIXED'}

class SignalJourneyTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory()
        self.path=Path(self.t.name)/'signal.sqlite3'
        self.store=SignalStore(self.path)
    def tearDown(self):self.t.cleanup()
    def tick(self,r,cs,minutes=2):
        return self.store.refresh(r,cs,T+minutes*60000)
    def test_no_prior_potential_never_reached(self):
        got=self.tick(row(110,2,False,False),[candle(0,100),candle(1,109),candle(2,110)],minutes=12)
        self.assertEqual(got['categories'],[])
        self.assertEqual(self.store.audit_events(),[])
    def test_transition_overlap_and_reversal(self):
        r=self.tick(row(100,0,True),[candle(0,100)],0)
        self.assertEqual(r['categories'],['POTENSI_NAIK'])
        self.assertEqual(r['journeys'][0]['baselinePrice'],100)
        # Wick above target does NOT confirm when candle closes below the threshold.
        r=self.tick(row(100.2,1,True),[candle(0,100),candle(1,100.2,high=102)],5)
        self.assertEqual(r['categories'],['POTENSI_NAIK'])
        # A later CLOSED candle breaks the target +0.65%; bearish setup appears simultaneously.
        r=self.tick(row(100.9,2,False,True),[candle(0,100),candle(1,100.2,high=102),candle(2,100.9)],10)
        self.assertEqual(set(r['categories']),{'SUDAH_NAIK','POTENSI_TURUN'})
        self.assertEqual(r['category'] in r['categories'],True)
        reached=next(x for x in r['journeys'] if x['direction']=='UP')
        self.assertGreater(reached['peakClosePct'],.65)
        self.assertGreater(reached['peakWickPct'],reached['peakClosePct'])
        self.assertTrue(reached['confirmedAt'])
        # A previous hit remains in Sudah Naik even after price reverses.
        r=self.tick(row(99.9,3,False,True),[candle(0,100),candle(1,100.2,high=102),candle(2,100.9),candle(3,99.9)],15)
        self.assertIn('SUDAH_NAIK',r['categories'])
        self.assertIn('SUDAH_TURUN',r['categories'])
        self.assertLess(next(x for x in r['journeys'] if x['direction']=='UP')['currentPct'],0)
        # Reinitialize to simulate process restart: category history survives.
        store2=SignalStore(self.path)
        restored=store2.latest_rows()
        self.assertEqual(len(restored),1)
        self.assertIn('SUDAH_NAIK',restored[0]['categories'])
        self.assertIn('SUDAH_TURUN',restored[0]['categories'])
        self.assertEqual(len(store2.audit_events()),2)
    def test_no_same_candle_confirmation(self):
        r=self.tick(row(100,1,True),[candle(0,96),candle(1,100,high=104)],5)
        self.assertEqual(r['categories'],['POTENSI_NAIK'])
    def test_completed_short_only_from_previous_potential_down(self):
        self.tick(row(100,0,False,True),[candle(0,100)],0)
        r=self.tick(row(99,1,False,False),[candle(0,100),candle(1,99)],5)
        self.assertEqual(r['categories'],['SUDAH_TURUN'])
        e=r['journeys'][0]
        self.assertAlmostEqual(e['currentPct'],1)
    def test_cooldown_reduces_repeat_events(self):
        self.tick(row(100,0,True),[candle(0,100)],0)
        for i in range(1,10):
            self.tick(row(100+i*.01,i,True),[candle(j,100+j*.01) for j in range(i+1)],i*5)
        self.assertEqual(len(self.store.audit_events()),1)
    def test_expiration_pending(self):
        self.tick(row(100,0,True),[candle(0,100)],0)
        # Trigger time is 12h; a pending event older than 12h is not a forever signal.
        r=self.tick(row(100.1,146,False),[candle(i,100.1) for i in range(147)],146*5)
        self.assertEqual(r['categories'],[])
        self.assertEqual(self.store.audit_events()[0]['status'],'EXPIRED')

if __name__=='__main__':unittest.main()