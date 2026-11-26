"""Offline R10 cohort report: per formula/version, direction, regime, policy and period."""
import argparse,json,sqlite3
from pathlib import Path
def report(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    base="""WITH x AS (SELECT json_extract(t.value,'$.id') filter_id,json_extract(t.value,'$.version') version,
        s.source,s.direction,s.regime,s.symbol,date(s.decision/1000,'unixepoch') day,
        CASE WHEN s.decision<(SELECT value FROM r10_meta WHERE key='holdout_start') THEN 'DEVELOPMENT' ELSE 'HOLDOUT' END period,
        o.horizon,o.policy,o.state,o.gross_pct FROM r10_setups s JOIN r10_outcomes o ON o.setup_id=s.id,json_each(s.tags) t) """
    group='filter_id,version,source,direction,regime,period,horizon,policy'
    agg="""COUNT(*) n,COUNT(gross_pct) observed,SUM(state='UNOBSERVED') unobserved,
        COUNT(DISTINCT CASE WHEN gross_pct IS NOT NULL THEN symbol END) coins,
        COUNT(DISTINCT CASE WHEN gross_pct IS NOT NULL THEN day END) days,
        AVG(gross_pct)-.10 net10,AVG(gross_pct)-.20 net20,AVG(gross_pct)-.35 net35"""
    try:
        comparison=[dict(r) for r in db.execute(base+'SELECT '+group+','+agg+' FROM x GROUP BY '+group)]
        clusters=[dict(r) for r in db.execute(base+'SELECT '+group+',symbol,day,'+agg+' FROM x GROUP BY '+group+',symbol,day')]
        # Descriptive concentration stress test, separately within each fixed cohort.
        grouped={}
        keys=group.split(',')
        for row in clusters:
            k=tuple(row[x] for x in keys);coin=grouped.setdefault(k,{}).setdefault(row['symbol'],[0,0.])
            if row['observed']:
                coin[0]+=row['observed'];coin[1]+=row['observed']*row['net20']
        for row in comparison:
            k=tuple(row[x] for x in keys);coins=grouped.get(k,{})
            ranked=sorted(((s,n,total) for s,(n,total) in coins.items() if n),key=lambda x:x[2],reverse=True)
            removed=ranked[:2];remaining=ranked[2:];n=sum(x[1] for x in remaining)
            row['top2_contributors']=[x[0] for x in removed]
            row['net20_excluding_top2']=sum(x[2] for x in remaining)/n if n else None
            row['observed_excluding_top2']=n
        return {'comparison':comparison,'symbol_day_clusters':clusters,'holdoutStart':db.execute("SELECT value FROM r10_meta WHERE key='holdout_start'").fetchone()[0],
                'note':'Overlapping signals; not independent trials. Holdout is a fixed temporal split, not proof. Costs are assumed round trip; funding and fill slippage not modeled.'}
    finally:db.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('database');p.add_argument('--output',default='r10-report.json');a=p.parse_args()
    Path(a.output).write_text(json.dumps(report(a.database),indent=2),encoding='utf-8')
    print(a.output)
