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

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Additional accessible evidence: historical handoff case narratives (USER-SUPPLIED SUMMARY, not raw OHLCV)
The earlier section's access limitation refers to its original migration; two research handoffs are now accessible. The following are **reported replay observations** from `Pasted text (2).txt`, not independently rerun here, no live signals, no verified actor identity. All pairs quoted in USDT; times WIB. Excursions are not realized returns.
| Pair/date | Reported observations | Interpretation / counterexample |
|---|---|---|
| PIEVERSE 22 Nov | High 5.3679 ~17:10, low 2.7365 ~21:00 (−49%); RSI5m 88.5→79.8 at higher high; 17:45 breakdown RVOL 2.26×, RSI47.8, taker buy45.8%; replay SHORT ~17:50; OI first rose then fell | Exhaustion/divergence/structure; OI sign not mandatory |
| SKYAI 22 Nov | Pump27.6%; high .04493 ~15:20, low .03334 ~16:00 (−25.8%); 1m 15:25 break taker buy34.3%; 15:27 −5.63%, RVOL5.95×; 5m 15:25 −7.3%, RVOL3.82× RSI47.2; OI −~10% early dump | Low timeframe timing |
| PIEVERSE 23 Nov | Low3.2527 high4.0575 (+24.7%), then3.4833 (−14.15%); prior high4.0415 RSI76.3 vs new high RSI67.2; MACD histogram flipped negative; break ~14:05; OI −3.3% on rebound | Double top/divergence hypothesis, distinct event |
| CYS 23 Nov 23:30 | RSI69.1 RVOL2.33× buy59.6%, OI1h+3.49%; max favorable12.44%, adverse .41% in hour | Continuation |
| ARIA 23 Nov 18:40 | RSI39.1 RVOL3.40× sell56.2%; adverse SHORT +8.33% price | False short/entry timing |
| AIOT 23 Nov 21:10 | RSI38.3 RVOL4.44× sell70.1%; down only .2% then up4.76% | Absorption proxy, not proof |
| FLOCK 23 Nov 21:15 | RSI90 RVOL~368× OI1h+43%; adverse LONG7.92% | Anti-chase; extreme activity not direction |
| SKY 23 Nov 20:40 SHORT | RSI37.15 RVOL7.92× normalized delta30m−19.61%, OI1h+1.81%; adverse18.90% | False SHORT |
| SKY 23 Nov 21:00 LONG | RSI57.48 RVOL4.10× delta30m+1.33%, OI1h+2.01%; favorable12.85%, adverse .87% | Direction can change rapidly |
| AIN 23 Nov 21:10 SHORT | RSI32.61 RVOL13.39× delta30m−18.60%, OI1h+.13%, body4.46× prior ATR; favorable10.45%, adverse1.66% | Compare SKY: negative delta alone insufficient |
SKY and SKYAI are distinct. 45-pair cohort (not uniform indicator coverage): batch1 PIEVERSE SKYAI ACE EVAA PROM BULLA BLESS ELSA BTC ETH DOGE; batch2 CYS ARIA AIOT MUBARAK FLOCK CROSS ICNT TRX BNB NAORIS; batch3 INX LISTA AVAAI DOS LIGHT APR AKE SKY MMT AIN IRYS ENSO AGT BMT MON HMSTR HOT BARD SOL ASTER; additional NIGHT XRP LTC ADA. SKDD excluded as TradFi. Source: both supplied handoffs.
R09 export 26 Nov: pooled R08 exhaustion 60m result concentrated in EVAAUSDT (7 candidates, +3.212% mean net) and BIGTIMEUSDT (3, +5.666%). Removing both yields −.0816%. Not individual event replay or a coin-exclusion recommendation.

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
[Original chat detailed evidence](research/EARLY_DISCOVERY_2026-11-22_24.md) is now available: retained connector-derived 1m/5m/15m price, RSI/EMA, OI, funding and account-share observations, per-pair 45-cohort tables and contrary cases. Earlier claims of absent coin-specific evidence apply to earlier migration scope; these are original historical derived observations, not full raw arrays or independent holdout. Do not count them twice.

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## Claude V1 cohort appendix
[All 131 original pair summaries](research/CLAUDE_V1_PAIR_DATA.md) preserve exact separate 22–24 Nov window, category, return, drawdown, open-based run-up and event time/counts. [Selected event counterexamples](research/CLAUDE_V1_ARTIFACT_AUDIT.md#c-result-details-beyond-existing-aggregate) include ACE, IDOL, PIEVERSE rebound, AKE, BULLA, AGT, JCT and INIT. Unlike early discovery, Claude max_runup is relative to first open, not chronological low-to-later-high. 132 combined unique symbols, not independent event counts.

<!-- migration-note:2026-11-26-r01-r06-modular-overnight-chat -->
## Additional chat-specific observations, not independent cases
[28-pair initial EMA crossing table](research/R01_R06_MODULAR_OVERNIGHT_CHAT_2026-11-24.md#b-earlier-isolated-crossing-pilot--chat-reported-no-original-raw-arrays) preserves per-pair 23/24 Nov mean gross signed 30m return from the chat (raw arrays unavailable). [24 Nov screenshot](research/R01_R06_MODULAR_OVERNIGHT_CHAT_2026-11-24.md#f-screenshot-apparent-opposite-direction-24-nov-1641-wib-chat): BNB/BTC/ETH SHORT moved +.12/+.22/+.18%, ADA SHORT −.14%, VELVET LONG −.12%; 4/5 adverse at observation, not final outcome. Includes displayed 15m/1h/24h returns, RVOL, OI, trend, age and score. Do not count as new trades or combine with Claude VELVET case; separate observation. Earlier statements of no screenshot apply to their original chat scopes.
