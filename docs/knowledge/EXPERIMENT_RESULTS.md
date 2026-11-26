# Experiment Results — preserve failures and denominators

**Verification level:** numerical summaries transcribed from existing repository research on 2026-11-26. They are **EXPLORATORY** proxy outcomes, not trades, audited P&L, or validated strategy performance. The complete original files remain authoritative.

## v0.5 retrospective replay, published 2026-11-22

[Full report](../../research/BACKTEST_V05_2026_REPORT.md). Binance USDT-M Futures; Aug 11–30 (4 pairs, bull) and Nov 1–21 (8 pairs, bear); open-after-signal proxy; closed candles; 0.20% round-trip assumed cost.

| Cohort | Top5 simulated events | Mean gross | Mean net | Net-positive | Close-based target hit | Timeout |
|---|---:|---:|---:|---:|---:|---:|
| August bull | 893 | +0.0111% | **−0.1889%** | 15.34% | 2.13% | 92.72% |
| November bear | 2,057 | +0.0050% | **−0.1950%** | 21.00% | 3.06% | 86.63% |
| Combined | **2,950** | +0.0068% | **−0.1932%** | 19.29% | 2.78% | 88.47% |

LONG 729 events, −0.1896% mean net; SHORT 2,221, −0.1944%; score ≥90 group 837, −0.1894%. Separate RSI70–80 hypothetical SHORT: 163, −0.1740%, **not** v0.5 live SHORT. Delaying simulated entry 5m: target 1.49% (n=2,759); 10m: 0.32% (n=2,538), selection not matched. Alternative close-target 0.25%, 0.35%, 0.50%, 0.65% all net negative (−0.1942%, −0.1936%, −0.1929%, −0.1919%). Results overlap by coin/time; `n` not independent trades; scanner timing/EMA parity incomplete. **Decision: NO-GO for auto-entry.**

## R01–R05 exploratory technical follow-up (23–24 Nov 2026)

[Exact table and strata](../../research/TECHNICAL_FOLLOWUP_2026-11-24.md). 28 pairs; eight 2h windows; 2,688 5m screening points (2,649 liquid), 1,078 unique pair/time/direction snapshots, 15/30/60m horizons. At 30m: original B21 first episodes **142, −0.0260%**; EMA9/9 first **233, −0.0825%**; EMA21 1h first **44, +0.1593%**, but explore subgroup **−0.3602% (n=10)** and later subgroup **+0.4097% (n=25)**; 9/9+EMA9 5m cross first **89, +0.0482%** with mixed windows. RVOL 0.85–<1.1 + VWAP near joint stratum **n=7, +0.2422%**; account share aligned **n=11, +0.2991%**, heavily confounded. No variant promoted.

## R06 modular futures research (23–24 Nov 2026)

[Complete R06 report](../../research/R06_REPORT_2026-11-24.md). 30 new pairs (former 28 excluded), 8 windows, 2,880/2,880 points with OI/global ratio/realized funding, 4,992 unique candidate pair/time/direction snapshots across tags; first-episode net **30m** below, assumed 0.20% cost:

| R06 rule | First n | Mean net 30m |
|---|---:|---:|
| EMA9 crossing standalone | 509 | −0.1466% |
| EMA21 pullback standalone | 241 | +0.0007% |
| OI build continuation | 468 | −0.1461% |
| OI build fade | 468 | −0.2904% |
| OI unwind continuation | 414 | −0.0599% |
| OI unwind fade | 414 | −0.3442% |
| Taker dominance | 532 | −0.0932% |
| Taker + volume spike | 193 | −0.0210% |
| OI build + flow | 179 | −0.2432% |
| OI unwind + flow | 178 | −0.0007% |
| Account shift | 165 | −0.0154% |
| Crowd continuation | 60 | +0.0227% |
| Crowd fade | 60 | −0.0885% |
| Funding continuation | 84 | −0.1706% |
| Funding fade | 84 | −0.1567% |

Caution: some groups change sign across dates (e.g. account shift November 23 −0.3379%, November 24 +0.7055%). OI unwind+flow LONG +0.3397% (68) versus SHORT −0.2111% (110); taker+spike LONG +0.4936% (69) versus SHORT −0.3073% (124): **regime/confounding warning**, not standalone edge.

## R07/R08/R09/R10

- **R07:** implemented independent EMA timing challenger; no validated profitability. [R07](../../research/R07_SCALP_V2.md).
- **R08:** 16 hypothesis tags and CORE/FULL/ablation; case-driven discovery, not independent out-of-sample proof. [R08](../../research/R08_MULTI.md).
- **R09 audit (reported R10, 2026-11-26):** WebSocket observed latency about **5.49s**, long gap **~17h49m**; all **12** minute formulas negative at assumed **0.20%** costs. R08 exhaustion +**0.2541%** at 60m in pooled sample, but **−0.0816%** excluding EVAA and BIGTIME, illustrating concentration. Neither is a selection rule. [R10 audit](../../research/R10_RESEARCH.md).
- **R10:** 13 shadow hypotheses, fixed future holdout and symbol/day clustering planned/implemented in ledger/reporting infrastructure, but **no completed independently profitable holdout or real-fill evaluation available here**. Costs tested as assumptions 0.10/0.20/0.35%. [R10](../../research/R10_RESEARCH.md), [report generator](../../research/report_r10.py).

No numeric new experiment was performed **in this chat**; no raw exchange market dataset or local live-result ZIP for this migration was available. Never conflate simulated outcome counts with live positions.
