---
name: trade-journal
description: "Record, settle and review trades: close a trade with its exit price, settle paper trades against real candles, and show net P&L, charges paid, win rate and R-multiples by setup. Use at end of day, after an exit, or when the user asks how the experiment is going."
---

# Trade Journal

## Workflow

- `dd.py paper settle` closes open paper trades against real candles (stop, target or flat-by).
- `dd.py journal close <id-or-symbol> --price X --reason stop|target|manual` records a real exit.
- `dd.py journal stats` gives win rate, net P&L, charges paid, average R, and results by setup.
- `dd.py journal list` shows every trade. `dd.py journal export > trades.csv` exports them.
- `dd.py budget` shows what is left of the loss budget.

## Review

After stats, state: net result after charges, what share of gross profit went to charges, which setup is making or losing money, and whether any trade broke a rule. Fewer than 20 closed trades is too few to conclude anything; say so.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
