"""Health check: what is configured, what works today, what is stale."""
import os
import sys
from datetime import date

from . import refdata, risk
from .providers import get_data


def run(cfg, live=False):
    r = refdata.rates()
    age = (date.today() - r["reviewed"]).days
    checks = {
        "python": sys.version.split()[0],
        "mode": cfg["mode"], "broker": cfg["broker"], "data": cfg["data"], "capital": cfg["capital"],
        "kill_switch": "ON" if risk.kill_path().exists() else "off",
        "rate_table": {"effective_from": str(r["effective_from"]), "last_reviewed": str(r["reviewed"]),
                       "days_since_review": age,
                       "status": "ok" if age <= 180 else "STALE: check STT and exchange charges"},
        "holidays_on_file": len(refdata.HOLIDAYS),
        "secrets": {k: ("set" if os.environ.get(k) else "missing") for k in
                    ("UPSTOX_ACCESS_TOKEN", "KITE_API_KEY", "KITE_ACCESS_TOKEN", "LIVE_TRADING")},
    }
    warnings = []
    if len(refdata.HOLIDAYS) < 10:
        warnings.append("Holiday list is incomplete; add the NSE list to refdata.HOLIDAYS for correct expiries.")
    if cfg["mode"] == "live":
        warnings.append("LIVE mode. API orders need a static IP registered with your broker (SEBI, April 2026).")
        if cfg["broker"] in ("upstox", "kite"):
            warnings.append("The Upstox and Kite order adapters were not live-tested by the author. "
                            "Place a 1-share test order first.")
    if "yahoo" in cfg["data"]:
        warnings.append("Yahoo data is delayed about 15 minutes: fine for swing, not for live intraday entries.")
    if live:
        data = get_data(cfg)
        probes = {}
        for sym in ("NIFTY", "SBIN"):
            try:
                probes[sym] = {"quote": data.quote(sym), "bars_5m": len(data.candles(sym, "5m", 5)),
                               "bars_1d": len(data.candles(sym, "1d", 30))}
            except Exception as e:  # noqa: BLE001
                probes[sym] = {"error": str(e)}
        checks["data_probe"] = probes
    checks["warnings"] = warnings
    return checks
