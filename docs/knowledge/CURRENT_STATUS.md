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

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
Additional audit at pre-migration main `3e9ca4e4e4c9ec11d41a58e8f320ba89a6b291d1`: comparison with code baseline b9e5b28 showed three intervening commits, changes only within docs/knowledge; R08 default/R09–R10 shadow and operational-first local scope unchanged. Original 45-pair chat adds historical evidence, not new runtime state, code changes or validated holdout.

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## Source access update (26 Nov)
At pre-migration main 3d5f55fcaf2c203f4024e370c50f3f06cb51e998, compare with code baseline b9e5b2883f958d053ab9db432cb4ddacbf839bbd shows four intervening docs-only commits. R10 local/shadow, R08 core default and operational-first directive remain unchanged. Original Claude Research Lab V1 files now audited (not deployed); no new runtime or forward validation. [Audit](research/CLAUDE_V1_ARTIFACT_AUDIT.md).

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## V0.5 chat-specific branch audit — not main release (2026-11-26)

The separately reviewed `feature/v05-data-backtest-oneclick` branch exists at `7e404b84e9f5038559ce792f4338ddac9432e307`. It contains independent 1m/5m/15m/1h Scalping and 15m/1h/4h/8h/1d/1w Swing scanners, Top80 as default, separate event databases, public coin icons, 60/40 passive RSI warnings and a branch-only Swing timeout correction. GitHub Actions offline tests passed; no separate profitable profile backtest, Windows runtime audit or live fill verification was supplied.

**These branch features are not the authoritative main application:** main continues R08 CORE default, R09/R10 research/shadow and local operational-first scope described above. The desktop-app wrapper and Signal Journal were discussed, **not implemented/approved**. Baseline main was `3d5f55fc` at migration start and was subsequently advanced by an independent Claude research-document migration; see Git history for latest HEAD. [Evidence appendix](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md).

<!-- migration-note:2026-11-26-r01-r06-modular-overnight-chat -->
## Main and historical R01–R06 chat audit (26 Nov)
Pre-migration main `37a99d2b15054c780314c182e69cddc657b975c6`, latest commit V0.5 Scalp/Swing KB migration. Compare against code baseline b9e5b288: six intervening commits, files only under docs/knowledge. R08 CORE default, R09/R10 shadow and local-only operational-first status unchanged. The 24 Nov screenshot and first overnight log apply to old v0.5 modular branch, not a live R10 verification. Current canonical Windows DB remains %LOCALAPPDATA%/ScalpRadar/data/signals.sqlite3 unless overridden; original folder-relative D-drive discussion historical. [Evidence](research/R01_R06_MODULAR_OVERNIGHT_CHAT_2026-11-24.md).

<!-- r11-preview:2026-11-26 -->
## R11 implementation branch (2026-11-26; NOT merged)
User approved early radar pipeline and delegated transport choice. [PR #3](https://github.com/supermankesasar/Scalp-Radar/pull/3), branch feature/r11-early-radar, initial commit 1864b481f2474afc5201a516b2ca4d0b5680258f. [Branch preview documentation](https://github.com/supermankesasar/Scalp-Radar/blob/feature/r11-early-radar/docs/knowledge/R11_PREVIEW.md). Cache-only closed-1m preview, rolling 5/15/30/60 returns, separate readiness/monitor states and 15m outcomes, shared REST header weight budget. No new subscriptions or REST calls; no default dashboard change. Native 15m structure, intra-minute detection and missed-event report not implemented. CI triggered; runtime and signal effectiveness unverified. Main still R10 with R08 default. No R10 export supplied yet. Manual-only scope permanent.

## R11.1 P1–P6 development (2026-11-26)
Supersedes the earlier NOT merged R11 note: PR #3 merged at 12417cb06caac35f60def8ec964c1c2ebbb321c8; first operational export documented in EXPERIMENT_RESULTS. This R11.1 branch implements P1–P6 as a separate preview; [R111](R111.md). R08 dashboard and R11 v1 comparison preserved. CI and runtime performance not yet verified at commit creation. No fresh data audit or threshold promotion.

## R11.1 release update (26 Nov 2026)
PR #4 merged into main at `07543d22cc0492ba5afedce363ce3a37b7d2db71` after offline Windows/Linux CI run [45777543773](https://github.com/supermankesasar/Scalp-Radar/actions/runs/45777543773) completed successfully for head f74c0cd. User reports CPU/RAM are sufficiently capable; no measured resource capacity or benchmark supplied. Prioritize ALL-pair coverage and timely decisions over premature local resource optimization, while preserving Binance transport limits, bounded memory and measured CPU/DB contention. Existing R08 dashboard, R10 and R11 v1 comparator remain; R11.1 preview enabled by launcher. Runtime/coverage gains and trading decision quality not yet verified on user's PC. Use existing canonical DB and stop old process before starting upgraded main.
