#!/usr/bin/env python3
"""
Cross-sectional panel study: does ANY feature predict forward returns?

This answers the question that comes before backtest.py. The harness replays
one specific set of rules; this screens candidate signals across the whole
cross-section - including the stocks that did NOT dip, which the live loop
never looks at and therefore has no control group for.

Method, and why each part is there:

  1. PANEL. For every (symbol, day t) compute features knowable at the close
     of t, paired with forward returns entered at the OPEN of t+1. Anything
     using data past t is look-ahead and silently invents edge.

  2. EXCESS RETURNS. Every forward return is measured against the benchmark
     over the identical window. Raw returns over a rising market credit beta
     as though it were signal - the same mistake that let the live loop's
     6.7pp shortfall read as a mild -2.4%.

  3. DECILE SORT. Each day, rank the cross-section by the feature and bucket
     into deciles. Average each decile's forward excess return across days.
     Look for a MONOTONIC gradient. A single strong bucket is noise; a real
     signal gradates. Monotonicity is reported as the Spearman correlation
     between decile rank and mean return.

  4. DAILY SPREAD T-TEST. This is the part that matters most. 500 stocks x
     500 days is NOT 250,000 independent observations - every stock shares
     the market factor, so t-stats computed on stock-days are inflated by
     roughly an order of magnitude. Instead, collapse each day to ONE number
     (top decile minus bottom decile) and t-test that daily time series.
     N = number of days. This is the Fama-MacBeth structure and it
     self-corrects for cross-sectional correlation.

  5. REGIME SPLIT + FRICTION. Report the spread separately for days when the
     benchmark is above vs below its 200-day EMA, and subtract a round-trip
     cost. Most apparent edges die at one or the other.

Multiple testing is the standing danger: test enough features and some will
look significant on pure noise. Every report therefore prints the number of
features tested and a Bonferroni-adjusted threshold alongside the raw one.
Treat |t| > 3 as the working bar, not 2.

Usage:
    python3 panel_study.py --self-test
    python3 panel_study.py --data data/
    python3 panel_study.py --data data/ --horizon 5 --deciles 10
    python3 panel_study.py --data data/ --feature ret_21d --verbose

Data format is identical to backtest.py - raw get_equity_historicals
envelopes, benchmark (SPY) included in the same directory.

No third-party dependencies.
"""

import argparse
import math
import statistics
import sys

from backtest import load_data, ema, EMA_PERIOD

DEFAULT_HORIZON = 5
DEFAULT_DECILES = 10
DEFAULT_FRICTION = 1.5
MIN_CROSS_SECTION = 10   # need enough names on a day to form meaningful buckets


# --------------------------------------------------------------------------
# Feature construction
# --------------------------------------------------------------------------

def rsi(closes, period=2):
    """Wilder RSI aligned to closes; None until enough history."""
    out = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period
    for i in range(period, len(closes)):
        if i > period:
            avg_g = (avg_g * (period - 1) + gains[i - 1]) / period
            avg_l = (avg_l * (period - 1) + losses[i - 1]) / period
        out[i] = 100.0 if avg_l == 0 else 100.0 - 100.0 / (1 + avg_g / avg_l)
    return out


def build_features(bars):
    """
    Per-bar feature dict. Every value uses ONLY bars[:i+1] - never i+1 or
    later. Returns a list aligned to `bars`, with None where history is short.
    """
    closes = [b["close"] for b in bars]
    volumes = [b.get("volume") or 0.0 for b in bars]
    n = len(bars)
    ema200 = ema(closes, EMA_PERIOD)
    rsi2 = rsi(closes, 2)
    out = [None] * n

    for i in range(n):
        if i < 1:
            continue
        f = {}
        f["ret_1d"] = (closes[i] / closes[i - 1] - 1) * 100.0
        for lag, name in ((5, "ret_5d"), (21, "ret_21d")):
            f[name] = ((closes[i] / closes[i - lag] - 1) * 100.0) if i >= lag else None
        # 12-month momentum skipping the most recent month, per the standard
        # construction - the recent month is short-term reversal, not momentum.
        f["mom_12_1"] = (((closes[i - 21] / closes[i - 252] - 1) * 100.0)
                         if i >= 252 else None)
        window = closes[max(0, i - 251):i + 1]
        high52 = max(window)
        f["pct_from_52w_high"] = (closes[i] / high52 - 1) * 100.0 if high52 else None
        f["above_200ema"] = ((closes[i] / ema200[i] - 1) * 100.0
                             if ema200[i] else None)
        if i >= 21:
            rets = [(closes[j] / closes[j - 1] - 1) for j in range(i - 20, i + 1)]
            f["vol_21d"] = statistics.stdev(rets) * 100.0 if len(rets) > 1 else None
        else:
            f["vol_21d"] = None
        if i >= 21:
            avg_v = statistics.fmean(volumes[i - 20:i + 1])
            f["rel_volume"] = (volumes[i] / avg_v) if avg_v else None
        else:
            f["rel_volume"] = None
        f["rsi_2"] = rsi2[i]
        out[i] = f
    return out


