VERSION = "macd-v05"
def points(c, sign):
    return 10 if sign * c['macd5'] > 0 else 0
