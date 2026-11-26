# Claude Research Lab V1 — original artifact audit (Nov 2026)
**HISTORICAL / EXPLORATORY / REJECTED as a standalone trading strategy; not Scalp Radar runtime.** Migration 2026-11-26. This is primary-artifact supplementation of the existing 45-pair and Claude handoffs, not a second independent study. See [early discovery](EARLY_DISCOVERY_2026-11-22_24.md), [current status](../CURRENT_STATUS.md), [experiment results](../EXPERIMENT_RESULTS.md). User ran Claude-authored Python locally on 24 Nov at 10:41 WIB, not inside the current web. Model name is self-reported in the uploaded report (Claude Sonnet 5.5); not independently verified. No new Binance queries, no rerun of market backtest, no live trades during this migration. Reviewed source, original derived CSVs, configuration and report; recomputed descriptive statistics locally. Existing public-archive nine-pair report and illustrative follow-up remain secondary/unverified evidence.

## A. Source manifest and reproduction
Original uploaded artifacts accessible in this chat, preserved on user's side; the large derived CSVs and executable script are not duplicated in the public repository. SHA-256 below identifies exact bytes inspected, not a claim of exchange authenticity.
|File|Rows × columns / purpose|SHA-256|
|---|---|---|
|crypto_pattern_research.py|source, syntax AST parse succeeded|be228f8814195c1ee73ae5d4cba463a9644e7c5c823cc93419c19d2bf686da1b|
|RESEARCH_HANDOFF_REPORT.md|original report A–I|556ca4923761c99166462b98b7ab241dbb7baff22572d405833fac21d53f66e0|
|pairs.csv|131 × 13|8006f2ab18dd4c4a19c5a64fe705ab0d56b36647173627372ee0afaa463b0b98|
|events.csv|1172 × 20|04cc83a8dd4428996670ce37d5599305829923bb89c94b1b08f19a716cfe87e8|
|event_snapshots.csv|8204 × 19|ed3c9022b530e6eed6e2aa36a6ed2481f896791eb9ea9e19b46587efd2f056cf|
|trades.csv|52455 × 20|0697d95686e5d203f6dc31a8dd196aadf06b5de37d38747f022b19b3bdd4c658|
|backtest_summary.csv|192 × 26|e76636d7a5d5f7e2fe61e6ad0f971c5cbdbbe9fbb9037611fb3c5aa6871313e1|
|indicator_auc.csv|96 × 12|43b2a59418b00f1f2430d6fbda84acd487d3d639d77477830d8b1e8de6a984bf|
|tuning_log.csv|128 × 5|360df89d9db5bf98ea6ce702cabae648be20df25d5e2c550ab1c4f343fc1f09d|
|params.json|configuration|2bf70f34498cf6f793c1ba7b5f990084d86e9c8efb8af46679c4d526c9bf0fe8|

Reproduction environment: Python requests/pandas/numpy; args start 2026-11-22, end 2026-11-25 (exclusive), split 2026-11-24, extra-start 2026-11-01, extra-end 2026-11-22, n-new 60, n-control 30, tp 2.0, sl 1.0, fee .0005, slip .0005, move-floor .03, move-k 5, min-qv 5000000 USDT/day, seed 7. Main actual cutoff 24 Nov 10:40 WIB. All dates WIB unless stated. Two days warmup before earliest interval. Public Binance USDⓈ-M endpoints: /fapi/v1/exchangeInfo, /fapi/v1/klines (5m and 1h), /futures/data/openInterestHist (5m), /fapi/v1/fundingRate. No account keys. Excludes non-COIN, TradFi subtype, named stablecoins, inactive and too-recent listings relative to main start; PAXG and XAUT (tokenized gold) included in COIN universe, not pure crypto-only economic exposure. 1h selection by later outcome/turnover; category quotas then random fill; control from remaining eligible coins; current exchangeInfo creates survivorship risk. No archived point-in-time listing, no raw OHLCV persisted, no complete trade/depth/liquidation/long-short series. Funding/OI availability as reported; coverage not proof of every observation.

