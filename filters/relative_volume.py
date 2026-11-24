VERSION = "rvol-v05"
def points(c, sign):
    r = c['rvol5']
    return 11 if r >= 1.1 else 6 if r >= .85 else 0

def phase(c):
    r = c['rvol5']
    return 'LOW' if r < .85 else 'NORMAL' if r < 1.1 else 'ELEVATED' if r < 1.5 else 'SPIKE'
