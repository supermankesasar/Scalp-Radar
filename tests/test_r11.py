import tempfile,threading,unittest
from pathlib import Path
from filters import r11
from radar_r11 import RadarR11
from stream_engine import StreamEngine
from rest_guard import RestGuard

def bars():
    out=[]
    for i in range(61):
        p=100+i*.02
        c=p+(.12 if i==60 else .01)
        q=300 if i==60 else 100
        out.append([i*60000,p,c+.001,p-.001,c,1,(i+1)*60000-1,q,30 if i==60 else 10,1,q*.75,'0'])
    return out

class R11Tests(unittest.TestCase):
    def test_multihorizon_and_no_lookahead(self):
        rows=bars();cut=rows[-1][6]
        f=r11.features(rows,cut)
        self.assertTrue(f['watch'])
        self.assertEqual(f['direction'],'UP')
        self.assertTrue(f['trigger'])
        self.assertGreater(f['ret60'],f['ret30'])
        self.assertIsNone(r11.features(rows[:-1],cut))
        self.assertIsNone(r11.features(rows,cut-60000))
        broken=list(rows);broken.pop(20)
        self.assertIsNone(r11.features(broken,cut))
    def test_entry_guards_and_monitor(self):
        rows=bars();cut=rows[-1][6];f=r11.features(rows,cut);p=f['price']
        self.assertEqual(r11.advance(None,f,cut,cut+3000,p,None)['state'],'PREPARE')
        self.assertEqual(r11.advance(None,f,cut,cut+3000,p*1.005,.01)['state'],'LATE')
        self.assertEqual(r11.advance(None,f,cut,cut+3000,p,.2)['reason'],'WIDE_SPREAD')
        self.assertIsNone(r11.advance(None,f,cut,cut+16000,p,.01))
        ready=r11.advance(None,f,cut,cut+3000,p,.01)
        self.assertEqual(ready['state'],'READY')
        self.assertEqual(ready['prepareLeadMs'],0)
        mon=r11.advance(ready,f,cut+60000,cut+63000,p,.01)
        self.assertEqual(mon['state'],'MONITOR')
    def test_ledger_dedup_and_unobserved(self):
        rows=bars();cut=rows[-1][6];f=r11.features(rows,cut)
        ready=r11.advance(None,f,cut,cut+3000,f['price'],.01)
        with tempfile.TemporaryDirectory() as d:
            h=RadarR11(Path(d)/'test.db',threading.RLock(),StreamEngine())
            with h.db() as db:
                for _ in range(2):h.persist(db,'AAA',None,ready,cut,cut+3000)
                self.assertEqual(db.execute('SELECT COUNT(*) FROM r11_ready').fetchone()[0],1)
                h.settle(db,cut+35*60000)
                self.assertEqual(db.execute('SELECT state FROM r11_outcomes').fetchone()[0],'UNOBSERVED')
    def test_budget_from_exchange(self):
        g=RestGuard()
        g.observe({'X-MBX-USED-WEIGHT-1M':'1800'})
        self.assertIsNone(g.status()['limit1m'])
        g.observe({'X-MBX-USED-WEIGHT-1M':'2000'},{'rateLimits':[{'rateLimitType':'REQUEST_WEIGHT','interval':'MINUTE','intervalNum':1,'limit':2400}]})
        self.assertGreater(g.remaining(),0)
        self.assertEqual(g.status()['used'] if 'used' in g.status() else g.status()['weight1m'],2000)
if __name__=='__main__':unittest.main()
