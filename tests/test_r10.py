import tempfile,threading,unittest,sqlite3
from pathlib import Path
from filters import r10
from research_r10 import ResearchR10,entry_time,simulate
class R10Tests(unittest.TestCase):
    def test_strict_future_entry(self):
        self.assertEqual(entry_time(60000),120000)
        self.assertEqual(entry_time(60001),120000)
    def test_close_exit_and_gap(self):
        rows=[[0,'100','103','99','101.2',0,59999]]*15
        self.assertEqual(simulate(rows,'UP',.3,15,'FIXED')[0],'TARGET')
        self.assertAlmostEqual(simulate(rows,'UP',.3,15,'FIXED')[2],1.2)
        self.assertIsNone(simulate(rows[:-1],'UP',.3,15,'FIXED'))
    def test_regime_coverage(self):
        self.assertEqual(r10.regime({'BTCUSDT':1},100)['regime'],'UNKNOWN')
        self.assertEqual(r10.regime(dict({'BTCUSDT':1},**{'X'+str(i):1 for i in range(30)}),40)['regime'],'BULL')
    def test_ledger_dedup_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            h=ResearchR10(Path(d)/'test.db',threading.RLock())
            with h.db() as db:
                for _ in range(2):h.insert(db,'X','1m',59999,65000,.3,{'regime':'UNKNOWN'},[{'id':'A','direction':'UP'}])
                self.assertEqual(db.execute('SELECT COUNT(*) FROM r10_setups').fetchone()[0],1)
                h.settle(db,{},120000+80*60000)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM r10_outcomes WHERE state='UNOBSERVED'").fetchone()[0],9)
    def test_future_open_and_trailing(self):
        rows=[[i*60000,'100','104','98',str(v),0,(i+1)*60000-1] for i,v in enumerate([100.6,100.2]+[100.2]*13)]
        self.assertEqual(simulate(rows,'UP',.3,15,'ATR_TRAIL')[0],'TRAIL')
        self.assertAlmostEqual(simulate(rows,'UP',.3,15,'ATR_TRAIL')[2],.2)
    def test_shared_rate_limit(self):
        from rest_guard import RestGuard
        g=RestGuard();g.check();g.pause({'Retry-After':'60'})
        self.assertGreater(g.remaining(),290)
        with self.assertRaisesRegex(RuntimeError,'rate limit'):g.check()
    def test_no_missing_flow_as_evidence(self):
        bars=[[i*60000,'100','101','99','100',0,(i+1)*60000-1,100] for i in range(61)]
        self.assertEqual(r10.tags1({}, {}, bars,.3,{'regime':'UNKNOWN'}),[])
if __name__=='__main__':unittest.main()
