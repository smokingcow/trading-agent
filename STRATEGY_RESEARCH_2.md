# Strategy Research, Part 2 — Deeper Options

Date: 2026-08-08. Follow-up to `STRATEGY_RESEARCH.md`. Research note only — `PLAN.md` and `AGENT_PROMPT.md` remain the live source of truth; nothing here is implemented.

---

## 0. Correction to Part 1: options are not viable at this account size. I got this wrong.

Part 1 recommended cash-secured puts and covered calls. Having now checked the actual constraints, **both are impossible on this account**, for two independent reasons:

1. **No options approval on the agentic account.** `get_accounts` shows the cash/"Agentic" account (`506274612`) has `option_level: ""` — no options access at all. The account that *does* have `option_level_2` (`597998368`) has `agentic_allowed: false`, so the loop cannot touch it. An upgrade URL exists (`applink.robinhood.com/upgrade_options?account_number=506274612`), so this is fixable, but it isn't a code change — it's a broker application.
2. **Even with approval, the capital math doesn't work.** One contract = 100 shares. A cash-secured put on a $60 stock requires **$6,000** of collateral. A covered call requires owning **100 shares** — $4,000-$10,000 in the current $40-100 scan universe. The account has **$1,952 total** and holds 4-7 shares per position. The wheel strategy on this universe needs roughly **$15-25K minimum**; at $2K it is arithmetically unavailable.

Also worth noting for any future options plan: the MCP tool description states **multi-leg orders are not supported**, so credit spreads / defined-risk structures are off the table via this integration regardless of approval level.

The only options trade available at $2K would be *buying* long calls/puts — which means paying the volatility risk premium rather than collecting it, i.e. taking the historically losing side of the trade described in §3. Not recommended.

**Conclusion: this is an equities-only strategy for the foreseeable future.** Treat options as a "revisit at $20K+" item, not a near-term lever.

---

## 1. The measurement problem, which outranks every strategy idea below

Two numbers from your own fill history:

**Your stops are slipping ~1.5-1.75% past their trigger.**

| Trade | Entry | -8% stop trigger | Actual fill | Slippage past trigger |
|---|---|---|---|---|
| EIX | $75.69 | $69.63 | $68.56 | **-1.5%** |
| PBF | $67.54 | $62.14 | $61.05 | **-1.8%** |

That's the cost of exiting on market orders (a locked decision in `PLAN.md`, and defensible on its own terms) — but it means **the effective stop-loss is about -9.5%, not -8%.** Combined with the +6% take-profit, the real breakeven win rate isn't 57.1%, it's closer to **58-61%**.

**How many trades before you could tell whether you're clearing that bar?** Standard one-sided proportion test, 95% confidence, 80% power, against a 57.5% breakeven:

| If the true win rate is… | Trades needed | At ~150 round-trips/yr |
|---|---|---|
| 70% (a genuinely strong edge) | ~92 | **~7 months** |
| 65% (a good edge) | ~262 | **~1.7 years** |
| 62% (a slim but real edge) | ~737 | **~5 years** |

