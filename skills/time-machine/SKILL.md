---
name: time-machine
description: "Stress-test an intraday plan before risking money: replay the rest of the day 10,000 times from the stock's own past 5-minute candles, and backtest the same rule on real past sessions net of Indian charges. Use when the user asks for the odds, a backtest, or whether a setup works."
---

# Time Machine

## Workflow

1. Needs an intraday plan in `trader/plan.json` (from `trade-plan`).
2. `dd.py sim` (options: `--runs 10000 --seed 7 --from HH:MM`). Reports how often the target came first, the stop came first, or the trade was still open at flat-by time, and the mean result in R after charges.
3. `dd.py backtest SYMBOL --side BUY --r 2 --stop-mode mid` runs the opening-range rule on about 60 real sessions.

## How to report it

- Lead with `mean_net_r` and the `read` line. Below zero means skip.
- Give target-first and stop-first percentages side by side.
- Say the sample is small (about 60 sessions) and that the simulation shuffles past candles; it cannot know today's news.
- Never describe a positive result as an edge or a prediction.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
