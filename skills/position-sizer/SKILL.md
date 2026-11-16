---
name: position-sizer
description: "Work out how many shares or lots to trade so the loss at the stop, including Indian charges, stays within the per-trade risk limit and the account's buying power. Use after a trade plan exists or when the user asks how much to buy."
---

# Position Sizer

## Workflow

1. `dd.py size` reads `trader/plan.json` and writes `trader/size.json`.
2. Report `qty`, `position_value`, `max_loss`, `net_profit_at_target` and `net_reward_risk`. All are after charges.
3. If `qty` is 0, give the `reason` and stop. Do not suggest a wider risk limit; suggest a tighter stop or a cheaper stock.

Default limits (from `config.json`): 1% of capital risked per trade, no leverage (`mis_leverage` 1.0), options premium capped at 10% of capital. The user can change these in `config.json`; you do not change them. If `option_risk_limit` is `warn`, an option plan is sized at one lot and every limit it breaks is listed as a risk warning; show those warnings to the user word for word.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
