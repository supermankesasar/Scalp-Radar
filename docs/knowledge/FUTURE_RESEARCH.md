# Future Research — hypotheses and unimplemented ideas

**Not approved trading signals.** Maintain data provenance, pre-register criteria, run outside the discovery sample, report both negative and positive results.

| Priority | Question / experiment | Design and acceptance criteria | Status |
|---|---|---|---|
| 1 | Can R10/R09 rules survive real-time monitoring and costs? | Freeze rule/version and cohorts; observe fixed holdout, report event-level + symbol/day clusters, regime, latency, missingness, 0.10/0.20/0.35% sensitivity; independent holdout before promotion | Prospective infrastructure exists; validation outstanding |
| 2 | Are large-trade/flow events helpful beyond candle/volume baseline? | Compare `aggTrade`, taker delta, partial depth, liquidations/OI with baseline at matched timestamps and coverage; never label known whales | Shadow hypotheses; no actor labels |
| 3 | Does exhaustion/reversal remain after removing dominant contributors? | Robustness by coin/day, compare excluding EVAA/BIGTIME, new periods; prevent cherry-picking after observation | Historical audit unstable |
| 4 | Does delayed observation erase the signal? | Measure signal decision→receipt→eligible entry, 1m vs 5m baseline, stale windows and costs; include missing/UNOBSERVED | Open |
| 5 | Can TP reminders reduce late exits without encouraging overtrading? | Separate `watch` alerts from trading; test exit policy against preset hold/stop on paper positions, UI/browser notification delivery and permission handling | User pain point, **not** tested |
| 6 | Which regime differences are real? | Synchronized universe coverage, BTC-relative breadth, long/short split and time-block holdout; compare matched eligible samples | R10 regime logic exists; validation open |
| 7 | Is an optional AI commentary layer useful? | AI reads versioned snapshots and evidence, explains uncertainty, never fabricates whale identity or executes orders; measure cost, hallucination and false confidence | Early aspiration only; **no runtime AI** |
| 8 | Reliable access across Windows and Android | Only after user authorizes network deployment, design authenticated remote access, uptime, source freshness, persistent disk; distinguish local loopback from HTTPS mobile | Deferred by R10 **local-only** directive |
| 9 | Full case study reconstruction | Require symbol, UTC time, timeframe, OHLCV/flow/depth source and receipt, decision, outcomes, contrary examples | Named R08 narratives have no independent case-level data in accessible chat |

Method template for each future experiment: date/period, pair/eligibility, regime, timeframe, source and receipt, version/thresholds, hypothesis, preregistered protocol, sample N + independent clusters, net-cost scenario, missing-data count, results incl. nulls, failure modes and explicit promotion decision. Preserve rejected/deprecated variants.
