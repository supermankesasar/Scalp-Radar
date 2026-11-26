"""R11-v1 provisional, independent multi-horizon opportunity/entry rules.

Only contiguous CLOSED 1m candles. Rolling horizons are not native timeframe bars.
No I/O, weights, probability claims, or trading execution.
"""
import math
from statistics import median

VERSION = 'r11-preview-v1'
STEP = 60000
FRESH_MS = 15000
WATCH_MS = 15 * STEP
SPREAD_CAP = .10  # percentage points, provisional
def features(rows, cutoff):
    if len(rows) < 61:
        return None
    rows = rows[-61:]
    if any(int(r[6]) != cutoff - (60-i)*STEP for i,r in enumerate(rows)):
        return None
    try:
        o,h,l,c,q,n,b = ([float(r[j]) for r in rows] for j in (1,2,3,4,7,8,10))
        if not all(math.isfinite(x) for a in (o,h,l,c,q,n,b) for x in a):
            return None
        if any(x <= 0 for x in c+o+h+l) or any(x < 0 for x in q+n+b):
            return None
        if any(not (lo <= min(op,cl) <= max(op,cl) <= hi) or buy>vol
               for lo,op,cl,hi,buy,vol in zip(l,o,c,h,b,q)):
            return None
        def ret(k, end=-1):
            return 100*(c[end]/c[end-k]-1)
        def flow(a,z):
            total=sum(q[a:z])
            return (2*sum(b[a:z])-total)/total if total else None
        tr=[max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])) for i in range(40,60)]
        atr=100*sum(tr)/len(tr)/c[-2]
        if atr<=0 or median(q[-21:-1])<=0 or median(n[-21:-1])<=0:
            return None
        rv=q[-1]/median(q[-21:-1]); trades=n[-1]/median(n[-21:-1])
        width=max(h[-16:-1])-min(l[-16:-1])
        prev_width=max(h[-31:-16])-min(l[-31:-16])
        compression=prev_width>0 and width<=.70*prev_width
        f={'price':c[-1],'atr1mPct':atr,'rvol1m':rv,'tradeRatio1m':trades,
           'ret1':ret(1),'ret5':ret(5),'ret15':ret(15),'ret30':ret(30),'ret60':ret(60),
           'priorRet15':ret(15,-2),'flow1':flow(-1,None),'flow5':flow(-5,None),
           'flow15':flow(-15,None),'priorFlow5':flow(-6,-1),'compression':compression}
        f['watch']=rv>=1.5 or trades>=2 or (compression and (rv>=1.1 or trades>=1.1))
        options=[]
        for s,di in ((1,'UP'),(-1,'DOWN')):
            def aligned(x,limit=0):
                return x is not None and s*x>=limit
            break3=c[-1]>max(h[-4:-1]) if s==1 else c[-1]<min(l[-4:-1])
            break15=c[-1]>max(h[-16:-1]) if s==1 else c[-1]<min(l[-16:-1])
            sweep=(l[-1]<min(l[-6:-1]) and c[-1]>min(l[-6:-1])) if s==1 else (h[-1]>max(h[-6:-1]) and c[-1]<max(h[-6:-1]))
            flip=aligned(f['flow1'],.15) and f['priorFlow5'] is not None and s*f['priorFlow5']<=-.10
            reversal=s*f['priorRet15']<=-max(.4,3*atr) and (sweep or flip) and aligned(f['ret1'],.03)
            breakout=compression and break15 and aligned(f['flow1'],.10)
            continuation=aligned(f['ret15'],max(.10,atr)) and aligned(f['ret5']) and aligned(f['flow5'],.10)
            if reversal or breakout or continuation:
                setup='REVERSAL' if reversal else 'BREAKOUT' if breakout else 'CONTINUATION'
                trigger=aligned(f['flow1'],.10) and aligned(f['ret1'],.03) and (break3 or (reversal and sweep))
                options.append((di,setup,trigger))
        f['direction'],f['setup'],f['trigger']=options[0] if len(options)==1 else (None,None,False)
        return f
    except (ValueError,TypeError,IndexError,ZeroDivisionError,OverflowError):
        return None

def advance(previous,f,cutoff,decision,quote=None,spread=None):
    """One decision per fresh minute. Current quote/spread are separate from closed-bar features."""
    if f is None or not 0<=decision-cutoff<=FRESH_MS:
        return None
    prev=previous if previous and previous['cutoff']==cutoff-STEP else None
    if prev and prev['state'] in ('READY','MONITOR') and decision-prev['readyAt']<=WATCH_MS:
        result=dict(prev,cutoff=cutoff,decisionAt=decision,state='MONITOR',features=f,reason='TRACKING')
        s=1 if prev['direction']=='UP' else -1
        change=s*100*(f['price']/prev['readyPrice']-1)
        result['movePct']=change
        if change<=-max(.4,prev['readyAtr']):
            result.update(state='INVALIDATED',reason='ADVERSE_MOVE')
        return result
    if prev and prev['state']=='INVALIDATED' and decision-prev['readyAt']<=WATCH_MS:
        return dict(prev,cutoff=cutoff,decisionAt=decision,features=f)
    watching=prev and prev['state'] in ('PREPARE','LATE') and decision-prev['prepareAt']<=WATCH_MS
    if not f['watch'] and not watching:
        return None
    start=prev['prepareAt'] if watching else decision
    anchor=prev['anchor'] if watching else f['price']
    result=dict(state='PREPARE',cutoff=cutoff,decisionAt=decision,prepareAt=start,anchor=anchor,
                direction=f['direction'],setup=f['setup'],features=f,reason='AWAIT_DIRECTION_OR_TRIGGER')
    if not f['direction'] or not f['trigger']:
        return result
    if quote is None or not math.isfinite(quote) or quote<=0 or spread is None or not math.isfinite(spread) or spread<0:
        return dict(result,reason='QUOTE_OR_SPREAD_UNKNOWN')
    s=1 if f['direction']=='UP' else -1
    chase=s*100*(quote/f['price']-1)
    since=s*100*(quote/anchor-1)
    # Reuse .30% anti-chase control; ATR-scaled episode distance is a provisional guard.
    if chase>.30 or since>max(.30,1.5*f['atr1mPct']):
        return dict(result,state='LATE',reason='CHASE',chasePct=chase)
    if chase<-.15:
        return dict(result,reason='TRIGGER_REJECTED')
    if spread>SPREAD_CAP:
        return dict(result,reason='WIDE_SPREAD')
    return dict(result,state='READY',reason='ENTRY_CONDITIONS_MET',readyAt=decision,
                readyPrice=quote,readyAtr=f['atr1mPct'],chasePct=chase,spreadPct=spread,
                prepareLeadMs=decision-start)
