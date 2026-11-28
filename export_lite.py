"""Compact cumulative analysis export, read-only, no full SQLite copy."""
import argparse,csv,io,json,os,sqlite3,sys,tempfile,time,traceback,zipfile
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path
from database_location import existing_database,configured
ROOT=Path(__file__).resolve().parent
MAX_ZIP=9*1024*1024
QUERY_SECONDS=8
SUMMARY_SECONDS=75
DETAIL_SECONDS=25

def progress(message):print(message,flush=True)

@contextmanager
def query_budget(db,deadline,seconds=QUERY_SECONDS):
    # Each query and phase is bounded in routine mode; complete mode passes None.
    if deadline is None:
        yield;return
    end=min(deadline,time.monotonic()+seconds)
    if time.monotonic()>=end:raise sqlite3.OperationalError('export time budget reached')
    db.set_progress_handler(lambda:int(time.monotonic()>=end),10000)
    try:yield
    finally:db.set_progress_handler(None,0)

STEPS={'kline_1m':60000,'kline_5m':300000,'kline_15m':900000,'kline_1h':3600000,'kline_4h':14400000}
def rows(db,sql,args=()):
    return [dict(r) for r in db.execute(sql,args)]
def continuity(db,now,deadline=None,unavailable=None):
    """Observed history span and recent gaps, not proof of listing dates."""
    result=[]
    day=now-86400000
    for kind,step in STEPS.items():
        last=now//step*step-1
        try:
            with query_budget(db,deadline):
                data=rows(db,"""SELECT symbol,COUNT(*) n,MIN(source_ts) first,MAX(source_ts) latest,
                  SUM(CASE WHEN source_ts>=? THEN 1 ELSE 0 END) recent,
                  SUM(CASE WHEN (source_ts+1)%?!=0 THEN 1 ELSE 0 END) offGrid
                  FROM market_observations WHERE kind=? AND source_ts<=? AND received_at<=? GROUP BY symbol""",
                  (day,step,kind,last,now))
        except sqlite3.OperationalError as exc:
            if unavailable is None:raise
            unavailable['continuity_'+kind]=str(exc);continue
        for r in data:
            first,latest=r['first'],r['latest']
            # Only observed-span denominator; never assume continuous listing before first observation.
            expected=(latest-first)//step+1 if not r['offGrid'] else None
            recent_start=max(first,((day+1+step-1)//step)*step-1)
            expected_recent=max(0,(last-recent_start)//step+1) if not r['offGrid'] else None
            r.update(kind=kind,intervalMs=step,expectedWithinSpan=expected,
                     missingWithinSpan=expected-r['n'] if expected is not None else None,
                     expectedRecent=expected_recent,
                     missingRecent=expected_recent-r['recent'] if expected_recent is not None else None,
                     lagMs=last-latest)
            result.append(r)
    return result

def daily_continuity(db,now,deadline=None,unavailable=None):
    """24h-only coverage; full-window expectation assumes coin active throughout."""
    day=now-86400000;result=[];universe=set()
    try:
        with query_budget(db,deadline):
            row=db.execute("SELECT reasons FROM r111_cycles WHERE cutoff<=? ORDER BY cutoff DESC LIMIT 1",(now,)).fetchone()
        if row:universe={s for group in json.loads(row[0]).values() for s in group}
    except (sqlite3.OperationalError,ValueError,TypeError) as exc:
        if unavailable is not None:unavailable['daily_current_universe']=str(exc)
    for kind,step in STEPS.items():
        last=now//step*step-1;start=((day+1+step-1)//step)*step-1
        try:
            with query_budget(db,deadline):
                data=rows(db,"SELECT symbol,COUNT(*) n,MIN(source_ts) first,MAX(source_ts) latest,SUM((source_ts+1)%?!=0) offGrid FROM market_observations WHERE kind=? AND source_ts BETWEEN ? AND ? AND received_at<=? GROUP BY symbol",(step,kind,start,last,now))
        except sqlite3.OperationalError as exc:
            if unavailable is None:raise
            unavailable['continuity_'+kind]=str(exc);continue
        seen={r['symbol']:r for r in data}
        for symbol in sorted(universe|set(seen)):
            r=seen.get(symbol,{'symbol':symbol,'n':0,'first':None,'latest':None,'offGrid':0})
            expected=(last-start)//step+1 if not r['offGrid'] else None
            r.update(kind=kind,intervalMs=step,recent=r['n'],expectedRecentAssumingActive=expected,
                     missingRecentAssumingActive=expected-r['n'] if expected is not None else None,
                     lagMs=last-r['latest'] if r['latest'] is not None else None)
            result.append(r)
    return result

def collect(db,now,deadline=None,notify=lambda message:None,daily_only=False):
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    out={'schema':'scalp-radar-lite-v1','exportedAtMs':now,'counts':{},'sections':{},'unavailable':{},
         'note':'Cumulative and last 24h summaries; overlapping events, assumed costs in percentage points, no real fills. Missing returns are not zero.'}
    pending=[]
    def q(name,required,sql,args=()):
        if daily_only and (name.endswith('_all') or name in ('archive_coverage','dashboard_status')):return
        if not set(required)<=tables:
            out['unavailable'][name]='missing tables: '+','.join(sorted(set(required)-tables));return
        pending.append((name,sql,args))
    day=now-86400000
    q('archive_coverage',['market_observations'],"SELECT kind,COUNT(*) n,COUNT(DISTINCT symbol) pairs,MIN(source_ts) first,MAX(source_ts) latest,MAX(received_at) received FROM market_observations GROUP BY kind")
    q('archive_runs',['market_collection_runs'],"SELECT * FROM market_collection_runs ORDER BY id DESC LIMIT 48")
    q('archive_errors',['market_collection_errors'],"SELECT symbol,kind,at,message FROM market_collection_errors ORDER BY id DESC LIMIT 100")
    q('dashboard_status',['events'],"SELECT status,end_reason,COUNT(*) n FROM events GROUP BY 1,2")
    q('r10_meta',['r10_meta'],"SELECT * FROM r10_meta")
    for label,where,args in [('all','',()),('24h',' WHERE cutoff>=?',(day,))]:
        q('r10_coverage_'+label,['r10_cycles'],"SELECT regime,COUNT(*) cycles,AVG(1.0*observed/NULLIF(universe,0)) observed,AVG(1.0*fresh/NULLIF(universe,0)) fresh,AVG(1.0*atr_ready/NULLIF(universe,0)) atrReady,AVG((decision-cutoff)/1000.0) lagSec FROM r10_cycles"+where+" GROUP BY 1",args)
        q('r111_moves_'+label,['r111_moves'],"SELECT direction,v1_class,v2_class,COUNT(*) n,AVG(v1_lead_ms) v1LeadMs,AVG(v2_lead_ms) v2LeadMs FROM r111_moves"+where+" GROUP BY 1,2,3",args)
        q('r111_drop_reasons_'+label,['r111_cycles'],"SELECT j.key reason,COUNT(*) cycles,SUM(json_array_length(j.value)) symbolCycles FROM r111_cycles c,json_each(c.reasons) j"+where+" GROUP BY 1",args)
        q('r111_regime_'+label,['r111_cycles'],"SELECT json_extract(regime,'$.regime') regime,json_extract(regime,'$.nativeContext.regime') nativeRegime,COUNT(*) cycles,AVG(json_extract(regime,'$.coverage')) coverage FROM r111_cycles"+where+" GROUP BY 1,2",args)
        for pre in ('r11','r111'):
            q(pre+'_coverage_'+label,[pre+'_cycles'],f"SELECT COUNT(*) cycles,AVG(1.0*eligible/NULLIF(universe,0)) eligibleShare,MIN(cutoff) first,MAX(cutoff) latest FROM {pre}_cycles"+where,args)
    for label,where,args in [('all','',()),('24h',' WHERE s.decision>=?',(day,))]:
        q('r10_outcomes_'+label,['r10_setups','r10_outcomes'],
          "SELECT s.source,s.direction,s.regime,o.horizon,o.policy,COUNT(*) n,COUNT(o.gross_pct) observed,SUM(o.state='UNOBSERVED') unobserved,SUM(o.state='TARGET') targets,SUM(o.state='STOP') stops,AVG(o.gross_pct) gross,AVG(o.gross_pct)-.10 net010,AVG(o.gross_pct)-.20 net020,AVG(o.gross_pct)-.35 net035 FROM r10_setups s JOIN r10_outcomes o ON o.setup_id=s.id"+where+" GROUP BY 1,2,3,4,5",args)
        q('r10_rules_'+label,['r10_setups','r10_outcomes','r10_meta'],
          "SELECT json_extract(t.value,'$.id') filter_id,json_extract(t.value,'$.version') version,s.source,s.direction,s.regime,CASE WHEN s.decision<(SELECT value FROM r10_meta WHERE key='holdout_start') THEN 'DEVELOPMENT' ELSE 'HOLDOUT' END period,o.horizon,o.policy,COUNT(*) n,COUNT(o.gross_pct) observed,COUNT(DISTINCT CASE WHEN o.gross_pct IS NOT NULL THEN s.symbol END) coins,SUM(o.state='UNOBSERVED') unobserved,AVG(o.gross_pct) gross,AVG(o.gross_pct)-.20 net020 FROM r10_setups s JOIN r10_outcomes o ON o.setup_id=s.id,json_each(s.tags) t"+where+" GROUP BY 1,2,3,4,5,6,7,8",args)
    for pre in ('research','ws'):
        confirm=',o.confirm' if pre=='research' else ''
        for label,where,args in [('all','',()),('24h',' WHERE c.candle_time>=?',(day,))]:
            q(pre+'_rules_'+label,[pre+'_candidates',pre+'_outcomes'],
              f"SELECT c.filter_id,c.version,c.direction,o.horizon{confirm},COUNT(*) n,SUM(o.state='TARGET') targets,SUM(o.state='STOP') stops,SUM(o.state='TIMEOUT') timeouts,SUM(o.state='UNOBSERVED') unobserved,AVG(CASE o.state WHEN 'TARGET' THEN c.target-.20 WHEN 'STOP' THEN -c.stop-.20 WHEN 'TIMEOUT' THEN o.endpoint_pct-.20 END) net020,AVG((c.observed_at-c.candle_time)/1000.0) lagSec FROM {pre}_candidates c JOIN {pre}_outcomes o ON c.id=o.candidate_id"+where+" GROUP BY 1,2,3,4"+(',5' if confirm else ''),args)
    for pre in ('r11','r111'):
        for label,where,args in [('all','',()),('24h',' WHERE r.decision>=?',(day,))]:
            q(pre+'_outcomes_'+label,[pre+'_ready',pre+'_outcomes',pre+'_events'],
              f"SELECT json_extract(e.payload,'$.setup') setup,json_extract(e.payload,'$.features.entryVariant') variant,r.direction,COUNT(*) ready,COUNT(o.state) settled,SUM(o.state='UNOBSERVED') unobserved,SUM(o.state='TARGET') targets,SUM(o.state='STOP') stops,AVG(o.gross_pct) gross,AVG(o.gross_pct)-.10 net010,AVG(o.gross_pct)-.20 net020,AVG(o.gross_pct)-.35 net035,AVG(o.mfe) mfe,AVG(o.mae) mae,AVG(json_extract(e.payload,'$.prepareLeadMs')) leadMs,AVG((r.decision-r.cutoff)/1000.0) lagSec FROM {pre}_ready r LEFT JOIN {pre}_outcomes o USING(symbol,cutoff) LEFT JOIN {pre}_events e ON e.symbol=r.symbol AND e.cutoff=r.cutoff AND e.state='READY'"+where+" GROUP BY 1,2,3",args)
            q(pre+'_reasons_'+label,[pre+'_events'],f"SELECT state,json_extract(payload,'$.reason') reason,COUNT(*) n FROM {pre}_events"+(' WHERE decision>=?' if label=='24h' else '')+" GROUP BY 1,2",args)
            q(pre+'_coin_'+label,[pre+'_ready',pre+'_outcomes'],f"SELECT r.symbol,r.direction,COUNT(*) ready,COUNT(o.gross_pct) observed,AVG(o.gross_pct) gross,AVG(o.gross_pct)-.20 net020 FROM {pre}_ready r LEFT JOIN {pre}_outcomes o USING(symbol,cutoff)"+where+" GROUP BY 1,2",args)
    for label,where,args in [('all','',()),('24h',' WHERE e.decision>=?',(day,))]:
        q('r112_outcomes_'+label,['r112_entries','r112_outcomes'],"SELECT e.cohort,e.direction,o.horizon,o.policy,COUNT(*) n,COUNT(o.gross_pct) observed,SUM(o.state='UNOBSERVED') unobserved,AVG(o.gross_pct) gross,AVG(o.gross_pct)-.10 net010,AVG(o.gross_pct)-.20 net020,AVG(o.gross_pct)-.35 net035,AVG(o.mfe) mfe,AVG(o.mae) mae FROM r112_entries e JOIN r112_outcomes o USING(symbol,cutoff,cohort)"+where+" GROUP BY 1,2,3,4",args)
    q('ws_coin_24h',['ws_minute_snapshots'],"SELECT symbol,COUNT(*) n,MIN(candle_time) first,MAX(candle_time) latest,AVG(observed_at-candle_time) lagMs,SUM(json_extract(payload,'$.micro.coverage.trades')=1) tradeCovered,SUM(json_extract(payload,'$.micro.coverage.depth')=1) depthCovered FROM ws_minute_snapshots WHERE candle_time>=? GROUP BY symbol",(day,))
    # Daily all-coin denominators, not capped event samples.
    q('daily_scan_cycles',['scan_live_cycles'],"SELECT COUNT(*) cycles,MIN(started_at) first,MAX(finished_at) latest,AVG(finished_at-started_at) meanDurationMs,MAX(finished_at-started_at) maxDurationMs,SUM(processed) processed,SUM(successful) successful,SUM(cache_skipped) cacheSkipped,SUM(failed) failed,MAX(json_extract(payload,'$.cpuWorkers')) cpuWorkers,AVG(json_extract(payload,'$.cpuCalcMs')) meanCpuCalcMs,AVG(json_extract(payload,'$.cpuElapsedMs')) meanCpuElapsedMs,SUM(json_extract(payload,'$.cpuFallbacks')) cpuFallbacks FROM scan_live_cycles WHERE started_at>=? AND started_at<=?",(day,now))
    q('daily_research_queue',['scan_research_queue'],"SELECT COUNT(*) pending,MIN(observed_at) oldest,MAX(observed_at) newest FROM scan_research_queue")
    q('daily_coin_r111_reasons',['r111_cycles'],"SELECT s.value symbol,j.key reason,COUNT(*) n FROM r111_cycles c,json_each(c.reasons) j,json_each(j.value) s WHERE c.cutoff>=? AND c.cutoff<=? GROUP BY 1,2",(day,now))
    q('daily_coin_r111_eligible',['r111_cycles'],"SELECT s.value symbol,COUNT(*) n FROM r111_cycles c,json_each(c.eligible_symbols) s WHERE c.cutoff>=? AND c.cutoff<=? GROUP BY 1",(day,now))
    q('daily_coin_movement',['r111_moves'],"SELECT symbol,direction,v1_class,v2_class,COUNT(*) n,MAX(ABS(ret15)) maxAbsRet15,AVG(v2_lead_ms) leadMs FROM r111_moves WHERE cutoff>=? AND cutoff<=? GROUP BY 1,2,3,4",(day,now))
    q('daily_coin_r08',['research_snapshots'],"SELECT symbol,COUNT(*) n,MAX(recorded_at-candle_time) maxLagMs,AVG(recorded_at-candle_time) avgLagMs,SUM(json_extract(payload,'$.potentialUp')=1) up,SUM(json_extract(payload,'$.potentialDown')=1) down,MAX(json_extract(payload,'$.longScore')) maxLong,MAX(json_extract(payload,'$.shortScore')) maxShort,COUNT(json_extract(payload,'$.researchFeatures.extraIndicators.5m.adx14')) extraCovered FROM research_snapshots WHERE candle_time>=? AND candle_time<=? GROUP BY 1",(day,now))
    q('daily_coin_dashboard',['events'],"SELECT symbol,direction,status,end_reason,COUNT(*) n FROM events WHERE started_at>=? AND started_at<=? GROUP BY 1,2,3,4",(day,now))
    q('daily_coin_r112',['r112_entries','r112_outcomes'],"SELECT e.symbol,e.cohort,e.direction,COUNT(*) n,COUNT(o.gross_pct) observed,AVG(o.gross_pct) gross,AVG(o.gross_pct)-.20 net020 FROM r112_entries e JOIN r112_outcomes o USING(symbol,cutoff,cohort) WHERE e.decision>=? AND e.decision<=? AND o.horizon=15 AND o.policy='FIXED' GROUP BY 1,2,3",(day,now))
    # Recent R11.1/R11 sections first, then operational coverage and other recent
    # results; expensive historical rule expansion is lower priority.
    def priority(item):
        name=item[0]
        if name.startswith('daily_') or name=='ws_coin_24h':return -1
        if name.startswith(('r112_','r111_')) and name.endswith('_24h'):return 0
        if name.startswith('r11_') and name.endswith('_24h'):return 1
        if name.startswith(('archive_runs','archive_errors','r10_meta','dashboard_status')):return 2
        if name.endswith('_24h'):return 3
        if name.startswith(('r112_','r111_','r11_')):return 4
        if name=='archive_coverage':return 5
        return 6
    for i,(name,sql,args) in enumerate(sorted(pending,key=priority),1):
        notify('Summary %d/%d: %s'%(i,len(pending),name))
        try:
            with query_budget(db,deadline):out['sections'][name]=rows(db,sql,args)
        except sqlite3.OperationalError as e:out['unavailable'][name]=str(e)
    for t in sorted(tables) if not daily_only else ():
        if t.startswith(('r10_','r11_','r111_','r112_','ws_','research_','market_')) or t in ('events','last_rows','scan_research_queue','scan_live_cycles'):
            try:
                with query_budget(db,deadline):
                    out['counts'][t]=db.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0]
            except sqlite3.OperationalError as e:out['unavailable']['count:'+t]=str(e)
    out['dailyWindow']={'fromMs':day,'toMs':now,'kind':'rolling_24h','completeSections':[k for k in out['sections'] if k.startswith('daily_')],'missingSections':{k:v for k,v in out['unavailable'].items() if k.startswith('daily_')}}
    return out,tables

def json_write(z,name,value):
    z.writestr(name,json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False))
def csv_query(db,sql,args=()):
    cur=db.execute(sql,args);buf=io.StringIO(newline='');w=csv.writer(buf)
    w.writerow([x[0] for x in cur.description]);w.writerows(cur)
    return buf.getvalue().encode('utf-8')
def csv_dict(data):
    if not data:return b''
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    return buf.getvalue().encode('utf-8')

def export(source,dest,coin=None,hours=24,now=None,complete=False,notify=lambda message:None,daily_only=False):
    source=Path(source).resolve();dest=Path(dest).resolve()
    if source==dest or dest.exists():raise RuntimeError('Destination exists or equals database')
    now=int(time.time()*1000) if now is None else now
    if not 1<=hours<=168:raise ValueError('hours must be 1–168')
    dest.parent.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=10);db.row_factory=sqlite3.Row
    tmp=None
    try:
        fd,name=tempfile.mkstemp(prefix='lite-',suffix='.tmp',dir=dest.parent)
        os.close(fd);tmp=Path(name)
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        # Reserve a separate continuity budget so heavy rule history cannot starve it.
        summary,tables=collect(db,now,None if complete else time.monotonic()+SUMMARY_SECONDS,notify,daily_only=daily_only)
        summary['databaseBytes']=source.stat().st_size
        summary['mode']='daily' if daily_only else 'complete' if complete else 'routine'
        summary['queryBudgetsEnabled']=not complete
        notify('Checking coin continuity...')
        coverage_fn=daily_continuity if daily_only else continuity
        cont=coverage_fn(db,now,None if complete else time.monotonic()+25,summary['unavailable']) if 'market_observations' in tables else []
        if 'market_observations' not in tables:summary['unavailable']['continuity']='missing market_observations'
        detail_deadline=None if complete else time.monotonic()+DETAIL_SECONDS
        optional_errors={}
        def optional(name,fn):
            try:
                with query_budget(db,detail_deadline):return fn()
            except (sqlite3.OperationalError,OSError,ValueError) as exc:
                optional_errors[name]=str(exc);return None
        specs=[('scan_live_cycles',288),('r111_cycles',360),('r11_cycles',360),('r10_cycles',720),('r111_moves',2000),
               ('r111_events',1500),('r11_events',1000),('r111_ready',1500),('r111_outcomes',1500),('r11_ready',1000),('r11_outcomes',1000)]
        def write(scale):
            manifest={'schema':summary['schema'],'snapshotMs':now,'detailLimits':{},'coin':coin,'hours':hours if coin else None,
                'note':'Not a restorable backup. Per-coin continuity is computed from all stored aligned candle timestamps, not the raw sample. Recent window ends at the last expected closed candle. Unknown listing dates/delisting can affect missing counts. Raw optional details are not representative.'}
            manifest['omittedDetails']={}
            if daily_only:manifest['note']='Rolling 24h exact aggregate queries over recorded data, not full raw replay. Candle expectation assumes each coin active throughout; listing changes may alter denominator. Older cumulative queries intentionally omitted. Optional raw samples remain capped.'
            with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                json_write(z,'summary.json',summary);z.writestr('coin_continuity.csv',csv_dict(cont))
                # Explicit coin diagnostics: don't let global newest-event sampling hide the requested symbol.
                if coin:
                    start=now-hours*3600000
                    targets=[('research_snapshots','candle_time'),('research_candidates','candle_time'),
                             ('events','started_at'),('ws_minute_snapshots','candle_time'),
                             ('r11_events','cutoff'),('r111_events','cutoff'),('r112_events','cutoff')]
                    for table,clock in targets:
                        name='coin_'+table
                        if table not in tables:
                            optional_errors[name]='table unavailable'
                            continue
                        # Keep targeted records across ZIP scales; explicit omission on query error.
                        sql=f'SELECT * FROM {table} WHERE symbol=? AND {clock} BETWEEN ? AND ? ORDER BY {clock}'
                        try:
                            with query_budget(db,None if complete else time.monotonic()+8):
                                data=csv_query(db,sql,(coin,start,now))
                        except (sqlite3.OperationalError,OSError,ValueError) as exc:
                            optional_errors[name]=str(exc);data=None
                        if data is not None:z.writestr(name+'.csv',data)
                    manifest['coinDiagnostics']={'symbol':coin,'fromMs':start,'toMs':now,'note':'Targeted recorded rows only, not proof of all promotion rejections; missing tables/errors in omittedDetails.'}
                for table,n in specs:
                    if table not in tables or int(n*scale)<=0:continue
                    limit=int(n*scale)
                    order='started_at DESC' if table=='scan_live_cycles' else 'cutoff DESC' if table.endswith('_cycles') else 'cutoff DESC,symbol'
                    data=optional(table,lambda:csv_query(db,f'SELECT * FROM {table} ORDER BY {order} LIMIT ?',(limit,)))
                    if data is not None:
                        z.writestr(table+'.csv',data);manifest['detailLimits'][table]=limit
                # Joined settled feature/outcome records, not independently capped newest events.
                for pre in ('r11','r111'):
                    if scale and {pre+'_ready',pre+'_events',pre+'_outcomes'}<=tables:
                        sql=f"SELECT r.symbol,r.cutoff,r.decision,r.direction,e.payload,o.state,o.gross_pct,o.mfe,o.mae FROM {pre}_ready r JOIN {pre}_outcomes o USING(symbol,cutoff) JOIN {pre}_events e ON e.symbol=r.symbol AND e.cutoff=r.cutoff AND e.state='READY' ORDER BY r.cutoff DESC,r.symbol LIMIT ?"
                        data=optional(pre+'_joined',lambda:csv_query(db,sql,(int(600*scale),)))
                        if data is not None:z.writestr(pre+'_joined.csv',data)
                if scale and {'r112_entries','r112_outcomes'}<=tables:
                    data=optional('r112_joined',lambda:csv_query(db,"SELECT e.symbol,e.cutoff,e.cohort,e.direction,e.decision,e.payload,o.horizon,o.policy,o.state,o.gross_pct,o.mfe,o.mae FROM r112_entries e JOIN r112_outcomes o USING(symbol,cutoff,cohort) WHERE o.horizon=15 ORDER BY e.cutoff DESC,e.symbol,e.cohort,o.policy LIMIT ?",(int(1000*scale),)))
                    if data is not None:z.writestr('r112_joined.csv',data)
                if 'market_observations' in tables:
                    symbols=[coin] if coin else ['BTCUSDT']
                    if not coin and scale:
                        for table in ('r111_moves','r111_ready','r11_ready'):
                            if table in tables:
                                extra=optional(table+'_symbols',lambda:list(db.execute(f'SELECT symbol FROM {table} ORDER BY cutoff DESC LIMIT 100')))
                                if extra:symbols.extend(r[0] for r in extra)
                        symbols=list(dict.fromkeys(symbols))[:max(1,int(20*scale))]
                    if coin or scale:
                        start=now-(hours*3600000 if coin else 7200000)
                        mark=','.join('?' for _ in symbols)
                        kinds=tuple(STEPS);km=','.join('?' for _ in kinds)
                        query=f"SELECT kind,symbol,source_ts,received_at,payload FROM market_observations WHERE kind IN ({km}) AND symbol IN ({mark}) AND source_ts BETWEEN ? AND ? AND received_at<=? ORDER BY symbol,kind,source_ts"
                        args=(*kinds,*symbols,start,now,now)
                        # Explicitly requested coin data is required, not silently dropped.
                        data=csv_query(db,query,args) if coin else optional('sample_candles',lambda:csv_query(db,query,args))
                        if data is not None:
                            z.writestr('sample_candles.csv',data)
                            manifest['rawSample']={'symbols':symbols,'fromMs':start,'toMs':now}
                for name in ('r10-heartbeat.json','r10-runtime.jsonl'):
                    p=source.parent/name;limit=int(128*1024*scale)
                    if p.is_file() and limit:
                        try:
                            with p.open('rb') as f:
                                f.seek(max(0,p.stat().st_size-limit))
                                if f.tell():f.readline()
                                data=f.read(limit)
                            if data:z.writestr(name,data)
                        except OSError as exc:optional_errors[name]=str(exc)
                manifest['omittedDetails']=dict(optional_errors)
                manifest['sampleScale']=scale
                json_write(z,'manifest.json',manifest)
        for scale in (1,.5,.25,0):
            notify('Writing ZIP (sample scale %s)...'%scale)
            write(scale)
            if tmp.stat().st_size<=MAX_ZIP:break
        else:raise RuntimeError('Required summary or requested coin data exceeds 9 MiB; reduce --hours for coin export.')
        with zipfile.ZipFile(tmp) as z:
            if z.testzip() is not None:raise RuntimeError('ZIP integrity check failed')
        # No overwrite: a concurrent exporter may have selected the same destination.
        if os.name=='nt':tmp.rename(dest)
        else:os.link(tmp,dest)
    finally:
        db.close()
        if tmp is not None and tmp.exists():tmp.unlink()
    return dest

