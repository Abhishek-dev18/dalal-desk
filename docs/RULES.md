# Where the numbers come from

Everything here was gathered in November 2026 and should be rechecked before you rely on it.
The values live in `dalal/refdata.py`.

## Charges (effective 1 April 2026)

| Item | Delivery | Intraday | Futures | Options |
|---|---|---|---|---|
| STT | 0.1% buy and sell | 0.025% sell | 0.05% sell | 0.15% of premium, sell |
| NSE transaction charge | 0.00307% | 0.00307% | 0.00183% | 0.03553% of premium |
| Stamp duty (buy) | 0.015% | 0.003% | 0.002% | 0.003% |
| SEBI fee | Rs 10 per crore | same | same | same |
| GST | 18% of brokerage + exchange + SEBI fee | same | same | same |
| DP charge | about Rs 15.34 per scrip on sell | none | none | none |

- STT on futures and options rose on 1 April 2026 (Finance Act 2026; NSE circular NSE/FATAX/73524).
- NSE cash transaction charge of 0.00307% is the rate Zerodha lists from 1 March 2026. Some tables
  still show 0.00297%.
- Brokerage profile `zerodha`: delivery free; intraday and futures 0.03% or Rs 20 an order,
  whichever is lower; options Rs 20 an order.

## Contracts

- Lot sizes from the January 2026 contracts: Nifty 65, Bank Nifty 30, Fin Nifty 60, Midcap Nifty 120
  (NSE circular NSE/FAOP/70616). Sensex 20.
- Weekly expiries: Nifty on Tuesday, Sensex on Thursday. Other indices are monthly only, expiring
  on the last Tuesday. A holiday moves expiry to the previous trading day.

## Ticks

NSE cash tick by price: under 250 is 0.01; 250 to 1,000 is 0.05; 1,000 to 5,000 is 0.10;
5,000 to 10,000 is 0.50; 10,000 to 20,000 is 1.00; above that 5.00. Confirm against your broker's
instrument file, which is the authority.

## Regulation

- SEBI's retail algo framework applies fully from 1 April 2026: API orders need a static IP
  registered with the broker, OAuth with two-factor login, and a daily logout. Strategies sending
  10 or more orders a second must be registered. Dalal Desk sends two orders per ticket.

## Tax (Tax Year 2026-27)

- Intraday equity: speculative business income at slab rates; losses carry forward 4 years.
- F&O: non-speculative business income; losses carry forward 8 years.
- Listed equity: short-term gains 20%; long-term 12.5% above Rs 1.25 lakh.
- Have a chartered accountant confirm before filing.
