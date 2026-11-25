"""Experimental short-EMA timing; no I/O, no future candles, no AI."""
VERSION = 'scalp-v2-ema-short-v1'
PERIODS = (9, 10, 14)

def crosses(close, prev_close, ema, prev_ema, sign):
    return sign*(close-ema)>0 and sign*(prev_close-prev_ema)<=0

def minute_features(rows, cutoff, ema):
    # Align to the 5m signal close, never use later 1m candles.
    bars = [b for b in rows if b['closeTime'] <= cutoff][-60:]
    if len(bars)!=60 or bars[-1]['closeTime']!=cutoff or any(
        b['closeTime']-a['closeTime']!=60000 for a,b in zip(bars,bars[1:])):
        return None
    closes = [b['close'] for b in bars]
    return {'cutoff':cutoff,'close':closes[-1], 'series':{
        str(p): {'ema':ema(closes,p)[-4:], 'close':closes[-4:]} for p in PERIODS}}

def minute_cross(m, p, sign):
    if not m:
        return False
    v=m['series'][str(p)]
    c,e=v['close'],v['ema']
    return sign*(c[-1]-e[-1])>0 and any(
        crosses(c[i],c[i-1],e[i],e[i-1],sign) for i in range(1,4))

def evaluate(c, sign):
    d='BULLISH' if sign==1 else 'BEARISH'
    if any(c.get(k) is None for k in ('ema14_5','ema9_5','ema21_5','rsi5','ret5')):
        return {'score':0,'potential':False,'contributions':{},'timing':False}
    aligned=sign*(c['ema9_5']-c['ema14_5'])>0 and sign*(c['ema14_5']-c['ema21_5'])>0
    timing=minute_cross(c.get('minute'),9,sign) or minute_cross(c.get('minute'),14,sign)
    r=c['rsi5']
    points={
        'trend1h':12 if c['trend1h']==d else 0,
        'trend4h':5 if c['trend4h']==d else 0,
        'ema15':13 if sign*(c['close15']-c['ema21_15'])>0 else 0,
        'ema_alignment5':20 if aligned else 0,
        'timing1':20 if timing else 0,
        'rsi5':10 if (47<=r<=70 if sign==1 else 30<=r<=53) else 0,
        'rvol5':10 if c['rvol5']>=1.1 else 5 if c['rvol5']>=.85 else 0,
        'vwap':5 if c['vwap'] is not None and sign*(c['close5']-c['vwap'])>0 else 0,
        'macd5':5 if sign*c['macd5']>0 else 0,
    }
    score=sum(points.values())
    atr=c['atr_pct']
    dist=sign*100*(c['close5']/c['ema14_5']-1)
    anti=0<=dist<=max(.75,1.4*atr) and -.4<=sign*c['ret5']<=max(.4,1.3*atr)
    return {'score':score,'potential':bool(score>=68 and aligned and timing and anti and c['rvol5']>=.85),
            'contributions':points,'timing':timing,'antiFomo':anti}

def challengers(c,sign):
    tags=[]
    for p in PERIODS:
        e,prev=c.get('ema%d_5'%p),c.get('prev_ema%d_5'%p)
        # EMA9 5m already has its historical tag in registry.
        if p!=9 and e is not None and prev is not None and crosses(c['close5'],c['prev_close5'],e,prev,sign):
            tags.append('EMA%d_CROSS_5M'%p)
        if minute_cross(c.get('minute'),p,sign):
            tags.append('EMA%d_CROSS_1M_SYNC5'%p)
    return tags
