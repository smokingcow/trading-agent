# Trading Ledger

Source of truth is the live Robinhood account (positions + orders). This ledger is a human-readable log **rebuilt from Robinhood order history at the start of every run** — see `AGENT_PROMPT.md` Step 1. It is a derived artifact, not primary state: if it is ever lost, truncated, or fails to push, the next run reconstructs it. Never hand-maintain it in a way that conflicts with the account.

Columns: Date | Ticker | Action | Price | Qty | Reason | Dip-Attribution Summary | P&L | Running Total | Attribution Correct? | SPY Over Hold | Excess

`SPY Over Hold` and `Excess` are filled in on SELL rows only, and `Excess` is the number that actually matters: trade return minus SPY's return over the *identical* holding window. A +6% take-profit during a +8% market week books as a win and is a loss in the only sense that counts. Without this column a portfolio number cannot be told apart from market beta.

`Attribution Correct?` is filled in on SELL rows only — it scores whether the original buy thesis proved right (`YES` = exited on take-profit, thesis held; `NO` = exited on stop-loss, thesis failed; `TIMEOUT` = force-closed at max hold, thesis neither confirmed nor refuted). This column exists so win rate can be measured *by classification type*, which is what makes the strategy falsifiable over time.

---

## Backfill note (2026-08-08)

Rows dated 2026-07-31 through 2026-08-07 were **reconstructed from `get_equity_orders`** after discovering that no run had ever successfully written to this file (see `LEDGER_BUG.md` for the root cause). Prices, quantities, dates and P&L are exact — they come from the broker's own fill records.

**The Dip-Attribution Summary for those rows is permanently lost.** Each run computed a thesis and then discarded it when the push failed. It is not recoverable from any source, and it has been left blank rather than reconstructed — inventing plausible-sounding rationales after seeing the outcomes would poison the only dataset this strategy has. Treat the pre-2026-08-08 rows as price/P&L data only, with no usable signal about *why* each trade was taken.

---

| Date | Ticker | Action | Price | Qty | Reason | Dip-Attribution Summary | P&L | Running Total | Attribution Correct? | SPY Over Hold | Excess |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-07-31 | EIX | BUY | $75.6900 | 5 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$0.00 | — | — | — |
| 2026-07-31 | BTSG | BUY | $60.7799 | 6 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$0.00 | — | — | — |
| 2026-07-31 | NXT | BUY | $89.7632 | 4 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$0.00 | — | — | — |
| 2026-08-03 | FTI | BUY | $69.5699 | 6 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$0.00 | — | — | — |
| 2026-08-03 | PBF | BUY | $67.5399 | 6 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$0.00 | — | — | — |
| 2026-08-04 | NXT | SELL | $96.1165 | 4 | Take-profit (limit order) | *(original thesis not recorded)* | **+$25.41 (+7.08%)** | +$25.41 | YES | +3.25% | **+3.82 pp** |
| 2026-08-05 | EIX | SELL | $68.5601 | 5 | Stop-loss (market order) | *(original thesis not recorded)* | **-$35.65 (-9.42%)** | -$10.24 | NO | +3.05% | **-12.47 pp** |
| 2026-08-06 | PBF | SELL | $61.0501 | 6 | Stop-loss (market order) | *(original thesis not recorded)* | **-$38.94 (-9.61%)** | -$49.18 | NO | +1.44% | **-11.05 pp** |
| 2026-08-06 | ACIW | BUY | $54.6889 | 7 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$49.18 | — | — | — |
| 2026-08-06 | XYZ | BUY | $79.0299 | 5 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$49.18 | — | — | — |
| 2026-08-07 | MNST | BUY | $90.4400 | 4 | Backfilled from broker fill record | *(not recorded — lost to Step 9 push failure)* | — | -$49.18 | — | — | — |
| 2026-08-10 | FTI | SELL | $74.2301 | 6 | Take-profit (limit order) | *(original thesis not recorded — backfilled buy row)* | **+$27.96 (+6.70%)** | -$21.22 | YES | +2.06% | **+4.64 pp** |

