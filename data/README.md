# Backtest data

Drop `get_equity_historicals` responses here as `<name>.json`, verbatim —
no reshaping. `backtest.py` reads the whole MCP envelope, splits multi-symbol
responses by their `symbol` field, and drops interpolated (gap-fill) bars.

Fetch with:

    get_equity_historicals(
        symbols=["ACIW", "FTI", "XYZ", ...],   # up to 10 per call
        start_time="2024-01-01T00:00:00Z",
        interval="day",
        adjustment_type="split",
    )

Then:

    python3 backtest.py --self-test        # validate the harness first
    python3 backtest.py --data data/       # baseline + trend-filter comparison
    python3 backtest.py --data data/ --sweep

Aim for enough symbols and history to clear ~100 trades minimum; a few
hundred is where the numbers start meaning something. See
STRATEGY_RESEARCH_2.md §1 for why sample size is the binding constraint.

JSON files here are gitignored — this is scratch data, refetchable at any time.
