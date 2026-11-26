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

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Handoff research — 22–24 Nov discovery, reported not recomputed
Initial rule TP5%/SL3%, 1h, no fees/leverage: batch2 LONG 20 (8 TP first/9 SL/3 neither), SHORT 15 (1/9/5); batch3 LONG 20 (3/7/10), SHORT 18 (1/9/8). No-go.
Batch3 620 hourly snapshots: 11 +5% extreme, 8 −5% extreme, 227 intermediate, 374 <1% moves. Median RSI/RVOL5m/ATR%/normalized delta30m: pump 52.80/1.19/.91/−4.41%; dump 57.88/2.08/1.38/−2.31%; quiet 47.84/.78/.47/−1.73%. Prior ret30m pump −.21%, dump +1.28%. 7/8 dumps had EMA9>EMA21 beforehand. Small exploratory sample.
Squeeze fuel on BLESS PIEVERSE NIGHT XRP LTC: 1,005 snapshots, 2 qualifiers both NIGHT, zero +5% in following hour. External archive reported big print 13.3% probability of 5% move in 1h, lift2.8×, direction53% up/47% down; unverified, no valid controls.
Claude V1 reported 131 pairs (60 additional, 30 random control, 41 validation), 884,512 5m candles, 1,172 events (547 pump/625 dump), 8,204 snapshots, 52,455 simulations including repeated parameters, 1–24 Nov. AUC at −60m in extra 1–22 Nov, pump/dump: trade count Z .660/.568; ATR ratio .652/.606; RVOL15 .648/.589; RVOL5 .648/.565; BB width .643/.518; OI .523/.542; funding .537/.530; RSI14 .515/.434; CVD1h .489/.465. AUC is not win rate.
| Claude reported OOS strategy | n | mean net |
|---|---:|---:|
| Breakout expansion LONG |1386|−.250%|
| Breakout expansion SHORT |1873|−.261%|
| OI continuation LONG |1220|−.232%|
| OI continuation SHORT |1027|−.238%|
| Exhaustion fade LONG |164|−.369%|
| Exhaustion fade SHORT |110|−.128%|
| Failed breakout LONG |12350|−.268%|
| Failed breakout SHORT |9796|−.146%|
OOS label is historical report wording, not genuine forward validation: see leakage caveats. Market sync extra 1–22 Nov: 356/591 dumps and 60/430 pumps in hours with ≥10 same-direction events; removing synchronized events reduced several AUCs toward .5. Independent market-wide case 23 Nov 20:55–21:30 WIB: XRP+8.50 SOL+7.83 ADA+7.36 LTC+6.82 ETH+6.73 BNB+5.57 NIGHT+5.18 BTC+5.14%; 7/8 local high 21:25. Cause not established.

