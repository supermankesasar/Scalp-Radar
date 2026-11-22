"""RSI risk badges are independent of trading signals and reversible thresholds."""
import json,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import indicator_settings,scalp_engine,swing_engine
from rsi_alerts import warning_values

class RSIWarningTests(unittest.TestCase):
    def test_strict_thresholds_and_timeframe(self):
        cfg=dict(indicator_settings.DEFAULTS)
        self.assertFalse(warning_values(60,cfg,'5m')['rsiRiskLong'])
        self.assertTrue(warning_values(60.1,cfg,'5m')['rsiRiskLong'])
        self.assertFalse(warning_values(40,cfg,'1h')['rsiRiskShort'])
        self.assertTrue(warning_values(39.9,cfg,'1h')['rsiRiskShort'])
        self.assertEqual(warning_values(65,cfg,'5m')['rsiRiskTimeframe'],'5m')
        self.assertEqual(warning_values(35,cfg,'1h')['rsiRiskTimeframe'],'1h')
    def test_invalid_values_do_not_raise_false_alarms(self):
        cfg=dict(indicator_settings.DEFAULTS)
        for value in (None,'not numeric',float('nan'),float('inf'),-2,110):
            got=warning_values(value,cfg,'5m')
            self.assertIsNone(got['rsiRiskValue'])
            self.assertFalse(got['rsiRiskLong'])
            self.assertFalse(got['rsiRiskShort'])
    def test_custom_warning_values_do_not_change_score(self):
        cfg=dict(indicator_settings.DEFAULTS)
        warm=dict(cfg,rsi_warning_long=55,rsi_warning_short=45)
        self.assertFalse(warning_values(58,cfg,'5m')['rsiRiskLong'])
        self.assertTrue(warning_values(58,warm,'5m')['rsiRiskLong'])
        self.assertFalse(warning_values(42,cfg,'5m')['rsiRiskShort'])
        self.assertTrue(warning_values(42,warm,'5m')['rsiRiskShort'])
    def test_legacy_five_field_settings_load_with_new_defaults(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'indicator_settings.sqlite3'
            legacy={k:v for k,v in indicator_settings.DEFAULTS.items()
                    if k not in ('rsi_warning_long','rsi_warning_short')}
            legacy['min_score']=71
            with sqlite3.connect(path) as db:
                db.execute('''CREATE TABLE config(id INTEGER PRIMARY KEY CHECK(id=1),
                       payload TEXT NOT NULL,revision INTEGER NOT NULL,
                       updated_ms INTEGER NOT NULL)''')
                db.execute('INSERT INTO config VALUES(1,?,4,1234)',(json.dumps(legacy),))
            with patch.object(indicator_settings,'DB_PATH',path):
                current=indicator_settings.current()
                self.assertEqual(current['revision'],4)
                self.assertEqual(current['values']['min_score'],71)
                self.assertEqual(current['values']['rsi_warning_long'],60)
                self.assertEqual(current['values']['rsi_warning_short'],40)
                after=indicator_settings.save(current['values'])
                self.assertEqual(after['revision'],4)
                changed=dict(current['values'],rsi_warning_long=62)
                self.assertEqual(indicator_settings.save(changed)['revision'],5)
                self.assertEqual(indicator_settings.current()['values']['min_score'],71)
    def test_scalp_engine_includes_warning_from_5m(self):
        cfg=dict(indicator_settings.DEFAULTS)
        one={'close':100,'atr14':1,'ema21':99,'macdHistogram':1,'volumeRatio':1.2}
        five={'close':100,'atr14':1,'ema21':99,'rsi14':65,'volumeRatio':1.2}
        tf15={'close':100,'ema21':99,'rsi14':58}
        hour={'close':100,'ema21':99}
        data={'1m':[{'close':99.9},{'close':100,'open':99.9}],
              '5m':[{'close':99.9},{'close':100}], '15m':[{'close':100}], '1h':[{'close':100}]}
        inds={'1m':one,'5m':five,'15m':tf15,'1h':hour}
        result=scalp_engine.score_and_candidates(data,inds,cfg,lambda ind:'BULLISH',
             lambda bars:(99.0,0),lambda series:62,lambda *args:False)
        self.assertTrue(result['potentialUp'])
        self.assertTrue(result['rsiRiskLong'])
        self.assertFalse(result['rsiRiskShort'])
        self.assertEqual(result['rsiRiskTimeframe'],'5m')
        self.assertEqual(result['rsiRiskValue'],65)
    def test_swing_engine_includes_warning_from_1h(self):
        cfg=dict(indicator_settings.DEFAULTS)
        f={'close':100,'atr14':1,'ema21':101,'macdHistogram':-1,'volumeRatio':1.5,'rsi14':42}
        hour={'close':100,'ema21':101,'rsi14':35}
        four={'close':100,'ema21':101}
        eight={'close':100,'ema21':101}
        day={'close':100,'atr14':1,'ema21':101}
        data={'15m':[{'close':101,'open':101},{'close':100,'open':101}],
              '1h':[{'close':101},{'close':100}], '4h':[{'close':101}],
              '8h':[{'close':101}],'1d':[{'close':101}],
              '1w':[{'close':101}]*40}
        inds={'15m':f,'1h':hour,'4h':four,'8h':eight,'1d':day}
        with patch.object(swing_engine,'weekly_regime',return_value='BEARISH'):
            result=swing_engine.score_and_candidates(
                 data,inds,cfg,lambda ind:'BEARISH',lambda a,b:[],
                 None,lambda series:37,lambda *args:False,-1.2)
        self.assertTrue(result['potentialDown'])
        self.assertTrue(result['rsiRiskShort'])
        self.assertFalse(result['rsiRiskLong'])
        self.assertEqual(result['rsiRiskTimeframe'],'1h')

if __name__=='__main__':unittest.main()
