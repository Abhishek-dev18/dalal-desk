"""Candles from local CSV files: <dir>/<SYMBOL>_<interval>.csv with columns t,o,h,l,c,v.

`t` is epoch seconds or an ISO time in IST (2026-11-13T09:15:00). Use this for
replays, tests, and data you exported from your broker.
"""
import csv
from datetime import datetime
from pathlib import Path

from ..util import IST, now


def _ts(v):
    try:
        return int(float(v))
    except ValueError:
        d = datetime.fromisoformat(v)
        return int((d if d.tzinfo else d.replace(tzinfo=IST)).timestamp())


class CsvDir:
    name = "csv"
    delayed = True

    def __init__(self, folder):
        self.folder = Path(folder)

    def candles(self, symbol, interval="5m", days=5):
        path = self.folder / f"{symbol}_{interval}.csv"
        if not path.exists():
            raise FileNotFoundError(str(path))
        cutoff = now().timestamp()
        bars = []
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                t = _ts(row["t"])
                if t > cutoff:
                    continue
                bars.append({"t": t, "o": float(row["o"]), "h": float(row["h"]), "l": float(row["l"]),
                             "c": float(row["c"]), "v": int(float(row["v"]))})
        bars.sort(key=lambda b: b["t"])
        start = cutoff - (days + 1) * 86400
        return [b for b in bars if b["t"] >= start]

    def quote(self, symbol):
        for interval in ("5m", "1d"):
            try:
                return self.candles(symbol, interval, 10)[-1]["c"]
            except (FileNotFoundError, IndexError):
                continue
        raise FileNotFoundError(f"no csv for {symbol}")
