#!/usr/bin/env python3
"""Scalp Radar v0.5 — Top 10 active journeys, fast watch, read-only."""
from __future__ import annotations

import json
import math
import os
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from concurrent.futures.process import BrokenProcessPool
import multiprocessing
from scan_math import (ema,rsi,atr,macd_hist,parse_klines,indicators,extra_indicators,regime,utc_vwap,price_return,rsi_reversal_watch,compute_scan_math)
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from signals import SignalStore, ACTIVE_LIMIT
from filters.registry import evaluate as evaluate_filters
from filters import scalp_v2, multifactor, microstructure
from research_history import ResearchHistory
from market_archive import MarketArchive, crypto_universe, usdt_perpetual_metadata
from scan_worker import compute_full_scan,evaluate_scan_features
from stream_engine import StreamEngine, LIMIT as WS_LIMIT, TF as WS_TF, close_at
from stream_research import StreamResearch
from research_r10 import ResearchR10
from radar_r11 import RadarR11
from radar_r111 import RadarR111, restore_minutes
from runtime_r10 import Runtime
from rest_guard import REST_GUARD
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
OVERNIGHT = os.getenv('SCANNER_OVERNIGHT', '0') == '1'
LIVE_FILTER = os.getenv('SCANNER_LIVE_FILTER', 'BASELINE').upper()
if LIVE_FILTER not in ('BASELINE','SCALP_V2','R08_MULTI_CORE','R08_MULTI_FULL','R09_HYBRID'):
    raise ValueError('Unknown SCANNER_LIVE_FILTER')
# Windows spawn imports the main script as __mp_main__; do not open/mutate SQLite in CPU children.
if __name__!='__mp_main__':
    STORE = SignalStore(os.getenv('SCANNER_DB', str(ROOT / 'data' / 'signals.sqlite3')))
    HISTORY = ResearchHistory(STORE.path, STORE.lock)
    ARCHIVE = MarketArchive(STORE.path, STORE.lock) if OVERNIGHT else None
    STREAM = StreamEngine() if os.getenv('SCANNER_WEBSOCKET','0')=='1' else None
    WS_HISTORY = StreamResearch(STORE.path, STORE.lock) if STREAM is not None else None
    R10 = ResearchR10(STORE.path, STORE.lock) if os.getenv('SCANNER_R10','0')=='1' and STREAM is not None else None
    R11 = RadarR11(STORE.path, STORE.lock, STREAM) if STREAM is not None and os.getenv('SCANNER_R11','0')=='1' else None
    R111 = RadarR111(STORE.path, STORE.lock, STREAM) if R11 is not None and os.getenv('SCANNER_R111','0')=='1' else None
else:
    STORE=HISTORY=ARCHIVE=STREAM=WS_HISTORY=R10=R11=R111=None
RUNTIME = None
# Research cohort is a historical experiment only; live shadow rules apply to all scanned crypto pairs.
BASE = "https://fapi.binance.com"
SCAN_MODES = ('all', 'liquid', 'top80')
DEFAULT_MODE = 'all'
DEFAULT_TURNOVER = 30000000
SCAN_MIN_TURNOVER = (10000000, 30000000, 100000000)
# 20 symbols x four kline calls (~8 weight/symbol), separated by >= 7 seconds.
# These are conservative baseline limits; inspect Binance response headers/logs on hosting.
SCAN_BATCH_SIZE = 20
SCAN_BATCH_INTERVAL = 7.0
SCAN_MAX_WORKERS = 4  # retain bounded legacy REST concurrency

def cpu_workers(value=None,cores=None):
    cores=max(1,cores if cores is not None else (os.cpu_count() or 1))
    default=min(32,cores)
    try:requested=int(value) if value is not None else default
    except (ValueError,TypeError):requested=default
    return max(1,min(requested,48,cores))

SCAN_CPU_WORKERS=cpu_workers(os.getenv('SCANNER_CPU_WORKERS'))
CPU_POOL=None
LOCAL_CACHE_READY=threading.Event()
DRAIN_REQUEST=threading.Event()
APP_STOP=threading.Event()
SCAN_THREAD=None
SCAN_REFRESH_MS = 180000
ACTIVE_FAST_POLL_SECONDS = 30
FRESH_CANDLE_MS = 8 * 60_000
PROMOTION_MIN_TURNOVER = 10_000_000
# A live move this far in the proposed trade direction is too extended to promote.
MAX_CHASE_PCT = 0.30
CACHE = {}
CACHE_LOCK = threading.Lock()


def request_market(endpoint: str, params: dict, ttl: int = 20):
    ws_kline=STREAM is not None and endpoint=='/fapi/v1/klines' and params.get('interval') in WS_LIMIT and 'startTime' not in params and 'endTime' not in params
    if ws_kline:
        sym,tf=params['symbol'],params['interval']
        rows=STREAM.candles(sym,tf,max(1,int(params['limit'])-1),int(time.time()*1000))
        if rows is not None:
            with STREAM.lock:STREAM.cache_hits+=1
            return rows
    key = endpoint + "?" + urlencode(params)
    with CACHE_LOCK:
        hit = CACHE.get(key)
        if hit and hit[0] > time.monotonic() and not ws_kline:
            return hit[1]
    REST_GUARD.check()
    if REST_GUARD.history_delay(endpoint)>0:raise RuntimeError('Binance history request budget active')
    url = BASE + endpoint + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "ScalpMonitor/1.0 (market-data-only)", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=13) as response:
            data = json.loads(response.read().decode("utf-8"))
            REST_GUARD.observe(getattr(response, "headers", None), data if endpoint=="/fapi/v1/exchangeInfo" else None)
    except HTTPError as e:
        detail = e.read(600).decode("utf-8", "replace")
        if e.code in (403, 451):
            raise RuntimeError("Akses Binance dibatasi dari jaringan/server ini (HTTP %s). Coba jaringan yang mengizinkan akses resmi Binance." % e.code) from e
        if e.code in (418, 429):
            REST_GUARD.pause(e.headers)
            raise RuntimeError("Binance rate limit (HTTP %s). Kurangi refresh dan coba lagi." % e.code) from e
        raise RuntimeError("Binance API HTTP %s: %s" % (e.code, detail)) from e
    except (URLError, TimeoutError) as e:
        raise RuntimeError("Gagal menghubungi Binance: %s" % str(e)) from e
    if isinstance(data, dict) and "code" in data and int(data["code"]) < 0:
        raise RuntimeError("Binance API error: %s" % str(data.get("msg", data["code"])))
    with CACHE_LOCK:
        CACHE[key] = (time.monotonic() + ttl, data)
    if ws_kline and isinstance(data,list):
        STREAM.seed(sym,tf,data,int(time.time()*1000))
        with STREAM.lock:STREAM.rest_hits+=1
    return data


def interest_metrics(hist):
    valid = [r for r in hist if float(r.get('sumOpenInterest', '0')) > 0]
    if len(valid) < 13:
        return {"available": False, "reason": "Riwayat OI kurang dari 13 titik 5m"}
    def delta(a, b):
        den = float(valid[a]['sumOpenInterest'])
        return ((float(valid[b]['sumOpenInterest']) / den) - 1) * 100 if den else None
    return {
        "available": True,
        "timestamp": int(valid[-1]['timestamp']),
        "openContractsBase": float(valid[-1]['sumOpenInterest']),
        "notionalUSDT": float(valid[-1].get('sumOpenInterestValue', 0)),
        "delta5mPct": delta(-2,-1), "delta15mPct": delta(-4,-1), "delta60mPct": delta(-13,-1),
    }


