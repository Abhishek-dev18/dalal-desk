---
name: intraday-scanner
description: "Scan NSE stocks for intraday setups: gaps, opening-range breakouts, VWAP position and relative volume, ranked by score. Use during market hours when the user wants intraday or day-trading candidates."
---

# Intraday Scanner

## Workflow

1. `dd.py scan intraday` (add `--symbols A,B` or `--universe file.txt`, `--top 10`).
2. Read each row: `gap_pct`, `or_status` (above, below or inside the 09:15-09:30 range), `side`, `rvol` (today's volume against the same time on earlier days), `turnover_cr`, `score`.
3. Keep only rows where `liquid` is true and `side` is set. Drop anything with `rvol` under 1.

## Limits to state every time

- With the Yahoo source the bars are about 15 minutes late. A breakout shown here may already be over. Say this whenever `dd.py doctor` lists yahoo as the data source.
- The scan runs only from 09:30 onwards, once the opening range is complete.
- A score is a reason to look, not a signal. Hand the best one or two to `trade-plan`.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
