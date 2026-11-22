"""Read-only historical candle archive and recorded-event evaluation, stdlib only."""
import json, os, sqlite3, threading, time, math
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parent
DB=ROOT/'data'/'market_history.sqlite3'
EVENT_DB=Path(os.getenv('SCANNER_DB',str(ROOT/'data'/'signals.sqlite3')))
REPORT=ROOT/'research'/'recorded_event_backtest.json'
LOCK=threading.RLock()
STATE={'status':'NOT_STARTED','message':'Research belum berjalan','updated_ms':None,'data':{},'backtest':None}
STARTED=False
STEP=300000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT')

def update(**fields):
    with LOCK: STATE.update(fields)

def status():
    with LOCK: return dict(STATE)

def connect():
    DB.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(DB,timeout=15)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('''CREATE TABLE IF NOT EXISTS bars(
    symbol TEXT NOT NULL,open_ms INTEGER NOT NULL,close_ms INTEGER NOT NULL,
    o REAL NOT NULL,h REAL NOT NULL,l REAL NOT NULL,c REAL NOT NULL,
    volume REAL NOT NULL, quote_volume REAL NOT NULL, ingested_ms INTEGER NOT NULL,
    PRIMARY KEY(symbol,open_ms))''')
    return con

def fetch(symbol,start,end):
    args=urlencode({'symbol':symbol,'interval':'5m','startTime':start,'endTime':end-1,'limit':1500})
    req=Request('https://fapi.binance.com/fapi/v1/klines?'+args,headers={'User-Agent':'ScalpRadar-Research/0.5'})
    with urlopen(req,timeout=20) as resp: return json.loads(resp.read())

def parse(row):
    t=int(row[0]); end=int(row[6]); o,h,l,c=map(float,row[1:5])
    vol=float(row[5]);q=float(row[7])
    if t%STEP or end!=t+STEP-1 or not all(math.isfinite(x) for x in (o,h,l,c,vol,q)):
        raise ValueError('Invalid candle')
    if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or vol<0 or q<0:
        raise ValueError('Invalid OHLCV')
    return t,end,o,h,l,c,vol,q

def sync(con,symbol,start,end,fetcher=fetch):
    # Closed bars only; do not fill missing candles with fabricated values.
    n=0
    for a in range(start,end,1500*STEP):
        b=min(end,a+1500*STEP)
        rows=fetcher(symbol,a,b)
        valid={r[0]:r for r in (parse(raw) for raw in rows) if a<=r[0]<b}
        with con:
            for r in valid.values():
                prior=con.execute('SELECT o,h,l,c,volume,quote_volume FROM bars WHERE symbol=? AND open_ms=?',(symbol,r[0])).fetchone()
                if prior is not None and tuple(prior)!=r[2:]:
                    raise ValueError('Historical candle conflict at '+str(r[0]))
                n+=con.execute('INSERT OR IGNORE INTO bars VALUES(?,?,?,?,?,?,?,?,?,?)',(symbol,*r,int(time.time()*1000))).rowcount
        time.sleep(.25)
    count=con.execute('SELECT count(*) FROM bars WHERE symbol=? AND open_ms>=? AND open_ms<?',(symbol,start,end)).fetchone()[0]
    expected=(end-start)//STEP
    return {'bars':count,'expected':expected,'gaps':max(0,expected-count),'inserted':n,'coverage_pct':round(count/expected*100,2)}

def events(path,start):
    if not path.exists():return []
    con=sqlite3.connect('file:'+path.resolve().as_posix()+'?mode=ro',uri=True,timeout=10)
    try:
        has=con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='events'").fetchone()
        if not has:return []
        return [x for x in con.execute('SELECT symbol,direction,baseline_time,initial_score FROM events WHERE baseline_time>=?',(start,))
                if x[1] in ('UP','DOWN')]
    finally:con.close()

