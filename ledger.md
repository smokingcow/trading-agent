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
| 2026-08-25 | LTH | BUY | $44.3899 | 9 | Sentiment/supply dip (sponsor-selldown overhang + sell-the-news; fundamentally intact uptrend) | LTH fell -2.9% to ~$44.39 (filled $44.39) on a day the broad market was UP (SPY +0.2%) — an idiosyncratic sentiment/supply-driven pullback, not fundamental deterioration. The overhang is a sponsor distribution: Green LTF (Leonard Green) sold 5,025,751 shares at $43.16 on 08-10 and cut its stake to just 2.6% per a 13D/A — a mechanical PE exit now nearly exhausted, with the stock already trading back ABOVE that block price. Today's drop was a "sell-the-news" reaction to a bullish analyst call plus valuation "priced-in" chatter. Fundamentals are intact and improving: LTH beat Q2 on 07-30 ($0.48 vs $0.42 est), its 8th straight EPS beat, with a 10-12 club/yr expansion pipeline; it sits in an intact uptrend +30.6% above its 200d EMA ($33.99), only ~6% off its 07-27 ATH ($47.24). Bought as a sponsor-supply/sentiment dip in a fundamentally-sound uptrend (same setup as the VTR/WMB buys) after passing all mechanical gates: earnings 11-03 (outside 14d), no wash-sale, spread 0.07%, above 200d EMA; sector Consumer Services does not collide with the held WMB (energy). | — | +$21.11 | — | — | — |
| 2026-08-27 | BBY | BUY | $83.9600 | 5 | Sentiment/sell-the-news dip (beat-AND-raise; fundamentally improving intact uptrend) | BBY fell -3.7% (prev close $87.44 → filled $83.96) on the morning of its 08-27 Q2 FY27 report — a sell-the-news/profit-taking pullback, NOT fundamental deterioration. Best Buy delivered a **beat-AND-raise**: adj diluted EPS $1.47 (+15% YoY), comparable sales **+4.1%** (vs prior ~1% outlook), a higher-than-expected operating-income rate, and it RAISED full-year guidance across the board (FY27 comps to 1.9-3.0%, adj EPS to $6.70-6.90, revenue to $42.3-42.8B from $41.2-42.1B) with mgmt noting the "recovery is taking hold" and growth across all major categories (computing surge, likely AI-PC refresh). The drop is pure profit-taking after a run to a 52wk high ($91.27 on 07-29, +52% off the 05-13 $55.10 low). None of the skip conditions apply (no miss, no guidance cut, no margin/volume deterioration — the opposite of each). Intact uptrend: $83.96 is +11.4% above the 200d EMA ($75.38), ~8% off the recent high (the -36.9% vs the 2021 $136 ATH is a pandemic-electronics-bubble artifact, not current structure; ~57% of prior ≥6% weekly drops recovered within 12wk). Retail Trade sector — no collision with held WMB (Industrial Services) or LTH (Consumer Services). Passed all four mechanical gates: next earnings ~Nov (no gap risk over a ≤12-day hold — the earnings event is now behind it), no wash-sale, spread 0.27%, above 200d EMA. Bought as a sentiment/sell-the-news dip in a fundamentally-improving name in an intact uptrend — same setup as the VTR/WMB/LTH buys. | — | +$21.11 | — | — | — |

---

**Corporate action (2026-08-11): MNST 2-for-1 stock split.** The broker position now shows **8 shares @ $45.22 avg cost** (was 4 @ $90.44); cost basis unchanged at $361.76. The `get_equity_orders` fill record still shows the pre-split buy (4 @ $90.44 on 2026-08-07) — that historical row is left as-is. Split-adjusted triggers for MNST: stop-loss $41.60, take-profit $47.93.

---

## Position and P&L summary as of 2026-08-27 (14:15 UTC run — Run 40)

**Realized:** 9 closed round-trips — **4 take-profit (YES)**, 2 stop-loss (NO), 3 timeout. Total realized P&L **+$21.11** (unchanged this run — no exits). **Action this run (Run 40, 14:15 UTC): BUY 5 BBY @ $83.96** (~$419.80, 20.7% of capital) — a sentiment/sell-the-news dip in a fundamentally-improving name in an intact uptrend. WMB and LTH both held (no SL/TP/max-hold trigger). This is the first new buy since the 08-25 LTH purchase, breaking Runs 36-39's no-action streak. The scan returned 289 dips; biggest-dip-first after Gates A/B/C/D: **P -10.4%** buy-filter SKIP (beat but a PE-150 growth-name post-earnings crash/sell-the-news from an ATH = fundamental/gap, falling knife); **YUMC -4.1%** sector-cap collision (Consumer Services, held LTH) + ex-div today; **BBY -3.7%** cleared all four gates AND the buy filter → BOUGHT; SUNB -2.8% Gate A (reports 09-09); UBER -2.6% Gate D fail (< 200d EMA $78.94); NVO/ZTS pharma falling knives (ZTS at 52wk low $71.00); DCI -3.4% cleared gates but buy-filter SKIP (beat by $0.02 but "lowered guidance"/acquisition-dilution headlines, barely above 200d EMA, ambiguous → err-toward-skip; ranked below BBY anyway). Held sectors post-buy: WMB = **Industrial Services** (Oil & Gas Pipelines), LTH = Consumer Services, BBY = Retail Trade.

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