def build_analysis(data):
    ind = data['indicators']
    trend1 = regime(ind['1h'])
    trend4 = regime(ind['4h'])
    mode = trend1 if trend1 == trend4 and trend1 != "MIXED" else "MIXED"
    i5, i15 = ind['5m'], ind['15m']
    close = i5['close']
    vwap = data['vwap']['value']
    oi = data['openInterest']
    reasons = []
    rsi15 = i15['rsi14']
    vrel = i5['volumeRatio']
    long_ok = (mode == "BULLISH" and close > i5['ema21'] and (vwap is not None and close > vwap)
        and 50 <= rsi15 <= 70 and i5['macdHistogram'] > 0 and vrel >= 1.1)
    short_ok = (mode == "BEARISH" and close < i5['ema21'] and (vwap is not None and close < vwap)
        and 30 <= rsi15 <= 50 and i5['macdHistogram'] < 0 and vrel >= 1.1)
    if mode == "MIXED":
        reasons.append("Tren EMA200 1H dan 4H belum searah; hindari memaksakan entry.")
    else:
        reasons.append("Tren EMA200 1H dan 4H searah: %s." % mode)
    reasons.append("RSI 15m %.1f; volume candle 5m %.2fx rata-rata 20 candle sebelumnya." % (rsi15, vrel))
    if vwap is not None:
        reasons.append("Candle 5m terakhir %s VWAP harian UTC." % ("di atas" if close > vwap else "di bawah"))
    if oi.get('available'):
        d15 = oi['delta15mPct']
        reasons.append("OI 15m %+.2f%%; menunjukkan perubahan total posisi, bukan arah LONG/SHORT." % d15)
    else:
        reasons.append("Data OI tidak tersedia, hindari menyimpulkan arah posisi futures.")
    state = "WATCH LONG" if long_ok else "WATCH SHORT" if short_ok else "WAIT"
    atr5 = i5['atr14']
    risk = None
    if state != "WAIT" and atr5:
        distance = atr5 * 1.5
        risk = {
            "referenceClose": close, "stopCandidate": close - distance if long_ok else close + distance,
            "targetCandidate": close + distance*1.5 if long_ok else close - distance*1.5,
            "rr": 1.5, "warning": "Level indikatif dari candle 5m tertutup; bukan order atau rekomendasi eksekusi."
        }
    return {"trend1h":trend1,"trend4h":trend4,"marketRegime":mode,"status":state,"reasons":reasons,"riskIllustration":risk}


def snapshot(symbol):
    if not re.fullmatch(r"[A-Z0-9]{3,30}", symbol) or symbol not in active_symbols():
        raise ValueError("Pair tidak aktif sebagai USDT perpetual di Binance Futures.")
    now_ms = int(time.time() * 1000)
    endpoints = {
        "5m": ("/fapi/v1/klines", {"symbol":symbol,"interval":"5m","limit":400}, 24),
        "15m": ("/fapi/v1/klines", {"symbol":symbol,"interval":"15m","limit":260}, 60),
        "1h": ("/fapi/v1/klines", {"symbol":symbol,"interval":"1h","limit":260}, 110),
        "4h": ("/fapi/v1/klines", {"symbol":symbol,"interval":"4h","limit":260}, 160),
        "oiHist": ("/futures/data/openInterestHist", {"symbol":symbol,"period":"5m","limit":30}, 45),
        "premium": ("/fapi/v1/premiumIndex", {"symbol":symbol}, 45),
        "price": ("/fapi/v1/ticker/price", {"symbol":symbol}, 15),
    }
    data = {}
    errors = []
    with ThreadPoolExecutor(max_workers=7) as pool:
        pending = {name: pool.submit(request_market, path, args, ttl) for name, (path,args,ttl) in endpoints.items()}
        for name, task in pending.items():
            try:
                data[name] = task.result()
            except Exception as e:
                if name in ("5m", "15m", "1h", "4h"):
                    raise RuntimeError("Gagal mengambil candle %s: %s" % (name, e)) from e
                errors.append(name + ": " + str(e))
    kline = {tf:parse_klines(data[tf], now_ms) for tf in ("5m","15m","1h","4h")}
    ind = {tf:indicators(kline[tf]) for tf in kline}
    vwap, reset_date = utc_vwap(kline['5m'])
    oi = interest_metrics(data['oiHist']) if 'oiHist' in data else {"available":False,"reason":"Data OI tidak dapat diambil"}
    premium = data.get('premium') or {}
    funding = float(premium['lastFundingRate'])*100 if 'lastFundingRate' in premium else None
    current = float(data['price']['price']) if 'price' in data and 'price' in data['price'] else None
    obj = {
        "symbol": symbol, "generatedAt":now_ms, "source":"Binance USD-M Futures public API",
        "indicators":ind, "vwap":{"value":vwap,"anchor":"00:00 UTC","date":reset_date},
        "openInterest":oi, "fundingRatePct":funding, "markPrice":float(premium['markPrice']) if 'markPrice' in premium else None,
        "lastPrice":current, "issues":errors,
        "chart5m": [{"t":c['time'],"close":c['close']} for c in kline['5m'][-80:]],
    }
    obj['analysis'] = build_analysis(obj)
    return obj


# --------------------- Scanner otomatis: universe & kategori ---------------------
CATEGORIES = ("POTENSI_NAIK", "SUDAH_NAIK", "POTENSI_TURUN", "SUDAH_TURUN", "NETRAL")
SCAN_LOCK = threading.Lock()
SCAN_STATE = {
    'running': False, 'rows': [], 'processed': 0, 'total': 0, 'eligible': 0,
    'universe': 0, 'missingTicker': 0, 'trackedExtra': 0,
    'errors': [], 'startedAt': None, 'completedAt': None,
    'mode': DEFAULT_MODE, 'minTurnover': DEFAULT_TURNOVER,
    'requestedMode': DEFAULT_MODE, 'requestedMinTurnover': DEFAULT_TURNOVER,
    'generation': 0, 'message': 'Belum dipindai', 'cacheSkipped':0,'cacheSkippedSymbols':[],
}


def active_symbols():
    """USDT-margined perpetual in TRADING status; no predefined watchlist."""
    exchange = request_market('/fapi/v1/exchangeInfo', {}, ttl=3600)
    return crypto_universe(exchange)


def validate_scan_options(mode, min_turnover):
    if mode not in SCAN_MODES:
        raise ValueError('Mode scan harus ALL PAIRS, LIQUID, atau TOP 80.')
    if min_turnover not in SCAN_MIN_TURNOVER:
        raise ValueError('Volume minimum LIQUID harus $10M, $30M, atau $100M.')


def active_tickers(mode=DEFAULT_MODE, min_turnover=DEFAULT_TURNOVER, tracked=None):
    """Return selected perpetual contracts and transparent counts for each scan mode.

    ALL never silently filters low-volume symbols. Tracked symbols are retained
    outside the LIQUID/TOP80 cut, so potential->reached history is not lost.
    """
    validate_scan_options(mode, min_turnover)
    metadata=usdt_perpetual_metadata(request_market('/fapi/v1/exchangeInfo',{},ttl=3600))
    available=set(metadata)
    if STREAM is not None:STREAM.set_symbols(available)
    tickers = request_market('/fapi/v1/ticker/24hr', {}, ttl=120)
    by_symbol = {}
    if not isinstance(tickers, list):
        raise RuntimeError('Format ticker 24h Binance tidak dikenali')
    for t in tickers:
        symbol = t.get('symbol')
        if symbol not in available:
            continue
        try:
            quote_volume = max(0, float(t['quoteVolume']))
            last = float(t.get('lastPrice', 0))
            pct24h = float(t.get('priceChangePercent', 0))
        except (KeyError, ValueError, TypeError):
            continue
        if not all(map(math.isfinite, (quote_volume, last, pct24h))) or last <= 0:
            continue
        by_symbol[symbol] = {
            'symbol': symbol, 'turnover24h': quote_volume, 'change24h': pct24h,
            'tickerAvailable': True,
        }
    # Missing 24h tickers are still scanned in ALL mode; candle history may
    # be insufficient, which gets counted as a per-symbol failure rather than hidden.
    all_tickers = [by_symbol.get(sym, {
        'symbol': sym, 'turnover24h': 0.0, 'change24h': None,
        'tickerAvailable': False,
    }) for sym in available]
    for row in all_tickers:
        row['_universe_size']=len(available)
        row['contractType']=metadata[row['symbol']]['contractType']
        row['underlyingType']=metadata[row['symbol']]['underlyingType']
        row['universeVersion']='USDT_PERP_ALL_V2'
    all_tickers.sort(key=lambda r:(-r['turnover24h'], r['symbol']))
    if mode == 'all':
        selected = list(all_tickers)
    elif mode == 'liquid':
        selected = [r for r in all_tickers if r['tickerAvailable'] and r['turnover24h'] >= min_turnover]
    else:
        selected = [r for r in all_tickers if r['tickerAvailable']][:80]
    eligible = len(selected)
    seen = {x['symbol'] for x in selected}
    extras = [r for r in all_tickers if r['symbol'] in (tracked or set()) and r['symbol'] not in seen]
    selected.extend(extras)
    return selected, {
        'universe': len(available), 'eligible': eligible,
        'missingTicker': len(available) - len(by_symbol),
        'trackedExtra': len(extras),
    }


