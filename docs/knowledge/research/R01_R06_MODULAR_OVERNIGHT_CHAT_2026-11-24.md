# R01–R06: technical discovery, modular scanner and first overnight run (23–24 Nov 2026)

Migration date 26 Nov 2026; historical evidence only. This supplements, not replaces, the current R08/R09/R10 system and existing 45-pair, Claude V1 and V0.5 Scalp/Swing appendices. The 28/30 cohorts below are the original technical/R06 experiment cohorts, NOT additional new cohorts to sum with other studies.

## A. User decisions and discarded early proposals

**USER-CHAT:** Futures only (Binance USD-M, crypto USDT perpetual); no Spot dependency. User questioned history as a prediction standard; prefers fixed, explainable **rule-based + real-time** behavior. History is data for computing indicators, coin technical profile, and evaluating whether signals work/still apply, not an assumed repeating pattern. Adaptive need not be a separate engine; relative/volatility-normalized arithmetic can be a fixed rule. User explicitly wants EMA9 hypothesis tested, 8 old +20 additional, then 30 new pair cohort for R06, 15m/30m validity and both 5m/15m confirmation; ALL candidates evaluated, even outside Top5. No neutral category displayed. User approved modular independent files and centralized history; when first overnight collection was proposed for 30 pairs, user explicitly corrected **ALL pairs**, including prior cohorts. Prior cohorts are historical research, not excluded from monitoring. User delegated GitHub organization and allowed EMA adjustments, not automatic trading or unvalidated weights.

**HISTORICAL / superseded assistant proposals (not empirical scores):** initial F01 liquidity, F02 volume anomaly, F03 whale/shark, F04 buy/sell pressure, F05 accumulation, F06 trend, F07 breakout, F08 momentum, F09 anti-FOMO, F10 distribution, F11 reversal, F12 exit/TP. Draft weight whale25/volume20/accumulation20/trend15/momentum10/anti-FOMO10; tiers ≥80 high, ≥60 watch, ≥40 weak. Later suitability ratings rule95/real-time95/adaptive65/history30 were subjective, not measurements; draft 50:50 rule/real-time directional score was not adopted. Later proposed Technical40/Activity20/Positioning20/OrderFlow20 explicitly withdrawn as main configuration pending backtest. Do not substitute any of these for R08 or R10. Separate directional/activity/risk/validity scores and coin historical profile were ideas. AI integration deferred; later user preference Arkham and local AI in other chats, and R10 operational-first/zero runtime AI, have precedence.

Coin Historical Profile proposal: listing age, highest/lowest since contract listing, distance from each, 24h/7d/30d ranges and max pump/dump by defined interval; not "cheap" or a prediction. Technical history for EMA/RSI/ATR/volume/OI; signal history for validity, outcome, MFE/MAE and elapsed time. Proposed lifecycle DETECTED → CONFIRMED → ACTIVE → SUCCESS / FAILED / INVALIDATED / EXPIRED; separate setup validity from price outcome, include UNOBSERVED and ranking-only replacement. Proposed 100 events example (60 success,20 failure,10 expired/invalidated,10 active) yielded 75% among resolved TP/SL only, not overall rate (60/90 evaluated =66.7%); illustrative, NOT market results.

## B. Earlier isolated crossing pilot — chat-reported, no original raw arrays

23 and 24 Nov, detection 12:30–13:30 WIB, evaluation through 14:30; EMA9 or EMA21 5m price crossing, warm-up, 15/30/60m from signal. Separate from the later 13:00–14:00 run below. Per-pair values are reported mean gross direction-adjusted horizon return at 30m, percent, not executed P&L. Dash=no crossing in that window. Source: earlier assistant table in this chat; raw input arrays not recovered, no recomputation, lower evidence strength than attached report.

