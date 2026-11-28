"""Prospective impulse exhaustion hypothesis. No I/O; frozen provisional thresholds."""
from filters import r11
VERSION='r112-impulse-v1'
STEP=60000
WAIT=5*STEP
COOLDOWN=15*STEP

def impulse(f):
    if f['rvol1m']<1.5 or abs(f['ret5'])<.30 or f['flow5'] is None:return None
    sign=1 if f['ret5']>0 else -1
    return ('DOWN' if sign==1 else 'UP') if sign*f['flow5']>=.10 else None

def assess(previous,f,rows,cut,decision,quote,spread):
    """Only live contiguous closed inputs, recovery must follow an earlier impulse."""
    if not 0<=decision-cut<=15000:return None
    p=previous
    if p and p['state'] in ('READY','MONITOR','INVALIDATED'):
        if decision-p['readyAt']<=COOLDOWN:
            sign=1 if p['direction']=='UP' else -1
            change=sign*100*(f['price']/p['readyPrice']-1)
            state='INVALIDATED' if p['state']=='INVALIDATED' or change<=-max(.4,p['readyAtr']) else 'MONITOR'
            return dict(p,state=state,cutoff=cut,decisionAt=decision,movePct=change,reason='ADVERSE_MOVE' if state=='INVALIDATED' else 'TRACKING')
        return None
    if p and cut-p['impulseCutoff']>WAIT:
        return dict(p,state='EXPIRED',cutoff=cut,decisionAt=decision,reason='RECOVERY_TIMEOUT')
    if p and p['state'] in ('EXPIRED','LATE','CANCELLED'):return None
    if p is None:
        di=impulse(f)
        if not di:return None
        return dict(state='PREPARE',direction=di,cutoff=cut,decisionAt=decision,impulseCutoff=cut,
                    prepareAt=decision,anchor=f['price'],impulseFeatures=f,features=f,reason='IMPULSE_DETECTED')
    sign=1 if p['direction']=='UP' else -1
    # Require a consecutive observed minute for confirmation; no invented live history.
    if p['cutoff']!=cut-STEP:
        return dict(p,state='CANCELLED',cutoff=cut,decisionAt=decision,reason='LIVE_GAP')
    if impulse(f) and impulse(f)!=p['direction']:
        return dict(p,state='CANCELLED',cutoff=cut,decisionAt=decision,reason='OPPOSITE_IMPULSE')
    bar=rows[-1];prev=rows[-2]
    op,hi,lo,cl=map(float,bar[1:5]);rng=hi-lo
    wick=((min(op,cl)-lo) if sign==1 else (hi-max(op,cl)))/rng if rng>0 else 0.
    break1=cl>float(prev[2]) if sign==1 else cl<float(prev[3])
    # A rejection wick is a price-response proxy, not proof of absorption.
    recovery=sign*f['ret1']>=.03 and f['flow1'] is not None and sign*f['flow1']>=.10 and (break1 or wick>=.4)
    result=dict(p,state='PREPARE',cutoff=cut,decisionAt=decision,features=f,wickFraction=wick,
                reclaimPrevious=break1,reason='WAIT_RECOVERY')
    if not recovery:return result
    result.update(reason='BOOK_UNKNOWN',recoveryCutoff=cut)
    if quote is None or spread is None:return result
    if spread>r11.SPREAD_CAP:return dict(result,reason='WIDE_SPREAD')
    chase=sign*100*(quote/f['price']-1)
    distance=sign*100*(quote/p['anchor']-1)
    if chase>.30 or distance>max(.30,1.5*f['atr1mPct']):
        return dict(result,state='LATE',reason='CHASE')
    if chase<-.15:return dict(result,reason='TRIGGER_REJECTED')
    return dict(result,state='READY',reason='RECOVERY_CONFIRMED',readyAt=decision,readyPrice=quote,
                readyAtr=f['atr1mPct'],spreadPct=spread,chasePct=chase,prepareLeadMs=decision-p['prepareAt'])
