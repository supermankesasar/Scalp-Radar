# Early discovery research — detailed evidence supplement (22–24 Nov 2026 WIB)

Migration 2026-11-26. **HISTORICAL / EXPLORATORY, not active rules.** This chat contains the original analysis narrative and retained Binance connector outputs, not only the later master handoff. See [case overview](../COIN_CASE_STUDIES.md), [experiment results](../EXPERIMENT_RESULTS.md), [formulas](../FORMULA_DATABASE.md). No new market queries or rerun in this migration. Preserve current R08/R10 status. Sources: accessible chat messages/tool outputs and two uploaded external AI reports, described below. Full raw candle arrays and original screener logs were not retained as reproducible files here. Times WIB (UTC+7), 2026; pair suffix USDT, Binance USDⓈ-M perpetual unless indicated. Candle time denotes OPEN unless explicitly labelled signal availability. Prices USDT. All excursion results retrospective proxies, not executed trades.

## A. Initial problem and detailed timeline

User observed PIEVERSE fell around 17–18 WIB on 22 Nov without web signal; other selected coins moved little. Later asked for SKYAI and further PIEVERSE, then broad independent pattern discovery. Spot lookup for PIEVERSE and SKYAI returned invalid symbol (-1121) in original investigation; Futures worked. Spot-only universe, excessive 1h latency or restrictive RSI gate were proposed possible causes, **not established bugs** without the old screener logs/code. TradingCursor BINANCE PIEVERSEUSDT request invalid symbol; PIEVERSEUSDT.P retry cooldown until 23 Nov 02:12:37 UTC. Binance historical candles/OI/account ratio/funding supplied evidence instead. No TradingCursor data was incorporated.

### PIEVERSE 22 Nov — 15m candle open time / open / close / return / RVOL (where reported)
| WIB | O | C | % | RVOL × |
|---|---:|---:|---:|---:|
|13:00|3.488|3.541|1.53|3.18|
|14:00|3.554|3.603|1.38|9.41|
|14:45|3.725|3.818|2.50|4.55|
|15:00|3.820|3.941|3.17|5.16|
|15:15|3.941|4.144|5.17|8.76|
|16:15|4.359|4.787|9.82|11.76|
|16:30|4.787|5.002|4.48|6.74|
|16:45|5.003|4.938|-1.30|—|
|17:00|4.938|5.216|5.63|—|
|17:15|5.213|5.113|-1.91|—|
|17:30|5.113|4.884|-4.48|—|
|17:45|4.884|4.716|-3.42|—|
|18:00|4.718|4.629|-1.89|—|
|18:15|4.629|4.380|-5.38|—|
|18:30|4.379|4.617|5.43|—|
|18:45|4.617|4.311|-6.61|—|
|19:00|4.312|3.995|-7.35|—|
|19:15|3.993|3.844|-3.73|—|
|19:30|3.843|3.188|-17.03|—|
|19:45|3.188|3.143|-1.41|—|
|20:00|3.143|3.278|4.31|—|
|20:45|3.173|2.932|-7.61|—|
|21:00|2.932|3.050|4.02|—|
|21:15|3.050|3.626|18.87|—|

5m: 16:30 close 4.927 RSI88.5; 17:10 high5.3679 close5.216 RSI79.8 (divergence indication, not pivot-confirmed); 17:15 close5.0645 RSI70.4; 17:20 close5.0112 RSI67.4; 17:25 close5.1128 RSI70.0. 17:30 close4.9261 (-3.65%), EMA9 4.9780/EMA21 4.7699, RSI60.4, RVOL1.45; 17:45 close4.6386 (-5.02%), EMA9 4.8908/EMA21 4.7805, below previous six lows, RSI47.8, RVOL2.26, taker buy45.8%; **known 17:50**. 18:15 close4.5897 EMA9 4.7183/EMA21 4.7294 RSI45.6 (cross available18:20); 19:00 close4.1276 RSI33 RVOL1.76; 19:30 close3.5045 (-8.8%); 19:35 close3.3830 (-3.48%) RVOL4.36. Daily peak-to-subsequent-low 5.3679→2.7365 (-49.02%); low candle21:00.
OI contract/base quantity snapshots 17:30 14,284,682; 18:00 14,481,257; 19:00 14,504,507; 20:00 14,049,673; 21:00 13,337,183; 22:00 12,945,039. OI +1.54% 17:30→19:00, not a 5% rise over that interval. Account short share 17:00 66.34%, 17:30 67.28%, 18:00 70.66%, 18:30 71.32%, 19:00 70.73%, 20:00 61.14%, 21:00 60.69%. Realized funding 15:00 +.012956%, 19:00 +.048745%, 23:00 +.009692%. OI increases with falling price do not identify shorts/whales, later OI decline does not prove liquidation.