def main():
    p=argparse.ArgumentParser();p.add_argument('--database');p.add_argument('--output');p.add_argument('--coin');p.add_argument('--hours',type=int,default=24);p.add_argument('--complete',action='store_true',help='No SQL time budget; may take longer');p.add_argument('--daily',action='store_true',help='Rolling 24h report; skip cumulative queries');p.add_argument('--open-folder',action='store_true');a=p.parse_args()
    source=Path(a.database).resolve() if a.database else existing_database(ROOT)
    out=source.parent.parent/'exports' if a.database or configured() is not None else ROOT/'exports'
    out.mkdir(parents=True,exist_ok=True)
    dest=(Path(a.output) if a.output else out/('scalp-radar-LITE-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip')).resolve()
    progress('Database: '+str(source))
    progress('Output: '+str(dest))
    progress('Creating compact analysis report...')
    export(source,dest,a.coin.upper() if a.coin else None,a.hours,complete=a.complete,notify=progress,daily_only=a.daily)
    with zipfile.ZipFile(dest) as z:
        summary=json.loads(z.read('summary.json'))
        manifest=json.loads(z.read('manifest.json'))
    progress('LITE EXPORT OK: '+str(dest))
    progress('Size: %.2f MiB'%(dest.stat().st_size/1024/1024))
    if summary['unavailable'] or manifest['omittedDetails']:
        progress('Some sections unavailable or timed out; see summary.json and manifest.json. Use --complete for unbounded SQL queries.')
    progress('Upload this ZIP; full database stays local.')
    if a.open_folder and os.name=='nt':
        try:os.startfile(str(dest.parent))
        except OSError as exc:progress('Cannot open Explorer: '+str(exc))
if __name__=='__main__':
    try:main()
    except Exception:
        detail=traceback.format_exc()
        print('LITE EXPORT FAILED:\n'+detail,file=sys.stderr,flush=True)
        try:
            log=Path(tempfile.gettempdir())/'ScalpRadar-lite-error.log'
            log.write_text(detail,encoding='utf-8')
            progress('Error log: '+str(log))
        except OSError:pass
        sys.exit(1)
