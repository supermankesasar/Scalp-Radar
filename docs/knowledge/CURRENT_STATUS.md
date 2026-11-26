# Current Status — verified from main on 2026-11-26

**Baseline inspected before migration:** `b9e5b2883f958d053ab9db432cb4ddacbf839bbd` — `fix(r10): bound pending evaluation, share API cooldown, add concentration diagnostics` (2026-11-26 02:38 UTC). This SHA identifies the **pre-migration state**, not the knowledge-doc commit. Inspect latest `main` before using operationally.

## Active application and research

- **Local Windows** Python scanner; `START-WINDOWS.bat` single launcher, API/UI local. R08_MULTI_CORE remains **default live watchlist ranking**; user direction is local-only. No automated orders, exchange keys, runtime/paid AI or live trading advice. Current repo contains R09 WebSocket and R10 persistence/recovery research on top of v0.5/R08.
- **R09:** public 1m/5m/15m/1h/4h candle streams + aggTrade, partial depth, sampled liquidations, REST fallback; 12 1m research rule IDs + R09_HYBRID. 39 distinct research rule IDs *before* R10, not independent trades.
- **R10:** 13 additional shadow rule IDs (7 1m + 6 5m). Decision-time entry proxy, 15/30/60m outcome policies, UNOBSERVED paths, 7-day-offset fixed holdout, coin/day clustering, cost sensitivity, no live rule promotion. `/api/runtime`, `/api/research/r10` and `research/report_r10.py`.
- **Operations:** local process supervisor/heartbeat/restart tracking; shared REST 418/429 cooldown, bounded pending settlement; database canonical Windows path `%LOCALAPPDATA%\\ScalpRadar\\data\\signals.sqlite3` (`SCANNER_DB` override); no automatic merge if canonical DB exists.
- **Evidence:** v0.5 retrospective NO-GO; R09 audit has all 12 minute rules negative under 0.20% assumed cost; R08 exhaustion concentration fragile. **No proven profitable signal**, no user-PC runtime verification or completed independent R10 holdout in reviewed materials.

## Do not infer from older docs

Historical `DEPLOY_ONLINE.md` and a paragraph in `README.md` describe Render deployment; these do not override the **current R10 local-only** decision. Older R07 default SCALP_V2 was **superseded** by R08. Early Whale Radar HTML/GitHub Pages concept is a different historical prototype, not the current app runtime.

Sources: [README](../../README.md), [R08](../../research/R08_MULTI.md), [R09](../../research/R09_WEBSOCKET.md), [R10](../../research/R10_RESEARCH.md), [implementation](../../filters/r10.py). This document reflects repository evidence, not a live exchange or on-PC test.

<!-- migration-note:2026-11-26-scalping-swing-local-ai-arkham -->
## Preferensi terbaru dari chat yang dimigrasikan (produk, bukan status rilis)

Pengguna menyatakan **scalping futures dan swing trading** adalah fokus sekarang. Fitur **whale monitor internal bukan prioritas**, karena pengguna memeriksanya melalui **Arkham** secara terpisah. Sebelumnya pengguna ingin memakai framework trading-AI berbasis web yang sudah jadi dengan **AI berjalan di PC sendiri**, bukan web custom lama. **Tidak ada bukti Ollama/QuantDinger/TradingAgents berjalan dalam runtime main**; ini tetap usulan arsitektur. Status code R08 default + R09/R10 shadow di bagian atas **tidak berubah**. Mode swing khusus dan TP-coaching belum teruji/terimplementasi.

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Latest operational directive and verified status (26 Nov)
Checked main at `3bfc820969376ec5835e7b8eaf6e5da850f80381`; later commits after code baseline b9e5b28 are KB migrations. R10 CI run 45743765334 **completed success** Windows/Linux; no verified live R10 test on user's PC. R09 uploaded DB reopened and quick_check passed; full counts in EXPERIMENT_RESULTS. R10 code remains 52 total documented rule IDs, 39 prior +13 new, R08_MULTI_CORE dashboard default; do not infer 52 independent trades or profitability.
**Current user priority: operational-first, collect data concurrently; do not wait for further research or holdout to continue development.** Keep simple UI, deterministic backend, local-only, no online access work. R10 prospective shadow ledger and fixed holdout stay in place; no source/config change authorized by this docs migration. To upgrade: stop R09, extract main ZIP, copy old data folder before first launch, START-WINDOWS.bat, canonical DB copied if absent; if canonical already exists do not overwrite/merge blindly. Export via export_overnight.bat.
