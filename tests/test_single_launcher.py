import os
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
import app

ROOT=Path(__file__).resolve().parents[1]

class LauncherTests(unittest.TestCase):
    def test_unified_launcher(self):
        start=(ROOT/'START-WINDOWS.bat').read_text()
        alias=(ROOT/'run_overnight.bat').read_text()
        for flag in ('SCANNER_OVERNIGHT=1','SCANNER_BACKGROUND=1','SCANNER_LIVE_FILTER=R08_MULTI_CORE',
                     'SCANNER_OPEN_BROWSER=1','HOST=127.0.0.1'):
            self.assertIn(flag,start)
        self.assertIn('if not defined SCANNER_DB',start)
        self.assertIn('call "%~dp0START-WINDOWS.bat"',alias)
        self.assertNotIn('app.py',alias)
    def test_bind_failure_starts_no_workers(self):
        with patch.object(app,'ThreadingHTTPServer',side_effect=OSError('port busy')), patch.object(app.threading,'Thread') as worker:
            with self.assertRaises(OSError): app.serve()
            worker.assert_not_called()
    def test_browser_and_workers_after_bind(self):
        server=Mock()
        server.server_address=('127.0.0.1',8765)
        workers=[]
        def thread(*args,**kwargs):
            workers.append(kwargs['name'])
            return Mock()
        with patch.dict(os.environ,{'SCANNER_BACKGROUND':'1','SCANNER_OPEN_BROWSER':'1'}), patch.object(app,'ARCHIVE',Mock()), patch.object(app,'ThreadingHTTPServer',return_value=server), patch.object(app.threading,'Thread',side_effect=thread):
            app.serve()
        app.DRAIN_REQUEST.clear();app.APP_STOP.clear()
        self.assertEqual(workers,['scan-scheduler','fast-watch','all-pair-archive','open-dashboard'])
        server.serve_forever.assert_called_once()
        server.server_close.assert_called_once()
if __name__=='__main__':unittest.main()
