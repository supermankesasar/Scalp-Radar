# Formula Database — versioned parameters, not interchangeable

All numeric thresholds below are **version-specific research or implementation parameters**, not optimized profitability guarantees. Units: % are percentage points of price/return unless noted; USDT notional is quote currency.

## v0.5 / historical live signaling

- Trend/context used EMA200 (1h, 4h), EMA21, RSI14, MACD, volume, VWAP, score 0–100; read [README](../../README.md) and [v0.5 study](../../research/BACKTEST_V05_2026_REPORT.md) for exact reproduction caveats.
- Top5 = max **five simultaneous combined direction events**, not five/day; candidate with ≥1 score point advantage may replace lowest in a scanned batch.
- Minimum quote turnover **10,000,000 USDT per 24h**; closed trigger candle age ≤**8m**; price direction chase >**0.30%** rejects; adverse move >`max(0.40%, ATR5m%)` rejects.
- Target movement relative to signal baseline: `max(0.65%, 1.5 × ATR5m%)`; stop movement: `max(0.40%, ATR5m%)`. **Close-based status**, not limit/stop execution.
- 5m confirmation for "Sudah" requires subsequent closed candle; Potensi validity ≤**15m**, age ≥**8m** too late for entry; same direction cooldown **60m**; confirmed display **6h**; historical event retention **30 days**.
- RSI 15m 70–80 falling + bearish 5m + negative MACD histogram = **reversal/TP watch**, not automatic SHORT or score bonus.
- Highlights: 15m ≥2%, 1h ≥4%, 24h ≥8%, since-signal ≥2%; ticker high-move 1h ≥2%. UI labels, **not entry signals**.

## R01–R06 archived comparators

- Technical baseline B21 (EMA21/21), challenger EMA9/21, EMA9/9, EMA21/9; test trend 1h EMA50 or EMA21; momentum both/either/removal, RSI/MACD; RVOL bins `<0.85`, `0.85–<1.1`, `1.1–<1.5`, `≥1.5`; VWAP signed-distance bins 0–1, >1–3, >3 ATR. Historical discovery, not new live score.
- R06 exploratory: OI sign change + price over 15m minimum **0.1%**, account shift **0.5 percentage points**, crowd share **≥65% / ≤35%**, last realized funding abs **≥0.01%**; taker buy-share **≥55%/≤45%**, volume spike **≥1.5×**. OI and account percentages are **not** whale identity.
- R06 proxy entry next 5m open, 15/30/60m horizons, assumed round-trip cost **0.20%**; event overlap/selection bias.
- Full definitions: [technical study](../../research/TECHNICAL_FOLLOWUP_2026-11-24.md), [R06](../../research/R06_REPORT_2026-11-24.md).

## R07 (HISTORICAL experiment, live default superseded by R08)

`SCALP_V2` score components: 1h EMA200 trend **12**; 4h trend **5**; 15m EMA21 price **13**; 5m EMA9/14/21 alignment **20**; recent 1m EMA9 **or** EMA14 cross **20**; RSI14 on 5m **10**; RVOL **10** (5 at 0.85–<1.1); VWAP **5**; MACD histogram **5**. Minimum **68** + mandatory EMA alignment, cross timing, RVOL ≥**0.85**, distance to EMA14 5m 0..`max(0.75%,1.4×ATR5m%)`, signed 5m return −0.4..`max(0.4%,1.3×ATR5m%)`. LONG RSI 47–70 / SHORT 30–53. Still evaluated on 5m closes, **not a 1m scanner**. [R07](../../research/R07_SCALP_V2.md).

## R08 (CURRENT default live ranking: `R08_MULTI_CORE`)

Core weights (100): **trend/EMA/structure 15, activity/volume/trades/ATR 20, order flow/price response 20, structure/pattern 20, timing/sequence 15, RSI/VWAP 10**. Threshold **65** plus setup/trap/freshness/anti-chase gates. Example extracted R08 activity anomaly: RVOL ≥**1.5**, trade-count Z ≥**2**, or ATR ratio ≥**1.2** with candle range ≥**1.5 ATR**. R08_FULL = **0.75×core + derivative points up to 15 + market/context points up to 10**, only with fresh required inputs; **shadow/optional** not default. NO_TREND_ABLATION removes trend component, threshold **55**. 16 independently recorded hypothesis tags, not 16 independent trades. [R08](../../research/R08_MULTI.md), [implementation](../../filters/multifactor.py).

## R09 (shadow by default)

`R09_HYBRID`: **65% R08 core + up to 35% observed recent 1m microstructure**, requiring fresh flow/book agreement and R08 gates. Can be explicitly enabled; **not current default**. Twelve separate 1m rules; close-based outcome windows 15/30/60m using 1m ATR, floors 0.65% target / 0.4% stop, not actual fills. [R09](../../research/R09_WEBSOCKET.md).

## R10 (SHADOW only; do not silently promote)

13 new tags = **7 1m** (`EXHAUSTION_1M`, `SWEEP_FLIP_1M`, `ABSORPTION_CVD_1M`, `LIQUIDATION_REVERSAL_1M`, `DEPTH_FLOW_1M`, `LARGE_PRINT_FLOW_1M`, `REGIME_FLOW_1M`) + **6 5m** (`EXHAUST_SWEEP_5M`, `EXHAUST_DIVERGENCE_5M`, `SWEEP_ABSORPTION_5M`, `EXHAUST_OI_UNWIND_5M`, `OI_FLOW_BUILD_5M`, `REGIME_CONTINUATION_5M`). Source of truth: [filters/r10.py](../../filters/r10.py).
- Synchronized market regime: available current universe coverage **≥60%**, **≥20** symbols, BTC included; BULL if positive share ≥**65%** and BTC return ≥**+0.15%**; BEAR if share ≤**35%** and BTC return ≤**−0.15%**; otherwise MIXED/UNKNOWN.
- R10 exploratory 1m examples in code: flow flip thresholds ±**0.15**, opposing flow ≤−**0.30**, wick fraction ≥**0.4**, RVOL ≥**1.5**, depth ratio ≤**0.5**, one liquidation burst test ≥**10,000 USDT** and ≥**3×** opposite; these are **test hypotheses**, not independently validated thresholds.
- Outcome entry proxy: first fully future minute open after decision; horizons **15/30/60m**; fixed/wide ATR and close-based trailing, price overshoot charged; missing contiguous paths = **UNOBSERVED**. Assumed round-trip sensitivity **0.10% / 0.20% / 0.35%**. Fixed seven-day-after-table-creation holdout; no observed profitable holdout claimed. [R10 methodology](../../research/R10_RESEARCH.md).

## Early Whale Radar UI example values (ASSISTANT-CHAT; NOT active formulas)

The earlier assistant suggested demo filters of **$50k / $100k / $250k USDT trades**, timeframe **15m** or 1h, and an example BTC TP alert at $72,000 when an *illustrative* price was $70,000. These were **tutorial/demo inputs**, not optimized whale criteria, current pricing, guaranteed alert implementation, or evidence about the present Scalp Radar code.