### SKYAI 22 Nov — rapid reversal, control within same coin
Day open .03550 close .03682 (+3.7%), low before high .03520, high .04493 at15:20, low .03334 at16:00; run-up27.6%, peak-to-low −25.8%. Hour14:00 +5.9% quote volume $9.35m; hour15:00 −17.9% $24.80m; hour16:00 +4.1% $18.59m.
5m 14:05 close .04045 RSI52.1 RVOL.91 taker buy43%, six-low break; 14:10 close .04003 RSI47.5 RVOL1.21 buy46.5%, false early breakdown (later higher high). 14:55 close .04318 RSI72.9 RVOL2.01; 15:00 high .04443 close .04388 RSI76.3 RVOL3.40 buy54%; 15:05 close .04301 RSI65.5 RVOL2.67 buy46.1%, no six-low break; 15:10 close .04431 RSI71.9; 15:15 close .04476 RSI73.7; 15:20 close .04463 RSI72.2 high .04493 RVOL1.30 buy50.1%; 15:25 close .04137 −7.3%, RSI47.2, EMA9 .04303 EMA21 .04218 EMA50 .04101, RVOL3.82 buy44.9%, below six lows and EMA9/21, not EMA50 (available15:30). 15:40 close .03962; 15:45 close .03762 RSI31.3 EMA9 .04096 EMA21 .04141 (available15:50); 15:55 close .03546 RSI28.4 RVOL2.86; 16:00 low .03334 close .03680.
1m 15:25 open .04462 close .04426 −.81%, RSI57, RVOL.94, buy34.3% six-low break (available15:26, watch only); 15:26 close .04439; 15:27 close .04188 −5.63%, RSI27.9 RVOL5.95 buy42.2%, known15:28; 15:29 close .04137 RVOL2.44; 15:42 close .03937 −2.09% RVOL1.97.
OI snapshots 14:00 233,152,681; 14:15 234,549,505; 14:30 234,572,882; 14:45 237,691,014; 15:00 244,488,638; 15:15 248,809,596; 15:30 243,820,252; 15:45 234,968,908; 16:00 224,103,497; 16:15 219,877,865; 16:30 217,117,753; 17:00 213,431,165; 18:00 203,873,064. 15:15→16:00 −9.93%. Funding 03:00 .006236%,07:00 .009948%,11:00 .011607%,15:00 .021949%,19:00 .005%,23:00 .005%. Account L/S 15:15 1.1286,15:30 1.0947,16:00 1.1377,16:30 1.3787. Neither these nor OI prove liquidation.

