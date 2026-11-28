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

| Nov 26, user clarification | **PERMANENT NON-GOAL:** auto-trading is excluded, not deferred | User: “autotrading tidak akan di lakukan sama sekali, jadi tidak perlu jadikan itu patokan”; see [canonical scope and research criteria](MASTER_PROJECT.md#current-scope-and-non-goals-current-verified-repo) |

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

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Latest workflow decisions (USER-CHAT, 26 Nov after R10)
- **CURRENT:** "gas r10 secara keseluruhan ... abaikan web untuk di buat online" — implement all R10 locally, not hosting.
- **CURRENT:** "tanpa penelitian lagi ... langsung aja kita skip sambil ambil data ... terlalu banyak test" — proceed operationally now; collect/evaluate in background; prioritize practical entry/exit monitoring, speed and reliability. **SUPERSEDES** older handoff instruction to delay all coding until research completes and assistant's suggestion to wait seven days before further development. Holdout remains recorded for scientific validation; not a release gate for routine improvements. No change to active filter, no permission for actual orders, no assertion of profit.
- **CURRENT:** User asks each old chat to read existing KB then merge only missing information, preserve failures/conflicts, commit docs to main, no force push or source modification. Use this index on new chats.
- **HISTORICAL:** free hosting/no card/normal fixed URL desired; InfinityFree, Quick Tunnel, Render and Tailscale did not produce verified working remote dashboard. Deferred; do not restart hosting task without request.

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
22–25 Nov original discovery chat: user explicitly wanted independent pattern discovery, not identical indicator definitions across AIs; standardize only metadata and compare definitions transparently. User explicitly rejected adding chart-pattern/indicator panels: keep existing UI, run complex backend locally without runtime AI. Historical research-first gate was superseded by the later 26 Nov operational-first directive above; do not revive gate or change current code on this migration. See [original discovery appendix](research/EARLY_DISCOVERY_2026-11-22_24.md).

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## Further user decisions from the historical V0.5 feature chat (not the current main policy)

| User requirement or decision | Temporal/validation status | Consequence |
| --- | --- | --- |
| Scalping **1m/5m/15m/1h** | **USER-CHAT, corrected** | Original requested 3m was explicitly **SUPERSEDED**. Feature branch changed scanner and 1m event cadence; speed/edge not validated |
| Second category named **Swing 15m/1h/4h/8h/1d/1w** | **USER-CHAT, corrected** | Original **Intraday** UI-only 24h sign filter and shared Top5 became historical; independent mode/DB implemented on unmerged branch |
| Exclude 24h price movement from Scalp, but turnover still selects liquid pairs | **USER-CHAT with assistant design choice** | Swing uses 24h price-change *sign gate* (not weighted score); TOP80 refers to pre-filter universe, not passed candidates |
| Display RSI>60 warning in Potensi Naik; opposite in Potensi Turun | >60 explicit **USER-CHAT**; <40 SHORT **ASSISTANT interpretation** | Warnings were added as passive badge, not invalidation/order; thresholds not empirically proven |
| Preserve data of failed/invalidated radar setups | **USER-CHAT** | Separate technical validity from price outcome; Signal Journal proposed, **not yet implemented** |
| Discuss desktop Windows app before development | **USER-CHAT: "jangan di buat langsung, kita bahas dulu"** | Wrapping current local web UI preferred by assistant, but no user decision, no installer or native app built |
| Keep later R10 main operational direction | **CURRENT-MAIN** | R08 CORE default, R09/R10 shadow/research and local-only persist; unmerged V0.5 branch is not replacement |

[Full chronological source and distinctions](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md).

<!-- migration-note:2026-11-26-r01-r06-modular-overnight-chat -->
## Original research workflow decisions (24 Nov; later R10 workflow supersedes research-first gate)
- USER: Futures-only, rule/real-time basis; history technical/context/outcomes, not predictor standard; no separate adaptive engine. Keep explicit thresholds relative or fixed where appropriate.
- USER: EMA9/21 alternatives; 15/30m validity and 5/15m confirmation; record 60m follow-up; all passing candidates tracked, Top5 only UI; no neutral display; split filters into independent files and centralize history.
- USER: archive previous 28 for R06 and select 30 new; explicitly corrected overnight to **ALL** active crypto pair incl previous ones. Do not conflate research cohort with scan scope.
- Assistant withdrew draft 40/20/20/20 weights pending testing; other early score schemes unadopted. User requested Windows theme preference and D-drive storage (old path only). During adverse screenshot no signal rule change was made. [Provenance](research/R01_R06_MODULAR_OVERNIGHT_CHAT_2026-11-24.md). Current R08/R10 and later operational-first instruction preserved.

<!-- decision:2026-11-26-r11-hybrid -->
## R11 direction approved (USER-CHAT, 2026-11-26)
User approves **Detect Early → Identify Direction → Validate Entry → Monitor Movement**, asks developer to choose the appropriate data transport and account for API/WebSocket limitations. Developer chooses WebSocket-first hybrid: reuse existing public kline, aggTrade/quotes and partial-depth caches; REST for bootstrap, closed-candle repair and derivative context. No additional 30m stream is required for rolling 30m context; do not confuse rolling returns with native closed timeframe candles. No extra per-symbol polling for R11 first phase. Preserve R08 default while the independent R11 preview is implemented, instrument coverage, latency, and request-weight telemetry. Official USD-M references: https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/general-info and https://www.binance.com/en-IN/support/announcement/detail/ebf9b0aa9eca4ff3804eef6fb09ba32a ; 24h connection lifecycle, routed market/public streams, 1024 streams/connection, 10 inbound control messages/s/connection, IP request weight and 429/418 backoff. Existing R09 lag/coverage evidence is historical, not a guarantee. R11 thresholds provisional; no claims of profitable or earlier alerts until observed. Manual decision support only.

## R11.1 P1–P6 authorization (26 Nov 2026)
User: “ok lakukan p1-p6 gas”. Implement coverage and diagnostic improvements, native 15m context, missed movement tracker and independent entry challenger as specified in [R111](R111.md). Keep original R11 as comparator, no unsupported improvement claims or auto-trading. Developer chose provisional thresholds, depth bid/ask and parallel preview rather than replacing active dashboard.

## 28 Nov 2026 — R11.2
User approves Impulse Exhaustion Radar. Developer chooses cache-only integrated prospective paired controls and confirmed recovery cohort, preserves dashboard and existing formulas, fixes joined export sample mismatch. [R112](R112.md).


## 28 Nov 2026 — user direction: speed, weekly storage, Top10, separate profiles
USER-CHAT: 36m04s ALL scan unacceptable for scalping. Prioritize speed and coverage; show 10 highest-score potential slots (combined sides), sort score descending. Additional technical indicators as research data, not mandatory entry gates. Daily Lite should represent whole observed market, not just newest sample. User prefers weekly database grouping instead of monthly; design hot rolling 7 days plus immutable weekly archive partitions, no auto-delete or rotation until safe migration verified. Warmup requirements remain separate: existing R08 reads 229 closed 4h bars (~38 days) and 229 1h bars (~9.5 days), so a hard 7-day raw cutoff would break current EMA/indicators. Preserve higher-timeframe warmup/cache, all pending/outcome linkage, timestamps and per-coin continuity across weeks; propose Monday 00:00 WIB weekly boundary, archive verified row counts/hash and restore test before deletion; archive-aware research reports needed. Swing tab is separate proposed profile (prior user TF definition 15m/1h/4h/8h/1d/1w vs scalp 1m/5m/15m/1h), separate score, cadence and outcomes; not a change to scalp ranking. Do not blindly add indicator weights or promote negative prior experiments. Implementation now: speed/Top10/shadow indicators/daily export only; weekly migration and swing not implemented in this release.
