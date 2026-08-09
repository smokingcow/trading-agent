#!/usr/bin/env python3
"""
Backtest harness for the dip-buy loop.

Why this exists: the live loop produces ~150 round-trips a year, and
distinguishing a real edge from luck needs 92-737 closed trades (see
STRATEGY_RESEARCH_2.md section 1). That is 7 months to 5 years of live
trading. This harness gets the same sample size from historical bars in
seconds, so parameters are settled by evidence instead of argument.

Data in: JSON files of OHLCV bars as returned by the Robinhood MCP
`get_equity_historicals` tool. Dump them with:

    get_equity_historicals(
        symbols=["ACIW", "FTI", ...],      # up to 10 per call
        start_time="2024-01-01T00:00:00Z",
        interval="day",
        adjustment_type="split",           # correct default for backtesting
    )

and write each response verbatim to data/<name>.json - no reshaping needed.
The whole envelope is accepted ({"data": {"results": [{"symbol", "bars"}]}}),
including multi-symbol responses, which are split out automatically by the
"symbol" field. A bare list of bars also works, in which case the filename
supplies the symbol.

Bars flagged interpolated=true are dropped: they are server-side gap fill
and carry no traded prices, so keeping them would invent highs and lows that
fire phantom stops and targets.

Put a benchmark (SPY by default) in the same directory. Without one, results
are RAW returns, which over a rising market credit market beta as though it
were strategy edge - the exact mistake that hid the live loop's 6.7pp
shortfall behind a "-2.4%" that looked mild.

Usage:
    python3 backtest.py --self-test
    python3 backtest.py --data data/                    # excess vs SPY
    python3 backtest.py --data data/ --sweep
    python3 backtest.py --data data/ --compare-stops    # absolute vs relative
    python3 backtest.py --data data/ --regime-gate --trend-filter

No third-party dependencies - it runs anywhere the loop runs.
"""

import argparse
import glob
import json
import math
import os
import random
import statistics
import sys

# Defaults mirror AGENT_PROMPT.md judgment calls #2, #3, #5 and the
# measured slippage from the 2026-08 stop-outs (1.5-1.8% past trigger).
DEFAULT_TP = 6.0
DEFAULT_SL = 7.0
DEFAULT_MAX_HOLD = 12
DEFAULT_SLIPPAGE = 1.5
DEFAULT_DIP = -6.0
EMA_PERIOD = 200


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def _num(value):
    """Robinhood returns numerics as strings; tolerate both."""
    if value is None:
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def normalize_bars(raw):
    """Convert one symbol's raw bar list into sorted OHLCV dicts."""
    bars = []
    for entry in raw:
        # Interpolated bars are gap-fill synthesized by the server and carry
        # no new information. Keeping them would invent highs and lows that
        # never traded, firing phantom stops and targets.
        if entry.get("interpolated") is True:
            continue
        bar = {
            "date": entry.get("begins_at") or entry.get("date"),
            "open": _num(entry.get("open_price") or entry.get("open")),
            "high": _num(entry.get("high_price") or entry.get("high")),
            "low": _num(entry.get("low_price") or entry.get("low")),
            "close": _num(entry.get("close_price") or entry.get("close")),
            # Carried for panel_study.py's rel_volume feature. Not used by the
            # simulator, but dropping it here silently disabled that feature.
            "volume": _num(entry.get("volume")) or 0.0,
        }
        # A bar missing any price, or with a non-positive price, cannot be
        # simulated against - drop it rather than silently trading on zeros.
        if all(bar[k] is not None and bar[k] > 0 for k in ("open", "high", "low", "close")):
            bars.append(bar)

    bars.sort(key=lambda b: b["date"] or "")
    return bars


