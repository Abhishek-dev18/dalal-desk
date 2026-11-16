---
name: option-buyer
description: "Check whether a small account can afford to buy an index option and what it needs to work: lot cost, breakeven, move needed, implied volatility, Greeks and daily time decay. Also prices options with Black-Scholes. Use when the user wants to buy a call or put, asks about F&O with small capital, or asks for option price, IV or Greeks."
---

# Option Buyer

Built for small accounts. It only supports buying options; selling and futures are refused by the risk gate.

## Workflow

1. `dd.py options buycheck --underlying NIFTY --kind CE --spot S --strike K --premium P --days D`
   Reports cost of one lot, whether it fits the premium cap, breakeven, the move needed, implied volatility, and time decay per day for one lot.
2. If `affordable` is false or there are warnings, say so first and recommend not taking it.
3. To trade it: `dd.py plan manual NIFTY25300CE --segment options --side BUY --entry P --stop X --target Y --lot 65`, then `position-sizer`, `risk-gate`, `order-ticket`. Option orders go through the paper or manual broker only.
4. Pricing tools: `dd.py options price|greeks --kind CE --spot S --strike K --days D --vol 0.14` and `dd.py options iv ... --premium P`.

## Always say

- The whole premium can be lost, and on expiry day that can happen within hours.
- Compare `theta_cost_per_day_one_lot` with the planned profit: if a day of waiting costs more than a third of the target profit, the trade needs to work fast.

## Present it as the trade card

After planning, sizing and the gate, run `dd.py card`. For options it adds the contract, expiry and lot size. Show the card as it prints, including a NO TRADE verdict.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