| USDT pair | 23 Nov EMA9 | 23 Nov EMA21 | 24 Nov EMA9 | 24 Nov EMA21 |
|---|---:|---:|---:|---:|
|BTC|+.06|—|+.36|−.11|
|ETH|+.04|+.33|+.37|−.11|
|SOL|−.35|—|+.04|−.31|
|BNB|+.34|+.29|+.49|−.04|
|XRP|−.05|—|+.28|+.28|
|DOGE|+.09|−.31|+.07|+.01|
|ADA|−.27|—|−.13|−.13|
|LINK|+.08|+.16|−.10|−.04|
|AVAX|−.08|−.11|+.29|+.29|
|LTC|+.07|−.20|−.05|−.17|
|BCH|+.37|−.57|+.53|+.19|
|TRX|+.08|+.09|+.12|+.12|
|DOT|−.19|—|+.71|+.15|
|SUI|−.26|—|−.07|−.02|
|APT|−.19|—|−.16|−.10|
|NEAR|+.05|+.80|−.16|−.43|
|ATOM|+.50|+.17|+.45|—|
|INJ|+.58|+.40|−.36|−.34|
|UNI|+.13|+.25|+.18|+.01|
|AAVE|−.02|—|+.38|−.07|
|ARB|+.73|−.53|+.57|+.19|
|OP|−.41|−.18|−.03|−.13|
|FIL|—|—|+.60|+.05|
|ETC|+.03|−.09|+.51|+.17|
|WLD|−.76|−.21|.00|−.23|
|ENA|−.75|−.99|−.02|−.09|
|SEI|−.19|—|+.02|+.23|
|TIA|—|—|−.19|−.20|

24 Nov group A reported gross 30m EMA9 +.1107% (11), EMA21 −.0440% (12). Group B reported gross 15/30/60m EMA9 −.0415/+ .0618/+.2010%, EMA21 −.0527/−.0309/+.0954%. Overall 24 Nov reported direction-positive counts EMA9 24/44,21/44,27/44; EMA21 23/46,24/46,25/46 respectively. Fixed experimental target .65%, stop .40% (not ATR-based): at 15m, 5m/15m close target counts 1/0 of44 EMA9, 2/0 of46 EMA21; at 30m 5/3 of44, 3/0 of46. These rounded chat tables and aggregate counts have not been reconciled to original event rows; don't combine with later archived replay or assert validity. EMA9 responsiveness does not establish direction accuracy. No market regime independently classified.

## C. Original attached R01–R05 two-window replay — verified local report transcription

Source file SCALP_RADAR_R01_R05_2026-11-24.md, SHA-256 5c9de72ef0edca06ad229ae023660c2e66290ede89934f8ff1e192bb44ca6b06, reopened directly 26 Nov. Baseline app.py blob c23da9bc542714ec40206ea3f54ad89c65dbc99d (old v0.5). Binance public USD-M historical klines via connector. 23/24 Nov 13:00–14:00 WIB detection (13:05 through14:00), evaluation through15:00. 28 pairs as above, 672 screening points; 5m/1h inputs, 15m/4h reconstructed from complete bars, 309/229/229/229 closed bars approximate production; prior 24h quote turnover ≥10M for full rule only. No Top5/cooldown, repeated candidates. Only already closed bars at detection. R01 isolated cross; R02 four EMA periods with original gates; EMA15m change also affects Anti-FOMO distance. All full-rule candidates reportedly passed next-open .30% chase/stop gate in these windows. Signal price close; proxy entry next 5m open; target max(.65%,1.5×ATR5m%), stop max(.40%,ATR5m%). Target/stop compare 5m or calendar-aligned 15m closes, first terminal hit, exact horizon 5m close for timeout; endpoint gross measured independently. Net deducts assumed .20% round trip. No latency replication, actual fills, funding/liquidation or independent holdout. Counts not independent trades; weighted rounded batch means.

### C1. R01 isolated cross

|Date|EMA|n|Correct 15m|Correct 30m|Correct 60m|Net30m %|
|---|---:|---:|---:|---:|---:|---:|
|23 Nov|9|73|36|39|36|−.2070|
|23 Nov|21|45|20|20|18|−.2018|
|24 Nov|9|85|31|29|41|−.2713|
|24 Nov|21|95|43|43|48|−.2846|

Pooled 30m direction correct EMA9 68/158=43.0%, EMA21 63/140=45.0%; not net win rate. R01 not standalone edge.

### C2. R02 full rule, 30m / close5m

|Date|EMA5/15|n|Target|Stop|Direction correct|Gross horizon %|Net proxy %|
|---|---|---:|---:|---:|---:|---:|---:|
|23 Nov|21/21|28|0|7|7|−.1941|−.3537|
|23 Nov|9/21|28|0|7|7|−.1941|−.3537|
|23 Nov|9/9|63|0|17|21|−.1480|−.3556|
|23 Nov|21/9|63|0|17|21|−.1480|−.3556|
|24 Nov|21/21|61|6|3|46|+.1731|−.0445|
|24 Nov|9/21|61|6|3|46|+.1731|−.0445|
|24 Nov|9/9|104|9|5|85|+.2358|+.0227|
|24 Nov|21/9|103|9|5|84|+.2350|+.0217|

EMA5-only change did not alter these candidate counts/outcomes; EMA15 change did, likely because of distance gate. Date-dependent, combined negative; broader follow-up below splits gate from score.

