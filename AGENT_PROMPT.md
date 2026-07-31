# Dip-Buy Loop — Runtime Instructions

**This file is read and executed by the scheduled cloud routine itself.** Each run is a fresh, isolated session with zero memory of prior runs — this file plus the repo's other files (`PLAN.md`, `ledger.md`, `run-log.md`) are the entire context. If you are the agent executing a scheduled run: follow the numbered steps below in order, exactly. If you are a human reviewing this before it goes live: read the callout box first — those are the specific numbers and structural choices that were *not* explicitly locked in `PLAN.md` and need your sign-off before this runs with real money.

---

## ⚠️ Judgment calls made while drafting this file — reviewed and confirmed 2026-07-31

`PLAN.md`'s "Locked decisions" give *ranges* (e.g. "+5-8% take-profit") or leave some mechanics unspecified. An autonomous agent needs exact numbers and exact mechanics, not ranges. **All defaults below, including "max 1 new position per run," were reviewed and explicitly confirmed by the user on 2026-07-31 — this table is no longer pending, it's the locked implementation.** Keep it in sync if any of these are ever revisited.

| # | Item | Default chosen | Why this one | Locked range/constraint it must stay inside |
|---|---|---|---|---|
| 1 | Position size | **20%** of current total capital per position | Lower bound of the range → more diversification headroom | Locked: 20-25% |
| 2 | Take-profit | **+6%** | Middle of range | Locked: +5-8% |
| 3 | Stop-loss | **-8%** | Middle of range | Locked: -7% to -10% |
| 4 | Daily circuit breaker | **6%** of total capital cumulative daily loss | Middle of range | Locked: 5-8% |
| 5 | Max hold period | **12** trading days | Middle of range | Locked: 10-15 days |
| 6 | New positions bought per run | **At most 1** (top-ranked qualifying candidate; others wait for a future run) | Simpler, more auditable, slower capital deployment | **Not specified in PLAN.md** — ranking rule could plausibly mean "buy several if they qualify," this is my interpretation |
| 7 | Pause-flag mechanism | A file named **`PAUSE`** in repo root; presence = halted, regardless of content | Simple, git-trackable, works naturally with the fresh-clone-per-run model | **Not specified in PLAN.md** — file name/location was never decided |
| 8 | Starting capital (for -20% kill switch) | **$2,000** — confirmed via `get_portfolio` on 2026-07-30 | Matches the actual funded amount at time of writing | Must be updated here if more capital is ever added to the account |
| 9 | Sector field source | Robinhood's `sector` field from `get_equity_fundamentals` | Only real option available | Resolves the open item in `PLAN.md` |

**If any of these should change, edit this table and the corresponding step below before the routines go live — don't leave the mismatch.**

---

## Step 0 — Check the pause flag

Check whether a file named `PAUSE` exists in the repo root.

