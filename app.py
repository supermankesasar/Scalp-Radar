#!/usr/bin/env python3
"""Scalp Radar v0.5 — Top 5 active journeys, fast watch, read-only."""
from __future__ import annotations

import json
import math
import os
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from signals import SignalStore
from filters.registry import evaluate as evaluate_filters
from filters import scalp_v2, multifactor
from research_history import ResearchHistory
from market_archive import MarketArchive, crypto_universe
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
STORE = SignalStore(os.getenv('SCANNER_DB', str(ROOT / 'data' / 'signals.sqlite3')))
HISTORY = ResearchHistory(STORE.path, STORE.lock)
OVERNIGHT = os.getenv('SCANNER_OVERNIGHT', '0') == '1'
LIVE_FILTER = os.getenv('SCANNER_LIVE_FILTER', 'BASELINE').upper()
if LIVE_FILTER not in ('BASELINE','SCALP_V2','R08_MULTI_CORE','R08_MULTI_FULL'):
    raise ValueError('Unknown SCANNER_LIVE_FILTER')
ARCHIVE = MarketArchive(STORE.path, STORE.lock) if OVERNIGHT else None
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
SCAN_MAX_WORKERS = 4
SCAN_REFRESH_MS = 180000
ACTIVE_FAST_POLL_SECONDS = 30
FRESH_CANDLE_MS = 8 * 60_000
PROMOTION_MIN_TURNOVER = 10_000_000
# A live move this far in the proposed trade direction is too extended to promote.
MAX_CHASE_PCT = 0.30
CACHE = {}
CACHE_LOCK = threading.Lock()


def request_market(endpoint: str, params: dict, ttl: int = 20):
    key = endpoint + "?" + urlencode(params)
    with CACHE_LOCK:
        hit = CACHE.get(key)
        if hit and hit[0] > time.monotonic():
            return hit[1]
    url = BASE + endpoint + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "ScalpMonitor/1.0 (market-data-only)", "Accept": "application/json"})
    try:
        with urlopen(req, timeout=13) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as e:
        detail = e.read(600).decode("utf-8", "replace")
        if e.code in (403, 451):
            raise RuntimeError("Akses Binance dibatasi dari jaringan/server ini (HTTP %s). Coba jaringan yang mengizinkan akses resmi Binance." % e.code) from e
        if e.code in (418, 429):
            raise RuntimeError("Binance rate limit (HTTP %s). Kurangi refresh dan coba lagi." % e.code) from e
        raise RuntimeError("Binance API HTTP %s: %s" % (e.code, detail)) from e
    except (URLError, TimeoutError) as e:
        raise RuntimeError("Gagal menghubungi Binance: %s" % str(e)) from e
    if isinstance(data, dict) and "code" in data and int(data["code"]) < 0:
        raise RuntimeError("Binance API error: %s" % str(data.get("msg", data["code"])))
    with CACHE_LOCK:
        CACHE[key] = (time.monotonic() + ttl, data)
    return data


def ema(values, period):
    vals = [None] * len(values)
    if len(values) < period:
        return vals
    avg = sum(values[:period]) / period
    vals[period - 1] = avg
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        avg = values[i] * alpha + avg * (1 - alpha)
        vals[i] = avg
    return vals


def rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    avg_gain = sum(max(x, 0) for x in changes[:period]) / period
    avg_loss = sum(max(-x, 0) for x in changes[:period]) / period
    for delta in changes[period:]:
        avg_gain = (avg_gain * (period - 1) + max(delta, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0)) / period
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def atr(candles, period=14):
    if len(candles) < period + 1:
        return None
    tr = []
    for i in range(1, len(candles)):
        cur, prev = candles[i], candles[i - 1]
        tr.append(max(cur['high'] - cur['low'], abs(cur['high'] - prev['close']), abs(cur['low'] - prev['close'])))
    avg = sum(tr[:period]) / period
    for x in tr[period:]:
        avg = ((period - 1) * avg + x) / period
    return avg


def macd_hist(values):
    ef = ema(values, 12)
    es = ema(values, 26)
    diffs = [(a - b) for a, b in zip(ef, es) if a is not None and b is not None]
    if len(diffs) < 9:
        return None
    line = ema(diffs, 9)
    return diffs[-1] - line[-1]


