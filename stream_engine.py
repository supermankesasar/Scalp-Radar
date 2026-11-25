"""Public Binance USD-M streams. No private endpoints, credentials, or orders.
Bounded candle cache and minute microstructure aggregates; no SQLite in receive loop.
"""
import asyncio
import json
import math
import threading
import time
from collections import defaultdict
from statistics import median

BASE='wss://fstream.binance.com'
TF={'1m':60000,'5m':300000,'15m':900000,'1h':3600000,'4h':14400000}
LIMIT={'1m':100,'5m':310,'15m':230,'1h':230,'4h':230}
def ms():return int(time.time()*1000)
def close_at(now,step):return now//step*step-1
def finite(x):return math.isfinite(x)
def chunks(values,n):
    return [values[i:i+n] for i in range(0,len(values),n)]
def stream_groups(symbols):
    syms=sorted(s.lower() for s in symbols)
    return [('market','candles',g,[s+'@kline_'+tf for s in g for tf in TF]) for g in chunks(syms,30)]+[
      ('market','trades',g,[s+'@aggTrade' for s in g]) for g in chunks(syms,50)]+[
      ('public','depth',g,[s+'@depth5@500ms' for s in g]) for g in chunks(syms,60)]+[
      ('market','liquidations',syms,['!forceOrder@arr']),('market','tickers',syms,['!ticker@arr'])]

