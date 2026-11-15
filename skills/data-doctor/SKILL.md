---
name: data-doctor
description: "Check and set up Dalal Desk: mode, broker and data provider, API keys, loss limits, rate-table age and whether live data actually works. Use on first run, when a command fails, or when the user wants to connect Upstox or Zerodha or switch from paper to live."
---

# Data Doctor

## Workflow

1. `dd.py doctor --live` shows configuration, which secrets are set, and a live data probe.
2. First run: copy `config.example.json` to `config.json` and `.env.example` to `.env` in the user's working folder, then run the doctor again.

## Data sources (`data` in config.json, tried in order)

- `yahoo`: free, no key, about 15 minutes late. Fine for swing work and study.
- `upstox`: real time. Needs `UPSTOX_ACCESS_TOKEN` in `.env`, renewed every day.
- `csv`: files in `csv_dir` named `SYMBOL_5m.csv` and `SYMBOL_1d.csv` (columns t,o,h,l,c,v).

## Going live (only when the user asks)

1. Recommend at least 20 settled paper trades first.
2. `mode: live` with `broker: manual` prints orders for the user to place by hand. This works anywhere and is the recommended first step.
3. `broker: upstox` or `kite` sends orders by API. Needs the token in `.env`, `LIVE_TRADING=1`, and a static IP registered with the broker (SEBI rule since April 2026; most home connections do not have one). These adapters were written from the brokers' documentation and have not been tested on a live account by the author, so the first order should be one share.

Never write secrets into chat, into `config.json`, or into any file other than `.env`.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
