"""Offline regression for indicator defaults and persisted threshold customization."""
import tempfile, unittest
from pathlib import Path
from unittest.mock import patch

import indicator_settings as settings
import app

class ThresholdSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.patcher=patch.object(settings,'DB_PATH',Path(self.tmp.name)/'indicator_settings.sqlite3')
        self.patcher.start()
    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()
    def test_defaults_are_safe_and_separate(self):
        s=settings.current()
        self.assertEqual(s['revision'],0)
        self.assertEqual(s['values']['rsi_watch_threshold'],70)
        self.assertEqual(s['values']['rsi_long_max'],70)
        self.assertEqual(s['values']['min_score'],68)
        self.assertEqual(s['values']['max_chase_pct'],0.30)
    def test_save_persists_after_reopen_and_versions(self):
        vals=dict(settings.DEFAULTS)
        vals.update(rsi_watch_threshold=75,min_score=72)
        first=settings.save(vals)
        self.assertEqual(first['revision'],1)
        self.assertEqual(settings.current()['values']['rsi_watch_threshold'],75)
        self.assertEqual(settings.save(vals)['revision'],1)
        self.assertEqual(settings.save(settings.DEFAULTS)['revision'],2)
        self.assertEqual(settings.current()['values']['rsi_watch_threshold'],70)
    def test_reject_unknown_missing_non_numeric_nan_or_extreme(self):
        originals=settings.current()['values']
        for corrupt in ({'rsi_watch_threshold':70},dict(settings.DEFAULTS,unknown=50),
                        dict(settings.DEFAULTS,rsi_watch_threshold=100),
                        dict(settings.DEFAULTS,max_chase_pct=float('nan')),
                        dict(settings.DEFAULTS,min_score=True)):
            with self.assertRaises(ValueError):
                settings.save(corrupt)
        self.assertEqual(settings.current()['values'],originals)
    def test_watch_threshold_70_has_no_upper_limit(self):
        bar={'open':101,'close':100}
        self.assertTrue(app.rsi_reversal_watch(84,73,bar,-.1,70))
        self.assertFalse(app.rsi_reversal_watch(69,60,bar,-.1,70))
        self.assertFalse(app.rsi_reversal_watch(84,73,bar,+.1,70))
        self.assertFalse(app.rsi_reversal_watch(84,85,bar,-.1,70))
        self.assertFalse(app.rsi_reversal_watch(84,73,bar,-.1,85))

if __name__=='__main__':unittest.main()
