# Strategy Research — More Effective Stock/Options Selection

Date: 2026-08-08. This is a research note, not a strategy change — `PLAN.md` and `AGENT_PROMPT.md` remain the live source of truth until the user decides to act on something below and those files are edited explicitly.

## 0. Two things found while pulling data for this note, unrelated to "which stocks to pick," that matter more right now

**A. The ledger and run-log are silently broken.** `ledger.md` and `run-log.md` in this repo still have zero data rows — untouched since the initial commit on 2026-07-31. But the live Robinhood account shows **11 real fills** since then (7 buys, 3 sells, across BTSG, FTI, ACIW, XYZ, MNST, PBF, EIX, NXT), most recently a MNST buy on 2026-08-07. `AGENT_PROMPT.md` Step 9 requires every run — including "no action" runs — to append to both files and push. That step has not landed once in 8 days despite runs clearly executing trades. Either the git write/push is failing every single run (Step 9 says a failed push is "not fatal to the run," so it fails silently and nothing surfaces it) or the routines aren't reading Step 9 at all. **This means the audit trail the whole design depends on ("silence must never mean the loop didn't check") does not currently exist** — you've been flying on Robinhood's own order history only. Worth root-causing before anything else here, independent of strategy quality.

**B. Current real P&L, computed from live account data (not the ledger, since it's empty):**

| Symbol | Side | Entry | Exit | Return | Status |
|---|---|---|---|---|---|
| NXT | round-trip | $89.76 | $96.12 | **+7.1%** | Hit take-profit — win |
| EIX | round-trip | $75.69 | $68.56 | **-9.4%** | Hit stop-loss — loss |
| PBF | round-trip | $67.54 | $61.05 | **-9.6%** | Hit stop-loss — loss |
| BTSG, FTI, ACIW, XYZ, MNST | open | — | — | ~flat to +2.7% unrealized | still held |

Account value: **$1,952 vs. $2,000 starting capital (-2.4%)**. Not close to the -20% kill switch, but the realized trades so far are 1 win / 2 losses.

That 1-in-3 hit rate is too small a sample to judge the *stock-picking* itself, but it exposes a structural math problem worth fixing regardless of sample size: **take-profit is +6%, stop-loss is -8%.** For that asymmetry to break even before any costs, the strategy needs to win **more than 57% of the time** (8 / (6+8)). A dip-attribution filter based on "was the drop sentiment or fundamental" has to be a genuinely good classifier to clear that bar — it's not enough for it to be directionally reasonable. This is the single highest-leverage lever below, independent of anything about *which* stocks get scanned.

## 1. What the current strategy actually is, in factor terms

The dip-buy loop is a **short-horizon contrarian / mean-reversion** strategy: buy after a sharp drop, on the belief the drop was overreaction that will partially reverse. That's a real, studied phenomenon — but it's worth being precise about what the research says about it, because it cuts both for and against the current design.

### Short-term reversal — the closest academic match to what this loop does
Weekly and monthly return reversals are well documented (Jegadeesh 1990; Lehmann 1990 — a weekly contrarian strategy showing ~1.79%/week gross). The behavioral explanation is investor overreaction to news followed by partial correction — exactly the "sentiment-driven dip" thesis in `PLAN.md`. **But** the same literature is explicit that these profits are fragile: they concentrate in small, illiquid, high-spread names, and multiple follow-up studies conclude **transaction costs consume most or all of the apparent edge** once you account for realistic bid-ask spreads and slippage. That's directly relevant here — a live quote pull today showed **FTI's bid/ask was $62.79/$78.09 and XYZ's was $78.50/$94.95**, absurdly wide spreads for supposedly-liquid $5B+ names (likely a stale/thin quote snapshot, but it illustrates the point: liquidity in the $40-100/$5B-cap universe is not uniformly good, and the strategy has no explicit spread check before entering).
[Short-Term Reversal — Quantpedia](https://quantpedia.com/strategies/short-term-reversal-in-stocks) · [A Closer Look at the Short-Term Return Reversal](https://www.researchgate.net/publication/277677053_A_Closer_Look_at_the_Short-Term_Return_Reversal)

### Cross-sectional momentum — the opposite trade, also well-documented, worth knowing you're *not* doing
Jegadeesh & Titman (1993) and 30+ years of follow-up show stocks that have *outperformed* over the past 3-12 months continue to outperform over the next 3-12 months — average abnormal returns near 1%/month, ~12%/year excess, robust to risk/size/value controls. This is the **opposite** trade from dip-buying: momentum says buy strength, not weakness. It's mentioned here because "buy the dip" and "buy the winner" are both real, both published, and they contradict each other at different horizons — the literature's actual resolution is that reversal dominates at very short horizons (days to ~1 month) and momentum dominates at intermediate horizons (3-12 months), with reversal again at multi-year horizons. A loop holding "up to 12 trading days" sits right at the boundary where the reversal edge is weakest and least reliable.
[Momentum: what do we know 30 years after Jegadeesh & Titman](https://link.springer.com/article/10.1007/s11408-022-00417-8) · [Quantitative Momentum Research: Short-Term Return Reversal](https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/)

### The base rate for this whole category: active retail trading underperforms, and it's not close
Barber & Odean's "Trading Is Hazardous to Your Wealth" (66,465 discount-broker households, 1991-96): the highest-turnover quintile earned **11.4%/year net** vs. **18.5%/year** for the lowest-turnover quintile, on statistically similar *gross* stock picks — the entire gap is turnover and cost, not picking skill. Overconfidence, not lack of research, was the identified cause. This is the sobering prior to hold this whole project against: a 3x/day scan-and-trade loop is, structurally, a high-turnover strategy, and the historical base rate for that category is bad even when the picks themselves are fine.
[Trading Is Hazardous to Your Wealth (Barber & Odean, 2000)](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00226) · [The Behavior of Individual Investors](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/behavior%20of%20individual%20investors.pdf)

## 2. Tax implications (the part of the ask this note is meant to speak to directly)

- **Every trade this loop has made is short-term.** Max hold is 12 trading days; actual holds so far are 1-6 days. Short-term gains are taxed as **ordinary income** (10-37% federal, vs. 0/15/20% long-term). NXT's +7.1% win is worth meaningfully less after tax than a +7.1% gain held >1 year would be.
[2026 capital gains rates — Schwab](https://www.schwab.com/learn/story/how-are-capital-gains-taxed)
- **Wash-sale exposure exists and nothing in the loop checks for it.** PBF was sold at a loss (-9.6%) on 2026-08-06. If PBF (or anything the IRS would treat as "substantially identical") gets bought again within 30 days before or after that sale — entirely possible, since it's still inside the fixed $40-100/≥$5B/≥500K scan universe and could dip again — **that realized loss becomes disallowed and gets added to the new position's cost basis instead of offsetting other gains this year.** Same applies to EIX. This is a real, mechanical tax-drag risk the loop currently has no logic to detect, since it only looks at *current* positions/sector, not *recent closed losses per symbol*.
[Wash Sale Rule 2026 — FileTax](https://filetax.com/tax-situation/bought-or-sold-stocks/wash-sale-rule-stocks)
- **Net effect:** short-horizon trading can still be worth it net-of-tax if the edge is large enough, but the bar is higher than the headline % gains suggest — a strategy needs to clear ordinary-income tax rates *and* the 57%+ win-rate breakeven above *and* transaction costs to actually be worth the complexity, versus a buy-and-hold or low-turnover approach that gets preferential long-term rates almost for free after 12 months.

## 3. More effective alternatives, ranked by fit for a small ($2K), fully-autonomous, LLM-judged account

1. **Fix the risk/reward asymmetry before anything else.** Either raise take-profit to match or exceed the loss side, or tighten the stop-loss, so the required win rate is closer to 50% or below. This is a one-line change with more expected impact than any stock-picking improvement below.
2. **Add a wash-sale guard.** Before buying a symbol, check whether it (or the same symbol) was sold at a loss in the last 30 days; if so, skip it this run even if it otherwise qualifies. Cheap to add, directly protects realized losses from becoming useless.
3. **Add a spread/liquidity check at entry**, not just average-volume — reversal-strategy research is explicit that spread cost is what kills this category's paper returns. Skip anything with an abnormally wide bid-ask relative to price.
4. **Consider a longer-hold, factor-tilted "core" sleeve alongside (or instead of) the dip-buy loop** — quality/value/low-volatility or momentum-based selection, held for months not days. Lower turnover means lower transaction-cost drag, qualifies for long-term capital gains after a year, and rides factor premiums with far more academic support than day-scale dip attribution. This is the highest-expected-value change if the goal is genuinely "more effective," at the cost of no longer being a fast autonomous loop — it's a different product, not a tweak.
5. **Options as a defined-risk alternative to the current market-order stop-loss:**
   - **Cash-secured puts** on names from the existing scan universe are a structurally similar but more disciplined version of "buy the dip" — you get paid a premium to commit to a buy price below market, and either keep the premium or buy the stock at a price you already decided was fair, instead of chasing today's dip price live.
   - **Covered calls** on the existing long positions (BTSG, FTI, ACIW, XYZ, MNST) would generate income while waiting for the take-profit/stop-loss to resolve, and are a very common way small accounts add yield to a stock-picking strategy that isn't confident enough to be pure buy-and-hold.
   - Caveat: options income (premium collected) is generally still short-term-taxed, and assignment/covered-call mechanics have their own tax wrinkles (qualified vs. unqualified covered calls can suspend the holding-period clock on the underlying) — this needs its own read-through before implementing, not a one-line add.
   [Covered Call vs Cash-Secured Put — 2026 comparison](https://optionspilot.app/covered-call-vs-cash-secured-put)
6. **Momentum as an explicit second screen, not a replacement** — e.g., only take a reversal/dip trade if the stock's *longer-term* (3-12mo) trend is still intact (i.e., you're buying a dip within an uptrend, not a dip in a structural downtrend). `PLAN.md`'s own DOCU/TW/CVNA recovery-history analysis was already gesturing at this; formalizing it as a momentum filter would tie the existing historicals step to a documented factor instead of ad hoc "recovery profile" judgment.

## 4. What this note is *not* saying

None of the above is a claim that any of these approaches reliably beats the market after costs — published factor premiums decay once well-known, momentum has had violent multi-month crashes (2009 being the canonical example), and reversal profits are the ones most explicitly flagged in the literature as possibly cost-illusory. The realistic takeaway is narrower: **the current design has an identifiable, fixable math problem (TP/SL asymmetry) and two unmanaged tax risks (wash sales, ordinary-income treatment on 100% of trades) that are worth addressing regardless of which stock-picking philosophy you end up preferring**, and if the goal is genuinely "more effective" rather than "same idea, tuned," a lower-turnover factor-based sleeve has more academic backing than the current day-scale dip-attribution approach.

## Sources

- [Momentum: what do we know 30 years after Jegadeesh and Titman's seminal paper?](https://link.springer.com/article/10.1007/s11408-022-00417-8)
- [Quantitative Momentum Research: Short-Term Return Reversal — Alpha Architect](https://alphaarchitect.com/quantitative-momentum-research-short-term-return-reversal/)
- [Short-Term Reversal Effect in Stocks — Quantpedia](https://quantpedia.com/strategies/short-term-reversal-in-stocks)
- [A Closer Look at the Short-Term Return Reversal](https://www.researchgate.net/publication/277677053_A_Closer_Look_at_the_Short-Term_Return_Reversal)
- [Trading Is Hazardous to Your Wealth (Barber & Odean, 2000, Journal of Finance)](https://onlinelibrary.wiley.com/doi/abs/10.1111/0022-1082.00226)
- [The Behavior of Individual Investors — Barber & Odean](https://faculty.haas.berkeley.edu/odean/papers%20current%20versions/behavior%20of%20individual%20investors.pdf)
- [Capital Gains Tax Rates: Short-term vs. Long-term — Charles Schwab](https://www.schwab.com/learn/story/how-are-capital-gains-taxed)
- [Wash Sale Rule 2026: How to Avoid the 30-Day Trap — FileTax](https://filetax.com/tax-situation/bought-or-sold-stocks/wash-sale-rule-stocks)
- [Covered Call vs Cash-Secured Put: 2026 Comparison — OptionsPilot](https://optionspilot.app/covered-call-vs-cash-secured-put)