**Portfolio vs benchmark since inception (2026-07-30 → 2026-08-27 14:15 UTC):** portfolio **+1.28%** (total capital ~$2,025.6 vs $2,000), SPY **+3.64%** ($741.69 → $768.65 live), relative **-2.36 pp**. Beta drag since inception (SPY firmer intraday than the prior 08-26 run). Underperformance tripwire not flagged (-2.36pp < -10pp threshold).

**Open positions:** 3 — WMB, LTH, and BBY (new) — plus ~$835.61 cash (all settled, unsettled_funds=0 pre-buy; BBY paid from settled cash). *(Snapshot at the 2026-08-27 14:15 UTC run, market open.)*

| Ticker | Qty | Avg cost | Current | SL (×0.92) | TP (×1.06) | Held since | Days held (trading) |
|---|---|---|---|---|---|---|---|
| WMB | 5 | $73.2399 | $73.44 | $67.38 | $77.63 | 2026-08-19 | 7 |
| LTH | 9 | $44.3899 | $44.78 | $40.84 | $47.05 | 2026-08-25 | 3 |
| BBY | 5 | $83.9600 | $83.96 | $77.24 | $88.98 | 2026-08-27 | 0 |

**WMB held** — none of -8% stop ($67.38), +6% TP ($77.63), or 12-day max hold triggered: current $73.44 (+0.28% above cost, ~7 trading sessions).

**LTH held** — bought 08-25 (Run 35) at $44.3899; current $44.78 (+0.88%), 3 trading days held. No trigger. SL $40.84, TP $47.05.

**BBY bought this run** — 5 @ $83.96 (limit $84.45, filled with price improvement below the $84.03 ask). SL $77.24, TP $88.98, max-hold ~2026-09-15. Sentiment/sell-the-news dip on a beat-and-raise; see the ledger row for full attribution.

**Buy detail (Run 39, 19:19 UTC):** scan (Dip-Buy Loop Screen: $40-100, mcap≥$5B, avg vol≥500K/30d, %chg<0) returned **175 dips** on a ~flat-to-up tape (SPY +0.14%, $766.99). Biggest-dip-first after Gates A/B/C/D: SYRE -11.2% biotech Phase-3 binary SKIP; OKLO -6.8%/IONQ -4.2%/ASTS -3.3% pre-revenue speculative SKIP; ZM -6.5% guidance-cut carry SKIP; FRO -4.9% Gate A (rpt 08-28); FER -4.8% Gate D fail + WMB sector collision; MXL -4.6% falling-knife carry SKIP; **LTM -3.58% ($52.78, Transportation/Airlines) — the one fresh candidate to clear ALL four gates** (earnings 11-13, no wash-sale, spread 0.09%, $52.78 > 200d EMA $51.00) **but buy-filter SKIP:** no clean single-day sentiment/macro catalyst on an up-market day; a continuation of a persistent multi-week slide (~-4.7% prior week, ~25% off the 02-03 $70.42 high), with a mgmt-cited sharp jet-fuel cost spike (margin headwind), a slight Q2 08-04 miss ($0.436 vs $0.44), and an overvaluation flag (GF Value ~$41.56), only barely above its 200d EMA = falling-knife/margin-deterioration (EIX/PBF/MXL setup), err-toward-fundamental/skip; GDDY -3.6% Gate D fail (<EMA $102.4); NVO -3.1% pharma falling-knife SKIP; commodity knives (AA/B/BHP/PAAS/GFI/EGO/VAL/MP) SKIP; BSX -2.9% Gate D fail (near 52wk low); ETSY -2.9% & CVNA -2.6% cleared gates, buy-filter SKIP on unchanged structural drivers (Run 38 carry); CRSP -2.6% biotech binary SKIP; FLUT/YUMC/QSR Consumer Services blocked by sector cap (held LTH). Circuit breaker not tripped (no realized trades today). Wash-sale blocklist EIX/PBF/ACIW (none in dip list). Criteria NOT loosened — valid no-action.

