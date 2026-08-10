# Run Log

One entry per scheduled run (3x/day, weekdays), including "no action taken" runs — see PLAN.md "Notifications": silence must never mean "didn't check."

Like `ledger.md`, this file is **derived, not primary**. If a run cannot push it, the run still happened and the trades are still authoritative on Robinhood's side — the next run reconstructs what it can. See `LEDGER_BUG.md`.

---

## Backfill note (2026-08-08)

No run between 2026-07-31 and 2026-08-07 ever wrote to this file — the Step 9 git push was never authorized and failed silently on all ~24 runs. The rows below are **partially reconstructed** from broker fill timestamps and routine `last_fired_at` values.

What is recoverable: that a run fired, and what it traded. Benchmark columns were added 2026-08-09 and are blank for this window — SPY data exists, but attributing a portfolio value to a specific run retroactively does not.
What is **not** recoverable: candidates scanned, reconciliation status, near-misses, and the reasoning behind each decision. Runs that took no action left no trace at all, so a "no action" run and a run that errored out mid-way are indistinguishable in this window. Rows are only listed where there is direct evidence a run fired; the absence of a row does not mean the run didn't happen.

---

| Timestamp (UTC) | Run # | Paused? | Reconciliation OK? | Candidates Scanned | Action Taken | Portfolio % | SPY % | Relative (pp) | Notes |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-31 14:00 | 1 | NO | unknown | unknown | bought EIX (5 @ $75.69) | — | — | — | Reconstructed from fill at 14:13:26Z |
| 2026-07-31 17:00 | 2 | NO | unknown | unknown | bought BTSG (6 @ $60.78) | — | — | — | Reconstructed from fill at 17:15:16Z |
| 2026-07-31 19:15 | 3 | NO | unknown | unknown | bought NXT (4 @ $89.76) | — | — | — | Reconstructed from fill at 19:22:20Z |
| 2026-08-03 14:00 | 4 | NO | unknown | unknown | bought FTI (6 @ $69.57) | — | — | — | Reconstructed from fill at 14:13:45Z |
| 2026-08-03 19:15 | 6 | NO | unknown | unknown | bought PBF (6 @ $67.54) | — | — | — | Reconstructed from fill at 19:20:56Z |
| 2026-08-04 14:00 | 7 | NO | unknown | unknown | sold NXT (take-profit, +7.08%) | — | — | — | Reconstructed from fill at 14:11:48Z |
| 2026-08-05 14:00 | 10 | NO | unknown | unknown | sold EIX (stop-loss, -9.42%) | — | — | — | Reconstructed from fill at 14:10:39Z |
| 2026-08-06 14:00 | 13 | NO | unknown | unknown | sold PBF (stop-loss, -9.61%); bought ACIW (7 @ $54.69) | — | — | — | Two fills same run: 14:16:13Z and 14:23:14Z |
| 2026-08-06 17:00 | 14 | NO | unknown | unknown | bought XYZ (5 @ $79.03) | — | — | — | Reconstructed from fill at 17:18:00Z |
| 2026-08-07 17:00 | 17 | NO | unknown | unknown | bought MNST (4 @ $90.44) | — | — | — | Reconstructed from fill at 17:17:50Z |
| 2026-08-07 19:15 | 18 | NO | unknown | unknown | no fills recorded | — | — | — | Routine `last_fired_at` 19:16:11Z confirms it fired; outcome unknown |
| 2026-08-10 14:20 | 1 (post-fix) | NO | YES (clean) | 0 (skipped — fully deployed) | none (no exits triggered; no buying power for new buys) | -1.79% | +4.37% | -6.15 | First post-fix logged run. Ledger reconciled cleanly vs broker (13 fills, 0 rows differed). 5 open positions all held: none hit -8% SL / +6% TP / 12-day max hold (oldest BTSG = 7 trading days). Settled cash $29 < 20% of capital ($392.86) → new-buy steps skipped, scan not run. Circuit breaker not tripped. Persisted? = NO (see below) |

Run numbers are approximate — they assume all 3 daily runs fired on each weekday, which `last_fired_at` supports but cannot prove retroactively for every slot. Numbering restarts cleanly from the first run after the 2026-08-08 fix.
