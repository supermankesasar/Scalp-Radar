# Technical research (R01–R05 follow-up)
Branch: research/technical-r01-r05. Production main remains unchanged.
 
## Run
Optional Node.js 18+ research utility, no npm dependencies. Existing Python app and deployment remain separate.
 
```sh
node research/run_technical.cjs
node research/run_technical.cjs path/to/config.json
node research/test_technical.cjs
```
 
Config example:
```json
{"runId":"example-20261124","end":"2026-11-24T08:00:00Z","symbols":["BTCUSDT","ETHUSDT"],"windows":[["anchor","2026-11-24T08:00:00Z"]]}
```
Windows specify the **end of the second hour** in UTC; the first hour scans every closed 5m candle. Each event is evaluated at 15/30/60m, with only closed bars available at detection. Use smaller date ranges if needed to fit the warm-up and endpoint limit. The CLI fetches Binance public data; network/access/rate-limit failures are surfaced and no access bypass is attempted. The actual research results were collected via the Binance connector and evaluated with the same core engine. The standalone HTTP runner is provided for future replay; live execution on the user's host has not been verified.
 
Each local run gets a unique output folder (default data/research-runs), an immutable config, raw responses + SHA256 manifest, candidate JSONL and summary. Keep raw files out of Git and production DB; the six dated GitHub audit files are a bounded research sample, not a long-term market-data store. Summary arrays: n, target, stop, gross-direction-positive count, net sum (% points), gross horizon sum (% points), chase rejects. Dated summary.json converts sums to averages. Strata distinguish first baseline episode from first transition into a variant. All candidate rows are retained, no Top5/cooldown in research; episode starts are approximate and reset at each window. 
   
## Hypotheses
B21 original 21/21. E9_21, E9_9, E21_9 change short EMA periods; E15_SCORE9_ONLY and E15_GATE9_ONLY isolate the distance gate. T1 variants isolate 1h score/gate or substitute EMA50/21, with 4h unchanged. MOM variants compare joint RSI/MACD score removal, both/either, acceleration. FAST variants require cross or prior-EMA touch/rejection within the 9/9 full rule. VOL bins use 5m quote turnover/mean previous 20 bars. VW bins use signed distance in 5m ATR units from UTC daily VWAP. LS is account share (not notional or contract direction), lagged one completed 5m interval, change comparison at 15m. Missing data excluded from ratio-only stratification. No new scoring weights; no auto execution.
 
## Limitations
Eight short windows across two dates; timecheck is a later-window descriptive check, not conclusive independent holdout. Correlated pair/time and repeated candidate outcomes. Close-based target/stop and next-open proxy entry with assumed 0.20% round-trip costs; not fills or portfolio results. 1h/4h context reconstructed from closed candles. No production latency emulation. Candidate observations include variants not shown on dashboard. Avoid selecting weights based on this sample; run more separated windows and forward test.
 
## Integration boundary
Production changes require a separate reviewed change: shared filter definitions, candidate ledger independent of UI ranking, versioned immutable outcomes, risk/validity, and data freshness gates. Do not enable experimental signals in main based solely on this report.