def scan_symbol(ticker, is_tracked=False, cache_only=False, scan_now=None):
    """Closed candles only; OI intentionally optional and queried for classified rows."""
    symbol = ticker['symbol']
    now = int(time.time() * 1000) if scan_now is None else scan_now
    raw_sets={}
    for tf,limit in (('5m',310),('15m',230),('1h',230),('4h',230)):
        if cache_only:
            candles=STREAM.candles(symbol,tf,limit-1,now)
            if candles is None:raise ValueError('CACHE_GAP '+tf)
        else:
            candles=request_market('/fapi/v1/klines',{'symbol':symbol,'interval':tf,'limit':limit},ttl=140)
            if ARCHIVE is not None:ARCHIVE.warmup(symbol,tf,candles,int(time.time()*1000))
        raw_sets[tf]=candles
    raw=None;minute_error=None
    want_minute=OVERNIGHT or LIVE_FILTER!='BASELINE'
    if want_minute:
        try:
            if cache_only:
                raw=STREAM.candles(symbol,'1m',99,now)
                if raw is None:raise ValueError('CACHE_GAP 1m')
            else:
                raw=request_market('/fapi/v1/klines',{'symbol':symbol,'interval':'1m','limit':100},ttl=30)
                if ARCHIVE is not None:ARCHIVE.warmup(symbol,'1m',raw,int(time.time()*1000))
        except Exception as exc:
            if any(t in str(exc).lower() for t in ('rate limit','http 429','http 418')):raise
            minute_error=str(exc)[:140]
    args=(raw_sets,raw,now,want_minute,minute_error)
    cpu_fallback=None;cpu_started=time.perf_counter()
    if cache_only and CPU_POOL is not None:
        cut=close_at(now,300000)
        micro_at=int(time.time()*1000)
        receipt=STREAM.receipt(symbol,'1m',cut)
        micro=STREAM.minute(symbol,cut,micro_at) if receipt is not None and receipt<=micro_at and 0<=micro_at-cut<=15000 else {}
        db_path=str(ARCHIVE.path) if ARCHIVE is not None else None
        breadth=None
        if ARCHIVE is not None:
            try:
                breadth=ARCHIVE.breadth_for(symbol,cut,ticker.get('_universe_size',0),ARCHIVE.breadth_returns(cut,micro_at,ticker.get('_universe_size',0)))
            except Exception:
                breadth={'sampleCount':0,'universeSize':ticker.get('_universe_size',0),'cutoff':cut}
        worker_args=(*args,symbol,ticker.get('_universe_size',0),db_path,micro,micro_at,LIVE_FILTER,breadth)
        try:result,evaluation,hybrid,selected,context_error,context_ms,worker_ms=CPU_POOL.submit(compute_full_scan,*worker_args).result()
        except BrokenProcessPool as exc:
            cpu_fallback=str(exc)[:140]
            result,evaluation,hybrid,selected,context_error,context_ms,worker_ms=compute_full_scan(*worker_args)
    else:
        result=compute_scan_math(*args)
        features=result['features'];i5=result['i5']
        features['derivatives'],features['breadth']={},{}
        context_error=None;context_started=time.perf_counter()
        if ARCHIVE is not None:
            try:
                features['derivatives'],features['breadth']=ARCHIVE.research_context(symbol,i5['time'],int(time.time()*1000),ticker.get('_universe_size',0))
            except Exception as exc:
                context_error=str(exc)[:140]
        if STREAM is not None:
            decision=int(time.time()*1000)
            receipt=STREAM.receipt(symbol,'1m',i5['time'])
            features['micro']=STREAM.minute(symbol,i5['time'],decision) if receipt is not None and receipt<=decision and 0<=decision-i5['time']<=15000 else {}
        else:features['micro']={}
        context_ms=1000*(time.perf_counter()-context_started)
        evaluation,hybrid,selected=evaluate_scan_features(features,LIVE_FILTER)
        worker_ms=result['calcMs']+context_ms
    cpu_elapsed=1000*(time.perf_counter()-cpu_started)
    features=result['features'];i5=result['i5'];t1=result['t1'];t4=result['t4']
    ret5=result['ret5'];ret15=result['ret15'];ret60=result['ret60'];atr_pct=result['atr_pct']
    threshold15=result['threshold15'];threshold60=result['threshold60'];vwap=result['vwap'];px=result['px']
    vratio=result['vratio'];rsi15=result['rsi15'];dist_ema=result['dist_ema']
    previous_rsi15=result['previous_rsi15'];reversal_rsi70=result['reversal_rsi70'];minute_error=result['minute_error']
    long_score = selected['UP']['score']
    short_score = selected['DOWN']['score']
    potential_up = selected['UP']['potential']
    potential_down = selected['DOWN']['potential']
    # OI intentionally not used to assign direction. It simply provides confirmation context.
    oi = {'available': False, 'reason': 'Hanya diambil untuk hasil terklasifikasi'}
    if STREAM is not None:
        d=features['derivatives']
        if d.get('oiDelta15') is not None:oi={'available':True,'delta15mPct':d['oiDelta15']}
    elif potential_up or potential_down or is_tracked:
        try:
            oi = interest_metrics(request_market('/futures/data/openInterestHist',
                {'symbol': symbol, 'period': '5m', 'limit': 15}, ttl=90))
        except Exception as e:
            oi = {'available': False, 'reason': str(e)[:140]}
    return {
        'symbol': symbol, 'contractType':ticker.get('contractType'), 'underlyingType':ticker.get('underlyingType'),
        'universeVersion':ticker.get('universeVersion'), 'potentialUp': bool(potential_up), 'potentialDown': bool(potential_down),
        'longScore': long_score, 'shortScore': short_score,
        'price': px, 'pct5m': ret5, 'pct15m': ret15, 'pct60m': ret60,
        'pct24h': ticker['change24h'], 'turnover24h': ticker['turnover24h'],
        'atr5mPct': atr_pct, 'trigger15mPct': threshold15, 'trigger60mPct': threshold60,
        'trend1h': t1, 'trend4h': t4, 'rsi15m': rsi15,
        'relVolume5m': vratio, 'ema15mDistancePct': dist_ema,
        'vwapBias': 'ABOVE' if vwap is not None and px > vwap else 'BELOW' if vwap is not None else 'N/A',
        'oi15mPct': oi.get('delta15mPct') if oi.get('available') else None,
        'oiAvailable': oi.get('available', False),
        'rsiPrevious15m': previous_rsi15, 'rsiReversalWatch': bool(reversal_rsi70),
        'oiNote': oi.get('reason') if not oi.get('available') else None,
        'lastClosed5m': i5['time'],
        'researchCandidates':evaluation['candidates'],
        'researchFeatures':features, 'filterBreakdown':evaluation['baseline'],
        'v2Breakdown':evaluation['v2'], 'liveFilter':LIVE_FILTER,
        'minuteError':minute_error, 'contextError':context_error,
        'r08Breakdown':evaluation['r08'], 'r09Breakdown':hybrid,
        'candleSource':'websocket' if STREAM is not None and STREAM.receipt(symbol,'5m',i5['time']) is not None else 'rest',
        'volumePhase':evaluation['volumePhase'], 'vwapDistanceATR':evaluation['vwapDistanceATR'],
        'computedAt':int(time.time()*1000),
        'cpuCalcMs':result['calcMs'],'cpuElapsedMs':cpu_elapsed,'cpuFallback':cpu_fallback,
        'contextMs':context_ms,'workerMs':worker_ms,
        '_recent5m':result['recent5m'],
    }


