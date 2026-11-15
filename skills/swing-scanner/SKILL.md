---
name: swing-scanner
description: "Scan NSE stocks for swing setups lasting days to weeks: trend template, tight bases, volume dry-up, breakouts over 20 and 55 days, pullbacks to the 20 EMA and relative strength against Nifty. Use when the user wants swing or positional candidates."
---

# Swing Scanner

## Workflow

1. Run `market-pulse` first, or at least `dd.py breadth`. In `Risk-Off`, report candidates as a watchlist only.
2. `dd.py scan swing` (optional `--symbols`, `--universe`, `--top`).
3. Read each row: `trend_template` (out of 6), `signals`, `pct_to_pivot`, `tightness`, `volume_dry_up`, `rs_vs_nifty_6m`.
4. For the top three, check `news-catalyst` for results due in the holding period. A result inside the hold is an event risk the stop cannot control.

## Output

Ranked shortlist with the reason each is on it and what would invalidate it. Pass a chosen stock to `trade-plan` with the `breakout` setup.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
