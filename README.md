# Dalal Desk

An Indian stock market trading desk for Claude. It scans NSE stocks, builds an exact trade plan,
tests the odds, sizes the position to your risk limit after charges, runs a hard risk check, and
places the trade only after you approve it: on paper by default, or for real when you switch it on.

Built for small accounts (the defaults assume Rs 20,000) and for intraday, swing and option-buying trades.

> **This is not investment advice and it does not give you an edge.** It makes the odds, the costs
> and the rules visible. Most retail day traders lose money. Use money you can afford to lose.

![One trade from scan to review, on sample data in paper mode](docs/demo.gif)

*The run above is real output on synthetic sample data. The simulation said skip, the demo took the
trade on paper anyway, and it was stopped out with the loss inside the limit.*

## What it does

| Step | Skill | Command |
|---|---|---|
| How is the market? | `market-pulse`, `news-catalyst` | `breadth`, `flows`, `news` |
| What is setting up? | `intraday-scanner`, `swing-scanner` | `scan intraday`, `scan swing` |
| Exact entry, stop, target | `trade-plan` | `plan orb`, `plan breakout`, `plan manual`, `entry` |
| What are the odds? | `time-machine` | `sim` (10,000 replays), `backtest` |
| How many shares? | `position-sizer`, `trading-costs` | `size`, `costs` |
| Is it allowed? | `risk-gate` | `gate`, `budget`, `kill on` |
| Place it | `order-ticket` | `ticket new`, `approve`, `execute` |
| Track it | `trade-journal`, `tax-report` | `paper settle`, `journal`, `tax` |
| Options | `option-chain`, `option-buyer` | `options chain`, `buycheck`, `greeks`, `iv`, `expiry` |
| Setup and the whole day | `data-doctor`, `daily-routine` | `doctor` |

Slash commands: `/brief`, `/scan`, `/trade SYMBOL`, `/eod`, `/kill`.
Sub-agents: `market-analyst`, `setup-analyst`, `risk-officer`.

## Install

Needs Python 3.9 or newer. There is nothing to `pip install`; it uses only the standard library.

**As a Claude Code plugin:**

```
/plugin marketplace add Abhishek-dev18/dalal-desk
/plugin install dalal-desk@dalal-desk
```

**Or by hand:** clone the repo and copy `skills/` into `~/.claude/skills/` (keep the repo; the skills call `dd.py`).

**First run**, in the folder where you want your trading state kept:

```
cp /path/to/dalal-desk/config.example.json config.json
cp /path/to/dalal-desk/.env.example .env
python3 /path/to/dalal-desk/dd.py doctor --live
```

Then ask Claude: "run the morning brief" or "scan for intraday setups".

## One trade, start to finish

```
dd.py scan intraday                      # ranked candidates after 09:30
dd.py plan orb SBIN --side BUY --r 2     # entry, stop, target on the tick grid
dd.py sim                                # 10,000 replays of the rest of the day, net of charges
dd.py size                               # shares so that loss at stop + charges <= 1% of capital
dd.py gate                               # PASS or BLOCK
dd.py entry                              # waiting / triggered / expired (closed 5m bars)
dd.py ticket new                         # proposes: "BUY 18 SBIN at 1081.6 ..."
dd.py ticket approve 3f9a1c2e --typed "YES 3f9a1c2e"
dd.py ticket execute 3f9a1c2e            # paper fill, logged to the journal
dd.py paper settle                       # after the close: stop, target or flat-by
dd.py journal stats
```

## Connecting data and a broker

Set these in `config.json`. Secrets go in `.env` only.

| Setting | Options | Notes |
|---|---|---|
| `data` | `yahoo` | Free, no key, about 15 minutes late. Fine for swing trades and study. Not for live intraday entries. |
| | `upstox` | Real time. Needs `UPSTOX_ACCESS_TOKEN`, renewed daily. |
| | `csv` | Your own files: `data/SYMBOL_5m.csv`, `data/SYMBOL_1d.csv` with columns `t,o,h,l,c,v`. |
| `mode` | `paper` (default) | Simulated fills, real candles. |
| | `research` | Analysis only; the gate blocks every ticket. |
| | `live` | Real money. See below. |
| `broker` (live only) | `manual` | Prints the exact orders; you enter them in your broker app. Works anywhere. |
| | `upstox`, `kite` | Sends entry and stop orders by API. |

### Before going live

1. Settle at least 20 paper trades and read `journal stats`.
2. Start with `mode: live`, `broker: manual`.
3. API orders (`upstox`, `kite`) need all of: the access token in `.env`, `LIVE_TRADING=1`, and a
   **static IP registered with your broker**. SEBI has required this for all API orders since
   1 April 2026, and most home internet connections do not have one.
4. The Upstox and Kite adapters were written from the brokers' public documentation and **have not
   been run against a live account by the author.** Make your first API order one share.

## Safety rules built in

- Paper mode until you change it.
- Risk per trade: 1% of capital, counting charges. Daily loss stop: 2%. Total loss budget: 20%.
- At most 3 trades a day and 2 open positions. No leverage unless you raise `mis_leverage`.
- No new intraday entries after 15:00. Plans are flat by 15:10.
- Reward must be at least 1.5 times risk **after charges**.
- Option buying only, premium capped at 10% of capital. Option selling and delivery shorts are blocked.
- Orders need a ticket you approve by typing `YES <id>`. Tickets expire in 15 minutes and are
  refused if their contents change after approval.
- A hook blocks any broker MCP order tool that has no matching approved ticket.
- `dd.py kill on` stops everything. Only you can clear it, by deleting `trader/KILL`.

The approval step is a process control: Claude is instructed to pass only what you typed. Keep
Claude Code's own permission prompt for broker tools on "ask", never "always allow".

## What is and is not tested

- `python3 -m unittest discover -s tests -v` runs 31 offline tests on synthetic candles: charges,
  tick rounding, expiry dates, option maths, scanners, sizing, every gate rule, the ticket flow,
  the hook, and the paper broker.
- **Not tested by the author:** live Yahoo and Upstox data (the build machine had no market
  access), the news feed URLs, and the Upstox and Kite order adapters. Run `dd.py doctor --live`
  on your machine first.

## Things you must keep current

Rules in India change often. They live in `dalal/refdata.py` with their effective dates:

- **Charges** (STT, exchange, stamp, GST): table effective 1 April 2026. Check against a contract note.
- **Holidays:** only two dates are filled in. Add the NSE holiday list each year, or expiry dates will be wrong.
- **Lot sizes and expiry days:** Nifty 65, weekly expiry Tuesday; Sensex weekly Thursday; others monthly only.
- **Tick sizes** follow NSE price bands; your broker's instrument file is the authority.

See `docs/RULES.md` for where each number came from.

## Layout

```
dd.py                 entry point for every command
dalal/                the library (stdlib only)
  providers/          yahoo, csv, upstox, kite, paper, manual
skills/               16 skills (SKILL.md each)
agents/ commands/     sub-agents and slash commands
hooks/                order guard (blocks unapproved broker orders)
universe/             watchlists to scan
tests/                offline tests and fixtures
```

## Credits

Dalal Desk is new code, but its design draws on ideas from other open-source projects. See
`THIRD_PARTY_NOTICES.md`. Licence: MIT.