def replay(con,evts,coverage_start,coverage_end):
    # Explicitly evaluated existing live events; not a whole-market historical strategy backtest.
    trades=[];skipped={}
    def skip(k):skipped[k]=skipped.get(k,0)+1
    for symbol,direction,signal_close,score in sorted(evts,key=lambda x:x[2]):
        # Signal baseline_time is candle CLOSE timestamp, next candle opens +1ms.
        entry_ms=((signal_close+1+STEP-1)//STEP)*STEP
        bars=con.execute('SELECT open_ms,o,h,l,c,close_ms FROM bars WHERE symbol=? AND open_ms>=? ORDER BY open_ms LIMIT 3',(symbol,entry_ms)).fetchall()
        if len(bars)<3 or any(bar[0]!=entry_ms+i*STEP for i,bar in enumerate(bars)):
            skip('MISSING_FUTURE_BARS');continue
        entry=bars[0][1]
        sign=1 if direction=='UP' else -1
        stop=entry*(1-sign*.004);target=entry*(1+sign*.0065)
        reason='TIMEOUT';price=bars[-1][4];exit_ms=bars[-1][5]
        for t,o,h,l,c,closed in bars:
            # For ambiguous candles, stop precedes target.
            if direction=='UP':
                if o<=stop: price=o;reason='STOP_GAP'
                elif l<=stop: price=stop;reason='STOP'
                elif h>=target: price=target;reason='TARGET'
                else:continue
            else:
                if o>=stop: price=o;reason='STOP_GAP'
                elif h>=stop: price=stop;reason='STOP'
                elif l<=target: price=target;reason='TARGET'
                else:continue
            exit_ms=closed;break
        gross=sign*(price/entry-1)*100
        net=gross-.20 # Explicit round-trip assumption, not account-specific fees.
        trades.append({'symbol':symbol,'direction':direction,'score':score,'entry_ms':entry_ms,'exit_ms':exit_ms,
                       'gross_pct':round(gross,6),'net_pct':round(net,6),'reason':reason})
    p=[r['net_pct'] for r in trades];positive=sum(x>0 for x in p)
    gains=sum(x for x in p if x>0);loss=-sum(x for x in p if x<0)
    return {'metrics':{'recorded_signals':len(evts),'trades':len(trades),'skipped':skipped,
            'win_rate_pct':round(positive/len(p)*100,3) if p else None,
            'mean_net_pct':round(sum(p)/len(p),6) if p else None,
            'profit_factor':round(gains/loss,4) if loss else None},
            'trades':trades,'audit':{'source':'RECORDED_LIVE_EVENTS_ONLY',
              'historical_full_strategy_backtest':False,'portfolio_performance_valid':False,
              'round_trip_cost_pct':.20,'note':'No historical signal reconstruction; excludes funding, real fills and latency.'}}

def run_once(fetcher=fetch,now_ms=None,symbols=SYMBOLS):
    now_ms=int(time.time()*1000) if now_ms is None else now_ms
    end=(now_ms//STEP)*STEP;start=end-7*86400000
    update(status='RUNNING',message='Mengunduh histori candle 7 hari...',data={},backtest=None)
    con=connect()
    summaries={};errors=[]
    try:
        for sym in symbols:
            try:summaries[sym]=sync(con,sym,start,end,fetcher)
            except Exception as exc:
                summaries[sym]={'error':str(exc)[:160]};errors.append(sym+': '+str(exc)[:160])
            update(data=dict(summaries),message='Selesai sync '+sym)
        recorded=events(EVENT_DB,start)
        eligible=[e for e in recorded if e[0] in symbols]
        report=replay(con,eligible,start,end)
        report['audit']['events_excluded_other_pairs']=len(recorded)-len(eligible)
        REPORT.parent.mkdir(parents=True,exist_ok=True)
        REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
        state='PARTIAL' if errors else ('READY' if eligible else 'NO_SIGNALS')
        update(status=state,message='Arsip siap; backtest event yang tercatat' if eligible else 'Arsip siap; belum ada event live untuk evaluasi',
               updated_ms=int(time.time()*1000),data=summaries,backtest=report['metrics'],errors=errors)
        return status()
    finally:con.close()

def _loop():
    while True:
        try:run_once()
        except Exception as exc:update(status='ERROR',message=str(exc)[:200],updated_ms=int(time.time()*1000))
        time.sleep(3600)

def start_background():
    global STARTED
    if os.getenv('RESEARCH_AUTO','1')!='1':
        update(status='DISABLED',message='RESEARCH_AUTO=0');return
    with LOCK:
        if STARTED:return
        STARTED=True
    threading.Thread(target=_loop,daemon=True,name='research-engine').start()
