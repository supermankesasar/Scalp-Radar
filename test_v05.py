"""New 0.5 regression tests; no external Binance calls."""
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from signals import SignalStore
import app

T = 1_900_000_000_000


def event_row(sym, score=80, direction='UP', price=100., bar=T):
    return {
        'symbol':sym, 'price':price, 'lastClosed5m':bar,
        'potentialUp':direction=='UP','potentialDown':direction=='DOWN',
        'longScore':score if direction=='UP' else 0,
        'shortScore':score if direction=='DOWN' else 0,
        'atr5mPct':.30, 'turnover24h':30_000_000,
        'pct15m':0,'pct60m':0, 'pct24h':0
    }


def candle(close=100., when=T, high=None, low=None):
    return {'closeTime':when,'close':close,'high':close if high is None else high,'low':close if low is None else low}


class Top5Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.store=SignalStore(Path(self.temp.name)/'test.sqlite')
    def tearDown(self):
        self.temp.cleanup()

    def test_top5_replaces_weakest_but_preserves_audit(self):
        for n,score in enumerate([70,74,79,81,83]):
            self.assertTrue(self.store.activate_top_candidate(event_row(f'COIN{n}USDT',score),[candle()], 'UP', T))
        self.assertEqual(len(self.store.active_pending(T)),5)
        self.assertFalse(self.store.activate_top_candidate(event_row('SLOWUSDT',69),[candle()], 'UP', T))
        self.assertTrue(self.store.activate_top_candidate(event_row('TOPUSDT',94),[candle()], 'UP', T))
        scores=[x['initialScore'] for x in self.store.active_pending(T)]
        self.assertEqual(sorted(scores),[74,79,81,83,94])
        archives=self.store.audit_events()
        self.assertEqual(len([e for e in archives if e['status']=='EXPIRED' and e['endReason']=='RANK_REPLACED']),1)
        self.assertEqual(len([e for e in archives if e['status']=='PENDING']),5)

    def test_future_quote_not_same_as_closed_candle_target(self):
        self.store.activate_top_candidate(event_row('WICKUSDT'),[candle()],'UP',T)
        # Quote rose 1.5% and wick touched, but candle closes below target.
        q=self.store.fast_update('WICKUSDT',[candle(),candle(100.2,T+300_000,high=102)],101.5,T+301_000)
        self.assertIn('POTENSI_NAIK',q['categories'])
        self.assertEqual(self.store.active_pending(T+301_000)[0]['status'],'PENDING')
        # Next CLOSED candle reaches threshold.
        q=self.store.fast_update('WICKUSDT',[candle(),candle(100.2,T+300_000,high=102),candle(100.9,T+600_000)],100.8,T+601_000)
        self.assertIn('SUDAH_NAIK',q['categories'])
        self.assertNotIn('POTENSI_NAIK',q['categories'])
        self.assertEqual(len(self.store.active_pending(T+601_000)),0)
        self.assertEqual(self.store.audit_events()[0]['endReason'],'TARGET_REACHED')
        self.assertEqual(self.store.audit_events()[0]['confirmedAt'],T+600_000)

    def test_expiry_and_archive(self):
        self.store.activate_top_candidate(event_row('TIMEUSDT'),[candle()],'UP',T)
        self.assertEqual(len(self.store.active_pending(T+16*60_000)),0)
        archive=self.store.audit_events()[0]
        self.assertEqual(archive['status'],'EXPIRED')
        self.assertEqual(archive['endReason'],'TIMEOUT_UNOBSERVED')
        self.assertEqual(self.store.watch_symbols(now_ms=T+16*60_000),[])

    def test_quotes_do_not_modify_original_candle_baseline(self):
        r=event_row('BASEUSDT',85)
        self.store.activate_top_candidate(r,[candle()],'UP',T)
        self.store.fast_update('BASEUSDT',[candle()],101.0,T+15_000)
        e=self.store.active_pending(T+15_000)[0]
        self.assertEqual(e['baselinePrice'],100.)
        self.assertAlmostEqual(e['currentMarketPct'],1.0)
        self.assertIn('BASEUSDT',self.store.watch_symbols(now_ms=T+15_000))


