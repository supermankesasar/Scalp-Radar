VERSION = "antifomo-v05"
def gate(c, sign):
    dist = sign * c['dist_ema15']
    ret = sign * c['ret15']
    return 0 <= dist <= max(.75, 1.4*c['atr_pct']) and -.4 <= ret <= max(.4, 1.3*c['atr_pct'])
