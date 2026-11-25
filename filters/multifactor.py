"""R08: frozen exploratory rules, no I/O, no AI, closed bars only."""
import statistics as st
VERSION='r08-multi-v1'
def mean(x): return st.mean(x) if x else 0.
def ratio(a,b): return a/b if b else None
def change(a,b): return 100*(a/b-1) if b else None
def z(x,history):
    sd=st.pstdev(history) if len(history)>1 else 0
    return (x-mean(history))/sd if sd else None
def signed(x,s,limit=0): return x is not None and s*x>limit
def at(x,k): return x.get(k) if x else None

def extract(rows,rsi,atr):
    if len(rows)<61: return None
    b=rows[-61:]
    if any(y['closeTime']-x['closeTime']!=300000 for x,y in zip(b,b[1:])):return None
    c=b[-1]; p=b[-2]; a=atr(b); prevatr=atr(b[:-12])
    if not a or not c['close']:return None
    q=[x['quoteVolume'] for x in b]
    n=[x.get('tradeCount') for x in b]
    delta=[2*x['takerBuyQuote']-x['quoteVolume'] for x in b]
    flow=lambda seq:ratio(sum(delta[seq]),sum(q[seq]))
    h=max(x['high'] for x in b[-13:-1]);l=min(x['low'] for x in b[-13:-1])
    h6=max(x['high'] for x in b[-7:-1]);l6=min(x['low'] for x in b[-7:-1])
    highs=[];lows=[]
    for i in range(2,len(b)-2):
        w=b[i-2:i+3]
        if all(b[i]['high']>v['high'] for j,v in enumerate(w) if j!=2):highs.append(i)
        if all(b[i]['low']<v['low'] for j,v in enumerate(w) if j!=2):lows.append(i)
    def neckline(ids,k,fn):
        if len(ids)<2:return None
        seq=[v[k] for v in b[ids[-2]+1:ids[-1]]]
        return fn(seq) if seq else None
    def near(ids,k):
        return len(ids)>=2 and ids[-1]-ids[-2]>=4 and abs(b[ids[-1]][k]-b[ids[-2]][k])<=.6*a
    def hs(ids,k,s):
        if len(ids)<3:return False
        x,y,z0=[b[i][k] for i in ids[-3:]]
        return abs(x-z0)<=a and s*(y-max(x,z0) if s==1 else y-min(x,z0))>.7*a
    nt=neckline(highs,'low',min);nb=neckline(lows,'high',max)
    def divergence(ids,k,s):
        if len(ids)<2:return False
        i,j=ids[-2:];ri=rsi([v['close'] for v in b[:i+1]]);rj=rsi([v['close'] for v in b[:j+1]])
        return ri is not None and rj is not None and s*(b[j][k]-b[i][k])>0 and s*(ri-rj)>=3
    def slopes(ids,k):
        return (b[ids[-1]][k]-b[ids[-2]][k])/(ids[-1]-ids[-2]) if len(ids)>=2 else None
    sh,sl=slopes(highs,'high'),slopes(lows,'low')
    compression=sh is not None and sl is not None and sh<0<sl
    width=max(c['high']-c['low'],1e-12)
    rvol=ratio(q[-1],mean(q[-21:-1]))
    validcounts=all(v is not None and v>0 for v in n[-21:])
    sizes=[v/t for v,t in zip(q[-21:],n[-21:])] if validcounts else []
    return {'cutoff':c['closeTime'],'rvol':rvol,'volumeZ':z(q[-1],q[-21:-1]),
      'tradeZ':z(n[-1],n[-21:-1]) if validcounts else None,
      'avgTradeSizeZ':z(sizes[-1],sizes[:-1]) if sizes else None,
      'atrRatio':ratio(a,prevatr),'rangeATR':width/a,'bodyATR':(c['close']-c['open'])/a,
      'flow5':flow(slice(-1,None)),'flow15':flow(slice(-3,None)),'flow60':flow(slice(-12,None)),
      'priorFlow15':flow(slice(-6,-3)),'ret5':change(c['close'],p['close']),
      'ret15':change(c['close'],b[-4]['close']),'ret60':change(c['close'],b[-13]['close']),
      'priorRet15':change(p['close'],b[-5]['close']),
      'priceEfficiency':ratio(abs(c['close']-b[-4]['close']),sum(abs(b[i]['close']-b[i-1]['close']) for i in range(len(b)-3,len(b)))),
      'upperWick':(c['high']-max(c['open'],c['close']))/width,
      'lowerWick':(min(c['open'],c['close'])-c['low'])/width,
      'breakUp':c['close']>h,'breakDown':c['close']<l,
      'breakUp6':c['close']>h6,'breakDown6':c['close']<l6,
      'sweepUp':c['low']<l6 and c['close']>l6,'sweepDown':c['high']>h6 and c['close']<h6,
      'doubleTop':near(highs,'high') and nt is not None and c['close']<nt<=p['close'],
      'doubleBottom':near(lows,'low') and nb is not None and c['close']>nb>=p['close'],
      'headShoulders':hs(highs,'high',1) and nt is not None and c['close']<nt<=p['close'],
      'inverseHS':hs(lows,'low',-1) and nb is not None and c['close']>nb>=p['close'],
      'bearDiv':divergence(highs,'high',1),'bullDiv':divergence(lows,'low',-1),
      'compression':compression,'hhhl':sh is not None and sl is not None and sh>0 and sl>0,
      'lhll':sh is not None and sl is not None and sh<0 and sl<0}

