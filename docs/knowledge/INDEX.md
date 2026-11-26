# Scalp Radar — Knowledge Base Index

Updated: 2026-11-26. Scope: consolidated knowledge with research provenance; **not** a trading recommendation or deployment approval.

## Reading order

1. [MASTER_PROJECT.md](MASTER_PROJECT.md) — user goals, constraints, scope.
2. [CURRENT_STATUS.md](CURRENT_STATUS.md) — current branch and operational/validation status (read this before historical files).
3. [DECISION_LOG.md](DECISION_LOG.md) — decisions, rationale, superseded approaches.
4. [RESEARCH_HISTORY.md](RESEARCH_HISTORY.md) — chronology and discovery vs validation.
5. [COIN_CASE_STUDIES.md](COIN_CASE_STUDIES.md) — named case hypotheses, evidence limits.
6. [FORMULA_DATABASE.md](FORMULA_DATABASE.md) — versioned rules, thresholds, scores and example-only values.
7. [EXPERIMENT_RESULTS.md](EXPERIMENT_RESULTS.md) — quantitative results, including failures.
8. [DATA_DICTIONARY.md](DATA_DICTIONARY.md) — sources, fields, timestamps and horizons.
9. [DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md) — prototype-to-R10 evolution.
10. [KNOWN_ISSUES.md](KNOWN_ISSUES.md) — gaps, conflicts, risks, operational caveats.
11. [FUTURE_RESEARCH.md](FUTURE_RESEARCH.md) — unvalidated ideas and next experiments.
12. [MIGRATION_LOG.md](MIGRATION_LOG.md) — sources inspected, deltas, inaccessible material.

## Existing primary research (authoritative for full methods and raw aggregates)

- [v0.5 exploratory backtest](../../research/BACKTEST_V05_2026_REPORT.md)
- [R01–R05 technical follow-up](../../research/TECHNICAL_FOLLOWUP_2026-11-24.md) and [methodology](../../research/README_TECHNICAL.md)
- [R06 report](../../research/R06_REPORT_2026-11-24.md) and [runner notes](../../research/README_R06.md)
- [R07 Scalp V2](../../research/R07_SCALP_V2.md)
- [R08 multifactor](../../research/R08_MULTI.md)
- [R09 WebSocket](../../research/R09_WEBSOCKET.md)
- [R10 local research](../../research/R10_RESEARCH.md)
- [Overnight collection](../../research/OVERNIGHT.md)
- Source datasets and immutable samples: [research/](../../research/); implementation: [filters/](../../filters/), [app.py](../../app.py), [signals.py](../../signals.py), [stream_engine.py](../../stream_engine.py).

## Evidence conventions

**VERIFIED-REPO** = observed in repository documentation/code at migration; not proof of on-device performance. **USER-CHAT** = user requirement from this conversation. **ASSISTANT-CHAT** = proposal or claim in old assistant response, not independently verified. **HYPOTHESIS** = unvalidated proposed mechanism. **EXPLORATORY** = retrospective non-independent test. **SHADOW** = recorded/tested but not live ranking. **CURRENT** = checked against main on 2026-11-26. **HISTORICAL / SUPERSEDED** = preserved for provenance, not current behavior.

Do not merge experiment tags into a single success metric, infer whale identity from volume/flow, promote rules from a discovery sample, or infer real fills from candle-close outcomes. For exact numbers, prefer the linked original research over this navigational synthesis.
