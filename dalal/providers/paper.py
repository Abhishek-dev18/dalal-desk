"""Paper broker: no real orders. Fills at the entry price and is settled later
against real candles by `dd.py paper settle`."""
from ..util import now


class Paper:
    name = "paper"

    def __init__(self, cfg):
        self.cfg = cfg

    def place(self, t):
        return {"broker": "paper", "filled": True, "fill_price": t["entry"], "time": now().isoformat(),
                "note": "Simulated fill at the entry price. Real fills can be worse."}

    def positions(self):
        from .. import journal
        return [t for t in journal.load() if t["status"] == "open" and t.get("paper")]