class ScannerIntegrationTop5Tests(unittest.TestCase):
    def test_full_batch_only_promotes_five_highest_scores(self):
        with tempfile.TemporaryDirectory() as td:
            original=app.STORE
            try:
                app.STORE=SignalStore(Path(td)/'integrated.sqlite3')
                now=int(time.time()*1000)
                close_time=now-120_000
                ranks=[68,76,83,92,88,74,90]
                tickers=[{'symbol':f'B{i}USDT','turnover24h':50_000_000,'change24h':0}
                         for i in range(len(ranks))]
                def make_row(t, is_tracked=False):
                    num=int(t['symbol'][1])
                    r=event_row(t['symbol'],ranks[num],bar=close_time)
                    r['_recent5m']=[candle(when=close_time)]
                    return r
                with app.SCAN_LOCK:
                    app.SCAN_STATE.update({'generation':121,'running':True,'rows':[], 'processed':0,
                        'total':0,'eligible':0,'universe':0,'errors':[], 'startedAt':now,
                        'completedAt':None,'mode':'all','minTurnover':30000000})
                counts={'universe':7,'eligible':7,'missingTicker':0,'trackedExtra':0}
                with patch.object(app,'active_tickers',return_value=(tickers,counts)),                     patch.object(app,'scan_symbol',side_effect=make_row),                     patch.object(app,'latest_quotes',return_value={t['symbol']:100.1 for t in tickers}):
                    app.scan_job(121,'all',30000000)
                active=app.STORE.active_pending()
                self.assertEqual(len(active),5)
                self.assertEqual(sorted(e['initialScore'] for e in active),[76,83,88,90,92])
                self.assertEqual(app.SCAN_STATE['processed'],7)
                self.assertFalse(app.SCAN_STATE['errors'],app.SCAN_STATE['errors'])
            finally:
                app.STORE=original


class CandidateTests(unittest.TestCase):
    def test_ranking_liquidity_age_and_chase_safeguards(self):
        now=T+120_000
        good=event_row('GOODUSDT',90,bar=T)
        other=event_row('OTHERUSDT',85,bar=T)
        stale=event_row('OLDUSDT',99,bar=T-600_000)
        illiquid=event_row('ILLIQUSDT',100,bar=T);illiquid['turnover24h']=9_000_000
        chasing=event_row('CHASEUSDT',100,bar=T)
        quotes={x:100.1 for x in ('GOODUSDT','OTHERUSDT','OLDUSDT','ILLIQUSDT')}
        quotes['CHASEUSDT']=101.5
        selected=app.promotion_candidates([good,other,stale,illiquid,chasing],now_ms=now,quote_prices=quotes)
        self.assertEqual([r[3]['symbol'] for r in selected],['GOODUSDT','OTHERUSDT'])

    def test_overbought_rsi_separate_from_confirmed_short(self):
        candle={'open':100,'close':99.8}
        self.assertTrue(app.rsi_reversal_watch(76,71,candle,-0.2))
        self.assertFalse(app.rsi_reversal_watch(76,77,candle,-0.2))
        self.assertFalse(app.rsi_reversal_watch(76,71,{'open':99,'close':100},-0.2))
        self.assertFalse(app.rsi_reversal_watch(76,71,candle,+0.2))
        self.assertTrue(app.rsi_reversal_watch(84,71,candle,-0.2))
        self.assertFalse(app.rsi_reversal_watch(69,65,candle,-0.2))
        self.assertTrue(app.rsi_reversal_watch(76,71,candle,-0.2,75))
        self.assertFalse(app.rsi_reversal_watch(74,71,candle,-0.2,75))

if __name__=='__main__':unittest.main()