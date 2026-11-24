# Modular R06 and scanner staging
Branch research/modular-r06; no production deployment or main merge.
 
- Python backend: filters/*.py are pure rules; registry.py composes the legacy score (unchanged) and independent EMA9 cross / EMA21 pullback / EMA21 1h shadow candidates for the new 30. R06 experimental positioning rules remain in research/filters/*.cjs; no unvalidated score in production.
- research_history.py uses the existing SQLite path and additive tables. Candidate records are independent of Top5. Evaluation: 15/30/60m x close 5/15m. Missing beyond retry is UNOBSERVED. This is a candle outcome ledger, not a fills/PnL or continuously live validity engine.
- research/cohorts/r06_30.json fixes the new cohort; old 28 are archived research only. Live baseline remains ALL/LIQUID/TOP80 according to existing UI.
- research/results/r06_C1...C10.json, r06_summary.json and R06_REPORT_2026-11-24.md record the actual completed replay.
- Generated bundle is a frozen execution artifact used for connector limits, not canonical source. Use research/r06_replay.cjs and individual modules for modifications.
 
## Repeat research (read-only)
Node >=18; no npm dependencies.
```sh
node research/run_r06.cjs
node research/run_r06.cjs path/to/config.json
```
Config: symbols (USDT contracts), windows (UTC end of each 2h window, e.g. ["2026-11-24T08:00:00Z"]), runId, outputDir. Each run creates a new directory with raw responses, SHA256 manifest, module hashes, candidate JSONL, and result.json. Old data may exceed API retention; errors/coverage are explicit. Standalone REST runner has not been tested on the user's host.
 
## Staging Python verification and archive
```sh
python -m unittest discover -s tests -p "test_modular_filters.py"
python -m unittest discover -s tests -p "test_research_history.py"
python research/import_history.py data/signals.sqlite3
```
The importer combines archived R01–R05 and R06 candidate snapshots with explicit run IDs in the same SQLite file, without deleting prior results. It has not been executed on production. The live staging API /api/research exposes aggregate candidate/outcome counts. A frontend research panel and live R06 feature collection remain separate future changes. Offline checks: four Python unit tests passed on the exact GitHub blobs (baseline parity, independent EMA timing, all-candidate dedup/outcomes, missing data). The R06 replay also passed synthetic future-data isolation and missing-data tests. Full scanner startup/hosting and standalone REST runners remain unverified; verify integration before merge.
