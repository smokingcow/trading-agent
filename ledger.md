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
| 2026-08-17 | BTSG | SELL | $61.0501 | 6 | Max-hold force-close (12 trading days; market order) | *(original thesis not recorded — backfilled buy row)* | **+$1.62 (+0.44%)** | -$19.60 | TIMEOUT | +3.81% | **-3.37 pp** |

---

**Corporate action (2026-08-11): MNST 2-for-1 stock split.** The broker position now shows **8 shares @ $45.22 avg cost** (was 4 @ $90.44); cost basis unchanged at $361.76. The `get_equity_orders` fill record still shows the pre-split buy (4 @ $90.44 on 2026-08-07) — that historical row is left as-is. Split-adjusted triggers for MNST: stop-loss $41.60, take-profit $47.93.

---

## Position and P&L summary as of 2026-08-19 (14:17 UTC run)

**Realized:** 5 closed round-trips — 2 wins, 2 losses, 1 timeout. Total realized P&L **-$19.60** (unchanged this run — no exits triggered and no new buy). Fourth consecutive run with the new-buy path open (cash $488.18 all settled) but no candidate surviving the buy filter — the semiconductor/electronics structural selloff continues to dominate the dip leaderboard.

| Ticker | Entry | Exit | Held | Return | SPY same window | **Excess** | Exit trigger |
|---|---|---|---|---|---|---|---|
| NXT | $89.7632 | $96.1165 | 4 days | +7.08% | +3.25% | **+3.82 pp** | Take-profit |
| EIX | $75.6900 | $68.5601 | 5 days | -9.42% | +3.05% | **-12.47 pp** | Stop-loss |
| PBF | $67.5399 | $61.0501 | 3 days | -9.61% | +1.44% | **-11.05 pp** | Stop-loss |
| FTI | $69.5699 | $74.2301 | 5 trading days | +6.70% | +2.06% | **+4.64 pp** | Take-profit |
| BTSG | $60.7799 | $61.0501 | 12 trading days | +0.44% | +3.81% | **-3.37 pp** | Max-hold (timeout) |
| | | | | **-4.81%** | **+13.61%** | **-18.43 pp** | |

**Read the Excess column, not the Return column.** Every closed trade so far ran during a market rally, so raw returns flatter the strategy. The two take-profit wins produced only **+3.82pp** and **+4.64pp** of genuine alpha; the rest was market drift the loop would have captured by doing nothing. BTSG is the first timeout: held the full 12 sessions, drifted +0.44% while SPY gained +3.81% over the identical window — a **-3.37pp** relative loss that books as a nominal "gain," the clearest illustration yet of why the Excess column is the one that matters. Across all five closed trades the strategy has given up **18.4 percentage points** relative to simply holding SPY. Sample is 5 closed trades — far too small to conclude anything about the strategy (92-737 closed trades are needed, see `STRATEGY_RESEARCH_2.md` §1).

**Stop-loss slippage:** both stop-outs filled *past* their -8% trigger — EIX at -9.42% vs a $69.63 trigger, PBF at -9.61% vs a $62.14 trigger. That is ~1.5-1.8% of market-order gap cost per stop, and it is the reason the take-profit/stop-loss levels were revised on 2026-08-08 (see `AGENT_PROMPT.md` judgment-call table #2/#3). The FTI take-profit, being a limit order, filled *above* its $74.15 limit at $74.2301 — price improvement rather than slippage. The BTSG max-hold exit, a market order, filled at $61.0501 essentially at the bid ($61.02) — no meaningful slippage on a non-stressed sale.

**Portfolio vs benchmark since inception (2026-07-30 → 2026-08-19 14:17 UTC):** portfolio **+0.43%** (total capital $2,008.63 vs $2,000), SPY **+3.74%** ($741.69 → $769.39 live), relative **-3.31 pp**. Roughly flat vs the prior run — the book edged up on modest gains in XYZ (+1.8%), MNST (+0.8%) and VTR (+0.3%) while SPY was near-flat (+0.25% intraday). The -3.31pp gap is persistent beta drag: the book has consistently trailed SPY's rally since inception. Underperformance tripwire not flagged (-3.31pp < -10pp threshold).

**Open positions:** 4, cost basis $1,504.76, plus $488.18 cash (all settled). *(Snapshot refreshed at the 2026-08-19 14:17 UTC run.)*

| Ticker | Qty | Avg cost | Current | Held since | Days held (trading) |
|---|---|---|---|---|---|
| ACIW | 7 | $54.69 | $52.68 | 2026-08-06 | 10 |
| XYZ | 5 | $79.03 | $80.835 | 2026-08-06 | 10 |
| MNST | 8 | $45.22 | $47.75 | 2026-08-07 | 9 |
| VTR | 4 | $88.1253 | $91.49 | 2026-08-11 | 7 |

**MNST** holds 8 shares @ $45.22 after the 2-for-1 split (cost basis unchanged $361.76; see corporate-action note above). **No exit this run:** none of the 4 positions hit the -8% stop, +6% take-profit, or the 12-day max hold (oldest ACIW/XYZ = 10 trading sessions, 2 short of 12): ACIW $52.68 (SL $50.31, TP $57.97), XYZ $80.835 (SL $72.71, TP $83.77 — ~$2.94 below TP), MNST $47.75 (SL $41.60, TP $47.93 — **~$0.18 below TP**, nearest a target), VTR $91.49 (SL $81.08, TP $93.41 — ~$1.92 below TP) all inside their bands. MNST remains the closest to a trigger and could hit +6% TP on a modest upside move. **No new buy despite the open path:** settled buying power $488.18 > 20% of capital ($401.73), Steps 5b–8 ran — SPY $769.39 > 200d EMA $709.28 (regime gate PASSED), scanned 115 dips. The dip leaderboard is again dominated by the **structural semiconductor/electronics selloff** (SPY flat at +0.25%, so these are idiosyncratic single-name plunges, not a macro dip): AXTI -10.9%, MXL -8.5%, HPE -7.2%, AMKR -7.0%, ACMR -6.9%, MRCY -6.4%, RKLB -6.2%, HUT -5.7%, INTC -5.2%, KTOS -5.0%, plus GFS/ON/RMBS/STM/MCHP — nearly all Electronic-Technology sector, many unprofitable, all far below 52-week highs. AXTI ($73.37 > EMA $55.58) and MXL ($66.44 > EMA $53.64) technically clear the trend gate (they ran up so hard the slow 200d average lags) but are **violent momentum unwinds down ~48% from May/June highs**, plunging -10.9%/-8.5% on a flat market with last earnings 3+ weeks ago — pure sector-sympathy selling in the documented structural downtrend (the exact falling-knife setup that stopped out EIX/PBF). MRCY -6.4% reported **08-18 pm**, beat ($0.37 vs $0.35 est) yet sold off — a beat-but-drop after a $62→$128 run reads as guidance/valuation derating, ambiguous → skip. Wash-sale blocklist (EIX, PBF) — PBF appeared in the scan at -1.95%, dropped. No fundamentally-sound isolated sentiment dip in an intact uptrend → **fourth consecutive no-buy**, valid no-action; did not force a trade.

**Account total:** $2,008.63 vs $2,000.00 starting capital = **+0.43%** (SPY +3.74% same window, $741.69 → $769.39 live; relative **-3.31 pp**). Kill-switch threshold is $1,600 (-20%); not close. Settled buying power: $488.18 (all settled).
