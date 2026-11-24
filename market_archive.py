"""All-crypto USDT perpetual market archive. Public read-only API, standard library.
Historical samples are timestamped separately from the time actually received.
"""
import json, sqlite3, threading, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError
from contextlib import contextmanager

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
        self.pause_until=0.
        self.stop=threading.Event()
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
        with self.pace:
            delay=max(self.next_request,self.pause_until)-time.monotonic()
            if delay>0 and self.stop.wait(delay): raise RuntimeError('Stopping')
            if self.stop.is_set(): raise RuntimeError('Stopping')
            self.next_request=time.monotonic()+.55
        url=BASE+endpoint+('?' + urlencode(params) if params else '')
        try:
            with urlopen(Request(url,headers={'Accept':'application/json','User-Agent':'ScalpRadar-market-archive/1.0'}),timeout=18) as r:
                return json.loads(r.read()),now_ms()
        except HTTPError as e:
            if e.code in (429,418,403,451):
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
    def warmup(self,symbol,tf,rows,received):
        # Archive longer-timeframe input already fetched by the scanner.
        kind='kline_'+tf
        with self.db() as db:
            exists=db.execute('SELECT 1 FROM market_observations WHERE kind=? AND symbol=? LIMIT 1',(kind,symbol)).fetchone()
        if exists: rows=rows[-12:]
        return self.put(kind,symbol,[(r[6],r) for r in rows],received)
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
                        for r in data:
                            if r.get('symbol') in universe:
                                stamp=int(r.get('time',r.get('closeTime',received-1)))
                                self.put(kind,r['symbol'],[(min(stamp,received-1),r)],received)
                    except Exception as e:
                        errors+=1; self.error(run,'*',kind,e)
                with ThreadPoolExecutor(max_workers=4) as pool:
                    futures={pool.submit(self.collect_symbol,run,s,first):s for s in sorted(universe)}
                    for f in as_completed(futures):
                        n=f.result(); processed+=1;errors+=n;complete+=int(n==0)
                        if processed%25==0 or processed==len(universe):
                            with self.db() as db:
                                db.execute('UPDATE market_collection_runs SET processed=?,complete=?,errors=? WHERE id=?',(processed,complete,errors,run))
                            print('[ARCHIVE]',processed,'/',len(universe),'complete:',complete,'errors:',errors,flush=True)
                state='COMPLETE' if processed==len(universe) and not errors else 'PARTIAL'
            except Exception as e:
                errors+=1; self.error(run,'*','sweep',e);state='ERROR'
                print('[ARCHIVE]',str(e),flush=True)
            with self.db() as db:
                db.execute('UPDATE market_collection_runs SET ended_at=?,processed=?,complete=?,errors=?,state=? WHERE id=?',(now_ms(),processed,complete,errors,state,run))
            first=False
            # At least 30 minutes between sweep starts. Endpoint batches return 5m samples
            # for past four hours; this is not a claim of simultaneous live 5m polling.
            self.stop.wait(max(30.,1800-(now_ms()-started)/1000))
    def status(self):
        with self.db() as db:
            row=db.execute('SELECT * FROM market_collection_runs ORDER BY id DESC LIMIT 1').fetchone()
            counts=db.execute('SELECT kind,COUNT(*) n,COUNT(DISTINCT symbol) pairs,MAX(source_ts) latest,MAX(received_at) last_received FROM market_observations GROUP BY kind').fetchall()
            recent=db.execute('SELECT symbol,kind,at,message FROM market_collection_errors ORDER BY id DESC LIMIT 10').fetchall()
            return {'run':dict(row) if row else None,'data':[dict(r) for r in counts],'recentErrors':[dict(r) for r in recent],
                    'note':'ALL active crypto USDT perpetuals; archived historical sample time and actual receipt time differ. No trades.'}
