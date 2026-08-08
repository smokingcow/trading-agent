# Trading Agent — Dip-Buy Loop

Status: **LIVE as of 2026-07-31; strategy and persistence revised 2026-08-08.** All 3 scheduled routines are running with real money, fully autonomous. Note: runs currently **cannot persist files** (read-only repo scope — see `LEDGER_BUG.md`); the loop is self-healing around this but each run's reasoning is lost until it's fixed. This file is the source of truth for the strategy design; `AGENT_PROMPT.md` is the source of truth for the runtime logic the loop actually executes. Build against these — don't re-derive from scratch in a new session. If something needs to stop immediately, create a `PAUSE` file in the repo root and push it (see AGENT_PROMPT.md Step 0) — it's checked at the start of every run, not instantly.

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

**Resolved (2026-07-31, this session):**

3. ~~robinhood-trading connector not visible to cloud routines~~ — **DONE.** The `schedule` skill's injected connector list stayed stale across multiple rechecks (kept showing only higgsfield/Zapier) even after the user confirmed via screenshot that Robinhood showed connected (green check) on https://claude.ai/customize/connectors. That list was just cached/stale — the **raw `RemoteTrigger` API response** (on `create`/`get`) confirms it's actually live: `connector_uuid: 63c68dd2-11bb-4d4c-acaf-3f7e627ea45a`, `name: Robinhood`, `url: https://agent.robinhood.com/mcp/trading`. Use this connector_uuid directly when building the production routines — don't trust the `schedule` skill's injected list for this connector.
4. ~~trading-agent/ untracked~~ — **DONE, but relocated.** User rejected using the `mySoftware` monorepo (it's their entire project portfolio). Repo now lives at **`https://github.com/smokingcow/trading-agent`** (public, personal account, dedicated repo — separate from `mySoftware`). Local `trading-agent/` is its own independent git repo (not nested/tracked inside the `mySoftware` repo), remote `origin` = `git@github.com:smokingcow/trading-agent.git` (SSH; local key `~/.ssh/id_ed25519` was added to the GitHub account to enable push). Local git identity for this repo: `Lucas Sielski <lucas.sielski@gmail.com>`.
   - **False start, documented so it isn't re-attempted:** first tried GitLab (`git@gitlab.com:lucas.sielski/trading-agent.git`, made public). A throwaway one-shot test routine against it failed with `Authentication failed while accessing the git_repository source. Check that your GitHub token or credentials...` — **the `RemoteTrigger`/cloud-routine `sources.git_repository` mechanism is GitHub-only**, regardless of host or public/private status. Do not use GitLab (or any non-GitHub host) for repos that cloud routines need to clone.
5. ~~GitHub App / repo access~~ — **DONE, but the actual fix was different than expected.** Making the GitHub repo public was **not** sufficient — routine creation 401'd with `"Connect your GitHub account before saving a routine that uses a GitHub repository."` This is a Claude.ai-side account connection, separate from local git/GitHub auth: running `gh auth login` locally did **not** resolve it (retried, same 401). What worked: the user completed the web flow at `/web-setup` → `https://claude.ai/code/onboarding?step=alt-auth` (fallback shown when local `gh` CLI wasn't installed). After that, routine creation succeeded and a follow-up one-shot test routine (`trig_01GZW99MqStSXqcj9pmgRtzg`) cloned the repo, read `PLAN.md` in full, and reported `GITHUB CLONE TEST: SUCCESS`.

