"""Exploratory R09 1m hypotheses. Missing stream data is not zero evidence."""
VERSION='r09-ws-micro-v1'
def evaluate(m,bars,ema):
    if len(bars)<22:return []
    c,p=bars[-1],bars[-2]
    px=float(c[4]);prev=float(p[4]);ret=100*(px/prev-1)
    q=float(c[7]);prior=sum(float(x[7]) for x in bars[-21:-1])/20
    rv=q/prior if prior else 0
    width=max(float(c[2])-float(c[3]),1e-12)
    body=(px-float(c[1]))/width
    flow=m.get('flow');imb=m.get('imbalance');vac=m.get('depthRatio')
    liqbuy=m.get('liqBuy');liqsell=m.get('liqSell')
    vol=m.get('volumeRatio');threshold=m.get('bigThreshold')
    closes=[float(x[4]) for x in bars]
    tags=[]
    def tag(name,s,score=None):tags.append({'id':'R09_'+name,'direction':'UP' if s==1 else 'DOWN','score':score})
    for s in (1,-1):
        for period in (9,10,14):
            es=ema(closes,period)
            if s*(px-es[-1])>0 and s*(prev-es[-2])<=0:tag('EMA%d_1M'%period,s)
        direction=s*ret>0
        aggressive=flow is not None and s*flow>=.20
        book=imb is not None and s*imb>=.20
        big=m.get('bigBuy' if s==1 else 'bigSell')
        printok=threshold is not None and big is not None and big>=threshold
        vacuum=vac is not None and vac<=.5 and book and direction
        liq=liqbuy if s==1 else liqsell
        other=liqsell if s==1 else liqbuy
        cascade=liq is not None and other is not None and liq>=10000 and liq>=3*max(other,1) and direction
        wick=(min(float(c[1]),px)-float(c[3]))/width if s==1 else (float(c[2])-max(float(c[1]),px))/width
        absorption=flow is not None and -s*flow>=.30 and abs(body)<=.30 and wick>=.40 and rv>=1.5
        acceleration=vol is not None and vol>=2 and aggressive and direction and rv>=1.5
        continuation=aggressive and direction and rv>=1.5
        if printok and direction:tag('BIG_AGG_PRINT',s)
        if book and direction:tag('BOOK_IMBALANCE',s)
        if vacuum:tag('DEPTH_VACUUM_PROXY',s)
        if cascade:tag('LIQUIDATION_BURST_PROXY',s)
        if absorption:tag('ABSORPTION',s)
        if acceleration:tag('ACCELERATION',s)
        if continuation:tag('FLOW_CONTINUATION',s)
        if rv>=1.5 and direction:tag('RVOL_CONTROL',s)
        score=(25 if aggressive else 0)+(20 if book else 0)+(15 if rv>=1.5 else 0)+(15 if direction else 0)+(15 if printok or cascade else 0)+(10 if acceleration or vacuum else 0)
        if flow is not None and imb is not None and score>=65 and direction and (aggressive or absorption) and abs(ret)<=2:tag('MULTI_MICRO',s,score)
    return tags

def hybrid(m, core, sign, direction_ok):
    """5m R08 plus last-minute microstructure: independent comparable tag."""
    flow=m.get('flow');imb=m.get('imbalance')
    if flow is None or imb is None:return {'score':None,'potential':False}
    aggressive=sign*flow>=.15
    book=sign*imb>=.15
    big=m.get('bigBuy' if sign==1 else 'bigSell')
    threshold=m.get('bigThreshold')
    liq=m.get('liqBuy' if sign==1 else 'liqSell')
    other=m.get('liqSell' if sign==1 else 'liqBuy')
    printok=big is not None and threshold is not None and big>=threshold
    cascade=liq is not None and other is not None and liq>=10000 and liq>=3*max(other,1)
    score=round(.65*core+(15 if aggressive else 0)+(10 if book else 0)+(10 if printok or cascade else 0),2)
    return {'score':score,'potential':bool(direction_ok and aggressive and book and score>=65)}
