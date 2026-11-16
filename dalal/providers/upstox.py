"""Upstox: real-time data and order placement.

STATUS: written from the public Upstox API documentation. It has NOT been run
against a live account by the author. Run `dd.py doctor --live` and place one
1-share test order yourself before relying on it.

Needs UPSTOX_ACCESS_TOKEN in .env (the token expires every day at 03:30 IST).
API orders also need your static IP registered with Upstox (SEBI rule, April 2026).
"""
import gzip
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import timedelta
from pathlib import Path

from ..util import now, state_dir

API = "https://api.upstox.com"
ORDER_API = "https://api-hft.upstox.com"
INSTRUMENTS = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
INDEX_KEYS = {"NIFTY": "NSE_INDEX|Nifty 50", "BANKNIFTY": "NSE_INDEX|Nifty Bank", "INDIAVIX": "NSE_INDEX|India VIX"}
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) dalal-desk/0.2"
UNITS = {"1m": ("minutes", "1"), "5m": ("minutes", "5"), "15m": ("minutes", "15"), "1d": ("days", "1")}


class Upstox:
    name = "upstox"
    delayed = False

    def __init__(self):
        self.token = os.environ.get("UPSTOX_ACCESS_TOKEN")
        if not self.token:
            raise RuntimeError("UPSTOX_ACCESS_TOKEN is not set in .env")
        self._keys = None

    def _req(self, url, body=None):
        headers = {"Accept": "application/json", "Authorization": f"Bearer {self.token}", "User-Agent": UA}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raw = e.read()[:2000].decode("utf-8", "replace")
            try:
                errs = json.loads(raw).get("errors") or []
                detail = "; ".join(f"{x.get('errorCode')}: {x.get('message')}" for x in errs)[:300]
            except Exception:  # noqa: BLE001
                detail = "non-JSON reply (a firewall, not the API): " + " ".join(raw.split())[:160]
            raise RuntimeError(f"Upstox HTTP {e.code} {detail}".strip()) from None

    def instrument_key(self, symbol):
        if symbol in INDEX_KEYS:
            return INDEX_KEYS[symbol]
        if self._keys is None:
            cache = Path(state_dir()) / "upstox_instruments.json"
            if cache.exists() and now().timestamp() - cache.stat().st_mtime < 86400:
                self._keys = json.loads(cache.read_text())
            else:
                req = urllib.request.Request(INSTRUMENTS, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=60) as r:
                    rows = json.loads(gzip.decompress(r.read()))
                self._keys = {x["trading_symbol"]: x["instrument_key"] for x in rows
                              if x.get("segment") == "NSE_EQ" and x.get("instrument_type") == "EQ"}
                cache.write_text(json.dumps(self._keys))
        if symbol not in self._keys:
            raise KeyError(f"{symbol} not found in Upstox NSE_EQ instruments")
        return self._keys[symbol]

    def candles(self, symbol, interval="5m", days=5):
        unit, n = UNITS[interval]
        key = urllib.parse.quote(self.instrument_key(symbol))
        today = now().date()
        rows = []
        if interval != "1d":
            rows += self._req(f"{API}/v3/historical-candle/intraday/{key}/{unit}/{n}")["data"]["candles"]
        frm = today - timedelta(days=days + 1)
        rows += self._req(f"{API}/v3/historical-candle/{key}/{unit}/{n}/{today}/{frm}")["data"]["candles"]
        from datetime import datetime
        bars = {}
        for c in rows:
            t = int(datetime.fromisoformat(c[0]).timestamp())
            bars[t] = {"t": t, "o": float(c[1]), "h": float(c[2]), "l": float(c[3]), "c": float(c[4]), "v": int(c[5])}
        return [bars[t] for t in sorted(bars)]

    def quote(self, symbol):
        key = self.instrument_key(symbol)
        data = self._req(f"{API}/v2/market-quote/ltp?instrument_key={urllib.parse.quote(key)}")["data"]
        return float(next(iter(data.values()))["last_price"])

    # ---- broker side ----
    def _order(self, t, side, order_type, price, trigger=0.0):
        body = {
            "quantity": t["qty"], "product": "I" if t["product"] == "MIS" else "D", "validity": "DAY",
            "price": price, "tag": "dalal-" + t["id"][:8], "instrument_token": self.instrument_key(t["symbol"]),
            "order_type": order_type, "transaction_type": side, "disclosed_quantity": 0,
            "trigger_price": trigger, "is_amo": False,
        }
        return self._req(f"{ORDER_API}/v2/order/place", body)

    def place(self, t):
        if t["segment"] == "options":
            raise RuntimeError("option orders via Upstox are not implemented; use broker 'manual'")
        exit_side = "SELL" if t["side"] == "BUY" else "BUY"
        entry = self._order(t, t["side"], "LIMIT", t["entry"])
        stop = self._order(t, exit_side, "SL", t["stop_limit"], t["stop"])
        return {"broker": "upstox", "entry_order": entry, "stop_order": stop,
                "note": "Target is NOT placed. Set an alert or exit by hand."}

    def positions(self):
        return self._req(f"{API}/v2/portfolio/short-term-positions")["data"]
