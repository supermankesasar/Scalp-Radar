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