class StreamEngine:
    def __init__(self):
        self.lock=threading.RLock()
        self.stop=threading.Event()
        self.symbols=set()
        self.bars={}
        self.quotes={}
        self.buckets={}
        self.last_trade={}
        self.last_depth={}
        self.last_liq={}
        self.candle_received={}
        self.last_prune=0
        self.connected={}
        self.conn={}
        self.errors=[]
        self.rest_hits=0
        self.cache_hits=0
        self.late=0
        self.messages=0
        self.gaps=0
    def set_symbols(self,symbols):
        with self.lock:
            self.symbols=set(symbols)
            for mapping in (self.bars,self.buckets,self.connected,self.candle_received):
                for k in list(mapping):
                    if k[0] not in self.symbols: del mapping[k]
            for mapping in (self.quotes,self.last_trade,self.last_depth,self.last_liq):
                for k in list(mapping):
                    if k not in self.symbols: del mapping[k]
    def seed(self,symbol,tf,rows,now):
        with self.lock:
            if symbol not in self.symbols:return
            key=(symbol,tf)
            d=self.bars.setdefault(key,{})
            for r in rows:
                t=int(r[6])
                if t<now:d.setdefault(t,r)
            self.trim(d,LIMIT[tf]+5)
    @staticmethod
    def trim(d,n):
        if len(d)>n:
            for k in sorted(d)[:-n]:del d[k]
    def candles(self,symbol,tf,limit,now,require=True):
        with self.lock:
            d=self.bars.get((symbol,tf),{})
            step=TF[tf]; end=close_at(now,step)
            rows=[d[t] for t in range(end-(limit-1)*step,end+1,step) if t in d]
            if require and (len(rows)!=limit or int(rows[-1][6])!=end):return None
            return rows or None
    def ready(self,symbol,now):
        # R08 uses at least 220 bars and latest closed candle; full lookback matches REST.
        return all(self.candles(symbol,tf,n-1,now) is not None for tf,n in LIMIT.items())
    def prices(self,symbols,now):
        with self.lock:
            return {s:p for s,(p,t) in self.quotes.items() if (symbols is None or s in symbols) and 0<=now-t<=10000}
    def bucket(self,s,t):
        key=(s,t//60000*60000)
        return self.buckets.setdefault(key,{'buy':0.,'sell':0.,'count':0,'maxBuy':0.,'maxSell':0.,
            'tradeGap':False,'depthCount':0,'depthSum':0.,'imbSum':0.,'depthLast':None,'spreadLast':None,
            'depthTs':None,'liqBuy':0.,'liqSell':0.,'liqCount':0})
    def ingest(self,msg,received=None):
        received=ms() if received is None else received
        data=msg.get('data',msg) if isinstance(msg,dict) else msg
        events=data if isinstance(data,list) else [data]
        with self.lock:
            for e in events:
                if not isinstance(e,dict):continue
                try:self._ingest(e,received)
                except (ValueError,KeyError,TypeError,IndexError,OverflowError,ZeroDivisionError):
                    self.errors=(self.errors+['invalid stream event'])[-20:]
    def _ingest(self,e,received):
        kind=e.get('e');s=e.get('s')
        if kind=='forceOrder':s=e['o']['s']
        if s not in self.symbols:return
        self.messages+=1
        if kind=='kline':
            k=e['k'];tf=k['i']
            if tf not in TF:return
            if k['x']:
                t=int(k['T'])
                if t>=received or t%TF[tf]!=TF[tf]-1:return
                raw=[k['t'],k['o'],k['h'],k['l'],k['c'],k['v'],t,k['q'],k['n'],k['V'],k['Q'],'0']
                if not all(finite(float(raw[i])) for i in (1,2,3,4,5,7,9,10)) or float(raw[4])<=0:return
                d=self.bars.setdefault((s,tf),{})
                d[t]=raw;self.trim(d,LIMIT[tf]+5)
                receipts=self.candle_received.setdefault((s,tf),{})
                receipts.setdefault(t,received);self.trim(receipts,LIMIT[tf]+5)
            return
        if kind=='24hrTicker':
            p=float(e['c']); t=int(e['E'])
            if p>0 and finite(p) and 0<=received-t<=10000 and t>=self.quotes.get(s,(0,0))[1]:
                self.quotes[s]=(p,t)
            return
        t=int(e.get('T',e.get('E',received)))
        if kind=='forceOrder':t=int(e['o']['T'])
        if t>received+2000 or received-t>15000:
            self.late+=1;return
        if kind=='aggTrade':
            aid=int(e['a']); old=self.last_trade.get(s)
            if old is not None and aid<=old:return
            q=float(e['p'])*float(e['q'])
            if q<=0 or not finite(q):return
            b=self.bucket(s,t)
            if old is not None and aid!=old+1:b['tradeGap']=True;self.gaps+=1
            self.last_trade[s]=aid
            side='sell' if e['m'] else 'buy';big='maxSell' if e['m'] else 'maxBuy'
            b[side]+=q;b['count']+=1;b[big]=max(b[big],q)
            p=float(e['p'])
            if t>=self.quotes.get(s,(0,0))[1]:self.quotes[s]=(p,t)
        elif kind=='depthUpdate':
            u=int(e['u']);old=self.last_depth.get(s)
            if old is not None and u<=old:return
            bids=[(float(p),float(q)) for p,q in e['b'] if float(q)>0]
            asks=[(float(p),float(q)) for p,q in e['a'] if float(q)>0]
            if not bids or not asks:return
            bid=max(p for p,q in bids);ask=min(p for p,q in asks)
            if bid<=0 or ask<bid:return
            bq=sum(p*q for p,q in bids);aq=sum(p*q for p,q in asks);total=bq+aq
            if total<=0 or not finite(total):return
            self.last_depth[s]=u
            b=self.bucket(s,t);b['depthCount']+=1;b['depthSum']+=total;b['imbSum']+=(bq-aq)/total
            if b['depthTs'] is None or t>=b['depthTs']:
                b['depthLast']=total;b['spreadLast']=100*(ask-bid)/((ask+bid)/2);b['depthTs']=t
        elif kind=='forceOrder':
            o=e['o'];key=(t,o['S'],o['ap'],o['z'])
            if self.last_liq.get(s)==key:return
            self.last_liq[s]=key
            q=float(o['ap'])*float(o['z'])
            if q<=0 or not finite(q):return
            b=self.bucket(s,t);b['liqBuy' if o['S']=='BUY' else 'liqSell']+=q;b['liqCount']+=1
    def connection(self,kind,group,online,now):
        with self.lock:
            for s in group:
                s=s.upper()
                if online:self.connected[(s,kind)]=now
                else:self.connected.pop((s,kind),None)
                if kind=='trades':self.last_trade.pop(s,None)
                if kind=='depth':self.last_depth.pop(s,None)
    def minute(self,s,cutoff,now):
        start=cutoff-59999
        with self.lock:
            b=dict(self.buckets.get((s,start),{}))
            past=[dict(self.buckets.get((s,start-i*60000),{})) for i in range(1,21)]
            connected={kind:self.connected.get((s,kind),now+1) for kind in ('trades','depth','liquidations')}
            coverage={kind:t<=start for kind,t in connected.items()}
            if start>self.last_prune:
                for k in list(self.buckets):
                    if k[1]<start-22*60000:del self.buckets[k]
                self.last_prune=start
        trade=coverage['trades'] and not b.get('tradeGap') and b.get('count',0)>0
        depth=coverage['depth'] and b.get('depthCount',0)>=3 and b.get('depthTs',0)>=cutoff-5000
        liq=coverage['liquidations']
        trade_past=[x for i,x in enumerate(past,1) if connected['trades']<=start-i*60000 and x.get('count',0)>0 and not x.get('tradeGap')]
        depth_past=[x for i,x in enumerate(past,1) if connected['depth']<=start-i*60000 and x.get('depthCount',0)>=3]
        sizes=[(x['buy']+x['sell'])/x['count'] for x in trade_past]
        volumes=[x['buy']+x['sell'] for x in trade_past]
        depths=[x['depthSum']/x['depthCount'] for x in depth_past]
        # Compare to prior complete windows only after 10 observed minutes.
        if not coverage['trades'] or self.connected_since(s,'trades')>start-10*60000:sizes=[];volumes=[]
        if not coverage['depth'] or self.connected_since(s,'depth')>start-10*60000:depths=[]
        total=b.get('buy',0)+b.get('sell',0)
        return {'coverage':{'trades':bool(trade),'depth':bool(depth),'liquidations':bool(liq)},
          'tradeQuote':total if trade else None,'tradeCount':b.get('count') if trade else None,
          'cvdQuote':b.get('buy',0)-b.get('sell',0) if trade else None,
          'flow':(b['buy']-b['sell'])/total if trade and total else None,
          'bigBuy':b.get('maxBuy') if trade else None,'bigSell':b.get('maxSell') if trade else None,
          'bigThreshold':max(10000.,10*median(sizes)) if len(sizes)>=10 else None,
          'volumeRatio':total/median(volumes) if trade and len(volumes)>=10 and median(volumes)>0 else None,
          'imbalance':b['imbSum']/b['depthCount'] if depth else None,
          'depthQuote':b['depthLast'] if depth else None,'spreadPct':b['spreadLast'] if depth else None,
          'depthRatio':b['depthLast']/median(depths) if depth and len(depths)>=10 and median(depths)>0 else None,
          'liqBuy':b.get('liqBuy',0.) if liq else None,'liqSell':b.get('liqSell',0.) if liq else None,
          'liqCount':b.get('liqCount',0) if liq else None}
    def receipt(self,s,tf,cutoff):
        with self.lock:return self.candle_received.get((s,tf),{}).get(cutoff)
    def connected_since(self,s,kind):
        with self.lock:return self.connected.get((s,kind),ms()+1)
    def status(self):
        with self.lock:
            return {'enabled':True,'symbols':len(self.symbols),'cachedSymbols':len({k[0] for k in self.bars}),
              'connections':dict(self.conn),'onlineConnections':sum(v=='connected' for v in self.conn.values()),'messages':self.messages,'lateEvents':self.late,'tradeIdGaps':self.gaps,
              'restKlineRequests':self.rest_hits,'wsCacheHits':self.cache_hits,'recentErrors':list(self.errors)}
    async def session(self,route,kind,group,streams,delay):
        from websockets.asyncio.client import connect
        await asyncio.sleep(delay)
        label=kind+':'+group[0]
        url=BASE+'/'+route+'/stream?streams='+'/'.join(streams)
        backoff=2
        while not self.stop.is_set():
            try:
                async with connect(url,open_timeout=20,ping_interval=30,ping_timeout=20,max_queue=64,max_size=4*1024*1024) as ws:
                    self.connection(kind,group,True,ms())
                    with self.lock:self.conn[label]='connected'
                    started=time.monotonic()
                    while not self.stop.is_set() and time.monotonic()-started<23*3600:
                        message=await asyncio.wait_for(ws.recv(),timeout=90)
                        self.ingest(json.loads(message))
                        backoff=2
            except asyncio.CancelledError:raise
            except Exception as exc:
                with self.lock:self.errors=(self.errors+[label+': '+str(exc)[:160]])[-20:]
            finally:
                self.connection(kind,group,False,ms())
                with self.lock:self.conn[label]='disconnected'
            await asyncio.sleep(backoff);backoff=min(120,backoff*2)
    async def run(self):
        tasks=[];current=set()
        try:
            while not self.stop.is_set():
                with self.lock:desired=set(self.symbols)
                if desired!=current:
                    for t in tasks:t.cancel()
                    await asyncio.gather(*tasks,return_exceptions=True)
                    with self.lock:self.conn.clear()
                    current=desired
                    tasks=[asyncio.create_task(self.session(*g,i*.4)) for i,g in enumerate(stream_groups(current))] if current else []
                await asyncio.sleep(3)
        finally:
            for t in tasks:t.cancel()
            await asyncio.gather(*tasks,return_exceptions=True)
    def run_forever(self):
        try:asyncio.run(self.run())
        except Exception as exc:
            with self.lock:self.errors=(self.errors+[str(exc)[:200]])[-20:]