**Verified derived CSV counts:** 131 = 60 new_selected + 30 random_control + 41 prior_validation; 704 main-window candles per pair (92,224 main rows); 884,512 total 5m candles reported in original report, not independently reconstructible without raw candle frames. With earlier 45 pair set union is 132 (XRP, LTC, NIGHT overlap additional; ADA only absent from Claude cohort). 1,172 unique event IDs; 8,204 unique event/offset rows; no unmatched snapshot parent or missing snapshot features. 52,455 trade rows, 30,482 base (train 2,556; test 431; extra 27,495), 21,973 improved (train 1,942; test 236; extra 19,795); 33,113 unique symbol/timestamp/pattern/side keys and 32,804 unique symbol/timestamp/side keys across versions, not independent trades; all ev_hit present. CSVs are derived features/outcomes, not raw data or executed P&L.
|Segment|PUMP|DUMP|PUMP caught by any raw base pattern|DUMP caught|
|---|---:|---:|---:|---:|
|train 22–24 Nov 00:00|116|33|34|15|
|test 24 Nov 00:00–10:40|1|1|0|0|
|extra 1–22 Nov 00:00|430|591|121|89|
Totals 547 PUMP /625 DUMP; 259 events flagged caught, 25 with best lead=0 (not advance warning). 234 have positive reported lead, still raw/not executable. Onset is forward-label reference bar, not necessarily first market move.

## B. Exact V1 calculations (source functions feat, add_labels, signals, sim_one, run, auc_table)
Notation: C/O/H/L, Q=quote volume USDT, B=taker-buy quote volume, T=trade count. Index is candle OPEN time; feature usable after close. 5m base, H=12 bars horizon. All ratios fractional unless expressly %.
- sig5 = rolling std(log(C/Cprev),288).shift(1) (pandas sample std); sig_h=sig5*sqrt(12); z_n=(C/C[t−n]−1)/(sig5*sqrt(n)), n=1,3,12. Mixed simple/log scaling, not standardized normal-return probability. rel_z12 = coin z12 − BTC z12 (not beta-adjusted excess return).
- TR% = max(H−L,abs(H−Cprev),abs(L−Cprev))/Cprev; atr_ratio = mean TR% latest12 / mean TR% prior288 shifted12. Not Wilder ATR. RVOL=Q/median(Q prior288), rvol3=mean latest3 RVOL; trades_z=(log1p(T)−prior288 mean)/prior288 std. Not current R08 mean20 nor original chat median20.
- delta=2B−Q; cvd3/cvd12=sum(delta,3/12)/sum(Q,3/12); signed normalized quote imbalance, not cumulative tick CVD. BB width=4*std(C,20)/mean(C,20), bbw_ratio=width/prior288 median width, squeeze=min latest12 bbw_ratio. RSI14=100−100/(1+EWMA(up,alpha=1/14)/EWMA(down,alpha=1/14)), adjust=False (Wilder-like initialization, not exact SMA seed); eff12=abs(C−C[t−12])/sum(abs(C−Cprev),12) Kaufman ratio, different from early discovery price-efficiency proxy.
- hh48/ll48 = prior48 high max/low min excluding current. OI last observation timestamp <= bar OPEN, ffill tolerance20m; oi_chg12=OI/OI[t−12]−1; oi_z12=oi_chg12/(std(prior288 single-bar OI fractional changes)*sqrt12). Funding last realized observation <= open, ffill tolerance9h (funding intervals may differ). Missingness not zero.
- Future label only: fwd_hi=max high next12/C−1; fwd_lo=min low next12/C−1; threshold=max(.03,5*sig_h); PUMP when fwd_hi>=threshold and fwd_hi>=−2*fwd_lo; DUMP when −fwd_lo>=threshold and −fwd_lo>=2*fwd_hi. Onset when current label true and no same label prior12; forward labels overlap, event counts not independent. For valid flags need sig_h, atr_ratio, rvol, cvd12 non-null, plus available forward bars for lab_ok; not all indicator completeness checked.
- Base rules (each mirrored L/S): breakout_expansion: close beyond hh48/ll48, rvol>=2, atr_ratio>=1.5, cvd3 sign aligned. oi_continuation: z12>=2 LONG or <=−2 SHORT, cvd12 sign aligned, oi_z12>=1.5, rvol>=1.5. exhaustion_fade: LONG z12<=−3.5 RSI<=20 ret1>=0; SHORT z12>=3.5 RSI>=80 ret1<=0; rvol>=2. failed_breakout: last3 low < ll48.shift(3) then close above level LONG; last3 high > hh48.shift(3) then close below SHORT; max last3 rvol>=1.5. This includes wick sweeps without confirmed close breakout, no geometric chart patterns.
- Tuning grid 16 variants/rule/side: RVOL base or base+1, BTC flag, funding flag, CVD flag each 0/1. BTC filter LONG z12>−2/SHORT<2 (BTC series); funding filter LONG <=.0003 / SHORT >=−.0003; CVD filter cvd3 aligned. Choose highest train mean net with n>=15 and improvement >.0005 over base; otherwise base. Only breakout LONG changed (rvol3, atr1.5, funding1, BTC0, CVD0) and failed-breakout LONG changed (rvol2.5, funding1, CVD1, BTC0). All others identical base.
- Same symbol/pattern/side cooldown12 bars. Direction d=+1 LONG/−1 SHORT. Entry next bar open*(1+d*slip); TP=entry*(1+d*2*sig_h); SL=entry*(1−d*sig_h); max holding 12 bars. Same-bar collision -> SL first; SL price=SL*(1−d*slip); TP price=TP (no exit slip); timeout=last close*(1−d*slip). gross=d*(exit/entry−1), net=gross−2*fee; gross already includes modeled slippage. Fees .05%/side, slip .05%/side assumption, nominal .2% for two sides but TP lacks exit slip. No funding cashflow/leverage/fill/queue/spread. MFE/MAE per sim through exit bar, full high/low of exit bar can include post-exit moves; fw5/15/30/60/240m computed regardless exit, not realized returns. TP-before-SL rate not same as event precision.
- Precision=mean ev_hit (directional future label true at signal), baseline=share of eligible label bars, lift=precision/base. Recall=event onset preceded by any **raw** signal within 0–30m (includes onset, not actual post-cooldown alert); lead uses earliest in that window. AUC Mann–Whitney rank, PUMP or DUMP onset-offset vs normal bars excluding centered ±12 label bars; sample normal up to 40k, seed7, feature-specific missing dropped; normal not matched by coin/time regime. AUC .5 no rank discrimination; below .5 inverse association, not negative accuracy. Tags based on abs(AUC−.5)>=.10 at −240/−60m, sample<30 small. Not probability, profit or direct pump-vs-dump classification.

