---
name: order-ticket
description: "Turn a plan that passed the risk gate into an order ticket, get the user's typed approval, and place it: on the paper broker by default, as manual instructions, or through a broker API in live mode. Use only when the user says to place, execute or take the trade."
---

# Order Ticket

The only skill that places orders. The flow is propose, approve, place.

## Workflow

1. `dd.py ticket new` builds a ticket from the plan and size. It re-runs the risk gate and refuses on a block.
2. Show the user the `plain` sentence exactly, the mode (paper or live) and the expiry time. Then ask them to type the approval phrase shown in `to_approve`, for example `YES 3f9a1c2e`.
3. Wait. Do nothing until the user has typed that exact phrase in their own message.
4. `dd.py ticket approve <id> --typed "YES <id>"` passing the user's text unchanged.
5. `dd.py ticket execute <id>`.
   - `paper`: simulated fill, logged to the journal.
   - `manual`: prints the three orders for the user to enter in their broker app.
   - `upstox` or `kite`: sends the entry and stop orders. Needs `mode: live`, `LIVE_TRADING=1` and a static IP registered with the broker.

## Hard rules

- Never type or construct the approval phrase yourself. "ok", "go ahead" or "yes" is not approval; ask for the exact phrase.
- Never run approve and execute in the same turn as the proposal.
- A ticket expires after 15 minutes. If it expired, rebuild the plan; do not reuse old levels.
- If a broker MCP order tool is available, do not call it directly. The plugin's hook blocks order tools without an approved ticket.
- In live mode, remind the user that the target order is not placed automatically.

## How to run the tool

Every command is `python3 <root>/dd.py <command>`, where `<root>` is the Dalal Desk folder
(two folders above this file; it contains `dd.py`). Run it from the user's working folder,
where `config.json` and the `trader/` state folder live. Each command prints JSON. Report
the numbers it prints; never invent or adjust them.

## Rules

- This is decision support, not advice. Say what the numbers show and what they do not.
- Never place, approve or change an order yourself. Only the `order-ticket` skill places orders, and only after the user types the approval phrase.
- If a command fails, show the error and stop. Do not fill the gap with a guess.