### PIEVERSE 23 Nov — repeated cycle and failed early reversal
Open3.7304; 09:05 close3.6414 RSI32.8 RVOL3.45, six-low break; 09:15 close3.5296 RSI21.9 RVOL2.73; 09:40 close3.4138 −4.86% RVOL3.47; 09:45 low3.2527 close3.2704 RSI22.3 RVOL4.50; 09:50 close3.3569 RSI31.7 RVOL3.26. 10:05 close3.5287 +5.50%, RSI47.6 RVOL2.05; 10:10 close3.6505 +3.45%, RSI55.1 RVOL2.03 MACD hist +.00215; 11:10 close3.7070 RSI60.1 EMA9 3.5606>EMA21 3.5502 (available11:15).
12:30 close3.9971 RSI75.2 RVOL5.51; 12:35 high4.0415 close4.0243 RSI76.3 RVOL2.77 MACD hist+.03210. 12:40 close3.9068 −2.92%, RSI63.1 RVOL3.34 buy45.7%, no six-low break; later higher high, hence early red candle insufficient.
13:40 high4.0575 close4.0050 RSI67.2 RVOL2.90 MACD hist−.00308 (available13:45); 13:50 close3.9071 below EMA9, RSI55; 14:00 close3.8182 RSI46.2 RVOL1.66 buy46.3%, six-low break, EMA9 3.9014/EMA21 3.8778 (available14:05); 14:10 close3.7558 RSI41.6 RVOL3.44 buy48.3%, EMA9 3.8646/EMA21 3.8647 (available14:15); later low3.4833 at15:35, −14.15% from 13:40 high. Ticker ~16:11 3.5497; rolling24h −16.721%, not same as daily return. 1m low09:49, high13:41. OI 09:45 13,080,608→13:40 12,649,763 (~−3.3%); short covering possible but not proven. Double top only a candidate until objective swing/neckline confirmation.

## B. Pair-level cohort results retained from chat

First batch 11: 5m day open-to-close %, chronological maximum drawdown %, maximum low-to-later-high run-up %. 22 Nov complete day; 23 Nov through ~16:00 (the original tool included the 16:00 candle; partial-bar ambiguity, not equivalent to exact closed cutoff). No same-candle extreme ordering inferred.
|Pair|22 ret/DD/up|23 ret/DD/up|
|---|---|---|
|PIEVERSE|19.7/-49/72.5|-4.8/-14.9/24.7|
|SKYAI|3.7/-25.8/27.6|.5/-4.6/5.3|
|ACE|1.4/-4.1/4.6|-20.1/-63.1/174.6|
|EVAA|-59.8/-62.6/49.1|23.9/-15.3/56.6|
|BULLA|35.1/-16.3/62.4|25.3/-26.5/38.9|
|BLESS|50.3/-15.3/58.4|5.9/-22.4/28.7|
|ELSA|26.7/-14.6/35.5|23.3/-9.7/33.5|
|PROM|-1/-29.3/33.9|-12.5/-16/15|
|BTC|2/-3/4.9|.5/-1.8/2.6|
|ETH|2.3/-2.6/5.2|.2/-2.2/3.3|
|DOGE|.5/-3.1/4.2|.7/-2/2.9|

Batch 2 & 3: 23 Nov 00:00–24 Nov 08:20 WIB, 388 closed 5m bars/pair. Return/DD/run-up in %, L and S = total/TP-first/SL-first/neither, no same-bar ambiguous outcomes reported. NAORIS replacement run-up not captured (—).
|Pair|ret|DD|up|L|S|
|---|---:|---:|---:|---|---|
|CYS|41.6|-11.9|53|4/2/2/0|2/0/1/1|
|ARIA|25.6|-33.9|48|9/3/4/2|4/1/3/0|
|AIOT|26|-11.3|40.2|2/2/0/0|2/0/2/0|
|MUBARAK|26.7|-6.2|34.9|4/1/2/1|0/0/0/0|
|FLOCK|-.6|-25.2|25.9|1/0/1/0|1/0/1/0|
|CROSS|-15.5|-23.9|11.2|0/0/0/0|3/0/1/2|
|ICNT|-12.3|-19.2|6.6|0/0/0/0|1/0/1/0|
|TRX|1.9|-1.1|2.9|0/0/0/0|0/0/0/0|
|BNB|.05|-5.6|6.6|0/0/0/0|0/0/0/0|
|NAORIS|-13.8|-20.5|—|0/0/0/0|2/0/0/2|
|INX|17.56|-15.27|37.42|3/0/1/2|0/0/0/0|
|LISTA|37.05|-10.96|42.86|2/0/0/2|2/0/2/0|
|AVAAI|31.48|-7.83|35.21|1/0/1/0|2/0/0/2|
|DOS|-8.59|-23.88|22.76|1/0/1/0|1/0/1/0|
|LIGHT|12.64|-12.84|30.51|2/0/2/0|1/0/1/0|
|APR|23.35|-8.28|29.54|1/0/0/1|1/0/1/0|
|AKE|-10.8|-32.71|26.65|2/1/0/1|3/0/3/0|
|SKY|-4.37|-14.27|26.01|4/2/0/2|1/0/1/0|
|MMT|-3.62|-20.11|16.3|0/0/0/0|3/0/0/3|
|AIN|-4.2|-19.4|19.61|3/0/2/1|2/1/0/1|
|IRYS|-14.74|-16.65|4.72|0/0/0/0|0/0/0/0|
|ENSO|-9.09|-17.18|8.92|0/0/0/0|0/0/0/0|
|AGT|-3.63|-13.06|10.89|1/0/0/1|1/0/0/1|
|BMT|-3.59|-11.55|9.63|0/0/0/0|0/0/0/0|
|MON|-11.86|-15.25|15.32|0/0/0/0|1/0/0/1|
|HMSTR|2.9|-3.51|5.14|0/0/0/0|0/0/0/0|
|HOT|-1.51|-4.91|5.33|0/0/0/0|0/0/0/0|
|BARD|-1.35|-5.43|4.69|0/0/0/0|0/0/0/0|
|SOL|2.41|-8.85|12.4|0/0/0/0|0/0/0/0|
|ASTER|-.02|-7.28|9.32|0/0/0/0|0/0/0/0|

