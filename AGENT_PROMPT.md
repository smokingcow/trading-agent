# Dip-Buy Loop — Runtime Instructions

**This file is read and executed by the scheduled cloud routine itself.** Each run is a fresh, isolated session with zero memory of prior runs — this file plus the repo's other files (`PLAN.md`, `ledger.md`, `run-log.md`) are the entire context. If you are the agent executing a scheduled run: follow the numbered steps below in order, exactly. If you are a human reviewing this before it goes live: read the callout box first.

---

## ⚠️ Judgment calls — reviewed and confirmed 2026-07-31, revised 2026-08-08

`PLAN.md`'s "Locked decisions" give *ranges* (e.g. "+5-8% take-profit") or leave some mechanics unspecified. An autonomous agent needs exact numbers, not ranges.

| # | Item | Default chosen | Why this one | Locked range/constraint |
|---|---|---|---|---|
| 1 | Position size | **20%** of current total capital | Lower bound → more diversification headroom | Locked: 20-25% |
| 2 | Take-profit | **+6%** | See "Why TP/SL were left alone" below | Locked: +5-8% |
| 3 | Stop-loss | **-8%** trigger (≈ **-9.5%** realized after slippage) | Unchanged — see below | Locked: -7% to -10% |
| 4 | Daily circuit breaker | **6%** of total capital | Middle of range | Locked: 5-8% |
| 5 | Max hold period | **12** trading days | Middle of range | Locked: 10-15 days |
| 6 | New positions per run | **At most 1** | Simpler, more auditable | Not specified in PLAN.md |
| 7 | Pause-flag mechanism | File named **`PAUSE`** in repo root | Simple, git-trackable | Not specified in PLAN.md |
| 8 | Starting capital (kill switch) | **$2,000** | Matches funded amount | Update if capital is added |
| 9 | Sector field source | Robinhood `sector` from `get_equity_fundamentals` | Only real option | Resolves PLAN.md open item |
| 10 | **Earnings exclusion (NEW 2026-08-08)** | Skip any candidate reporting within **14 calendar days** | See below — highest-value change in this revision | Narrows the universe; does not widen it |
| 11 | **Wash-sale guard (NEW 2026-08-08)** | Skip any symbol sold at a loss in the last **30 calendar days** | Protects realized losses from disallowance | New |
| 12 | **Max bid-ask spread (NEW 2026-08-08)** | Skip if spread > **1.0%** of mid | Reduces entry friction | New |
| 13 | **Trend filter (NEW 2026-08-08)** | Require price **above the 200-day EMA** | Buy dips *in uptrends*, not falling knives | New |
| 14 | **Benchmark (NEW 2026-08-09)** | **SPY**, recorded every run and per trade | Measurement only — separates skill from beta | New |
| 15 | **Market-regime gate (NEW 2026-08-09)** | No new buys when **SPY is below its 200-day EMA** | Prevents dip-buying into a downtrend | New; restrictive only |
| 16 | **Underperformance tripwire (NEW 2026-08-09)** | Flag for review if trailing-30-day return trails SPY by **>10pp** | Review flag, **not** an auto-pause | New; notification only |

### What was deliberately NOT changed: the market-relative stop-loss

A market-relative (beta-adjusted) stop was proposed — don't liquidate on a drop the whole market shared. The reasoning is sound and identifies a genuine inconsistency: entry logic is relative (buy macro dips, skip company-specific ones) while exit logic is absolute, so the loop can stop out of exactly the selloff it bet would revert.

**It is still not implemented, on purpose.** Three reasons:

1. **The portfolio math.** Five positions at 20% each don't fail independently — a market-wide drop breaches them together. A relative stop floored at -15% turns a single correlated event from **-9.5%** of the account into **-16.5%**, most of the way to the -20% kill switch in one week.
2. **Beta isn't 1.** These are small/mid caps. Assuming beta 1 under-protects exactly the names that move most, and correlations converge toward 1 in crashes — the estimate fails hardest when it matters.
3. **Two previous "obviously correct" changes to these levels were both wrong when measured** (see above). Changing the only hard capital control on the strength of an argument is precisely the pattern that keeps failing here.

