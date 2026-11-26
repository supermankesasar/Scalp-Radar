# Research History — chronology and evidence strength

| Stage | Period | What changed | Result / status | Primary source |
|---|---|---|---|---|
| Early Whale Radar concept | Oct 2026 chat context | Proposed candle dashboard, large-transaction radar, TP alerts, later AI | **USER-CHAT** requirements; assistant described HTML demo, but original bytes unavailable in this migration | [Migration log](MIGRATION_LOG.md) |
| v0.5 | 2026-11-22 analysis; Aug/Nov samples | 5m Top5 continuation, close-based target/stop, anti-chase | **EXPLORATORY NO-GO:** combined mean net −0.1932% after assumed 0.20% round trip | [v0.5](../../research/BACKTEST_V05_2026_REPORT.md) |
| R01–R05 | 2026-11-23/24 | EMA9/21 timing alternatives; 1h trend, RSI/MACD, RVOL/VWAP/account-share ablations | Many weak/negative; promising subgroup results highly sample-dependent; no live promotion | [Technical follow-up](../../research/TECHNICAL_FOLLOWUP_2026-11-24.md) |
| R06 | 2026-11-23/24 | 30 new frozen pairs; OI build/unwind, taker share, crowding, funding | Several averages negative and positive subgroups inconsistent across dates/directions | [R06 report](../../research/R06_REPORT_2026-11-24.md) |
| R07 | 2026-11-25 | SCALP_V2 short-EMA/1m-timing challenger, using 5m outcome grid | Experimental; R07's originally default live filter later superseded by R08 | [R07](../../research/R07_SCALP_V2.md) |
| R08 | 2026-11-25 | Multifactor score, flow/structure and case-derived tags, ablation, independent ledgers | **CURRENT live default** CORE; hypothesis tags not validated as profitable | [R08](../../research/R08_MULTI.md) |
| R09 | 2026-11-25 | Hybrid WebSocket + REST cache, 12 1m rules + R09_HYBRID, receipt/coverage tracking | Audit: all 12 1m rules net negative under assumed 0.20% costs; gaps/lag noted | [R09](../../research/R09_WEBSOCKET.md), [R10 audit](../../research/R10_RESEARCH.md) |
| R10 | 2026-11-26 | 13 new shadow hypotheses; local runner, canonical DB, prospective ledger/holdout; bounded pending evaluation | **CURRENT research system**; no forward holdout or live profitability validation established | [R10](../../research/R10_RESEARCH.md), [R10 code](../../filters/r10.py) |

## Research lessons preserved

- **Failed/weak alternatives remain informative:** v0.5 high score (≥90) still had negative mean net; 5/10-minute delayed entry reduced target attainment; lower TP thresholds did not fix aggregate profitability.
- R01–R05 9/9 EMA variant produced more signals but first-episode average was worse than B21; isolated EMA21 1h and fast crosses generated positive *subsamples*, not robust confirmation. Account-ratio alignment sample heavily confounded by pair and direction.
- R06 OI build/fade and unwind/fade are not independent identity or direction signals. Even positive rule/date/side strata should **not** be promoted based on these exploration windows.
- R08 case narratives (PIEVERSE, SKYAI, AIOT, SKY, FLOCK, CYS, AIN) drove rule design; therefore these are **discovery cases**, not independent out-of-sample evidence.
- R09 latency/coverage and R10 anti-concentration safeguards show why raw signal counts and pooled averages can mislead.

Historical documentation sometimes speaks as if a branch was still in staging, and older README sections discuss cloud hosting. Prefer [CURRENT_STATUS](CURRENT_STATUS.md) and latest code for current state; retain historical language only as timestamped evidence.

<!-- migration-note:2026-11-26-scalping-swing-local-ai-arkham -->
## Diskusi produk trading-AI lokal pada chat lain [USER-CHAT / bukan eksperimen]

