"""Separate, read-only Scalping scanner/runtime with its own event SQLite DB.

The existing Intraday scanner, state machine and database remain untouched.
Do NOT run both market-wide scans at once. The owning app's scheduler selects one.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
import threading,time
from signals import SignalStore

TIMEFRAMES=('1m','3m','5m','15m','1h')
FRESH_1M_MS=110_000
SCAN_REFRESH_MS=60_000
BATCH_SIZE=12
BATCH_INTERVAL=7.0
WORKERS=4

class ScalpRuntime:
    def __init__(self,db_path,active_tickers,scan_symbol,latest_quotes,promotion_candidates,settings):
        self.store=SignalStore(db_path,bar_time_key='lastClosed1m')
        self.active_tickers=active_tickers
        self.scan_symbol=scan_symbol
        self.latest_quotes=latest_quotes
        self.promotion_candidates=promotion_candidates
        self.settings=settings
        self.lock=threading.RLock()
        self.settings_snapshot=settings()
        self.state={
            'running':False,'rows':[],'processed':0,'total':0,'eligible':0,
            'universe':0,'missingTicker':0,'trackedExtra':0,'errors':[],
            'startedAt':None,'completedAt':None,'mode':'top80',
            'minTurnover':30_000_000,'requestedMode':'top80','requestedMinTurnover':30_000_000,
            'generation':0,'settingsRevision':-1,'message':'Belum dipindai',
        }

    def _same_generation(self,generation):
        with self.lock:return generation==self.state['generation']

    def scan_job(self,generation,mode,min_turnover):
        store=self.store
        try:
            tracked=store.active_symbols()
            tickers,info=self.active_tickers(mode,min_turnover,tracked)
            with self.lock:
                if generation!=self.state['generation']:return
                self.state['total']=len(tickers)
                self.state.update(info)
                self.state['message']='Scalping: memindai candle 1m/3m/5m/15m/1H'
            if not tickers:raise RuntimeError('Tidak ada pair sesuai mode.')
            stop_for_limit=False
            eligible_rows=[]
            recent={}
            with ThreadPoolExecutor(max_workers=WORKERS) as pool:
                for offset in range(0,len(tickers),BATCH_SIZE):
                    if not self._same_generation(generation):return
                    started=time.monotonic()
                    batch=tickers[offset:offset+BATCH_SIZE]
                    futures={pool.submit(self.scan_symbol,t,t['symbol'] in tracked,self.settings_snapshot):t['symbol']
                             for t in batch}
                    for fut in as_completed(futures):
                        if not self._same_generation(generation):return
                        sym=futures[fut]
                        try:
                            result=fut.result()
                            bars=result.pop('_recent1m')
                            recent[sym]=bars
                            result=store.refresh(result,bars,allow_new=False)
                            if result.get('potentialUp') or result.get('potentialDown'):
                                eligible_rows.append(result)
                            err=None
                        except Exception as exc:
                            result=None
                            err=f'{sym}: {str(exc)[:160]}'
                            if any(s in str(exc).lower() for s in ('http 429','http 418','rate limit')):
                                stop_for_limit=True
                        with self.lock:
                            if generation!=self.state['generation']:return
                            self.state['processed']+=1
                            if result:self.state['rows'].append(result)
                            if err:self.state['errors'].append(err)
                    if stop_for_limit:
                        with self.lock:
                            self.state['errors'].append('Rate limit Binance; scanning scalping dihentikan.')
                        break
                    try:
                        quotes=self.latest_quotes({r['symbol'] for r in eligible_rows})
                        options=self.promotion_candidates(eligible_rows,
                            quote_prices=quotes,bar_time_key='lastClosed1m',
                            fresh_candle_ms=FRESH_1M_MS,
                            max_chase_pct=self.settings_snapshot['values']['max_chase_pct'])
                        for score,turnover,direction,candidate in options:
                            sym=candidate['symbol']
                            if not self._same_generation(generation):return
                            if sym in recent and store.activate_top_candidate(candidate,recent[sym],direction):
                                with self.lock:
                                    for i,old in enumerate(self.state['rows']):
                                        if old['symbol']==sym:
                                            latest=next((r for r in store.latest_rows() if r['symbol']==sym),None)
                                            if latest:self.state['rows'][i]=latest
                                            break
                    except Exception as exc:
                        with self.lock:self.state['errors'].append('Ranking scalping: '+str(exc)[:120])
                    if offset+BATCH_SIZE<len(tickers):
                        remaining=BATCH_INTERVAL-(time.monotonic()-started)
                        if remaining>0:time.sleep(remaining)
        except Exception as exc:
            with self.lock:
                if generation==self.state['generation']:
                    self.state['errors'].append('Scanner scalp: '+str(exc)[:160])
        finally:
            with self.lock:
                if generation==self.state['generation']:
                    self.state['running']=False
                    self.state['completedAt']=int(time.time()*1000)
                    stopped=self.state['processed']<self.state['total']
                    self.state['message']=('Scalp scan berhenti sebelum selesai' if stopped
                        else 'Scalp scan selesai' if self.state['rows']
                        else 'Belum ada data 1m yang berhasil dipindai')

    def read(self,mode='top80',min_turnover=30_000_000,force=False):
        if mode not in ('all','liquid','top80'):raise ValueError('Mode tidak dikenal')
        if min_turnover not in (10_000_000,30_000_000,100_000_000):
            raise ValueError('Turnover minimum tidak valid.')
        now=int(time.time()*1000)
        current=self.settings()
        with self.lock:
            s=self.state
            s['requestedMode']=mode
            s['requestedMinTurnover']=min_turnover
            new_filters=(mode,min_turnover if mode=='liquid' else None)!=(s['mode'],s['minTurnover'] if s['mode']=='liquid' else None)
            changed=s.get('settingsRevision')!=current['revision']
            age=now-(s['completedAt'] or 0)
            start_age=now-(s['startedAt'] or 0)
            restart=not s['running'] and (
                s['completedAt'] is None or new_filters or changed or age>=SCAN_REFRESH_MS
                or (force and start_age>=30_000))
            if restart:
                self.settings_snapshot=current
                s.update({'running':True,'rows':[],'processed':0,'total':0,
                    'eligible':0,'universe':0,'missingTicker':0,'trackedExtra':0,
                    'errors':[],'startedAt':now,'completedAt':None,
                    'mode':mode,'minTurnover':min_turnover,
                    'settingsRevision':current['revision'],
                    'generation':s['generation']+1,
                    'message':'Mengambil daftar pair untuk Scalping'})
                threading.Thread(target=self.scan_job,args=(s['generation'],mode,min_turnover),
                                 daemon=True,name='scalp-scan').start()
            fresh=list(s['rows'])
            persisted=self.store.latest_rows()
            ranked=sorted(persisted,key=lambda r:-(r.get('turnover24h') or 0))
            if mode=='liquid':ranked=[r for r in ranked if (r.get('turnover24h') or 0)>=min_turnover or r.get('categories')]
            elif mode=='top80':
                kept={r['symbol'] for r in ranked[:80]}
                ranked=[r for r in ranked if r['symbol'] in kept or r.get('categories')]
            by_symbol={r['symbol']:r for r in ranked}
            combined=[]
            for row in fresh:
                cached=by_symbol.pop(row['symbol'],None)
                combined.append(cached if cached and (cached.get('quoteAt') or 0)>(row.get('quoteAt') or 0) else row)
            combined.extend(dict(row,stale=True) for row in by_symbol.values())
            active=self.store.active_pending(now)
            return {
                'strategy':'scalping','timeframes':list(TIMEFRAMES),
                'running':s['running'],'rows':combined,
                'activeSignals':len(active),'activeLimit':5,'signals':active,
                'processed':s['processed'],'total':s['total'],'successful':len(fresh),
                'failed':s['processed']-len(fresh),'eligible':s['eligible'],
                'universe':s['universe'],'missingTicker':s['missingTicker'],
                'trackedExtra':s['trackedExtra'],'errors':s['errors'][:10],
                'errorCount':len(s['errors']),'startedAt':s['startedAt'],
                'completedAt':s['completedAt'],'mode':s['mode'],
                'requestedMode':mode,'configPending':s['running'] and new_filters,
                'minTurnover':s['minTurnover'],'requestedMinTurnover':min_turnover,
                'message':s['message'],'source':'Binance USD-M Futures public REST',
                'categories':['POTENSI_NAIK','SUDAH_NAIK','POTENSI_TURUN','SUDAH_TURUN','NETRAL'],
                'tracking':'Scalp SQLite: event outcome uses CLOSED 1m candles',
                'scoring':'Heuristic 0-100; NOT a verified profit probability',
                'settingsRevision':s.get('settingsRevision',-1),
                'settingsPending':s.get('settingsRevision')!=current['revision'] and s['running'],
            }
