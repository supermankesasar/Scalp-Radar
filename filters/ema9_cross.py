VERSION = "ema9-cross-v1"
def detect(c, sign):
    return sign*(c['close5']-c['ema9_5']) > 0 and sign*(c['prev_close5']-c['prev_ema9_5']) <= 0
