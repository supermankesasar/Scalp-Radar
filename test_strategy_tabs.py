"""Scalping vs intraday: 24h change is confirmation for Intraday ONLY."""
import unittest
import math
import app

class StrategyTabsTests(unittest.TestCase):
    def test_intraday_24h_direction_filter(self):
        self.assertTrue(app.intraday_24h_confirms('UP',1.5))
        self.assertFalse(app.intraday_24h_confirms('DOWN',1.5))
        self.assertTrue(app.intraday_24h_confirms('DOWN',-0.25))
        self.assertFalse(app.intraday_24h_confirms('UP',-0.25))
        for missing in (0,0.0,None,float('nan'),float('inf'),True,'2.4'):
            self.assertFalse(app.intraday_24h_confirms('UP',missing))
            self.assertFalse(app.intraday_24h_confirms('DOWN',missing))
    def test_base_scoring_does_not_depend_on_24h_change(self):
        # Score and existing candidate rules are independent of ticker change24h;
        # 24H is used only for intraday alignment and the display.
        import inspect
        source=inspect.getsource(app.scan_symbol)
        start=source.index('    def score_for(up):')
        end=source.index('    # OI intentionally')
        self.assertNotIn('change24h',source[start:end])
        self.assertNotIn('pct24h',source[start:end])
        self.assertIn('intraday_24h_confirms',source[end:])

if __name__=='__main__':unittest.main()
