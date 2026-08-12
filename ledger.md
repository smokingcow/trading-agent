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
| 2026-08-11 | VTR | BUY | $88.1253 | 4 | Sentiment/sector dip (healthcare-REIT selloff; fundamentally intact) | VTR fell -4.1% to ~$87.86 (filled $88.13), a sector/rate-driven pullback: AHR priced a $712M dilutive secondary offering that pressured senior-housing REIT peers (VTR, OHI also down) on a day the broad market was up (+0.2%). VTR beat Q2 earnings 07-29 ($0.97 vs $0.96 est, +9% YoY FFO growth) with no company-specific negative news; the ~13% slide from its 07-28 ATH ($101.60) is a valuation/rate derating of a sector that ran ~50%, not fundamental deterioration. Bought as a sentiment/sector dip in an intact uptrend — still +5% above its 200-day EMA ($83.60), with a long history of recovering pullbacks. | — | -$21.22 | — | — | — |

---

**Corporate action (2026-08-11): MNST 2-for-1 stock split.** The broker position now shows **8 shares @ $45.22 avg cost** (was 4 @ $90.44); cost basis unchanged at $361.76. The `get_equity_orders` fill record still shows the pre-split buy (4 @ $90.44 on 2026-08-07) — that historical row is left as-is. Split-adjusted triggers for MNST: stop-loss $41.60, take-profit $47.93.

---

## Position and P&L summary as of 2026-08-12 (19:16 UTC run)

**Realized:** 4 closed round-trips — 2 wins, 2 losses. Total realized P&L **-$21.22** (unchanged; no exits and no new buy this run — settled cash below the 20% threshold).

| Ticker | Entry | Exit | Held | Return | SPY same window | **Excess** | Exit trigger |
|---|---|---|---|---|---|---|---|
| NXT | $89.7632 | $96.1165 | 4 days | +7.08% | +3.25% | **+3.82 pp** | Take-profit |
| EIX | $75.6900 | $68.5601 | 5 days | -9.42% | +3.05% | **-12.47 pp** | Stop-loss |
| PBF | $67.5399 | $61.0501 | 3 days | -9.61% | +1.44% | **-11.05 pp** | Stop-loss |
| FTI | $69.5699 | $74.2301 | 5 trading days | +6.70% | +2.06% | **+4.64 pp** | Take-profit |
| | | | | **-5.25%** | **+9.80%** | **-15.06 pp** | |

**Read the Excess column, not the Return column.** Every trade so far ran during a market rally, so raw returns flatter the strategy. The two wins produced only **+3.82pp** and **+4.64pp** of genuine alpha — the rest was market drift the loop would have captured by doing nothing. Across all four closed trades the strategy has given up **15.1 percentage points** relative to simply holding SPY. FTI is the second win in a row that cleared its target *and* beat SPY over the identical window — the first two closed trades that both booked a gain and produced positive excess.

**Portfolio vs benchmark since inception (2026-07-30 → 2026-08-12 19:16 UTC):** portfolio **-2.16%** ($1,956.83 vs $2,000), SPY **+4.24%** ($741.69 → $773.17 live), relative **-6.40 pp**. (The prior 17:13 snapshot read -6.51 pp at total capital $1,953.80; roughly flat into the close — BTSG $59.88→$59.90, VTR $88.97→$88.74, XYZ $77.74→$77.92, MNST $45.525→$45.67, ACIW $51.99→$52.24 — total capital +$3 as SPY ticked up ~0.04pp.) Sample is 4 closed trades — far too small to conclude the strategy is broken (92-737 closed trades are needed, see `STRATEGY_RESEARCH_2.md` §1). It is, however, large enough to establish that absolute P&L alone was hiding the picture entirely. Underperformance tripwire not flagged (-6.40pp < -10pp threshold).

**Stop-loss slippage:** both stop-outs filled *past* their -8% trigger — EIX at -9.42% vs a $69.63 trigger, PBF at -9.61% vs a $62.14 trigger. That is ~1.5-1.8% of market-order gap cost per stop, and it is the reason the take-profit/stop-loss levels were revised on 2026-08-08 (see `AGENT_PROMPT.md` judgment-call table #2/#3). The FTI take-profit, being a limit order, filled *above* its $74.15 limit at $74.2301 — price improvement rather than slippage.

**Open positions:** 5, cost basis $1,857.31, plus $121.88 settled cash (unsettled_funds $0 — all cash settled). *(Snapshot refreshed at the 2026-08-12 19:16 UTC run.)*

| Ticker | Qty | Avg cost | Current | Held since | Days held (trading) |
|---|---|---|---|---|---|
| BTSG | 6 | $60.78 | $59.90 | 2026-07-31 | 9 |
| ACIW | 7 | $54.69 | $52.24 | 2026-08-06 | 5 |
| XYZ | 5 | $79.03 | $77.92 | 2026-08-06 | 5 |
| MNST | 8 | $45.22 | $45.67 | 2026-08-07 | 4 |
| VTR | 4 | $88.1253 | $88.74 | 2026-08-11 | 2 |

**MNST** holds 8 shares @ $45.22 after the 2-for-1 split (cost basis unchanged $361.76; see corporate-action note above). **No exits this run:** none of the 5 positions hit the -8% stop, +6% take-profit, or the 12-trading-day max hold (oldest = BTSG at 9 trading sessions). BTSG $59.90 (SL $55.92); ACIW $52.24 (SL $50.31, nearest to a stop but inside band), XYZ $77.92 (SL $72.71), MNST $45.67 (SL $41.60), VTR $88.74 (SL $81.07) all inside their bands. **No new buy:** settled cash $121.88 is below 20% of total capital ($391.37), so Step 5a skipped the new-buy path (regime gate and scan not reached). No overnight settlement this run since no exit sold anything.

**Account total:** $1,956.83 vs $2,000.00 starting capital = **-2.16%** (SPY +4.24% same window, $741.69 → $773.17 live; relative -6.40 pp). Kill-switch threshold is $1,600 (-20%); not close. Settled buying power: $121.88.
