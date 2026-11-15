"""Dated India market rules. Every table carries the date it took effect.

These change. Check them against your broker's contract note and the NSE
circulars before trusting the numbers; `dd.py doctor` warns when they are old.
"""
from datetime import date, timedelta

# Statutory + exchange rates, in percent of traded value unless noted.
# Source notes are in docs/RULES.md.
RATES = [
    {
        "effective_from": date(2026, 4, 1),
        "reviewed": date(2026, 11, 15),
        "stt": {  # (buy %, sell %)
            "delivery": (0.1, 0.1),
            "intraday": (0.0, 0.025),
            "futures": (0.0, 0.05),
            "options": (0.0, 0.15),
        },
        "exchange": {"delivery": 0.00307, "intraday": 0.00307, "futures": 0.00183, "options": 0.03553},
        "stamp_buy": {"delivery": 0.015, "intraday": 0.003, "futures": 0.002, "options": 0.003},
        "sebi": 0.0001,          # Rs 10 per crore
        "gst": 18.0,             # on brokerage + exchange + SEBI fee
        "dp_sell": 15.34,        # per scrip per day, delivery sells
    },
]

LOTS = {  # effective from the January 2026 contracts
    "NIFTY": 65, "BANKNIFTY": 30, "FINNIFTY": 60, "MIDCPNIFTY": 120, "SENSEX": 20,
}

# Weekday trading holidays, equity and F&O. Source: NSE circulars NSE/FAOP/71777
# (12 Dec 2025) and NSE/FAOP/72262 (15 Jan 2026 election holiday).
# The 2027 list was not yet published when this was written: add it from the NSE circular.
HOLIDAYS = {
    date(2026, 1, 15),   # Municipal Corporation Election, Maharashtra
    date(2026, 1, 26),   # Republic Day
    date(2026, 3, 3),    # Holi
    date(2026, 3, 26),   # Shri Ram Navami
    date(2026, 3, 31),   # Shri Mahavir Jayanti
    date(2026, 4, 3),    # Good Friday
    date(2026, 4, 14),   # Dr. Baba Saheb Ambedkar Jayanti
    date(2026, 5, 1),    # Maharashtra Day
    date(2026, 5, 28),   # Bakri Id
    date(2026, 6, 26),   # Muharram
    date(2026, 9, 14),   # Ganesh Chaturthi
    date(2026, 10, 2),   # Mahatma Gandhi Jayanti
    date(2026, 10, 20),  # Dussehra
    date(2026, 11, 10),  # Diwali-Balipratipada
    date(2026, 11, 24),  # Prakash Gurpurb Sri Guru Nanak Dev
    date(2026, 12, 25),  # Christmas
}
HOLIDAY_YEARS = {2026}

WEEKLY_EXPIRY_WEEKDAY = {"NIFTY": 1, "SENSEX": 3}          # Tue, Thu
MONTHLY_EXPIRY_WEEKDAY = {"NIFTY": 1, "BANKNIFTY": 1, "FINNIFTY": 1, "MIDCPNIFTY": 1, "SENSEX": 3}


def rates(on=None):
    on = on or date.today()
    best = RATES[0]
    for r in RATES:
        if r["effective_from"] <= on:
            best = r
    return best


def tick_size(price):
    """NSE cash tick by price band. The broker's instrument file is the authority."""
    if price < 250:
        return 0.01
    if price < 1000:
        return 0.05
    if price < 5000:
        return 0.10
    if price < 10000:
        return 0.50
    if price < 20000:
        return 1.00
    return 5.00


def round_to_tick(price, direction="nearest", tick=None):
    tick = tick or tick_size(price)
    n = price / tick
    if direction == "up":
        k = int(n) if abs(n - int(n)) < 1e-9 else int(n) + 1
    elif direction == "down":
        k = int(n + 1e-9)
    else:
        k = int(round(n))
    return round(k * tick, 2)


def on_tick(price, tick=None):
    tick = tick or tick_size(price)
    n = price / tick
    return abs(n - round(n)) < 1e-6


def is_trading_day(d):
    return d.weekday() < 5 and d not in HOLIDAYS


def prev_trading_day(d):
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def weekly_expiry(underlying, on=None):
    u = underlying.upper()
    if u not in WEEKLY_EXPIRY_WEEKDAY:
        raise ValueError(f"{u} has no weekly expiry (monthly only)")
    on = on or date.today()
    d = on
    while True:
        target = d + timedelta(days=(WEEKLY_EXPIRY_WEEKDAY[u] - d.weekday()) % 7)
        exp = prev_trading_day(target)
        if exp >= on:
            return exp
        d = target + timedelta(days=1)


def monthly_expiry(underlying, year, month):
    u = underlying.upper()
    wd = MONTHLY_EXPIRY_WEEKDAY.get(u, 1)
    d = date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)
    while d.weekday() != wd:
        d -= timedelta(days=1)
    return prev_trading_day(d)
