# Decision Log — versioned, with reasons

| Date/stage | Decision and status | Reason / evidence |
|---|---|---|
| Oct 2026, early chat | **HISTORICAL proposal:** start with browser dashboard and public market feeds; phase in alert and AI later | User beginner in code/trading and specifically asked to view candles and whale activity without complexity; no successful deployment verified |
| Oct 2026, early chat | **HISTORICAL** illustrative large-trade size filters and example TP alert | Teaching/demo affordance, **not** derived from signal statistics |
| Nov 22, v0.5 | **NO-GO** on live/autotrade from v0.5 Top5 | 2,950 event retrospective mean net −0.1932% with 0.20% assumed costs; target rarely reached; latency and fill mismatch |
| Nov 24, R01–R05 | **KEEP** EMA21 baseline and separate EMA9/21 timing challengers, RSI/MACD contextual | Mixed/low-N cohorts; no independent profitable holdout; no weight promotion |
| Nov 24, R06 | **KEEP** OI/flow/positioning/funding as independent research tags | OI and account ratios cannot attribute actors or contract direction; negative and regime-dependent results |
| Nov 25, R07 | **HISTORICAL**, SCALP_V2 launch/default trial, then **SUPERSEDED by R08 CORE** | Needed short-frame timing experiment; profitability unvalidated |
| Nov 25, R08 | **CURRENT** R08_MULTI_CORE as default live **watchlist** filter; R08_FULL shadow/optional; 16 tags independent | Avoid silently requiring unavailable fresh derivative/breadth context; no profit claim |
| Nov 25, R09 | **KEEP** public WS + REST cache/recovery; 1m rules and R09_HYBRID not live default | Stream can reduce stale inputs but gaps/latency and costs still require validation |
| Nov 26, R10 | **CURRENT** local-only; no paid/runtime AI, hosting or auto-order; 13 R10 tags shadow only | R09 weak audit, concentrated R08 exhaustion and missing real forward data; prioritize prospective holdout and operational resilience |
| Nov 26, R10 | **CURRENT** fixed future holdout, explicit UNOBSERVED, no look-ahead; local persistent canonical DB and restart telemetry | Avoid selection bias, missing-path false wins, accidental data loss |

## Conflict/supersession register

1. **Static GitHub Pages idea vs Python scanner:** early single-file demo hosting idea was superseded in practice by local Python/SQLite scanner; GitHub repository hosting alone does not run an always-on scanner.
2. **Older deployment instructions vs R10 local-only:** `README.md` and `DEPLOY_ONLINE.md` retain a Render/cloud path as historical documentation. `CURRENT_STATUS.md` and R10 say user currently requested **local-only**; do not treat hosting text as present instruction.
3. **R06/R07 branch wording vs current main:** older research reports say branch/main unchanged or R07 default; these are snapshots. Later merge/R08/R10 have precedence.
4. **AI aspiration vs implementation:** TradingAgents-inspired AI was an idea; R10 specifically states **no runtime/paid AI**. No contradiction when dated and classified correctly.

Sources: user chat and requirements attachments; [v0.5](../../research/BACKTEST_V05_2026_REPORT.md), [R07](../../research/R07_SCALP_V2.md), [R08](../../research/R08_MULTI.md), [R10](../../research/R10_RESEARCH.md).

<!-- migration-note:2026-11-26-scalping-swing-local-ai-arkham -->
## Tambahan keputusan pengguna dari chat terpisah (waktu pesan asal tidak lengkap; migrasi 2026-11-26)

| Sumber / urutan | Keputusan atau pembahasan | Alasan | Klasifikasi |
| --- | --- | --- | --- |
| USER-CHAT, sebelum penegasan gaya trading | Custom web yang pernah dicoba **tidak cocok**; ingin memakai framework/trading-AI web yang telah tersedia dengan AI **lokal di PC** | Mengurangi pembangunan UI khusus; tidak bergantung pada AI cloud berbayar | **PREFERENSI**; bukan otorisasi migrasi kode R10 |
| USER-CHAT, setelahnya | **Scalping futures + swing trading** adalah gaya trading saat ini | Menyesuaikan fokus alat bantu entry, monitoring dan exit | **KEPUTUSAN KEBUTUHAN**; belum ada bukti mode swing teruji pada main |
| USER-CHAT, setelahnya | Built-in **whale monitor dikesampingkan** karena pengguna cek **Arkham** secara terpisah | Tidak menggandakan alat eksternal | **SUPERSEDED** dari prioritas whale awal; Arkham bukan integrasi kode |
| ASSISTANT-CHAT | QuantDinger + Ollama direkomendasikan; TradingAgents, OpenAlgo, AI-Trader dan platform lain dibahas | Alternatif reuse open-source | **PROPOSAL**, bukan pilihan final dan bukan komponen R10 |
| ASSISTANT-CHAT | Timeframe 1m/5m/15m untuk scalp, 4h/1D untuk swing | Contoh pembagian analisis | **SARAN**; belum dikonfirmasi pengguna sebagai parameter |

Jika diskusi AI-local tampak bertentangan dengan **R10 tanpa runtime AI**, keduanya benar dalam konteksnya masing-masing: pengguna membahas **arah produk masa depan**, sedangkan main yang diaudit masih berupa scanner/research read-only tanpa Ollama/LLM. Jangan mengganti formula aktif berdasarkan diskusi ini.
