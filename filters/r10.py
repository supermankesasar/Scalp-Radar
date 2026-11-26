"""R10 preregistered shadow hypotheses; no trading or future inputs."""
VERSION='r10-v1'
def regime(returns,total):
    if not total or len(returns)<max(20,.6*total) or 'BTCUSDT' not in returns:
        return {'regime':'UNKNOWN','coverage':len(returns)/max(1,total)}
    up=sum(x>0 for x in returns.values())/len(returns)
    btc=returns['BTCUSDT']
    label='BULL' if up>=.65 and btc>=.15 else 'BEAR' if up<=.35 and btc<=-.15 else 'MIXED'
    return {'regime':label,'coverage':len(returns)/total,'upShare':up,'btcRet15':btc}

def tags1(m,prev,bars,a,ctx):
    if len(bars)<61 or not a:return []
    c=bars[-1];p=float(c[4]);o=float(c[1]);hi=float(c[2]);lo=float(c[3])
    w=max(hi-lo,1e-12);ret=100*(p/float(bars[-16][4])-1)
    prior=bars[-21:-1];v=sum(float(x[7]) for x in prior)/20
    rv=float(c[7])/v if v else 0
    flow=m.get('flow');old=prev.get('flow');book=m.get('imbalance')
    result=[]
    def tag(n,s):result.append({'id':'R10_'+n,'version':VERSION,'direction':'UP' if s==1 else 'DOWN'})
    for s in (1,-1):
        wick=(min(o,p)-lo)/w if s==1 else (hi-max(o,p))/w
        sweep=lo<min(float(x[3]) for x in bars[-7:-1]) and p>min(float(x[3]) for x in bars[-7:-1]) if s==1 else hi>max(float(x[2]) for x in bars[-7:-1]) and p<max(float(x[2]) for x in bars[-7:-1])
        flip=flow is not None and old is not None and s*flow>=.15 and s*old<=-.15
        opposing=flow is not None and s*flow<=-.30
        exhaust=-s*ret>=max(1.,3*a) and wick>=.4 and (sweep or flip) and rv>=1.5
        absorb=opposing and abs(p-o)/w<=.35 and wick>=.4 and rv>=1.5
        liq=m.get('liqSell' if s==1 else 'liqBuy')
        other=m.get('liqBuy' if s==1 else 'liqSell')
        cascade=liq is not None and other is not None and liq>=10000 and liq>=3*max(other,1)
        big=m.get('bigBuy' if s==1 else 'bigSell');threshold=m.get('bigThreshold')
        pressure=flow is not None and s*flow>=.20 and book is not None and s*book>=.15
        vacuum=m.get('depthRatio') is not None and m['depthRatio']<=.5
        aligned=ctx['regime']==('BULL' if s==1 else 'BEAR')
        for n,ok in [('EXHAUSTION_1M',exhaust),('SWEEP_FLIP_1M',sweep and flip and rv>=1.5),
                     ('ABSORPTION_CVD_1M',absorb and old is not None and s*old<=-.15),
                     ('LIQUIDATION_REVERSAL_1M',cascade and (sweep or exhaust)),
                     ('DEPTH_FLOW_1M',vacuum and pressure and s*(p-o)>0 and rv>=1.5),
                     ('LARGE_PRINT_FLOW_1M',pressure and big is not None and threshold is not None and big>=threshold and s*(p-o)>0),
                     ('REGIME_FLOW_1M',aligned and pressure and s*(p-o)>0 and rv>=1.5)]:
            if ok:tag(n,s)
    return result

def tags5(row):
    f=row.get('researchFeatures') or {};m=f.get('multi') or {};d=f.get('derivatives') or {};b=f.get('breadth') or {}
    result=[]
    for s,di in ((1,'UP'),(-1,'DOWN')):
        tags={x['id'] for x in row.get('researchCandidates',[]) if x['direction']==di}
        flow=m.get('flow5');oi=d.get('oiDelta15');price=d.get('oiPriceRet15');up=b.get('upShare');btc=b.get('btcRet15')
        aligned=up is not None and btc is not None and (up>=.65 and btc>=.15 if s==1 else up<=.35 and btc<=-.15)
        exhaust='R08_EXHAUSTION' in tags;sweep='R08_LIQUIDITY_SWEEP_PROXY' in tags;absorb='R08_ABSORPTION' in tags
        for n,ok in [('EXHAUST_SWEEP_5M',exhaust and sweep),('EXHAUST_DIVERGENCE_5M',exhaust and m.get('bullDiv' if s==1 else 'bearDiv')),
                     ('SWEEP_ABSORPTION_5M',sweep and absorb),('EXHAUST_OI_UNWIND_5M',exhaust and oi is not None and oi<=-.5 and price is not None and s*price<0),
                     ('OI_FLOW_BUILD_5M',oi is not None and oi>=.5 and price is not None and s*price>=.1 and flow is not None and s*flow>=.15 and 'R08_CONTINUATION' in tags),
                     ('REGIME_CONTINUATION_5M',aligned and 'R08_CONTINUATION' in tags)]:
            if ok:result.append({'id':'R10_'+n,'version':VERSION,'direction':di})
    return result
