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

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Historical handoff experiments (not live)
22–24 Nov initial rule: 4h range ≥10%, break of previous six candles, RVOL≥1.5×, RSI>50 LONG/<50 SHORT, price vs EMA9 and taker flow aligned. TP5%, SL3%, horizon1h, same-direction cooldown1h; no fees/leverage. Rejected as inconsistent; see results. Squeeze fuel: funding≤+.005%, OI6h≥+5%, price6h within ±3%; failed initial test.
R10 exact exit policy (verified code at R10 implementation; a=source ATR in price percent): FIXED target max(.65,1.5a), stop max(.4,a); ATR_WIDE target max(.8,2a), stop max(.45,1.25a); ATR_TRAIL target max(1,3a), stop max(.4,a), trail after favorable close peak ≥max(.5,a), distance max(.25,.75a). Evaluate close overshoot at actual close, not threshold. Entry strictly future minute boundary after actual decision. Nine outcome combinations per setup; cost sensitivity computed on same outcomes, not 27 independent trades. Source [research_r10.py](../../research_r10.py).
R10 1m fresh decision cap15s, contiguous 61 bars for ATR, 5m decision cap300s. Exhaustion requires opposing 15m move ≥max(1%,3a), wick≥.4, sweep or flow flip, RVOL≥1.5. Sweep/flip uses ±.15; absorption requires opposing flow≤−.30, body/range≤.35 and preceding opposing flow≥.15 magnitude, wick≥.4, RVOL≥1.5. Liquidity reversal opposite-side liquidation≥10k USDT and≥3× other + sweep/exhaustion. Pressure requires aligned flow≥.20 and book≥.15; large print ≥ dynamic threshold; depth ratio≤.5. Exact signs and conditions in [r10.py](../../filters/r10.py); no claim optimal.

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
The [original discovery appendix §D](research/EARLY_DISCOVERY_2026-11-22_24.md#d-exact-historical-calculations-caveats-and-rejected-proposals) records exact historic RVOL median convention differences, normalized delta, ATR/efficiency/wick formulas, entry/exit proxy and unadopted RSI/MACD/BB/VP/OBV/funding/OI proposals. These are historical experimental rules, not R08/R10 active parameters.

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## Claude Research Lab V1 (historical, no promotion)
[Exact source-derived formula registry](research/CLAUDE_V1_ARTIFACT_AUDIT.md#b-exact-v1-calculations-source-functions-feat-add_labels-signals-sim_one-run-auc_table) records 288-bar volatility and RVOL references, normalized CVD, OI/funding alignment, four base rules, tuning grid, TP/SL as 2×/1× sigma, slippage, label and recall semantics. These are separate from early median20 and R08 mean20 and from R10 exit policies. All base/improved variants failed combined OOS criterion; do not substitute them for live filters.

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## Historical V0.5 Scalp/Swing feature branch (UNMERGED; not current R08/R10)

Exact code verified at feature commit `7e404b84`. [Detailed weight/gate/threshold tables](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md#c-feature-branch-formula-database-not-active-main).

| Profile | Closed-candle timeframes | 100-point scoring components | Additional gates | Pending / TP / SL |
| --- | --- | --- | --- | --- |
| Scalping | **1m/5m/15m/1h** | 1h trend EMA200 **24**, 15m EMA200 **12** (MIXED=5), 5m EMA21 **14**, 1m EMA21 **11**, 1m MACD hist **10**, RSI14 5m **10**, RVOL 1m **11** (partial=6), VWAP 5m **8** | Score≥68 default; directional trend, 1m EMA21 distance and 1m return/chase bands; 24h price change **excluded** (but 24h turnover used for TOP80/liquidity) | **15m** / max(**0.65%**,1.5×ATR5m%) / max(**0.40%**,ATR5m%); closed 1m event outcomes |
| Swing | **15m/1h/4h/8h/1d/1w** | 1w EMA21 trend **16**, 1d EMA200 **20**, 8h EMA200 **12**, 4h EMA200 **12**, 1h EMA21 **11**, 15m MACD hist **10**, RSI14 1h **10**, RVOL15m **9** (partial=4) | Score≥68 default; weekly+daily regime; 1h EMA21 distance; 24h price-change *sign* confirmation LONG>0, SHORT<0 (not weighted) | **3d** experimental / max(**2%**,1.5×ATR1d%) / max(**1%**,ATR1d%); closed 1h outcomes |

Editable persisted keys/defaults on branch: `rsi_watch_threshold=70`, `rsi_warning_long=60` (**RSI>60**, Potensi Naik), `rsi_warning_short=40` (**RSI<40**, Potensi Turun), `rsi_long_max=70`, `min_score=68`, `volume_full_score_min=1.10`, `max_chase_pct=0.30%`. Warning badge **does not** change score, signal eligibility, targets or actual orders. RSI watch/reversal70 is separate. **SHORT 40** was the assistant's interpretation of user's "sebaliknya"; no threshold research supports the value. The 3m and earlier UI-only Intraday variants are **SUPERSEDED**. All values are branch-only, not R08/R10 production formulas.

<!-- migration-note:2026-11-26-r01-r06-modular-overnight-chat -->
## Exact original v0.5 control (historical, old app.py c23da9bc)
Weights: EMA200 1h trend24, EMA200 4h trend12 (MIXED5), 15m EMA21 price14, 5m EMA21 price11, MACD histogram5m10, RSI14 15m10 (LONG47–70 / SHORT30–53), RVOL5m11 if ≥1.1 else6 if ≥.85 else0, UTC daily VWAP side8. Total max100; threshold68; trend1h must align and 4h not opposite. Signed 15m EMA distance 0..max(.75%,1.4×ATR5m%); signed ret15 −.4..max(.4%,1.3×ATR5m%). EMA200 direction requires price side and slope vs six bars earlier. RVOL uses mean previous20 quote-volume bars; VWAP typical price×base volume. This is NOT feature branch Scalp/Swing or R08. Separate EMA9-cross and EMA21 prior-line touch/rejection; 1h EMA21 challenger requires price>EMA>EMA six bars earlier (reverse SHORT). See [R01–R06 appendix](research/R01_R06_MODULAR_OVERNIGHT_CHAT_2026-11-24.md). Draft whale25/volume20/accumulation20/trend15/momentum10/anti-FOMO10, subjective 95/95/65/30 ratings, 50:50 rule/realtime and 40:20:20:20 scoring were **unadopted/withdrawn**, not measured accuracy or active rules.