FEATURES = ["ret_1d", "ret_5d", "ret_21d", "mom_12_1", "pct_from_52w_high",
            "above_200ema", "vol_21d", "rel_volume", "rsi_2"]


def build_panel(data, benchmark, horizon):
    """
    Assemble {date: [observation, ...]}.

    Forward return is measured OPEN(t+1) -> OPEN(t+1+horizon), which is what
    a loop scanning at the close of t and buying next session can actually
    capture. Excess subtracts the benchmark over that identical window.
    """
    panel = {}
    for symbol, bars in data.items():
        feats = build_features(bars)
        n = len(bars)
        for i in range(n):
            entry_idx, exit_idx = i + 1, i + 1 + horizon
            if exit_idx >= n or feats[i] is None:
                continue
            entry = bars[entry_idx]["open"]
            exit_price = bars[exit_idx]["open"]
            if not entry or not exit_price:
                continue
            fwd = (exit_price / entry - 1) * 100.0

            excess = None
            if benchmark:
                b0 = benchmark.get(bars[entry_idx]["date"])
                b1 = benchmark.get(bars[exit_idx]["date"])
                if b0 and b1:
                    excess = fwd - (b1 / b0 - 1) * 100.0

            panel.setdefault(bars[i]["date"], []).append({
                "symbol": symbol,
                "features": feats[i],
                "fwd": fwd,
                "excess": excess if excess is not None else fwd,
                "has_excess": excess is not None,
            })
    return panel


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------

def spearman(xs, ys):
    """Rank correlation. Used to score decile monotonicity."""
    if len(xs) < 3:
        return None
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, idx in enumerate(order):
            r[idx] = float(pos)
        return r
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.fmean(rx), statistics.fmean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def t_test(values):
    """One-sample t against zero. Returns (mean, t, n)."""
    n = len(values)
    if n < 2:
        return (statistics.fmean(values) if values else 0.0), None, n
    mean = statistics.fmean(values)
    sd = statistics.stdev(values)
    if sd == 0:
        return mean, None, n
    return mean, mean / (sd / math.sqrt(n)), n


def analyze_feature(panel, feature, n_deciles, use_excess=True):
    """
    Decile-sort by `feature` within each day, then build the daily
    top-minus-bottom spread series.

    Returning the spread as a per-day series (not pooled stock-days) is the
    entire point - it is what keeps the t-statistic honest under the heavy
    cross-sectional correlation of equity returns.
    """
    key = "excess" if use_excess else "fwd"
    bucket_returns = [[] for _ in range(n_deciles)]
    spread_series = []          # one number per day
    spread_dates = []

    for date in sorted(panel):
        obs = [o for o in panel[date] if o["features"].get(feature) is not None]
        if len(obs) < max(MIN_CROSS_SECTION, n_deciles):
            continue
        obs.sort(key=lambda o: o["features"][feature])
        size = len(obs) / n_deciles
        day_means = []
        for d in range(n_deciles):
            lo, hi = int(round(d * size)), int(round((d + 1) * size))
            chunk = obs[lo:hi]
            if not chunk:
                day_means.append(None)
                continue
            m = statistics.fmean([o[key] for o in chunk])
            bucket_returns[d].append(m)
            day_means.append(m)
        if day_means[0] is not None and day_means[-1] is not None:
            spread_series.append(day_means[-1] - day_means[0])
            spread_dates.append(date)

    decile_means = [statistics.fmean(b) if b else None for b in bucket_returns]
    mean_spread, t_stat, n_days = t_test(spread_series)

    valid = [(i, m) for i, m in enumerate(decile_means) if m is not None]
    mono = spearman([i for i, _ in valid], [m for _, m in valid]) if len(valid) >= 3 else None

    return {
        "feature": feature,
        "decile_means": decile_means,
        "spread_series": spread_series,
        "spread_dates": spread_dates,
        "mean_spread": mean_spread,
        "t_stat": t_stat,
        "n_days": n_days,
        "monotonicity": mono,
    }