def extract_symbols(raw, fallback_symbol):
    """
    Pull {symbol: bars} out of whatever shape the file holds.

    Accepted:
      - the get_equity_historicals envelope: {"data": {"results": [{"symbol", "bars"}]}}
        (possibly several symbols, since the tool takes up to 10 per call)
      - a single symbol's payload: {"bars": [...]} or {"historicals": [...]}
      - a bare list of bar objects
    """
    if isinstance(raw, list):
        return {fallback_symbol: normalize_bars(raw)}

    if not isinstance(raw, dict):
        return {}

    body = raw.get("data") if isinstance(raw.get("data"), dict) else raw

    results = body.get("results")
    if isinstance(results, list) and results:
        out = {}
        for result in results:
            if not isinstance(result, dict):
                continue
            symbol = (result.get("symbol") or fallback_symbol).upper()
            out[symbol] = normalize_bars(result.get("bars") or [])
        return out

    for key in ("bars", "historicals"):
        if isinstance(body.get(key), list):
            return {fallback_symbol: normalize_bars(body[key])}

    return {}


def load_data(path, min_bars=30):
    """Load {symbol: bars} from a directory of JSON files or a single file."""
    files = sorted(glob.glob(os.path.join(path, "*.json"))) if os.path.isdir(path) else [path]
    if not files:
        sys.exit(f"No JSON files found in {path!r}")

    data = {}
    for filepath in files:
        fallback = os.path.splitext(os.path.basename(filepath))[0].upper()
        try:
            with open(filepath) as handle:
                extracted = extract_symbols(json.load(handle), fallback)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  ! skipping {filepath}: {exc}", file=sys.stderr)
            continue
        if not extracted:
            print(f"  ! {filepath}: no recognizable bar data", file=sys.stderr)
            continue
        for symbol, bars in extracted.items():
            if len(bars) < min_bars:
                print(f"  ! skipping {symbol}: only {len(bars)} usable bars "
                      f"(need {min_bars})", file=sys.stderr)
                continue
            data[symbol] = bars
    return data


# --------------------------------------------------------------------------
# Indicators
# --------------------------------------------------------------------------

def ema(values, period):
    """EMA aligned to `values`; None until `period` samples are available."""
    out = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    k = 2.0 / (period + 1)
    prev = seed
    for i in range(period, len(values)):
        prev = values[i] * k + prev * (1 - k)
        out[i] = prev
    return out


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------