def promotion_candidates(rows, now_ms=None, quote_prices=None):
    """Rank fresh, liquid potential candidates for up to five watch slots.

    Candidate must still be near the baseline at the latest quote. Does not
    assert any probability or attempt to place orders.
    """
    now_ms = int(time.time()*1000) if now_ms is None else now_ms
    quote_prices = quote_prices or {}
    candidates = []
    for r in rows:
        if (r.get('turnover24h') or 0) < PROMOTION_MIN_TURNOVER:
            continue
        closed = r.get('lastClosed5m') or 0
        if closed > now_ms or now_ms - closed > FRESH_CANDLE_MS:
            continue
        px = r.get('price')
        quote = quote_prices.get(r['symbol'])
        if not px or not quote or quote <= 0:
            continue
        for direction, flag, score in (
            ('UP', r.get('potentialUp'), r.get('longScore',0)),
            ('DOWN', r.get('potentialDown'), r.get('shortScore',0)),
        ):
            if not flag:
                continue
            chase_pct = 100 * (quote / px - 1) * (1 if direction == 'UP' else -1)
            # Avoid chasing and also avoid an adverse move that has already hit
            # the paper-stop, to avoid advertising an invalidated baseline.
            if chase_pct > MAX_CHASE_PCT or chase_pct < -max(.40, r['atr5mPct']):
                continue
            candidates.append((int(score), r.get('turnover24h') or 0, direction, r))
    candidates.sort(key=lambda e:(-e[0],-e[1],e[3]['symbol'],e[2]))
    return candidates


def latest_quotes(symbols=None):
    """Binance bulk lightweight current price endpoint; quote only, not fill."""
    if STREAM is not None:
        result=STREAM.prices(symbols,int(time.time()*1000))
        # Never use stale WS prices. REST fallback only when a requested quote is absent.
        if symbols is not None and set(symbols)<=set(result):return result
    response = request_market('/fapi/v1/ticker/price', {}, ttl=15)
    if not isinstance(response, list):
        raise RuntimeError('Harga terkini bulk tidak tersedia')
    keep = None if symbols is None else set(symbols)
    result = {}
    for t in response:
        sym = t.get('symbol')
        if keep is not None and sym not in keep:
            continue
        try:
            result[sym] = float(t['price'])
        except (KeyError,ValueError,TypeError):
            pass
    return result


def _same_generation(generation):
    with SCAN_LOCK:
        return generation == SCAN_STATE['generation']


def scan_cached_universe(generation,tickers,tracked,scan_now):
    """Submit ALL ready coins without a 20-pair barrier or per-coin DB writes.
    Results are frozen at their actual completion time; publication is atomic.
    """
    started=time.perf_counter()
    cold=[t['symbol'] for t in tickers if not all(STREAM.candles(t['symbol'],tf,WS_LIMIT[tf]-1,scan_now) is not None for tf in ('5m','15m','1h','4h'))]
    cold_set=set(cold)
    ready=[t for t in tickers if t['symbol'] not in cold_set]
    with SCAN_LOCK:
        SCAN_STATE.update(cacheSkipped=len(cold),cacheSkippedSymbols=cold,processed=len(cold),
            computed=0,phase='COMPUTE',message='Analisis paralel seluruh cache siap',progressAt=int(time.time()*1000))
    cache_ms=1000*(time.perf_counter()-started)
    results=[]
    compute_started=time.perf_counter()
    with ThreadPoolExecutor(max_workers=min(64,max(8,SCAN_CPU_WORKERS*2))) as executor:
        futures={executor.submit(scan_symbol,t,t['symbol'] in tracked,True,scan_now):t['symbol'] for t in ready}
        for future in as_completed(futures):
            if not _same_generation(generation):return
            errors=[]
            try:
                row=future.result()
                results.append((row,row.get('computedAt') or int(time.time()*1000)))
                for field,label in (('minuteError','1m'),('contextError','context'),('cpuFallback','CPU fallback')):
                    if row.get(field):errors.append(row['symbol']+': '+label+' '+str(row[field]))
            except Exception as exc:
                errors.append(futures[future]+': '+str(exc))
            with SCAN_LOCK:
                SCAN_STATE['processed']+=1
                SCAN_STATE['computed']=len(results)
                SCAN_STATE['progressAt']=int(time.time()*1000)
                SCAN_STATE['errors'].extend(errors)
    compute_ms=1000*(time.perf_counter()-compute_started)
    with SCAN_LOCK:
        SCAN_STATE.update(phase='PUBLISH',message='Ranking Top 10 dan simpan hasil',progressAt=int(time.time()*1000))
    with SCAN_LOCK:SCAN_STATE['phaseMetrics']={'cacheCheckMs':cache_ms,'computeWallMs':compute_ms}
    print('[SCAN] Computed',len(results),'/',len(tickers),'cache skipped',len(cold),'in %.2fs; publishing'%(compute_ms/1000),flush=True)
    if RUNTIME:RUNTIME.beat('scan-pipeline',phase='PUBLISH',computed=len(results),cacheMs=cache_ms,computeMs=compute_ms)
    metrics={'cacheCheckMs':cache_ms,'computeWallMs':compute_ms,'dbLockWaitMs':0.,'dbBatchMs':0.}
    if results:
        try:
            rows,db_metrics=STORE.refresh_ranked_batch([r for r,_ in results],promotion_candidates,STREAM.prices)
            metrics.update(db_metrics)
            with SCAN_LOCK:
                SCAN_STATE['rows']=rows
        except Exception as exc:
            with SCAN_LOCK:SCAN_STATE['errors'].append('Publication failed: '+str(exc)[:200])
    # Record independent research even if dashboard publication failed.
    with SCAN_LOCK:
        SCAN_STATE.update(phase='STAGE_RESEARCH',message='Simpan antrean penelitian',progressAt=int(time.time()*1000))
    if RUNTIME:RUNTIME.beat('scan-pipeline',phase='STAGE_RESEARCH',**metrics)
    stage_started=time.perf_counter()
    try:HISTORY.stage_scan(results)
    except Exception as exc:
        with SCAN_LOCK:SCAN_STATE['errors'].append('Research queue: '+str(exc)[:150])
    metrics['researchStageMs']=1000*(time.perf_counter()-stage_started)
    metrics['contextSumMs']=sum(r.get('contextMs',0) for r,_ in results)
    with SCAN_LOCK:SCAN_STATE['phaseMetrics']=metrics
    print('[SCAN] DB wait %.2fs; DB publish %.2fs; research stage %.2fs'%(metrics['dbLockWaitMs']/1000,metrics['dbBatchMs']/1000,metrics['researchStageMs']/1000),flush=True)
    if RUNTIME:RUNTIME.beat('scan-pipeline',phase='DONE',**metrics)


