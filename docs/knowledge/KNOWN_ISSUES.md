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