def regime_split(result, panel, benchmark_trend):
    """Mean spread on days the benchmark is above vs below its 200-day EMA."""
    if not benchmark_trend:
        return None, None
    up = [s for s, d in zip(result["spread_series"], result["spread_dates"])
          if benchmark_trend.get(d) is True]
    down = [s for s, d in zip(result["spread_series"], result["spread_dates"])
            if benchmark_trend.get(d) is False]
    return (t_test(up) if up else None), (t_test(down) if down else None)


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def print_feature(result, friction, trend_map=None, panel=None, verbose=False):
    f = result["feature"]
    t = result["t_stat"]
    print(f"\n--- {f} ---")
    if t is None:
        print("  insufficient data")
        return

    if verbose:
        print("  decile means (low -> high feature value):")
        cells = ["  n/a" if m is None else f"{m:+5.2f}" for m in result["decile_means"]]
        print("    " + " ".join(cells))

    mono = result["monotonicity"]
    mono_txt = f"{mono:+.2f}" if mono is not None else " n/a"
    print(f"  monotonicity (rank corr) : {mono_txt}"
          f"{'   <- gradates cleanly' if mono is not None and abs(mono) > 0.7 else ''}")
    print(f"  mean daily spread        : {result['mean_spread']:+.4f} pp "
          f"(top decile - bottom)")
    print(f"  t-statistic              : {t:+.2f}  over {result['n_days']} days")

    net = abs(result["mean_spread"]) - friction
    print(f"  after {friction:.1f}pp friction    : "
          f"{net:+.4f} pp {'SURVIVES' if net > 0 else 'DIES'}")

    if trend_map and panel:
        up, down = regime_split(result, panel, trend_map)
        if up:
            print(f"  benchmark uptrend        : {up[0]:+.4f} pp "
                  f"(t={up[1]:+.2f} n={up[2]})" if up[1] is not None
                  else f"  benchmark uptrend        : {up[0]:+.4f} pp (n={up[2]})")
        if down:
            print(f"  benchmark downtrend      : {down[0]:+.4f} pp "
                  f"(t={down[1]:+.2f} n={down[2]})" if down[1] is not None
                  else f"  benchmark downtrend      : {down[0]:+.4f} pp (n={down[2]})")


