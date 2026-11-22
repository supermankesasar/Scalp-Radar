"""Swing heuristic on closed 15m,1h,4h,8h,1d,1w Futures candles.

Indicators require >=220 closed candles except weekly EMA21 needs >=30.
Weekly trend uses EMA21 because 200 weekly bars would exclude most new coins.
Research-only: NOT a validated return model.
"""
TIMEFRAMES=('15m','1h','4h','8h','1d','1w')
CANDLE_REQUESTS=(('15m',260),('1h',250),('4h',250),('8h',250),('1d',250),('1w',80))

def timeframe_snapshot(symbol,request_market,parse_klines,indicators,now_ms=None):
    import time
    now_ms=int(time.time()*1000) if now_ms is None else now_ms
    rows={};ind={}
    for tf,limit in CANDLE_REQUESTS:
        raw=request_market('/fapi/v1/klines',{'symbol':symbol,'interval':tf,'limit':limit},ttl=230)
        completed=parse_klines(raw,now_ms)
        needed=30 if tf=='1w' else 220
        if len(completed)<needed:
            raise ValueError(f'Swing data tidak cukup {tf}: {len(completed)}/{needed} candle tutup')
        rows[tf]=completed
        if tf!='1w':ind[tf]=indicators(completed)
    return rows,ind

def weekly_regime(rows,ema):
    prices=[x['close'] for x in rows]
    line=ema(prices,21)
    if len(prices)<30 or line[-7] is None:return 'MIXED'
    if prices[-1]>line[-1] and line[-1]>line[-7]:return 'BULLISH'
    if prices[-1]<line[-1] and line[-1]<line[-7]:return 'BEARISH'
    return 'MIXED'

def score_and_candidates(rows,ind,config,regime,ema,utc_vwap,rsi,rsi_reversal_watch,change24h):
    """0–100: W1 EMA21=16, D1 EMA200=20, 8H EMA200=12, 4H EMA200=12,
    1H EMA21=11, 15m MACD=10, 1H RSI=10, 15m relative volume=9.
    24h ticker price change is an additional DIRECTION gate, not score points.
    """
    f=ind['15m'];hour=ind['1h'];four=ind['4h'];eight=ind['8h'];day=ind['1d']
    week=weekly_regime(rows['1w'],ema)
    dreg=regime(day);e8=regime(eight);f4=regime(four)
    px=f['close'];atr1d=100*day['atr14']/day['close']
    vrel=f['volumeRatio'] or 0
    prev_rsi=rsi([b['close'] for b in rows['1h'][:-1]])
    overbought=rsi_reversal_watch(prev_rsi,hour['rsi14'],rows['15m'][-1],
                                  f['macdHistogram'],config['rsi_watch_threshold'])
    def score(up):
        sign=1 if up else -1
        direction='BULLISH' if up else 'BEARISH'
        s=16 if week==direction else 0
        s+=20 if dreg==direction else 0
        s+=12 if e8==direction else 0
        s+=12 if f4==direction else 0
        s+=11 if sign*(hour['close']-hour['ema21'])>0 else 0
        s+=10 if sign*f['macdHistogram']>0 else 0
        s+=10 if (47<=hour['rsi14']<=config['rsi_long_max'] if up else 30<=hour['rsi14']<=53) else 0
        s+=9 if vrel>=config['volume_full_score_min'] else 4 if vrel>=.85 else 0
        return s
    longscore=score(True);shortscore=score(False)
    valid_change=isinstance(change24h,(float,int)) and not isinstance(change24h,bool)
    import math
    valid_change=valid_change and math.isfinite(change24h)
    # The last 24h direction validates consistency but never becomes retrospective
    # evidence for an old signal.
    long24=valid_change and change24h>0
    short24=valid_change and change24h<0
    distance=100*(hour['close']/hour['ema21']-1)
    up=(week=='BULLISH' and dreg=='BULLISH'
        and longscore>=config['min_score'] and long24
        and 0<=distance<=max(2.5,1.4*atr1d))
    down=(week=='BEARISH' and dreg=='BEARISH'
          and shortscore>=config['min_score'] and short24
          and -max(2.5,1.4*atr1d)<=distance<=0)
    return dict(potentialUp=bool(up),potentialDown=bool(down),
        longScore=longscore,shortScore=shortscore,
        trend1h=regime(hour),trend4h=f4,trend8h=e8,trend1d=dreg,trend1w=week,
        rsi1h=hour['rsi14'],rsi15m=f['rsi14'],rsiPrevious1h=prev_rsi,
        rsiReversalWatch=bool(overbought),rsiWatchTimeframe='1h',
        rsiWatchThreshold=config['rsi_watch_threshold'],relVolume15m=vrel,
        relVolume5m=None,ema1hDistancePct=distance,
        atr1dPct=atr1d,atr5mPct=atr1d,
        triggerPct=max(2.0,1.5*atr1d),stopPct=max(1.0,atr1d),
        intraday24hLong=bool(long24),intraday24hShort=bool(short24))

def scan_symbol(ticker,request_market,parse_klines,indicators,regime,ema,rsi,
                rsi_reversal_watch,interest_metrics,config,now_ms=None,
                settings_revision=0,is_tracked=False):
    symbol=ticker['symbol']
    rows,ind=timeframe_snapshot(symbol,request_market,parse_klines,indicators,now_ms)
    result=score_and_candidates(rows,ind,config,regime,ema,None,rsi,
                  rsi_reversal_watch,ticker.get('change24h'))
    f=rows['15m'];hour=rows['1h'];p=ind['15m']['close']
    oi={'available':False,'reason':'OI opsional'}
    if result['potentialUp'] or result['potentialDown'] or is_tracked:
        try:
            oi=interest_metrics(request_market('/futures/data/openInterestHist',
                {'symbol':symbol,'period':'5m','limit':15},ttl=90))
        except Exception as e:
            oi={'available':False,'reason':str(e)[:140]}
    result.update({
        'strategy':'swing','timeframes':list(TIMEFRAMES),
        'symbol':symbol,'price':p,
        'pct5m':None,
        'pct15m':100*(f[-1]['close']/f[-2]['close']-1),
        'pct60m':100*(hour[-1]['close']/hour[-2]['close']-1),
        'pct24h':ticker.get('change24h'),
        'turnover24h':ticker['turnover24h'],
        'oi15mPct':oi.get('delta15mPct') if oi.get('available') else None,
        'oiAvailable':oi.get('available',False),
        'oiNote':oi.get('reason') if not oi.get('available') else None,
        'lastClosed1h':ind['1h']['time'],
        'lastClosed15m':ind['15m']['time'],
        'lastClosed5m':ind['15m']['time'],
        'settingsRevision':settings_revision,
        '_recent1h':[{'closeTime':b['closeTime'],'close':b['close'],
                       'high':b['high'],'low':b['low']} for b in hour],
    })
    return result
