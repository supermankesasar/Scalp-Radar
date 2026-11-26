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

<!-- migration-note:2026-11-26-scalping-swing-local-ai-arkham -->
## 2026-11-26 — migrasi tambahan dari chat scalping futures / swing / Arkham / AI lokal

**Konteks:** saat audit, main berubah dari `b9e5b2883f958d053ab9db432cb4ddacbf839bbd` ke `14a3414b98dfe2b2334dbffb7898f2753e18dfb5` akibat **commit migrasi Knowledge Base dari chat lain**. Tidak dilakukan penulisan berdasarkan snapshot lama. Semua 13 file Knowledge Base baru pada commit `14a3414b` dibaca ulang; migrasi ini **hanya menambahkan delta chat yang belum dicakup**, tidak menghapus atau mengganti catatan percakapan lain. Sumber code/research lama tetap dibaca untuk memisahkan proposal dari implementasi.

### Materi chat dan lampiran yang bisa diakses

1. **USER-CHAT:** pengguna menolak bentuk custom web lama dan lebih memilih framework trading-AI web yang sudah ada, memakai model AI di komputernya sendiri; user menempelkan ringkasan Google tentang TradingView/webhook, Streamlit/Gradio, Backtrader/Jesse, OpenAlgo, QuantDinger/OpenByte OS, HKUDS AI-Trader, TraderMagic. Ini **kutipan pengguna**, bukan audit independen fitur tiap platform.
2. **ASSISTANT-CHAT:** asisten merekomendasikan QuantDinger + Ollama dan menggambarkan pilihan timeframe/scalping; bukan pengesahan bahwa komponen tersebut terpasang.
3. **USER-CHAT:** gaya trading kini **scalping futures dan swing trade**; **whale monitor dikesampingkan** karena Arkham dapat digunakan secara terpisah.
4. **ATTACHMENT:** analisis.txt membahas TradingAgents, alat bantu beginner, candles dan awalnya shark/whale; kondisi-dasar.txt membahas aplikasi awal, eksplorasi forex/crypto, dan masalah terlambat TP. Kedua file tersedia/dibaca penuh; informasi umum yang sudah tercantum di KB lain tidak digandakan.
5. **REPO:** audit struktur main, commit mutakhir, seluruh KB yang ada, laporan R01–R10, filter/runner/data ledger yang relevan; implementasi **R08 CORE default, R09/R10 shadow, tanpa runtime AI dan tanpa auto-order** tetap otoritatif.

### Delta dan deduplikasi

**Ditambahkan** ke MASTER_PROJECT, DECISION_LOG, RESEARCH_HISTORY, DEVELOPMENT_HISTORY, FUTURE_RESEARCH, CURRENT_STATUS, KNOWN_ISSUES, dan INDEX: preferensi trading scalping/swing, keputusan Arkham, alasan web custom tidak cocok, opsi framework/AI lokal sebagai proposal, serta gap validasi mode swing. **Tidak disalin ulang:** semua numerik v0.5/R01–R10 yang sudah lengkap di EXPERIMENT_RESULTS, parameter aktif di FORMULA_DATABASE, tabel definisi DATA_DICTIONARY, atau motif COIN_CASE_STUDIES. Tidak ada formula, coin dataset, statistik eksperimen, atau threshold baru dari chat ini.

### Konflik dan batas akses

- **Kebutuhan awal whale** vs **penggunaan Arkham dan whale diprioritaskan rendah**: perubahan keinginan pengguna. Kebutuhan awal disimpan sebagai sejarah.
- **Saran QuantDinger/Ollama** vs **main R10 tanpa LLM**: ide belum diterapkan, bukan state produksi.
- **Saran timeframe asisten** vs **konfigurasi pengguna**: tidak ada timeframe yang disetujui secara eksplisit dalam chat ini.
- Tidak tersedia transkrip chat lain di luar yang ditampilkan, original raw coin cases, database PC, screenshots lokal, hasil live-trade atau spesifikasi hardware PC. Klaim lampiran/diskusi lain pada catatan migrasi sebelumnya tidak diubah.
- Tidak ada perubahan pada kode, formula aktif, konfigurasi, database, atau file di luar docs/knowledge. Commit ini harus dibaca dari riwayat GitHub, bukan dari perkiraan ID.

