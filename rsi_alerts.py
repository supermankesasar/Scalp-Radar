"""Pure RSI exhaustion warning values for candidate watchlists.

These alarms annotate potential signals without suppressing, altering scores,
creating events, or implying that a reversal is guaranteed.
"""
import math

def warning_values(value, config, timeframe):
    try:
        rsi=float(value)
    except (TypeError, ValueError, OverflowError):
        rsi=None
    if rsi is None or not math.isfinite(rsi) or not 0<=rsi<=100:
        rsi=None
    return {
        'rsiRiskTimeframe':timeframe,
        'rsiRiskValue':rsi,
        'rsiRiskLongThreshold':float(config['rsi_warning_long']),
        'rsiRiskShortThreshold':float(config['rsi_warning_short']),
        'rsiRiskLong':rsi is not None and rsi>config['rsi_warning_long'],
        'rsiRiskShort':rsi is not None and rsi<config['rsi_warning_short'],
    }
