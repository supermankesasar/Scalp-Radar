"""All-crypto USDT perpetual market archive. Public read-only API, standard library.
Historical samples are timestamped separately from the time actually received.
"""
import json, sqlite3, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from contextlib import contextmanager
from pathlib import Path
from rest_guard import REST_GUARD

BASE = 'https://fapi.binance.com'
KINDS = {
    'oi':'/futures/data/openInterestHist',
    'global_ls':'/futures/data/globalLongShortAccountRatio',
    'top_accounts':'/futures/data/topLongShortAccountRatio',
    'top_positions':'/futures/data/topLongShortPositionRatio',
}
def now_ms(): return int(time.time()*1000)
def crypto_universe(info):
    return {s['symbol'] for s in info.get('symbols',[])
        if s.get('status')=='TRADING' and s.get('contractType')=='PERPETUAL'
        and s.get('quoteAsset')=='USDT' and s.get('marginAsset')=='USDT'
        and s.get('underlyingType')=='COIN' and 'Crypto' in (s.get('underlyingSubType') or [])
        and s['symbol'] not in ('PAXGUSDT','XAUTUSDT','XAUUSDT','XAGUSDT')}

class MarketArchive:
    def __init__(self,path,lock):
        self.path,self.lock=str(path),lock
        self.pace=threading.Lock()
        self.next_request=0.
        self.stream=None
        self.metrics_lock=threading.Lock();self.metrics={'restRequests':0,'cached5m':0,'rest5m':0}
        self.pause_until=0.
        self.stop=threading.Event()
        self.breadth_lock=threading.Lock()
        self.breadth_cache={}
        self.heartbeat=lambda **kw:None
        with self.db() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript("""
            CREATE TABLE IF NOT EXISTS market_observations(
                kind TEXT NOT NULL,symbol TEXT NOT NULL,source_ts INTEGER NOT NULL,
                received_at INTEGER NOT NULL,payload TEXT NOT NULL,
                PRIMARY KEY(kind,symbol,source_ts));
            CREATE INDEX IF NOT EXISTS market_by_time ON market_observations(kind,source_ts);
            CREATE TABLE IF NOT EXISTS market_collection_runs(
                id INTEGER PRIMARY KEY,started_at INTEGER NOT NULL,ended_at INTEGER,
                universe INTEGER NOT NULL DEFAULT 0,processed INTEGER NOT NULL DEFAULT 0,
                complete INTEGER NOT NULL DEFAULT 0,errors INTEGER NOT NULL DEFAULT 0,state TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS market_collection_errors(
                id INTEGER PRIMARY KEY,run_id INTEGER,symbol TEXT,kind TEXT,at INTEGER,message TEXT);
            """)
            db.execute("UPDATE market_collection_runs SET state='INTERRUPTED',ended_at=? WHERE state='RUNNING'",(now_ms(),))
    @contextmanager
    def db(self):
        with self.lock:
            db=sqlite3.connect(self.path,timeout=30)
            db.row_factory=sqlite3.Row
            try:
                yield db
                db.commit()
            except Exception:
                db.rollback()
                raise
            finally: db.close()
    def fetch(self,endpoint,params=None):
        # Shared pacing across workers. A restricted endpoint is not bypassed.
        while True:
            with self.pace:
                delay=max(self.next_request-time.monotonic(),self.pause_until-time.monotonic(),REST_GUARD.remaining())
                if delay<=0:
                    delay=REST_GUARD.history_delay(endpoint)
                    if delay<=0:
                        self.next_request=time.monotonic()+.40
                        break
            if self.stop.wait(max(.01,delay)):raise RuntimeError('Stopping')
        if self.stop.is_set():raise RuntimeError('Stopping')
        REST_GUARD.check()
        with self.metrics_lock:self.metrics['restRequests']+=1
        url=BASE+endpoint+('?' + urlencode(params) if params else '')
        try:
            with urlopen(Request(url,headers={'Accept':'application/json','User-Agent':'ScalpRadar-market-archive/1.0'}),timeout=18) as r:
                data=json.loads(r.read())
                REST_GUARD.observe(getattr(r,'headers',None),data if endpoint=='/fapi/v1/exchangeInfo' else None)
                return data,now_ms()
        except HTTPError as e:
            if e.code in (429,418,403,451):
                if e.code in (429,418):REST_GUARD.pause(e.headers)
                with self.pace:
                    try: retry=float(e.headers.get('Retry-After','300'))
                    except (ValueError,TypeError): retry=300.
                    self.pause_until=max(self.pause_until,time.monotonic()+max(300.,retry))
                raise RuntimeError('HTTP %s: collection paused; no bypass'%e.code) from e
            raise
    def put(self,kind,symbol,items,received):
        rows=[(kind,symbol,int(t),received,json.dumps(p,separators=(',',':'),allow_nan=False)) for t,p in items if int(t)<received]
        if not rows:return 0
        with self.db() as db:
            cur=db.executemany('INSERT OR IGNORE INTO market_observations VALUES(?,?,?,?,?)',rows)
            return cur.rowcount
    def cached_5m(self,symbol,limit,now):
        """Reuse exact closed rows already in SQLite or WS; never imply fresh WS provenance."""
        step=300000;cut=now//step*step-1;start=cut-(limit-1)*step
        expected=set(range(start,cut+1,step))
        # Read-only WAL snapshot; do not queue behind unrelated ledger writes.
        db=sqlite3.connect(Path(self.path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10)
        try:
            stored={r[0] for r in db.execute("SELECT source_ts FROM market_observations WHERE kind='kline_5m' AND symbol=? AND source_ts BETWEEN ? AND ? AND received_at<=?",(symbol,start,cut,now))}
        finally:db.close()
        missing=expected-stored
        if not missing:return True
        cached=self.stream.candles(symbol,'5m',limit,now,require=False) if self.stream is not None else None
        additions={int(r[6]):r for r in (cached or []) if int(r[6]) in missing}
        if missing-set(additions):return False
        self.put('kline_5m',symbol,list(additions.items()),now)
        return True
    def warmup(self,symbol,tf,rows,received):
        # Archive longer-timeframe input already fetched by the scanner.
        kind='kline_'+tf
        with self.db() as db:
            exists=db.execute('SELECT 1 FROM market_observations WHERE kind=? AND symbol=? LIMIT 1',(kind,symbol)).fetchone()
        if exists and tf!='1m': rows=rows[-12:]
        # 1m backfill spans slow ALL scans; INSERT OR IGNORE deduplicates.
        return self.put(kind,symbol,[(r[6],r) for r in rows],received)
    def research_context(self,symbol,cutoff,decision,universe_size):
        # Strict point-in-time receipt and source bounds; stale context is absent.
        d={}
        with self.db() as db:
            for kind,key,field in [('oi','oiDelta15','sumOpenInterest'),
              ('global_ls','globalDeltaPP','longAccount'),('top_accounts','topAccountDeltaPP','longAccount'),
              ('top_positions','topPositionDeltaPP','longAccount')]:
                rows=db.execute("SELECT source_ts,payload FROM market_observations WHERE kind=? AND symbol=? AND source_ts<=? AND received_at<=? AND source_ts>=? ORDER BY source_ts DESC LIMIT 8",
                                (kind,symbol,cutoff,decision,cutoff-35*60000)).fetchall()
                if not rows or cutoff-rows[0]['source_ts']>10*60000:continue
                t=rows[0]['source_ts'];prior=next((x for x in rows[1:] if 15*60000<=t-x['source_ts']<=20*60000),None)
                if prior is None:continue
                try:
                    x=float(json.loads(rows[0]['payload'])[field]);y=float(json.loads(prior['payload'])[field])
                    if kind=='oi':
                        if not y:continue
                        # Match price return to OI interval, not present price.
                        end=(t//300000)*300000-1;start=(prior['source_ts']//300000)*300000-1
                        bars=db.execute("SELECT source_ts,payload FROM market_observations WHERE kind='kline_5m' AND symbol=? AND source_ts IN (?,?) AND received_at<=?",(symbol,start,end,decision)).fetchall()
                        prices={v['source_ts']:float(json.loads(v['payload'])[4]) for v in bars}
                        if start not in prices or end not in prices or not prices[start]:continue
                        d[key]=100*(x/y-1);d['oiPriceRet15']=100*(prices[end]/prices[start]-1);d['oiSourceTs']=t
                    else:d[key]=100*(x-y)
                except (KeyError,ValueError,TypeError,IndexError,ZeroDivisionError):continue
            row=db.execute("SELECT source_ts,payload FROM market_observations WHERE kind='mark_funding' AND symbol=? AND source_ts<=? AND source_ts>=? AND received_at<=? ORDER BY source_ts DESC LIMIT 1",(symbol,cutoff,cutoff-40*60000,decision)).fetchone()
            if row:
                try:
                    v=json.loads(row['payload']);d['fundingSnapshot']=float(v['lastFundingRate'])
                    mark,index=float(v['markPrice']),float(v['indexPrice'])
                    if index:d['basisPct']=100*(mark/index-1)
                    d['fundingSourceTs']=row['source_ts']
                except (KeyError,ValueError,TypeError,ZeroDivisionError):pass
        # Breadth is synchronized at one exact close; never combine different symbol timestamps.
        # Cache is built no later than the caller's decision, for 30 seconds only.
        bucket=(cutoff,universe_size)
        with self.breadth_lock:
            cached=self.breadth_cache.get(bucket)
            if cached is None or not 0<=decision-cached[0]<=30000:
                with self.db() as db:
                    rows=db.execute("SELECT symbol,source_ts,payload FROM market_observations WHERE kind='kline_5m' AND source_ts IN (?,?) AND received_at<=?",(cutoff,cutoff-900000,decision)).fetchall()
                prices={}
                for row in rows:
                    try:prices.setdefault(row['symbol'],{})[row['source_ts']]=float(json.loads(row['payload'])[4])
                    except (ValueError,TypeError,IndexError):continue
                returns={s:100*(v[cutoff]/v[cutoff-900000]-1) for s,v in prices.items() if cutoff in v and v.get(cutoff-900000,0)>0}
                cached=(decision,returns)
                self.breadth_cache={k:v for k,v in self.breadth_cache.items() if 0<=decision-v[0]<=300000}
                self.breadth_cache[bucket]=cached
            returns=cached[1]
        n=len(returns);b={'sampleCount':n,'universeSize':universe_size,'cutoff':cutoff}
        if universe_size and n>=max(20,.6*universe_size) and symbol in returns and 'BTCUSDT' in returns:
            b.update(upShare=sum(v>0 for v in returns.values())/n,relativeBTC=returns[symbol]-returns['BTCUSDT'],btcRet15=returns['BTCUSDT'])
        return d,b
    def error(self,run,symbol,kind,e):
        with self.db() as db:
            db.execute('INSERT INTO market_collection_errors(run_id,symbol,kind,at,message) VALUES(?,?,?,?,?)',(run,symbol,kind,now_ms(),str(e)[:300]))
    def collect_symbol(self,run,symbol,first):
        failures=0
        jobs=[('kline_5m','/fapi/v1/klines',{'symbol':symbol,'interval':'5m','limit':400 if first else 48})]
        jobs += [(k,v,{'symbol':symbol,'period':'5m','limit':100 if first else 48}) for k,v in KINDS.items()]
        for kind,endpoint,params in jobs:
            if self.stop.is_set(): break
            try:
                if kind=='kline_5m':
                    # REST limit usually includes open candle; require complete closed window conservatively.
                    if self.cached_5m(symbol,params['limit']-1,now_ms()):
                        with self.metrics_lock:self.metrics['cached5m']+=1
                        continue
                    with self.metrics_lock:self.metrics['rest5m']+=1
                data,received=self.fetch(endpoint,params)
                if not isinstance(data,list) or not data: raise ValueError('Empty or invalid market response')
                items=[(r[6],r) for r in data] if kind=='kline_5m' else [(r['timestamp'],r) for r in data]
                self.put(kind,symbol,items,received)
            except Exception as e:
                failures+=1
                self.error(run,symbol,kind,e)
        return failures
    def collect_forever(self):
        first=True
        while not self.stop.is_set():
            started=now_ms()
            with self.metrics_lock:self.metrics={'restRequests':0,'cached5m':0,'rest5m':0}
            self.heartbeat(state='collecting',processed=0)
            with self.db() as db:
                run=db.execute("INSERT INTO market_collection_runs(started_at,state) VALUES(?,'RUNNING')",(started,)).lastrowid
            errors=processed=complete=0
            universe=set()
            try:
                info,_=self.fetch('/fapi/v1/exchangeInfo')
                universe=crypto_universe(info)
                if not universe: raise RuntimeError('No eligible active crypto perpetual symbols')
                with self.db() as db: db.execute('UPDATE market_collection_runs SET universe=? WHERE id=?',(len(universe),run))
                print('[ARCHIVE] Run',run,'ALL',len(universe),'crypto pairs',flush=True)
                # Bulk snapshots, including estimated/last funding fields as returned by Binance.
                for kind,endpoint in [('mark_funding','/fapi/v1/premiumIndex'),('ticker24h','/fapi/v1/ticker/24hr')]:
                    try:
                        data,received=self.fetch(endpoint)
                        if not isinstance(data,list): raise ValueError('Expected bulk list')
                        batch=[]
                        for r in data:
                            if r.get('symbol') in universe:
                                stamp=int(r.get('time',r.get('closeTime',received-1)))
                                batch.append((kind,r['symbol'],min(stamp,received-1),received,json.dumps(r,separators=(',',':'),allow_nan=False)))
                        # Bounded transactions instead of opening a connection per symbol.
                        for offset in range(0,len(batch),64):
                            with self.db() as db:db.executemany('INSERT OR IGNORE INTO market_observations VALUES(?,?,?,?,?)',batch[offset:offset+64])
                    except Exception as e:
                        errors+=1; self.error(run,'*',kind,e)
                with ThreadPoolExecutor(max_workers=6) as pool:
                    futures={pool.submit(self.collect_symbol,run,s,first):s for s in sorted(universe)}
                    for f in as_completed(futures):
                        n=f.result(); processed+=1;errors+=n;complete+=int(n==0)
                        if processed%25==0 or processed==len(universe):
                            self.heartbeat(state='collecting',processed=processed,total=len(universe),errors=errors)
                            with self.db() as db:
                                db.execute('UPDATE market_collection_runs SET processed=?,complete=?,errors=? WHERE id=?',(processed,complete,errors,run))
                            with self.metrics_lock:metrics=dict(self.metrics)
                            print('[ARCHIVE]',processed,'/',len(universe),'complete:',complete,'errors:',errors,'REST:',metrics['restRequests'],'cached5m:',metrics['cached5m'],flush=True)
                state='COMPLETE' if processed==len(universe) and not errors else 'PARTIAL'
            except Exception as e:
                errors+=1; self.error(run,'*','sweep',e);state='ERROR'
                print('[ARCHIVE]',str(e),flush=True)
            with self.db() as db:
                db.execute('UPDATE market_collection_runs SET ended_at=?,processed=?,complete=?,errors=?,state=? WHERE id=?',(now_ms(),processed,complete,errors,state,run))
            first=False
            self.heartbeat(state='waiting',processed=processed,total=len(universe),errors=errors)
            # At least 30 minutes between sweep starts. Endpoint batches return 5m samples
            # for past four hours; this is not a claim of simultaneous live 5m polling.
            self.stop.wait(max(30.,1800-(now_ms()-started)/1000))
    def status(self):
        with self.db() as db:
            row=db.execute('SELECT * FROM market_collection_runs ORDER BY id DESC LIMIT 1').fetchone()
            counts=db.execute('SELECT kind,COUNT(*) n,COUNT(DISTINCT symbol) pairs,MAX(source_ts) latest,MAX(received_at) last_received FROM market_observations GROUP BY kind').fetchall()
            recent=db.execute('SELECT symbol,kind,at,message FROM market_collection_errors ORDER BY id DESC LIMIT 10').fetchall()
            with self.metrics_lock:metrics=dict(self.metrics)
            return {'run':dict(row) if row else None,'data':[dict(r) for r in counts],'recentErrors':[dict(r) for r in recent],'transport':metrics,
                    'note':'ALL active crypto USDT perpetuals; archived historical sample time and actual receipt time differ. No trades.'}
