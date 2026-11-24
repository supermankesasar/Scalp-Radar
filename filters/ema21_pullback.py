VERSION = "ema21-pullback-v1"
def detect(c, sign):
    old = c['prev_ema21_5']
    return c['low5'] <= old <= c['high5'] and sign*(c['close5']-c['ema21_5']) > 0 and sign*(c['prev_close5']-old) > 0
