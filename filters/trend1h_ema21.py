VERSION = "trend1h-ema21-v1"
def direction(c):
    p, e, old = c['close1h'], c['ema21_1h'], c['ema21_1h_prev6']
    return 'BULLISH' if p > e > old else 'BEARISH' if p < e < old else 'MIXED'
