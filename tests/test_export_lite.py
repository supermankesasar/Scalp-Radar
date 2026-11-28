import csv,io,json,sqlite3,tempfile,unittest,zipfile
from pathlib import Path
from contextlib import closing
from export_lite import export,MAX_ZIP,collect
from unittest.mock import patch
class LiteTests(unittest.TestCase):
    def test_continuity_read_only_and_missing_schema(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'test.sqlite3';dest=Path(d)/'lite.zip'
            with closing(sqlite3.connect(src)) as db:
                db.executescript("""CREATE TABLE market_observations(kind TEXT,symbol TEXT,source_ts INTEGER,received_at INTEGER,payload TEXT,PRIMARY KEY(kind,symbol,source_ts));
                INSERT INTO market_observations VALUES('kline_1m','AAA',59999,60001,'[]'),('kline_1m','AAA',179999,180001,'[]'),('kline_1m','BBB',179999,180001,'[]');
                CREATE TABLE r11_cycles(cutoff INTEGER PRIMARY KEY,universe INTEGER,eligible INTEGER);
                INSERT INTO r11_cycles VALUES(1,10,5);""")
                db.commit()
            before=src.read_bytes()
            export(src,dest,coin='AAA',now=240000)
            self.assertEqual(src.read_bytes(),before)
            self.assertLessEqual(dest.stat().st_size,MAX_ZIP)
            with zipfile.ZipFile(dest) as z:
                s=json.loads(z.read('summary.json'));self.assertEqual(s['sections']['r11_coverage_all'][0]['eligibleShare'],.5)
                self.assertIn('r111_coverage_all',s['unavailable'])
                c=list(csv.DictReader(io.StringIO(z.read('coin_continuity.csv').decode())))
                self.assertEqual(c[0]['missingWithinSpan'],'1');self.assertEqual(c[0]['missingRecent'],'2')
                self.assertEqual(c[1]['missingWithinSpan'],'0')
                raw=z.read('sample_candles.csv').decode();self.assertIn('AAA',raw);self.assertNotIn('BBB',raw)
                self.assertNotIn('signals.sqlite3',z.namelist())
    def test_targeted_coin_diagnostics(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'test.sqlite3';dest=Path(d)/'lite.zip'
            with closing(sqlite3.connect(src)) as db:
                db.executescript("""CREATE TABLE research_snapshots(symbol TEXT,candle_time INTEGER,recorded_at INTEGER,payload TEXT);
                INSERT INTO research_snapshots VALUES('AAA',1000,1001,'{}'),('BBB',1000,1001,'{}');
                CREATE TABLE events(symbol TEXT,started_at INTEGER);
                INSERT INTO events VALUES('AAA',2000),('BBB',2000);""")
                db.commit()
            export(src,dest,coin='AAA',now=3000,complete=True)
            with zipfile.ZipFile(dest) as z:
                for name in ('coin_research_snapshots.csv','coin_events.csv'):
                    rows=list(csv.DictReader(io.StringIO(z.read(name).decode())))
                    self.assertEqual([r['symbol'] for r in rows],['AAA'])
                m=json.loads(z.read('manifest.json'))
                self.assertEqual(m['coinDiagnostics']['symbol'],'AAA')
                self.assertIn('coin_r112_events',m['omittedDetails'])
    def test_ready_outcome_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'test.sqlite3';dest=Path(d)/'lite.zip'
            with closing(sqlite3.connect(src)) as db:
                db.executescript("""CREATE TABLE r111_ready(symbol TEXT,cutoff INTEGER,decision INTEGER,direction TEXT);
                CREATE TABLE r111_outcomes(symbol TEXT,cutoff INTEGER,state TEXT,gross_pct REAL,mfe REAL,mae REAL);
                CREATE TABLE r111_events(symbol TEXT,cutoff INTEGER,decision INTEGER,state TEXT,payload TEXT);
                INSERT INTO r111_ready VALUES('A',1,2,'UP'),('B',1,2,'UP');
                INSERT INTO r111_outcomes VALUES('A',1,'TARGET',.5,.6,-.1);
                INSERT INTO r111_events VALUES('A',1,2,'READY','{"setup":"CONTINUATION"}'),('B',1,2,'READY','{"setup":"CONTINUATION"}');""")
                db.commit()
            export(src,dest)
            with zipfile.ZipFile(dest) as z:
                r=json.loads(z.read('summary.json'))['sections']['r111_outcomes_all'][0]
                self.assertEqual(r['ready'],2);self.assertEqual(r['settled'],1);self.assertAlmostEqual(r['net020'],.3)
    def test_optional_failure_still_saves_zip(self):
        with tempfile.TemporaryDirectory() as d:
            src=Path(d)/'test.sqlite3';dest=Path(d)/'nested'/'lite.zip'
            with closing(sqlite3.connect(src)) as db:
                db.executescript("CREATE TABLE r11_cycles(cutoff INTEGER PRIMARY KEY,universe INTEGER,eligible INTEGER); INSERT INTO r11_cycles VALUES(1,10,5);")
                db.commit()
            with patch('export_lite.csv_query',side_effect=sqlite3.OperationalError('interrupted')):
                export(src,dest)
            with zipfile.ZipFile(dest) as z:
                self.assertIsNone(z.testzip())
                self.assertIn('r11_cycles',json.loads(z.read('manifest.json'))['omittedDetails'])
                self.assertEqual(json.loads(z.read('summary.json'))['sections']['r11_coverage_all'][0]['eligibleShare'],.5)
    def test_expired_summary_budget_is_explicit(self):
        with closing(sqlite3.connect(':memory:')) as db:
            db.row_factory=sqlite3.Row
            db.execute('CREATE TABLE r11_cycles(cutoff INTEGER PRIMARY KEY,universe INTEGER,eligible INTEGER)')
            result,_=collect(db,1000,deadline=0)
            self.assertIn('r11_coverage_all',result['unavailable'])
            self.assertNotIn('r11_coverage_all',result['sections'])
            self.assertIn('count:r11_cycles',result['unavailable'])
if __name__=='__main__':unittest.main()