SKDD initially ret−33.9/DD−42/up24.4; L 3/0/2/1 S 3/0/1/2; excluded on exchangeInfo underlyingType EQUITY/contractType TRADIFI_PERPETUAL. Initial mixed aggregate L23/8/11/4, S16/1/10/5 superseded by corrected crypto-only aggregate in main KB. Initial filter subgroup stats **include SKDD**, not corrected; do not pool. 
Four extra pairs (same 388 bars): NIGHT ret−1.93/DD−9.64/up9.12; XRP 2.05/−9.04/12.43; LTC 4.34/−6.27/10.36; ADA 3.38/−6.46/10.30.

## C. Additional counterexamples and ablations
Batch1 replay SHORT candidate at candle open timestamp (available +5m), next 12 bars favorable/adverse excursion %, not TP/SL first. Selected results:
|Pair/date/time|favorable|adverse|
|---|---:|---:|
|PIEVERSE 22 17:45|6.2|2.8|
|PIEVERSE 22 19:00|26|1.4|
|PIEVERSE 22 20:45|5.4|32.4|
|PIEVERSE 22 23:40|.4|10.4|
|PIEVERSE 23 09:45|.1|12.4|
|PIEVERSE 23 14:00|7.9|1|
|SKYAI 22 13:00|.1|8.2|
|SKYAI 22 15:25|19.4|.8|
|ACE 23 01:00|56|5.8|
|EVAA 23 12:15|.1|25.3|
|PROM 22 22:55|17.6|10.3|
|BULLA 23 00:20|.1|21.7|
|BLESS 22 20:05|.7|22.1|
|ELSA 23 14:50|2|10.5|
Raw/dedup alerts (60m cooldown): PIEVERSE11/6, SKYAI5/2, ACE8/4, EVAA19/9, PROM5/2, BULLA11/8, BLESS13/7, ELSA6/5; BTC/ETH/DOGE zero. No independent signal recall measured.
Batch2 ARIA 20:40 SHORT favorable9.65 adverse6.37, **SL first**, OI previous1h+.85%; ARIA18:40 OI+.98% yet failed. CYS23:30 OI previous1h+3.49%, subsequent1h+29.3% (future only). AIOT21:10 OI preceding1h+.31%; FLOCK21:15 OI+43.01% preceding1h, RVOL368.48, RSI90, MFE3.82/MAE7.92, SL first. NAORIS SHORT 23:35 RVOL3.57 RSI26.2 buy41.3%, MFE1.31/MAE.97; 24 Nov00:50 RVOL1.74 RSI29.5 buy31.4%, MFE1.08/MAE1.02; neither reached targets.
Batch3 additional cases: AKE 23 Nov09:25 SHORT RVOL8.66 RSI20.16 delta30m−16.33%, OI1h−1.39%, MFE.08/MAE15.05 SL first; 09:55 LONG RVOL2.95 RSI51.96 delta−1%, OI1h−1.41%, MFE9.11/MAE.19 TP first. LIGHT21:30 LONG RSI94.2 RVOL34.87 delta+11.52%, OI1h+1.27%, MFE5.96/MAE3.73 **SL first**, even though later target reached. AIN20:50 LONG MFE1.25/MAE11.5 SL first; 21:10 SHORT TP first. SKY20:40 SHORT SL first; 21:00 LONG TP first.
Batch3 ablations (not optimized, n/TP/SL/neither):
|Filter|L|S|
|---|---|---|
|CVD30m aligned|15/1/5/9|18/1/9/8|
|CVD aligned magnitude ≥5%|11/0/4/7|17/1/9/7|
|EMA9/21 alignment|15/0/6/9|14/1/8/5|
|RVOL≥2|15/3/6/6|13/1/8/4|
|Body/previous ATR≥1.5|7/3/2/2|8/1/5/2|
Only 3 LONG TP-first; median RSI57.48, RVOL4.10, delta−.59%, body/ATR2.35, 0/3 EMA9>21. 7 LONG SL-first median RSI75.06 RVOL3.07 delta+5.46%, body/ATR.57, 6/7 EMA9>21. Only one SHORT TP-first, no statistical claim. High signed flow and trend alignment may be late/continuation rather than pre-reversal indicators.
620 hourly snapshots (31/pair): extra medians UP/DOWN/FLAT: prior60m return .89%/1.39%/−.07%; 30m volume ratio1.50/1.34/1.02; price efficiency .59%/.68%/.33%; MACD hist/price .11%/.17%/0%; body/ATR .35/.41/.30; EMA9>21 counts6/11,7/8,139/374. 227 mid group median RSI50.57 RVOL.93 ATR%.83 delta−3.65%, prior30m−.06%; no stable direction inference.

