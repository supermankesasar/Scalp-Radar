import unittest,sqlite3
from filters import r112
from impulse_radar import ImpulseRadar
from stream_engine import StreamEngine

def features(**kw):
    return dict({'rvol1m':2.,'ret5':-.5,'flow5':-.3,'ret1':-.1,'flow1':-.4,'price':100.,'atr1mPct':.1},**kw)
class ImpulseTests(unittest.TestCase):
    def test_recovery_and_no_same_candle_ready(self):
        cut=60000-1
        f=features()
        p=r112.assess(None,f,[],cut,cut+2000,100,.01)
        self.assertEqual((p['state'],p['direction']),('PREPARE','UP'))
        rows=[[0,100,100.01,99.9,100,0,cut],[0,100,100.2,99.98,100.1,0,cut+60000]]
        f2=features(ret1=.1,flow1=.2,price=100.1,rvol1m=1)
        r=r112.assess(p,f2,rows,cut+60000,cut+62000,100.11,.01)
        self.assertEqual(r['state'],'READY')
        self.assertEqual(r112.assess(p,f2,rows,cut+60000,cut+62000,100.11,.2)['reason'],'WIDE_SPREAD')
        self.assertEqual(r112.assess(p,f2,rows,cut+120000,cut+122000,100.11,.01)['reason'],'LIVE_GAP')
        self.assertIsNone(r112.assess(p,f2,rows,cut+60000,cut+76000,100.11,.01))
    def test_short_is_separate(self):
        self.assertEqual(r112.impulse(features(ret5=.5,flow5=.3)),'DOWN')
        self.assertIsNone(r112.impulse(features(ret5=.5,flow5=-.3)))
    def test_paired_controls_and_missing_outcomes(self):
        db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
        try:
            h=ImpulseRadar(db);cut=59999;h.begin(cut)
            h.process('AAA',features(),[],cut,cut+2000,lambda *args:(100,.01,'BOOK_OK'))
            h.persist(db,StreamEngine(),cut,1)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM r112_entries').fetchone()[0],2)
            h.settle(db,StreamEngine(),cut+40*60000)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM r112_outcomes WHERE state='UNOBSERVED'").fetchone()[0],6)
            self.assertEqual(db.execute('SELECT SUM(complete) FROM r112_entries').fetchone()[0],2)
        finally:db.close()
if __name__=='__main__':unittest.main()