def scan_job(generation, mode, min_turnover):
    try:
        tracked = set() if STREAM is not None and mode=='all' else STORE.active_symbols()
        research_pending = set() if STREAM is not None and mode=='all' else HISTORY.pending_symbols(int(time.time()*1000))
        tickers, info = active_tickers(mode, min_turnover, tracked | research_pending)
        with SCAN_LOCK:
            if generation != SCAN_STATE['generation']:
                return
            SCAN_STATE['total'] = len(tickers)
            SCAN_STATE.update(info)
            SCAN_STATE['message'] = 'Memindai pair dalam batch, prioritaskan volume besar'
        if not tickers:
            raise RuntimeError('Tidak ditemukan pair USDT perpetual sesuai mode filter.')

        # In WS mode the live pass never waits on per-symbol REST history.
        cache_only=STREAM is not None
        scan_now=int(time.time()*1000)
        if cache_only:
            scan_cached_universe(generation,tickers,tracked,scan_now)
            return
        # Limited batches avoid flooding futures kline endpoints when ALL is
        # selected. Rate-limit errors interrupt the remaining cycle for safety.
        stop_for_limit = False
        eligible_rows = []  # rolling pool of fresh potential setups
        recent_candles = {}
        with ThreadPoolExecutor(max_workers=min(24,max(4,SCAN_CPU_WORKERS*2)) if cache_only and CPU_POOL is not None else SCAN_MAX_WORKERS) as executor:
            for offset in range(0, len(tickers), SCAN_BATCH_SIZE):
                if not _same_generation(generation):
                    return
                started_batch = time.monotonic()
                batch = tickers[offset:offset+SCAN_BATCH_SIZE]
                cached_batch=cache_only
                staged=[]
                futures = {executor.submit(scan_symbol,t,t['symbol'] in tracked,True,scan_now) if cache_only else executor.submit(scan_symbol,t,t['symbol'] in tracked):t['symbol'] for t in batch}
                for future in as_completed(futures):
                    if not _same_generation(generation):
                        return
                    try:
                        res = future.result()
                        # Advance existing journeys, but don't flood active tab with
                        # first-come events: rank across completed batch candidates.
                        recent_candles[res['symbol']] = res['_recent5m']
                        if res.get('cpuFallback'):
                            with SCAN_LOCK:SCAN_STATE['errors'].append(res['symbol']+': CPU pool fallback '+res['cpuFallback'])
                        if res.get('minuteError'):
                            with SCAN_LOCK:
                                SCAN_STATE['errors'].append(res['symbol']+': '+res['minuteError'])
                        if res.get('contextError'):
                            with SCAN_LOCK:
                                SCAN_STATE['errors'].append(res['symbol']+': context '+res['contextError'])
                        # Ledger records all rules independently of Top10 ranking or journey rotation.
                        # Failure is visible but must not corrupt production tracking.
                        if cache_only:
                            staged.append((res,int(time.time()*1000)))
                        else:
                            try:
                                HISTORY.record_and_evaluate(res, res['_recent5m'], int(time.time()*1000))
                            except Exception as history_error:
                                with SCAN_LOCK:
                                    SCAN_STATE['errors'].append('Research ledger: '+str(history_error)[:150])
                            if R10 is not None:
                                try:R10.record5(res,int(time.time()*1000))
                                except Exception as exc:print('R10 5m ledger:',str(exc)[:160],flush=True)
                        res = STORE.refresh(res, res['_recent5m'], allow_new=False)
                        if res.get('potentialUp') or res.get('potentialDown'):
                            eligible_rows.append(res)
                        error = None
                    except Exception as exc:
                        res = None
                        error = '%s: %s' % (futures[future], str(exc))
                        if any(term in str(exc).lower() for term in ('rate limit', 'http 429', 'http 418')):
                            stop_for_limit = True
                    with SCAN_LOCK:
                        if generation != SCAN_STATE['generation']:
                            return
                        SCAN_STATE['processed'] += 1
                        SCAN_STATE['progressAt'] = int(time.time()*1000)
                        if res:
                            SCAN_STATE['rows'].append(res)
                        if error:
                            SCAN_STATE['errors'].append(error)
                if staged:
                    try:HISTORY.stage_scan(staged)
                    except Exception as exc:
                        with SCAN_LOCK:SCAN_STATE['errors'].append('Research queue: '+str(exc)[:150])
                if stop_for_limit:
                    with SCAN_LOCK:
                        SCAN_STATE['errors'].append('Rate limit Binance terdeteksi; siklus scan dihentikan untuk melindungi koneksi API.')
                    break
                # Promote highest scores seen SO FAR (rolling Top 10).
                # Fresh quote check stops misleading old candle entries.
                try:
                    wanted={r['symbol'] for r in eligible_rows}
                    quotes=STREAM.prices(wanted,int(time.time()*1000)) if cache_only else latest_quotes(wanted)
                    for score, turnover, direction, candidate in promotion_candidates(eligible_rows, quote_prices=quotes):
                        sym = candidate['symbol']
                        if STORE.activate_top_candidate(candidate, recent_candles[sym], direction):
                            match = next(iter(STORE.latest_rows(symbol=sym)),None)
                            with SCAN_LOCK:
                                if generation==SCAN_STATE['generation'] and match:
                                    for i, prior in enumerate(SCAN_STATE['rows']):
                                        if prior['symbol']==sym:
                                            SCAN_STATE['rows'][i]=match
                                            break
                except Exception as exc:
                    with SCAN_LOCK:
                        SCAN_STATE['errors'].append('Peringatan ranking/kutipan: '+str(exc)[:120])
                # Track the signal journeys already found while scanning the
                # next batch; no need for the browser to stay open.
                if offset + SCAN_BATCH_SIZE < len(tickers) and not cached_batch:
                    remaining = SCAN_BATCH_INTERVAL - (time.monotonic() - started_batch)
                    if remaining > 0:
                        time.sleep(remaining)
    except Exception as exc:
        with SCAN_LOCK:
            if generation == SCAN_STATE['generation']:
                SCAN_STATE['errors'].append('Scanner: ' + str(exc))
    finally:
        audit=None
        with SCAN_LOCK:
            if generation == SCAN_STATE['generation']:
                SCAN_STATE['running'] = False
                SCAN_STATE['completedAt'] = int(time.time()*1000)
                stopped = SCAN_STATE['processed'] < SCAN_STATE['total']
                SCAN_STATE['message'] = ('Scan terhenti sebelum selesai' if stopped else
                    'Scan selesai (sebagian menunggu cache)' if SCAN_STATE.get('cacheSkipped') else
                    'Scan selesai' if SCAN_STATE['rows'] else 'Tidak ada data berhasil dianalisis')
                audit={k:SCAN_STATE.get(k) for k in ('startedAt','completedAt','universe','total','processed','cacheSkipped','cacheSkippedSymbols','mode','errors')}
                audit['successful']=len(SCAN_STATE['rows'])
                audit['computed']=SCAN_STATE.get('computed',audit['successful']) if STREAM is not None else audit['successful']
                audit['phaseMetrics']=dict(SCAN_STATE.get('phaseMetrics',{}))
                SCAN_STATE['phase']='DONE'
                audit['cpuWorkers']=SCAN_CPU_WORKERS if CPU_POOL is not None else 0
                audit['cpuCalcMs']=sum(r.get('cpuCalcMs',0) for r in SCAN_STATE['rows'])
                audit['cpuElapsedMs']=sum(r.get('cpuElapsedMs',0) for r in SCAN_STATE['rows'])
                audit['cpuFallbacks']=sum(bool(r.get('cpuFallback')) for r in SCAN_STATE['rows'])
                audit['failed']=max(0,audit['processed']-audit['successful']-(audit['cacheSkipped'] or 0))
        if audit and audit['startedAt']:
            try:HISTORY.record_scan_cycle(audit['startedAt'],audit['completedAt'],audit)
            except Exception as exc:print('Scan cycle audit:',str(exc)[:150],flush=True)


