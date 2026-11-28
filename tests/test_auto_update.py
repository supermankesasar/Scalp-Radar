import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import auto_update as u

def result(code=0,out='',err=''):
    return subprocess.CompletedProcess([],code,out,err)

class AutoUpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
        (self.root/'.git').mkdir()
        self.addCleanup(patch.stopall)
        patch.object(u,'ROOT',self.root).start()
        patch.object(u,'scanner_running',return_value=False).start()
        self.calls=[]
        self.head='old'
        self.target='new'
        self.dirty=''
        self.origin=next(iter(u.ORIGINS))
        self.branch='main'
        self.fetch_code=0
        self.ancestor=0
        def run(*args,**kwargs):
            self.calls.append(args)
            if args==('rev-parse','--show-toplevel'):return result(out=str(self.root))
            if args==('remote','get-url','origin'):return result(out=self.origin)
            if args==('branch','--show-current'):return result(out=self.branch)
            if args[0]=='status':return result(out=self.dirty)
            if args==('rev-parse','HEAD'):return result(out=self.head)
            if args[0]=='fetch':return result(self.fetch_code,err='network offline')
            if args==('rev-parse','refs/remotes/origin/main'):return result(out=self.target)
            if args[0]=='merge-base':return result(self.ancestor)
            if args[0]=='merge':
                self.head=self.target
                return result()
            raise AssertionError(args)
        patch.object(u,'git',side_effect=run).start()
    def test_fast_forward_only(self):
        self.assertEqual(u.update(),'new')
        self.assertIn(('merge','--ff-only','--no-overwrite-ignore','new'),self.calls)
    def test_already_current(self):
        self.target='old'
        self.assertEqual(u.update(),'old')
        self.assertFalse(any(x[0]=='merge' for x in self.calls))
    def test_offline_keeps_existing(self):
        self.fetch_code=1
        self.assertEqual(u.update(),'old')
        self.assertFalse(any(x[0]=='merge' for x in self.calls))
    def test_dirty_tracked_refuses(self):
        self.dirty=' M app.py'
        with self.assertRaisesRegex(RuntimeError,'Local tracked'):
            u.update()
        self.assertFalse(any(x[0]=='fetch' for x in self.calls))
    def test_wrong_origin_refuses(self):
        self.origin='https://example.com/other.git'
        with self.assertRaisesRegex(RuntimeError,'origin'):u.update()
    def test_wrong_branch_refuses(self):
        self.branch='dev'
        with self.assertRaisesRegex(RuntimeError,'Not on main'):u.update()
    def test_divergence_refuses(self):
        self.ancestor=1
        with self.assertRaisesRegex(RuntimeError,'diverged'):u.update()
        self.assertFalse(any(x[0]=='merge' for x in self.calls))
    def test_running_refuses(self):
        u.scanner_running.return_value=True
        with self.assertRaisesRegex(RuntimeError,'Scanner is running'):u.update()
        self.assertEqual(self.calls,[])
    def test_zip_folder_refuses(self):
        (self.root/'.git').rmdir()
        with self.assertRaisesRegex(RuntimeError,'ZIP folder'):u.update()

if __name__=='__main__':unittest.main()
