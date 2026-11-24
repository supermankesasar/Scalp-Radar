VERSION = "vwap-v05"
def points(c, sign):
    return 8 if c['vwap'] is not None and sign * (c['close5'] - c['vwap']) > 0 else 0

def distance_atr(c, sign):
    v, atr_pct = c['vwap'], c['atr_pct']
    return None if not v or not atr_pct else sign * 100 * (c['close5']/v-1) / atr_pct