### C3. R03/R04 pooled two dates

|EMA combo|Horizon min|Confirm min|n|Target|Stop|Timeout|Correct direction|Net %|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|21/21 and 9/21|15|5|89|0|5|84|43|−.2080|
|21/21 and 9/21|15|15|89|0|2|87|43|−.2024|
|21/21 and 9/21|30|5|89|6|10|73|53|−.1418|
|21/21 and 9/21|30|15|89|5|6|78|53|−.1372|
|21/21 and 9/21|60|5|89|16|12|61|65|−.0572|
|21/21 and 9/21|60|15|89|16|10|63|65|−.0429|
|9/9|15|5|167|0|10|157|86|−.1975|
|9/9|15|15|167|0|6|161|86|−.1934|
|9/9|30|5|167|9|22|136|106|−.1200|
|9/9|30|15|167|6|14|147|106|−.1157|
|9/9|60|5|167|36|33|98|118|−.0343|
|9/9|60|15|167|35|27|105|118|−.0111|
|21/9|15|5|166|0|10|156|85|−.1981|
|21/9|15|15|166|0|6|160|85|−.1940|
|21/9|30|5|166|9|22|135|105|−.1215|
|21/9|30|15|166|6|14|146|105|−.1171|
|21/9|60|5|166|35|33|98|117|−.0375|
|21/9|60|15|166|34|27|105|117|−.0142|

First 15m target zero for all full-rule variants; 30/60m improved observed target counts but net still negative. 15m confirmation misses adverse intra-candle movements; fewer stops not proof of lower risk. Keep separate 5m fast and 15m persistence checks, 15/30m validity research, 60m follow-up, not automatic holding period change. Live legacy UI still 15m at that time.

### C4. R05 leave-one-out (30m / close5m)

Removed one score component, normalized remaining max to100, retained threshold68; trend removal also drops corresponding gate, EMA15-score removal retains distance gate; Anti-FOMO and both trend gates ablations retain original scoring. Not isolated causal weight estimate.

|Variant|23 Nov n|23 Nov net %|24 Nov n|24 Nov net %|Combined net %|
|---|---:|---:|---:|---:|---:|
|Original|28|−.3537|61|−.0445|−.1418|
|No MACD|28|−.3537|58|−.0541|−.1516|
|No RSI|28|−.3537|58|−.0541|−.1516|
|No RVOL|28|−.3537|61|−.0445|−.1418|
|No VWAP|28|−.3537|61|−.0445|−.1418|
|No EMA5 score|28|−.3537|61|−.0445|−.1418|
|No EMA15 score|28|−.3537|58|−.0541|−.1516|
|No 1h trend component+gate|28|−.3537|79|−.0700|−.1442|
|No 4h trend component+gate|28|−.3537|73|−.1153|−.1814|
|No Anti-FOMO gate|58|−.3946|84|−.0820|−.2097|
|No both trend gates|28|−.3537|72|−.0837|−.1593|

Anti-FOMO/4h removal worse in this sample. Unchanged aggregate for RVOL/VWAP/EMA5 does not prove uselessness: threshold may not change candidate set; ranking effects untested. No new weights accepted.

## D. Expanded 28-pair follow-up and 30-pair R06 — repository primary evidence

[Full technical report](../../../research/TECHNICAL_FOLLOWUP_2026-11-24.md), [summary JSON](../../../research/results/technical_2026-11-24_summary.json), [strata](../../../research/results/technical_2026-11-24_strata.json), [method](../../../research/README_TECHNICAL.md); eight two-hour windows end UTC 23 Nov 04/08/12/16/20h, 24 Nov 00/04/08h. 2,688 scans,2,649 liquid,1,078 snapshots. This expands C, not independent confirmation. First episode resets per window/rule, not an independent position. Preserve linked complete tables: all vs first, EMA gate-only vs score-only, 1h EMA200/50/21/relaxed/remove, joint RSI/MACD, cross/pullback, RVOL/VWAP/account ratio strata. EMA9/9+EMA9 cross first +.0482% (89) vs EMA21 cross −.0740% (46); EMA21 pullback +.0360% (77), EMA9 touch +.0016% (145). 9/9 gate-only larger candidate count but weaker first episode; requiring both RSI/MACD worsened first outcome (130,−.0946%) vs 142,−.0260% baseline. No 1h EMA9-specific test. Activity phase and VWAP signed distance useful hypotheses, not proven thresholds. BTC account ratio example reported 71.88% long/28.12% short (2.5562) at 24 Nov 15:00 WIB; account count, not contracts or wallet identity; original tool sample unavailable here. Ratio alignment first n=11 heavily confounded, all243 old-cohort baseline snapshots opposed.