- **If it exists:** append one line to `run-log.md` (Timestamp, Run #, `Paused? = YES`, Reconciliation OK = `—`, Candidates Scanned = `—`, Action Taken = `none (paused)`, Notes = contents of the `PAUSE` file if any). Send a `PushNotification` saying the loop is paused. **Do nothing else. Exit immediately.** Do not reconcile, do not check positions, do not scan. This matches `PLAN.md`'s locked kill-switch mechanism literally: paused means paused, full stop.
- **If it doesn't exist:** continue to Step 1.

## Step 1 — Reconcile the ledger against the live account

Per `PLAN.md`: **the Robinhood account (positions + orders) is authoritative, not the ledger.** The ledger can be wrong (e.g., a prior run placed an order but crashed before writing the ledger row).

1. Fetch current account state: `get_accounts` (confirm you're using the cash/"Agentic" account, `agentic_allowed: true`), `get_equity_positions`, `get_equity_orders` (open/pending orders), `get_portfolio`.
2. Compare against `ledger.md`'s rows. If the account shows a position, fill, or order that isn't reflected in the ledger (or vice versa — a ledger row with no matching account activity), **update the ledger to match reality** and note the discrepancy in this run's `run-log.md` Notes column. Never edit the account to match the ledger — only ever the other direction.
3. If reconciliation finds nothing to fix, that's the normal case — proceed.

Record `Reconciliation OK? = YES` (clean) or `YES (fixed N discrepancies)` in this run's `run-log.md` row once done.

## Step 2 — Compute current total capital and check the overall kill switch

1. Total capital = cash + market value of all open positions (from `get_portfolio`, post-reconciliation).
2. If total capital ≤ **80% of $2,000** (i.e., ≤ $1,600 — see judgment-call #8 above), the account has hit the locked -20% drawdown kill switch:
   - Write `PAUSE` to the repo root with contents: `AUTO-PAUSED <UTC timestamp>: total capital $<X> is <Y>% below starting capital $2,000 (-20% kill switch triggered).`
   - Commit and push this change (see Step 9 for git mechanics).
   - Log this run as the pause-triggering run in `run-log.md` (Action Taken = `AUTO-PAUSE TRIGGERED`).
   - Send a `PushNotification` clearly stating the kill switch fired and the loop is now halted until the user deletes `PAUSE`.
   - **Do not proceed to any further step this run.** Exit.
3. If capital is above the threshold, continue.

## Step 3 — Manage existing positions (exits take priority over new buys)

For every open position (from Step 1's reconciled state):

1. **Stop-loss check:** if current price ≤ buy price × 0.92 (locked -8% default, judgment-call #3), sell immediately via **market order** (locked order-type decision — certainty of exit over price precision). No exceptions, no judgment override, even if you believe the drop is "temporary" — this is explicitly locked in `PLAN.md`.
2. **Take-profit check:** if current price ≥ buy price × 1.06 (locked +6% default, judgment-call #2), sell via **limit order** near current price (locked order-type decision).
3. **Max hold check:** if neither has triggered and the position has been held ≥ 12 trading days (judgment-call #5), force-close at market.
4. For every exit executed: record it in `ledger.md` (Date, Ticker, `Action = SELL`, Price, Qty, Reason = which trigger fired, Dip-Attribution Summary = carry forward from the original buy row, P&L = realized gain/loss on this trade, Running Total = updated cumulative).
5. **Settlement note:** a same-day exit's proceeds are not settled cash until T+1 — don't count today's exit proceeds as available buying power later in this same run (see Step 5).

## Step 4 — Daily circuit breaker check

Sum today's realized P&L from `ledger.md` (rows with today's date and `Action = SELL`), cross-checked against Robinhood's own realized-P&L data for today if available.

- If today's cumulative realized loss ≥ **6% of total capital** (judgment-call #4): **halt new buys for the rest of today only.** This does *not* set the `PAUSE` file and does *not* affect future days — it only skips Step 5-8 below for this run and any remaining runs scheduled later today. Note this clearly in `run-log.md` (Action Taken = `circuit breaker — no new buys today`).
- This check only blocks *new* positions. It never blocks Step 3 (exits) — protecting capital on existing positions always happens regardless of circuit-breaker state.
- If the breaker is tripped, skip to Step 9 (ledger/log write + notification) — do not scan for new candidates.

## Step 5 — Check settled buying power

Before scanning for anything to buy, confirm **settled cash**, not just account balance or total buying power — per `PLAN.md`'s cash-account/T+1 note. If settled buying power is below the minimum viable position size (20% of current total capital), skip new-buy steps entirely this run (there's nothing to buy with) and note this in `run-log.md`.

## Step 6 — Screen for dip candidates

Use the **fixed** scan criteria — do not widen them even if this run returns few or no candidates:

- Price: $40-100/share
- Market cap: ≥ $5B
- Average volume: ≥ 500K/day

Use the Robinhood scanner tools (`get_scanner_filter_specs`, `create_scan` or `update_scan_filters`, `run_scan`) to find today's biggest dips within this universe. **Zero candidates is a valid, normal outcome** — if nothing qualifies, log it and move to Step 9. Do not loosen criteria to force a result.

## Step 7 — Research and classify each candidate (the buy filter)

For each candidate from Step 6, in order of biggest dip first:

1. `get_equity_fundamentals` — sector (for the sector-cap rule below), valuation context.
2. `get_earnings_results` — did the company report recently? Beat, meet, or miss?
3. `get_equity_historicals` (weekly bars, back to 2016 or IPO) — recovery-history profile. Write the result to a temp file and process with `jq`/Python rather than reading the raw output inline (it's large). Look for: how many prior ≥6% drops, how long they typically took to recover, whether any are still unrecovered, and how far the stock currently sits from its all-time high. A stock with many stacked unrecovered drops or deep below-ATH is showing structural decline, not a dip — treat that as a strong negative signal regardless of what today's news says.
4. `WebSearch` for "why is $TICKER down today" — get the actual news/analyst attribution.

**Apply the locked buy filter exactly:**
- **Buy candidate** if the dip is sentiment/macro-driven (analyst downgrade alone, sector-wide selloff, index/rebalance noise) **or** an in-line-results-but-oversold reaction.
- **Skip** if there's a real earnings miss, guidance cut, margin/volume deterioration, or other fundamental worsening — **even if the market's reaction looks oversized relative to the news.** This loop is not equipped to underwrite "how much is this guidance cut really worth" in a 2-3x/day cycle; when genuinely unsure whether something is fundamental or sentiment, treat it as fundamental and skip. Err toward skipping, not buying.

Write a 2-4 sentence dip-attribution summary per candidate you seriously evaluate — this becomes the ledger's Dip-Attribution Summary for any that get bought, and is worth keeping even for skipped ones in this run's reasoning (not persisted, just needed to make the ranking decision in Step 8).

## Step 8 — Rank, size, and buy

1. Among candidates that passed Step 7's filter, rank by biggest justified dip first.
2. Apply the sector cap: skip any candidate whose sector (per `get_equity_fundamentals`) matches a sector you already hold a position in.
3. Take the **single top-ranked** remaining candidate (judgment-call #6 — only one new position per run).
4. Position size = 20% of current total capital (judgment-call #1), capped by available settled buying power from Step 5.
5. Use `review_equity_order` first to preflight the order, then `place_equity_order` as a **limit order** near current price (locked order-type decision for entries).
6. If the order fills (or is accepted — note whether you confirmed a fill or just submission), record it in `ledger.md`: Date, Ticker, `Action = BUY`, Price, Qty, Reason (which buy-filter category it qualified under), Dip-Attribution Summary (from Step 7), P&L = blank (position still open), Running Total = carried forward unchanged.
7. If no candidate survives Steps 6-8 (nothing scanned, nothing passed the filter, or sector/capital constraints eliminated everything), that's a valid "no action" outcome — log it plainly, don't force a trade.

## Step 9 — Write the run log, commit, push, notify

1. Append one row to `run-log.md`: Timestamp (UTC, use the actual current time), Run # (increment from the last row), Paused? = NO, Reconciliation OK?, Candidates Scanned (count from Step 6), Action Taken (plain summary — e.g. `bought TICKER`, `sold TICKER (stop-loss)`, `no action — no qualifying candidates`, `circuit breaker — no new buys`), Notes (anything unusual: reconciliation fixes, near-misses, errors encountered).
2. If `ledger.md` was modified in this run, make sure those edits are saved too.
3. Set a git identity if none is configured in this fresh clone (`git config user.name "Trading Agent Loop"` / `git config user.email "trading-agent@noreply.local"` — check first with `git config user.name` before setting, don't overwrite if already present).
4. `git add ledger.md run-log.md` (and `PAUSE` if Step 2 created it), commit with a short message summarizing the run's action, and push. **If push fails for any reason, do not treat this as fatal to the run** — the trade itself (if any) already happened on the authoritative Robinhood side; a failed push just means this run's log entry needs to be reconciled by the *next* run (Step 1 handles this). Note the push failure in this run's notification.
5. **Always send a `PushNotification`** — including "no action taken" runs. Summarize: whether paused/circuit-breaker/normal, what was scanned, what (if anything) was bought or sold, and current total capital. Silence must never mean "the loop didn't check" — this is a locked decision in `PLAN.md` precisely because live money is involved.

## Step 10 — Exit

Nothing further. The next scheduled run starts fresh with no memory of this one — everything it needs to pick up where this run left off lives in the reconciled Robinhood account state and in `ledger.md`/`run-log.md`, which is why Steps 1 and 9 matter as much as the trading logic itself.
