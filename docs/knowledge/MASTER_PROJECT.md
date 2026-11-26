# Master Project — purpose, boundaries, preferences

## Original user requirements (USER-CHAT; initial context 2026-10-08)

- User is a **beginner in trading and coding**; wants step-by-step, practical assistance rather than assuming programming experience.
- Initial goal: a browser-based **decision-support tool**, monitoring candlestick movement and signs of large participants described as “shark/whale”; inspiration: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents). Inspiration is not evidence of AI integration or a required architecture.
- Pain point: **late take-profit decisions**, including watching a coin rise and failing to act in time. Price/TP alerts and a clear, cautious presentation matter.
- Initial context: used Ajaib, newly installed Binance but had not used it, had seen MetaTrader without trying it, and was undecided between crypto and forex. This is **historical discovery context**, not proof of current exchange usage or trade activity.
- Hardware/access preference: **Windows laptop and Android phone**; wants very basic instructions, low setup friction.
- No request to execute orders in this chat. Distinguish observation, simulated status, alert, and actual trading execution.

## Current scope and non-goals (CURRENT; VERIFIED-REPO)

- Current system is Scalp Radar, a local Python/Windows **Binance USDⓈ-M USDT perpetual** scanner and research ledger with desktop/mobile web UI capability, not the one-file early prototype.
- **R08_MULTI_CORE** is live default *ranking/monitoring filter*, while R09/R10 research is independent/shadow unless explicitly configured as documented. A watchlist is not a validated entry recommendation.
- **No auto-trading, Binance account keys, runtime/paid AI, or order placement.** R10 user direction is local-only; prior hosting guidance is historical, not present authorization.
- Preserve evidence of failed experiments, avoid look-ahead and false precision; compare directional setups under realistic fee, latency, regime and data-coverage constraints.
- Prioritize availability/freshness of data and actual outcome observation over flashy scoring, and **do not treat whale/shark identity as directly observable** from order flow, account ratios or aggregated prints.

## Product philosophy

Beginner-readable labels for Potential vs Confirmed, source freshness and insufficient data; explicit **No Trade / Watch** states; TP monitoring as a research requirement, not a promise of push notifications or guaranteed fills. Consider a future optional AI analysis layer only after stable data provenance, validation, and cost/security review.

Sources: this conversation, `analisis.txt`, `kondisi-dasar.txt`; [README](../../README.md), [R08](../../research/R08_MULTI.md), [R10](../../research/R10_RESEARCH.md).

<!-- migration-note:2026-11-26-scalping-swing-local-ai-arkham -->
## Handoff tambahan: scalping futures + swing dan AI lokal (USER-CHAT; dimigrasikan 2026-11-26)

Dalam percakapan terpisah yang kini dimigrasikan ini, pengguna secara eksplisit menyatakan **gaya trading saat ini adalah scalping futures dan swing trade**. Tujuan produk bergeser dari pemantauan whale menjadi **asisten keputusan untuk kedua gaya tersebut**. Pengguna menyatakan **whale monitor dapat dikesampingkan karena dapat dicek lewat Arkham**. Pernyataan ini lebih baru dalam alur chat terkait dibanding kebutuhan awal shark/whale dan perlu digunakan saat mengklarifikasi roadmap; *tidak* berarti Arkham terhubung ke aplikasi.

Pengguna juga menegaskan **web custom yang sebelumnya dicoba tidak cocok**, sehingga ingin memanfaatkan solusi trading-AI berbasis web yang sudah ada, dengan **AI berjalan di komputer sendiri**. Ia membawa daftar kandidat framework dari hasil Google; itu merupakan **ide eksplorasi produk, bukan verifikasi fitur, pilihan final platform, dependensi yang sudah terpasang, atau izin mengganti arsitektur R10**. Saran asisten waktu itu adalah QuantDinger + Ollama, tetapi tidak pernah menjadi implementasi di source main.

Kebutuhan tetap **decision support dahulu, bukan auto order**. Pertanyaan spesifikasi Windows/RAM/GPU pernah diajukan asisten, tetapi **tidak dijawab dalam chat ini**. Timeframe scalping 1m/5m/15m dan swing 4h/1D yang disebut asisten hanyalah **saran desain**, bukan konfigurasi yang dikonfirmasi pengguna. Sumber: chat ini; status kode: [CURRENT_STATUS](CURRENT_STATUS.md).

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Operational-first directive (USER-CHAT, 2026-11-26, after R10)
The two supplied handoffs explicitly specify **Complex Backend, Simple Frontend, Zero AI Dependency**: local PC, deterministic math/statistics/rules, Binance API/WS, independent background scanning even when browser closes, keep existing frontend, store technical reasons in SQLite/debug logs. Do not add indicator/chart-pattern panels merely because research uses them. User wants a proactive developer, parallel evaluation of alternatives, not repeated requests to remind AI of prior requirements.
The original handoffs said research before coding; subsequent explicit user authorization to implement R10 and "tanpa penelitian lagi ... langsung aja kita skip sambil ambil data ... terlalu banyak test" supersede that **workflow gate**. Operational development and live data collection proceed concurrently; do not wait for a 7-day study to fix UI/backend or improve practical monitoring. Preserve passive research/holdout, code reliability checks and honest uncertainty. No authorization for automated orders, unvalidated formula promotion as proven, paid services or new hosting. User prefers local only for now. Prior AI-local framework preference belongs to another product discussion, not R10 runtime.

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## Additional user requirements: fast modes, warnings and journal (USER-CHAT, ~22–25 Nov)

User explicitly revised Scalp timeframe from 1m/3m/5m/15m/1h to **1m/5m/15m/1h**, and described **Swing** as **15m/1h/4h/8h/1d/1w**; an initial "Intraday" tab name was superseded. They want recognisable coin icons, visible RSI warnings *without hiding* existing Potensi signals, clarity that "TOP80" is universe size before technical filters, and preservation of failed/invalidated events for future analysis.

For a standalone Windows app, user explicitly said **discuss only, do not build yet**. The assistant suggested wrapping current Python/web first; native Qt, sound/notification/tray, installer and auto-update are exploratory possibilities, not approved implementation. The user prefers low-friction Windows operation and evidence-aware exit monitoring, not complexity for its own sake. [Detailed history](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md).

<!-- migration-note:2026-11-26-r01-r06-modular-overnight-chat -->
## Historical product clarification — rule-based + real-time (USER-CHAT, Nov 24)
User explicitly chose Binance Futures only, explainable rule + real-time rather than historical pattern as a predictive standard; historical data remains important for technical indicators, coin history and actual signal evaluation. Adaptive is not a separate decision method. Modular independent filter files, shared data/history, all passing candidates evaluated regardless of displayed rank, no neutral dashboard category. AI deferred. 30 new pairs were a research sample; overnight scope explicitly ALL active crypto pairs including old cohorts. These preferences coexist with later R10 operational-first / no runtime AI and Arkham decisions. [Details](research/R01_R06_MODULAR_OVERNIGHT_CHAT_2026-11-24.md#a-user-decisions-and-discarded-early-proposals).