[R06 report](../../../research/R06_REPORT_2026-11-24.md), [cohort](../../../research/cohorts/r06_30.json), [full results](../../../research/results/r06_summary.json). New cohort excludes the 28 in research only. 30 names (USDT suffix): ZEC HYPE BLESS 1000PEPE EVAA PROM MMT PIEVERSE ARIA LISTA ELSA BULLA ACE PUMP CYS TAO AKE TRUMP ON LIT QNT VVV SKY MUBARAK INX ONDO XLM XMR WLFI FET. Ranked later-known 24h turnover of active crypto contracts, not random or unbiased historical universe. 2,880 scans,4,992 unique pair/time/side rows, full OI/ratio/funding coverage; separate 15/30/60m, net .20% proxy. Same eight dates/windows, no new temporal holdout. R06 standalone cross/pullback NOT earlier 9/9 conditioned triggers. Existing KB records numeric 30m table; additional results in JSON (e.g. BUILD_FLOW_DIVERGENCE 44 first −.371%, BUILD_FLOW_VOLUME 51 −.3562%, BUILD_FLOW_ACCOUNT_SHIFT 12 −.6295%, UNWIND_FLOW_CROWD 15 +.0005%, tiny mixed-direction sample). No stable profit across both dates; OI rise/fall + price direction does not identify initiator; last realized funding not forecast. Top trader, aggTrade/large print, book/liquidation not included in R06 historical replay (later collectors added some, see R09/R10). No new experiment run in migration.

## E. Modular implementation and chronology, historically at 24 Nov

Research branch research/technical-r01-r05 engine 24120473f032d3e99435d0f7b5ba698d9ae7ce2d, six audit JSONs, reusable Node runner, offline leakage fixture. Research/modular-r06 branch: separate research/filters/{oi,order_flow,positioning,composite,technical_ema}.cjs, generated frozen bundle e43a89db1d1c3d50ac40029234492d4981781a94 only tool execution artifact, not edit target; summary commit d71f65786bc7871441e9baff2bc7a041f8aebf98. Python filters/trend, ema5, ema15, rsi, macd, relative_volume, vwap, anti_fomo, ema9_cross, ema21_pullback, trend1h_ema21 separate; registry combines independent contributions, immutable snapshot, versioned tags. Staging integration 4374a2edfa4b9c84ac7ed74d2961b733f6a8fe02 kept v0.5 live ranking and added shadow tags. ResearchHistory additive central SQLite (same path/lock as SignalStore): research_snapshots(symbol,candle_time), research_candidates(symbol,candle_time,filter_id,version,direction), research_outcomes(candidate_id,horizon,confirm), research_archive(run_id,batch,symbol,candle_time,direction). Record before Top5, no rank-driven research cancellation, dedup by key, outcome 15/30/60m×5/15m close. Missing retry beyond24h in historical implementation UNOBSERVED, not stop; compare current code for changed settlement. Archive importer provided, not run on user DB in this chat. Replay synthetic future-isolation and missing-data tests passed, standalone REST runner not verified on host, Python test files added; no claim CI executed at this historical stage. Raw full connector arrays not committed; candidate snapshots and summaries preserved. Current main later merged and extended R07–R10; see CURRENT_STATUS.

### E1. First overnight rollout, user-observed log

User intended unattended office Windows PC. Corrected assistant's mistaken 30-pair limit to ALL active crypto USDT perpetuals, including old samples. Exchange info observed 516 qualifying contracts (dynamic count). market_archive.py initial commit 39eb6b0e00dbcb9da9b32b32a3c10b1340e99aae, app wiring 0781fc8f51c61ebf15b4a70594d565158ad16a18; raw archive paced .55s across workers, at least30m between sweep starts, endpoint history overlap with source timestamp/receipt timestamp stored; not simultaneous 5m live polling. Archived 5m klines incl taker buy, OI, global/top account and top position ratios, premiumIndex/mark/funding and ticker24h, longer TF input as scanner fetched; initial no WS orderbook/aggTrade/liquidation. REST 403/451/418/429 pauses, logged errors, no bypass. SQLite additive market_observations(kind,symbol,source_ts) and collection run/error telemetry. Legacy run_overnight.bat local only, 127.0.0.1:8765; /api/overnight and /api/research. Export via consistent SQLite backup ZIP, not live DB file alone with WAL. User requested move installation to D drive; old folder-copy procedure stop process, copy entire directory, restart, check printed DB path; actual move not confirmed. **Superseded operationally by R10 canonical %LOCALAPPDATA% path and explicit SCANNER_DB override**; do not apply old move advice blindly. No personal paths saved.