---

## Position and P&L summary as of 2026-08-10 (19:17 UTC run)

**Realized:** 4 closed round-trips — 2 wins, 2 losses. Total realized P&L **-$21.22**. FTI take-profit (+6.70%) closed this run.

| Ticker | Entry | Exit | Held | Return | SPY same window | **Excess** | Exit trigger |
|---|---|---|---|---|---|---|---|
| NXT | $89.7632 | $96.1165 | 4 days | +7.08% | +3.25% | **+3.82 pp** | Take-profit |
| EIX | $75.6900 | $68.5601 | 5 days | -9.42% | +3.05% | **-12.47 pp** | Stop-loss |
| PBF | $67.5399 | $61.0501 | 3 days | -9.61% | +1.44% | **-11.05 pp** | Stop-loss |
| FTI | $69.5699 | $74.2301 | 5 trading days | +6.70% | +2.06% | **+4.64 pp** | Take-profit |
| | | | | **-5.25%** | **+9.80%** | **-15.06 pp** | |

**Read the Excess column, not the Return column.** Every trade so far ran during a market rally, so raw returns flatter the strategy. The two wins produced only **+3.82pp** and **+4.64pp** of genuine alpha — the rest was market drift the loop would have captured by doing nothing. Across all four closed trades the strategy has given up **15.1 percentage points** relative to simply holding SPY. FTI is the second win in a row that cleared its target *and* beat SPY over the identical window — the first two closed trades that both booked a gain and produced positive excess.

**Portfolio vs benchmark since inception (2026-07-30 → 2026-08-10):** portfolio **-1.34%**, SPY **+4.26%**, relative **-5.60 pp**. Sample is 4 closed trades — far too small to conclude the strategy is broken (92-737 closed trades are needed, see `STRATEGY_RESEARCH_2.md` §1). It is, however, large enough to establish that absolute P&L alone was hiding the picture entirely.

**Stop-loss slippage:** both stop-outs filled *past* their -8% trigger — EIX at -9.42% vs a $69.63 trigger, PBF at -9.61% vs a $62.14 trigger. That is ~1.5-1.8% of market-order gap cost per stop, and it is the reason the take-profit/stop-loss levels were revised on 2026-08-08 (see `AGENT_PROMPT.md` judgment-call table #2/#3). The FTI take-profit, being a limit order, filled *above* its $74.15 limit at $74.2301 — price improvement rather than slippage.

**Open positions:** 4, cost basis $1,504.41, plus $29 settled cash + $445.38 unsettled FTI proceeds (T+1). Current market value of holdings $1,498.74 (unrealized **-$5.67**). *(Snapshot refreshed at the 2026-08-10 19:17 UTC run.)*

| Ticker | Qty | Avg cost | Current | Held since | Days held |
|---|---|---|---|---|---|
| BTSG | 6 | $60.78 | $61.50 | 2026-07-31 | 7 |
| ACIW | 7 | $54.69 | $52.745 | 2026-08-06 | 4 |
| XYZ | 5 | $79.03 | $79.28 | 2026-08-06 | 4 |
| MNST | 4 | $90.44 | $91.03 | 2026-08-07 | 3 |

FTI hit its +6% take-profit this run (current $74.19 ≥ $73.74 trigger) and was sold via limit order at $74.2301. No other position triggered: none hit the -8% stop or the 12-trading-day max hold (oldest = BTSG at 7 trading days). New buys skipped — settled cash $29 is below 20% of total capital ($394.62), so Step 5a halted the new-buy steps before the regime gate and scan. FTI's proceeds settle T+1 and are not buying power this run.

**Account total:** $1,973.12 vs $2,000.00 starting capital = **-1.34%** (SPY +4.26% same window; relative -5.60 pp). Kill-switch threshold is $1,600 (-20%); not close.
