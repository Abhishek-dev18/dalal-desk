---
name: trading-costs
description: "Calculate exact Indian trading charges for a trade: brokerage, STT, exchange charges, SEBI fee, stamp duty, GST and DP charges, with net P&L and the breakeven move, for delivery, intraday, futures and options. Use when the user asks about charges, brokerage, breakeven or net profit."
---

# Trading Costs

## Workflow

`dd.py costs --segment intraday|delivery|futures|options --buy PRICE --sell PRICE --qty N`

Reports each charge, the total, net P&L and `breakeven_move_per_share` (how far price must move just to pay the charges).

## Notes

- Rates are dated tables in `dalal/refdata.py`, effective 1 April 2026 (STT on futures 0.05%, on option premium 0.15%). `dd.py doctor` warns when the table has not been reviewed for six months.
- Brokerage follows the `brokerage` setting: `zerodha` (0.03% or Rs 20, lower of the two; delivery free; options Rs 20 an order) or `flat10`.
- The broker's contract note is the final word. Small differences from rounding are normal.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
