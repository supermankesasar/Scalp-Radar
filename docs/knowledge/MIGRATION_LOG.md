# Migration Log — chat research and project history

## 2026-11-26 — this conversation → `docs/knowledge/`

**Scope:** the visible conversation beginning with a beginner asking how to build a crypto monitoring website; subsequent Windows/Android opening instructions; today's explicit knowledge migration request. Initial local date context 2026-10-08; per-message exact timestamps not independently recoverable. Only material accessible **in this conversation** was eligible; **other chats were not accessed or silently assumed**.

### Sources read

1. `analisis.txt` (local uploaded attachment): TradingAgents-inspired AI idea; decision-support first; monitor shark/whale and candles.
2. `kondisi-dasar.txt` (local uploaded attachment): historical Ajaib/Binance/MetaTrader/crypto-versus-forex context, late TP problem.
3. User and assistant messages in the visible chat: novice onboarding, Windows+Android, initial file/demo descriptions, illustrative TP/large-trade filters, promises and caveats about Mode contoh and non-order alert.
4. GitHub `main` tree, last commits and prior `docs/knowledge/INDEX.md` / `CURRENT_STATUS.md`.
5. Current research docs R01–R10, `README.md`, `DEPLOY_ONLINE.md`, `filters/multifactor.py`, `filters/r10.py`, R10 report generator and related operational docs; raw aggregate datasets linked rather than copied or recomputed.

### Newly integrated details

- Original user goals/pain point and beginner UX/hardware constraints, classified as USER-CHAT; early static HTML/GitHub Pages as historical concepts only.
- Source-aware progression from demo to current local R10 system, including explicit **no runtime AI/auto-trade** distinction.
- A versioned cross-reference to baseline/R07/R08/R09/R10 scoring, example-only thresholds versus live/shadow formulas.
- Preserved quantitative **negative** v0.5, R01–R05, R06 and R09 studies and counterexamples, with outcome limitations.
- R08 named case labels treated as **unverified discovery narratives**, not coin-specific validated studies.
- Conflicts: past cloud deployment suggestions vs R10 local-only; R07 default vs current R08; assistant's old example TP filters vs actual R10 formula config.

### Deduplication choices

- Existing research reports and raw JSON assets retained **unchanged** as authoritative. No duplicated raw batch JSON or fabricated recomputation; KB supplies a synthesis with direct links and selected representative tables.
- Existing `INDEX.md` links to R06–R10 were expanded, not discarded. Existing `CURRENT_STATUS.md` accurately stated R10/local/R08 and was elaborated without reversing its direction.

### Access limitations / unverified claims

- Prior assistant linked `crypto-whale-dashboard.html`, `whale-radar-starter.zip` and desktop/mobile screenshots; those **original generated files were not mounted/readable** in the migration session. The assistant's past claim of successful testing is **not independently verifiable** here.
- No additional chat transcripts, historical file contents from other conversations, user trade P&L, wallet data, private SQLite DB, current Binance connection, complete raw orderbook ticks, or per-coin user screenshots were accessible.
- This was a **documentation-only** migration; no source code, production config, database, files outside `docs/knowledge/`, or live deployments were changed.

**Source baseline SHA:** `b9e5b2883f958d053ab9db432cb4ddacbf839bbd`. The actual migration commit ID is in GitHub history and the completion report; not guessed in this file.