Pengguna menolak bentuk web custom sebelumnya dan mengusulkan memakai solusi open-source berbasis browser serta model AI yang berjalan di komputer pribadi. Salinan hasil pencarian Google yang dibawa pengguna mencantumkan **TradingView/webhook, Streamlit, Gradio, Backtrader, Jesse, OpenAlgo, QuantDinger/OpenByte OS, HKUDS AI-Trader, dan TraderMagic**. Sebelumnya TradingAgents dijadikan acuan konseptual di analisis.txt. Asisten mengusulkan QuantDinger + Ollama; kemudian pengguna **mengubah fokus menjadi scalping futures dan swing**, serta mengesampingkan whale radar karena **Arkham**.

**Status evidensi:** ini sejarah penentuan kebutuhan/arsitektur, **bukan penelitian coin, backtest, pengukuran win rate, keberhasilan instalasi lokal, atau bukti library tersebut ada di main**. Deskripsi fitur dari hasil pencarian tersebut tidak diaudit sebagai bagian migrasi; klaim mengenai TraderMagic belum terverifikasi. Baseline R10 yang lebih baru tetap menjadi sumber kebenaran untuk implementasi. Tidak ada hasil eksperimen baru dari chat ini.

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Handoff evidence: 45-pair discovery and external Research Lab V1 (22–24 Nov 2026 WIB)
Source: supplied `Pasted text.txt` and `Pasted text (2).txt` (earlier research handoffs, not raw market dataset). The same 45 pairs appear in both; count once. Details in [COIN_CASE_STUDIES](COIN_CASE_STUDIES.md) and [EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md).
Initial problem: PIEVERSE/SKYAI extreme moves missed while selected coins often moved little. Discovery separates abnormal activity, direction and entry timing; OI/RSI/EMA/CVD alone were insufficient. Chart patterns and market synchronization were explicitly requested as backend features, not UI panels.
External Claude report: 131 pairs, 1–24 Nov, 132 combined unique symbols after dedup with the 45-pair research (as reported). External public-archive study examined nine rather than requested 50; its 13.3% big-print volatility claim and 2.8× lift are unverified. Claude results are historical reported research, not independent confirmation or live P&L. See [EXPERIMENT_RESULTS](EXPERIMENT_RESULTS.md) for failures and [KNOWN_ISSUES](KNOWN_ISSUES.md) for leakage.
Two overnight audits (25 and 26 Nov) are distinct exports, not a cumulative time series; R09 WS materially reduced receipt latency but gaps and negative returns persisted. R10 implemented prospective evaluation and operational resilience. After R10 user explicitly preferred operational-first development with concurrent background collection.

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## Claude V1 original evidence (24 Nov 2026)
The original source and all nine companion files were reopened in this migration; prior handoff-only caveat no longer applies to these files. [Artifact audit](research/CLAUDE_V1_ARTIFACT_AUDIT.md) preserves exact calculations, source manifest, split leakage, 131-pair coverage, conditional directional AUC and failed OOS rules. No new exchange fetch or forward validation. The early 45-pair and external nine-pair reports were already fully summarized in the existing appendix; no duplicate research cohort.

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## Prototype design timeline, not quantitative new research

Approx. 22–25 Nov, a separate V0.5 feature discussion moved from configurable RSI70 reversal watch to a **Scalping/Intraday two-tab UI filter** (24h sign confirmation, shared signals; subsequently **SUPERSEDED**). The user then explicitly corrected the timeframe set to **Scalping 1m/5m/15m/1h** (3m removed) and **Swing 15m/1h/4h/8h/1d/1w**. The branch implemented independent close-bar event streams and archives; added coin-logo fallback and RSI >60 LONG / assistant-inferred <40 SHORT visual warnings. Finally, user requested a taxonomy for invalidated/failed signals and discussed—but did not authorize building—a Windows desktop app. Feature regression CI passed, **no new coin-level datasets or strategy performance measurements** were produced in this chat. [Source appendix](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md). R01–R10 research findings remain authoritative separately.
