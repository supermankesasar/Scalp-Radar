# Coin Case Studies — named discovery cases and cohorts

**Important:** The accessible chat itself contains *no individual coin OHLCV records, chart screenshots with recoverable data, wallet addresses, case P&L or detailed time-indexed narratives*. Named cases below come from the repository's [R08 research document](../../research/R08_MULTI.md), not from this chat. Their names may be labels rather than verified exchange symbols. All are **HYPOTHESIS / discovery**, not tested independent success cases.

| Case label | Pattern suggested in R08 | Proposed observable proxies | Major confound / open test |
|---|---|---|---|
| PIEVERSE | Exhaustion, RSI divergence, double top, structure break | Confirmed swings/divergence + break; do not require OI sign as gate | Need timestamped full-case replay and independent holdout |
| SKYAI | Rapid reversal after structure break and flow flip | 1m timing inside 5m cutoff, flow flip; no hard 1h direction veto | Low latency/availability may dominate |
| AIOT | Aggressive flow opposite limited price movement, rejection | Body/ATR, wick, taker-flow **absorption proxy** | Does not prove passive limit liquidity |
| SKY | Similar opposing flow and rejection | Flow/body/wick absorption-proxy tag | Same microstructure ambiguity |
| FLOCK | Extreme activity before reversal | Activity spike plus rejection/anti-chase | Volume spike alone is non-directional |
| CYS | Continuation accompanied by unusual activity | Price response + directional aggressive flow + anomaly | Avoid treating OI sign alone as continuation |
| AIN | Similar continuation | Directional price response, activity, flow | Regime and delay confounding |

No exact timestamp, trading pair, 1m/5m chart or numerical win rate for those seven cases is present in the accessible source. Do not invent one. [R08 code](../../filters/multifactor.py) contains the generalized implementation, not case-level proof.

## Retrospective cohorts, not individual case studies

- v0.5 Aug 11–30, 2026: **BTCUSDT, ETHUSDT, SOLUSDT, DOGEUSDT** (four pairs); Nov 1–21: **BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT, XRPUSDT, DOGEUSDT, ADAUSDT, LINKUSDT** (eight pairs). Aggregate results are in [EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md); per-pair raw event samples are referenced in [v0.5 report](../../research/BACKTEST_V05_2026_REPORT.md).
- R01–R05: 28-pair pooled technical exploration, eight 2h windows, 2026-11-23/24. [Follow-up](../../research/TECHNICAL_FOLLOWUP_2026-11-24.md).
- R06: additional **30 frozen new pairs**, with former 28 intentionally excluded from that cohort. Exact identities in [r06_30.json](../../research/cohorts/r06_30.json); selection used later turnover, so not a point-in-time universe. [R06](../../research/R06_REPORT_2026-11-24.md).

For future case entries require pair, UTC timestamps, source/receipt time, timeframe, regime, candidate rule and version, fees/latency, observation window, chart/data locator, and explicit validation status.