def _saved_visible(rows, mode, min_turnover):
    """Choose already scanned rows without pretending they belong to a new scan."""
    ranked = sorted(rows, key=lambda r:-(r.get('turnover24h') or 0))
    if mode == 'all':
        chosen = ranked
    elif mode == 'liquid':
        chosen = [r for r in ranked if (r.get('turnover24h') or 0) >= min_turnover]
    else:
        chosen = ranked[:80]
    # Always retain rows with ongoing/completed signal journeys in any mode.
    keep = {r['symbol'] for r in chosen}
    return [r for r in ranked if r['symbol'] in keep or r.get('categories')]


def schedule_scan(mode=DEFAULT_MODE, min_turnover=DEFAULT_TURNOVER, force=False):
    global SCAN_THREAD
    if OVERNIGHT:
        mode = 'all'  # browser filters must not reduce the overnight scan universe
    validate_scan_options(mode, min_turnover)
    now_ms = int(time.time()*1000)
    with SCAN_LOCK:
        SCAN_STATE['requestedMode'] = mode
        SCAN_STATE['requestedMinTurnover'] = min_turnover
        running = SCAN_STATE['running']
        new_filters = (mode, min_turnover if mode == 'liquid' else None) != (
            SCAN_STATE['mode'], SCAN_STATE['minTurnover'] if SCAN_STATE['mode'] == 'liquid' else None)
        elapsed = now_ms - (SCAN_STATE['completedAt'] or 0)
        started_age = now_ms - (SCAN_STATE['startedAt'] or 0)
        new_ws_bar=STREAM is not None and close_at(now_ms-7000,300000) > (SCAN_STATE['startedAt'] or 0)
        need_start = (not running and (SCAN_STATE['completedAt'] is None or new_filters or new_ws_bar
                                      or elapsed >= SCAN_REFRESH_MS or (STREAM is not None and SCAN_STATE.get('cacheSkipped',0)>0 and elapsed>=30000) or (force and started_age >= 60000)))
        if need_start and not DRAIN_REQUEST.is_set():
            SCAN_STATE.update({
                'running': True, 'rows': [], 'processed': 0, 'total': 0, 'eligible': 0,
                'universe': 0, 'missingTicker': 0, 'trackedExtra': 0,
                'errors': [], 'cacheSkipped':0,'cacheSkippedSymbols':[], 'computed':0,'phase':'UNIVERSE','phaseMetrics':{}, 'startedAt': now_ms, 'progressAt':now_ms, 'completedAt': None,
                'mode': mode, 'minTurnover': min_turnover,
                'generation': SCAN_STATE['generation']+1,
                'message': 'Mengambil daftar USDT perpetual Binance',
            })
            job = threading.Thread(target=scan_job, args=(SCAN_STATE['generation'],mode,min_turnover), daemon=True)
            SCAN_THREAD=job
            job.start()
        # Return a shallow immutable-by-convention snapshot without SQLite I/O.
        state=dict(SCAN_STATE,rows=list(SCAN_STATE['rows']),errors=list(SCAN_STATE['errors']))
        return state,new_filters,mode,now_ms


def read_scanner(mode=DEFAULT_MODE, min_turnover=DEFAULT_TURNOVER, force=False):
    state,new_filters,mode,now_ms=schedule_scan(mode,min_turnover,force)
    fresh = state['rows']
    from_disk,active = STORE.dashboard_snapshot(now_ms)
    # While the scan progresses, snapshots may be up to 36h old: explicitly
    # mark them stale, never mistake them for fresh candle data.
    visible_disk = _saved_visible(from_disk, mode, min_turnover)
    # Quote watcher updates can be newer than the full scanner result; use
    # persisted quote+journey when its quote timestamp is newer than the row.
    persisted = {x['symbol']: x for x in visible_disk}
    combined = []
    for x in fresh:
        cached = persisted.pop(x['symbol'], None)
        if cached and (cached.get('quoteAt') or 0) > (x.get('quoteAt') or 0):
            combined.append(cached)
        else:
            combined.append(x)
    combined.extend(dict(x, stale=True) for x in persisted.values())
    pending = state['running'] and new_filters
    return {
        'running': state['running'], 'rows': combined,
        'activeSignals': len(active), 'activeLimit': ACTIVE_LIMIT,
        'signals': active,
        'processed': state['processed'], 'total': state['total'],
        'successful': len(fresh), 'computed':state.get('computed',len(fresh)) if STREAM is not None else len(fresh),
        'phase':state.get('phase'),'phaseMetrics':state.get('phaseMetrics',{}),
        'updatePending':DRAIN_REQUEST.is_set(),
        'failed': max(0,state['processed'] - (state.get('computed',len(fresh)) if STREAM is not None and state['running'] else len(fresh))-state.get('cacheSkipped',0)),
        'cacheSkipped':state.get('cacheSkipped',0),'cacheSkippedSymbols':state.get('cacheSkippedSymbols',[]),
        'eligible': state['eligible'], 'universe': state['universe'],
        'missingTicker': state['missingTicker'], 'trackedExtra': state['trackedExtra'],
        'errors': state['errors'][:10], 'errorCount': len(state['errors']),
        'startedAt': state['startedAt'], 'completedAt': state['completedAt'],
        'mode': state['mode'], 'requestedMode': mode, 'configPending': pending,
        'minTurnover': state['minTurnover'], 'requestedMinTurnover': min_turnover,
        'message': state['message'],
        'source': 'Binance USD-M Futures public API',
        'categories': list(CATEGORIES),
        'tracking': 'SQLite: status Sudah memerlukan sinyal Potensi lebih dulu dan candle berikutnya',
        'scoring': 'Aturan heuristik, bukan probabilitas atau sinyal tervalidasi',
    }


