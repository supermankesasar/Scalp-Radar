# Development History — prototypes, architecture and migration boundaries

## Early conversation: standalone Whale Radar (ASSISTANT-CHAT, Oct 2026)

- Assistant proposed phased architecture: v1 candle/large trade dashboard → v2 TP alerts/technical indicators → v3 optional AI market analysis, inspired by TradingAgents.
- Assistant claimed to create a downloadable **`crypto-whale-dashboard.html`** (single-file demo) and **`whale-radar-starter.zip`**, accessible by double-click in Windows; guided opening the file in Android Files/Chrome. Mentioned `LIVE · BINANCE`, `DATA SEBAGIAN`, `KONEKSI GAGAL`, `MODE CONTOH`, timeframe/large-trade filters, **Perbarui**, and a simple in-page price reminder.
- Assistant explicitly said demo alert was **in-page only**, not an Android push alert and not a Binance order. Users were instructed to try Mode contoh when data could not load.
- Earlier assistant also suggested **GitHub Pages** for a static page. This is **historical suggestion only**, not current R10 Python/SQLite deployment architecture or authorization to put scanner online.
- **Audit limit:** the generated HTML, ZIP and screenshots linked in prior assistant messages were **not present as readable files** during this migration. Their actual code, exact release, mode behavior and successful testing cannot be certified. The two original text requirement attachments *were* read.

## Repository evolution (VERIFIED-REPO)

- **v0.5:** `app.py` Python REST scanner (ALL/LIQUID/TOP80), `signals.py` SQLite Potensi/Sudah state, `index.html`/`ui.js` dashboard, PWA assets; live no order execution. Fast watch (~30s) differs from full-all-pair scanning; not guaranteed low-latency scalping.
- **R01–R06:** research engines, immutable sample batches, independently tracked candidate/outcome ledger and modular filter registry. Earlier research-only branch statuses remain in original reports for history.
- **R07:** short EMA/1m timing challenger; originally SCALP_V2 default, but later superseded.
- **R08:** multifactor CORE default live filter, FULL/ablation and independent case-derived tags; branch `main` becomes canonical distribution. All prior controls preserved.
- **R09:** public WS hybrid/cache with REST fallback, streams for candles/aggTrade/depth/liquidations, 1m candidate ledger; no account keys. Optional hybrid live ranking, default R08 CORE.
- **R10, 2026-11-26:** 13 more shadow tags; decision-time prospective outcome schema and report; local worker supervisor/backoff/heartbeat, REST 418/429 shared cooldown and bounded pending settlement; canonical persistent Windows SQLite path with non-destructive migration rules. No online deployment work by current user direction.

## Operator boundary (current)

`START-WINDOWS.bat` is single Windows launcher; server local URL documented as `http://127.0.0.1:8765`; PC, terminal and network remain on for scanning. `export_overnight.bat` creates a consistent SQLite backup ZIP; never casually overwrite canonical local DB or copy only live SQLite with active WAL. Python requirements may change by release; follow current main launcher. Source paths: [README](../../README.md), [OVERNIGHT](../../research/OVERNIGHT.md), [R10](../../research/R10_RESEARCH.md).

**No code or production configuration was modified by this Knowledge Base migration.**

<!-- migration-note:2026-11-26-scalping-swing-local-ai-arkham -->
## Alternatif arsitektur yang dibahas, tetapi tidak diimplementasikan [CHAT]

Di samping sejarah prototype Whale Radar, sebuah chat lain merekam **penolakan pengguna terhadap web custom yang sudah dicoba** dan preferensi **memakai aplikasi/framework trading-AI open-source yang memiliki dashboard web dengan AI lokal di PC**. Kandidat yang disebut/dibawa pengguna: TradingAgents sebagai inspirasi, TradingView integrations/webhooks, Streamlit/Gradio, Backtrader/Jesse, OpenAlgo, QuantDinger/OpenByte OS, HKUDS AI-Trader dan TraderMagic. **QuantDinger + Ollama adalah rekomendasi asisten saat itu**, bukan release/tag, migrasi aplikasi ataupun dependency yang terverifikasi di repository.

Pengguna setelahnya mengutamakan **scalping futures dan swing trade**, tidak lagi mengutamakan whale monitor internal karena memakai **Arkham terpisah**. Ini dicatat sebagai **perubahan perspektif produk**, bukan perintah saat ini untuk mengganti backend Python R10. Tidak ada bukti bahwa framework kandidat tersebut dipasang atau diuji pada komputer pengguna.

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Operational history from R06–R10 implementation chat
Branch cleanup: PR2 merged; incompatible older scalping/swing PR1 closed without merge rather than overwrite canonical main. Historical branches not deleted (connector lacked deletion action). Main ZIP and unified START-WINDOWS.bat, run_overnight.bat compatibility alias, export_overnight.bat preserved. R09 code commits 1f46a9c and c9f3ac9; R10 71d9e75 and b9e5b28. R10 final CI run [45743765334](https://github.com/supermankesasar/Scalp-Radar/actions/runs/45743765334) now completed success (earlier chat said Windows pending; resolved), no live-PC test. No app change in migration.
Historical online attempt: InfinityFree static/PHP host unsuitable for long-running Python/WS; Cloudflare quick tunnel QUIC then HTTP2 encountered connection/DNS issues, no reliable access; Render free deploy requested card and user declined; Tailscale Serve enabled private proxy, public Funnel attempted/recommended but user reported access failure. No confirmed remote success, no hosting config changed in this chat. Do not retain tunnel URLs, account or device identifiers. User explicitly deferred online work. No access to PC mouse/keyboard was available in chat mode.

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## Research Lab V1 external script (historical standalone)
The Claude-authored crypto_pattern_research.py and original CSVs were inspected; Python AST parses, no runtime AI, no evidence script integrated into Scalp Radar. [Audit and proposed V2](research/CLAUDE_V1_ARTIFACT_AUDIT.md#e-source-code-audit-and-conflicts). Keep original baseline immutable locally, use current main for runtime. Research-first historical constraint does not supersede newer operational-first instruction.

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## Experimental V0.5 side branch not merged to R10 main

From the accessible chat: configurable RSI70 reversal watch + revisioned SQLite/manual control → initial **Scalping/Intraday** tab with shared events and 24h sign UI filter (**SUPERSEDED**) → corrected user choice **Scalping 1m/5m/15m/1h**, **Swing 15m/1h/4h/8h/1d/1w** → `scalp_engine.py`, `swing_engine.py`, `scalp_runtime.py`, separate `signals_scalping.sqlite3`/`signals_swing.sqlite3`, separate strategy-aware API → lazy coin-logo/fallback `coin_logos.js`, RSI>60 LONG and RSI<40 SHORT warning badges (as interpreted) → regression-tested fix for hardcoded 15m Swing expiration. Feature commit `7e404b84`/run 45012562202; no proof of profitability or on-PC runtime.

User then asked to **discuss before coding** a desktop app. Existing web UI packaged as a Windows app shell was assistant's preferred option, but Qt/native rewrite, system tray, notifications, sound, autostart and installer/updater remain ideas only. Signal Journal was also **proposed**, not implemented. [Detailed historical appendix](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md). This does not alter the later main R08 default/R09–R10 shadow history.
