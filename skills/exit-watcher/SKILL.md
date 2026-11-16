---
name: exit-watcher
description: "Watch open trades and say when to exit: stop or target hit, trail the stop once the trade is up 1R, the intraday exit time, and an intraday stock losing VWAP. Use when the user asks should I sell, check my trade, watch my position, or after any entry while the market is open."
---

# Exit Watcher

`dd.py watch` checks every open trade in the journal once and returns one action per trade:

| Action | Meaning |
|---|---|
| `EXIT NOW` | Through the stop, past the exit time, or an option's index stop broke |
| `BOOK PROFIT` | Target reached |
| `MOVE STOP` | Up 1R or more: move the stop-loss order to the new `stop` (1R to entry, then +0.5R per extra 0.5R) |
| `WEAK` | Intraday stock on the wrong side of VWAP: the move has lost support |
| `HOLD` | Nothing to do |
| `CHECK BY HAND` | No price available |

## Workflow

1. Make sure the trade is in the journal. Ticket trades are logged automatically. A trade placed by hand in the broker app is logged with `dd.py journal add SYMBOL --qty N --entry E --stop S --target T [--segment intraday|delivery|options]`.
2. For options, the data feed has no premiums. Either pass the premium with `--price NIFTY25450CE=31.5`, or log the trade with `--underlying NIFTY --underlying-stop LEVEL --underlying-target LEVEL` so the index level is watched.
3. Run `dd.py watch` during the session, every few minutes for intraday trades and once a day for swing trades. In a terminal, `dd.py watch --loop --every 60 --minutes 120` prints only changes.
4. Tell the user the action and the reason in one line per trade, with the price and the profit or loss now. For `MOVE STOP`, give the exact new stop price.

The watcher only advises and moves its own trailing stop. It never places or changes orders. The user does that in the broker app.
