---
name: risk-gate
description: "Run the PASS or BLOCK risk check on a sized trade plan, show the loss budget, and control the kill switch. Use before any order ticket, when the user asks if a trade is allowed, how much loss budget is left, or says to stop trading."
---

# Risk Gate

## Workflow

- `dd.py gate` checks the plan and size against every limit: kill switch, mode, daily loss stop, total loss budget, trades per day, open positions, maximum loss, reward-to-risk after charges, entry window, tick grid, no option selling, no delivery shorts.
- `dd.py budget` shows today's P&L, room left today, and room left in the total loss budget.
- `dd.py kill on` stops all new orders. Only a human can clear it, by deleting `trader/KILL`.

## Rules

- A `BLOCK` is final. Report which checks failed and why. Never rework the numbers to get a pass, and never suggest editing limits to get one trade through.
- If the user says stop, halt, or kill, run `dd.py kill on` immediately.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
