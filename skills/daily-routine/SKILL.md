---
name: daily-routine
description: "Run the full Dalal Desk trading day in order: morning brief, scan, plan, simulation, sizing, risk gate, ticket, and end-of-day settlement and review. Use when the user says start the day, run the routine, find me a trade today, or do the end-of-day review."
---

# Daily Routine

The other skills in order. Stop at the first step that says no.

## Morning (before 09:15)

1. `market-pulse`. In `Risk-Off`, the default answer is no trades today.
2. `dd.py budget`. If `locked` is true, there are no trades today.
3. `swing-scanner` for a watchlist; `news-catalyst` for overnight results.

## Market hours (09:30 to 15:00)

4. `intraday-scanner` after 09:30.
5. Pick at most one or two candidates. For each: `trade-plan`, then `time-machine`. Drop it if the simulation is negative after charges.
6. `position-sizer`, then `risk-gate`. A block ends it.
   Show the result with `dd.py card`.
7. `dd.py entry` until it says `triggered` (or `expired`).
8. `order-ticket`, only when the user asks to take the trade.

## End of day (after 15:30)

8b. While a trade is open, run `exit-watcher` (`dd.py watch`) every few minutes and pass on any action that is not HOLD.
9. `dd.py paper settle` (paper) or `dd.py journal close` for each real exit.
10. `trade-journal` stats and `dd.py budget`.
11. Three lines: what was traded and the net result, whether every rule was followed, and one thing to do differently tomorrow.

Doing nothing is a valid outcome of this routine. Say so when no setup passes.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
