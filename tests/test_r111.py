import json,sqlite3,tempfile,threading,unittest
from pathlib import Path
from filters import r11,r111
from radar_r111 import RadarR111,movement
from stream_engine import StreamEngine,stream_groups

def bars(n,step,end,price=100):
    rows=[]
    for i in range(n):
        t=end-(n-1-i)*step;p=price+i*.10;c=p+.05
        rows.append([t-step+1,p,c+.01,p-.01,c,1,t,100,10,1,75,'0'])
    return rows

class R111Tests(unittest.TestCase):
    def test_native_closed_alignment(self):
        cut=7200000-1
        ctx=r111.native_context(bars(4,900000,cut),bars(2,3600000,cut),cut)
        self.assertEqual(ctx['structure15'],'UP')
        self.assertIsNotNone(ctx['ret30Closed'])
        self.assertIsNone(r111.native_context(bars(4,900000,cut+900000),[],cut))
    def test_depth_snapshot_and_disconnect(self):
        e=StreamEngine();e.set_symbols({'AAAUSDT'});t=1800000000000
        e.connection('depth',['AAAUSDT'],True,t-10)
        e.ingest({'e':'depthUpdate','s':'AAAUSDT','T':t,'u':1,'b':[['100','2']],'a':[['100.05','2']]},t+1)
        with tempfile.TemporaryDirectory() as d:
            h=RadarR111(Path(d)/'test.db',threading.RLock(),e)
            q,sp,r=h.market('AAAUSDT',t+2,'UP')
            self.assertEqual(q,100.05);self.assertEqual(r,'BOOK_OK')
            self.assertEqual(h.market('AAAUSDT',t+2,'DOWN')[0],100)
            self.assertEqual(h.market('AAAUSDT',t+6000,'UP')[2],'BOOK_STALE')
            e.connection('depth',['AAAUSDT'],False,t+3)
            self.assertEqual(h.market('AAAUSDT',t+4,'UP')[2],'BOOK_MISSING')
    def test_groups_keep_total_and_isolate_minute(self):
        groups=stream_groups({'X%dUSDT'%i for i in range(516)})
        candles=[g for g in groups if g[1]=='candles']
        self.assertEqual(sum(len(g[3]) for g in candles),516*5)
        self.assertTrue(all(all(x.endswith('@kline_1m') for x in g[3]) or all(not x.endswith('@kline_1m') for x in g[3]) for g in candles))
    def test_context_gate_and_direction_reset(self):
        cut=7200000-1;rows=bars(61,60000,cut)
        f=r11.features(rows,cut);f.update(direction='UP',setup='CONTINUATION',trigger=True,watch=True)
        x=r111.enrich(f,rows,None)
        self.assertFalse(x['trigger'])
        self.assertEqual(r111.advance(None,x,cut,cut+3000,f['price'],.01)['reason'],'NATIVE15_UNKNOWN')
        x=r111.enrich(f,rows,{'structure15':'DOWN','ret15Closed':-1})
        self.assertFalse(x['trigger'])
        self.assertEqual(x['entryVariant'],'CONTEXT_CONFLICT')
        x=r111.enrich(f,rows,{'structure15':'UP','ret15Closed':1})
        old={'state':'PREPARE','direction':'DOWN','cutoff':cut-60000,'prepareAt':cut-57000,'anchor':10}
        self.assertEqual(r111.advance(old,x,cut,cut+3000,f['price'],.01)['prepareAt'],cut+3000)
    def test_native_regime_fallback_is_separate(self):
        e=StreamEngine();s='BTCUSDT';e.set_symbols({s});cut=7200000-1
        e.seed(s,'15m',bars(2,900000,cut),cut+1)
        with tempfile.TemporaryDirectory() as d:
            h=RadarR111(Path(d)/'test.db',threading.RLock(),e);h.universe=[s]
            ctx=h.regime(cut,cut+15000)
            self.assertEqual(ctx['source'],'ROLLING_15M_WS')
            self.assertEqual(ctx['nativeContext']['source'],'NATIVE_CLOSED_15M')
            self.assertEqual(ctx['nativeContext']['ageMs'],0)
    def test_movement_requires_contiguous_window(self):
        cut=7200000-1;rows=bars(17,60000,cut)
        self.assertIsNotNone(movement(rows,cut))
        self.assertIsNone(movement(rows[1:],cut))
        self.assertIsNone(movement(rows,cut+60000))
    def test_coverage_classification_and_settlement(self):
        with tempfile.TemporaryDirectory() as d:
            h=RadarR111(Path(d)/'test.db',threading.RLock(),StreamEngine())
            cut=7200000-1;start=cut-900000
            with h.db() as db:
                self.assertEqual(h.compare(db,'r111_ready','AAA','UP',start,cut,10)[0],'COVERAGE_GAP')
                self.assertEqual(h.compare(db,'r111_ready','AAA','UP',start,cut,15)[0],'NO_READY_WITH_DATA')
                db.execute("INSERT INTO r111_ready(symbol,cutoff,decision,direction,entry_at,atr,setup,variant) VALUES(?,?,?,?,?,?,?,?)",('AAA',start-60000,start-50000,'UP',start,.2,'CONTINUATION','BASE_TRIGGER'))
                self.assertEqual(h.compare(db,'r111_ready','AAA','UP',start,cut,15)[0],'BEFORE_WINDOW')
                h.settle(db,cut+35*60000)
                self.assertEqual(db.execute('SELECT state FROM r111_outcomes').fetchone()[0],'UNOBSERVED')
if __name__=='__main__':unittest.main()
