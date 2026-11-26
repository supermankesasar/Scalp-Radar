# Historical feature-branch discussion: V0.5 Scalping / Swing, RSI alarms, coin logos, signal journaling, desktop options

**Migrated 2026-11-26. Original chat mainly around 2026-11-22–25 WIB; exact per-message timestamps were not recoverable.**

**Provenance:** USER-CHAT (user decisions), ASSISTANT-CHAT (assistant recommendation/interpretation), VERIFIED-FEATURE (read directly from the GitHub feature branch on 2026-11-26), CURRENT-MAIN (compared with main). No new market research was run. All implementation details in this appendix refer to `feature/v05-data-backtest-oneclick` as read at commit [`7e404b84`](https://github.com/supermankesasar/Scalp-Radar/commit/7e404b84e9f5038559ce792f4338ddac9432e307), **not** main. Main at migration start [`3d5f55fc`](https://github.com/supermankesasar/Scalp-Radar/commit/3d5f55fcaf2c203f4024e370c50f3f06cb51e998) contains newer **R08 default + R09/R10 research**. Older PR #1 was reported closed without merge in the existing KB. Do not apply this feature branch's defaults to main.

## A. Context, problem and research standard

- User is a novice programmer/trader and wants a practical Windows one-click local scanner rather than handling source code. Existing starter: `START-WINDOWS.bat`, local web on `127.0.0.1:8765`, Binance USD-M Futures public feed, Python + SQLite, **read-only, no account trading/order execution**.
- User wanted a watchlist that distinguishes **Potensi Naik / Sudah Naik / Potensi Turun / Sudah Turun**. **Sudah** requires a prior stored potential event and a subsequent *closed candle* reaching the target; neither category proves a realized trade.
- Strong motivation to monitor quick price changes without chasing a move already far advanced. User asked for manual indicator thresholds (including RSI default 70), default in panel, and plain UI.
- Core v0.5 scoring (historical, pre-profile separation) used EMA200 1h (24 points), EMA200 4h (12), EMA21 15m (14), EMA21 5m (11), MACD histogram 5m (10), RSI 15m (10), relative volume 5m (11) and UTC VWAP (8): **100 maximum**. Minimum score 68; quote-turnover floor 10M USDT/24h at promotion; anti-chase 0.30%; target=max(0.65%,1.5×ATR5m%), stop=max(0.40%,ATR5m%), horizon ~15m. Scoring is *heuristic*, not probability.
- v0.5 exploratory audit from [original report](../../../research/BACKTEST_V05_2026_REPORT.md) had **2,950 events, mean net −0.1932%** after assumed 0.20% round-trip cost. This was an earlier version, not an empirical test of new Scalping/Swing rules. Existing [EXPERIMENT_RESULTS](../EXPERIMENT_RESULTS.md) preserves full denominators/caveats.

## B. Requirement and implementation sequence (historical; not R10 release log)

| Sequence | User request/decision | Feature-branch implementation and caveat | Provenance |
| --- | --- | --- | --- |
| 1 | RSI 70 alarm and thresholds editable manually | `indicator_settings.py` persists settings with revisions; `indicator_ui.js` save/reset; local-only API writes; reversal **watch**, not standalone SHORT | USER-CHAT + VERIFIED-FEATURE |
| 2 | Split existing web into Scalping and Intraday; remove 24h movement from Scalping but include in second mode | Initial **UI-filter-only** proposal: 24h price change >0 confirms LONG, <0 confirms SHORT in Intraday. It was not a weighted 24h score. Both tabs originally shared events; explicitly recognized insufficient to compare two strategies. **SUPERSEDED** by independent engines | USER-CHAT + ASSISTANT-CHAT |
| 3 | Make Scalping quicker; first requested 1m/3m/5m/15m/1h, later corrected to **1m/5m/15m/1h** | Dedicated `scalp_engine.py`, closed 1m event outcome, only four requested candle intervals; 3m removed. **Final user choice** supersedes earlier five-timeframe proposal | USER-CHAT + VERIFIED-FEATURE |
| 4 | Longer horizon called **Swing**: **15m/1h/4h/8h/1d/1w** | `swing_engine.py` with independent 1h-close monitoring, approximate 3-day pending window and separate DB; **Intraday** tab label superseded. Swing profile is experimental and not backtested | USER-CHAT + VERIFIED-FEATURE |
| 5 | Clarify "80 pair" in web | TOP80 = **universe selection before indicator filters**, 80 highest reported USDT 24h quote-turnover tickers, not 80 passing signals. Tracked active-event symbols may be appended beyond cut. LIQUID minimum $10M/$30M/$100M; ALL PAIRS all eligible USDT perps. TOP80 is **feature-branch default** for lighter REST scanning; main default may differ | USER-CHAT + VERIFIED-FEATURE |
| 6 | Add coin icons | `coin_logos.js` loads public `spothq/cryptocurrency-icons` via jsDelivr, lazy loading, initials fallback, quantity-prefix handling; used in rows/high movers/detail/history. Visual only, no data confidence | USER-CHAT + VERIFIED-FEATURE |
| 7 | Display warning even when a signal is already "Potensi Naik" with RSI >60, and symmetrical warning in "Potensi Turun" | Assistant interpreted symmetry as **RSI <40** for SHORT. Added editable `rsi_warning_long=60`, `rsi_warning_short=40`; strict comparisons (> / <), 5m RSI on Scalping and 1h RSI on Swing; separate from RSI reversal watch 70. User explicitly said >60 for LONG, but **<40 is the assistant's interpretation**; user did not separately spell out 40 | USER-CHAT / ASSISTANT interpretation / VERIFIED-FEATURE |
| 8 | What if radar signal fails or no longer follows criteria? | Existing event statuses reviewed; recommendation to preserve failures and separate **indicator invalidation** from **price outcome**. Proposed Signal Journal for event-time snapshots, changed conditions, reasons and terminal results. **NOT IMPLEMENTED** in this chat | USER-CHAT + ASSISTANT-CHAT |
| 9 | What if desktop application, not browser? **"jangan di buat langsung, kita bahas dulu"** | Three options discussed: native desktop, web UI wrapped as desktop, and completely rewritten PySide6; assistant recommended **packaging existing web** for least disruption. No selection or code change. Future tray/sound/Windows notifications/autostart/update suggestions remain ideas | USER-CHAT + ASSISTANT-CHAT |

## C. Feature-branch formula database (not active main)

All following rules are from the **historical branch** sources, not today's R08 ranking logic. `scan_symbol` uses closed candles; the functions and filenames are preserved for reproducibility.

### C1. Scalping `scalp_engine.py`

**Candle requests:** 1m 260; 5m 310; 15m 230; 1h 230. Minimum **220 closed candles each**. Trend: EMA200 `regime` on 1h and 15m. Scores separately for LONG and SHORT:

| Component | Points / condition |
| --- | --- |
| 1h trend | 24 if aligned |
| 15m trend | 12 if aligned; 5 if mixed |
| 5m close vs EMA21 | 14 if directional alignment |
| 1m close vs EMA21 | 11 if aligned |
| 1m MACD histogram | 10 if aligned |
| 5m RSI14 | 10 if LONG RSI ∈[47,`rsi_long_max`], or SHORT RSI ∈[30,53] |
| 1m relative volume | 11 if ≥ `volume_full_score_min`; 6 if ≥0.85 |
| 5m UTC VWAP | 8 if close on directional side |

Minimum `min_score` default **68**; `atr1pct=100×ATR14(1m)/close1m`; `atr5pct=100×ATR14(5m)/close5m`; `dist1=100×(close1m/EMA21(1m)−1)`; `ret1=100×(close1m/previous1m_close−1)`; `distance_limit=max(0.45%,1.4×atr1pct)`.

- LONG potential if trend1h=BULLISH, trend15m≠BEARISH, score≥min, `0≤dist1≤distance_limit`, `−0.25%≤ret1≤max(0.25%,1.4×atr1pct)`.
- SHORT potential if trend1h=BEARISH, trend15m≠BULLISH, score≥min, `−distance_limit≤dist1≤0`, `−max(0.25%,1.4×atr1pct)≤ret1≤0.25%`.
- `pct24h=None` as displayed directional metric, **not** part of scoring, yet 24h turnover persists for universe/liquidity ranking; tickers are fetched from the 24h endpoint for discovery.
- 1m candle-close state tracking, pending horizon **15m**, cooldown **60m**, display REACHED **6h**. Indicative TP=max(0.65%,1.5×ATR5m%), SL=max(0.40%,ATR5m%). One can miss short-lived moves because full-market scan runs in batches; quote polling is not a guaranteed instant entry.

### C2. Swing `swing_engine.py`

**Candle requests:** 15m 260; 1h/4h/8h/1d 250 each; 1w 80. Minimum **220 closed** for nonweekly and **30** for weekly. Weekly trend via EMA21 slope (last vs seven weeks prior) and last close, **not** EMA200(1w). Daily/8h/4h regime uses EMA200.

| Component | Points / condition |
| --- | --- |
| 1w EMA21 regime | 16 if aligned |
| 1d EMA200 regime | 20 if aligned |
| 8h EMA200 regime | 12 if aligned |
| 4h EMA200 regime | 12 if aligned |
| 1h close vs EMA21 | 11 if aligned |
| 15m MACD histogram | 10 if aligned |
| 1h RSI14 | 10 if LONG RSI ∈[47,`rsi_long_max`], SHORT ∈[30,53] |
| 15m relative volume | 9 if ≥`volume_full_score_min`; 4 if ≥0.85 |

- 24h **price change is an extra directional gate**, **not points**: `change24h>0` for LONG; `change24h<0` for SHORT. Valid finite numeric value required.
- LONG potential: weekly and daily BULLISH, score≥68(default), 24h positive, distance of 1h close from EMA21 within `0..max(2.5%,1.4×ATR1d%)`.
- SHORT: weekly and daily BEARISH, score≥68(default), 24h negative, signed 1h distance from EMA21 in `−max(2.5%,1.4×ATR1d%)..0`.
- TP=max(2.0%,1.5×ATR1d%); SL=max(1.0%,ATR1d%); monitored on **1h close**; **3-day PENDING**, 7-day REACHED display, 24h same-direction cooldown; all are exploratory assumptions, not validated profitability.
- Missing enough 1w history yields an analysis error for that pair, not fabricated candles.

### C3. Persisted manual configuration `indicator_settings.py`

| Key | Default | Allowed (feature branch) | Function |
| --- | ---: | ---: | --- |
| `rsi_watch_threshold` | 70 | 50–95 | Independent RSI reversal watch, historically prior RSI≥threshold then weaker with bearish close and negative histogram |
| `rsi_warning_long` | 60 | 50–90 | **Warn only** for current Potensi Naik and RSI greater than threshold |
| `rsi_warning_short` | 40 | 10–50 | **Warn only** for Potensi Turun and RSI below threshold |
| `rsi_long_max` | 70 | 47–90 | LONG RSI score range upper bound |
| `min_score` | 68 | 50–95 | Candidate minimum |
| `volume_full_score_min` | 1.10× | 0.85–5 | Full volume score |
| `max_chase_pct` | 0.30% | 0.05–2 | Promotion anti-chase threshold |

Configuration is **shared across two feature profiles but formulas differ**. Revisioned SQLite settings `data/indicator_settings.sqlite3`; earlier five-key payloads are read with two added warning defaults (backward compatibility). New settings take effect on next scan, past events not resimulated. Warnings are **badge-only, not score deduction, cancellation, extra SHORT signal, or entry/exit order**. Current feature indicator watch uses RSI5m for Scalping, RSI1h for Swing. Limits are validation bounds, not optimized safe trading ranges.

### C4. Top5 candidates / persistence / event reasoning

- `scalp_runtime.py` keeps independent `ScalpRuntime` instances with `SignalStore` and separate paths: `data/signals_scalping.sqlite3` and `data/signals_swing.sqlite3`. Legacy `data/signals.sqlite3` is retained without destructive migration. On Windows main R10 the authoritative canonical DB is elsewhere; do not manually merge.
- The event DB stores `symbol,direction,status,started_at,baseline_time,baseline_price,trigger_pct,stop_pct,initial_score,last_price,last_seen,last_score,setup_active,confirmed_at,ended_at,end_reason,peak_close_pct,peak_wick_pct`. `last_rows` holds replaceable latest technical snapshot. Event archive retention ~30 days.
- Stored statuses include `PENDING`, `REACHED`, `EXPIRED`. End reasons `TARGET_REACHED`, `STOP_HIT`, `TIMEOUT`, `TIMEOUT_UNOBSERVED`, `RANK_REPLACED`. An expired signal is not automatically a losing fill: timeout, missing path and rank replacement must be distinct categories.
- **Bug fixed within feature branch:** `signals.py::_expire_unobserved` originally hardcoded `PENDING_MS` (15m) even for Swing configured 3 days. Changed to `self.pending_ms`; offline regression in `test_event_expiry_profiles.py`. This fix is **not** a claim of live Swing validation or R10 main defect.
- An event can remain `PENDING` while current `potentialUp/potentialDown` becomes false; `setup_active` is the **latest** Boolean, not timestamped reason/history. This motivated a proposed change-log, **not** an implemented signal invalidation journal. The UI does not necessarily display expired events in Potensi/Sudah, but `/api/events?strategy=...` can retrieve recent archive.

## D. Important product and methodological distinctions

### D1. "Gagal indikator" vs actual outcome

The user asked what to do with data after a signal had already entered radar but later failed or ceased to meet criteria. Recommendation (ASSISTANT-CHAT; **not implemented**) was an append-only **Signal Journal** with:

1. Immutable creation snapshot: symbol/side, profile/version, settings revision, chosen closed-candle time, decision and quote receipt time, baseline/eligible-entry proxy, initial score and each indicator/threshold, initial regime, TP/SL/fee assumptions.
2. Observation snapshots over time, including changes in EMA/RSI/MACD/volume, source age, and reason why setup became **INVALIDATED**. Preserve original signal row, never backfill a new score as if known at creation.
3. Independent **setup-validity axis** (`VALID`, `INVALIDATED`, `UNKNOWN`) and **price-outcome axis** (`TARGET`, `STOP`, `TIMEOUT`, `UNOBSERVED`, `RANK_REPLACED`). No conversion of invalidation to an automatic losing trade.
4. Separate lead time to invalidation, subsequent true price outcome, false alarms, missed moves, day/symbol clustering, outcome path completeness, costs and delayed-entry sensitivity.
5. RSI warning 60/40 must **not** itself invalidate a setup. Define any invalidation rule explicitly and test it; e.g., trend reverses or score breaches a threshold across *closed candles*, not quotes alone.

A hypothetical BTC LONG initial score 82 dropping to 60 a few minutes later was **an illustration, not a real observed trade or case study**. The chat supplied no original coin-specific timestamped signal record, CSV, screenshot, or live trading P&L for this design.

### D2. Test evidence and limitations

- GitHub Actions offline runs for feature branch were reported green after multi-timeframe/JS and RSI tests; final expiry change at commit `7e404b84` had run [45012562202](https://github.com/supermankesasar/Scalp-Radar/actions/runs/45012562202) **success**. That checks syntax and offline regressions, **not Windows boot, Binance network, OI/WS freshness, actual profitable signal, or end-to-end user trial**.
- No complete per-profile historical replay/backtest or R10 direct comparison was performed in this chat. Original v0.5 negative metrics cannot be transferred as performance of newly rewritten profiles. User said they were trying the app but supplied **no actual testing result or market journal**.
- Klines are queried over public REST in limited batches. Swapping to 1m does **not** prove 1m reaction speed for all 80+ symbols; no guarantee of order fills or unbroken real-time acquisition. Logs may show insufficient history/429.
- `TOP80` counts pre-filter symbols; combining with tracked legacy events can exceed 80. Market-wide ALL may take significantly longer. `LIQUID` means chosen quote-volume threshold, not automatically 80 symbols.
- Fast-watch DB snapshots may be recent quotes attached to **older** indicator values. Do not advertise a fresh RSI risk badge as tick-level risk without a fresh confirmed RSI candle and provenance.

### D3. Desktop application discussion (uncommitted concept only)

User asked, "sekarang kan dalam format web ... gimana kalo bukan web, jangan di buat langsung, kita bahas dulu ... jadi app". Options presented: (a) packaged desktop `.exe`, (b) **web UI in an app shell** with existing Python engine retained, (c) rewritten PySide6/Qt native desktop. Assistant preferred (b) for lower rewrite risk, but **user did not decide**. Future possibilities: Windows native notifications, sound alerts, system tray/background worker, optional auto-start, installer/updater, separate signal journal. Need distinguish "window closed" from worker process stopped, security of remote/mobile access, rate-limit, local data persistence, and packaging maintenance. Some earlier different chat expressed dissatisfaction with custom web / preference for preexisting AI framework; those are separate product explorations. No actual desktop code/installer was created here.

## E. Conflicts, supersessions and source/access limits

1. **Main vs feature:** latest R10 main's `R08_MULTI_CORE` is authoritative; branch Scalp/Swing default Top80, profile-specific formula and 2 SQLite DBs are **unmerged historical implementation**. Main's README may retain legacy ALL default. Do not present either branch's config as the other's.
2. **Initial Intraday UI filter vs independent Swing runtime:** UI-only 24h gate and shared Top5 were **SUPERSEDED**. User later chose the name Swing; do not claim separate Intraday backtest exists.
3. **3m Scalping idea vs user correction:** 3m was requested once then explicitly **removed**, final only 1m/5m/15m/1h.
4. **24h price movement vs turnover:** 24h *price-change* excluded from Scalping directional scoring; 24h *USDT quote turnover* retained as liquidity/universe selector. User's statement "intraday data24 dimasukkan dalam hitungan" was implemented as an extra sign-confirmation gate, **not a weighted feature**, by assistant. Distinguish intention from implementation.
5. **RSI 60/40 asymmetric user wording:** >60 LONG explicit; <40 SHORT was assistant's operational interpretation of "sebaliknya". Do not imply user empirically validated threshold pairs.
6. **Context/freshness:** quoted branch code tested offline only; earlier future strategy branch was closed/unmerged into main according to prior KB migration. Do not silently replace R08/R09/R10 with it.
7. **Access:** only visible conversation messages, a safe prior-chat handoff summary, the two original text files `analisis.txt`/`kondisi-dasar.txt`, main/feature GitHub files and existing KB were accessible. No user local PC runtime, market logs, private SQLite contents, actual trade history, original coin screenshots, or every independent chat transcript. External logo CDN contents not bulk validated; this is a presentation library only.

## F. Next research, not implementation authorization

- Freeze feature-version settings and extract event-time snapshots to a new **Journal** format; test 60/40 warning usefulness conditional on *potential category*, without label leakage.
- Compare 1m Scalp vs 1h Swing separately with point-in-time universe, separate horizons/costs, realistic latency, missing bars/terminal outcomes and symbol/day holdout. Test 3-day Swing horizon against distinct targets, do not assume it's suitable.
- Prototype a desktop shell **only after user chooses** between wrapped UI vs Qt/native. Do not imply prior discussion approved coding or a native rewrite.
- Continue R10 operational-first collection **separately** on main per latest existing [Decision Log](../DECISION_LOG.md). This appendix is evidence preservation only.

**Primary source links (feature branch):** [scalp_engine.py](https://github.com/supermankesasar/Scalp-Radar/blob/feature/v05-data-backtest-oneclick/scalp_engine.py), [swing_engine.py](https://github.com/supermankesasar/Scalp-Radar/blob/feature/v05-data-backtest-oneclick/swing_engine.py), [scalp_runtime.py](https://github.com/supermankesasar/Scalp-Radar/blob/feature/v05-data-backtest-oneclick/scalp_runtime.py), [signals.py](https://github.com/supermankesasar/Scalp-Radar/blob/feature/v05-data-backtest-oneclick/signals.py), [indicator_settings.py](https://github.com/supermankesasar/Scalp-Radar/blob/feature/v05-data-backtest-oneclick/indicator_settings.py), [rsi_alerts.py](https://github.com/supermankesasar/Scalp-Radar/blob/feature/v05-data-backtest-oneclick/rsi_alerts.py), [README.md](https://github.com/supermankesasar/Scalp-Radar/blob/feature/v05-data-backtest-oneclick/README.md); [main CURRENT_STATUS](../CURRENT_STATUS.md).
