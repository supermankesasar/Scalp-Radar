"""Pure per-coin technical and filter evaluation plus read-only archive context."""
import time
from scan_math import compute_scan_math
from market_archive import MarketContextReader
from filters.registry import evaluate as evaluate_filters
from filters import microstructure

_READERS={}
def evaluate_scan_features(features,live_filter):
    evaluation = evaluate_filters(features, shadow=True)
    hybrid={}
    for sign,key in ((1,'UP'),(-1,'DOWN')):
        base=evaluation['r08'][key]
        hybrid[key]=microstructure.hybrid(features['micro'],base['core'],sign,base.get('setup',False) and base.get('fresh',False) and not base.get('trap',True))
        if hybrid[key]['potential']:
            evaluation['candidates'].append({'id':'R09_HYBRID','version':microstructure.VERSION,'direction':key,'score':hybrid[key]['score']})
    selected=evaluation['v2' if live_filter=='SCALP_V2' else 'baseline']
    if live_filter.startswith('R08_'):
        full=live_filter=='R08_MULTI_FULL'
        selected={k:{'score':int(v['full'] or 0) if full else v['core'],
                     'potential':v['fullPotential'] if full else v['potential']} for k,v in evaluation['r08'].items()}
    if live_filter=='R09_HYBRID':
        selected={k:{'score':int(v['score'] or 0),'potential':v['potential']} for k,v in hybrid.items()}
    return evaluation,hybrid,selected

def compute_full_scan(raw_sets,raw,now,want_minute,minute_error,symbol,universe_size,db_path,micro,micro_at,live_filter):
    started=time.perf_counter()
    result=compute_scan_math(raw_sets,raw,now,want_minute,minute_error)
    features=result['features'];cut=result['i5']['time']
    features['derivatives'],features['breadth']={},{}
    context_error=None;context_started=time.perf_counter()
    if db_path:
        try:
            reader=_READERS.get(db_path)
            if reader is None:
                reader=_READERS[db_path]=MarketContextReader(db_path)
            features['derivatives'],features['breadth']=reader.research_context(symbol,cut,int(time.time()*1000),universe_size)
        except Exception as exc:context_error=str(exc)[:140]
    decision=int(time.time()*1000)
    # Input was captured in main receiver at its actual receipt time, never re-stamp it.
    features['micro']=micro if micro_at is not None and 0<=micro_at-cut<=15000 and 0<=decision-cut<=15000 else {}
    context_ms=1000*(time.perf_counter()-context_started)
    evaluation,hybrid,selected=evaluate_scan_features(features,live_filter)
    return result,evaluation,hybrid,selected,context_error,context_ms,1000*(time.perf_counter()-started)
