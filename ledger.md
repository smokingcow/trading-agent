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
| 2026-08-21 | ACIW | SELL | $52.0601 | 7 | Max-hold force-close (12 trading days; market order) | *(original thesis not recorded — backfilled buy row)* | **-$18.40 (-4.81%)** | -$38.00 | TIMEOUT | -0.44% | **-4.37 pp** |
| 2026-08-21 | XYZ | SELL | $82.0300 | 5 | Max-hold force-close (12 trading days; market order) | *(original thesis not recorded — backfilled buy row)* | **+$15.00 (+3.80%)** | -$23.00 | TIMEOUT | -0.44% | **+4.24 pp** |

---

**Corporate action (2026-08-11): MNST 2-for-1 stock split.** The broker position now shows **8 shares @ $45.22 avg cost** (was 4 @ $90.44); cost basis unchanged at $361.76. The `get_equity_orders` fill record still shows the pre-split buy (4 @ $90.44 on 2026-08-07) — that historical row is left as-is. Split-adjusted triggers for MNST: stop-loss $41.60, take-profit $47.93.

---

## Position and P&L summary as of 2026-08-21 (14:12 UTC run — Run 28)

**Realized:** 7 closed round-trips — 2 take-profit (YES), 2 stop-loss (NO), 3 timeout. Total realized P&L **-$23.00** (this run: ACIW -$18.40, XYZ +$15.00, net -$3.40). **Action this run:** two max-hold force-closes — ACIW and XYZ both hit 12 trading days (bought 2026-08-06) and were sold at market. Neither hit the -8% stop or +6% TP; the 12-session max-hold fired. No new buy (Step 5a — settled cash below the 20% threshold, same as recent runs; today's sale proceeds are unsettled T+1 and not spendable this run).

| Ticker | Entry | Exit | Held | Return | SPY same window | **Excess** | Exit trigger |
|---|---|---|---|---|---|---|---|
| NXT | $89.7632 | $96.1165 | 4 days | +7.08% | +3.25% | **+3.82 pp** | Take-profit |
| EIX | $75.6900 | $68.5601 | 5 days | -9.42% | +3.05% | **-12.47 pp** | Stop-loss |
| PBF | $67.5399 | $61.0501 | 3 days | -9.61% | +1.44% | **-11.05 pp** | Stop-loss |
| FTI | $69.5699 | $74.2301 | 5 trading days | +6.70% | +2.06% | **+4.64 pp** | Take-profit |
| BTSG | $60.7799 | $61.0501 | 12 trading days | +0.44% | +3.81% | **-3.37 pp** | Max-hold (timeout) |
| ACIW | $54.6889 | $52.0601 | 12 trading days | -4.81% | -0.44% | **-4.37 pp** | Max-hold (timeout) |
| XYZ | $79.0299 | $82.0300 | 12 trading days | +3.80% | -0.44% | **+4.24 pp** | Max-hold (timeout) |
| | | | | **-5.82%** | **+12.73%** | **-18.56 pp** | |

**Read the Excess column, not the Return column.** Every closed trade so far ran during a market rally, so raw returns flatter the strategy. Today's two timeouts illustrate both sides of the max-hold rule: ACIW drifted -4.81% (a -4.37pp relative loss), while XYZ booked a nominal +3.80% "win" — but SPY *fell* -0.44% over that identical 08-06→08-21 window, so XYZ's +4.24pp is the rare stretch where the loop actually beat the tape. Even so, across all seven closed trades the strategy has given up **18.6 percentage points** relative to simply holding SPY. Sample is 7 closed trades — still far too small to conclude anything about the strategy (92-737 closed trades needed, see `STRATEGY_RESEARCH_2.md` §1).

**Stop-loss slippage:** the two stop-outs (EIX -9.42%, PBF -9.61%) filled ~1.5-1.8% past their -8% trigger — the market-order gap cost behind the 2026-08-08 revisions (see `AGENT_PROMPT.md` judgment-call table #2/#3). Today's two max-hold market sells were non-stressed: ACIW filled $52.0601 vs a $52.04 bid, XYZ filled $82.0300 vs an $81.87 bid (slight price improvement) — no meaningful slippage.

**Portfolio vs benchmark since inception (2026-07-30 → 2026-08-21 14:12 UTC):** portfolio **+0.19%** (total capital $2,003.81 vs $2,000), SPY **+3.17%** ($741.69 → $765.20 live), relative **-2.98 pp**. Persistent beta drag: the book has trailed SPY's rally since inception, though the gap narrowed slightly this run as SPY pulled back from its mid-August highs. Underperformance tripwire not flagged (-2.98pp < -10pp threshold).

**Open positions:** 3, cost basis ~$1,096.34, plus $896.55 cash ($121.98 settled + $774.57 unsettled T+1 sale proceeds). *(Snapshot refreshed at the 2026-08-21 14:12 UTC run, market open.)*

| Ticker | Qty | Avg cost | Current | SL (×0.92) | TP (×1.06) | Held since | Days held (trading) |
|---|---|---|---|---|---|---|---|
| MNST | 8 | $45.22 | $47.57 | $41.60 | $47.93 | 2026-08-07 | 11 |
| VTR | 4 | $88.1253 | $92.64 | $81.08 | $93.41 | 2026-08-11 | 9 |
| WMB | 5 | $73.2399 | $71.23 | $67.38 | $77.63 | 2026-08-19 | 3 |

**MNST** holds 8 shares @ $45.22 after the 2-for-1 split (cost basis unchanged $361.76; see corporate-action note above). **Remaining 3 positions all held** — none hit the -8% stop, +6% TP, or 12-day max hold: MNST $47.57 (**$0.36 below its $47.93 TP** — nearest a target, 11 sessions), VTR $92.64 ($0.77 below its $93.41 TP, 9 sessions), WMB $71.23 (-2.7% below cost, 3 sessions). **No new buy:** Step 5a closed the new-buy path — settled cash $121.98 (unsettled_funds excludes today's $774.57 sale proceeds, which are T+1) < 20% of capital ($400.76). Steps 5b–8 (regime gate, scan) not reached. Circuit breaker not tripped (today's realized -$3.40 vs 6% threshold ≈ $120). Wash-sale blocklist now **EIX, PBF, ACIW** (ACIW sold at a -4.81% loss today — blocked for 30 days through ~2026-09-20). XYZ sold at a gain, so no wash-sale restriction.

**Account total:** $2,003.81 vs $2,000.00 starting capital = **+0.19%** (SPY +3.17% same window, $741.69 → $765.20 live; relative **-2.98 pp**). Kill-switch threshold is $1,600 (-20%); not close. Cash: $896.55 ($121.98 settled, $774.57 unsettled T+1).