def simulate(bars, tp_pct, sl_pct, max_hold, slippage_pct, dip_threshold,
             use_trend_filter=False, ema_period=EMA_PERIOD,
             benchmark=None, stop_mode="absolute", stop_floor_pct=15.0,
             regime_gate=False):
    """
    Replay the loop's entry/exit rules over one symbol's bars.

    No lookahead: the dip signal is evaluated at the close of bar i, and
    entry fills at the OPEN of bar i+1 - which is what the live loop
    actually achieves, since it scans during the session and buys after.

    When a single bar's range contains both the stop and the target, the
    stop is assumed to fill first. Daily bars cannot resolve intrabar
    ordering, so the harness takes the pessimistic branch rather than
    flattering the strategy.

    `benchmark` is a {date: close} map (normally SPY). When supplied, each
    trade also carries the benchmark's return over the IDENTICAL window and
    the excess of one over the other. Excess is the number that matters:
    raw returns over a rising market credit beta as though it were edge.

    `stop_mode` selects how the stop trigger is computed:
      "absolute" - fixed -sl_pct from entry. This is what runs live.
      "relative" - the trigger widens by however much the benchmark has
                   fallen since entry, so a market-wide drop does not
                   liquidate the position. Unbounded.
      "floored"  - as "relative", but never wider than -stop_floor_pct.

    The relative modes exist to be TESTED, not because they are endorsed.
    See the callout in AGENT_PROMPT.md: five correlated positions make a
    widened stop a portfolio-level risk, not a per-position one.
    """
    closes = [b["close"] for b in bars]
    trend = ema(closes, ema_period) if use_trend_filter else None

    bench_trend = None
    if regime_gate:
        if not benchmark:
            raise ValueError("regime_gate=True requires a benchmark series")
        # EMA over the benchmark, aligned to THIS symbol's trading dates so
        # the lookup below cannot drift out of sync.
        bench_closes = [benchmark.get(b["date"]) for b in bars]
        usable = [c for c in bench_closes if c is not None]
        if len(usable) >= ema_period:
            filled, last = [], None
            for c in bench_closes:
                last = c if c is not None else last
                filled.append(last if last is not None else usable[0])
            bench_trend = ema(filled, ema_period)

    trades = []
    warmup = ema_period if (use_trend_filter or regime_gate) else 1
    i = max(1, warmup)
    n = len(bars)

    while i < n - 1:
        pct_change = (closes[i] - closes[i - 1]) / closes[i - 1] * 100.0
        if pct_change > dip_threshold:
            i += 1
            continue
        if use_trend_filter and (trend[i] is None or closes[i] < trend[i]):
            i += 1
            continue
        if regime_gate:
            bench_now = benchmark.get(bars[i]["date"])
            if bench_trend is None or bench_trend[i] is None or bench_now is None \
                    or bench_now < bench_trend[i]:
                i += 1
                continue

        entry_idx = i + 1
        entry = bars[entry_idx]["open"]
        tp_price = entry * (1 + tp_pct / 100.0)
        bench_entry = benchmark.get(bars[entry_idx]["date"]) if benchmark else None

        exit_price = exit_idx = reason = None
        for j in range(entry_idx, min(entry_idx + max_hold, n)):
            # Recompute the stop each bar - under the relative modes it moves
            # with the benchmark.
            effective_sl = sl_pct
            if stop_mode != "absolute" and bench_entry:
                bench_now = benchmark.get(bars[j]["date"])
                if bench_now:
                    bench_move = (bench_now - bench_entry) / bench_entry * 100.0
                    if bench_move < 0:
                        effective_sl = sl_pct - bench_move  # widen by the drop
                    if stop_mode == "floored":
                        effective_sl = min(effective_sl, stop_floor_pct)
            sl_price = entry * (1 - effective_sl / 100.0)

            if bars[j]["low"] <= sl_price:
                # Market exit slips past the trigger, as measured live.
                exit_price = sl_price * (1 - slippage_pct / 100.0)
                exit_idx, reason = j, "stop"
                break
            if bars[j]["high"] >= tp_price:
                # Limit exit fills at the target.
                exit_price = tp_price
                exit_idx, reason = j, "target"
                break

        if exit_price is None:
            exit_idx = min(entry_idx + max_hold, n) - 1
            exit_price = bars[exit_idx]["close"]
            reason = "timeout"

        ret = (exit_price - entry) / entry * 100.0
        trade = {
            "entry_date": bars[entry_idx]["date"],
            "exit_date": bars[exit_idx]["date"],
            "entry": entry,
            "exit": exit_price,
            "return_pct": ret,
            "held_bars": exit_idx - entry_idx,
            "reason": reason,
            "bench_pct": None,
            "excess_pct": None,
        }
        if benchmark:
            bench_exit = benchmark.get(bars[exit_idx]["date"])
            if bench_entry and bench_exit:
                bench_ret = (bench_exit - bench_entry) / bench_entry * 100.0
                trade["bench_pct"] = bench_ret
                trade["excess_pct"] = ret - bench_ret
        trades.append(trade)
        i = exit_idx + 1

    return trades


