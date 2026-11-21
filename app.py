#!/usr/bin/env python3
"""Binance Futures Scalping Scanner — fase 1 v0.2, read-only, Python standard library."""
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
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
STORE = SignalStore(os.getenv('SCANNER_DB', str(ROOT / 'data' / 'signals.sqlite3')))
BASE = "https://fapi.binance.com"
SCAN_LIMITS = (40, 80, 120)
SCAN_MIN_TURNOVER = (10000000, 30000000, 100000000)
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
            "quoteVolume": float(c[7]), "takerBuyQuote": float(c[10]),
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
    "running": False, "rows": [], "processed": 0, "total": 0, "eligible": 0,
    "errors": [], "startedAt": None, "completedAt": None,
    "limit": 80, "minTurnover": 30000000, "generation": 0, "message": "Belum dipindai",
}


def active_symbols():
    """USDT-margined perpetual in TRADING status; no predefined watchlist."""
    exchange = request_market('/fapi/v1/exchangeInfo', {}, ttl=3600)
    return {
        s['symbol'] for s in exchange.get('symbols', [])
        if s.get('status') == 'TRADING'
        and s.get('contractType') == 'PERPETUAL'
        and s.get('quoteAsset') == 'USDT'
    }


def active_tickers(limit, min_turnover, tracked=None):
    available = active_symbols()
    tickers = request_market('/fapi/v1/ticker/24hr', {}, ttl=120)
    good = []
    by_symbol = {}
    for t in tickers:
        try:
            symbol = t['symbol']
            q = float(t['quoteVolume'])
            last = float(t.get('lastPrice', 0))
            chg = float(t.get('priceChangePercent', 0))
        except (KeyError, ValueError, TypeError):
            continue
        if symbol not in available or last <= 0:
            continue
        record = {'symbol': symbol, 'turnover24h': q, 'change24h': chg}
        by_symbol[symbol] = record
        if q >= min_turnover:
            good.append(record)
    good.sort(key=lambda x: x['turnover24h'], reverse=True)
    selected = good[:limit]
    present = {x['symbol'] for x in selected}
    # Keep following prior signals even if a pair exits the volume Top-N.
    for sym in sorted(tracked or []):
        if sym not in present and sym in by_symbol:
            selected.append(by_symbol[sym])
            present.add(sym)
    return selected, len(good)


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
    # Scores are descriptive heuristics; NOT calibrated probabilities of success.
    def score_for(up):
        sign = 1 if up else -1
        trend = 'BULLISH' if up else 'BEARISH'
        s = 0
        s += 24 if t1 == trend else 0
        s += 12 if t4 == trend else 5 if t4 == 'MIXED' else 0
        s += 14 if sign*(i15['close']-i15['ema21']) > 0 else 0
        s += 11 if sign*(px-i5['ema21']) > 0 else 0
        s += 10 if sign*i5['macdHistogram'] > 0 else 0
        s += 10 if (47 <= rsi15 <= 70 if up else 30 <= rsi15 <= 53) else 0
        s += 11 if vratio >= 1.1 else 6 if vratio >= .85 else 0
        s += 8 if vwap is not None and sign*(px-vwap) > 0 else 0
        return s
    long_score, short_score = score_for(True), score_for(False)
    # Independent potential flags; reaching a move NEVER directly creates a 'Sudah' tab.
    # 'Sudah' is solely assigned by a prior stored potential signal + later closed candles.
    potential_up = (t1 == 'BULLISH' and t4 != 'BEARISH' and long_score >= 68
            and 0 <= dist_ema <= max(.75, 1.4*atr_pct) and -0.4 <= ret15 <= threshold15)
    potential_down = (t1 == 'BEARISH' and t4 != 'BULLISH' and short_score >= 68
            and -max(.75, 1.4*atr_pct) <= dist_ema <= 0 and -threshold15 <= ret15 <= .4)
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
        'oiNote': oi.get('reason') if not oi.get('available') else None,
        'lastClosed5m': i5['time'],
        '_recent5m': [{'closeTime':r['closeTime'],'close':r['close'],'high':r['high'],'low':r['low']} for r in c5],
    }


def scan_job(generation, limit, min_turnover):
    try:
        tracked = STORE.active_symbols()
        tickers, eligible = active_tickers(limit, min_turnover, tracked)
        with SCAN_LOCK:
            if generation != SCAN_STATE['generation']:
                return
            SCAN_STATE['total'] = len(tickers)
            SCAN_STATE['eligible'] = eligible
            SCAN_STATE['message'] = 'Memindai candle, tren, dan Open Interest'
        if not tickers:
            raise RuntimeError('Tidak ditemukan pair aktif dengan batas volume yang dipilih.')
        # Limit concurrency: less API pressure, and report incremental progress.
        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {executor.submit(scan_symbol, t, t['symbol'] in tracked):t['symbol'] for t in tickers}
            for future in as_completed(futures):
                try:
                    res = future.result()
                    res = STORE.refresh(res, res['_recent5m'])
                    err = None
                except Exception as e:
                    res = None
                    err = '%s: %s' % (futures[future], str(e))
                with SCAN_LOCK:
                    if generation != SCAN_STATE['generation']:
                        return
                    SCAN_STATE['processed'] += 1
                    if res:
                        SCAN_STATE['rows'].append(res)
                    if err:
                        SCAN_STATE['errors'].append(err)
    except Exception as e:
        with SCAN_LOCK:
            if generation == SCAN_STATE['generation']:
                SCAN_STATE['errors'].append('Scanner: ' + str(e))
    finally:
        with SCAN_LOCK:
            if generation == SCAN_STATE['generation']:
                SCAN_STATE['running'] = False
                SCAN_STATE['completedAt'] = int(time.time()*1000)
                SCAN_STATE['message'] = 'Selesai' if SCAN_STATE['rows'] else 'Data scanner belum tersedia'


