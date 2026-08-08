# The silent ledger bug (2026-07-31 → 2026-08-08)

## Symptom

`ledger.md` and `run-log.md` contained zero data rows for 8 days, while the live Robinhood account showed **11 real fills** across 8 tickers. The loop was trading correctly and logging nothing.

## Root cause: the routines have read access to the repo, not push access

The three production routines are configured with:

```json
"sources": [{"git_repository": {"url": "https://github.com/smokingcow/trading-agent"}}]
```

A `git_repository` source grants the session a **clone**. It does not grant push. This platform treats the two as distinct capabilities — the `add_repo` tool takes an explicit `access: "read" | "push"` parameter (push is "attached with credentials after the full repository-access checks"), and `create_session` exposes a separate `outcome_branch` parameter specifically for pushing changes back. The routines declared neither. Git credentials in these containers are proxy-injected (`GITHUB_TOKEN=proxy-injected`, `https_proxy` → agent proxy), and the proxy authorizes per-repo scope, so an unauthorized push is rejected at the proxy rather than by GitHub.

Every run therefore: cloned fine → read `AGENT_PROMPT.md` fine → traded fine → hit Step 9 → push rejected → **and Step 9 explicitly said not to treat that as fatal**, so the run swallowed the error, sent a normal-looking notification, and exited. The container was then reclaimed, taking the ledger edits with it.

## Why we're confident this is the cause

- **~24 consecutive runs, zero commits, no exceptions.** A context/token exhaustion problem would be intermittent. Perfect determinism points to a permissions wall.
- `git ls-remote` shows only `main` and the research branch — the agent never pushed to *any* branch, so it isn't a wrong-branch or detached-HEAD problem.
- The 2026-07-31 clone test succeeded (read path verified). No write path was ever tested — the pre-launch wiring test explicitly instructed *"Do NOT modify, write, commit, or push any file in the repo."* **The one path that mattered for persistence was the one path never exercised before going live.**
- Trades executed normally throughout, confirming the failure is isolated to Step 9.

## What was lost

Prices, quantities, dates and P&L were all recoverable from `get_equity_orders` and have been backfilled into `ledger.md`.

**The dip-attribution reasoning is permanently gone.** Every run computed a thesis for why a dip was sentiment-driven rather than fundamental, then discarded it. That was the only data that could ever have told us whether the buy filter works. It has deliberately *not* been reconstructed — writing plausible rationales after seeing the outcomes would corrupt the dataset with hindsight.

## The fix (2026-08-08)

Repairing the routines' git scope isn't possible from inside a session: `update_trigger` only exposes name, cron, enabled, model, and prompt — not `sources`. So rather than depend on a push that may never be authorized, persistence was made **defensive**:

1. **The ledger is now derived, not primary.** Step 1 rebuilds it from `get_equity_orders` on every run. If a push fails, the next run reconstructs everything except the reasoning. Data loss is bounded to one run's thesis instead of accumulating forever.
2. **Push failure is now loud.** Step 9 verifies the push actually landed (`git rev-parse` against the remote) instead of trusting the exit code, and a failure is escalated into the push notification as a prominent `⚠️ PUSH FAILED` line. The old "do not treat this as fatal" wording is what made an 8-day outage invisible; it's gone.
3. **The run log records its own persistence status**, so a future gap is self-evident in the data rather than requiring someone to notice absence.

## Outstanding action for the user (cannot be done from a session)

To restore real persistence — and recover the decision log, which is what makes the strategy measurable — the routines need push access to the repo. Options:

- **Recreate the three routines via the `RemoteTrigger` HTTP API** with push-scoped repo access (or an `outcome_branch`), matching how they were originally created.
- Or confirm in the Claude GitHub settings (https://claude.ai/admin-settings/claude-in-slack) that the connected GitHub App grants **write** to `smokingcow/trading-agent`, not just read.

Until then the mitigations above keep the loop honest and self-healing, but each run's dip-attribution reasoning will still be lost — meaning the strategy stays unfalsifiable. **This is the single highest-value open item in the project**, for the reasons in `STRATEGY_RESEARCH_2.md` §1.

## Lesson worth keeping

The pre-launch test suite verified every capability except the one that persisted state, because the test was written to be safe (`do NOT write, commit, or push`). Safety in a wiring test should mean *writing to a throwaway location*, not *skipping the write path*. Any future capability added to this loop should have its write path exercised end-to-end before go-live.