def parse_klines(rows, now_ms):
    out = []
    for c in rows:
        # Hanya candle selesai agar indikator tidak memakai candle yang masih berubah.
        if int(c[6]) >= now_ms:
            continue
        out.append({
            "time": int(c[0]), "closeTime": int(c[6]),
            "open": float(c[1]), "high": float(c[2]), "low": float(c[3]),
            "close": float(c[4]), "volume": float(c[5]),
            "quoteVolume": float(c[7]), "takerBuyQuote": float(c[10]), "tradeCount": int(c[8]),
        })
    return out


def indicators(rows):
    if len(rows) < 220:
        raise RuntimeError("Data candle tidak cukup untuk EMA 200.")
    close = [x['close'] for x in rows]
    e21 = ema(close, 21)
    e200 = ema(close, 200)
    cur = rows[-1]
    hist = macd_hist(close)
    last20 = close[-20:]
    mid = statistics.mean(last20)
    sd = statistics.pstdev(last20)
    volavg = statistics.mean([x['quoteVolume'] for x in rows[-21:-1]])
    price_change = 100 * (cur['close'] / close[-2] - 1)
    return {
        "time": cur['closeTime'], "close": cur['close'], "changeBarPct": price_change,
        "ema21": e21[-1], "ema200": e200[-1], "ema200Prev6": e200[-7],
        "rsi14": rsi(close), "macdHistogram": hist,
        "bollinger": {"lower": mid-2*sd, "middle": mid, "upper": mid+2*sd},
        "atr14": atr(rows), "volumeRatio": cur['quoteVolume'] / volavg if volavg else None,
        "takerBuySharePct": 100 * cur['takerBuyQuote'] / cur['quoteVolume'] if cur['quoteVolume'] else None,
    }


def regime(ind):
    slope = (ind['ema200'] - ind['ema200Prev6']) / ind['ema200Prev6'] * 100
    if ind['close'] > ind['ema200'] and slope > 0:
        return "BULLISH"
    if ind['close'] < ind['ema200'] and slope < 0:
        return "BEARISH"
    return "MIXED"


def utc_vwap(rows):
    """UTC anchored daily VWAP from 5m completed candles; typical price weighted by volume."""
    if not rows:
        return None, None
    date = datetime.fromtimestamp(rows[-1]['time'] / 1000, tz=timezone.utc).date()
    segment = [x for x in rows if datetime.fromtimestamp(x['time'] / 1000, tz=timezone.utc).date() == date]
    total_vol = sum(x['volume'] for x in segment)
    if not total_vol:
        return None, date.isoformat()
    return sum((x['high'] + x['low'] + x['close'])/3*x['volume'] for x in segment) / total_vol, date.isoformat()


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
    'generation': 0, 'message': 'Belum dipindai',
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
    available = active_symbols()
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


def price_return(rows, back):
    return 100.0 * (rows[-1]['close'] / rows[-1-back]['close'] - 1.0)


