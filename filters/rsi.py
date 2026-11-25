VERSION = "rsi-v05"
def points(c, sign):
    r = c['rsi15']
    return 10 if (47 <= r <= 70 if sign == 1 else 30 <= r <= 53) else 0
