"""Composition only. Each rule has its own file; the immutable context is shared.
No experimental rule modifies the v0.5 ranking. Versions form a configuration id.
"""
from types import MappingProxyType
from . import trend, ema5, ema15, rsi, macd, relative_volume, vwap, anti_fomo
from . import ema9_cross, ema21_pullback, trend1h_ema21, scalp_v2, multifactor

BASE_MODULES = (trend, ema15, ema5, macd, rsi, relative_volume, vwap)
BASE_VERSION = 'baseline-v05:' + '+'.join(m.VERSION for m in BASE_MODULES + (anti_fomo,))
def evaluate(values, shadow=False):
    c = MappingProxyType(dict(values))
    details = {}
    tags = []
    v2 = {}
    r08 = {}
    for sign, key in ((1, 'UP'), (-1, 'DOWN')):
        contributions = {m.__name__.split('.')[-1]: m.points(c, sign) for m in BASE_MODULES}
        score = sum(contributions.values())
        potential = score >= 68 and trend.gate(c, sign) and anti_fomo.gate(c, sign)
        details[key] = {'score': score, 'potential': potential, 'contributions': contributions}
        if potential:
            tags.append({'id':'BASELINE', 'version':BASE_VERSION, 'direction':key, 'score':score})
        v2[key] = scalp_v2.evaluate(c, sign)
        r08[key] = multifactor.evaluate(c, sign)
        if not shadow:
            continue
        for name in r08[key]['tags']:
            tags.append({'id':name,'version':multifactor.VERSION,'direction':key,
                         'score':r08[key]['full'] if name=='R08_MULTI_FULL' else r08[key]['core'] if name=='R08_MULTI_CORE' else None})
        for name in scalp_v2.challengers(c, sign):
            tags.append({'id':name,'version':'ema-cross-sync5-v1','direction':key,'score':None})
        if v2[key]['potential']:
            tags.append({'id':'SCALP_V2','version':scalp_v2.VERSION,'direction':key,'score':v2[key]['score']})
        # Independent timing hypotheses. Neither depends on the other.
        for module, name in ((ema9_cross,'EMA9_CROSS'), (ema21_pullback,'EMA21_PULLBACK')):
            if module.detect(c, sign):
                tags.append({'id':name,'version':module.VERSION,'direction':key,'score':None})
        # Replace only 1h regime; all other baseline gates/weights remain unchanged.
        alt = MappingProxyType(dict(c, trend1h=trend1h_ema21.direction(c)))
        alt_score = score - contributions['trend'] + trend.points(alt, sign)
        if alt_score >= 68 and trend.gate(alt, sign) and anti_fomo.gate(alt, sign):
            tags.append({'id':'TREND1H_EMA21','version':trend1h_ema21.VERSION+'|'+BASE_VERSION,'direction':key,'score':alt_score})
    return {'baseline':details, 'v2':v2, 'r08':r08, 'candidates':tags, 'volumePhase':relative_volume.phase(c),
            'vwapDistanceATR':{k:vwap.distance_atr(c,s) for s,k in ((1,'UP'),(-1,'DOWN'))}}