def summarize(trades):
    if not trades:
        return {"n": 0, "win_rate": 0.0, "ev": 0.0, "median": 0.0,
                "stdev": 0.0, "total": 0.0, "max_dd": 0.0,
                "stops": 0, "targets": 0, "timeouts": 0, "avg_hold": 0.0}

    rets = [t["return_pct"] for t in trades]
    wins = [r for r in rets if r > 0]

    equity = cumulative = peak = max_dd = 0.0
    for r in rets:
        cumulative += r
        peak = max(peak, cumulative)
        max_dd = min(max_dd, cumulative - peak)
        equity = cumulative

    out = {
        "n": len(trades),
        "win_rate": len(wins) / len(trades) * 100.0,
        "ev": statistics.fmean(rets),
        "median": statistics.median(rets),
        "stdev": statistics.stdev(rets) if len(rets) > 1 else 0.0,
        "total": equity,
        "max_dd": max_dd,
        "stops": sum(1 for t in trades if t["reason"] == "stop"),
        "targets": sum(1 for t in trades if t["reason"] == "target"),
        "timeouts": sum(1 for t in trades if t["reason"] == "timeout"),
        "avg_hold": statistics.fmean([t["held_bars"] for t in trades]),
        "excess_n": 0, "excess_ev": None, "excess_stdev": 0.0,
        "excess_win_rate": None, "excess_total": None,
    }

    # Excess over the benchmark, where available. This is the headline number:
    # raw returns measured over a rising market credit beta as edge.
    exc = [t["excess_pct"] for t in trades if t.get("excess_pct") is not None]
    if exc:
        out["excess_n"] = len(exc)
        out["excess_ev"] = statistics.fmean(exc)
        out["excess_stdev"] = statistics.stdev(exc) if len(exc) > 1 else 0.0
        out["excess_win_rate"] = sum(1 for e in exc if e > 0) / len(exc) * 100.0
        out["excess_total"] = sum(exc)
    return out


def significance(stats, prefix=""):
    """
    Is the mean distinguishable from zero? Returns a t-statistic and the
    trade count needed to resolve an edge of the observed size.

    Pass prefix="excess_" to test excess returns instead of raw. A
    good-looking EV over 20 trades is noise, and the harness should say so.
    """
    n = stats["excess_n"] if prefix else stats["n"]
    sd = stats[prefix + "stdev"]
    ev = stats[prefix + "ev"]
    if not n or n < 2 or not sd or ev is None:
        return None, None
    t_stat = ev / (sd / math.sqrt(n))
    needed = math.ceil((1.96 * sd / ev) ** 2) if ev != 0 else None
    return t_stat, needed


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def print_report(label, stats, trades):
    print(f"\n=== {label} ===")
    if stats["n"] == 0:
        print("  No trades generated. Loosen the dip threshold or add more data.")
        return

    print(f"  Trades          : {stats['n']}")
    print(f"  Win rate        : {stats['win_rate']:.1f}%")
    print(f"  EV / trade      : {stats['ev']:+.3f}%")
    print(f"  Median trade    : {stats['median']:+.3f}%")
    print(f"  Std dev         : {stats['stdev']:.2f}%")
    print(f"  Sum of returns  : {stats['total']:+.1f}%")
    print(f"  Max drawdown    : {stats['max_dd']:.1f}%")
    print(f"  Avg hold        : {stats['avg_hold']:.1f} bars")
    print(f"  Exits           : {stats['targets']} target / "
          f"{stats['stops']} stop / {stats['timeouts']} timeout")

    if stats["excess_ev"] is None:
        print("  ! No benchmark loaded - these are RAW returns. Over a rising")
        print("    market they credit beta as edge. Supply --benchmark.")
    else:
        print(f"  --- vs benchmark ({stats['excess_n']} trades matched) ---")
        print(f"  Excess / trade  : {stats['excess_ev']:+.3f} pp   <-- headline")
        print(f"  Excess win rate : {stats['excess_win_rate']:.1f}%")
        print(f"  Sum of excess   : {stats['excess_total']:+.1f} pp")

    # Significance is reported on excess when a benchmark exists, raw otherwise.
    prefix = "excess_" if stats["excess_ev"] is not None else ""
    t_stat, needed = significance(stats, prefix)
    if t_stat is None:
        return
    basis = "excess" if prefix else "raw"
    verdict = "SIGNIFICANT" if abs(t_stat) >= 1.96 else "NOT significant"
    print(f"  t-statistic     : {t_stat:+.2f} ({basis})  ->  {verdict} at 95%")
    if abs(t_stat) < 1.96 and needed:
        have = stats["excess_n"] if prefix else stats["n"]
        print(f"  Trades needed   : ~{needed} to resolve an edge this size "
              f"(have {have})")