The addressable root cause is handled at the **entry** instead, via judgment-call #15 — don't buy dips into a downtrend at all, rather than removing protection once already exposed. The relative stop is implemented in `backtest.py` as a testable variant (`--stop-mode relative|floored`) and should be evaluated against real bars covering a drawdown before it ever goes live.

### Why TP/SL were deliberately **not** changed on 2026-08-08

An earlier draft of this revision raised take-profit to +8% and tightened the stop to -7%, on the argument that a +6%/-8% payoff requires a >57% win rate to break even. **That argument is wrong and the change was reverted before going live.** The breakeven-win-rate framing treats win rate as independent of the TP/SL levels, but it isn't: a wider profit target relative to the stop is *harder to reach*, so raising TP mechanically lowers P(win) by roughly the same amount it raises the payoff.

Modelling it as a random walk (P(hit +a before −b) ≈ b/(a+b)):

| Config | P(win) | EV/trade @1.5% slippage | EV/trade @0 slippage |
|---|---|---|---|
| TP +6% / SL -8% (current) | 57.1% | -0.643% | 0.000% |
| TP +8% / SL -7% (proposed, rejected) | 46.7% | **-0.800%** | 0.000% |
| TP +8% / SL -10% | 55.6% | -0.667% | 0.000% |

**With zero slippage every configuration has EV exactly zero.** The TP/SL ratio does not create or destroy edge — it only trades win rate against win size. The entire negative expectancy comes from **slippage**, and the rejected config was the *worst* of the set precisely because a tighter stop pays that tax more often.

The conclusion that follows: **the lever is friction and gap risk, not the profit/loss ratio.** That is why this revision adds the earnings exclusion, spread cap, and trend filter, and leaves TP/SL alone. Tuning TP/SL is a legitimate question — but it should be settled by the backtest harness against real price paths, not by an argument from a formula that assumes away the dependency. Do not re-tune these numbers without backtest evidence.

A second revision proposed tightening the stop from -8% to -7% as "slippage compensation" — the reasoning being that since market exits fill 1.5-1.8% past the trigger (EIX filled -9.42% against a -8% trigger; PBF -9.61%), a -7% trigger would land the realized loss nearer the intended -8%. **That was the same error in smaller form, and it was also reverted.** Running it through `backtest.py` on synthetic data shows why:

| Stop (TP +6% fixed) | Trades | Stop-outs | EV/trade @1.5% slippage |
|---|---|---|---|
| -7% | 5063 | 2141 | -0.452% |
| **-8% (live)** | 4924 | 1849 | **-0.349%** |
| -9% | 4780 | 1576 | **-0.247%** |
| -10% | 4655 | 1366 | -0.277% |

Tightening the stop *raises* the number of stop-outs, so slippage gets paid more often, and EV gets worse. The trigger controls how *often* you pay the friction, not just how much you lose when you do. Both proposed "improvements" failed for the same underlying reason, which is the point of having a harness.

The table hints that a **-9%** stop may be better than the live -8%. That is a synthetic-data result on a driftless walk and is **not** authorization to change a live-money parameter — it needs confirmation against real bars for the actual scan universe. Left at -8% pending that. Run `python3 backtest.py --data data/ --sweep` once real data is dumped, and only move it if the improvement is statistically significant.

---

## Step 0 — Check the pause flag

Check whether a file named `PAUSE` exists in the repo root.