def scan_symbol(ticker, is_tracked=False):
    """Closed candles only; OI intentionally optional and queried for classified rows."""
    symbol = ticker['symbol']
    now = int(time.time() * 1000)
    sets = {}
    # Small bounded queries, sequential by symbol; executor provides controlled parallelism.
    for tf, limit in (('5m', 310), ('15m', 230), ('1h', 230), ('4h', 230)):
        candles = request_market('/fapi/v1/klines', {'symbol': symbol, 'interval': tf, 'limit': limit}, ttl=140)
        received = int(time.time()*1000)
        if ARCHIVE is not None:
            ARCHIVE.warmup(symbol, tf, candles, received)
        rows = parse_klines(candles, now)
        if len(rows) < 220:
            raise ValueError('Candle %s tidak cukup: %s' % (tf, len(rows)))
        sets[tf] = rows
    ins = {tf: indicators(rows) for tf, rows in sets.items()}
    c5, i5, i15 = sets['5m'], ins['5m'], ins['15m']
    t1, t4 = regime(ins['1h']), regime(ins['4h'])
    ret5, ret15, ret60 = [price_return(c5, n) for n in (1, 3, 12)]
    atr_pct = 100 * i5['atr14'] / i5['close']
    threshold15, threshold60 = max(.4, atr_pct*1.3), max(.85, atr_pct*2.0)
    intensity_up = max(ret15/threshold15, ret60/threshold60)
    intensity_down = max(-ret15/threshold15, -ret60/threshold60)
    vwap, _ = utc_vwap(c5)
    px = i5['close']
    vratio = i5['volumeRatio'] or 0
    rsi15 = i15['rsi14']
    dist_ema = 100 * (i15['close'] / i15['ema21'] - 1)
    # Separate experimental overbought-rejection watch. This is NOT a short signal.
    previous_rsi15 = rsi([x['close'] for x in sets['15m'][:-1]])
    reversal_rsi70 = rsi_reversal_watch(previous_rsi15, rsi15, c5[-1], i5['macdHistogram'])
    # Pure independent filter modules consume one point-in-time snapshot.
    e9_5 = ema([x['close'] for x in c5], 9)
    e21_5 = ema([x['close'] for x in c5], 21)
    e21_1h = ema([x['close'] for x in sets['1h']], 21)
    features = {
        'trend1h':t1, 'trend4h':t4, 'close5':px, 'close15':i15['close'],
        'ema21_5':i5['ema21'], 'ema21_15':i15['ema21'],
        'ema9_5':e9_5[-1], 'prev_ema9_5':e9_5[-2],
        'prev_ema21_5':e21_5[-2], 'prev_close5':c5[-2]['close'],
        'low5':c5[-1]['low'], 'high5':c5[-1]['high'],
        'close1h':ins['1h']['close'], 'ema21_1h':e21_1h[-1],
        'ema21_1h_prev6':e21_1h[-7],
        'rsi15':rsi15, 'macd5':i5['macdHistogram'], 'rvol5':vratio,
        'vwap':vwap, 'atr_pct':atr_pct, 'ret15':ret15, 'dist_ema15':dist_ema,
    }
    for p in (10,14):
        es=ema([r['close'] for r in c5],p)
        features['ema%d_5'%p],features['prev_ema%d_5'%p]=es[-1],es[-2]
    features.update(prev_ema9_5=e9_5[-2],rsi5=i5['rsi14'],ret5=ret5,minute=None)
    minute_error=None
    if OVERNIGHT or LIVE_FILTER!='BASELINE':
        try:
            raw=request_market('/fapi/v1/klines',{'symbol':symbol,'interval':'1m','limit':100},ttl=30)
            if ARCHIVE is not None:
                ARCHIVE.warmup(symbol,'1m',raw,int(time.time()*1000))
            features['minute']=scalp_v2.minute_features(parse_klines(raw,now),i5['time'],ema)
            if features['minute'] is None:
                minute_error='1m missing or not aligned to 5m close'
        except Exception as exc:
            if any(t in str(exc).lower() for t in ('rate limit','http 429','http 418')):
                raise
            minute_error=str(exc)[:140]
    features['multi']=multifactor.extract(c5,rsi,atr)
    features['derivatives'],features['breadth']={},{}
    context_error=None
    if ARCHIVE is not None:
        try:
            features['derivatives'],features['breadth']=ARCHIVE.research_context(symbol,i5['time'],int(time.time()*1000),ticker.get('_universe_size',0))
        except Exception as exc:
            context_error=str(exc)[:140]
    evaluation = evaluate_filters(features, shadow=True)
    selected=evaluation['v2' if LIVE_FILTER=='SCALP_V2' else 'baseline']
    if LIVE_FILTER.startswith('R08_'):
        full=LIVE_FILTER=='R08_MULTI_FULL'
        selected={k:{'score':int(v['full'] or 0) if full else v['core'],
                     'potential':v['fullPotential'] if full else v['potential']} for k,v in evaluation['r08'].items()}
    long_score = selected['UP']['score']
    short_score = selected['DOWN']['score']
    potential_up = selected['UP']['potential']
    potential_down = selected['DOWN']['potential']
    # OI intentionally not used to assign direction. It simply provides confirmation context.
    oi = {'available': False, 'reason': 'Hanya diambil untuk hasil terklasifikasi'}
    if potential_up or potential_down or is_tracked:
        try:
            oi = interest_metrics(request_market('/futures/data/openInterestHist',
                {'symbol': symbol, 'period': '5m', 'limit': 15}, ttl=90))
        except Exception as e:
            oi = {'available': False, 'reason': str(e)[:140]}
    return {
        'symbol': symbol, 'potentialUp': bool(potential_up), 'potentialDown': bool(potential_down),
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
        'r08Breakdown':evaluation['r08'],
        'volumePhase':evaluation['volumePhase'], 'vwapDistanceATR':evaluation['vwapDistanceATR'],
        '_recent5m': [{'closeTime':r['closeTime'],'close':r['close'],'high':r['high'],'low':r['low']} for r in c5],
    }


