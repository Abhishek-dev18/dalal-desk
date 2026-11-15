"""Yahoo Finance chart endpoint. Free, no key, delayed about 15 minutes.

Good for swing work and for studying intraday history (5m bars go back ~60 days).
Not good enough to time a live intraday entry.
"""
import json
import time
import urllib.parse
import urllib.request

INDEX = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "INDIAVIX": "^INDIAVIX", "SENSEX": "^BSESN"}
MAX_DAYS = {"1m": 7, "5m": 59, "15m": 59, "1h": 700, "1d": 3650}


def ticker(symbol):
    s = symbol.upper()
    if s in INDEX:
        return INDEX[s]
    if s.startswith("^") or s.endswith((".NS", ".BO")):
        return s
    return s + ".NS"


class Yahoo:
    name = "yahoo"
    delayed = True

    def _chart(self, symbol, interval, days):
        days = min(days, MAX_DAYS.get(interval, 59))
        end = int(time.time()) + 86400
        params = urllib.parse.urlencode({
            "interval": interval, "period1": end - (days + 1) * 86400, "period2": end,
            "includePrePost": "false",
        })
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(ticker(symbol))}?{params}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
        res = data["chart"]["result"]
        if not res:
            raise ValueError(str(data["chart"].get("error")))
        return res[0]

    def candles(self, symbol, interval="5m", days=5):
        res = self._chart(symbol, interval, days)
        q = res["indicators"]["quote"][0]
        bars = []
        for i, t in enumerate(res.get("timestamp") or []):
            o, h, l, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i]
            if None in (o, h, l, c):
                continue
            bars.append({"t": int(t), "o": float(o), "h": float(h), "l": float(l), "c": float(c), "v": int(v or 0)})
        return bars

    def quote(self, symbol):
        return float(self._chart(symbol, "1d", 5)["meta"]["regularMarketPrice"])