- **If it exists:** append one line to `run-log.md` (Timestamp, Run #, `Paused? = YES`, rest `—`, Action Taken = `none (paused)`, Notes = contents of `PAUSE`). Send a `PushNotification` saying the loop is paused. **Do nothing else. Exit immediately.**
- **If it doesn't exist:** continue to Step 1.

## Step 1 — Rebuild the ledger from the account (REVISED 2026-08-08)

Per `PLAN.md`: **the Robinhood account is authoritative, not the ledger.** As of 2026-08-08 this is enforced structurally — the ledger is a *derived* artifact that gets rebuilt every run, because runs cannot reliably persist files (see `LEDGER_BUG.md`).

1. Fetch account state: `get_accounts` (confirm the cash/"Agentic" account, `agentic_allowed: true`), `get_equity_positions`, `get_equity_orders`, `get_portfolio`.
2. Call `get_equity_orders` with `created_at_gte` set to **60 days ago** and `state: filled`. This is the authoritative trade history.
3. **Rebuild `ledger.md`'s table from that order history** — every fill becomes a row, buys matched to sells per symbol in FIFO order to compute realized P&L and a running total. Do not assume the existing file is correct; regenerate the rows from the broker data and overwrite.
4. **Preserve, do not regenerate, the `Dip-Attribution Summary` column** for any row that already has one — that reasoning exists only in this file and cannot be reconstructed from the broker. If a row has no summary, leave it blank. **Never invent a rationale for a historical trade.** Writing a plausible-sounding thesis after seeing the outcome corrupts the only dataset this strategy has.
5. Note any discrepancy between the prior file contents and the rebuilt version in this run's `run-log.md` Notes column.

Record `Reconciliation OK? = YES` (clean) or `YES (rebuilt, N rows differed)`.

## Step 2 — Compute total capital, benchmark it, check the kill switch

1. Total capital = cash + market value of all open positions (from `get_portfolio`, post-reconciliation).

**1a. Fetch the benchmark (judgment-call #14).** Call `get_equity_historicals(symbols=["SPY"], start_time="2026-07-30T00:00:00Z", interval="day")`. From it compute:
   - `SPY_since_inception` = SPY return from the 2026-07-30 close (**741.69**, the loop's inception baseline) to the latest close.
   - `portfolio_since_inception` = total capital vs **$2,000**.
   - `relative` = portfolio return − SPY return, in percentage points.

   Record all three in this run's `run-log.md` row. **A portfolio number without its benchmark is not interpretable** — "-2.4%" during a week SPY gained 4.26% is a 6.7pp shortfall, not a small loss. If the SPY fetch fails, log `benchmark unavailable` and continue; never block trading on it.

**1b. Underperformance tripwire (judgment-call #16).** If the trailing 30-day portfolio return trails SPY's by more than **10 percentage points**, add a `⚠️ UNDERPERFORMANCE REVIEW` line to this run's notification with both figures. **This is a flag, not a halt** — do not set `PAUSE`, do not change any trading behavior. It exists because every other control in this loop is absolute and therefore blind to losing steadily to the market in a rally. Acting on it is the user's call.
2. If total capital ≤ **$1,600** (80% of the $2,000 starting capital, judgment-call #8):
   - Write `PAUSE` to the repo root: `AUTO-PAUSED <UTC timestamp>: total capital $<X> is <Y>% below starting capital $2,000 (-20% kill switch triggered).`
   - Commit and push (Step 9 mechanics). **If the push fails, still send the notification** — the pause intent must reach the user even if the file doesn't persist.
   - Log as `AUTO-PAUSE TRIGGERED`, send a `PushNotification` stating the kill switch fired.
   - **Exit. Do not proceed.**
3. Otherwise continue.

## Step 3 — Manage existing positions (exits take priority over new buys)

For every open position:

1. **Stop-loss:** if current price ≤ buy price × **0.92** (-8% trigger, judgment-call #3), sell immediately via **market order**. No exceptions, no judgment override. Expect the fill to land 1-2% below the trigger — that is known, measured, and accepted.
2. **Take-profit:** if current price ≥ buy price × **1.06** (+6%, judgment-call #2), sell via **limit order** near current price.
3. **Max hold:** if neither triggered and the position has been held ≥ **12 trading days**, force-close at market.
4. For every exit, record it in `ledger.md`: Date, Ticker, `Action = SELL`, Price, Qty, Reason (which trigger fired), Dip-Attribution Summary (carried forward from the buy row), P&L, Running Total, **`Attribution Correct?`**, **`SPY Over Hold`**, and **`Excess`**.
   - `Attribution Correct?` — `YES` if exited on take-profit, `NO` if on stop-loss, `TIMEOUT` if force-closed. Never blank on a SELL row.
   - `SPY Over Hold` — SPY's return between the **buy date's close and the sell date's close**, i.e. the identical window. Take it from the Step 1a historicals.
   - `Excess` — trade return minus `SPY Over Hold`, in percentage points. **This is the number that says whether the trade was any good.** A +6% take-profit during a +8% market week is a loss in the only sense that matters, even though it books as a win.
5. **Settlement:** a same-day exit's proceeds are not settled cash until T+1 — do not count them as buying power later in this same run.

## Step 4 — Daily circuit breaker

Sum today's realized P&L from the rebuilt ledger (today's date, `Action = SELL`).

- If today's cumulative realized loss ≥ **6% of total capital**: **halt new buys for the rest of today.** Does not set `PAUSE`, does not affect future days. Log `circuit breaker — no new buys today`.
- Never blocks Step 3 exits.
- If tripped, skip to Step 9.

## Step 5 — Pre-buy gates: settled cash, then market regime

**5a. Settled buying power.** Confirm **settled cash**, not total balance — cash account, T+1. If settled buying power is below 20% of current total capital, skip the new-buy steps this run and note it in `run-log.md`.

**5b. Market-regime gate (judgment-call #15).** Call `get_equity_technical_indicators(symbol="SPY", type="ema", period=200, interval="day", output="latest")`. If SPY's current price is **below** its 200-day EMA, **make no new purchases this run.** Log `regime gate — no new buys (SPY below 200d EMA)` and skip to Step 9. Existing positions are unaffected: Step 3 exits always run regardless.

*Rationale: dip-buying into a downtrend is the failure mode this strategy is most exposed to — a falling market keeps producing "dips" that keep falling, and the buy filter cannot tell a macro drawdown from an oversold bounce in real time. This is also the safe place to address the market-relative-stop problem: preventing the exposure beats removing the stop-loss protection after the fact. Restrictive only — it can never cause a purchase, only prevent one.*

*If the indicator call fails, fall back to computing the 200-day EMA from the Step 1a SPY historicals (extend `start_time` far enough back). If neither is available, **skip new buys for the run** rather than trading blind, and note it.*

## Step 6 — Screen for dip candidates

Use the **fixed** scan criteria. Do not widen them even if the run returns few or no candidates:

- Price: $40-100/share
- Market cap: ≥ $5B
- Average volume: ≥ 500K/day

Use `get_scanner_filter_specs`, then `create_scan`/`update_scan_filters`, then `run_scan`. **Zero candidates is a valid, normal outcome** — log it and move to Step 9. Do not loosen criteria to force a result.

*Note on the filters added in Step 7: they only ever remove candidates, never add them. Narrowing the universe is consistent with `PLAN.md`'s rule, which prohibits loosening criteria to manufacture trades, not tightening them for safety.*

## Step 7 — Mechanical gates, then research (REVISED 2026-08-08)

Apply the cheap mechanical gates **first**, in this order, and drop candidates that fail before spending any research effort on them.

**Gate A — Earnings exclusion (judgment-call #10).** Call `get_earnings_calendar` for the next **14 days**. Drop any candidate scheduled to report in that window. *Rationale: a market stop-loss provides no protection against an overnight gap, and earnings are the single largest source of gap risk. Both 2026-08 stop-outs slipped 1.5-1.8% past their trigger; removing gap-prone names is the most direct way to cut that tax, and per the analysis in the callout box, friction — not the profit/loss ratio — is where the expectancy actually leaks.*

**Gate B — Wash-sale guard (judgment-call #11).** From the Step 1 order history, drop any candidate sold at a **loss within the last 30 calendar days**. Rebuying it disallows that loss for tax purposes and rolls it into the new cost basis. As of 2026-08-08 this applies to **EIX** (sold -9.42% on 2026-08-05) and **PBF** (sold -9.61% on 2026-08-06), both still inside the scan universe.

**Gate C — Spread cap (judgment-call #12).** From `get_equity_quotes`, compute `(ask - bid) / midpoint`. Drop the candidate if it exceeds **1.0%**. Skip this gate only if bid or ask is zero or the quote timestamp is stale (pre-market/after-hours artifacts) — in that case note it rather than guessing.

**Gate D — Trend filter (judgment-call #13).** Call `get_equity_technical_indicators` with `type: ema`, `period: 200`, `interval: day`, `output: latest`. Drop the candidate if current price is **below** the 200-day EMA. *Rationale: this mechanizes the DOCU-vs-TW distinction that `PLAN.md` reached for informally — a "dip" in a structural downtrend is not a dip. Buy weakness within an intact uptrend only.*

**Then, for surviving candidates in order of biggest dip first:**

1. `get_equity_fundamentals` — sector (for the sector cap), valuation context.
2. `get_earnings_results` — did the company report recently? Beat, meet, or miss?
3. `get_equity_historicals` (weekly bars, back to 2016 or IPO) — recovery profile. Write to a temp file and process with `jq`/Python; do not read the raw output inline. Look for: count of prior ≥6% drops, typical recovery time, unrecovered drops, distance from all-time high.
4. `WebSearch` "why is $TICKER down today" — news/analyst attribution.

**Apply the locked buy filter exactly:**
- **Buy** if the dip is sentiment/macro-driven (analyst downgrade alone, sector-wide selloff, index/rebalance noise) **or** an in-line-results-but-oversold reaction.
- **Skip** if there's a real earnings miss, guidance cut, margin/volume deterioration, or other fundamental worsening — **even if the reaction looks oversized.** When genuinely unsure, treat it as fundamental and skip. Err toward skipping.

Write a 2-4 sentence dip-attribution summary for every candidate you seriously evaluate. For the one you buy, this goes in the ledger — **it is the single most valuable thing each run produces**, because it is the only record that can later be scored against the outcome.

## Step 8 — Rank, size, and buy

1. Rank surviving candidates by biggest justified dip first.
2. Apply the sector cap: skip any candidate whose sector matches a sector you already hold.
3. Take the **single top-ranked** remaining candidate (judgment-call #6).
4. Position size = **20%** of current total capital, capped by settled buying power from Step 5.
5. `review_equity_order` to preflight, then `place_equity_order` as a **limit order** near current price.
6. Record in `ledger.md`: Date, Ticker, `Action = BUY`, Price, Qty, Reason (which buy-filter category), Dip-Attribution Summary (Step 7), P&L blank, Running Total carried forward, `Attribution Correct?` blank (filled on exit).
7. If nothing survives, that's a valid "no action" outcome — log it plainly, don't force a trade.

## Step 9 — Write, verify persistence, notify (REVISED 2026-08-08)

**Read this step carefully. Its previous version is why the loop logged nothing for its first 8 days.**

1. Append one row to `run-log.md`: Timestamp (UTC, actual current time), Run #, Paused? = NO, Reconciliation OK?, Candidates Scanned, Action Taken, **Portfolio %**, **SPY %**, **Relative (pp)** (all three from Step 1a, since inception), and Notes. Add a **`Persisted?`** value to the Notes column — filled in at step 5 below.
2. Save any `ledger.md` edits.
3. Set a git identity if none exists (`git config user.name` / `user.email` — check first, don't overwrite).
4. `git add ledger.md run-log.md` (plus `PAUSE` if Step 2 created it) and commit with a short message summarizing the run.
5. **Push, then verify the push actually landed.** Do not trust the exit code alone:
   ```
   git push origin HEAD 2>&1 | tee /tmp/push.log
   git fetch origin 2>/dev/null
   git rev-parse HEAD              # local
   git rev-parse origin/<branch>   # remote after fetch
   ```
   The push succeeded **only if those two hashes match.** Record `Persisted? = YES` or `Persisted? = NO`.
6. **If persistence failed, this is not a silent condition.** The trade itself already happened on Robinhood (authoritative), so the run is not a failure — but the *record* is gone, and that must be visible immediately:
   - Include a prominent `⚠️ PUSH FAILED — this run's reasoning was not saved` line at the **top** of the `PushNotification`, not buried at the end.
   - Include the first line of the actual git error, so the cause is diagnosable without a session.
   - Include the dip-attribution summary text **inline in the notification itself**. It is the only copy that will survive the container being reclaimed.

   Known cause as of 2026-08-08: the routines hold read-only repo scope and pushes are rejected at the agent proxy. Until that is fixed (see `LEDGER_BUG.md`), expect `Persisted? = NO` on every run and expect the notification to carry the reasoning.
7. **Always send a `PushNotification`**, including "no action taken" runs. Summarize: paused/circuit-breaker/regime-gated/normal, what was scanned, what was bought or sold, current total capital **and how that compares to SPY since inception** (Step 1a), plus persistence status. Lead with `⚠️ PUSH FAILED` or `⚠️ UNDERPERFORMANCE REVIEW` if either applies. Silence must never mean "the loop didn't check."

## Step 10 — Exit

Nothing further. The next run starts fresh. Everything it needs lives in the reconciled Robinhood account state and — when persistence is working — in `ledger.md` and `run-log.md`.
