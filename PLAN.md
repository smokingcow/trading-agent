# Trading Agent — Dip-Buy Loop

Status: **spec agreed, scheduling in progress, blocked on Robinhood MCP setup**. This file is the source of truth for the strategy design. Build against this — don't re-derive it from scratch in a new session.

## Goal

Agentic loop, run 2-3x/day during trading hours via Robinhood MCP. Find stock dips, research whether the dip is company-specific (fundamental) or sentiment/macro-driven, buy the sentiment-driven ones, sell on a fixed profit target or stop-loss. Track everything in a markdown ledger.

Capital: $2,000-$5,000. Fully at-risk — treat as money you're OK losing entirely, not money you need back.

## Why this shape (context from design session)

- Screener + fundamentals + earnings-history + WebSearch news pulls were prototyped live in a prior conversation against MO, RLI, CVNA, TW, DOCU, CHDN (all real July 2026 dips). That workflow (Robinhood scanner → fundamentals → earnings check → news search → historical weekly-bar recovery analysis) is the template for the "research" step below.
- Historical recovery-rate analysis (weekly bars, ≥6% drops, going back to 2016 or IPO) showed wildly different profiles per stock — e.g. DOCU had 15 stacked unrecovered drops and was down 84% from ATH (structural decline, not a dip); TW recovered fast and reliably (median 7.5wk, only 1 unrecovered); CVNA is high-beta with a near-bankruptcy period where recoveries took 100-180 weeks. **Conclusion: "% change from close" alone is not enough signal — always check recovery history and whether the drop is company-fundamental vs sentiment/macro before buying.**
- Real example from that session: MO dropped -8.8% on an actual earnings miss + narrowed guidance (skip, per buy filter below). RLI dropped -6.7% on an analyst downgrade alone, no news, after a beat-and-raise quarter (buy candidate, per buy filter below). CHDN beat estimates but dropped -9.1% on sector-wide gaming softness + a structural regional-casino overhang (borderline — mixed signal, judgment call under the filter).

## Locked decisions

| Area | Decision |
|---|---|
| Trial mode | Live money, day one. No paper-trade period. |
| Position size | Max 20-25% of total capital per position (~$400-1,250 on $2-5K) |
| Take-profit | Fixed +5-8% gain from buy price → sell |
| Stop-loss | Fixed -7% to -10% loss from buy price → sell, no exceptions, no judgment override |
| Daily circuit breaker | If cumulative daily loss hits 5-8% of total capital, halt new buys for rest of day |
| Overall kill switch | Auto-pause entire loop at -20% total drawdown from starting capital; loop writes its own pause flag and notifies |
| Buy filter | Only buy dips that are sentiment/macro-driven (analyst downgrade, sector selloff, index/rebalance noise) or in-line-results-but-oversold reactions. **Skip** any dip involving a real earnings miss, guidance cut, margin/volume deterioration, or other fundamental worsening — even if the reaction looks oversized. The loop is not equipped to underwrite "how much is this guidance cut really worth" in a 2-3x/day cycle. |
| Scan universe | Fixed every run: price $40-100/share, market cap ≥$5B, average volume ≥500K/day (liquidity floor so exits are always achievable). Do not widen criteria on a run that returns few/no candidates. |
| Candidate ranking | When multiple candidates qualify: rank by biggest justified dip first, max 1 position per sector at a time (no correlated-bet stacking) |
| Max hold period | Force-close at market if neither take-profit nor stop-loss has hit within 10-15 trading days |
| Autonomy | Fully autonomous — no per-trade confirmation required from the user |
| Account type | Cash account. No PDT (Pattern Day Trader) restriction, but T+1 settlement — must check *settled* cash before placing a new buy, not just account balance. A same-day take-profit sell doesn't free up buying power until next business day. |
| Kill switch mechanism | Pause-flag file, checked at the very start of every run. If present: log "paused", do nothing else, exit. User creates/deletes the file to stop/resume. |
| Notifications | Push notification after every single run, including "no action taken" runs. Silence must never mean "didn't check" — a missed run is worse than a noisy one with real money involved. |
| Source of truth | Robinhood live account state (positions + orders) is authoritative. Every run starts by reconciling the ledger against actual account state, not the other way around — prevents double-buys or phantom positions if a prior run crashed mid-write. |
| Order types | Stop-loss exits: market order (certainty of exit > price precision). Entries and take-profit exits: limit order near current price (avoid slippage; these are liquid enough names). |

## Models

| Phase | Model | Why |
|---|---|---|
| Build (writing the agent/skill code) | `claude-sonnet-5` (this Claude Code session) | Well-specified engineering task, not a judgment task. No reason to pay Opus rates to write code. |
| Runtime (each loop iteration — screener → research → buy/sell decision → order) | `claude-opus-4-8` | Real money, full autonomy, no human check (per Locked decisions). The buy filter (fundamental miss vs sentiment dip) is a judgment call, not extraction — worth the stronger model. Loop volume is low (2-3x/day, ~5-10 calls per run), so the Opus vs Sonnet cost delta ($5/$25 vs $3/$15 per MTok) is trivial next to the cost of one misclassified trade. |

Runtime request shape:

```python
client.messages.create(
    model="claude-opus-4-8",
    max_tokens=8000,
    thinking={"type": "adaptive"},
    output_config={"effort": "high"},  # bump to "xhigh" if borderline dip-attribution calls look under-thought
    tools=[...],  # robinhood MCP tools
    messages=[...],
)
```

