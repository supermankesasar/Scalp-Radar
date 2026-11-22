# Data Engine + Backtest — One-click experimental integration

## Windows usage
1. Download the ZIP of branch `feature/v05-data-backtest-oneclick` (not the old `main` ZIP).
2. Extract to a new folder (do **not** overwrite the currently running scanner folder).
3. Double-click `START-WINDOWS.bat`. Requires Python 3.10+ and internet.
4. Open `http://127.0.0.1:8765/research.html` or click **Data Engine + Backtest** on the home page.
5. Keep the terminal open to keep scanner and research running. Closing the browser does not terminate the server.

## What is implemented
- The original v0.5 scanner, signal logic and SQLite archive are retained.
- On Windows start, `RESEARCH_AUTO=1` starts a daemon collector.
- Download the most recent 7 days of fully closed **5m** candles for BTCUSDT, ETHUSDT, SOLUSDT from Binance USD-M futures public REST, with a request gap between batches.
- Local `data/market_history.sqlite3` has a UNIQUE (symbol, open_ms) key and validates OHLC. Existing complete chunks are not re-downloaded.
- Per-symbol gap counts are displayed. Missing candles are not invented; checks do not overwrite historical conflicts.
- Inspect **recorded scanner events**, if any, and evaluate simplified hypothetical 3-bar exits, with next-bar entry, stop-first wick evaluation and **0.20% round-trip costs**. Save `research/recorded_event_backtest.json`.
- Results are clearly labeled **NOT A FULL BACKTEST OF THE V0.5 SCANNER**, and cannot be compared directly with the 2,950-event research report. No execution, no orders, no automatic trading.
- Automatic hourly checks are in-process and therefore stop when the Python process stops. They do not run when the PC is off.
- Hosted environments default to `RESEARCH_AUTO=0` unless explicitly enabled, so no unnecessary background download burden is imposed.

## Safety and limitations
- Historical source availability is controlled by Binance; network restrictions and rate limits may prevent sync.
- 7 days is an initial rolling bootstrap window, **not** a long-term historical backfill or 5-year archive.
- Current standalone evaluator uses a fixed 0.65% TP and 0.40% SL, not the historical ATR-adaptive v0.5 thresholds. It ignores funding, full tick execution, queue delay and leverage.
- If no recorded event falls in the archive and among these 3 symbols, performance metrics stay N/A.
- The stored data is research-only. No model training or historical all-symbol strategy replay is started by clicking Start.
- Do not delete the `data` folder when updating to newer builds; back up SQLite files first.

## Offline checks
Run `python -m unittest discover -p "test_*.py" -v` from the downloaded project folder.
These tests do not rely on Binance connectivity. Live end-to-end verification has not yet been completed.