def evaluate(c,s):
    m=c.get('multi')
    if not m:return {'core':0,'full':None,'potential':False,'fullPotential':False,'tags':[],'coverage':{},'points':{}}
    d=c.get('derivatives') or {};b=c.get('breadth') or {}
    rv=m['rvol'] or 0
    anomaly=rv>=1.5 or (m['tradeZ'] or 0)>=2 or ((m['atrRatio'] or 0)>=1.2 and m['rangeATR']>=1.5)
    flow=signed(m['flow15'],s,.10); nowflow=signed(m['flow5'],s,.10)
    br=m['breakUp' if s==1 else 'breakDown'];fastbr=m['breakUp6' if s==1 else 'breakDown6']
    sweep=m['sweepUp' if s==1 else 'sweepDown']
    divg=m['bullDiv' if s==1 else 'bearDiv']
    pattern=m['doubleBottom' if s==1 else 'doubleTop'] or m['inverseHS' if s==1 else 'headShoulders']
    wick=m['lowerWick' if s==1 else 'upperWick']>=.4
    aligned=m['hhhl' if s==1 else 'lhll']
    # AIOT/SKY hypothesis: opposing aggressive flow with limited price response and rejection.
    absorb=rv>=1.5 and signed(m['flow5'],-s,.25) and abs(m['bodyATR'])<=.5 and wick
    # PIEVERSE/FLOCK: extended move then divergence/rejection and new opposing structure.
    exhaustion=signed(m['ret60'],-s,2) and (divg or wick) and (fastbr or sweep)
    # SKYAI: short-frame structural break and flow flip; no 1h trend gate.
    flip=nowflow and signed(m['priorFlow15'],-s,.05)
    minute=c.get('minute') or {};series=minute.get('series',{}).get('9',{})
    mc=series.get('close',[])
    fastmove=len(mc)>=4 and signed(change(mc[-1],mc[0]),s,max(.15,.5*c['atr_pct']))
    reversal=(fastbr or sweep) and (flip or fastmove) and (divg or wick or signed(m['priorRet15'],-s,.3))
    # CYS/AIN: actual price response plus aggressive flow, not volume alone.
    continuation=anomaly and flow and fastbr and signed(m['bodyATR'],s,.3)
    trap=(m['sweepDown'] if s==1 else m['sweepUp']) or (signed(m['flow5'],s,.25) and signed(m['bodyATR'],-s,.25))
    oi=d.get('oiDelta15');oi_price=d.get('oiPriceRet15')
    build=oi is not None and oi>=.5 and signed(oi_price,s,.1)
    unwind=oi is not None and oi<=-.5 and signed(oi_price,s,.1)
    position=d.get('topPositionDeltaPP');account=d.get('globalDeltaPP')
    pos=signed(position,s,.5) or signed(account,s,.5)
    funding=d.get('fundingSnapshot')
    # Funding as crowding context only, never treated as realized funding or direction alone.
    crowded=funding is not None and s*funding>=.0005
    breadth=b.get('upShare');relative=b.get('relativeBTC')
    market=breadth is not None and (breadth>=.55 if s==1 else breadth<=.45)
    rel=signed(relative,s,.2)
    emaok=signed(c['close5']-c['ema21_5'],s)
    r=c.get('rsi5');rs=r is not None and (47<=r<=70 if s==1 else 30<=r<=53)
    momentum=signed(m['ret5'],s) and rs
    pts={'trend':(5 if c['trend1h']==('BULLISH' if s==1 else 'BEARISH') else 0)+(5 if emaok else 0)+(5 if aligned else 0),
         'activity':(10 if rv>=1.5 else 5 if rv>=1.1 else 0)+(5 if (m['tradeZ'] or 0)>=2 else 0)+(5 if (m['atrRatio'] or 0)>=1.2 else 0),
         'flow':(10 if flow else 0)+(5 if nowflow else 0)+(5 if signed(m['bodyATR'],s,.3) else 0),
         'structure':20 if br or pattern else 15 if fastbr or sweep else 0,
         'timing':(10 if reversal or continuation or absorb or exhaustion else 0)+(5 if fastmove or flip else 0),
         'momentum':(5 if momentum else 0)+(5 if c['vwap'] is not None and signed(c['close5']-c['vwap'],s) else 0)}
    core=sum(pts.values())
    # Avoid chasing an unusually large already-closed bar; ATR-scaled cap.
    fresh=abs(m['ret5'])<=max(1.0,2.5*c['atr_pct'])
    setup=(continuation or reversal or absorb or exhaustion or (pattern and anomaly))
    gate=setup and not trap and fresh
    potential=core>=65 and gate
    have_deriv=oi is not None and (position is not None or account is not None)
    have_breadth=breadth is not None and relative is not None
    derivative_pts=(8 if (build or unwind) and flow else 0)+(4 if pos else 0)+(3 if funding is not None and not crowded else 0)
    context_pts=(5 if market else 0)+(5 if rel else 0)
    full=round(.75*core+derivative_pts+context_pts,2) if have_deriv and have_breadth else None
    fullok=full is not None and full>=65 and gate
    tags=[]
    for ok,name in [(continuation,'CONTINUATION'),(reversal,'FAST_REVERSAL'),(absorb,'ABSORPTION'),(exhaustion,'EXHAUSTION'),
                    (pattern,'CHART_PATTERN'),(sweep,'LIQUIDITY_SWEEP_PROXY'),(anomaly and flow,'ANOMALY_FLOW'),
                    (flip and fastbr,'FLOW_FLIP'),(build and flow,'OI_BUILD_FLOW'),(unwind and flow,'OI_UNWIND_FLOW'),
                    (pos and flow,'POSITIONING_FLOW'),(market and rel and anomaly,'BREADTH_RELATIVE'),
                    (m['compression'] and fastbr and anomaly,'COMPRESSION_BREAK'),
                    (potential,'MULTI_CORE'),(fullok,'MULTI_FULL'),
                    (core-pts['trend']>=55 and gate,'NO_TREND_ABLATION')]:
        if ok:tags.append('R08_'+name)
    return {'core':core,'full':full,'potential':potential,'fullPotential':fullok,'tags':tags,'points':pts,
            'coverage':{'derivatives':have_deriv,'breadth':have_breadth,'minute':bool(mc),'trades':m['tradeZ'] is not None},
            'anomaly':anomaly,'trap':trap,'fresh':fresh,'setup':setup}
