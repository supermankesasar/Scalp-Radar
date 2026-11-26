# Master Project — purpose, boundaries, preferences

## Original user requirements (USER-CHAT; initial context 2026-10-08)

- User is a **beginner in trading and coding**; wants step-by-step, practical assistance rather than assuming programming experience.
- Initial goal: a browser-based **decision-support tool**, monitoring candlestick movement and signs of large participants described as “shark/whale”; inspiration: [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents). Inspiration is not evidence of AI integration or a required architecture.
- Pain point: **late take-profit decisions**, including watching a coin rise and failing to act in time. Price/TP alerts and a clear, cautious presentation matter.
- Initial context: used Ajaib, newly installed Binance but had not used it, had seen MetaTrader without trying it, and was undecided between crypto and forex. This is **historical discovery context**, not proof of current exchange usage or trade activity.
- Hardware/access preference: **Windows laptop and Android phone**; wants very basic instructions, low setup friction.
- No request to execute orders in this chat. Distinguish observation, simulated status, alert, and actual trading execution.

## Current scope and non-goals (CURRENT; VERIFIED-REPO)

- Current system is Scalp Radar, a local Python/Windows **Binance USDⓈ-M USDT perpetual** scanner and research ledger with desktop/mobile web UI capability, not the one-file early prototype.
- **R08_MULTI_CORE** is live default *ranking/monitoring filter*, while R09/R10 research is independent/shadow unless explicitly configured as documented. A watchlist is not a validated entry recommendation.
- **No auto-trading, Binance account keys, runtime/paid AI, or order placement.** R10 user direction is local-only; prior hosting guidance is historical, not present authorization.
- Preserve evidence of failed experiments, avoid look-ahead and false precision; compare directional setups under realistic fee, latency, regime and data-coverage constraints.
- Prioritize availability/freshness of data and actual outcome observation over flashy scoring, and **do not treat whale/shark identity as directly observable** from order flow, account ratios or aggregated prints.

## Product philosophy

Beginner-readable labels for Potential vs Confirmed, source freshness and insufficient data; explicit **No Trade / Watch** states; TP monitoring as a research requirement, not a promise of push notifications or guaranteed fills. Consider a future optional AI analysis layer only after stable data provenance, validation, and cost/security review.

Sources: this conversation, `analisis.txt`, `kondisi-dasar.txt`; [README](../../README.md), [R08](../../research/R08_MULTI.md), [R10](../../research/R10_RESEARCH.md).