<!-- migration-note:2026-11-26-r09-r10-operational-audit -->
## 2026-11-26 — R09/R10 operational chat and uploaded research handoffs
Base main 3bfc820969376ec5835e7b8eaf6e5da850f80381; inspected all 13 existing KB files, repository tree and CI. All updated additively, no new files. Directly read both Pasted text handoffs, analisis.txt and kondisi-dasar.txt; original requirements already recorded. Reopened 26 Nov ZIP and SQLite, verified quick_check, counts and R09 60m aggregate query. 25 Nov ZIP present; numerical audit transcribed from earlier conversation, not recomputed in this migration. Claude original Python and CSV files named in handoff (crypto_pattern_research.py, RESEARCH_HANDOFF_REPORT.md, pairs.csv, events.csv, event_snapshots.csv, trades.csv, backtest_summary.csv, indicator_auc.csv, tuning_log.csv, params.json) not directly available; reported numbers and audit preserved as secondary evidence. Other AI source datasets, full chat transcripts outside accessible context, live PC and R10 holdout not accessible. No raw SQLite, credentials, personal identifiers or tunnel addresses committed.
Delta: 45 pair cohort and timestamped cases, initial failed rules, 620 snapshot stats, squeeze/Claude AUC and OOS negatives and limitations, market-wide sync; detailed R09 audit counts/outcomes, R10 exact exit thresholds and data schema; historical online attempts and user directive to defer; operational-first decision superseding research-before-coding. Existing R01–R10 reports, old prototype and AI-local/swing migration retained unchanged; duplicated numerical summaries and initial requirements not copied wholesale. Earlier statements "no raw ZIP/case data" refer to their own chats; this migration adds accessible summaries and R09 ZIP verification. Windows CI earlier pending now success. No code, configs, database or files outside docs/knowledge modified. No new trading validation performed.

<!-- migration-note:2026-11-26-early-45-pair-chat-detail -->
## 2026-11-26 — original early 45-pair discovery conversation
Base main 3e9ca4e4e4c9ec11d41a58e8f320ba89a6b291d1. Read repository tree, all 13 KB files, R10 report and filter registry; compared to b9e5b28 code baseline (three intervening docs-only commits). Reviewed accessible initial chat context, Binance-derived observations/tool outputs, original research discussions, master handoff, mounted analisis.txt and kondisi-dasar.txt, full supplied Pasted text.txt (nine-pair external report) and Pasted markdown.md (illustrative follow-up). The initial PIEVERSE/SKYAI portions are available through retained conversational summary rather than entire original tool arrays. External source sites not independently reopened; no raw full candle/depth/tick data, original screener logs/config, source code from old version, independent live PC, original screenshots, other AI raw datasets or actual trading P&L available in this chat. No new market experiment run.
Added research/EARLY_DISCOVERY_2026-11-22_24.md and linked relevant existing files; details include timelines, per-pair cohort statistics, failed signals, ablations, historical formulas, external source limitations and exact NIGHT retest. Deduplicated already recorded 45-pair roster, aggregate results, synchronization example and R08/R10 implementation; retained latest operational-first decision, earlier research-first gate only historical. Conflicts/corrections: SKDD TradFi excluded, RVOL median vs mean/version differences, peak-to-end vs MAE, external 5/5 selection bias, and independent indicator definitions. Current operational state unchanged. No code, active formulas, production config, database or outside-KB file modified. Actual commit ID in GitHub history; no guessed SHA.

<!-- migration-note:2026-11-26-claude-v1-original-artifacts -->
## 2026-11-26 — Claude V1 original-artifact supplement from early research chat
Base main 3d5f55fcaf2c203f4024e370c50f3f06cb51e998. Read repo recursive tree, all 13 root KB files and existing early-discovery appendix, R10 report and filter registry; compared with b9e5b28 (four docs-only commits). Reviewed entire accessible chat and original research handoffs, both external archive reports and requirement attachments (already recorded by prior migration), original Claude report, source, params and seven CSV files. Local pandas recomputed counts, fee and grouped returns, cross-boundary/zero-lead counts, clustering and directional AUC; Python source AST syntax parsed; no rerun of exchange backtest. Added two research appendices with SHA-256 manifest, exact V1 formulas and methodology, 131 pair summaries, original OOS and actual TEST stats, cases, contradiction and data dictionary; linked from INDEX and relevant files. Original source/CSV access limitation in previous migrations now resolved for these uploads; no raw OHLCV arrays, actual fills, old scanner logs, independent live PC or other AI complete datasets. Original earlier turns partially retained as conversational summary; original full connector arrays unavailable. No additional Gemini/DeepSeek full report available here. Deduplicated 45-pair roster/cases/early calculations and public archive findings already in EARLY_DISCOVERY, Claude headline counts/negative OOS and current R10 docs; 132 symbols union unchanged. Conflict: latest operational-first directive overrides historical research-first coding gate; different RVOL, efficiency, timestamp, drawdown/run-up and outcome definitions are versioned; TP fee/slip and recall limitations explicitly documented. No raw CSVs/source duplicated into public repo (retain locally; manifest identifies bytes); no credentials/personal info, production code, active formulas, config, database or non-KB files changed. Commit ID recorded by GitHub history, not guessed.
