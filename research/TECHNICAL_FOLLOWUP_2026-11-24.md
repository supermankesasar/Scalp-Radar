# Scalp Radar — technical follow-up, 24 November 2026
Baseline production app.py blob c23da9bc542714ec40206ea3f54ad89c65dbc99d. Replay engine commit 24120473f032d3e99435d0f7b5ba698d9ae7ce2d. Binance USD-M historical klines and global account ratio via connector. Production main untouched.

## Scope
28 pair (8 old + 20 additional), eight two-hour windows Nov 23–24, 2026, 2,688 5m screening points (2,649 with rolling turnover >=10M USDT), 1,078 unique pair/time/direction snapshots across variants. All candidates recorded; 15/30/60m outcomes. End windows UTC: 23 Nov 04:00,08:00,12:00,16:00,20:00; 24 Nov 00:00,04:00,08:00. 08:00 windows reproduce earlier R01–R05. Results are exploratory with correlated observations, not independent trades. First episodes reset per window and variant; strata use first original B21 episode, not first transition into a stratum. Outcome close 5m target=max(0.65%,1.5*ATR%), stop=max(0.40%,ATR%), next-open reference, assumed 0.20% round-trip. Gross endpoint separately measured. No production latency/fill simulation.

## Main comparisons (net proxy % per candidate, 30m)
| Variant | All n | All net | First n | First net |
|---|---:|---:|---:|---:|
| B21 original |623|-0.0412|142|-0.0260|
| 9/21 |618|-0.0427|143|-0.0257|
| 9/9 |965|-0.0259|233|-0.0825|
|21/9|971|-0.0254|233|-0.0821|
|EMA15 score only 9|622|-0.0404|141|-0.0222|
|EMA15 distance gate only 9|869|-0.0196|211|-0.0680|
|Trend 1h score only|641|-0.0354|156|-0.0217|
|Trend 1h allow mixed|628|-0.0372|145|-0.0204|
|No 1h score/gate|694|-0.0351|176|-0.0398|
|EMA50 1h|157|+0.0591|34|-0.0108|
|EMA21 1h|176|+0.1065|44|+0.1593|
|Remove RSI + MACD score|617|-0.0412|145|-0.0323|
|Require both|512|-0.0639|130|-0.0946|
|Require either|623|-0.0412|142|-0.0260|
|Both + accelerating|181|-0.0805|112|-0.0816|
|9/9 + EMA9 cross 5m|89|+0.0482|89|+0.0482|
|9/9 + EMA9 touch 5m|206|+0.0324|145|+0.0016|
|9/9 + EMA21 touch 5m|95|+0.0848|77|+0.0360|
|9/9 + EMA21 cross 5m|46|-0.0740|46|-0.0740|

EMA21 1h first episodes old/new: +0.0465% (16) / +0.2238% (28). Explore -0.3602% (10), later timecheck +0.4097% (25); not a validated replacement. EMA9 cross within 9/9 setup explore +0.0075% (54), timecheck +0.3289% (20), anchors -0.1795% (15). EMA21 touch and EMA9 cross are separate entry-timing hypotheses. Do not remove EMA21 or change weights.

## Relative volume / VWAP / account ratio: first B21 episodes (n=142)
| Feature | n | Net % |
|---|---:|---:|
|RVOL <0.85|78|-0.0953|
|RVOL 0.85–<1.1|23|+0.1328|
|RVOL 1.1–<1.5|27|-0.0166|
|RVOL >=1.5|14|+0.0812|
|VWAP opposite direction|45|-0.0384|
|VWAP aligned, 0–1 ATR|36|+0.0665|
|VWAP aligned, >1–3 ATR|53|-0.1022|
|VWAP aligned, >3 ATR|8|+0.1324|
|RVOL 0.85–<1.1 + VWAP aligned 0–1 ATR|7|+0.2422|
|Long/short account share aligned with signal|11|+0.2991|
|Account share opposed|131|-0.0533|
|Account share 45–55%|39|+0.0599|
|Account share 15m change aligned|71|-0.0207|
|Account share 15m change opposed|67|-0.0483|

All 623 original candidate snapshots have timestamp-lagged ratio coverage; 588 are opposed. In old 8 pair, all 243 baseline snapshots are opposed, making absolute alignment heavily confounded by cohort and direction. A ratio measures account count/share, not actual position notional, and total futures contracts have matched long/short sides. Do not infer whale activity from global account ratio. Ratio is context/shadow feature only. R06 can separately evaluate top trader accounts/positions, OI, taker buy/sell, funding, liquidation; no scores assigned.

## Decisions
1. Preserve v0.5 control. Research EMA21 1h, EMA9 price cross / EMA21 pullback with 9/9 setup as timing challengers; keep 4h filter fixed.
2. RSI and MACD are phase/context, not mandatory both. No weight change.
3. RVOL normal versus spike is context, not directional evidence. VWAP distance and side, not mere above/below; joint RVOL+VWAP hypothesis only seven first signals, not production-ready.
4. Record all candidate outcomes independent of display rank. Keep 15/30m validity research and 60m observation; do not call close-based outcomes actual trade PnL.
5. Need more separated time windows and forward testing; no independent robust holdout. R06 not started except account-ratio pilot.
6. Research branch only. Core replay executed on connector data, standalone CLI syntax checked, offline future-data isolation fixture checked. HTTP runner on hosting not verified. Raw connector candles not committed; dated candidate feature/outcome snapshots and aggregate files are committed, future CLI stores raw data + checksums locally.

Results: technical_2026-11-24_summary.json, technical_2026-11-24_strata.json, six batch JSONs in research/results.