## C. Result details beyond existing aggregate
OOS below means combined test+extra (extra before train), ALL groups, base. CSV-derived gross and net expressed percent; TP/SL/lift/recall as original summary. No strategy validated.
|Rule/side|n|Precision %|Baseline %|Lift|Recall %|Median lead min|TP %|SL %|Gross %|Net %|PF|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|breakout L|1386|6.061|.411|14.74|4.176|25|20.996|57.143|−.150|−.250|.781|
|breakout S|1873|5.232|.531|9.846|1.52|25|23.545|53.711|−.161|−.261|.695|
|OI L|1220|5.738|.411|13.955|6.961|27.5|19.426|56.066|−.132|−.232|.788|
|OI S|1027|3.019|.531|5.68|1.52|30|18.987|51.704|−.138|−.238|.717|
|exhaust L|164|1.829|.411|4.449|1.16|15|14.024|74.39|−.269|−.369|.659|
|exhaust S|110|4.545|.531|8.554|.845|10|25.455|53.636|−.028|−.128|.914|
|failed L|12350|.421|.411|1.024|18.561|20|6.049|35.433|−.168|−.268|.585|
|failed S|9796|.623|.531|1.172|11.655|20|6.196|31.441|−.046|−.146|.774|
27,926 base OOS rows; gross−net exactly .001 fraction for all 52,455 rows. Negative gross (including modeled slip) for all eight, so subtracting recorded fees is not sole issue. Do not infer pre-all-cost gross without rerun. OOS random control n/net/lift: breakout L219/−.208%/24.357, S483/−.067%/9.887; OI L238/−.215%/9.961, S226/−.148%/5.829; exhaust L37/−.589%/0, S14/+.369%/11.762 (tiny); failed L2865/−.248%/1.034, S2135/−.126%/1.388. Controls are not fully unbiased. Train breakout S +.580% n58 vs OOS−.261%; failed L improved train+.118% n245 vs OOS−.262% n4638 (lift1.416). Breakout L improved OOS n1203 precision6.567%, lift15.972, net−.313%, worse than base−.250%. 0/16 variants meet report mechanical criterion n>=30, lift>=1.5, mean_net>0 and control lift>=1.2. Six improved variants equal base. True later TEST only 431 base rows, 2 onset events; base net by rule (n): breakout L−.851% (14), S−.473% (12), OI L−.277% (7), S−.650% (11), failed L−.605% (274), S−.155% (113); no exhaustion signals. No promotion.
Event examples from original events.csv/report (timestamp is bar open, future 1h extremes not P&L): ACE 23 Nov01:20 PUMP price .03962, +64.03/−19.69%, threshold25.87%, RVOL1316.37, RSI .907, none caught; PIEVERSE 22 Nov20:45 PUMP price2.8915 +32.35/−5.36%, threshold27.32%, RVOL23.235, RSI22.199, OI Z−6.906, none caught (rebound after prior dump); IDOL 22 Nov06:30 DUMP .036836 +1.51/−30.21%, threshold29.29%, none; AKE 20 Nov14:45 DUMP .009047 +1.93/−32.33%, threshold27.92%, OI continuation raw lead30m; BULLA 16 Nov07:40 DUMP .02694 +.37/−45.06%, RVOL .682, none; AGT 11 Nov20:55 PUMP .04127 +56.24/−10.30%, RVOL434.48, failed-breakout raw lead10m; JCT 9 Nov02:05 PUMP .013779 +54.90/−8.24%, none; INIT 10 Nov20:50 PUMP .21806 +32.07/−6.43%, OI continuation raw lead5m. Many extreme events missed. These labels are not the same as earlier fixed 5% replay.