class Handler(BaseHTTPRequestHandler):
    def _reply(self, code, content, ctype):
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        route = urlparse(self.path)
        if route.path in ('/', '/index.html'):
            self._reply(200, (ROOT/'index.html').read_bytes(), 'text/html; charset=utf-8')
        elif route.path == '/manifest.webmanifest':
            self._reply(200, (ROOT/'manifest.webmanifest').read_bytes(), 'application/manifest+json')
        elif route.path == '/ui.js':
            self._reply(200, (ROOT/'ui.js').read_bytes(), 'text/javascript; charset=utf-8')
        elif route.path == '/sw.js':
            self._reply(200, (ROOT/'sw.js').read_bytes(), 'text/javascript; charset=utf-8')
        elif route.path == '/icon.png':
            self._reply(200, (ROOT/'icon.png').read_bytes(), 'image/png')
        elif route.path == '/api/health':
            self._reply(200, json.dumps({'ok':True,'version':'0.5','storage':'SQLite','activeTracked':len(STORE.active_symbols())}).encode(), 'application/json')
        elif route.path == '/api/runtime':
            self._reply(200,json.dumps(dict(RUNTIME.status(),scan={k:SCAN_STATE.get(k) for k in ('running','progressAt','processed','total','startedAt','cacheSkipped','cacheSkippedSymbols','computed','phase','phaseMetrics')},restCooldownSeconds=REST_GUARD.remaining(),stream=STREAM.status() if STREAM else None) if RUNTIME else {'enabled':False}).encode(),'application/json')
        elif route.path == '/api/radar/r11':
            self._reply(200,json.dumps(R11.status() if R11 else {'enabled':False},allow_nan=False).encode(),'application/json')
        elif route.path == '/api/radar/r111':
            self._reply(200,json.dumps(R111.status() if R111 else {'enabled':False},allow_nan=False).encode(),'application/json')
        elif route.path == '/api/research/r111':
            self._reply(200,json.dumps(R111.report() if R111 else {'enabled':False},allow_nan=False).encode(),'application/json')
        elif route.path == '/api/radar/r112':
            self._reply(200,json.dumps(R111.impulse_status() if R111 else {'enabled':False},allow_nan=False).encode(),'application/json')
        elif route.path == '/api/research/r112':
            self._reply(200,json.dumps(R111.impulse_report() if R111 else {'enabled':False},allow_nan=False).encode(),'application/json')
        elif route.path == '/api/rest-budget':
            self._reply(200,json.dumps(REST_GUARD.status()).encode(),'application/json')
        elif route.path == '/api/research/r10':
            self._reply(200,json.dumps(R10.status() if R10 else {'enabled':False}).encode(),'application/json')
        elif route.path == '/api/movement':
            result=STREAM.movement_status() if STREAM is not None else {'enabled':False}
            self._reply(200,json.dumps(result,allow_nan=False).encode(),'application/json')
        elif route.path == '/api/websocket':
            result=STREAM.status() if STREAM is not None else {'enabled':False}
            self._reply(200,json.dumps(result,allow_nan=False).encode(),'application/json')
        elif route.path == '/api/research/1m':
            result=WS_HISTORY.summary() if WS_HISTORY is not None else {'enabled':False}
            self._reply(200,json.dumps(result,allow_nan=False).encode(),'application/json')
        elif route.path == '/api/overnight':
            try:
                result = ARCHIVE.status() if ARCHIVE is not None else {'enabled':False}
                self._reply(200, json.dumps(dict(result, enabled=OVERNIGHT), allow_nan=False).encode(), 'application/json; charset=utf-8')
            except Exception as exc:
                self._reply(502, json.dumps({'error':str(exc)}).encode(), 'application/json; charset=utf-8')
        elif route.path == '/api/research':
            try:
                self._reply(200, json.dumps(HISTORY.summary(), allow_nan=False).encode(), 'application/json; charset=utf-8')
            except Exception as exc:
                self._reply(502, json.dumps({'error':str(exc)}).encode(), 'application/json; charset=utf-8')
        elif route.path == '/api/events':
            self._reply(200, json.dumps({'events':STORE.audit_events(200)}).encode(), 'application/json')
        elif route.path == '/api/scan':
            args = parse_qs(route.query)
            try:
                mode = args.get('mode', [DEFAULT_MODE])[0].lower()
                turnover = int(args.get('min_turnover', [str(DEFAULT_TURNOVER)])[0])
                payload = read_scanner(mode, turnover, args.get('force', ['0'])[0] == '1')
                self._reply(200, json.dumps(payload, allow_nan=False).encode(), 'application/json; charset=utf-8')
            except (ValueError, TypeError) as e:
                self._reply(400, json.dumps({'error': str(e)}).encode(), 'application/json; charset=utf-8')
            except Exception as e:
                self._reply(502, json.dumps({'error': str(e)}).encode(), 'application/json; charset=utf-8')
        elif route.path == '/api/snapshot':
            symbol = parse_qs(route.query).get('symbol', ['BTCUSDT'])[0]
            try:
                payload = snapshot(symbol)
                self._reply(200, json.dumps(payload, allow_nan=False).encode(), 'application/json; charset=utf-8')
            except ValueError as e:
                self._reply(400, json.dumps({'error':str(e)}).encode(), 'application/json; charset=utf-8')
            except Exception as e:
                self._reply(502, json.dumps({'error':str(e)}).encode(), 'application/json; charset=utf-8')
        else:
            self._reply(404, b'Not found', 'text/plain; charset=utf-8')

    def log_message(self, fmt, *args):
        if self.path.startswith('/api/') or self.path == '/':
            super().log_message(fmt, *args)


def fast_watch_loop():
    """Update ACTIVE signal price and 5m outcomes every 30s, independently
    of the slower full-market scanner. Closed candle determines outcome.
    """
    while not APP_STOP.is_set():
        try:
            symbols = STORE.watch_symbols(max_symbols=20)
            if symbols:
                quotes = latest_quotes(symbols)
                now = int(time.time()*1000)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    tasks = {pool.submit(request_market, '/fapi/v1/klines',
                              {'symbol':s,'interval':'5m','limit':20}, 12):s for s in symbols if quotes.get(s)}
                    for fut in as_completed(tasks):
                        symbol = tasks[fut]
                        try:
                            candles = parse_klines(fut.result(), now)
                            if candles:
                                STORE.fast_update(symbol, candles, quotes[symbol], now_ms=now)
                        except Exception as exc:
                            print('Fast watch',symbol,str(exc)[:90],flush=True)
        except Exception as exc:
            print('Fast watch error:', str(exc)[:140],flush=True)
        if RUNTIME:RUNTIME.beat('fast-watch')
        APP_STOP.wait(ACTIVE_FAST_POLL_SECONDS)


def scheduler_loop():
    """Always-on server-side scanning independent from whether phone/browser is open."""
    while not APP_STOP.is_set():
        try:
            with SCAN_LOCK:
                mode, turnover = SCAN_STATE['requestedMode'], SCAN_STATE['requestedMinTurnover']
            schedule_scan(mode, turnover)
        except Exception as exc:
            print('Background scheduler:',str(exc),flush=True)
        if RUNTIME:RUNTIME.beat('scan-scheduler')
        APP_STOP.wait(12)


def minute_research_loop():
    last=0
    while not STREAM.stop.is_set():
        now=int(time.time()*1000)
        cutoff=close_at(now-5000,60000)
        if cutoff>last:
            try:
                if RUNTIME:RUNTIME.beat('ws-coverage',**STREAM.coverage_status(now))
                count=WS_HISTORY.process(STREAM,cutoff,now,ema,atr,parse_klines,r10=R10)
                if RUNTIME:RUNTIME.beat('ws-research',count=count,cutoff=cutoff)
                last=cutoff
            except Exception as exc:
                print('WS research:',str(exc)[:160],flush=True)
        STREAM.stop.wait(1)


def scan_research_loop():
    """Drain durable research independently from the live scanner.
    A failed row remains queued and errors are observable; replay uses frozen observation time.
    """
    last_cleanup=0
    while not STREAM.stop.is_set():
        try:
            pending=HISTORY.queued_scan(16)
            for item in pending:
                if STREAM.stop.is_set():return
                row=json.loads(item['payload']);bars=json.loads(item['candles'])
                decision=item['observed_at']
                HISTORY.record_and_evaluate(row,bars,decision)
                if R10 is not None:R10.record5(row,decision)
                HISTORY.ack_scan(item['symbol'],item['candle_time'])
            now=int(time.time()*1000)
            if now-last_cleanup>=60000:
                HISTORY.pending_symbols(now);last_cleanup=now
            if RUNTIME:RUNTIME.beat('scan-research-writer',batch=len(pending),oldestMs=pending[0]['observed_at'] if pending else None,error=None)
            STREAM.stop.wait(.1 if pending else 2)
        except Exception as exc:
            if RUNTIME:RUNTIME.beat('scan-research-writer',error=str(exc)[:160])
            print('Scan research queue:',str(exc)[:160],flush=True)
            STREAM.stop.wait(5)


def local_seed_pass(symbols,now):
    """Restore all local timeframes in parallel BEFORE slower network recovery."""
    asof=now-15000
    def restore(symbol):
        count=0
        for tf in ('1m','5m','15m','1h','4h'):
            limit=WS_LIMIT[tf]-1
            if STREAM.candles(symbol,tf,limit,asof) is not None:continue
            local=ARCHIVE.cached_rows(symbol,tf,limit,asof)
            STREAM.seed(symbol,tf,local,now)
            count+=int(STREAM.candles(symbol,tf,limit,asof) is not None)
        return count
    restored=0;errors=[]
    with ThreadPoolExecutor(max_workers=min(32,max(8,SCAN_CPU_WORKERS))) as pool:
        futures={pool.submit(restore,s):s for s in symbols}
        for fut in as_completed(futures):
            try:restored+=fut.result()
            except Exception as exc:errors.append(futures[fut]+': '+str(exc)[:100])
    return restored,errors