You currently have **3 closed trades**. The practitioner rule of thumb is 100 trades for basic significance, 200-500 for confidence — and "20 trades is not a backtest, it's noise."
[Overfitting in Backtests — Alpha Suite](https://alpha-suite.org/blog/overfitting-backtesting) · [Statistical Overfitting and Backtest Performance — Bailey et al.](https://sdm.lbl.gov/oapapers/ssrn-id2507040-bailey.pdf)

**This is the deepest finding in this note.** You cannot evaluate this strategy — or any replacement for it — from live P&L on any reasonable timeline. Swapping in a better-sounding strategy without a way to measure it just changes which unfalsifiable narrative you're running. **The highest-value thing to build is not a new strategy, it's a validation harness**: a backtester over historical bars (`get_equity_historicals` already provides them), plus a labeled decision log that records every dip-attribution classification and later scores it against the outcome. That converts the loop from a story into a dataset. Right now the ledger is empty, so even the 3 trades you have aren't generating learnable signal.

---

## 2. You are using 3 of ~55 available screening dimensions

`get_scanner_filter_specs` returns **55 filters**. The strategy uses **three**: price, market cap, average volume — plus `% change from close` for the dip itself. The unused ones map almost one-to-one onto the documented factor literature:

| Available but unused | What it enables |
|---|---|
| `FILTER_TYPE_EMA` (lengths incl. **200**) | Trend/regime filter — buy dips *in uptrends* only |
| `FILTER_TYPE_RSI` (lengths incl. **2**) | Connors-style extreme oversold — a real reversal signal, not "% down today" |
| `FILTER_TYPE_HIGH` (lengths incl. **52**) | Distance from 52-week high — the George & Hwang momentum measure |
| `FILTER_TYPE_EARNINGS_DATE` | Mechanically exclude names reporting soon (gap risk) |
| `ROE`, `ROA`, `gross/operating/net margin`, `PEG`, `forward P/E` | Quality + value gates, computed instead of LLM-judged |
| `FILTER_TYPE_RELATIVE_VOLUME` | Separates real-news dips from noise |
| `FILTER_TYPE_ATR` | Volatility-normalized stops and sizing |
| `IMPLIED_VOLATILITY` / `HISTORICAL_VOLATILITY` | IV/HV ratio (relevant only if options ever become viable) |

The single highest-value addition here is the **earnings-date exclusion**. A market stop-loss provides *no protection against overnight gaps* — and your two stop-outs already show slippage. Excluding names with earnings inside the holding window removes the fattest tail in the distribution for near-zero effort.

The second highest is the **200-day EMA trend filter**. `PLAN.md`'s own DOCU-vs-TW recovery analysis was informally reaching for exactly this: DOCU was a "dip" that was really a structural downtrend. A 200-EMA gate encodes that mechanically instead of asking the model to re-derive it from weekly bars every run. Faber (2006) and Siegel (2002) both show 10-month/200-day trend rules substantially reduce drawdowns, at the cost of slight lag.
[A Quantitative Approach to Tactical Asset Allocation — Faber](https://www.trendfollowing.com/whitepaper/CMT-Simple.pdf) · [Asset Class Trend-Following — Quantpedia](https://quantpedia.com/strategies/asset-class-trend-following)

---

## 3. Strategy families with more evidence behind them than day-scale dip attribution

Ranked by evidence strength × implementability on this stack.

### 3.1 Post-Earnings Announcement Drift (PEAD) — strongest candidate
Stocks with positive earnings surprises drift **upward for 60-90 days**; negative surprises drift down. It is one of the most replicated findings in empirical finance, survived decades of publication and arbitrage, and McLean & Pontiff found earnings-based anomalies decayed *less* post-publication than most others. Original hedge-portfolio returns ~25%/yr, decayed but still significant — strongest in smaller, less-followed names, which is exactly the $5B-cap universe already being scanned.

**Why it's a strong fit:** it's a *directional bet on an event*, not a judgment call about narrative. `get_earnings_results` and `get_earnings_calendar` already provide the surprise data. And it inverts the current design in a useful way — the loop currently *skips* anything with an earnings event, discarding the highest-signal moment in a stock's calendar.

**Cost:** a 60-90 day holding period is a different product from a 12-day loop — fewer trades, less turnover (good for costs and taxes: 90 days is still short-term, but 4x less turnover), and much slower feedback.
[PEAD: The Anomaly That Refuses to Die](https://alpha-suite.org/blog/post-earnings-announcement-drift) · [Post-Earnings Announcement Effect — Quantpedia](https://quantpedia.com/strategies/post-earnings-announcement-effect)

### 3.2 52-week-high momentum (George & Hwang, 2004)
Rank by *current price ÷ 52-week high*; stocks near their highs outperform those far from them. Nearness to the 52-week high **dominates and improves on past-return momentum** as a predictor, works in 18 of 20 international markets, and — unusually — the returns **do not reverse long-term**, unlike standard momentum. Directly screenable via `FILTER_TYPE_HIGH` at length 52.

This is the cleanest *opposite* of the current strategy: it says buy what's near its high, not what just dropped.
[The 52-Week High and Momentum Investing — George & Hwang, Journal of Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2004.00695.x) · [International evidence](https://www.sciencedirect.com/science/article/abs/pii/S0261560610001099)

### 3.3 Quality / gross profitability (Novy-Marx, 2013)
Gross profits-to-assets predicts cross-sectional returns with **roughly the same power as book-to-market**, and controlling for profitability dramatically improves value strategies — especially among large, liquid names. Fama & French folded it into their 2014 five-factor model. Screenable today via ROA/ROE/gross margin/operating margin filters.

Best used as a **gate, not a signal**: require minimum profitability before any dip qualifies. This mechanizes the "is this business structurally deteriorating?" question that Step 7 currently asks the LLM to answer from news text under time pressure.
[The Other Side of Value: The Gross Profitability Premium](https://www.sciencedirect.com/science/article/abs/pii/S0304405X13000044) · [Profitability factor: international evidence — Alpha Architect](https://alphaarchitect.com/the-profitability-factor-international-evidence/)

### 3.4 Volatility risk premium — real, but locked behind §0
IV exceeds subsequent realized vol in **~85% of observations since 1990**, averaging 2-4 percentage points, paying out in 83-87% of rolling 30-day windows. It is one of the most persistent premia documented. It is also the reason selling options beats buying them on average — and why the only options trade available at $2K (buying premium) is the wrong side.

Filed here for completeness and for the $20K+ revisit. **Not actionable now.** Note the standard warning: it "has made selling insurance one of the most profitable and most catastrophic strategies in modern markets" — the losses arrive correlated with everything else going wrong.
[What Is the Volatility Risk Premium? — CAIA](https://caia.org/blog/2024/02/01/what-volatility-risk-premium)

### 3.5 Keep short-term reversal, but tighten the trigger
Not abandoning the current thesis — the reversal effect is real (Jegadeesh 1990, Lehmann 1990). But "% change from close" is a crude trigger. RSI(2) below ~10, combined with price above the 200-day EMA, is the well-known formalization: *extreme short-term oversold within an intact uptrend*. Both are already screenable. This is the smallest-diff, highest-fidelity upgrade to what's running today.

---

## 4. Risk architecture — probably worth more than the signal change

- **ATR-normalized stops instead of fixed -8%.** A flat percentage stop means a low-vol utility (EIX) and a high-vol small-cap carry completely different real risk. `FILTER_TYPE_ATR` and the ATR indicator are both available. Stops at ~2× ATR normalize risk per trade so the win-rate math is stable across names.
- **Volatility-scaled position sizing** rather than flat 20%. Same reasoning.
- **You are 100% deployed with a $29 cash buffer.** Five positions × 20% = the entire account, all small/mid-cap equities, no hedge. Portfolio-level beta almost certainly dominates the stock-specific dip alpha — meaning most of your P&L variance is just "did small caps go up this week," not "was the dip attribution correct." The strategy has no market-regime awareness at all.
- **Market-regime gate.** Mean-reversion buying performs worst in downtrends, which is precisely when dips keep dipping. A simple SPY-above-200-day check before enabling new buys is one call.
- **Wash-sale guard** (carried over from Part 1, still unaddressed) — EIX and PBF are both realized losses within the last 30 days and both remain inside the scan universe.

---

## 5. The honest framing

At $2,000, with ~150 round-trips/year, ordinary-income tax on 100% of gains, ~1.5% stop slippage, and a required win rate near 60%, **the expected value of this as a money-making venture is likely negative** — that's the Barber & Odean result from Part 1 restated with your actual numbers, and the top-quintile-turnover households in that study underperformed by 7 percentage points a year on statistically identical gross picks.

That is not an argument to stop. It's an argument about **what to optimize for**. If the goal is returns, the answer is boring and doesn't need an agent. If the goal is a working autonomous system — which is what's actually been built here, and it does work — then the right objective is **learnability, not cleverness**: build the measurement layer first, then swap strategies against it and let the data pick. Otherwise you're choosing between §3.1 and §3.2 on the strength of how persuasive I was, which is exactly the failure mode the whole factor literature exists to prevent.

**Suggested order of work:**
1. Fix the ledger/run-log write bug (already agreed) — no measurement is possible without it.
2. Add the earnings-date exclusion and wash-sale guard — small, purely protective, no thesis change.
3. Fix the payoff asymmetry (raise TP, tighten SL, or move to ATR-based) so breakeven sits at or below 50%.
4. Build the backtest harness over `get_equity_historicals`.
5. *Then* evaluate PEAD / 52-week-high / quality-gated reversal against it, and let the backtest decide.

---

## Sources

- [PEAD: The Anomaly That Refuses to Die — Alpha Suite](https://alpha-suite.org/blog/post-earnings-announcement-drift)
- [Post-Earnings Announcement Effect — Quantpedia](https://quantpedia.com/strategies/post-earnings-announcement-effect)
- [The 52-Week High and Momentum Investing — George & Hwang (2004), Journal of Finance](https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.2004.00695.x)
- [The 52-week high momentum strategy in international stock markets](https://www.sciencedirect.com/science/article/abs/pii/S0261560610001099)
- [The Other Side of Value: The Gross Profitability Premium — Novy-Marx (2013)](https://www.sciencedirect.com/science/article/abs/pii/S0304405X13000044)
- [The Profitability Factor: International Evidence — Alpha Architect](https://alphaarchitect.com/the-profitability-factor-international-evidence/)
- [What Is the Volatility Risk Premium? — CAIA](https://caia.org/blog/2024/02/01/what-volatility-risk-premium)
- [A Quantitative Approach to Tactical Asset Allocation — Faber](https://www.trendfollowing.com/whitepaper/CMT-Simple.pdf)
- [Asset Class Trend-Following — Quantpedia](https://quantpedia.com/strategies/asset-class-trend-following)
- [Statistical Overfitting and Backtest Performance — Bailey, Borwein, López de Prado, Zhu](https://sdm.lbl.gov/oapapers/ssrn-id2507040-bailey.pdf)
- [Overfitting in Backtests: Why Most Strategies Fail Live — Alpha Suite](https://alpha-suite.org/blog/overfitting-backtesting)