## D. Recomputed cross-pair synchronization and direction discovery
From events.csv, group by WIB hour and type, count rows (not necessarily distinct market shocks). Counts confirmed: DUMP 9 Nov03h 85, 5 Nov21h 75, 10 Nov21h44, 20 Nov21h41; PUMP 4 Nov21h48, 23 Nov19h43, 23 Nov20h29. Extra: 356/591 dumps (60.24%) and 60/430 pumps (13.95%) in groups with >=10 same-direction events. Remove those groups -> 235 dump/370 pump. This filter uses later event labels, so retrospective diagnostic only; must use as-of breadth for live.
Median features at −60m relative to onset, extra segment, PUMP vs DUMP:
RVOL 1.464473/1.168221; ATR ratio1.114345/1.025071; BB width ratio1.337234/.998247; cvd12 −.007550/−.025042; OI Z .034241/.074991; RSI48.962234/45.207545; Kaufman .263579/.243243; trades Z .428404/.157264.
Directional AUC PUMP vs DUMP (different from original AUC against normal):
|Feature|All 1021|After exclusion 605|
|---|---:|---:|
|bbw_ratio|.619297|.510109|
|rsi14|.571365|.503565|
|rvol|.570920|.484681|
|atr_ratio|.553327|.511190|
|trades_z|.576760|.489948|
Interpretation: regime/clustering can explain apparent direction separation; no causal proof or deployable threshold. Original AUC vs normal at −60m / −15m / −5m (extra pump then dump):
|Feature|PUMP three AUCs|DUMP three AUCs|
|---|---|---|
|z1|.540/.518/.446|.462/.523/.548|
|z3|.520/.532/.491|.438/.496/.538|
|z12|.513/.537/.533|.413/.455/.499|
|rel_z12|.512/.552/.571|.544/.537/.573|
|rvol|.648/.633/.648|.565/.665/.675|
|rvol3|.648/.625/.654|.589/.672/.694|
|atr_ratio|.652/.653/.655|.606/.655/.673|
|bbw_ratio|.643/.599/.605|.518/.554/.588|
|squeeze|.624/.608/.607|.506/.514/.526|
|trades_z|.660/.633/.653|.568/.672/.681|
|cvd3|.520/.532/.509|.479/.504/.519|
|cvd12|.489/.522/.517|.465/.487/.503|
|oi_z12|.523/.543/.569|.542/.545/.549|
|rsi14|.515/.538/.522|.434/.450/.480|
|eff12|.537/.514/.547|.498/.563/.587|
|funding|.537/.532/.532|.530/.532/.532|
Anomaly vs direction must be separately validated, matched baselines and cluster-aware confidence needed.

