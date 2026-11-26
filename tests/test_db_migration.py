import os,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
from database_location import configured,existing_database,canonical
from migrate_database import migrate
from local_runner import stable_db

class MigrationTests(unittest.TestCase):
    def test_copy_preserves_original_and_switches(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'LOCALAPPDATA':d,'SCANNER_DB':''}):
            src=canonical();src.parent.mkdir(parents=True)
            with closing(sqlite3.connect(src)) as db:
                db.execute('CREATE TABLE t(x)')
                db.execute('INSERT INTO t VALUES(42)')
                db.commit()
            dest=Path(d)/'new'/'data'/'signals.sqlite3'
            migrate(src,dest)
            self.assertTrue(src.is_file())
            self.assertEqual(configured(),dest.resolve())
            self.assertEqual(existing_database(d),dest.resolve())
            self.assertEqual(stable_db(),dest.resolve())
            with closing(sqlite3.connect(dest)) as db:self.assertEqual(db.execute('SELECT x FROM t').fetchone()[0],42)
            with self.assertRaises(RuntimeError):migrate(src,dest)
            dest.unlink()
            with self.assertRaises(RuntimeError):existing_database(d)
            with self.assertRaises(RuntimeError):stable_db()
    def test_env_override(self):
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ,{'LOCALAPPDATA':d,'SCANNER_DB':str(Path(d)/'missing.db')}):
            with self.assertRaises(RuntimeError):existing_database(d)
if __name__=='__main__':unittest.main()
