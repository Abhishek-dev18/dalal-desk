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
        "holiday_years_on_file": sorted(refdata.HOLIDAY_YEARS),
        "secrets": {k: ("set" if os.environ.get(k) else "missing") for k in
                    ("UPSTOX_ACCESS_TOKEN", "KITE_API_KEY", "KITE_ACCESS_TOKEN", "LIVE_TRADING")},
    }
    warnings = []
    today = date.today()
    missing = [y for y in (today.year, today.year + 1) if y not in refdata.HOLIDAY_YEARS
               and (y == today.year or today.month >= 11)]
    if missing:
        warnings.append(f"No NSE holiday list for {missing}; add it to refdata.HOLIDAYS or expiry dates may be wrong.")
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
        from .providers import _make_data
        per = {}
        for name in cfg["data"]:
            try:
                d = _make_data(name, cfg)
                per[name] = {"NIFTY": d.quote("NIFTY"), "SBIN": d.quote("SBIN"), "ok": True}
            except Exception as e:  # noqa: BLE001
                per[name] = {"ok": False, "error": str(e)[:300]}
        checks["each_provider"] = per
    checks["warnings"] = warnings
    return checks