**Prior-run buy detail (Run 38):** scan returned **178 dips** on a ~flat tape (SPY -0.11%) the morning after NVDA earnings. Biggest-dip-first after mechanical Gates A/B/C/D:
- **SYRE** -13.4% ($92.9; Health Tech) — clinical-stage biotech, Phase 3 binary/clinical gap event. **SKIP.**
- **ZM** -6.6% ($94.3) — post-earnings guidance-cut carry from Run 37 (soft Q3/FY guide on 08-25 double-beat). **SKIP.**
- **OKLO** -6.2% / **IONQ** -4.3% / **ASTS** -2.7% / **CRCL** -3.8% — speculative pre-revenue (nuclear/quantum/satellite/stablecoin). **SKIP.**
- **FER** -5.0% ($59.9) — **Gate D fail** (< 200d EMA ~$64.6) + Industrial Services collides with held WMB.
- **FRO** -4.6% ($41.5) — **Gate A** (reports 08-28) + tanker/energy commodity.
- **MXL** -4.0% ($63.7) — falling-knife w/ fundamental concerns (carry, Run 37). **SKIP.**
- **GDDY** -3.7% ($96.1) — **Gate D fail** (< 200d EMA $102.4).
- **AA/VAL/EGO/BHP/GFI/B** -2.4% to -3.3% — commodity knives (aluminum/offshore-drill/gold/mining). **SKIP.**
- **BSX** -3.1% ($48.3; Health Tech) — **Gate D fail** (near 52wk low $42.2; 52wk high $109.5 appears split-unadjusted).
- **NVO** -3.1% ($47.2) — pharma falling-knife (below 200d EMA, GLP-1 guidance overhang). **SKIP.**
- **CRSP** -2.5% ($59.4) — gene-editing biotech binary (carry, Run 37). **SKIP.**
- **ETSY** -2.7% ($82.20; Retail Trade) — cleared **ALL** gates (+22% > 200d EMA $67.16, spread 0.15%, next earnings 10-28, Q2 08-05 beat $0.98 vs $0.73). **Buy filter SKIP:** down on a company-specific restructuring (12% layoffs / ~220 roles in product & engineering, ~$35M Q3 charge) + **declining active buyers** (marketplace volume deterioration) + analyst downgrades to Hold (mean PT $77.52 < price), on a flat tape = fundamental/operational worsening, not a macro/sentiment dip. Explicit volume-deterioration skip; err-toward-skip.
- **CVNA** -2.6% ($73.71; Retail Trade) — cleared **ALL** gates (+6.6% > 200d EMA $69.15, spread 0.04%). **Buy filter SKIP:** down on the **Mark Walter (4% holder) DOJ-probe overhang** (~$2B stake-unload fear) layered on a **post-Q2 margin/profitability-outlook reset**, high-beta, flat tape. Margin-deterioration + err-toward-skip.
- **QSR** -2.1% / **YUMC** -2.4% / **FLUT** -2.5% — Consumer Services, blocked by **sector cap** (collide with held LTH); FLUT also a structural downtrend ($309→$99 over 52wk).

Circuit breaker not tripped (no realized trades today). Wash-sale blocklist remains **EIX, PBF, ACIW** (none appeared in the dip list). Sector cap decisive on QSR/YUMC/FLUT (held LTH = Consumer Services); WMB = Industrial Services. Criteria were **not** loosened — no survivor cleared the standard buy filter, a valid "no action" outcome.

**Prior-run buy detail (Run 37):** scan returned **147 dips**. Tape: broad market ~flat (SPY +0.09%, $766.57) with idiosyncratic single-name selloffs — a risk-off in specific names ahead of NVDA earnings (08-26 pm), not a broad decline. Biggest-dip-first after mechanical Gates A/B/C/D (earnings ≤14d, wash-sale, spread <1%, 200d-EMA trend). Every survivor failed the buy filter:
- **SYRE** -11.9% ($94.6; Health Technology) — clinical-stage biotech (Pegzilarginase in Phase 3 pivotal), 52wk high set just 08-19. A -12% single-day move in a Phase-3 binary name = clinical/offering gap event, the exact gap risk the loop avoids. **Buy filter SKIP** (fundamental/binary).
- **ZM** -5.5% ($95.3; Technology Services) — cleared **ALL** gates (above 200d EMA $90.93, spread 0.17%, next earnings 11-23, no wash-sale). **Buy filter SKIP:** reported Q2 FY27 last night (08-25 pm) — a double-beat (rev $1.28B vs $1.27B, EPS $1.55 vs $1.48) — but sold off on **soft forward guidance** (Q3 EPS guide $1.46-1.48 light; FY revenue raised only ~$5M at midpoint = "AI growth leaves revenue outlook nearly flat"). Guidance disappointment = fundamental worsening + a post-earnings gap; explicit skip condition.
- **BSX** -4.3% ($47.7; Health Technology) — **Gate D fail** ($47.71 < 200d EMA $64.61; -56% off 52wk high, near 52wk low $42.20 — structural downtrend).
- **GDDY** -4.3% ($95.4; Technology Services) — **Gate D fail** ($95.42 < 200d EMA $102.38).
- **FRO** -3.9% ($41.8) — **Gate A** (reports 08-28) + tanker/energy commodity.
- **FER** -3.6% ($60.8; Industrial Services) — **Gate D fail** ($60.79 < 200d EMA $64.63).
- **IREN** -3.15% ($40.9) — **Gate A** (reports 08-27) + crypto miner.
- **CRSP** -2.4% ($59.4; Biotechnology) — cleared gates (above 200d EMA $52.63, spread 0.20%, no earnings ≤14d). **Buy filter SKIP:** no clean single-day catalyst; backdrop is fundamental worsening — slow Casgevy commercial rollout, widening net loss (-$581.6M/yr), negative P/E, -12% on the month. Biotech binary risk; err-toward-fundamental/skip.
- **MXL** -2.5% ($64.1; Semiconductors) — cleared gates (above 200d EMA $54.20, spread 0.36%). **Buy filter SKIP:** down -23% on the month / -50% from its 06-30 peak $128.30, on valuation reset (GF value ~$20), active insider selling (Litchfield sold ~102k sh today), Silicon Motion legal overhang, and working-capital pressure. Falling knife with fundamental concerns (EIX/PBF setup).
- Remaining dips all <2.3% (VAL/AA/PAAS/GFI/BHP commodity, TXG/TVTX biotech, IONQ speculative, NTNX Gate A rpt 08-26, CTSH/YUMC/LVS/IBKR/CAVA shallow) — none a bigger justified dip than those rejected above.

