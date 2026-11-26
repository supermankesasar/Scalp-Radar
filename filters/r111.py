"""R11.1 challenger: point-in-time native 15m structure, 1m trigger.
Versioned, provisional rules; R11 v1 is unchanged as comparator.
"""
from filters import r11
VERSION='r11.1-v1'
STEP=r11.STEP

def native_context(bars15,bars1h,cut):
    def closed(rows,step,n):
        end=(cut+1)//step*step-1
        rows=(rows or [])[-n:]
        return rows if len(rows)==n and all(int(r[6])==end-(n-1-i)*step for i,r in enumerate(rows)) else []
    b=closed(bars15,900000,4)
    h=closed(bars1h,3600000,2)
    if not b:return None
    a,z=b[-2:]
    high,low=float(z[2]),float(z[3])
    prev_high,prev_low=float(a[2]),float(a[3])
    trend='UP' if high>prev_high and low>prev_low else 'DOWN' if high<prev_high and low<prev_low else 'MIXED'
    # Exact UTC-aligned 30m bars from contiguous native 15m bars.
    pairs=[]
    for x,y in zip(b,b[1:]):
        if int(y[6])%1800000==1799999 and int(x[6])==int(y[6])-900000:
            pairs.append((float(x[1]),float(y[4]),max(float(x[2]),float(y[2])),min(float(x[3]),float(y[3]))))
    return {'cut15':int(z[6]),'structure15':trend,'ret15Closed':100*(float(z[4])/float(a[4])-1),
            'high15':high,'low15':low,'range45High':max(float(x[2]) for x in b[:-1]),
            'range45Low':min(float(x[3]) for x in b[:-1]),
            'ret30Closed':100*(pairs[-1][1]/pairs[-1][0]-1) if pairs else None,
            'ret1hClosed':100*(float(h[-1][4])/float(h[-2][4])-1) if h else None}

def enrich(f,rows,ctx):
    f=dict(f)
    # Early pressure without assuming direction from volume or order flow alone.
    quiet=abs(f['ret5'])<=max(.20,2*f['atr1mPct'])
    pressure=f['flow5'] is not None and abs(f['flow5'])>=.15
    f['watch']=f['watch'] or (quiet and pressure and (f['rvol1m']>=1.1 or f['tradeRatio1m']>=1.1))
    f['earlyPressure']=quiet and pressure
    f['native']=ctx
    f['entryVariant']='BASE_TRIGGER'
    if not f['direction']:return f
    if not ctx:
        f['trigger']=False;f['entryVariant']='NATIVE15_UNKNOWN';return f
    s=1 if f['direction']=='UP' else -1
    if f['setup']=='CONTINUATION':
        compatible=ctx['structure15']==f['direction'] or (ctx['structure15']=='MIXED' and s*ctx['ret15Closed']>0)
        if not compatible:
            f['trigger']=False;f['entryVariant']='CONTEXT_CONFLICT';return f
        # Pullback/retest alternative: previous 1m close clears prior 3-bar level,
        # next candle touches within 0.5 ATR and closes back on correct side.
        last,prev=rows[-1],rows[-2]
        level=(max(float(r[2]) for r in rows[-5:-2]) if s==1 else min(float(r[3]) for r in rows[-5:-2]))
        touch=float(last[3] if s==1 else last[2])
        tol=level*f['atr1mPct']/100*.5
        retest=(s*(float(prev[4])-level)>0 and abs(touch-level)<=tol and s*(float(last[4])-level)>0
                and f['flow1'] is not None and s*f['flow1']>=.10 and s*f['ret1']>=0)
        if retest and not f['trigger']:
            f['trigger']=True;f['entryVariant']='PULLBACK_RETEST'
    # Reversal is not vetoed by opposing high timeframe trend.
    # Breakout uses v1 rolling compression/trigger with native levels recorded.
    return f

def advance(previous,f,cut,decision,quote,spread):
    if previous and previous['state'] in ('PREPARE','LATE') and previous.get('direction') and f.get('direction') and previous['direction']!=f['direction']:
        previous=None  # do not inherit the opposite setup's anchor
    result=r11.advance(previous,f,cut,decision,quote,spread)
    if result and result['state']=='PREPARE' and f['entryVariant'] in ('NATIVE15_UNKNOWN','CONTEXT_CONFLICT'):
        result['reason']=f['entryVariant']
    return result