def rsi_reversal_watch(previous_rsi, current_rsi, bar, macd_histogram):
    """Unproven short-reversal / LONG-TP watch. Never a standalone SHORT."""
    return bool(previous_rsi is not None and current_rsi is not None
                and 70 <= previous_rsi <= 80 and current_rsi < previous_rsi
                and bar['close'] < bar['open'] and macd_histogram < 0)


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


def scan_job(generation, mode, min_turnover):
    try:
        tracked = STORE.active_symbols()
        research_pending = HISTORY.pending_symbols(int(time.time()*1000))
        tickers, info = active_tickers(mode, min_turnover, tracked | research_pending)
        with SCAN_LOCK:
            if generation != SCAN_STATE['generation']:
                return
            SCAN_STATE['total'] = len(tickers)
            SCAN_STATE.update(info)
            SCAN_STATE['message'] = 'Memindai pair dalam batch, prioritaskan volume besar'
        if not tickers:
            raise RuntimeError('Tidak ditemukan pair USDT perpetual sesuai mode filter.')

        # Limited batches avoid flooding futures kline endpoints when ALL is
        # selected. Rate-limit errors interrupt the remaining cycle for safety.
        stop_for_limit = False
        eligible_rows = []  # rolling pool of fresh potential setups
        recent_candles = {}
        with ThreadPoolExecutor(max_workers=SCAN_MAX_WORKERS) as executor:
            for offset in range(0, len(tickers), SCAN_BATCH_SIZE):
                if not _same_generation(generation):
                    return
                started_batch = time.monotonic()
                batch = tickers[offset:offset+SCAN_BATCH_SIZE]
                futures = {executor.submit(scan_symbol, t, t['symbol'] in tracked):t['symbol'] for t in batch}
                for future in as_completed(futures):
                    if not _same_generation(generation):
                        return
                    try:
                        res = future.result()
                        # Advance existing journeys, but don't flood active tab with
                        # first-come events: rank across completed batch candidates.
                        recent_candles[res['symbol']] = res['_recent5m']
                        if res.get('minuteError'):
                            with SCAN_LOCK:
                                SCAN_STATE['errors'].append(res['symbol']+': '+res['minuteError'])
                        if res.get('contextError'):
                            with SCAN_LOCK:
                                SCAN_STATE['errors'].append(res['symbol']+': context '+res['contextError'])
                        # Ledger records all rules before Top5 ranking or journey rotation.
                        # Failure is visible but must not corrupt production tracking.
                        try:
                            HISTORY.record_and_evaluate(res, res['_recent5m'], int(time.time()*1000))
                        except Exception as history_error:
                            with SCAN_LOCK:
                                SCAN_STATE['errors'].append('Research ledger: '+str(history_error)[:150])
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
                        if res:
                            SCAN_STATE['rows'].append(res)
                        if error:
                            SCAN_STATE['errors'].append(error)
                if stop_for_limit:
                    with SCAN_LOCK:
                        SCAN_STATE['errors'].append('Rate limit Binance terdeteksi; siklus scan dihentikan untuk melindungi koneksi API.')
                    break
                # Promote at most five highest scores seen SO FAR (rolling Top 5).
                # Fresh quote check stops misleading old candle entries.
                try:
                    quotes = latest_quotes({r['symbol'] for r in eligible_rows})
                    for score, turnover, direction, candidate in promotion_candidates(eligible_rows, quote_prices=quotes):
                        sym = candidate['symbol']
                        if STORE.activate_top_candidate(candidate, recent_candles[sym], direction):
                            with SCAN_LOCK:
                                for i, prior in enumerate(SCAN_STATE['rows']):
                                    if prior['symbol'] == sym:
                                        # Re-read persisted snapshot with just-created event.
                                        match = next((r for r in STORE.latest_rows() if r['symbol']==sym), None)
                                        if match:
                                            SCAN_STATE['rows'][i] = match
                                        break
                except Exception as exc:
                    with SCAN_LOCK:
                        SCAN_STATE['errors'].append('Peringatan ranking/kutipan: '+str(exc)[:120])
                # Track the signal journeys already found while scanning the
                # next batch; no need for the browser to stay open.
                if offset + SCAN_BATCH_SIZE < len(tickers):
                    remaining = SCAN_BATCH_INTERVAL - (time.monotonic() - started_batch)
                    if remaining > 0:
                        time.sleep(remaining)
    except Exception as exc:
        with SCAN_LOCK:
            if generation == SCAN_STATE['generation']:
                SCAN_STATE['errors'].append('Scanner: ' + str(exc))
    finally:
        with SCAN_LOCK:
            if generation == SCAN_STATE['generation']:
                SCAN_STATE['running'] = False
                SCAN_STATE['completedAt'] = int(time.time()*1000)
                stopped = SCAN_STATE['processed'] < SCAN_STATE['total']
                SCAN_STATE['message'] = ('Scan terhenti sebelum selesai' if stopped else
                    'Scan selesai' if SCAN_STATE['rows'] else 'Tidak ada data berhasil dianalisis')


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


