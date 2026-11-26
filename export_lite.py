"""Compact cumulative analysis export, read-only, no full SQLite copy."""
import argparse,csv,io,json,sqlite3,time,zipfile
from datetime import datetime
from pathlib import Path
from database_location import existing_database,configured
ROOT=Path(__file__).resolve().parent
MAX_ZIP=9*1024*1024
STEPS={'kline_1m':60000,'kline_5m':300000,'kline_15m':900000,'kline_1h':3600000,'kline_4h':14400000}
def rows(db,sql,args=()):
    return [dict(r) for r in db.execute(sql,args)]
def continuity(db,now):
    """Observed history span and recent gaps, not proof of listing dates."""
    result=[]
    day=now-86400000
    for kind,step in STEPS.items():
        last=now//step*step-1
        data=rows(db,"""SELECT symbol,COUNT(*) n,MIN(source_ts) first,MAX(source_ts) latest,
          SUM(CASE WHEN source_ts>=? THEN 1 ELSE 0 END) recent,
          SUM(CASE WHEN (source_ts+1)%?!=0 THEN 1 ELSE 0 END) offGrid
          FROM market_observations WHERE kind=? AND source_ts<=? AND received_at<=? GROUP BY symbol""",
          (day,step,kind,last,now))
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

def collect(db,now):
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    out={'schema':'scalp-radar-lite-v1','exportedAtMs':now,'counts':{},'sections':{},'unavailable':{},
         'note':'Cumulative and last 24h summaries; overlapping events, assumed costs in percentage points, no real fills. Missing returns are not zero.'}
    def q(name,required,sql,args=()):
        if not set(required)<=tables:
            out['unavailable'][name]='missing tables: '+','.join(sorted(set(required)-tables));return
        try:out['sections'][name]=rows(db,sql,args)
        except sqlite3.OperationalError as e:out['unavailable'][name]=str(e)
    for t in sorted(tables):
        if t.startswith(('r10_','r11_','r111_','ws_','research_','market_')) or t in ('events','last_rows'):
            out['counts'][t]=db.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0]
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
    q('ws_coin_24h',['ws_minute_snapshots'],"SELECT symbol,COUNT(*) n,MIN(candle_time) first,MAX(candle_time) latest,AVG(observed_at-candle_time) lagMs,SUM(json_extract(payload,'$.micro.coverage.trades')=1) tradeCovered,SUM(json_extract(payload,'$.micro.coverage.depth')=1) depthCovered FROM ws_minute_snapshots WHERE candle_time>=? GROUP BY symbol",(day,))
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

def export(source,dest,coin=None,hours=24,now=None):
    source=Path(source).resolve();dest=Path(dest).resolve()
    if source==dest or dest.exists():raise RuntimeError('Destination exists or equals database')
    now=int(time.time()*1000) if now is None else now
    if not 1<=hours<=168:raise ValueError('hours must be 1–168')
    db=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True,timeout=30);db.row_factory=sqlite3.Row
    tmp=dest.with_suffix('.tmp')
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN')
        summary,tables=collect(db,now);summary['databaseBytes']=source.stat().st_size
        cont=continuity(db,now) if 'market_observations' in tables else []
        specs=[('r111_cycles',360),('r11_cycles',360),('r10_cycles',720),('r111_moves',2000),
               ('r111_events',1500),('r11_events',1000),('r111_ready',1500),('r111_outcomes',1500),('r11_ready',1000),('r11_outcomes',1000)]
        def write(scale):
            manifest={'schema':summary['schema'],'snapshotMs':now,'detailLimits':{},'coin':coin,'hours':hours if coin else None,
                'note':'Not a restorable backup. Per-coin continuity is computed from all stored aligned candle timestamps, not the raw sample. Recent window ends at the last expected closed candle. Unknown listing dates/delisting can affect missing counts. Raw optional details are not representative.'}
            with zipfile.ZipFile(tmp,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                json_write(z,'summary.json',summary);z.writestr('coin_continuity.csv',csv_dict(cont))
                for table,n in specs:
                    if table not in tables or int(n*scale)<=0:continue
                    limit=int(n*scale)
                    order='cutoff DESC' if table.endswith('_cycles') else 'cutoff DESC,symbol'
                    z.writestr(table+'.csv',csv_query(db,f'SELECT * FROM {table} ORDER BY {order} LIMIT ?',(limit,)))
                    manifest['detailLimits'][table]=limit
                if 'market_observations' in tables:
                    symbols=[coin] if coin else ['BTCUSDT']
                    if not coin and scale:
                        for table in ('r111_moves','r111_ready','r11_ready'):
                            if table in tables:symbols.extend(r[0] for r in db.execute(f'SELECT symbol FROM {table} ORDER BY cutoff DESC LIMIT 100'))
                        symbols=list(dict.fromkeys(symbols))[:max(1,int(20*scale))]
                    if coin or scale:
                        start=now-(hours*3600000 if coin else 7200000)
                        mark=','.join('?' for _ in symbols)
                        z.writestr('sample_candles.csv',csv_query(db,f"SELECT kind,symbol,source_ts,received_at,payload FROM market_observations WHERE kind LIKE 'kline_%' AND symbol IN ({mark}) AND source_ts BETWEEN ? AND ? AND received_at<=? ORDER BY symbol,kind,source_ts",(*symbols,start,now,now)))
                        manifest['rawSample']={'symbols':symbols,'fromMs':start,'toMs':now}
                for name in ('r10-heartbeat.json','r10-runtime.jsonl'):
                    p=source.parent/name;limit=int(128*1024*scale)
                    if p.is_file() and limit:
                        with p.open('rb') as f:
                            f.seek(max(0,p.stat().st_size-limit))
                            if f.tell():f.readline()
                            data=f.read(limit)
                        if data:z.writestr(name,data)
                json_write(z,'manifest.json',manifest)
        for scale in (1,.5,.25,0):
            write(scale)
            if tmp.stat().st_size<=MAX_ZIP:break
        else:raise RuntimeError('Required summary or requested coin data exceeds 9 MiB; reduce --hours for coin export.')
        tmp.replace(dest)
    finally:
        db.close()
        if tmp.exists():tmp.unlink()
    return dest

def main():
    p=argparse.ArgumentParser();p.add_argument('--database');p.add_argument('--output');p.add_argument('--coin');p.add_argument('--hours',type=int,default=24);a=p.parse_args()
    source=Path(a.database).resolve() if a.database else existing_database(ROOT)
    out=source.parent.parent/'exports' if a.database or configured() is not None else ROOT/'exports'
    out.mkdir(parents=True,exist_ok=True)
    dest=Path(a.output) if a.output else out/('scalp-radar-LITE-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip')
    print('Creating compact analysis report...',flush=True)
    export(source,dest,a.coin.upper() if a.coin else None,a.hours)
    print('LITE EXPORT OK:',dest,flush=True)
    print('Size: %.2f MiB'%(dest.stat().st_size/1024/1024),flush=True)
    print('Upload this ZIP; full database stays local.',flush=True)
if __name__=='__main__':main()
