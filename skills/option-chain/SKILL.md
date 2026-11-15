---
name: option-chain
description: "Read an NSE option chain: put-call ratio, max pain, call and put OI walls, ATM straddle and the range it implies, plus expiry dates and lot sizes. Use when the user asks about option chain, OI, PCR, max pain, support and resistance from options, or expiry."
---

# Option Chain

## Workflow

1. `dd.py expiry NIFTY` (or BANKNIFTY, FINNIFTY, MIDCPNIFTY, SENSEX) for the next weekly and monthly expiry and the lot size. Only Nifty and Sensex have weekly expiries.
2. Get the chain into a CSV with columns `strike,ce_oi,pe_oi` and optionally `ce_ltp,pe_ltp,ce_oi_chg,pe_oi_chg`. Sources: a connected broker MCP, or the user's download from the NSE option-chain page converted to those columns.
3. `dd.py options chain --file chain.csv --spot 25144`

## Reading it

- `call_wall` and `put_wall` are the strikes with the most open interest: likely resistance and support until they break.
- `pcr_oi` above about 1.2 leans bullish, below about 0.8 leans bearish; near 1 is neutral.
- `implied_range` is strike plus or minus the ATM straddle: the move the market is pricing by expiry.
- This is positioning, not a forecast. Say when the chain is stale (a file from an earlier session).

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
