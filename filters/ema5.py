VERSION = "ema5-v05"
def points(c, sign):
    return 11 if sign * (c['close5'] - c['ema21_5']) > 0 else 0