**Leftover, harmless:** two throwaway one-shot test routines exist and have already fired (`ended_reason: run_once_fired`, can't recur) — `trig_01T5NcAzCvCdY5L7nbytqF3k` (GitLab attempt, failed as expected) and `trig_01GZW99MqStSXqcj9pmgRtzg` (GitHub, succeeded). The `RemoteTrigger` tool cannot delete routines; if the user wants them off the list, do it manually at https://claude.ai/code/routines — not urgent.

7. ~~Create the 3 production `RemoteTrigger` routines~~ — **DONE. The loop is live as of 2026-07-31.**
   - Runtime instructions drafted as `AGENT_PROMPT.md` (self-contained step-by-step procedure, read fresh by the agent every run). It documents 9 implementation-level judgment calls not explicitly locked in this file's ranges (exact position size, take-profit/stop-loss %, circuit-breaker %, max hold days, positions-per-run cap, pause-flag mechanism, starting-capital reference, sector field source) — all reviewed and confirmed by the user before going live. See that file's top callout table; keep it in sync if any of these are revisited.
   - Pre-launch, a full-production-config wiring test (throwaway, read-only, no trades/no writes) confirmed the Robinhood MCP tools, WebSearch, and PushNotification all work correctly inside a routine, and that push notifications actually arrive on-device — not just that the tool call reports success.
   - Production routines (all: model `claude-opus-4-8`, repo `https://github.com/smokingcow/trading-agent`, Robinhood connector `63c68dd2-11bb-4d4c-acaf-3f7e627ea45a` attached, `allowed_tools: [Bash, Read, Write, Edit, Glob, Grep, WebSearch, PushNotification]`):

     | Routine | ID | Cron (UTC) |
     |---|---|---|
     | Run 1 — 9:00 AM CT | `trig_01P9bwD1b1vw8CNLvUR24cHG` | `0 14 * * 1-5` |
     | Run 2 — 12:00 PM CT | `trig_017YRHR7p1qFgkjY85ZqK9Py` | `0 17 * * 1-5` |
     | Run 3 — 2:15 PM CT | `trig_01456i7e7s9sM2na3e6KnTao` | `15 19 * * 1-5` |

   - Each routine's kickoff message just tells the agent to read and follow `AGENT_PROMPT.md` from Step 0 — the actual trading logic lives in that file, not duplicated across the 3 routine configs, so strategy changes only require editing and pushing `AGENT_PROMPT.md`, not updating all 3 routines via `RemoteTrigger update`.
   - Two throwaway one-shot test routines also exist from earlier in this build (GitLab attempt, GitHub clone test, wiring test) — all already fired, harmless, not cleaned up (`RemoteTrigger` can't delete; manual cleanup at https://claude.ai/code/routines if desired).

**All blockers resolved. Status is now: live, monitoring only.** See "Open / not yet decided" below for what's still genuinely unaddressed (not blocking, but worth resolving soon).

## Progress log (2026-08-08) — first strategy review

**The loop logged nothing for its first 8 days.** 11 real fills executed while `ledger.md` and `run-log.md` stayed empty. Root cause: the routines hold **read-only** repo scope (`sources.git_repository` grants a clone, not push), so every Step 9 push was rejected at the agent proxy — and Step 9's old "don't treat a failed push as fatal" wording swallowed it silently on all ~24 runs. Full write-up in **`LEDGER_BUG.md`**.

Fixed by making persistence defensive rather than assumed: the ledger is now *rebuilt from Robinhood order history* every run (Step 1), pushes are *verified* by comparing local and remote hashes rather than trusting the exit code, and failure is escalated loudly into the push notification with the run's reasoning carried inline (Step 9). Historical rows have been backfilled from broker fill records; the dip-attribution reasoning for those trades is permanently lost and was deliberately **not** reconstructed.

**Still requires user action:** restoring real push access needs the routines recreated via the `RemoteTrigger` HTTP API with push-scoped repo access — `update_trigger` cannot modify `sources`. Until then each run's reasoning is lost, which is what keeps the strategy unfalsifiable.

**Strategy research** captured in `STRATEGY_RESEARCH.md` and `STRATEGY_RESEARCH_2.md`. Headline findings:
- **Options are not viable at this account size** — the agentic account has no options approval, and at $2K the collateral math for cash-secured puts (~$6K/contract) and covered calls (100 shares) doesn't work regardless. Revisit at $20K+.
- **TP/SL tuning does not create edge.** Under a random walk every TP/SL configuration has EV exactly zero; the ratio only trades win rate against win size. All negative expectancy comes from **slippage**. A proposed change to +8%/-7% was derived, tested, found to be *worse* than the status quo, and reverted before going live — see the callout box in `AGENT_PROMPT.md`.
- The real lever is **friction and gap risk**, which is what the new earnings/wash-sale/spread/trend gates target.
- **Sample size is the binding constraint**: 92-737 closed trades are needed to distinguish a real edge from luck. There are 3.

**Buy-filter changes now live** (all narrow the universe; none widen it): earnings-date exclusion (14 days), wash-sale guard (30 days), bid-ask spread cap (1.0%), and a 200-day EMA trend filter.

## Open / not yet decided

- ~~Ledger file format/schema~~ — **DONE.** Created, backfilled, and extended with an `Attribution Correct?` column so win rate can be measured by classification type.
- ~~Wash-sale rule implications (tax)~~ — **DONE.** Now an enforced gate (judgment-call #11); EIX and PBF are currently excluded.
- ~~Whether "1 per sector" uses Robinhood's `sector` fundamental field~~ — **DONE.** Confirmed, judgment-call #9.
- ~~Retry/error handling if a call fails mid-run~~ — **DONE.** Step 1 now rebuilds from the authoritative account every run, so a mid-run failure self-heals.
- **Backtest harness — the top open item.** Nothing in this project can currently distinguish a working strategy from a lucky one, and no parameter should be tuned until it can. Build over `get_equity_historicals`. Every strategy candidate below is gated on this.
- Restore push access to the routines (see above) — without it the decision log is lost every run.
- Strategy candidates to evaluate *once the harness exists*, in evidence order: post-earnings announcement drift, 52-week-high momentum, quality/gross-profitability gating. See `STRATEGY_RESEARCH_2.md` §3.
- Review cadence for the strategy itself — a fixed checkpoint (30 days or N trades) to decide keep/kill/tune, separate from the automatic -20% kill switch. **Still unresolved.**

## Reference: tools used in the prototype session

- `mcp__robinhood-trading__get_scanner_filter_specs`, `create_scan`, `run_scan`, `update_scan_filters` — dip screener
- `mcp__robinhood-trading__get_equity_quotes`, `get_equity_fundamentals` — price/valuation/sector checks
- `mcp__robinhood-trading__get_earnings_results` — did the company report today, beat/miss
- `mcp__robinhood-trading__get_equity_historicals` — weekly bars for recovery-history analysis (results are large; write to a temp file and process with `jq`/Python rather than reading inline)
- `WebSearch` — "why is $TICKER down today" news attribution
- `mcp__robinhood-trading__place_equity_order`, `review_equity_order`, `cancel_equity_order`, `get_equity_orders`, `get_equity_positions` — execution (not yet used; real-money actions)
- `PushNotification` — run summaries

## Next step

Build is complete and the loop is live (see Progress log above). Remaining work is monitoring and the still-open items above, not construction:

- Watch the first several live runs closely — `run-log.md` and push notifications are the fast signal; the live Robinhood account is the authoritative one.
- Resolve the "Open / not yet decided" items above, especially the review-cadence checkpoint (currently nothing forces a keep/kill/tune decision except the automatic -20% kill switch).
- If the strategy needs to change, edit `AGENT_PROMPT.md` and push — no routine reconfiguration needed, every run reads it fresh.
