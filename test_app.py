"""Offline regression tests: no Binance account and no internet required."""
import json
import math
import os
import sys
import time
import unittest
import tempfile
from pathlib import Path
from signals import SignalStore
from unittest.mock import patch
import app

BASE_SYMBOLS = ['AAAUSDT','BBBUSDT','CCCUSDT','DDDUSDT','EEEUSDT','ZZZUSDT']


def fake_candles(tf, symbol='AAAUSDT', direction=0, count=315):
    durations={'5m':300000,'15m':900000,'1h':3600000,'4h':14400000}
    ms=durations[tf]
    now=int(time.time()*1000)
    start=(now//ms-count-1)*ms
    out=[]
    for i in range(count):
        base=100 + i*.014 + math.sin(i*.45)*.16
        if tf=='5m' and i >= count-13:
            if direction==1:
                base += (i-(count-13))*.32
            if direction==-1:
                base -= (i-(count-13))*.32
        o=base-.015
        c=base
        high=base+.13
        low=base-.13
        q=650000+(i%7)*15000
        vol=q/base
        out.append([start+i*ms, str(o), str(high), str(low), str(c), str(vol), start+(i+1)*ms-1, str(q), 1000, str(vol*.54), str(q*.54), '0'])
    return out


def fake_market(endpoint, params, ttl=0):
    if endpoint.endswith('exchangeInfo'):
        symbols=[{'symbol':s,'status':'TRADING','contractType':'PERPETUAL','quoteAsset':'USDT'} for s in BASE_SYMBOLS]
        symbols += [{'symbol':'BADUSDT','status':'BREAK','contractType':'PERPETUAL','quoteAsset':'USDT'},
                    {'symbol':'BTCUSDC','status':'TRADING','contractType':'PERPETUAL','quoteAsset':'USDC'},
                    {'symbol':'DELIVERUSDT','status':'TRADING','contractType':'CURRENT_QUARTER','quoteAsset':'USDT'}]
        return {'symbols': symbols}
    if endpoint.endswith('ticker/24hr'):
        return [{'symbol':s,'quoteVolume':str(200e6-i*50e6),'priceChangePercent':str(i),'lastPrice':'102.0'} for i,s in enumerate(BASE_SYMBOLS)]
    if endpoint.endswith('klines'):
        sym=params['symbol']
        direction=1 if sym=='BBBUSDT' else -1 if sym=='CCCUSDT' else 0
        return fake_candles(params['interval'],sym,direction)[-params['limit']:]
    if endpoint.endswith('openInterestHist'):
        t=(int(time.time()*1000)//300000)*300000
        return [{'sumOpenInterest':str(1000+i*5),'sumOpenInterestValue':str(15000000+i*100000),'timestamp':t-(29-i)*300000} for i in range(30)]
    if endpoint.endswith('premiumIndex'):
        return {'markPrice':'101','lastFundingRate':'0.0001'}
    if endpoint.endswith('ticker/price'):
        return {'price':'101'}
    raise AssertionError(endpoint)


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self._tmp=tempfile.TemporaryDirectory()
        self._original_store=app.STORE
        app.STORE=SignalStore(Path(self._tmp.name)/'scanner.sqlite')
        with app.SCAN_LOCK:
            app.SCAN_STATE.update({'running':False,'rows':[],'processed':0,'total':0,'eligible':0,
                                   'errors':[],'startedAt':None,'completedAt':None,'generation':0,'limit':80,
                                   'minTurnover':30000000,'message':'Belum dipindai'})

    def tearDown(self):
        app.STORE=self._original_store
        self._tmp.cleanup()

    def test_ema_rsi(self):
        self.assertAlmostEqual(app.ema([1,2,3,4,5],3)[-1],4)
        self.assertAlmostEqual(app.rsi(list(range(40))),100)
        self.assertIsNone(app.ema([1],200)[-1])

    @patch.object(app,'request_market',side_effect=fake_market)
    def test_universe_selection(self, mock):
        self.assertEqual(len(app.active_symbols()),len(BASE_SYMBOLS))
        vals,eligible=app.active_tickers(40,30000000)
        self.assertEqual([x['symbol'] for x in vals],BASE_SYMBOLS[:4])
        self.assertEqual(eligible,4)

    @patch.object(app,'request_market',side_effect=fake_market)
    def test_dynamic_snapshot(self, mock):
        data=app.snapshot('AAAUSDT')
        self.assertEqual(data['symbol'],'AAAUSDT')
        self.assertTrue(data['openInterest']['available'])
        self.assertEqual(len(data['chart5m']),80)
        self.assertIn(data['analysis']['status'],('WAIT','WATCH LONG','WATCH SHORT'))
        with self.assertRaises(ValueError):
            app.snapshot('BADUSDT')
        with self.assertRaises(ValueError):
            app.snapshot('../../../secret')

    @patch.object(app,'request_market',side_effect=fake_market)
    def test_large_move_does_not_create_reached_without_potential(self, mock):
        t={'turnover24h':150000000,'change24h':1}
        up=app.scan_symbol(dict(t,symbol='BBBUSDT'))
        down=app.scan_symbol(dict(t,symbol='CCCUSDT'))
        self.assertGreater(up['pct60m'],0)
        self.assertLess(down['pct60m'],0)
        # Prior event is mandatory; scan_symbol alone MUST NOT have 'SUDAH' status.
        self.assertNotIn('category',up)
        self.assertNotIn('category',down)
        self.assertIn('potentialUp',up)
        self.assertIn('potentialDown',down)

    @patch.object(app,'request_market',side_effect=fake_market)
    def test_scan_job_full(self, mock):
        with app.SCAN_LOCK:
            app.SCAN_STATE.update({'generation':1,'running':True,'limit':40,'minTurnover':30000000})
        app.scan_job(1,40,30000000)
        st=app.read_scanner(40,30000000)
        self.assertFalse(st['running'])
        self.assertEqual(st['processed'],4)
        self.assertEqual(st['total'],4)
        self.assertEqual(st['errorCount'],0)
        self.assertEqual(len(st['rows']),4)
        self.assertTrue(all('categories' in r for r in st['rows']))
        self.assertTrue(all(not any(k.startswith('SUDAH') for k in r['categories']) for r in st['rows']))
        self.assertTrue(all('_recent5m' not in r for r in st['rows']))

    @patch.object(app,'request_market',side_effect=fake_market)
    def test_potential_up_down(self, mock):
        base={'close':100,'ema21':99.5,'ema200':99,'ema200Prev6':98,'rsi14':57,
              'macdHistogram':.05,'atr14':.14,'volumeRatio':1.25,'time':12345}
        i5=dict(base)
        i15=dict(base)
        it=dict(base)
        with patch.object(app,'indicators',side_effect=[i5,i15,it,it]), \
             patch.object(app,'regime',side_effect=['BULLISH','BULLISH']), \
             patch.object(app,'utc_vwap',return_value=(99,'2026-11-21')):
            up=app.scan_symbol({'symbol':'AAAUSDT','turnover24h':100000000,'change24h':.1})
        # Real synthetic data can show a small recent move, so use threshold checks rather than forcing predictions.
        self.assertTrue(up['potentialUp'])
        self.assertGreaterEqual(up['longScore'],65)
        bearish=dict(base,close=100,ema21=100.5,rsi14=43,macdHistogram=-.05)
        with patch.object(app,'indicators',side_effect=[bearish,bearish,it,it]), \
             patch.object(app,'regime',side_effect=['BEARISH','BEARISH']), \
             patch.object(app,'utc_vwap',return_value=(101,'2026-11-21')):
            down=app.scan_symbol({'symbol':'AAAUSDT','turnover24h':100000000,'change24h':-.1})
        self.assertTrue(down['potentialDown'])
        self.assertGreaterEqual(down['shortScore'],65)

    def test_invalid_config(self):
        with self.assertRaises(ValueError):
            app.read_scanner(10000,10)

if __name__ == '__main__':
    unittest.main()