USER-CHAT log 24 Nov 16:15–16:17 WIB: overnight enabled, background scanner=1, ALL516, local API 200, progress at ~16:17:05 **25/516 complete25 errors0**. Verifies that initial startup and first 25 archived pairs worked per supplied log; NOT entire sweep, continuous overnight success, candidate correctness or current R10 PC verification. Later separate 25/26 Nov exports already audited in KB; do not merge counts. User wanted Windows theme automatic: CSS prefers-color-scheme light/dark added only index.html (commit abf6595ee1e51140fb02bd922720038ffe6fda73), current main includes same blob 7337509d72eeb5858f8045e9688d1af9d4827b74. UI update fetch/restore index.html then refresh, no scanner restart needed for that historical static asset change; no confirmation user applied. Neutral/universe button removed historically; internal neutral data still useful.

## F. Screenshot: apparent opposite direction (24 Nov 16:41 WIB chat)

USER-CHAT observation, two displayed screenshot crops; not raw quote data, complete OHLCV or final event record. Main displayed rows in old v0.5 overnight UI:

|Pair|Signal|Market move since signal|15m|1h|24h|RVOL5m|OI15m|Trend 1h/4h|Initial score|
|---|---|---:|---:|---:|---:|---:|---:|---|---:|
|BNB|SHORT|+.12%|+.12%|−.24%|−1.54%|.64×|−.10%|BEAR/BEAR|100|
|BTC|SHORT|+.22%|+.28%|−.06%|−2.29%|.53×|−.01%|BEAR/BEAR|89|
|ETH|SHORT|+.18%|+.26%|−.22%|−2.09%|.40×|+.05%|BEAR/BEAR|89|
|ADA|SHORT|−.14%|−.07%|−.74%|+.34%|1.12×|+.27%|BEAR/BEAR|89|
|VELVET|LONG|−.12%|+.74%|+1.35%|+6.28%|1.07×|+.13%|BULL/BULL|not fully visible|

First three shorts ~6m old, ADA ~3m, VELVET ~6m; first screenshot quote not live, VELVET quote new. Short target shown −.65%, VELVET +1.00%. Four of five adverse as displayed, not final failure rate, not proof of inverse rule. No final outcomes or matching DB rows supplied here. BNB 100 is initial score; RVOL .64× at displayed snapshot would contribute 0 under baseline rule (<.85). No evidence all other current components equal initial values.

Source audit at then staging branch: signals.py _signed computes directional return sign×100(price/base−1); _public currentPct is direction-adjusted, currentMarketPct multiplies by sign to show raw price movement; peakMarketPct also raw sign. ui.js displays raw move and colors by price up/down, NOT favorability to side; score displays ev.initialScore, not ev.lastScore. Registry trend gate and Anti-FOMO sign direction consistent, no code evidence of inverted LONG/SHORT. Legacy setup_active/last_score updated only with new full snapshot; PENDING can persist even when setup weak, fast poll not full scoring; stale quote marker matters. Proposed show initial and current scores separately, label favorable/adverse using direction-adjusted metric while keeping raw percent explicit, timestamp freshness, validity weakened/invalidated separate from price outcome. Earlier example "78" was fictitious. Do not flip rule, change weights or count observed adverse motion as loss; evaluate against target/stop/timeouts and eventual MFE/MAE. User asked why, assistant advised preserving stable overnight config for investigation. No UI fix for this issue was applied in that turn; theme fix unrelated. Current R08/R10 status and newer evidence supersede historical formula; do not imply current defect without fresh verification.

## G. Provenance and limitations

Reopened local attachments analisis.txt, kondisi-dasar.txt, original R01–R05 report, local v0.5 report/app source, and visible screenshots/chat. Local app.py SHA-256 bd8b87e1d356d3ba2453935f2e2a80206bebac248c005626bc73743bbdd07a19; v0.5 report SHA-256 57a45abf34561ba2d321ee8577e2a3677eb78037378fe06f19db1a8e158f56e8. Earlier conversation context partly retained as summary; not every connector raw response recoverable. Screenshot crops visible, one mounted image path shared between attachments; original two distinct byte hashes unavailable; use visible transcription, no raw images or local identifying info committed. Original early 12:30 crossover arrays, raw order book/trades/liquidations, on-PC DB for this specific chat, live fills, current PC status unavailable. No new exchange test or source modification during migration. See [migration log](../MIGRATION_LOG.md) for merge audit.
