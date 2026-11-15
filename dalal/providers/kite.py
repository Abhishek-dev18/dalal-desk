"""Zerodha Kite Connect: order placement only (the free Personal plan has no data).

STATUS: written from the public Kite Connect v3 documentation. It has NOT been
run against a live account by the author. Place one 1-share test order yourself
before relying on it.

Needs KITE_API_KEY and KITE_ACCESS_TOKEN in .env (token expires 06:00 IST daily).
API orders also need your static IP registered with Zerodha (SEBI rule, April 2026).
"""
import json
import os
import urllib.parse
import urllib.request

API = "https://api.kite.trade"


class Kite:
    name = "kite"

    def __init__(self):
        self.key = os.environ.get("KITE_API_KEY")
        self.token = os.environ.get("KITE_ACCESS_TOKEN")
        if not (self.key and self.token):
            raise RuntimeError("KITE_API_KEY and KITE_ACCESS_TOKEN must be set in .env")

    def _req(self, path, form=None):
        headers = {"X-Kite-Version": "3", "Authorization": f"token {self.key}:{self.token}"}
        data = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(API + path, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.load(r)

    def _order(self, t, side, order_type, price, trigger=None):
        form = {
            "tradingsymbol": t["symbol"], "exchange": "NSE", "transaction_type": side,
            "order_type": order_type, "quantity": t["qty"], "product": t["product"],
            "price": price, "validity": "DAY", "tag": "dalal" + t["id"][:8],
        }
        if trigger is not None:
            form["trigger_price"] = trigger
        return self._req("/orders/regular", form)

    def place(self, t):
        if t["segment"] == "options":
            raise RuntimeError("option orders via Kite are not implemented; use broker 'manual'")
        exit_side = "SELL" if t["side"] == "BUY" else "BUY"
        entry = self._order(t, t["side"], "LIMIT", t["entry"])
        stop = self._order(t, exit_side, "SL", t["stop_limit"], t["stop"])
        return {"broker": "kite", "entry_order": entry, "stop_order": stop,
                "note": "Target is NOT placed. Set an alert or exit by hand."}

    def positions(self):
        return self._req("/portfolio/positions")["data"]["net"]
