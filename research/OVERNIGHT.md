# Overnight ALL-pair forward collection (Windows)

Use branch research/modular-r06. Stop any existing Scalp Radar instance first. Python 3.10+ and Git (or download branch ZIP); no pip packages, Binance API keys, exchange account or Node required. Double-click START-WINDOWS.bat (one launcher for daytime and overnight; run_overnight.bat is only a compatibility alias). Browser http://127.0.0.1:8765. Status http://127.0.0.1:8765/api/overnight and candidate evaluation /api/research. Server binds localhost only. Keep the terminal and Windows awake, network available; browser can close. Check archive progress and error counts before leaving. Overnight forces ALL active crypto USDT perpetuals, including former cohorts, irrespective of UI dropdown. Excludes non-crypto traditional asset futures and gold proxies. Research cohort is not a live restriction.

The existing central SQLite database data/signals.sqlite3 receives live candidate rows and immutable outcomes independent of Top5. Archive also records raw 5m klines (OHLCV, taker buy/sell data), historical OI, global account ratio, top trader account and position ratios, bulk mark/funding and 24h ticker snapshots; longer timeframe candles are archived when the scanner fetches them. The archive cycles are paced at >=30 minutes between starts, potentially longer depending on the network; each stats response contains 5-minute history and the actual received_at is stored. Not simultaneous 5-minute live polling. API restrictions/errors are logged; no bypass. No historical order book, full trade stream or liquidation capture yet. Live R06 market activity scoring not enabled. Data collection is local; GitHub receives code only.

Morning: double-click export_overnight.bat, upload the ZIP from exports/ to the chat. The SQLite backup API creates a consistent copy even with WAL writes ongoing. Do not copy only the live database file while running. No API key or account data collected. Verify free disk space and permission to use office PC/network overnight. No auto orders.

Staging branch, main unchanged. Host startup/network tests have not been verified here.

## R07 experimental filter (2026-11-25)
See [R07_SCALP_V2.md](R07_SCALP_V2.md). R07 originally defaulted to SCALP_V2 live ranking; previous rules are retained as independent research controls. Set SCANNER_LIVE_FILTER=BASELINE before launching to roll back ranking without deleting data.

## R08
START-WINDOWS.bat now defaults to R08_MULTI_CORE and enables the full collector; see [R08_MULTI.md](R08_MULTI.md) for hypotheses, data coverage and rollback modes.