## D. Exact historical calculations, caveats and rejected proposals
- 5m closed decision: prior48-bar max high/min low−1≥.10 (range **not ordered pump**); break close beyond prior6 bars, prior20 quote volume RVOL≥1.5, RSI14 <50 short/>50 long, price vs EMA9, current taker buy fraction <.5 or >.5 respectively. No OI requirement. Dedup ≥60m per symbol/direction. Original batches 1/2 used upper-middle prior20 sorted element, batch3 true even median; **not exact parity**. Use matched recomputation before pooled evaluation.
- RSI Wilder14, EMA9/21/12/26, MACD EMA9 signal; ATR Wilder14; body/previous ATR. CVD proxy 30m = sum(2*takerBuyQuote−quoteVolume) over latest six bars / sum(quoteVolume), dimensionless signed fraction; multiply by100 for %. Not full trade-tick CVD. 30m volume ratio = sum quote volume/(6×prior20 median), efficiency = abs(close/close6barsAgo−1)/that ratio; wick fractions = upper/lower wick divided by range. ATR% denominator current bar open; prior ATR excludes current bar. MACD hist/close normalized. Some snapshots include current candle in the rolling reference for 30m ratio; use same definition in any reproduction. Batch3 OI queried only for selected cases due tool-call limit; wick calculated but no aggregate outcome stratification reported.
- Outcome entry = signal candle close (optimistic proxy), next 12 bars, TP5% / SL3%, first touched via high/low, same bar both = ambiguous, neither recorded separately. No fees/slippage/leverage/funding or realistic fill. MFE/MAE full next hour may exceed stop. No forward test in original chat.
- External AI indicator proposal reviewed earlier: RSI14 cross 30/70 or divergence; MACD12/26/9; EMA20/50 or 9/20 vs50/200; Bollinger20,2 bandwidth below 15th percentile prior100 and volume>2×SMA20; middle-band bearish cross; approximate Volume Profile30 bins VAH/VAL breakout volume>1.5×SMA20; OBV vs MA20 and >3% change, divergence vs prior5; OI >5% 1h/4h with price ±2%. All **unvalidated suggestions**, not imported code. OBV percentage near zero unstable; OHLCV VP only proxy. Funding proposal had contradictory raw thresholds .03/.08 vs written .05%; use decimal .0005 for .05%; funding interval varies; no adopted rule. RSI70 exit alone is not short, EMA20/50 can lag. 
- Historical proposed alerts Pump Watch→Exhaustion/Reversal Watch→confirmed candidate→reset/invalidation, separate anomaly, direction and timing. User wanted research first then, not added UI; latest operational-first directive supersedes coding gate. No evidence original UI implemented any of these alert states at that point.