def print_verdict(results, n_tested):
    """
    Rank features and apply a multiple-testing correction.

    Without this the report is a machine for manufacturing false discoveries:
    test nine features at p<0.05 and you expect roughly one 'hit' from noise
    alone.
    """
    bonferroni = 1.96 + (math.log(max(n_tested, 1)) ** 0.5) if n_tested > 1 else 1.96
    # Exact two-sided Bonferroni z for alpha=0.05/n via a normal approximation.
    alpha = 0.05 / max(n_tested, 1)
    z = 0.0
    lo, hi = 0.0, 10.0
    for _ in range(200):                     # bisect the normal tail
        z = (lo + hi) / 2
        tail = 0.5 * math.erfc(z / math.sqrt(2)) * 2
        if tail > alpha:
            lo = z
        else:
            hi = z
    bonferroni = z

    print("\n" + "=" * 62)
    print(f"VERDICT  ({n_tested} features tested)")
    print("=" * 62)
    print(f"  Raw 95% threshold        : |t| > 1.96")
    print(f"  Bonferroni-corrected     : |t| > {bonferroni:.2f}   <- use this one")
    print(f"  Working bar in practice  : |t| > 3.00")

    ranked = sorted((r for r in results if r["t_stat"] is not None),
                    key=lambda r: -abs(r["t_stat"]))
    print(f"\n  {'feature':<20} {'t':>7} {'spread pp':>11} {'mono':>7}  verdict")
    print("  " + "-" * 58)
    for r in ranked:
        t = r["t_stat"]
        mono = r["monotonicity"]
        if abs(t) > max(bonferroni, 3.0) and mono is not None and abs(mono) > 0.7:
            verdict = "CANDIDATE"
        elif abs(t) > bonferroni:
            verdict = "survives correction"
        elif abs(t) > 1.96:
            verdict = "raw only - likely noise"
        else:
            verdict = "-"
        mono_txt = f"{mono:+.2f}" if mono is not None else "  n/a"
        print(f"  {r['feature']:<20} {t:>+7.2f} {r['mean_spread']:>+11.4f} "
              f"{mono_txt:>7}  {verdict}")

    strong = [r for r in ranked if abs(r["t_stat"]) > max(bonferroni, 3.0)
              and r["monotonicity"] is not None and abs(r["monotonicity"]) > 0.7]
    print()
    if strong:
        print(f"  {len(strong)} feature(s) cleared both the corrected t-threshold and the")
        print("  monotonicity check. That is a reason to investigate further in")
        print("  backtest.py - NOT a reason to trade. Confirm out-of-sample on a")
        print("  time period this run never touched before committing capital.")
    else:
        print("  Nothing cleared the bar. That is the expected outcome most of the")
        print("  time and it is a useful result, not a failed run - it means the")
        print("  data does not support trading any of these signals.")


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def _synth_panel(n_days, n_stocks, signal_strength, seed):
    """
    Build a panel directly, with a KNOWN planted effect.

    ret_1d is constructed so that low values predict HIGH forward excess
    returns when signal_strength > 0 (a reversal effect). Every other
    feature is pure noise. A correct implementation must find the planted
    one and reject the rest.

    Crucially each day also gets a large common shock, reproducing the
    cross-sectional correlation that makes naive stock-day t-tests lie.
    """
    rng = __import__("random").Random(seed)
    panel = {}
    for d in range(n_days):
        market = rng.gauss(0, 1.2)          # common factor, large
        obs = []
        for s in range(n_stocks):
            r1 = rng.gauss(0, 3.0)
            fwd = market + rng.gauss(0, 2.0) - signal_strength * r1
            obs.append({
                "symbol": f"S{s}",
                "features": {
                    "ret_1d": r1,
                    "ret_5d": rng.gauss(0, 3.0),
                    "noise_a": rng.gauss(0, 1.0),
                    "noise_b": rng.gauss(0, 1.0),
                },
                "fwd": fwd,
                "excess": fwd - market,     # excess strips the common factor
                "has_excess": True,
            })
        panel[f"D{d:05d}"] = obs
    return panel


