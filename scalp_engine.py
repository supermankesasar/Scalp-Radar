"""Dedicated rule-based fast Scalping scanner.

Uses ONLY closed 1m, 3m, 5m, 15m, 1h candles.
NO 4h prices, NO 24h price movement in scoring.
Rolling 24h USDT turnover is retained solely as a liquidity safeguard.

This is an experimental indicator heuristic, NOT a profit forecast or auto-trader.
"""
import math
import time
from datetime import datetime,timezone

TIMEFRAMES=('1m','3m','5m','15m','1h')
CANDLE_REQUESTS=(('1m',260),('3m',260),('5m',310),('15m',230),('1h',230))
MIN_COMPLETED=220

def timeframe_snapshot(symbol, request_market, parse_klines, indicators, now_ms=None):
    now_ms=int(time.time()*1000) if now_ms is None else now_ms
    rows={}
    for tf,limit in CANDLE_REQUESTS:
        raw=request_market('/fapi/v1/klines',
                           {'symbol':symbol,'interval':tf,'limit':limit},ttl=55 if tf in ('1m','3m') else 140)
        completed=parse_klines(raw,now_ms)
        if len(completed)<MIN_COMPLETED:
            raise ValueError(f'Not enough completed {tf} candles for EMA200: {len(completed)}')
        rows[tf]=completed
    return rows,{tf:indicators(candles) for tf,candles in rows.items()}

def score_and_candidates(rows,inds,config,regime,utc_vwap,rsi,rsi_reversal_watch):
    """Heuristic scale remains 0..100; timeframes are reassigned for fast entry.

    1h EMA200 trend:24; 15m EMA200 trend:12; 5m EMA21:14;
    3m EMA21:11; 1m MACD:10; 3m RSI:10;
    1m relative volume:11; 5m UTC VWAP:8.
    """
    one=inds['1m'];three=inds['3m'];five=inds['5m'];fifteen=inds['15m'];hour=inds['1h']
    px=one['close'];trend1h=regime(hour);trend15m=regime(fifteen)
    vwap,_=utc_vwap(rows['5m'])
    atr5pct=100*five['atr14']/five['close']
    atr1pct=100*one['atr14']/one['close']
    rsi3=three['rsi14']
    rel=one['volumeRatio'] or 0
    distance3=100*(three['close']/three['ema21']-1)
    p3=100*(three['close']/rows['3m'][-2]['close']-1)
    previous_rsi3=rsi([b['close'] for b in rows['3m'][:-1]])
    watch=rsi_reversal_watch(previous_rsi3,rsi3,rows['1m'][-1],
                             one['macdHistogram'],config['rsi_watch_threshold'])

    def score(up):
        sign=1 if up else -1
        direction='BULLISH' if up else 'BEARISH'
        points=0
        points+=24 if trend1h==direction else 0
        points+=12 if trend15m==direction else 5 if trend15m=='MIXED' else 0
        points+=14 if sign*(five['close']-five['ema21'])>0 else 0
        points+=11 if sign*(three['close']-three['ema21'])>0 else 0
        points+=10 if sign*one['macdHistogram']>0 else 0
        points+=10 if (47<=rsi3<=config['rsi_long_max'] if up else 30<=rsi3<=53) else 0
        points+=11 if rel>=config['volume_full_score_min'] else 6 if rel>=.85 else 0
        points+=8 if vwap is not None and sign*(px-vwap)>0 else 0
        return points

    longscore=score(True);shortscore=score(False)
    # 3m momentum must not be an already-extended candle.
    upper=max(.40,1.4*atr1pct)
    up=(trend1h=='BULLISH' and trend15m!='BEARISH'
        and longscore>=config['min_score']
        and 0<=distance3<=max(.75,1.4*atr5pct)
        and -.40<=p3<=upper)
    down=(trend1h=='BEARISH' and trend15m!='BULLISH'
          and shortscore>=config['min_score']
          and -max(.75,1.4*atr5pct)<=distance3<=0
          and -upper<=p3<=.40)
    return dict(potentialUp=bool(up),potentialDown=bool(down),longScore=longscore,
        shortScore=shortscore,trend1h=trend1h,trend15m=trend15m,trend4h=None,
        rsi3m=rsi3,rsi15m=fifteen['rsi14'],rsiPrevious3m=previous_rsi3,
        rsiReversalWatch=bool(watch),rsiWatchTimeframe='3m',
        rsiWatchThreshold=config['rsi_watch_threshold'],
        relVolume1m=rel, relVolume5m=five['volumeRatio'],
        ema3mDistancePct=distance3,ema15mDistancePct=100*(fifteen['close']/fifteen['ema21']-1),
        vwapBias='ABOVE' if vwap is not None and px>vwap else 'BELOW' if vwap is not None else 'N/A',
        atr1mPct=atr1pct,atr5mPct=atr5pct)

def scan_symbol(ticker, request_market,parse_klines,indicators,regime,utc_vwap,rsi,
                rsi_reversal_watch,interest_metrics,config,now_ms=None,
                settings_revision=0,is_tracked=False):
    symbol=ticker['symbol']
    rows,inds=timeframe_snapshot(symbol,request_market,parse_klines,indicators,now_ms)
    result=score_and_candidates(rows,inds,config,regime,utc_vwap,rsi,rsi_reversal_watch)
    one=rows['1m'];five=rows['5m']
    price=inds['1m']['close']
    oi={'available':False,'reason':'Hanya diambil untuk event atau pair dipantau'}
    if result['potentialUp'] or result['potentialDown'] or is_tracked:
        try:
            oi=interest_metrics(request_market('/futures/data/openInterestHist',
                {'symbol':symbol,'period':'5m','limit':15},ttl=90))
        except Exception as e:
            oi={'available':False,'reason':str(e)[:140]}
    result.update({
      'strategy':'scalping',
      'timeframes':list(TIMEFRAMES),
      'symbol':symbol,'price':price,
      'pct5m':100*(one[-1]['close']/one[-6]['close']-1),
      'pct15m':100*(one[-1]['close']/one[-16]['close']-1),
      'pct60m':100*(five[-1]['close']/five[-13]['close']-1),
      'pct24h':None, # Never use / display the 24h PRICE move in scalping.
      'turnover24h':ticker['turnover24h'], # Liquidity filter only.
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