def read_scanner(limit=80, min_turnover=30000000, force=False):
    if limit not in SCAN_LIMITS or min_turnover not in SCAN_MIN_TURNOVER:
        raise ValueError('Pilihan scan harus dari menu limit/volume yang tersedia.')
    now_ms = int(time.time()*1000)
    with SCAN_LOCK:
        running = SCAN_STATE['running']
        new_filters = (limit, min_turnover) != (SCAN_STATE['limit'], SCAN_STATE['minTurnover'])
        elapsed = now_ms - (SCAN_STATE['completedAt'] or 0)
        started_age = now_ms - (SCAN_STATE['startedAt'] or 0)
        need_start = (not running and (SCAN_STATE['completedAt'] is None or new_filters or elapsed >= 180000
                                       or (force and started_age >= 60000)))
        if need_start:
            SCAN_STATE.update({
                'running': True, 'rows': [], 'processed': 0, 'total': 0,
                'eligible': 0, 'errors': [], 'startedAt': now_ms, 'completedAt': None,
                'limit': limit, 'minTurnover': min_turnover,
                'generation': SCAN_STATE['generation']+1, 'message': 'Mengambil daftar pair Binance',
            })
            job = threading.Thread(target=scan_job, args=(SCAN_STATE['generation'],limit,min_turnover), daemon=True)
            job.start()
        fresh = list(SCAN_STATE['rows'])
        from_disk = STORE.latest_rows()
        # Keep saved snapshots visible during a scan, but respect chosen liquidity universe.
        eligible_saved = sorted((x for x in from_disk if x['turnover24h'] >= min_turnover),
                                key=lambda x:x['turnover24h'],reverse=True)
        selected_saved = eligible_saved[:limit]
        allowed = {x['symbol'] for x in selected_saved}
        allowed.update(x['symbol'] for x in from_disk if x.get('categories'))
        fresh_ids = {x['symbol'] for x in fresh}
        combined = fresh + [dict(x, stale=True) for x in from_disk
                            if x['symbol'] not in fresh_ids and x['symbol'] in allowed]
        return {
            'running': SCAN_STATE['running'], 'rows': combined,
            'processed': SCAN_STATE['processed'], 'total': SCAN_STATE['total'],
            'eligible': SCAN_STATE['eligible'], 'errors': SCAN_STATE['errors'][:10],
            'errorCount': len(SCAN_STATE['errors']), 'startedAt': SCAN_STATE['startedAt'],
            'completedAt': SCAN_STATE['completedAt'], 'limit': SCAN_STATE['limit'],
            'minTurnover': SCAN_STATE['minTurnover'], 'message': SCAN_STATE['message'],
            'source': 'Binance USD-M Futures public API',
            'categories': list(CATEGORIES),
            'tracking': 'SQLite: Sudah Naik/Turun hanya dari signal Potential yang tersimpan + candle tutup berikutnya',
            'scoring': 'Aturan heuristik, bukan probabilitas/prediksi tervalidasi',
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
        elif route.path == '/sw.js':
            self._reply(200, (ROOT/'sw.js').read_bytes(), 'text/javascript; charset=utf-8')
        elif route.path == '/icon.png':
            self._reply(200, (ROOT/'icon.png').read_bytes(), 'image/png')
        elif route.path == '/api/health':
            self._reply(200, json.dumps({'ok':True,'version':'0.3','storage':'SQLite','activeTracked':len(STORE.active_symbols())}).encode(), 'application/json')
        elif route.path == '/api/events':
            self._reply(200, json.dumps({'events':STORE.audit_events(200)}).encode(), 'application/json')
        elif route.path == '/api/scan':
            args = parse_qs(route.query)
            try:
                limit = int(args.get('limit', ['80'])[0])
                turnover = int(args.get('min_turnover', ['30000000'])[0])
                payload = read_scanner(limit, turnover, args.get('force', ['0'])[0] == '1')
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


def scheduler_loop():
    """Always-on server-side scanning independent from whether phone/browser is open."""
    while True:
        try:
            with SCAN_LOCK:
                limit, turnover = SCAN_STATE['limit'], SCAN_STATE['minTurnover']
            read_scanner(limit, turnover)
        except Exception as exc:
            print('Background scheduler:',str(exc),flush=True)
        time.sleep(12)


def serve():
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8765'))
    if os.getenv('SCANNER_BACKGROUND', '1') == '1':
        threading.Thread(target=scheduler_loop, daemon=True, name='scan-scheduler').start()
    server = ThreadingHTTPServer((host, port), Handler)
    print('Scalp Signal Tracker v0.3: host %s port %d' % (host,port),flush=True)
    print('DB:',STORE.path,'| background scanner:',os.getenv('SCANNER_BACKGROUND','1'),flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Server stopped')
    finally:
        server.server_close()

if __name__ == '__main__':
    serve()