# Known Issues, limitations and conflicts

## Trading validity / false inference

- v0.5 mean net negative on chosen historical sample; score and "Sudah" status do not imply profitable trades.
- R01–R06 tiny, clustered/exploratory subsets, later-known universe selection in R06, overlapping candidates and partial production parity; apparent positive strata not independent tests.
- R08 cases generated hypotheses, so re-testing those same cases is circular; R09 12 1m rules negative after assumed costs; R10 has **no validated holdout**.
- Fees, funding, execution costs, spread, slippage, queueing, fill probability, liquidation/leverage not adequately modeled. R10 applies actual close overshoot in synthetic outcomes but not live fills.
- Large transactions, aggressive flow, top trader ratios, order book snapshots, liquidations and OI are **proxies**; no verified whale/shark identification.
- TP alert in the early chat was an **in-page reminder proposal**, not a proven device push notification or actual sell order.

## Data / operations

- Binance REST rate limits (418/429), IP/region restrictions; shared cooldown and pace controls help but do not guarantee continuous data. No bypass.
- Full ALL-pair REST/bootstrap scanner may take minutes; Fast Watch / WS do not guarantee instantaneous execution; stale/partial data must be shown as such.
- R09 audit: ~5.49s receipt latency and ~17h49m long gap; reconnect cannot restore lost aggTrade/depth/forceOrder history.
- `depth5@500ms` is partial book snapshot, not full reconstructed queue; liquidation reporting sampled; zero data != absence of market events.
- R10 SQLite canonical path migration **does not auto-merge** different histories. Stop process and use consistent backup; risk of duplicated/lost context if manually overriding canonical DB.
- Runtime and hosting behavior on user PC, including R10 startup/restart/long overnight reliability, **not independently verified in this migration**.
- `/api/health` means server alive, not proof of fresh Binance data.

## Documentation/source conflicts and access gaps

- Historical `README.md` / `DEPLOY_ONLINE.md` describe online Render deployment, but newer R10 asks **local only**. Preserve both records with dates; current R10 wins for actual operations.
- Earlier R07/research branch documents reflect past default/merge state, not current `main`.
- Prototype HTML, starter ZIP and screenshots claimed by earlier assistant are **not accessible as working bytes** at migration. Do not certify tests or reproduce JS functions.
- No other chat transcripts, local SQLite databases, run exports, raw P&L or coin-specific user screenshots are available in this conversation for migration.

Resolution: prioritize upstream research for method, exact code for implementation, current R10 direction for scope, and new timestamped user evidence for future overrides. Keep conflicts explicit.

<!-- migration-note:2026-11-26-scalping-swing-local-ai-arkham -->
## Kesenjangan terhadap gaya trading yang dikonfirmasi pengguna

- **Tidak ada bukti fitur atau backtest swing terpisah** walaupun swing trading sudah menjadi kebutuhan yang dinyatakan. Jangan menganggap timeframe 4h/1D contoh asisten otomatis diimplementasikan.
- **AI lokal dan migrasi ke framework siap pakai masih ide**, sedangkan R10 main tanpa LLM; spesifikasi PC (OS/RAM/GPU) tidak dijawab dalam chat ini. Jangan mengeluarkan langkah instalasi atau klaim performa model lokal seolah sudah diverifikasi.
- **Arkham digunakan terpisah oleh pengguna** dan tidak ada konektor Arkham yang diaudit; jangan mengklaim data Arkham telah masuk ke scanner.

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## Additional audit caveats and Research Lab V1
Claude script audit as reported in handoff: leakage at TRAIN/TEST/EXTRA boundaries; pair selection using later movement; random control from remainder; raw signal recall ignores cooldown; zero lead counted; open timestamp used for close-known features; inconsistent slippage, no SL gap overshoot; no durable raw OHLCV cache or full continuity checks; no 1m/geometric patterns/breadth/big print/book/liquidation; forward TEST after 24 Nov only two events, most "OOS" before TRAIN. Original script/CSV not available here, do not claim independent verification. External nine-pair public archive had selection bias, no controls, erroneous drawdown/MAE; 5/5 squeeze spike selected on spike.
R09 two exports differ in period/counts: no automatic merge and no claim cumulative. Long overnight gap could be sleep/stop/network, cause not proven. R09 60m unobserved ~26.6%; dashboard rank-replaced excluded from TP/SL-only denominator. R10 idle sleep request not protection from forced shutdown. Runtime forward data absent. Existing earlier "no ZIP available" statements apply only to other migrations, not this chat.
Online attempt failure unresolved and now deferred; public Funnel would expose unauthenticated API. No actual remote accessibility verified. No need to revisit until user requests.

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
Original screener's missed PIEVERSE/SKYAI events were user-reported; old logs/config and code snapshot absent, hence spot-only universe, 1h lag and restrictive RSI remain unverified possible causes. Spot lookup invalid for these symbols in original session; Futures valid. TradingCursor invalid symbol/cooldown prevented confirmation. Historical batch1/2 median approximation vs batch3 true median, incomplete 23 Nov last-bar cutoff, close-entry optimism, selection on later moves, cooldown and same-bar ordering limit pooling. External reported percentages cannot establish whale identity, direction, spot demand or proven liquidation. See [appendix](research/EARLY_DISCOVERY_2026-11-22_24.md).

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## Claude original artifact access and precise audit
Supersedes only prior access limitation for Claude source/CSV: all ten artifacts now available. [Detailed audit](research/CLAUDE_V1_ARTIFACT_AUDIT.md#e-source-code-audit-and-conflicts) confirms base exit-open split leakage 19 TRAIN/24 EXTRA, both versions 38/41; full-horizon crossing may be larger; 25/259 caught events have zero lead; raw recall not emitted alerts. Gross includes some slip; TP exit no slip, gap stop optimism, outcome-bar excursion ambiguity. Pair run-up is open-based and group controls drawn from remaining future-selected pool. Two tokenized-gold symbols included. Earlier source report OOS mostly before TRAIN, true TEST two events. No new runtime bug inferred; do not erase prior notes or promote these rules.

<!-- migration-note:2026-11-26-v05-scalp-swing-desktop-chat -->
## V0.5 side-branch issues: preserve separately from current R10

- **Version divergence:** branch `feature/v05-data-backtest-oneclick` includes dual Scalp/Swing engines with TOP80 default; current main has R08 default and R09/R10 research, with an older README saying ALL default. Do not cross-apply settings, database layouts or performance claims.
- **Incomplete signal reasoning:** `setup_active` holds latest Boolean but no immutable series of indicator-invalidated times/reasons; `EXPIRED` groups stop, timeout, missing observation, and Top5 rank replacement that should remain distinct. RSI warnings 60/40 do not cancel candidate signals.
- **Bug caught and fixed only on the feature branch:** Swing had a 15-minute hardcoded expiry in `_expire_unobserved` although configured for 3 days. Changed to `self.pending_ms` and regression-tested at `7e404b84`. Do not assume main R10 has that defect.
- **No evidence of production performance:** 1m REST input does not guarantee scanning all TOP80/ALL with minute latency; Swing 3-day choice is experimental, candidate TP/SL are close-based proxies and event counts are not fills. User trial logs and real P&L were not accessible. A cached live quote can be newer than its RSI/EMA candle.
- **Presentation/deployment limitations:** icons depend on an outside CDN (fallback initials); desktop app, Windows notifications/sound/tray, optional autostart/updater, and an append-only Signal Journal were **discussed but not implemented**. User did not authorize immediate desktop conversion.

[Feature evidence and historical code links](research/V05_SCALPING_SWING_FEATURE_CHAT_2026-11-22_25.md).
