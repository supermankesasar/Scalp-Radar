"""Pure technical calculations for spawn-safe CPU workers. No network, database or application globals."""
import statistics
import time
from datetime import datetime, timezone
from filters import scalp_v2, multifactor

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


def extra_indicators(rows):
    """Compact shadow-only features. No scoring gates or extra API calls."""
    if len(rows)<35:return None
    b=rows[-60:];cl=[x['close'] for x in b]
    typ=[(x['high']+x['low']+x['close'])/3 for x in b]
    volume=[x['volume'] for x in b]
    pos=neg=0.
    for i in range(len(b)-14,len(b)):
        money=typ[i]*volume[i]
        if typ[i]>typ[i-1]:pos+=money
        elif typ[i]<typ[i-1]:neg+=money
    mfi=100*pos/(pos+neg) if pos+neg else None
    mean=statistics.mean(typ[-20:])
    dev=statistics.mean(abs(v-mean) for v in typ[-20:])
    cci=(typ[-1]-mean)/(.015*dev) if dev else None
    total=sum(volume[-20:])
    obv=sum(volume[i]*(1 if cl[i]>cl[i-1] else -1 if cl[i]<cl[i-1] else 0)
            for i in range(len(b)-20,len(b)))/total if total else None
    # Wilder directional movement and ADX (14).
    trs=[];plus=[];minus=[]
    for old,new in zip(b,b[1:]):
        up=new['high']-old['high'];down=old['low']-new['low']
        trs.append(max(new['high']-new['low'],abs(new['high']-old['close']),abs(new['low']-old['close'])))
        plus.append(up if up>down and up>0 else 0.)
        minus.append(down if down>up and down>0 else 0.)
    tr=sum(trs[:14]);p=sum(plus[:14]);m=sum(minus[:14]);dx=[]
    for i in range(13,len(trs)):
        if i>13:tr=tr-tr/14+trs[i];p=p-p/14+plus[i];m=m-m/14+minus[i]
        dx.append(100*abs(p-m)/(p+m) if p+m else 0.)
    adx=statistics.mean(dx[:14])
    for x in dx[14:]:adx=(13*adx+x)/14
    rs=[rsi(cl[:i]) for i in range(len(cl)-15,len(cl)+1)]
    stoch=[]
    for i in range(13,len(rs)):
        w=rs[i-13:i+1];lo=min(w);hi=max(w)
        stoch.append(100*(w[-1]-lo)/(hi-lo) if hi>lo else 50.)
    middle=statistics.mean(cl[-20:])
    return {'version':'shadow-extra-v1','adx14':adx,'plusDI14':100*p/tr if tr else None,
        'minusDI14':100*m/tr if tr else None,'mfi14':mfi,'cci20':cci,'obvFlow20':obv,
        'stochRsi14K3':statistics.mean(stoch[-3:]),'roc5Pct':100*(cl[-1]/cl[-6]-1),
        'bbWidth20Pct':400*statistics.pstdev(cl[-20:])/middle if middle else None}


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


def price_return(rows, back):
    return 100.0 * (rows[-1]['close'] / rows[-1-back]['close'] - 1.0)


def rsi_reversal_watch(previous_rsi, current_rsi, bar, macd_histogram):
    """Unproven short-reversal / LONG-TP watch. Never a standalone SHORT."""
    return bool(previous_rsi is not None and current_rsi is not None
                and 70 <= previous_rsi <= 80 and current_rsi < previous_rsi
                and bar['close'] < bar['open'] and macd_histogram < 0)


def compute_scan_math(raw_sets,raw,now,want_minute,minute_error=None):
    started=time.perf_counter()
    sets={}
    for tf,candles in raw_sets.items():
        rows=parse_klines(candles,now)
        if len(rows)<220:raise ValueError('Candle %s tidak cukup: %s' % (tf,len(rows)))
        sets[tf]=rows
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
    if want_minute and raw is not None:
        try:
            features['minute']=scalp_v2.minute_features(parse_klines(raw,now),i5['time'],ema)
            if features['minute'] is None:minute_error='1m missing or not aligned to 5m close'
        except (ValueError,TypeError,IndexError,KeyError,ZeroDivisionError) as exc:
            minute_error=str(exc)[:140]
    features['multi']=multifactor.extract(c5,rsi,atr)
    features['extraIndicators']={tf:extra_indicators(sets[tf]) for tf in ('5m','15m')}
    if raw is not None:
        minute_rows=[r for r in parse_klines(raw,now) if r['closeTime']<=i5['time']]
        if len(minute_rows)>=35 and all(y['closeTime']-x['closeTime']==60000 for x,y in zip(minute_rows,minute_rows[1:])):
            features['extraIndicators']['1m']=extra_indicators(minute_rows)
    return dict(i5=i5,t1=t1,t4=t4,ret5=ret5,ret15=ret15,ret60=ret60,atr_pct=atr_pct,threshold15=threshold15,threshold60=threshold60,vwap=vwap,px=px,vratio=vratio,rsi15=rsi15,dist_ema=dist_ema,previous_rsi15=previous_rsi15,reversal_rsi70=reversal_rsi70,minute_error=minute_error,features=features,
                recent5m=[{'closeTime':r['closeTime'],'close':r['close'],'high':r['high'],'low':r['low']} for r in c5],
                calcMs=1000*(time.perf_counter()-started))
