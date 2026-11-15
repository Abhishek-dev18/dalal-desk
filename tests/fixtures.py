"""Synthetic but realistic-looking candles so every test runs offline and repeatably."""
import csv
import random
from datetime import date, datetime, time, timedelta
from pathlib import Path

from dalal.util import IST

LAST_DAY = date(2026, 11, 13)


def _weekdays_back(end, n):
    days, d = [], end
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return days[::-1]


def _write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t", "o", "h", "l", "c", "v"])
        w.writerows(rows)


def build(folder, symbols=("TEST", "NIFTY", "AAA", "BBB"), seed=1):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    for k, sym in enumerate(symbols):
        rng = random.Random(seed + k)
        days = _weekdays_back(LAST_DAY, 360)
        price = 300.0 + 100 * k
        daily, intra = [], []
        for i, d in enumerate(days):
            o = price * (1 + rng.gauss(0.0008, 0.004))
            if i < 300:
                c = o * (1 + rng.gauss(0.0008, 0.01))
                h, l = max(o, c) * (1 + abs(rng.gauss(0, 0.004))), min(o, c) * (1 - abs(rng.gauss(0, 0.004)))
                v = rng.randint(2_000_000, 6_000_000)
            else:
                p, hi, lo, v = o, o, o, 0
                start = datetime.combine(d, time(9, 15), IST)
                for j in range(75):
                    bo = p
                    bc = bo * (1 + rng.gauss(0, 0.004 if j < 3 else 0.0015))
                    bh = max(bo, bc) * (1 + abs(rng.gauss(0, 0.0007)))
                    bl = min(bo, bc) * (1 - abs(rng.gauss(0, 0.0007)))
                    bv = rng.randint(20_000, 80_000)
                    intra.append([int((start + timedelta(minutes=5 * j)).timestamp()),
                                  round(bo, 2), round(bh, 2), round(bl, 2), round(bc, 2), bv])
                    p, hi, lo, v = bc, max(hi, bh), min(lo, bl), v + bv
                c, h, l = p, hi, lo
            ts = int(datetime.combine(d, time(9, 15), IST).timestamp())
            daily.append([ts, round(o, 2), round(h, 2), round(l, 2), round(c, 2), v])
            price = c
        _write(folder / f"{sym}_1d.csv", daily)
        _write(folder / f"{sym}_5m.csv", intra)