Not `claude-fable-5` — that tier is for multi-hour open-ended agentic work; this loop is bounded and well-specified, Opus 4.8 has no capability gap here at half the price. Not Sonnet or Haiku for runtime — cutting model tier on top of full autonomy + live capital stacks risk for no real savings given the low call volume.

## Biggest residual risk (stated explicitly, not hidden)

Live capital + full autonomy + zero trial period is the single riskiest combination on the board. The only nets are the daily circuit breaker and the -20% overall kill switch. If those weren't in place, this would not be a defensible plan.

## Progress log (2026-07-30)

**Scheduling mechanism — decided:** cloud routines via the `schedule` skill / `RemoteTrigger` tool (recurring cron on Anthropic's cloud infra), not the raw `CronCreate` tool. `CronCreate` was rejected — it's session-only (nothing written to disk, dies when the terminal/session closes) and auto-expires after 7 days regardless, which is unacceptable for a live-money loop meant to run for weeks unattended.

**Run times — decided:** 3x/day, weekdays, avoiding open/close volatility:

| Run | Central (local) | UTC (for cron) |
|---|---|---|
| 1 | 9:00 AM CT | 14:00 |
| 2 | 12:00 PM CT | 17:00 |
| 3 | 2:15 PM CT | 19:15 |

(CT = ET − 1 hour year-round, both observe DST the same way. Re-verify UTC offset if resuming this after a DST transition.)

**Resolved:**

1. ~~Robinhood MCP server needs a reachable URL~~ — **DONE (2026-07-30, this session).** `mcp__robinhood-trading__*` tools confirmed live: `get_accounts` returns two accounts — margin/individual (`597998368`, `agentic_allowed: false`) and **cash/"Agentic"** (`506274612`, `agentic_allowed: true`). The cash account matches the plan's account-type requirement. `get_portfolio` on `506274612` confirms **$2,000 cash, $0 positions, $2,000 buying power** — capital is funded and untouched.
2. ~~User restarting Claude Code~~ — **DONE**, this session is post-restart with MCP attached.
6. ~~Create ledger.md and run-log~~ — **DONE.** `ledger.md` (date/ticker/action/price/qty/reason/dip-attribution/P&L/running-total) and `run-log.md` (timestamp/run#/paused?/reconciliation-ok?/candidates/action/notes) created in this directory per the schema agreed below.

**Still blocked on, in order (re-verified 2026-07-30, this session, via `schedule` skill):**

3. **Confirmed still open.** `robinhood-trading` is connected locally (this session's tools work) but is **not** in the claude.ai connector list used by cloud routines — only `higgsfield` and `Zapier` show as connected. User needs to connect it at https://claude.ai/customize/connectors so it gets a `connector_uuid`, otherwise the cloud routine can't call any `mcp__robinhood-trading__*` tool.
4. `trading-agent/` still untracked. `ledger.md`/`run-log.md` now exist locally alongside this file — ready to commit, but not yet pushed. Waiting on explicit go-ahead (this is a shared-state action).
5. **Confirmed still open.** `schedule` skill's GitHub access check for `smokingcow/mySoftware` failed again ("may be temporary"). If routine creation errors on repo access, install the Claude GitHub App: https://claude.ai/code/onboarding?magic=github-app-setup.
7. Not yet created: the 3 `RemoteTrigger` routines themselves (blocked on 3-5 above). Model default for these per this doc's "Runtime" table: `claude-opus-4-8`.

## Open / not yet decided (resolve before or during build)

- Ledger file format/schema (columns: date, ticker, action, price, qty, reason, dip-attribution research summary, P&L, running total) — schema agreed above, file not yet created.
- Wash-sale rule implications (tax) — not addressed yet, informational only so far.
- Whether "1 per sector" uses Robinhood's `sector` fundamental field directly (seen in get_equity_fundamentals) — confirm mapping.
- Retry/error handling if a Robinhood MCP call fails mid-run (e.g., order placed but ledger write fails) — needs an explicit reconciliation step given "Robinhood account is authoritative."
- Review cadence for the strategy itself — e.g., a fixed checkpoint (30 days or N trades) to decide keep/kill/tune, separate from the automatic -20% kill switch.

## Reference: tools used in the prototype session

- `mcp__robinhood-trading__get_scanner_filter_specs`, `create_scan`, `run_scan`, `update_scan_filters` — dip screener
- `mcp__robinhood-trading__get_equity_quotes`, `get_equity_fundamentals` — price/valuation/sector checks
- `mcp__robinhood-trading__get_earnings_results` — did the company report today, beat/miss
- `mcp__robinhood-trading__get_equity_historicals` — weekly bars for recovery-history analysis (results are large; write to a temp file and process with `jq`/Python rather than reading inline)
- `WebSearch` — "why is $TICKER down today" news attribution
- `mcp__robinhood-trading__place_equity_order`, `review_equity_order`, `cancel_equity_order`, `get_equity_orders`, `get_equity_positions` — execution (not yet used; real-money actions)
- `PushNotification` — run summaries

## Next step

Build the agent/loop against this spec: screener → fundamentals/earnings/news attribution → buy filter → ranking → position sizing → order placement → ledger write → reconciliation → notification. Confirm scheduling mechanism and ledger schema first.
