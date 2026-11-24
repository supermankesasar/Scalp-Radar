import tempfile, threading, unittest
from pathlib import Path
from research_history import ResearchHistory
class HistoryTests(unittest.TestCase):
    def test_all_candidates_dedup_and_outcomes(self):
        with tempfile.TemporaryDirectory() as folder:
            h=ResearchHistory(Path(folder)/'history.sqlite3',threading.RLock())
            t=1795503599999
            row={'symbol':'TESTUSDT','lastClosed5m':t,'price':100.,'atr5mPct':.2,
                'researchCandidates':[{'id':'F'+str(i),'version':'v1','direction':'UP','score':None} for i in range(12)]}
            h.record_and_evaluate(row,[],t+1);h.record_and_evaluate(row,[],t+1)
            self.assertEqual(sum(r['n'] for r in h.summary()['candidates']),12)
            self.assertEqual(h.pending_symbols(t+1),{'TESTUSDT'})
            candles=[{'closeTime':t+300000*i,'close':101.,'high':101.2,'low':99.9} for i in range(1,13)]
            h.record_and_evaluate(dict(row,researchCandidates=[]),candles,t+3600001)
            self.assertEqual(sum(r['n'] for r in h.summary()['outcomes']),72)
            self.assertTrue(all(r['state']=='TARGET' for r in h.summary()['outcomes']))
            self.assertFalse(h.pending_symbols(t+3600001))
    def test_missing_not_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            h=ResearchHistory(Path(folder)/'history.sqlite3',threading.RLock());t=1795503599999
            h.record_and_evaluate({'symbol':'TESTUSDT','lastClosed5m':t,'price':100.,'atr5mPct':.2,
                'researchCandidates':[{'id':'F','version':'v1','direction':'DOWN','score':None}]},[],t+1)
            h.pending_symbols(t+25*3600000)
            self.assertEqual({r['state'] for r in h.summary()['outcomes']},{'UNOBSERVED'})
if __name__=='__main__':unittest.main()
