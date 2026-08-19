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
| 2026-08-19 | WMB | BUY | $73.2399 | 5 | Sentiment/sector dip (midstream selloff; fundamentally intact & improving) | WMB fell -2.5% to ~$73.24 as part of a sector-wide midstream/pipeline selloff (TRP, ENB, KGS all down the same day) on soft natural-gas sentiment (Henry Hub ~$2.87/MMBtu, ~29% off the Jan peak), while the broad market was UP (SPY +0.3% intraday) — so the dip is macro/sector-driven, not company-specific. Williams reported Q2 2026 on 08-03 essentially in-line ($0.50 vs $0.51 est) but RAISED full-year EBITDA guidance +$200M at midpoint and lifted its long-term growth target to 11%+ CAGR through 2030, drawing a wave of analyst upgrades/PT hikes (Goldman, Jefferies, RBC, BofA, Morgan Stanley; targets to $82) on Transco/LNG/AI-data-center demand. It is a fee-based (Transco) blue-chip largely insulated from gas prices, trading ~6% off its all-time high and +4.9% above its 200-day EMA ($69.86) — an intact uptrend — with a 10-year history of recovering ≥6% weekly drops (31 of 555 weeks, still near ATH). Bought as a sentiment/sector dip in a fundamentally-improving name in an intact uptrend. | — | -$19.60 | — | — | — |

---

**Corporate action (2026-08-11): MNST 2-for-1 stock split.** The broker position now shows **8 shares @ $45.22 avg cost** (was 4 @ $90.44); cost basis unchanged at $361.76. The `get_equity_orders` fill record still shows the pre-split buy (4 @ $90.44 on 2026-08-07) — that historical row is left as-is. Split-adjusted triggers for MNST: stop-loss $41.60, take-profit $47.93.

---

## Position and P&L summary as of 2026-08-19 (17:14 UTC run)

**Realized:** 5 closed round-trips — 2 wins, 2 losses, 1 timeout. Total realized P&L **-$19.60** (unchanged this run — no exits triggered). **NEW BUY this run: WMB, 5 shares @ $73.2399 ($366.20).** First new position since VTR (2026-08-11) and the first buy after five consecutive no-buy runs. The semiconductor/electronics structural selloff still dominates the top of the dip leaderboard (all skipped as falling knives / sector-cap / fundamental deterioration), but a fundamentally-sound midstream name (WMB) dipping on a sector-wide pullback in an intact uptrend cleared every gate and the buy filter.

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

**Portfolio vs benchmark since inception (2026-07-30 → 2026-08-19 17:14 UTC):** portfolio **+0.35%** (total capital ~$2,006.94 vs $2,000), SPY **+3.78%** ($741.69 → $769.74 live), relative **-3.43 pp**. Roughly flat vs the 14:17 run — the book eased slightly (ACIW $52.68→$52.425, VTR $91.49→$91.735, MNST $47.75→$47.305) as SPY ticked up. The -3.43pp gap is persistent beta drag: the book has consistently trailed SPY's rally since inception. Underperformance tripwire not flagged (-3.43pp < -10pp threshold).

**Open positions:** 5 after the WMB buy, cost basis ~$1,870.96, plus ~$121.98 cash (WMB buy consumed $366.20 of the $488.18 settled cash). *(Snapshot refreshed at the 2026-08-19 17:14 UTC run.)*

| Ticker | Qty | Avg cost | Current | Held since | Days held (trading) |
|---|---|---|---|---|---|
| ACIW | 7 | $54.69 | $52.425 | 2026-08-06 | 10 |
| XYZ | 5 | $79.03 | $81.28 | 2026-08-06 | 10 |
| MNST | 8 | $45.22 | $47.305 | 2026-08-07 | 9 |
| VTR | 4 | $88.1253 | $91.735 | 2026-08-11 | 7 |
| WMB | 5 | $73.2399 | $73.24 | 2026-08-19 | 0 (opened this run) |

**MNST** holds 8 shares @ $45.22 after the 2-for-1 split (cost basis unchanged $361.76; see corporate-action note above). **No exit this run:** none of the 5 positions hit the -8% stop, +6% take-profit, or the 12-day max hold (oldest ACIW/XYZ = 10 trading sessions, 2 short of 12): ACIW $52.425 (SL $50.31, TP $57.97), XYZ $81.28 (SL $72.71, TP $83.77 — ~$2.49 below TP), MNST $47.305 (SL $41.60, TP $47.93 — ~$0.63 below TP), VTR $91.735 (SL $81.08, TP $93.41 — ~$1.68 below TP), WMB $73.24 (SL $67.38, TP $77.63) all inside their bands. **NEW BUY: WMB 5 @ $73.2399 ($366.20).** New-buy path open (settled cash $488.18 > 20% of capital $401.41); regime gate PASSED (SPY $769.74 > 200d EMA $708.32); scanned 135 dips. The top of the leaderboard was again the **structural semiconductor/electronics selloff** — AXTI -8.5%, ACMR -7.4%, MXL -6.9%, MRCY -6.7%, AMKR -6.4%, plus INTC/STM/GFS/HPE/RKLB/CGNX/AVT/RAL — all Electronic-Technology names down ~40-50% from highs, skipped as falling knives / structural downtrend. Regional banks (CFG, ZION, USB, FITB, LNC) all sector-capped (Robinhood classifies them Finance, conflicting with VTR). Energy/pipelines split on the trend gate: **TRP $61.9 < EMA $62.33 and ENB $50.05 < EMA $52.26 both FAILED trend**; WMB, KGS both passed. Mechanical-gate survivors (earnings >14d, wash-sale, spread <1%, trend all PASS): **WMB, KGS, DPC, ARMK**. KGS skipped — real Q2 miss ($0.55 vs $0.75 est, -27%) on 08-06 with a recurring miss pattern, 22% off highs (fundamental deterioration). DPC skipped — brand-new listing (~2 months of history, 52w low set June 2026), obscure UK aerospace-castings spin, negative earnings, no recovery profile to assess. VIK dropped on the earnings gate (reported 08-19 am, beat but fell -3.6%, ambiguous). **WMB bought** as the biggest justified dip in a fundamentally-sound name in an intact uptrend (see the ledger row's dip-attribution summary). Wash-sale blocklist (EIX, PBF) — PBF not in today's candidates.

**Account total:** ~$2,006.94 vs $2,000.00 starting capital = **+0.35%** (SPY +3.78% same window, $741.69 → $769.74 live; relative **-3.43 pp**). Kill-switch threshold is $1,600 (-20%); not close. Post-buy cash: ~$121.98 (settled; WMB fill consumed $366.20).
