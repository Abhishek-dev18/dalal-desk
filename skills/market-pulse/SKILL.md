---
name: market-pulse
description: "Pre-market or any-time read of the Indian market: breadth health score, FII/DII flow regime, top headlines and a risk-on/cautious/risk-off label. Use when the user asks how the market looks, for a morning brief, or before any scan."
---

# Market Pulse

Gives one honest read of the market before anyone looks at single stocks.

## Workflow

1. `dd.py doctor` to confirm mode, data source and loss budget are sane. Report any warning.
2. `dd.py breadth` for the health score, regime and maximum exposure.
3. Flows: search the web for the latest NSE provisional FII and DII cash figures (net, Rs crore) for days not yet logged, then record each with `dd.py flows add --date YYYY-MM-DD --fii N --dii N`. Then `dd.py flows show`.
4. `dd.py news --hours 18` for scored headlines. If the feeds fail, use web search and say so.
5. Search the web for GIFT Nifty, India VIX, Brent crude and USD/INR, and for events due today (results, RBI, US data, expiry). `dd.py expiry NIFTY` gives the next expiry.

## Output

A brief of under 15 lines: regime and max exposure, flows in one line, three headlines that matter, events today, and one sentence on what that means for today (trade normally, trade small, or stand aside). Cite web sources.

In `Risk-Off`, say plainly that the default is no new long trades.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
