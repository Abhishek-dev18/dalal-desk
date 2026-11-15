---
name: trade-plan
description: "Build an exact trade plan for an NSE stock: entry, stop-loss and target on the tick grid, for an opening-range breakout, a swing breakout or user-given levels, and check whether the entry has triggered. Use when the user picks a stock to trade or asks for entry, stop and target."
---

# Trade Plan

Writes `trader/plan.json`, which the sizing, risk and ticket skills read.

## Workflow

- Intraday opening-range breakout: `dd.py plan orb SYMBOL --side BUY --r 2 --stop-mode mid`
  (`--side SELL` for a breakdown, `--stop-mode far` for a stop beyond the range, `--or-minutes 30`).
- Swing breakout over the 20-day high with an ATR stop: `dd.py plan breakout SYMBOL --r 2 --atr-mult 1.5`
- Levels from the user or from your own analysis:
  `dd.py plan manual SYMBOL --segment intraday|delivery --side BUY --entry X --stop Y --target Z`
- Has it triggered? `dd.py entry` returns `waiting`, `triggered` or `expired`, judged on closed 5-minute bars only.

## Then

Always continue to `position-sizer` and `risk-gate`. For intraday plans run `time-machine` too. A plan without a size and a gate verdict is not ready.

Explain the plan in plain words: where it enters and why, where it is wrong (the stop), and what it makes at target against what it loses at the stop.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