def self_test():
    """
    Validate against known answers:
      1. A planted reversal signal must be detected, with the right sign and
         clean monotonicity.
      2. Pure-noise features must NOT be flagged.
      3. Removing the signal must make the planted feature go quiet.
      4. Pooling stock-days must visibly inflate the t-stat versus the daily
         spread method - the bug this design exists to avoid.
    """
    print("Self-test: synthetic panel with a KNOWN planted reversal signal.\n")
    failures = []
    feats = ["ret_1d", "ret_5d", "noise_a", "noise_b"]

    print("  [1] signal present (strength 0.25)")
    panel = _synth_panel(400, 60, 0.25, seed=11)
    results = {f: analyze_feature(panel, f, 10) for f in feats}
    for f in feats:
        r = results[f]
        print(f"      {f:<9} t={r['t_stat']:+7.2f}  spread={r['mean_spread']:+7.4f}  "
              f"mono={r['monotonicity']:+.2f}")
    planted = results["ret_1d"]
    if planted["t_stat"] is None or abs(planted["t_stat"]) < 5:
        failures.append(f"planted signal not detected (t={planted['t_stat']})")
    if planted["mean_spread"] >= 0:
        failures.append("planted reversal has wrong sign (low ret_1d should "
                        "predict HIGH forward return -> negative spread)")
    if planted["monotonicity"] is None or abs(planted["monotonicity"]) < 0.9:
        failures.append(f"planted signal not monotonic ({planted['monotonicity']})")
    for f in ("noise_a", "noise_b", "ret_5d"):
        if results[f]["t_stat"] is not None and abs(results[f]["t_stat"]) > 3.0:
            failures.append(f"noise feature {f} flagged (t={results[f]['t_stat']:+.2f})")

    print("\n  [2] signal absent (strength 0.0) - nothing should fire")
    panel0 = _synth_panel(400, 60, 0.0, seed=12)
    for f in feats:
        r = analyze_feature(panel0, f, 10)
        print(f"      {f:<9} t={r['t_stat']:+7.2f}")
        if r["t_stat"] is not None and abs(r["t_stat"]) > 3.0:
            failures.append(f"{f} fired on data with no signal (t={r['t_stat']:+.2f})")

    print("\n  [3] pooled stock-days vs daily spread (the correlation trap)")
    pooled = []
    for date, obs in panel0.items():
        pooled += [o["fwd"] for o in obs]     # raw, common factor NOT removed
    _, t_pooled, n_pooled = t_test(pooled)
    daily = [statistics.fmean([o["fwd"] for o in obs]) for obs in panel0.values()]
    _, t_daily, n_daily = t_test(daily)
    print(f"      pooled stock-days : n={n_pooled:<6} t={t_pooled:+.2f}")
    print(f"      daily means       : n={n_daily:<6} t={t_daily:+.2f}")
    ratio = abs(t_pooled) / abs(t_daily) if t_daily else float("inf")
    print(f"      inflation factor  : {ratio:.1f}x")
    if ratio < 2.0:
        failures.append(f"pooling did not inflate t as expected ({ratio:.1f}x) - "
                        "the synthetic common factor may be too weak to test this")

    print()
    if failures:
        print("SELF-TEST FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("SELF-TEST PASSED.")
    print("  Planted signal found with correct sign and monotonicity, noise")
    print("  features stayed quiet, nothing fired on signal-free data, and")
    print(f"  naive stock-day pooling inflated the t-statistic {ratio:.1f}x -")
    print("  confirming why the daily-spread design is the one used here.")
    return 0


# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(description="Cross-sectional panel study.")
    p.add_argument("--data", help="Directory of get_equity_historicals JSON")
    p.add_argument("--benchmark", default="SPY", help="Benchmark symbol (default SPY)")
    p.add_argument("--horizon", type=int, default=DEFAULT_HORIZON,
                   help="Forward return horizon in bars (default 5)")
    p.add_argument("--deciles", type=int, default=DEFAULT_DECILES)
    p.add_argument("--friction", type=float, default=DEFAULT_FRICTION,
                   help="Round-trip cost in pp subtracted from the spread")
    p.add_argument("--feature", help="Analyze only this feature")
    p.add_argument("--verbose", action="store_true", help="Print decile means")
    p.add_argument("--self-test", action="store_true")
    args = p.parse_args()

    if args.self_test:
        return self_test()
    if not args.data:
        p.error("--data is required (or use --self-test)")

    data = load_data(args.data)
    if not data:
        sys.exit("No usable symbol data loaded.")

    benchmark = trend_map = None
    bench_sym = args.benchmark.upper() if args.benchmark else None
    if bench_sym and bench_sym in data:
        bars = data.pop(bench_sym)
        benchmark = {b["date"]: b["close"] for b in bars}
        closes = [b["close"] for b in bars]
        e = ema(closes, EMA_PERIOD)
        trend_map = {b["date"]: (closes[i] > e[i]) if e[i] else None
                     for i, b in enumerate(bars)}
        print(f"Benchmark: {bench_sym} - forward returns are EXCESS of it")
    else:
        print(f"! No benchmark ({bench_sym}) in --data. Returns are RAW; over a "
              f"rising market this credits beta as signal.", file=sys.stderr)

    if len(data) < MIN_CROSS_SECTION:
        print(f"! Only {len(data)} symbols. Cross-sectional deciles need at least "
              f"{MIN_CROSS_SECTION} names per day to mean anything.", file=sys.stderr)

    panel = build_panel(data, benchmark, args.horizon)
    obs = sum(len(v) for v in panel.values())
    print(f"Panel: {len(data)} symbols, {len(panel)} days, {obs} observations, "
          f"horizon {args.horizon} bars")
    print(f"Effective sample for significance is the {len(panel)} DAYS, "
          f"not the {obs} stock-days.")

    features = [args.feature] if args.feature else FEATURES
    results = []
    for f in features:
        r = analyze_feature(panel, f, args.deciles)
        results.append(r)
        print_feature(r, args.friction, trend_map, panel, args.verbose)

    print_verdict(results, len(features))
    return 0


if __name__ == "__main__":
    sys.exit(main())