## Overnight exports (separate, not cumulative)
25 Nov `scalp-radar-20261125-081109.zip` prior audit, historical assistant report: 507 dashboard events (17 target,50 stop,323 replaced,112 timeout unobserved,5 pending); 26/33 archive runs complete,42 errors,516 pairs,33,682 snapshots,61,866 candidates,353,866 outcomes,1,321,806 observations; 191 5m cutoffs, mean coverage34%, delay151s. 60m/5m confirm net at .20% assumed cost: BASELINE −.0578%, EMA21 pullback −.2019%, EMA9 cross −.1929%, 1h EMA21 trend −.0554%; 60m/15m confirm trend −.0369%. Do not pool with next export.
26 Nov `scalp-radar-20261126-082750.zip`, SQLite reopened, quick_check ok, 591,126,528 bytes. Directly recounted 516 pairs, 1,338,449 observations; 25,402 5m snapshots,79,837 candidates,451,124 outcomes; 79,512 WS snapshots,49,867 candidates,142,965 outcomes; 198 events (10 target/18 stop/151 rank replacement/14 timeout unobserved/5 pending); 11 archive runs (4 complete,4 partial,2 interrupted,1 running),21 errors. 10/28=35.71% among TP/SL only, **not overall win rate**. Prior audit reports active ~4h25m, gap ~17h49m, WS mean lag5.49s, 5m131.7s, 5m coverage86.4%, WS average ~300/516, candle WS98.9%, liquidation coverage97.7%, trades95.8%, depth88.5%, ATR ready56.9%. Coverage not proof of complete trade feed. 26.6% WS 60m outcomes unobserved (prior audit).
| R09 60m rule | observed n | mean net at .20% |
|---|---:|---:|
| Depth Vacuum |214|−.167%|
| Acceleration |3000|−.208%|
| Absorption |631|−.209%|
| Multi Micro |2915|−.213%|
| EMA9 |6055|−.219%|
| EMA10 |5762|−.219%|
| EMA14 |4953|−.220%|
| RVOL Control |4814|−.221%|
| Flow Continuation |3438|−.222%|
| Book Imbalance |3073|−.233%|
| Big Agg Print |103|−.251%|
| Liquidation Burst |1|−.600%|
Recomputed above from SQLite state TARGET=target−.20, STOP=−stop−.20, TIMEOUT=endpoint−.20; excludes unobserved. Prior rounded EMA14 −.221% corrected to −.220% at 3 decimals. Legacy ideal threshold proxy, not execution.
Prior R08 audit 60m/5m confirm net: exhaustion +.2541% (120); sweep −.0599%; breadth −.1309%; EMA14 cross1m Sync5 −.1339%; EMA21 pullback −.1399%; fast reversal −.1424%; absorption −.1426%; ScalpV2 −.1603%; core −.2223%; baseline −.3587%; positioning flow −.4308%. Exhaustion 15m n123 +.2711%, 30m n120 +.3175%; fragile concentration as documented. No promotion. R10 no live outcome data yet.

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
Detailed per-pair outcomes, first-batch failed SHORT examples, batch3 filter ablations, hourly group medians and NIGHT two-signal retest are preserved in [original discovery appendix §§B–E](research/EARLY_DISCOVERY_2026-11-22_24.md). Same 45-pair research already summarized above, **not another 45 or a new backtest**. Batch2 SKDD initially included (equity) then excluded; only corrected totals belong in crypto results. Batch3 true median differs from earlier upper-middle baseline. No independent validation implied.

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## Claude original CSV re-audit
[Full audit](research/CLAUDE_V1_ARTIFACT_AUDIT.md#c-result-details-beyond-existing-aggregate) verifies 52,455 rows, 27,926 base combined OOS rows, 32,804 distinct symbol/time/side keys (not independent trades), fee difference .1% exactly, eight negative gross returns (gross includes modeled slip), precise lift/precision/recall/control and test-only metrics. [Synchronization audit](research/CLAUDE_V1_ARTIFACT_AUDIT.md#d-recomputed-cross-pair-synchronization-and-direction-discovery) reproduces earlier cluster counts and adds −60m medians and directional AUC before/after filter (1,021→605); most differences disappear. No corrected backtest or new holdout. Earlier statements of unavailable source/CSV apply only to previous migrations.

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## V0.5 feature-branch CI versus financial outcomes (not a new backtest)

The dual-profile Scalp/Swing implementation, 60/40 RSI warning badges, crypto icon fallback and fixed Swing expiry were covered by feature-branch GitHub Actions offline regression run [45012562202](https://github.com/supermankesasar/Scalp-Radar/actions/runs/45012562202) at `7e404b84` (**success**: Python compile, JS syntax, unit tests). **No Windows/live market run, user-recorded trade outcome, full historical replay or profitable OOS test** of the new profiles was supplied in the chat. The user said they were trying the app but provided no result logs. The existing negative 2,950-event v0.5 result is **not** a performance estimate for rewritten Scalping/Swing formulas; it remains a warning against assuming edge. [Specific limitations](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md#d2-test-evidence-and-limitations).

<!-- migration-note:2026-11-26-r01-r06-modular-overnight-chat -->
## Original short-window replay recovered (23–24 Nov)
[Exact original R01–R05 tables](research/R01_R06_MODULAR_OVERNIGHT_CHAT_2026-11-24.md#c-original-attached-r01r05-two-window-replay--verified-local-report-transcription) from reopened attached report, not newly recomputed: two windows, 672 points, isolated EMA9 68/158 and EMA21 63/140 correct direction at30m; full-rule 21/21 n89 net −.1418%,9/9 n167 −.1200%, 30m/close5m. At15m no target hit in any full-rule variant; at60m 16/89 vs36/167 targets but net −.0572%/−.0343%. All horizon/confirm and ablation counts retained, including removal of Anti-FOMO −.2097%, trend4h −.1814%; unchanged RVOL/VWAP/EMA5 aggregate does not prove irrelevance. Earlier 12:30 pilot separate; expanded 8-window report and R06 tables already documented above, not new independent datasets. No new market replay in migration.