def local_seed_loop():
    while not STREAM.stop.is_set():
        with STREAM.lock:symbols=sorted(STREAM.symbols)
        if symbols:
            try:
                count,errors=local_seed_pass(symbols,int(time.time()*1000))
                LOCAL_CACHE_READY.set()
                if RUNTIME:RUNTIME.beat('local-cache-seed',restoredTimeframes=count,errors=errors[:10],errorCount=len(errors))
            except Exception as exc:
                print('Local cache restore:',str(exc)[:150],flush=True)
                if RUNTIME:RUNTIME.beat('local-cache-seed',error=str(exc)[:150])
        STREAM.stop.wait(30 if symbols else 1)


def minute_seed_loop():
    """Network recovery stays paced and independent of local all-timeframe restore."""
    if ARCHIVE is not None:
        while not LOCAL_CACHE_READY.wait(1):
            if STREAM.stop.is_set():return
    archived={}
    while not STREAM.stop.is_set():
        with STREAM.lock:symbols=sorted(STREAM.symbols)
        # R11 gets 1m first; higher context is warmed separately from live ranking.
        for tf in ('1m','5m','15m','1h','4h'):
            step=WS_TF[tf];limit=WS_LIMIT[tf]
            for symbol in symbols:
                if STREAM.stop.is_set():return
                now=int(time.time()*1000);asof=now-15000
                if asof<step:continue
                cached=STREAM.candles(symbol,tf,limit-1,asof)
                if cached is None:
                    try:
                        raw=request_market('/fapi/v1/klines',{'symbol':symbol,'interval':tf,'limit':limit},ttl=30)
                        if ARCHIVE is not None:
                            received=int(time.time()*1000)
                            ARCHIVE.put('kline_'+tf,symbol,[(r[6],r) for r in raw],received)
                        if STREAM.stop.wait(.8):return
                    except Exception as exc:
                        print('Cache seed:',symbol,tf,str(exc)[:100],flush=True)
                        if 'rate limit' in str(exc).lower():
                            if STREAM.stop.wait(30):return
                        elif STREAM.stop.wait(1):return
                elif ARCHIVE is not None and tf!='1m':
                    key=(symbol,tf);cut=int(cached[-1][6])
                    if archived.get(key)!=cut:
                        try:
                            ARCHIVE.put('kline_'+tf,symbol,[(r[6],r) for r in cached[-12:]],now)
                            archived[key]=cut
                        except Exception as exc:print('Cache archive:',symbol,tf,str(exc)[:100],flush=True)
                if RUNTIME:RUNTIME.beat('r10-minute-seed',symbol=symbol,timeframe=tf)
        STREAM.stop.wait(10)


def serve():
    global RUNTIME, CPU_POOL
    DRAIN_REQUEST.clear();APP_STOP.clear()
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8765'))
    server = ThreadingHTTPServer((host, port), Handler)
    # Bind successfully before starting workers or launching a browser.
    RUNTIME = Runtime(STORE.path) if R10 is not None else None
    if STREAM is not None and SCAN_CPU_WORKERS>1:
        CPU_POOL=ProcessPoolExecutor(max_workers=SCAN_CPU_WORKERS,mp_context=multiprocessing.get_context('spawn'))
    print('CPU logical cores:',os.cpu_count(),'| scan math processes:',SCAN_CPU_WORKERS if CPU_POOL is not None else 0,flush=True)
    workers=[]
    def worker(name,fn):
        if RUNTIME:t=RUNTIME.supervise(name,fn)
        else:
            t=threading.Thread(target=fn,daemon=True,name=name);t.start()
        workers.append(t)
    def scan_status():
        # Read only primitive values without acquiring a potentially stalled lock.
        return {k:SCAN_STATE.get(k) for k in ('running','progressAt','processed','total','startedAt','cacheSkipped','cacheSkippedSymbols','computed','phase','phaseMetrics')}
    if RUNTIME:
        threading.Thread(target=RUNTIME.watch,args=(scan_status,),daemon=True,name='r10-watchdog').start()
    if STREAM is not None:
        for lane in ('minute','ticker','other'):
            worker('ws-'+lane,lambda lane=lane:STREAM.run_forever(lane))
        worker('ws-research',minute_research_loop)
        worker('scan-research-writer',scan_research_loop)
        if R11 is not None:
            worker('r11-radar',lambda:R11.run(lambda:RUNTIME.beat('r11-radar') if RUNTIME else None))
        if R111 is not None:
            worker('r111-radar',lambda:R111.run(lambda:RUNTIME.beat('r111-radar') if RUNTIME else None))
        if ARCHIVE is not None:worker('local-cache-seed',local_seed_loop)
        worker('r10-minute-seed',minute_seed_loop)
        print('R09 WebSocket enabled; status /api/websocket; research /api/research/1m',flush=True)
    if os.getenv('SCANNER_BACKGROUND', '1') == '1':
        worker('scan-scheduler',scheduler_loop)
        worker('fast-watch',fast_watch_loop)
    if ARCHIVE is not None:
        if STREAM is not None:ARCHIVE.stream=STREAM
        if RUNTIME:ARCHIVE.heartbeat=lambda **kw:RUNTIME.beat('all-pair-archive',**kw)
        worker('all-pair-archive',ARCHIVE.collect_forever)
        print('OVERNIGHT ALL USDT perpetual pairs enabled; status /api/overnight',flush=True)
    print('Scalp Radar v0.5 / Full Universe P12: host %s port %d' % (host,port),flush=True)
    print('DB:',STORE.path,'| background scanner:',os.getenv('SCANNER_BACKGROUND','1'),flush=True)
    def drain():
        with SCAN_LOCK:
            DRAIN_REQUEST.set()
            job=SCAN_THREAD
        if RUNTIME:
            RUNTIME.event('update_drain_requested');RUNTIME.stop.set()
        print('Graceful shutdown: waiting for active scan to finish...',flush=True)
        if job is not None and job.is_alive():job.join()
        APP_STOP.set()
        if STREAM is not None:STREAM.stop.set()
        if ARCHIVE is not None:ARCHIVE.stop.set()
        for t in workers:t.join()
        print('Graceful shutdown: workers stopped; closing server.',flush=True)
        if RUNTIME:RUNTIME.event('update_drain_complete')
        server.shutdown()
    def shutdown_monitor(path):
        while not APP_STOP.wait(.5):
            if path.is_file():
                drain();return
    stop_file=os.getenv('SCANNER_SHUTDOWN_FILE')
    if stop_file:
        threading.Thread(target=shutdown_monitor,args=(Path(stop_file),),daemon=True,name='shutdown-monitor').start()
    try:
        if os.getenv('SCANNER_OPEN_BROWSER','0') == '1':
            import webbrowser
            url='http://127.0.0.1:%d' % server.server_address[1]
            def open_dashboard():
                try:
                    webbrowser.open(url)
                except Exception as exc:
                    print('Open browser manually:',url,str(exc),flush=True)
            threading.Thread(target=open_dashboard,daemon=True,name='open-dashboard').start()
        server.serve_forever()
    except KeyboardInterrupt:
        print('Server stopped')
    finally:
        APP_STOP.set();DRAIN_REQUEST.set()
        if RUNTIME:RUNTIME.stop.set()
        if STREAM is not None:STREAM.stop.set()
        if ARCHIVE is not None:
            ARCHIVE.stop.set()
        if CPU_POOL is not None:CPU_POOL.shutdown(wait=True,cancel_futures=True)
        server.server_close()

if __name__ == '__main__':
    serve()