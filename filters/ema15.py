VERSION = "ema15-v05"
def points(c, sign):
    return 14 if sign * (c['close15'] - c['ema21_15']) > 0 else 0