def run_sweep(data, args, benchmark=None):
    """
    Grid over TP/SL inside PLAN.md's locked ranges (+5-8%, -7 to -10%).

    The point is to test empirically what was argued analytically: that the
    TP/SL ratio does not create edge, and that slippage does all the damage.
    """
    print("\n=== TP/SL sweep (locked ranges) ===")
    print(f"  slippage={args.slippage}%  dip<={args.dip}%  "
          f"max_hold={args.max_hold}  trend_filter={args.trend_filter}\n")
    basis = "excess" if benchmark else "RAW"
    print(f"  EV column basis: {basis}")
    print(f"  {'TP':>5} {'SL':>5} | {'trades':>7} {'win%':>7} "
          f"{'EV/trade':>10} {'total':>9} {'t':>7}")
    print("  " + "-" * 56)

    rows = []
    for tp in (5.0, 6.0, 7.0, 8.0):
        for sl in (7.0, 8.0, 9.0, 10.0):
            trades = []
            for bars in data.values():
                trades += simulate(bars, tp, sl, args.max_hold, args.slippage,
                                   args.dip, args.trend_filter,
                                   benchmark=benchmark, stop_mode=args.stop_mode,
                                   stop_floor_pct=args.stop_floor,
                                   regime_gate=args.regime_gate)
            stats = summarize(trades)
            prefix = "excess_" if stats["excess_ev"] is not None else ""
            t_stat, _ = significance(stats, prefix)
            rows.append((tp, sl, stats, t_stat))
            t_txt = f"{t_stat:+.2f}" if t_stat is not None else "  n/a"
            ev = stats["excess_ev"] if stats["excess_ev"] is not None else stats["ev"]
            tot = stats["excess_total"] if stats["excess_total"] is not None else stats["total"]
            print(f"  {tp:>4.0f}% {sl:>4.0f}% | {stats['n']:>7} "
                  f"{stats['win_rate']:>6.1f}% {ev:>+9.3f}% "
                  f"{tot:>+8.1f}% {t_txt:>7}")

    def _ev(s):
        return s["excess_ev"] if s["excess_ev"] is not None else s["ev"]
    best = max((r for r in rows if r[2]["n"] > 0), key=lambda r: _ev(r[2]), default=None)
    if best:
        tp, sl, stats, t_stat = best
        print(f"\n  Best EV: TP +{tp:.0f}% / SL -{sl:.0f}% at {_ev(stats):+.3f}/trade")
        if t_stat is None or abs(t_stat) < 1.96:
            print("  ...but it is NOT statistically significant. Treat this as noise,")
            print("  not a parameter recommendation. Picking the best cell of a grid")
            print("  on an insignificant sample is exactly how backtests get overfit.")


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def synthetic_random_walk(n_bars, seed, daily_vol=0.02, drift=0.0):
    """Driftless geometric random walk with plausible intrabar range."""
    rng = random.Random(seed)
    price = 100.0
    bars = []
    for i in range(n_bars):
        open_p = price
        shock = rng.gauss(drift, daily_vol)
        close_p = max(0.01, open_p * (1 + shock))
        wick = abs(rng.gauss(0, daily_vol / 2))
        high_p = max(open_p, close_p) * (1 + wick)
        low_p = min(open_p, close_p) * (1 - wick)
        bars.append({"date": f"D{i:05d}", "open": open_p, "high": high_p,
                     "low": low_p, "close": close_p})
        price = close_p
    return bars


