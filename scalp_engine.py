"""Fast Scalping: exclusively CLOSED 1m, 5m, 15m, 1h Binance USD-M candles.

1h/15m = trend, 5m = momentum, 1m = entry and 1m event outcomes.
Not a model prediction; 24h PRICE change and 4h/1d/1w do not enter scalp scoring.
"""
from rsi_alerts import warning_values

TIMEFRAMES=('1m','5m','15m','1h')
CANDLE_REQUESTS=(('1m',260),('5m',310),('15m',230),('1h',230))
MIN_COMPLETED=220

def timeframe_snapshot(symbol,request_market,parse_klines,indicators,now_ms=None):
    import time
    now_ms=int(time.time()*1000) if now_ms is None else now_ms
    rows={}
    for tf,limit in CANDLE_REQUESTS:
        raw=request_market('/fapi/v1/klines',{'symbol':symbol,'interval':tf,'limit':limit},
                           ttl=35 if tf=='1m' else 140)
        completed=parse_klines(raw,now_ms)
        if len(completed)<MIN_COMPLETED:
            raise ValueError(f'Kurang candle tertutup {tf}: {len(completed)}')
        rows[tf]=completed
    return rows,{tf:indicators(bars) for tf,bars in rows.items()}

def score_and_candidates(rows,inds,config,regime,utc_vwap,rsi,rsi_reversal_watch):
    """0–100: trend 1h=24; 15m=12; EMA21 5m=14; EMA21 1m=11;
    MACD 1m=10; RSI 5m=10; volume relatif 1m=11; VWAP UTC 5m=8.
    """
    one,five,fifteen,hour=(inds[k] for k in TIMEFRAMES)
    px=one['close']
    trend1h,trend15m=regime(hour),regime(fifteen)
    vwap,_=utc_vwap(rows['5m'])
    atr1pct=100*one['atr14']/px
    atr5pct=100*five['atr14']/five['close']
    rsi5=five['rsi14']
    rel=one['volumeRatio'] or 0
    dist1=100*(px/one['ema21']-1)
    ret1=100*(px/rows['1m'][-2]['close']-1)
    prev_rsi5=rsi([b['close'] for b in rows['5m'][:-1]])
    watch=rsi_reversal_watch(prev_rsi5,rsi5,rows['1m'][-1],
                             one['macdHistogram'],config['rsi_watch_threshold'])
    def score(up):
        sign=1 if up else -1
        target='BULLISH' if up else 'BEARISH'
        s=24 if trend1h==target else 0
        s+=12 if trend15m==target else 5 if trend15m=='MIXED' else 0
        s+=14 if sign*(five['close']-five['ema21'])>0 else 0
        s+=11 if sign*(px-one['ema21'])>0 else 0
        s+=10 if sign*one['macdHistogram']>0 else 0
        s+=10 if (47<=rsi5<=config['rsi_long_max'] if up else 30<=rsi5<=53) else 0
        s+=11 if rel>=config['volume_full_score_min'] else 6 if rel>=.85 else 0
        s+=8 if vwap is not None and sign*(px-vwap)>0 else 0
        return s
    longscore,shortscore=score(True),score(False)
    distance_limit=max(.45,1.4*atr1pct)
    up=(trend1h=='BULLISH' and trend15m!='BEARISH'
        and longscore>=config['min_score']
        and 0<=dist1<=distance_limit
        and -.25<=ret1<=max(.25,1.4*atr1pct))
    down=(trend1h=='BEARISH' and trend15m!='BULLISH'
          and shortscore>=config['min_score']
          and -distance_limit<=dist1<=0
          and -max(.25,1.4*atr1pct)<=ret1<=.25)
    return dict(potentialUp=bool(up),potentialDown=bool(down),
        longScore=longscore,shortScore=shortscore,
        trend1h=trend1h,trend15m=trend15m,trend4h=None,
        rsi5m=rsi5,rsi15m=fifteen['rsi14'],rsiPrevious5m=prev_rsi5,
        **warning_values(rsi5,config,'5m'),
        rsiReversalWatch=bool(watch),rsiWatchTimeframe='5m',
        rsiWatchThreshold=config['rsi_watch_threshold'],
        relVolume1m=rel,relVolume5m=five['volumeRatio'],
        ema1mDistancePct=dist1,
        vwapBias='ABOVE' if vwap is not None and px>vwap else 'BELOW' if vwap is not None else 'N/A',
        atr1mPct=atr1pct,atr5mPct=atr5pct)

def scan_symbol(ticker,request_market,parse_klines,indicators,regime,utc_vwap,rsi,
                rsi_reversal_watch,interest_metrics,config,now_ms=None,
                settings_revision=0,is_tracked=False):
    symbol=ticker['symbol']
    rows,inds=timeframe_snapshot(symbol,request_market,parse_klines,indicators,now_ms)
    result=score_and_candidates(rows,inds,config,regime,utc_vwap,rsi,rsi_reversal_watch)
    one=rows['1m']
    price=inds['1m']['close']
    oi={'available':False,'reason':'OI opsional'}
    if result['potentialUp'] or result['potentialDown'] or is_tracked:
        try:
            oi=interest_metrics(request_market('/futures/data/openInterestHist',
                {'symbol':symbol,'period':'5m','limit':15},ttl=90))
        except Exception as e:
            oi={'available':False,'reason':str(e)[:140]}
    result.update({
      'strategy':'scalping','timeframes':list(TIMEFRAMES),
      'symbol':symbol,'price':price,
      'pct5m':100*(one[-1]['close']/one[-6]['close']-1),
      'pct15m':100*(one[-1]['close']/one[-16]['close']-1),
      'pct60m':100*(one[-1]['close']/one[-61]['close']-1),
      'pct24h':None, # Price direction 24h EXCLUDED from scalping.
      'turnover24h':ticker['turnover24h'], # Liquidity only, not momentum.
      'oi15mPct':oi.get('delta15mPct') if oi.get('available') else None,
      'oiAvailable':oi.get('available',False),
      'oiNote':oi.get('reason') if not oi.get('available') else None,
      'lastClosed1m':inds['1m']['time'],
      'lastClosed5m':inds['5m']['time'],
      'settingsRevision':settings_revision,
      '_recent1m':[{'closeTime':b['closeTime'],'close':b['close'],
                    'high':b['high'],'low':b['low']} for b in one],
    })
    return result
