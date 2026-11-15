"""Manual broker: prints the exact orders for you to type into your broker app.

This is the right choice on a laptop without a static IP.
"""


class Manual:
    name = "manual"

    def __init__(self, cfg):
        self.cfg = cfg

    def place(self, t):
        exit_side = "SELL" if t["side"] == "BUY" else "BUY"
        return {
            "broker": "manual",
            "place_these_orders_yourself": [
                {"step": 1, "order": f"{t['side']} {t['qty']} {t['symbol']}", "type": "LIMIT",
                 "price": t["entry"], "product": t["product"]},
                {"step": 2, "order": f"{exit_side} {t['qty']} {t['symbol']}", "type": "SL",
                 "trigger": t["stop"], "price": t["stop_limit"], "product": t["product"],
                 "when": "right after the entry fills"},
                {"step": 3, "order": f"{exit_side} {t['qty']} {t['symbol']}", "type": "LIMIT or alert",
                 "price": t["target"], "when": "cancel the stop order when this fills"},
            ],
            "after_exit": f"record it: dd.py journal close {t['id'][:8]} --price <your exit price>",
        }

    def positions(self):
        return []
