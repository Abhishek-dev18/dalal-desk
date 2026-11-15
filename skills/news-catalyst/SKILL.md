---
name: news-catalyst
description: "Find and score Indian market news and company catalysts (results, order wins, deals, regulatory action) for the market or for named NSE stocks. Use when the user asks what is moving, why a stock moved, or for stocks in news."
---

# News Catalyst

## Workflow

1. `dd.py news --hours 24` for the market, or `dd.py news --symbols SBIN,SENCO --hours 48` for named stocks.
2. For anything with impact 2 or 3, confirm it with a web search and, where possible, the NSE or BSE filing. A headline alone is not a catalyst.
3. For results, pull the actual numbers: revenue, profit, margin, and how the stock reacted.

## Output

A table: stock, catalyst, source, date, already-priced-in check (how far the stock has moved since), and a verdict of `fresh`, `stale` or `unconfirmed`. A catalyst older than two sessions with a big move behind it is stale.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
