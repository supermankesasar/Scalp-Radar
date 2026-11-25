"""Offline HTTP integration smoke test with a mocked Binance transport."""
import json
import tempfile
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
import app
from signals import SignalStore
from research_history import ResearchHistory
from test_app import fake_market

class HttpApiTests(unittest.TestCase):
    def test_health_and_scanner_end_to_end(self):
        with tempfile.TemporaryDirectory() as td:
            old_store=app.STORE
            old_history=app.HISTORY
            app.STORE=SignalStore(Path(td)/'db.sqlite3')
            app.HISTORY=ResearchHistory(app.STORE.path,app.STORE.lock)
            with app.SCAN_LOCK:
                app.SCAN_STATE.update({'running':False,'rows':[],'processed':0,'total':0,
                    'eligible':0,'errors':[],'startedAt':None,'completedAt':None,'generation':0,
                    'mode':'all','requestedMode':'all','requestedMinTurnover':30000000,
                    'minTurnover':30000000,'universe':0,'missingTicker':0,'trackedExtra':0,'message':'Fresh'})
            srv=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            threading.Thread(target=srv.serve_forever,daemon=True).start()
            base='http://127.0.0.1:%d'%srv.server_port
            try:
                with patch.object(app,'request_market',side_effect=fake_market):
                    health=json.load(urllib.request.urlopen(base+'/api/health',timeout=3))
                    self.assertTrue(health['ok'])
                    self.assertEqual(health['version'],'0.5')
                    js=urllib.request.urlopen(base+'/ui.js',timeout=3).read().decode()
                    self.assertIn('modeLabel',js)
                    result={}
                    for _ in range(100):
                        result=json.load(urllib.request.urlopen(base+'/api/scan?mode=liquid&min_turnover=30000000',timeout=5))
                        if not result['running']:break
                        time.sleep(.04)
                    self.assertEqual(result.get('processed'),4)
                    self.assertEqual(result.get('universe'),6)
                    self.assertEqual(result.get('errorCount'),0)
                    self.assertEqual(len(result['rows']),4)
                    self.assertTrue(all('journeys' in r and 'categories' in r for r in result['rows']))
                    detail=json.load(urllib.request.urlopen(base+'/api/snapshot?symbol=AAAUSDT',timeout=5))
                    self.assertEqual(detail['symbol'],'AAAUSDT')
                    events=json.load(urllib.request.urlopen(base+'/api/events',timeout=3))
                    self.assertIn('events',events)
            finally:
                srv.shutdown();srv.server_close();app.STORE=old_store;app.HISTORY=old_history

if __name__=='__main__':unittest.main()