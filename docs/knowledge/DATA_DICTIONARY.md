# Data Dictionary — meaning, provenance, and missingness

| Term/field | Definition and correct interpretation | Source/cadence | Caveat |
|---|---|---|---|
| Pair/symbol | Binance USDⓈ-M USDT perpetual contract | `/fapi/v1/exchangeInfo`; active `TRADING` | Not spot wallet or forex; listing universe changes |
| OHLCV | Open/high/low/close and base/quote traded volume | REST / futures kline WS; 1m,5m,15m,1h,4h | Only **fully closed** contiguous bars for decisions |
| `closeTime` / cutoff | Exchange bar close timestamp in milliseconds | Kline | Do not replace with receipt or display time |
| `recorded_at` / `received_at` | Local observation/arrival timestamp | Collector/WS ledger | Needed to quantify latency and prevent hindsight |
| `decision` | When rule could actually act on received data | R10 setup ledger | Entry proxy uses first fully future minute open |
| `quoteVolume`, turnover | USDT volume; 24h turnover for liquidity gate | Kline/ticker 24h | High activity does not identify a whale |
| trade count, average size proxy | Number of trades and quote volume divided by count | Klines | Not individual trade identities |
| `takerBuyQuote` / taker delta | Aggressive buy proportion; `2*takerBuyQuote - quoteVolume` used as signed delta proxy | Futures klines | CVD/flow proxy not precise order-by-order identity |
| RVOL / Z score | Current bar quote volume vs prior-20 mean; standardized volume/trade activity | Closed 5m/1m bars | High RVOL can mean exhaustion **or** continuation |
| ATR%, EMA, RSI14, MACD, VWAP | Volatility, trend/momentum and average-volume-price features | Derived from closed candles | Warmup, timeframe and code version matter |
| OI | Open interest, aggregate outstanding contracts | Archived REST, timestamp lag | Matched longs/shorts; sign does not identify whale direction |
| Global account ratio | Share of accounts long versus short | Binance global account ratio history | **Account count**, not net notional or trade direction |
| Top trader account/position ratio | Aggregated top-account vs position orientation | REST collector | Not named wallet; stale inputs must be excluded |
| Funding | Last realized or current snapshot rate as explicitly recorded | REST archive | Last realized ≠ forecast funding; not included in realized P&L |
| `aggTrade`, large print | Exchange aggregate trade / size bucket | R09 WS | Big aggregate print ≠ verified whale |
| `depth5@500ms` | Five-level order-book snapshot | R09 WS public market | Not full order book reconstruction / cancellation proof |
| `!forceOrder@arr` | Exchange sampled liquidation event stream | R09 WS market | Missing/zero reports ≠ no liquidations |
| breadth / relative BTC | Synchronized cross-symbol rise share and relative return | R08 point-in-time archive; R10 synchronized 15m | R10 requires ≥60% of current universe, ≥20 and BTC |
| `Potensi` / `Sudah` | UI state machine before/after close-confirmed movement | `signals.py` | Neither is an executable order or realized profit |
| `UNOBSERVED` | Outcome cannot be determined with contiguous required future observations | Research ledgers | Never coerce to win, loss, or zero |
| net proxy | Directional move from entry proxy less *assumed* total cost | Offline replay/report | No actual spread/fees/funding/order slippage |
| `source`, `version`, `horizon`, `policy` | Coverage, rule reproducibility and outcome grouping | R09/R10 research tables | Multiple tags can share the **same** trade-like event |

## Timing and data boundaries

- v0.5/R01–R08 primarily use 5m decision grid and 15/30/60m follow-up, even when 1m timing is an ingredient. R09/R10 add independent **1m** closed-minute research, with separately defined ATR and outcomes; do not pool horizons blindly.
- R08 derivative/positioning inputs require known receipt and source-age **≤10m** in FULL. R09 minute candidate latency cap **15s**; stale depth/trades excluded.
- R10 distinguishes acquisition, decision, first eligible future open, outcomes, and missing paths; fixed holdout starts **7 days after table creation**, not necessarily migration date.
- In R09 gaps cannot reconstruct historical aggTrade/depth/liquidation stream from 5m OHLCV. Persisted minute summaries are **not** raw tick archives.

Primary sources: [README](../../README.md), [R08](../../research/R08_MULTI.md), [R09](../../research/R09_WEBSOCKET.md), [R10](../../research/R10_RESEARCH.md), [r10.py](../../filters/r10.py).

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## R10 additive ledger / operational telemetry
`r10_cycles`: cutoff, decision, universe, observed/fresh/ATR-ready count, regime, coverage. `r10_setups`: symbol/source/cutoff/direction unique, decision, entry_at, ATR%, context JSON, deduplicated rule/version tags, completion marker. `r10_outcomes`: setup_id/horizon/policy key, state TARGET/STOP/TRAIL/TIMEOUT/UNOBSERVED, proxy entry, gross_pct, exit_at, threshold params. `r10_meta`: fixed holdout_start (creation +7 days). R10 report groups by filter/version, source, side, regime, period, horizon/policy, symbol/day clusters; observed-only mean costs and removal of top2 contributors (descriptive). Runtime heartbeat JSON and JSONL events exported alongside SQLite when available. Keep raw exports private; never confuse ledger row count with independent trades.

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
Historical discovery RVOL uses prior20 **quote-volume median** (upper-middle approximation in earlier batches; true median batch3), distinct from current code's mean-based metric. Normalized 30m delta = sum(2*takerBuyQuote−quoteVolume)/sum(quoteVolume) over six 5m bars. Raw CVD would be cumulative signed volume, not this normalized ratio. Body/previous ATR, wick fractions, price efficiency and exact timing are defined in [appendix §D](research/EARLY_DISCOVERY_2026-11-22_24.md). Do not compare differently scaled metrics or use future OI snapshots as leading data.