def self_test():
    """
    Validates the harness against known answers.

    Three properties must hold on driftless random-walk data:

      1. With zero slippage, no TP/SL configuration produces meaningful edge.
      2. Observed win rate matches the analytical P(hit +tp before -sl),
         which is sl/(tp+sl) for a driftless walk. This is the strongest
         correctness check available - it pins the exit logic to a closed
         form.
      3. EV falls monotonically as slippage rises, and ONLY because of
         slippage. This is the claim AGENT_PROMPT.md rests on.

    Test data uses 3% daily vol and a -4% entry trigger. The defaults
    (2% vol, -6% trigger) make entries a 3-sigma event, which yielded 18
    trades - far too few to detect bias. Sample size is the whole point of
    this harness; the self-test has to respect that too.
    """
    print("Self-test: driftless random walk (3% daily vol, -4% entry trigger).")
    print("Expect EV ~0% and win rate ~ sl/(tp+sl) for every configuration.\n")

    data = {f"SYN{i}": synthetic_random_walk(2000, seed=i, daily_vol=0.03)
            for i in range(40)}
    test_dip = -4.0
    failures = []

    print(f"  {'TP':>5} {'SL':>5} | {'trades':>7} {'win%':>7} {'predicted':>10} "
          f"{'EV/trade':>10}")
    print("  " + "-" * 56)
    for tp, sl in [(6.0, 8.0), (8.0, 7.0), (8.0, 10.0), (5.0, 10.0)]:
        trades = []
        for bars in data.values():
            trades += simulate(bars, tp, sl, DEFAULT_MAX_HOLD, 0.0, test_dip)
        stats = summarize(trades)
        predicted = sl / (tp + sl) * 100.0
        print(f"  {tp:>4.0f}% {sl:>4.0f}% | {stats['n']:>7} "
              f"{stats['win_rate']:>6.1f}% {predicted:>9.1f}% "
              f"{stats['ev']:>+9.3f}%")

        if stats["n"] < 500:
            failures.append(f"TP{tp}/SL{sl}: only {stats['n']} trades - too few to test")
        # Timeouts legitimately pull observed win rate off the closed form,
        # so allow a wide band; a broken exit path misses by far more.
        if abs(stats["win_rate"] - predicted) > 8.0:
            failures.append(
                f"TP{tp}/SL{sl}: win rate {stats['win_rate']:.1f}% vs "
                f"predicted {predicted:.1f}% - exit logic suspect")
        if abs(stats["ev"]) > 0.5:
            failures.append(
                f"TP{tp}/SL{sl}: EV {stats['ev']:+.3f}% on driftless data - "
                f"harness is biased")

    print("\n  Slippage check (TP +6% / SL -8%):")
    prev = None
    for slip in (0.0, 1.5, 3.0):
        trades = []
        for bars in data.values():
            trades += simulate(bars, 6.0, 8.0, DEFAULT_MAX_HOLD, slip, test_dip)
        stats = summarize(trades)
        print(f"    slippage {slip:>4.1f}%  ->  EV {stats['ev']:>+7.3f}%/trade")
        if prev is not None and stats["ev"] >= prev:
            failures.append(f"EV did not fall as slippage rose to {slip}%")
        prev = stats["ev"]

    print()
    if failures:
        print("SELF-TEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("SELF-TEST PASSED.")
    print("  Win rates match the closed form, no TP/SL config manufactured edge")
    print("  on driftless data, and EV fell monotonically with slippage -")
    print("  confirming that friction, not the profit/loss ratio, drives")
    print("  expectancy. Any edge found on REAL data is therefore attributable")
    print("  to the data, not to the choice of exit levels.")
    return 0


# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Backtest the dip-buy loop against historical bars.")
    parser.add_argument("--data", help="Directory of <SYMBOL>.json bar files, or one file")
    parser.add_argument("--tp", type=float, default=DEFAULT_TP, help="Take-profit %%")
    parser.add_argument("--sl", type=float, default=DEFAULT_SL, help="Stop-loss trigger %%")
    parser.add_argument("--max-hold", type=int, default=DEFAULT_MAX_HOLD, help="Max hold in bars")
    parser.add_argument("--slippage", type=float, default=DEFAULT_SLIPPAGE,
                        help="Extra %% lost past the stop trigger on market exits")
    parser.add_argument("--dip", type=float, default=DEFAULT_DIP,
                        help="Entry trigger: single-bar %% change at or below this")
    parser.add_argument("--trend-filter", action="store_true",
                        help="Only enter when price is above its 200-day EMA")
    parser.add_argument("--sweep", action="store_true", help="Grid over the locked TP/SL ranges")
    parser.add_argument("--benchmark", default="SPY",
                        help="Benchmark symbol for excess returns (default SPY). "
                             "Must be present in --data. Use '' to disable.")
    parser.add_argument("--stop-mode", choices=("absolute", "relative", "floored"),
                        default="absolute",
                        help="absolute (live default) | relative (widens with a "
                             "falling market, unbounded) | floored (relative, capped)")
    parser.add_argument("--stop-floor", type=float, default=15.0,
                        help="Widest stop under --stop-mode floored (default 15%%)")
    parser.add_argument("--regime-gate", action="store_true",
                        help="No entries when the benchmark is below its 200-day EMA")
    parser.add_argument("--compare-stops", action="store_true",
                        help="Run all three stop modes side by side")
    parser.add_argument("--self-test", action="store_true", help="Validate the harness itself")
    args = parser.parse_args()

    if args.self_test:
        return self_test()
    if not args.data:
        parser.error("--data is required (or use --self-test)")

    data = load_data(args.data)
    if not data:
        sys.exit("No usable symbol data loaded.")

    benchmark = None
    if args.benchmark:
        bench_sym = args.benchmark.upper()
        bench_bars = data.pop(bench_sym, None)
        if bench_bars:
            benchmark = {b["date"]: b["close"] for b in bench_bars}
            print(f"Benchmark: {bench_sym} ({len(benchmark)} bars) - "
                  f"reporting EXCESS returns")
        else:
            print(f"! Benchmark {bench_sym} not found in --data. Returns will be "
                  f"RAW, which over a rising market credits beta as edge.",
                  file=sys.stderr)
    if not data:
        sys.exit("No symbols left after removing the benchmark.")
    if args.regime_gate and not benchmark:
        sys.exit("--regime-gate requires a benchmark series.")

    total_bars = sum(len(b) for b in data.values())
    print(f"Loaded {len(data)} symbols, {total_bars} bars: {', '.join(sorted(data))}")

    if args.sweep:
        run_sweep(data, args, benchmark)
        return 0

    def run(stop_mode, trend, regime):
        trades = []
        for bars in data.values():
            trades += simulate(bars, args.tp, args.sl, args.max_hold,
                               args.slippage, args.dip, trend,
                               benchmark=benchmark, stop_mode=stop_mode,
                               stop_floor_pct=args.stop_floor, regime_gate=regime)
        return trades

    base = (f"TP +{args.tp:.0f}% / SL -{args.sl:.0f}% / hold {args.max_hold} / "
            f"slip {args.slippage}%")

    if args.compare_stops:
        # The live rule is "absolute". The other two are the market-relative
        # proposal; compare EV *and* worst drawdown before trusting either.
        for mode in ("absolute", "relative", "floored"):
            suffix = f" (floor -{args.stop_floor:.0f}%)" if mode == "floored" else ""
            print_report(f"{base} / stop={mode}{suffix}",
                         summarize(run(mode, args.trend_filter, args.regime_gate)), None)
        print("\n  Compare max drawdown, not just EV: a relative stop concentrates")
        print("  losses into correlated market-wide events across all positions.")
        return 0

    label = base + f" / stop={args.stop_mode}"
    if args.trend_filter:
        label += " / trend filter"
    if args.regime_gate:
        label += " / regime gate"
    print_report(label, summarize(run(args.stop_mode, args.trend_filter,
                                      args.regime_gate)), None)

    # Both live gates are restrictive, so always show what they cost/save.
    if not args.trend_filter:
        print_report(label + " + 200-EMA trend filter",
                     summarize(run(args.stop_mode, True, args.regime_gate)), None)
    if benchmark and not args.regime_gate:
        print_report(label + " + market-regime gate",
                     summarize(run(args.stop_mode, args.trend_filter, True)), None)

    return 0


if __name__ == "__main__":
    sys.exit(main())
