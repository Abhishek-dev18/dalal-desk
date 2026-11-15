"""Pick data and broker adapters from config.

Data adapters implement:   candles(symbol, interval, days) -> [{t,o,h,l,c,v}], quote(symbol) -> float
Broker adapters implement: place(ticket) -> dict, positions() -> list
"""


class DataError(Exception):
    pass


def _make_data(name, cfg):
    if name == "yahoo":
        from .yahoo import Yahoo
        return Yahoo()
    if name == "csv":
        from .csvdir import CsvDir
        return CsvDir(cfg["csv_dir"])
    if name == "upstox":
        from .upstox import Upstox
        return Upstox()
    raise SystemExit(f"unknown data provider: {name}")


class Chain:
    """Try each configured provider in order; first one that answers wins."""

    def __init__(self, cfg):
        self.names = list(cfg["data"])
        self.cfg = cfg
        self._made = {}

    def _get(self, name):
        if name not in self._made:
            self._made[name] = _make_data(name, self.cfg)
        return self._made[name]

    def _try(self, method, *args):
        errors = []
        for name in self.names:
            try:
                result = getattr(self._get(name), method)(*args)
                if result:
                    return result
                errors.append(f"{name}: empty")
            except Exception as e:  # noqa: BLE001 - report and fall through
                errors.append(f"{name}: {e}")
        raise DataError("; ".join(errors))

    def candles(self, symbol, interval="5m", days=5):
        return self._try("candles", symbol.upper(), interval, days)

    def quote(self, symbol):
        return self._try("quote", symbol.upper())


def get_data(cfg):
    return Chain(cfg)


def get_broker(cfg):
    name = cfg["broker"]
    if name == "paper":
        from .paper import Paper
        return Paper(cfg)
    if name == "manual":
        from .manual import Manual
        return Manual(cfg)
    if name == "upstox":
        from .upstox import Upstox
        return Upstox()
    if name == "kite":
        from .kite import Kite
        return Kite()
    raise SystemExit(f"unknown broker: {name}")
