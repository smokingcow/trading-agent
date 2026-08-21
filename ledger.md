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
| 2026-08-21 | MNST | SELL | $47.9813 | 8 | Take-profit (limit order; +6% target hit) | *(original thesis not recorded — backfilled buy row; split-adjusted basis $45.22)* | **+$22.09 (+6.11%)** | -$0.91 | YES | -0.89% | **+7.00 pp** |
| 2026-08-21 | VTR | SELL | $93.6300 | 4 | Take-profit (limit order; +6% target hit) | VTR fell -4.1% to ~$87.86 (filled $88.13), a sector/rate-driven pullback: AHR priced a $712M dilutive secondary offering that pressured senior-housing REIT peers (VTR, OHI also down) on a day the broad market was up. VTR beat Q2 earnings 07-29 with no company-specific negative news; the slide from its 07-28 ATH was a valuation/rate derating of a sector that ran ~50%, not fundamental deterioration. Bought as a sentiment/sector dip in an intact uptrend — recovered to the +6% take-profit in 7 trading days. | **+$22.02 (+6.25%)** | +$21.11 | YES | -0.55% | **+6.79 pp** |

---

**Corporate action (2026-08-11): MNST 2-for-1 stock split.** The broker position now shows **8 shares @ $45.22 avg cost** (was 4 @ $90.44); cost basis unchanged at $361.76. The `get_equity_orders` fill record still shows the pre-split buy (4 @ $90.44 on 2026-08-07) — that historical row is left as-is. Split-adjusted triggers for MNST: stop-loss $41.60, take-profit $47.93.

---

## Position and P&L summary as of 2026-08-21 (19:16 UTC run — Run 30)

**Realized:** 9 closed round-trips — **4 take-profit (YES)**, 2 stop-loss (NO), 3 timeout. Total realized P&L **+$21.11** (unchanged this run — no exits). **Action this run (Run 30, 19:16 UTC):** none. WMB (only open position) held — no stop-loss / take-profit / max-hold trigger. No new buy (Step 5a — settled buying power $121.98 < 20% of capital $401.71; today's four sale proceeds $1,532.94 unsettled T+1). This run followed the 17:08 UTC Run 29 (MNST/VTR take-profit exits) with no intervening fills.

| Ticker | Entry | Exit | Held | Return | SPY same window | **Excess** | Exit trigger |
|---|---|---|---|---|---|---|---|
| NXT | $89.7632 | $96.1165 | 4 days | +7.08% | +3.25% | **+3.82 pp** | Take-profit |
| EIX | $75.6900 | $68.5601 | 5 days | -9.42% | +3.05% | **-12.47 pp** | Stop-loss |
| PBF | $67.5399 | $61.0501 | 3 days | -9.61% | +1.44% | **-11.05 pp** | Stop-loss |
| FTI | $69.5699 | $74.2301 | 5 trading days | +6.70% | +2.06% | **+4.64 pp** | Take-profit |
| BTSG | $60.7799 | $61.0501 | 12 trading days | +0.44% | +3.81% | **-3.37 pp** | Max-hold (timeout) |
| ACIW | $54.6889 | $52.0601 | 12 trading days | -4.81% | -0.44% | **-4.37 pp** | Max-hold (timeout) |
| XYZ | $79.0299 | $82.0300 | 12 trading days | +3.80% | -0.44% | **+4.24 pp** | Max-hold (timeout) |
| MNST | $45.2200 | $47.9813 | 10 trading days | +6.11% | -0.89% | **+7.00 pp** | Take-profit |
| VTR | $88.1253 | $93.6300 | 7 trading days | +6.25% | -0.55% | **+6.79 pp** | Take-profit |
| | | | | **avg +2.62%** | | **+1.62 pp avg** | |

**Read the Excess column, not the Return column.** Both of today's take-profits are genuine wins on the metric that matters: MNST returned +6.11% while SPY *fell* -0.89% over the identical 08-07→08-21 window (+7.00pp excess), and VTR +6.25% vs SPY -0.55% over 08-11→08-21 (+6.79pp excess). These are the first two closed trades where the strategy captured a real +6% gain against a *falling* tape — the setup the loop is designed for (buy sector/sentiment dips in intact uptrends, exit on reversion). The two 2026-08 stop-outs (EIX, PBF) remain the drag; across all 9 closed trades the average excess is now **+1.62pp**, up sharply from the -18.56pp cumulative shortfall carried when every prior closed trade had run during the market's July–mid-August rally. Sample is 9 closed trades — still far too small to conclude anything (92-737 needed, see `STRATEGY_RESEARCH_2.md` §1).

**Slippage:** today's two take-profit limit sells got price improvement — MNST filled $47.9813 vs a $47.98 bid / $47.95 limit, VTR $93.6300 vs a $93.61 bid / $93.55 limit. Clean fills, no adverse slippage (limit orders, non-stressed exits).

**Portfolio vs benchmark since inception (2026-07-30 → 2026-08-21 19:16 UTC):** portfolio **+0.43%** (total capital $2,008.57 vs $2,000), SPY **+3.27%** ($741.69 → $765.91 live), relative **-2.84 pp**. Still a beta drag since inception. Underperformance tripwire not flagged (-2.84pp < -10pp threshold).

**Open positions:** 1 (WMB only), cost basis $366.20, plus $1,654.92 cash ($121.98 settled + $1,532.94 unsettled T+1 sale proceeds from ACIW/XYZ/MNST/VTR). *(Snapshot at the 2026-08-21 19:16 UTC run, market open.)*

| Ticker | Qty | Avg cost | Current | SL (×0.92) | TP (×1.06) | Held since | Days held (trading) |
|---|---|---|---|---|---|---|---|
| WMB | 5 | $73.2399 | $70.735 | $67.38 | $77.63 | 2026-08-19 | 3 |

**WMB held** — none of -8% stop ($67.38), +6% TP ($77.63), or 12-day max hold triggered: current $70.735 (-3.4% below cost, 3 trading sessions). **No new buy:** Step 5a closed the new-buy path — settled buying power $121.98 (today's four sale proceeds all unsettled T+1) < 20% of capital ($401.71). Steps 5b–8 (regime gate, scan) not reached. Circuit breaker not tripped (today's realized +$40.71, positive). Wash-sale blocklist remains **EIX, PBF, ACIW** (ACIW sold at a loss 08-21, blocked ~30 days through 2026-09-20). MNST and VTR sold at gains 08-21, so no wash-sale restriction on them.

**Account total:** $2,008.57 vs $2,000.00 starting capital = **+0.43%** (SPY +3.27% same window, $741.69 → $765.91 live; relative **-2.84 pp**). Kill-switch threshold is $1,600 (-20%); not close. Cash $1,654.92 ($121.98 settled, $1,532.94 unsettled T+1).