## E. Source-code audit and conflicts
1. Segment leakage: run() builds eligibility from signal timestamp, not complete horizon. Recount base rows where exit-bar OPEN timestamp (ts+bars*5m) >= next split: train 19, extra 24 (same counts previously reported; all versions 38/41). Using exit-bar close availability >= boundary: base22/24 (all44/41); at equality with boundary preceding candle may legitimately close there, so distinguish exact conventions. Full 12-bar label horizon can cross regardless early exit; base candidates with horizon close strictly after boundary train33/extra28. Purge/embargo by maximum horizon and split strictly; fw240m can cross more. AUC onset offsets and raw signal catch can also straddle split, no guard. Do not treat these counts as corrected performance; no rerun.
2. Features are mostly causal as-of closed bar, but report ts_wib and trades.ts store OPEN time; add +5m to availability, no assumption actual execution at next open. Receipt latency unmodeled. Recall ignores cooldown, can count raw unavailable or boundary-crossing alerts; 25 zero lead events. Apply eligible emitted alerts and lead>0 in future audit.
3. Universe selection looks at 22–24 Nov including test, and prior set includes handpicked extremes. Extra predates training, not prospective; remaining-set controls biased, no matched time/market normal. OOS aggregate masks weak true test. Point-in-time listings, frozen eligibility from prior data, held-out date blocks and clustered bootstrap needed.
4. Gross includes entry/exit slip where applied; TP no exit slip, SL fills threshold even on gap (optimistic), stop first ambiguity conservative within same bar, MFE/MAE exit bar can overstate reachable path; funding absent, no actual P&L.
5. Pair-level max_runup_pct = max(high)/first open−1 (NOT trough-to-later-peak); max_dd_pct=min(low/cumulative high−1) includes same-bar high/low unknown order. Pattern category uses window extrema and endpoint, not sequential geometry; e.g. ACE main runup3% despite >64% forward rebound. Do not compare directly to early discovery ordered excursions. Pair timestamp key_ts is max-magnitude labeled onset, fallback highest-high open time (not necessarily pattern confirmation).
6. Source stores no raw candles or API response cache; no explicit missing-bar continuity validation; rolling bars may span gaps. ffill OI/funding can conceal gaps; availability count means >50% coverage per frame, pair table 100% OI ffill not every observation independently observed. Some denominators zero/inf possible despite notna checks. Funding history single call limit1000. No tick/1m/order book/liquidation/long-short/geometry/breadth in V1.
7. Research Lab V2 proposal (historical, not release gate): raw immutable cache, quality/receipt timestamps, multi-timeframe, geometric swing/pattern detection without future data, pattern-sequence and feature discovery, ablation, anomaly/direction/false-signal separation, walk-forward/holdout, event clustering, realistic fill/exit sensitivities. Big print, depth vacuum, absorption, liquidity, and actual trade order-flow remain candidates, not proved. Existing R09/R10 implementations are newer and should not be overwritten by V1. Latest operational-first directive supersedes earlier request to wait for all AI reports; no formula promotion from this study.

## F. Original CSV field dictionary
pairs: symbol, group (new_selected/prior_validation/random_control), selection_category, jenis_pola (heuristic), period_wib, net_pct, max_dd_pct, max_runup_pct, key_ts_wib, n_pump_ev/n_dump_ev, n_bars, oi_cov_pct. events: event_id, symbol, group, seg, type, ts_wib, price=onset close, fwd_max_up_pct/down_pct, thr_pct, rvol, atr_ratio, bbw_ratio, cvd12, oi_z12, z12, rsi14, funding, caught_by, best_lead_min. snapshots: event_id/type/offset_min (−240/−60/−30/−15/−5/0/+60) + 16 features as above. trades: entry, reason TP/SL/TIME, bars, gross/net/mfe/mae/fw5m/fw15m/fw30m/fw60m/fw240m (fraction, MAE positive magnitude), sym, group selected/control, seg, ts UTC open, ev_hit, pattern, side, version. summary: pattern/side/version/seg/group/n_sig/n_pair/precision/base_rate/lift/n_events/recall/lead_med_min/win_tp/sl_rate/mean_net/median_net/sum_net/pf/mfe/mae/forward horizons; return and rate fields converted to percent, lift/pf dimensionless. indicator_auc: seg/side/feature/n_event/seven AUC offsets/tag. tuning_log: pattern/side/params/n_train/mean_net_train_pct. params: args/base_params/chosen. Original CSVs have more detail than this appendix; use hashes to match exact local files.
