import subprocess,tempfile,unittest,threading
from pathlib import Path
from unittest.mock import Mock,patch
import local_runner as r
import app

class LiveUpdateTests(unittest.TestCase):
    def test_update_waits_for_child_exit(self):
        with tempfile.TemporaryDirectory() as d:
            req=Path(d)/'stop'
            child=Mock();child.poll.return_value=None
            def wait(timeout=None):
                if not req.exists():raise subprocess.TimeoutExpired('app',timeout)
                self.assertEqual(req.read_text(),'new')
                return 0
            child.wait.side_effect=wait
            with patch.object(r,'check_update',return_value=('old','new')),patch.object(r,'apply_update') as merge:
                self.assertEqual(r.monitor(child,req,True),(0,('old','new')))
                merge.assert_not_called()
    def test_failed_shutdown_does_not_offer_update(self):
        with tempfile.TemporaryDirectory() as d:
            req=Path(d)/'stop'
            child=Mock();child.poll.return_value=None
            child.wait.side_effect=[subprocess.TimeoutExpired('app',60),75]
            with patch.object(r,'check_update',return_value=('old','new')):
                self.assertEqual(r.monitor(child,req,True),(75,None))
    def test_no_change_keeps_running(self):
        with tempfile.TemporaryDirectory() as d:
            req=Path(d)/'stop';child=Mock()
            child.wait.side_effect=[subprocess.TimeoutExpired('app',60),0]
            with patch.object(r,'check_update',return_value=('same','same')):
                self.assertEqual(r.monitor(child,req,True),(0,None))
            self.assertFalse(req.exists())
    def test_drain_blocks_new_scan(self):
        drain=threading.Event();drain.set()
        with patch.object(app,'DRAIN_REQUEST',drain),patch.dict(app.SCAN_STATE,{'running':False,'completedAt':None}),patch.object(app.threading,'Thread') as worker:
            state,*_=app.schedule_scan(force=True)
            self.assertFalse(state['running'])
            worker.assert_not_called()
if __name__=='__main__':unittest.main()