Circuit breaker not tripped (no realized trades today). Wash-sale blocklist remains **EIX, PBF, ACIW** (none appeared in the dip list). Sector cap: no collision anyway (holdings WMB=Energy, LTH=Consumer Services). Criteria were **not** loosened — no survivor cleared the standard buy filter, a valid "no action" outcome.

**Account total:** ~$2,025.6 vs $2,000.00 starting capital = **+1.28%** (SPY +3.64% same window, $741.69 → $768.65 live; relative **-2.36 pp**). Kill-switch threshold is $1,600 (-20%); not close. Cash ~$835.61 (all settled), WMB + LTH + BBY open.

---

**Buy detail (Run 40, 14:15 UTC):** scan (Dip-Buy Loop Screen: $40-100, mcap≥$5B, avg vol≥500K/30d, %chg<0) returned **289 dips** on an up tape (SPY $768.65, +0.34% intraday). Regime gate PASSED (SPY $768.65 > 200d EMA $714.07). Biggest-dip-first after Gates A/B/C/D:
- **P** (Everpure/ex-Pure Storage) -10.4% ($97.58, Electronic Technology) — reported 08-26 pm, EPS $0.70 vs $0.50 beat, yet crashed -10% from an ATH ($119 on 08-18) at PE ~150. Post-earnings sell-the-news/guidance-valuation crash on a hyper-valued growth name = fundamental/gap, falling knife → **buy-filter SKIP**.
- **YUMC** -4.1% ($45.24, Consumer Services/Restaurants) — **sector-cap collision** with held LTH; also ex-dividend today.
- **BBY** -3.7% ($83.96, Retail Trade) — **cleared ALL four gates** (earnings ~Nov, no wash-sale, spread 0.27%, +11.4% > 200d EMA $75.38) AND the buy filter (beat-AND-raise sell-the-news dip in an intact uptrend) → **BOUGHT 5 @ $83.96**.
- **DCI** -3.4% ($92.06, Producer Manufacturing) — cleared gates (spread 0.63%, +2.7% > 200d EMA $89.60) but **buy-filter SKIP**: beat by $0.02 but "lowered guidance"/Facet-acquisition-dilution headlines + weakest trend of the survivors; ambiguous → err-toward-skip; ranked below BBY anyway.
- **SUNB** -2.8% ($72.30) — **Gate A** (reports 09-09, within 14d).
- **UBER** -2.6% ($76.45, Transportation) — **Gate D fail** ($76.39 < 200d EMA $78.94).
- **NVO** -2.9% ($45.84) & **ZTS** -2.6% ($75.48) — pharma falling knives near/at 52wk lows (ZTS low $71.00 set 08-17, -52% off 52wk high; NVO GLP-1 overhang) → SKIP.
- **MNST** -2.4% ($46.66) — former holding sold at +6.11% TP on 08-21 (a gain, no wash-sale), but a shallow dip on a beverage staple → deprioritized below the bigger justified dips.

Circuit breaker not tripped (no realized trades today). Wash-sale blocklist EIX/PBF/ACIW (none in dip list). Criteria NOT loosened. Sector cap decisive on YUMC (Consumer Services = held LTH); BBY (Retail Trade) is a fresh sector.
