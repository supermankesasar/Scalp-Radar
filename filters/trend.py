VERSION = "trend-v05"
def points(c, sign):
    d = 'BULLISH' if sign == 1 else 'BEARISH'
    return (24 if c['trend1h'] == d else 0) + (12 if c['trend4h'] == d else 5 if c['trend4h'] == 'MIXED' else 0)

def gate(c, sign):
    d, opposite = ('BULLISH', 'BEARISH') if sign == 1 else ('BEARISH', 'BULLISH')
    return c['trend1h'] == d and c['trend4h'] != opposite