def read_scanner(mode=DEFAULT_MODE, min_turnover=DEFAULT_TURNOVER, force=False):
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
        need_start = (not running and (SCAN_STATE['completedAt'] is None or new_filters
                                      or elapsed >= SCAN_REFRESH_MS or (force and started_age >= 60000)))
        if need_start:
            SCAN_STATE.update({
                'running': True, 'rows': [], 'processed': 0, 'total': 0, 'eligible': 0,
                'universe': 0, 'missingTicker': 0, 'trackedExtra': 0,
                'errors': [], 'startedAt': now_ms, 'completedAt': None,
                'mode': mode, 'minTurnover': min_turnover,
                'generation': SCAN_STATE['generation']+1,
                'message': 'Mengambil daftar USDT perpetual Binance',
            })
            job = threading.Thread(target=scan_job, args=(SCAN_STATE['generation'],mode,min_turnover), daemon=True)
            job.start()
        fresh = list(SCAN_STATE['rows'])
        from_disk = STORE.latest_rows()
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
        pending = SCAN_STATE['running'] and new_filters
        active = STORE.active_pending(now_ms)
        return {
            'running': SCAN_STATE['running'], 'rows': combined,
            'activeSignals': len(active), 'activeLimit': 5,
            'signals': active,
            'processed': SCAN_STATE['processed'], 'total': SCAN_STATE['total'],
            'successful': len(fresh),
            'failed': SCAN_STATE['processed'] - len(fresh),
            'eligible': SCAN_STATE['eligible'], 'universe': SCAN_STATE['universe'],
            'missingTicker': SCAN_STATE['missingTicker'], 'trackedExtra': SCAN_STATE['trackedExtra'],
            'errors': SCAN_STATE['errors'][:10], 'errorCount': len(SCAN_STATE['errors']),
            'startedAt': SCAN_STATE['startedAt'], 'completedAt': SCAN_STATE['completedAt'],
            'mode': SCAN_STATE['mode'], 'requestedMode': mode, 'configPending': pending,
            'minTurnover': SCAN_STATE['minTurnover'], 'requestedMinTurnover': min_turnover,
            'message': SCAN_STATE['message'],
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
    while True:
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
        time.sleep(ACTIVE_FAST_POLL_SECONDS)


def scheduler_loop():
    """Always-on server-side scanning independent from whether phone/browser is open."""
    while True:
        try:
            with SCAN_LOCK:
                mode, turnover = SCAN_STATE['requestedMode'], SCAN_STATE['requestedMinTurnover']
            read_scanner(mode, turnover)
        except Exception as exc:
            print('Background scheduler:',str(exc),flush=True)
        time.sleep(12)


def serve():
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8765'))
    server = ThreadingHTTPServer((host, port), Handler)
    # Bind successfully before starting workers or launching a browser.
    if os.getenv('SCANNER_BACKGROUND', '1') == '1':
        threading.Thread(target=scheduler_loop, daemon=True, name='scan-scheduler').start()
        threading.Thread(target=fast_watch_loop, daemon=True, name='fast-watch').start()
    if ARCHIVE is not None:
        threading.Thread(target=ARCHIVE.collect_forever, daemon=True, name='all-pair-archive').start()
        print('OVERNIGHT ALL crypto pairs enabled; status /api/overnight',flush=True)
    print('Scalp Radar v0.5: host %s port %d' % (host,port),flush=True)
    print('DB:',STORE.path,'| background scanner:',os.getenv('SCANNER_BACKGROUND','1'),flush=True)
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
        if ARCHIVE is not None:
            ARCHIVE.stop.set()
        server.server_close()

if __name__ == '__main__':
    serve()