## E. External reports supplied in this chat (secondary evidence)
Attachments: Pasted text.txt (RESEARCH HANDOFF REPORT, 268 displayed lines) and Pasted markdown.md (illustrative backtest, 123 displayed lines). Both accessible in migration. Model name unspecified in report; **do not attribute to Claude**. First report 9 pairs, not 50, no raw OHLCV, biased toward upward events. References EdgeDepth event archive and CoinGraph briefs, public media; no independent source verification in this migration. Reported BLESS baseline .012569→.020346→.015528 (+61.9%, +23.5% net), OI+11.6%, short/long liquidation $1.6m/$1.2m, climax$2.5m, double-bottom proprietary confidence93%; ARIA big-print percentile .9926, PIEVERSE .9851, 21 markers and claimed sustained book imbalance ≥50% 15m; NIGHT OI USD +6.71% to$11.58m then $10.4m; reported 30 liquidations $59.4k mainly short. XRP .94→1.02→.984, reported short/long liquidation ratio 578% at peak, $9.45m 24h total. LTC/ADA/SOL reported peak +6.7/+7.6/+8.5%, net +1.3/+1.9/+1%; all different event windows from our fixed cohort, not direct discrepancies. Public source precision unknown.
Big print definition reportedly single trade threshold $25k small caps to $200k BTC, 15m share percentile≥98 over14d, 13.3% event probability vs ~4.75% matched baseline (claimed lift2.8×), 53% up first/47% down; not verified. Not direction accuracy; volatility hypothesis only. Thin book below 30-day depth p10, sustained imbalance, liquidation cascade and cross-sectional breadth are suggestions. Claimed absence of spot demand, squeeze causality, short buildup and absorption **not demonstrated**. MFE/MAE misuse: BLESS peak-to-end ~−23.7%, not −38.1%; ARIA normalized peak-to-end (0.975/1.299−1) ~−24.9%, not −32.4%; not necessarily maximum drawdown. Second report counts 5 squeeze examples with peak>5% and 2 end>5%, no tested signal timestamp or funding; entry at baseline and exit peak are hindsight, not backtest precision. Big-print examples two, no fixed direction forecast; 1/2 cannot be called directional precision. Claim of Sharpe−.28 for short peak/retracement edge not independently verified.
Our separate replay: 15m OHLCV, OI quantity, last realized funding as of decision; 201 eligible timestamps per BLESS/PIEVERSE/NIGHT/XRP/LTC (1005), 22 Nov–24 Nov cutoff08:20, 1h follow-up. Operationalization funding≤+.005%, abs(price6h return)≤3%, OI6h≥5%, dedup1h. Only NIGHT 2 signals: 23 Nov02:30 funding+.00116%, OI+6.80%, price+1.19%, next1h max+.41%, min−1.08%, close+.02%; 05:00 funding+.005%, OI+5.05%, price+2.03%, max+1.46%, min−.49%, close+1.10%. Zero ≥5% next1h. PIEVERSE funding positive throughout this fetch (min+.005208%, max+.048745%). Rule fails initial test, no general rejection of squeeze mechanisms.
Research prompts requested independent methods (not same indicator definitions), 50 new pairs per Gemini/DeepSeek/Claude, explicit sources and evidence, controls, temporal split, no fabricated data, handoff A–I including metadata, pair/events, recurring patterns, indicator evaluation, contradictions, recommendations, machine-readable data, summary. User corrected assistant: **do not impose same indicator definitions; independently discover data/patterns**, only normalize metadata on ingestion. Chart pattern addition discussed but user did not want to rush other AIs; algorithmic OHLCV detection without AI vision, no frontend panel. No evidence additional 50-pair reports received in this specific chat. 
