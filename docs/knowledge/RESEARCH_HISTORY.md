# Research History — chronology and evidence strength

| Stage | Period | What changed | Result / status | Primary source |
|---|---|---|---|---|
| Early Whale Radar concept | Oct 2026 chat context | Proposed candle dashboard, large-transaction radar, TP alerts, later AI | **USER-CHAT** requirements; assistant described HTML demo, but original bytes unavailable in this migration | [Migration log](MIGRATION_LOG.md) |
| v0.5 | 2026-11-22 analysis; Aug/Nov samples | 5m Top5 continuation, close-based target/stop, anti-chase | **EXPLORATORY NO-GO:** combined mean net −0.1932% after assumed 0.20% round trip | [v0.5](../../research/BACKTEST_V05_2026_REPORT.md) |
| R01–R05 | 2026-11-23/24 | EMA9/21 timing alternatives; 1h trend, RSI/MACD, RVOL/VWAP/account-share ablations | Many weak/negative; promising subgroup results highly sample-dependent; no live promotion | [Technical follow-up](../../research/TECHNICAL_FOLLOWUP_2026-11-24.md) |
| R06 | 2026-11-23/24 | 30 new frozen pairs; OI build/unwind, taker share, crowding, funding | Several averages negative and positive subgroups inconsistent across dates/directions | [R06 report](../../research/R06_REPORT_2026-11-24.md) |
| R07 | 2026-11-25 | SCALP_V2 short-EMA/1m-timing challenger, using 5m outcome grid | Experimental; R07's originally default live filter later superseded by R08 | [R07](../../research/R07_SCALP_V2.md) |
| R08 | 2026-11-25 | Multifactor score, flow/structure and case-derived tags, ablation, independent ledgers | **CURRENT live default** CORE; hypothesis tags not validated as profitable | [R08](../../research/R08_MULTI.md) |
| R09 | 2026-11-25 | Hybrid WebSocket + REST cache, 12 1m rules + R09_HYBRID, receipt/coverage tracking | Audit: all 12 1m rules net negative under assumed 0.20% costs; gaps/lag noted | [R09](../../research/R09_WEBSOCKET.md), [R10 audit](../../research/R10_RESEARCH.md) |
| R10 | 2026-11-26 | 13 new shadow hypotheses; local runner, canonical DB, prospective ledger/holdout; bounded pending evaluation | **CURRENT research system**; no forward holdout or live profitability validation established | [R10](../../research/R10_RESEARCH.md), [R10 code](../../filters/r10.py) |

## Research lessons preserved

- **Failed/weak alternatives remain informative:** v0.5 high score (≥90) still had negative mean net; 5/10-minute delayed entry reduced target attainment; lower TP thresholds did not fix aggregate profitability.
- R01–R05 9/9 EMA variant produced more signals but first-episode average was worse than B21; isolated EMA21 1h and fast crosses generated positive *subsamples*, not robust confirmation. Account-ratio alignment sample heavily confounded by pair and direction.
- R06 OI build/fade and unwind/fade are not independent identity or direction signals. Even positive rule/date/side strata should **not** be promoted based on these exploration windows.
- R08 case narratives (PIEVERSE, SKYAI, AIOT, SKY, FLOCK, CYS, AIN) drove rule design; therefore these are **discovery cases**, not independent out-of-sample evidence.
- R09 latency/coverage and R10 anti-concentration safeguards show why raw signal counts and pooled averages can mislead.

Historical documentation sometimes speaks as if a branch was still in staging, and older README sections discuss cloud hosting. Prefer [CURRENT_STATUS](CURRENT_STATUS.md) and latest code for current state; retain historical language only as timestamped evidence.
