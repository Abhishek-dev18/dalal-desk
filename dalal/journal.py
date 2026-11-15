"""Trade journal: every trade, its exact charges, net P&L and R-multiple."""
import csv
import sys

from . import backtest, costs
from .util import IST, hhmm, ist, now, read_json, state_dir, write_json


def _path():
    return state_dir() / "journal.json"


def load():
    return read_json(_path(), [])


def save(trades):
    write_json(_path(), trades)


def find(trades, key):
    hits = [t for t in trades if t["id"].startswith(key) or (t["symbol"] == key.upper() and t["status"] == "open")]
    if len(hits) != 1:
        raise SystemExit(f"'{key}' matches {len(hits)} trades; use a ticket id prefix")
    return hits[0]


def open_trade(ticket, paper):
    trades = load()
    trades.append({
        "id": ticket["id"], "symbol": ticket["symbol"], "side": ticket["side"], "qty": ticket["qty"],
        "segment": ticket["segment"], "product": ticket["product"], "setup": ticket["setup"],
        "entry": ticket["entry"], "stop": ticket["stop"], "target": ticket["target"],
        "risk_per_share": ticket["risk_per_share"], "flat_by": ticket.get("flat_by"),
        "opened": now().isoformat(), "status": "open", "paper": paper,
    })
    save(trades)


def close_trade(key, price, reason="manual", when=None, profile="zerodha"):
    trades = load()
    t = find(trades, key)
    if t["status"] != "open":
        raise SystemExit("trade is already closed")
    rt = costs.round_trip(t["segment"], t["entry"], price, t["qty"], t["side"], profile)
    t.update(status="closed", exit=price, exit_reason=reason, closed=when or now().isoformat(),
             pnl_gross=rt["gross"], charges=rt["charges"], pnl_net=rt["net"],
             r_multiple=round(rt["net"] / (t["risk_per_share"] * t["qty"]), 2))
    save(trades)
    return t


def _scope(trades, paper):
    return [t for t in trades if bool(t.get("paper")) == paper]


def realised(trades, paper, since=None):
    total = 0.0
    for t in _scope(trades, paper):
        if t["status"] == "closed" and (since is None or t["closed"][:10] >= since):
            total += t["pnl_net"]
    return round(total, 2)


def stats(paper):
    closed = [t for t in _scope(load(), paper) if t["status"] == "closed"]
    if not closed:
        return {"closed_trades": 0, "paper": paper}
    wins = [t for t in closed if t["pnl_net"] > 0]
    by_setup = {}
    for t in closed:
        s = by_setup.setdefault(t["setup"], {"trades": 0, "net": 0.0, "r": 0.0})
        s["trades"] += 1
        s["net"] = round(s["net"] + t["pnl_net"], 2)
        s["r"] = round(s["r"] + t["r_multiple"], 2)
    return {
        "paper": paper, "closed_trades": len(closed), "win_rate_pct": round(len(wins) / len(closed) * 100, 1),
        "net_pnl": round(sum(t["pnl_net"] for t in closed), 2),
        "gross_pnl": round(sum(t["pnl_gross"] for t in closed), 2),
        "charges_paid": round(sum(t["charges"] for t in closed), 2),
        "avg_r": round(sum(t["r_multiple"] for t in closed) / len(closed), 2),
        "best": max(t["pnl_net"] for t in closed), "worst": min(t["pnl_net"] for t in closed),
        "by_setup": by_setup,
    }


def export_csv(stream=sys.stdout):
    cols = ["id", "symbol", "side", "qty", "segment", "setup", "entry", "stop", "target", "opened", "status",
            "exit", "exit_reason", "closed", "pnl_gross", "charges", "pnl_net", "r_multiple", "paper"]
    w = csv.DictWriter(stream, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for t in load():
        w.writerow(t)


def settle_paper(cfg, data):
    """Close open paper trades against real candles since they were opened."""
    from datetime import datetime
    results = []
    for t in [x for x in load() if x["status"] == "open" and x.get("paper")]:
        opened = datetime.fromisoformat(t["opened"]).timestamp()
        intraday = t["segment"] == "intraday"
        if t["segment"] == "options":
            results.append({"id": t["id"][:8], "symbol": t["symbol"],
                            "status": "open: option paper trades are closed by hand with journal close"})
            continue
        try:
            bars = data.candles(t["symbol"], "5m" if intraday else "1d", 10 if intraday else 60)
        except Exception as e:  # noqa: BLE001
            results.append({"id": t["id"][:8], "symbol": t["symbol"], "error": str(e)})
            continue
        if intraday:
            day = ist(opened).date()
            bars = [b for b in bars if b["t"] >= opened and ist(b["t"]).date() == day]
        else:
            bars = [b for b in bars if ist(b["t"]).date() > ist(opened).date()]
        exit_, reason, when = backtest.walk(bars, t["side"], t["entry"], t["stop"], t["target"], t.get("flat_by"))
        if intraday and reason == "open" and bars and (ist(bars[-1]["t"]).date() < now().date()
                                                       or hhmm(now().timestamp()) >= "15:30"):
            reason = "session_end"
        if reason == "open":
            results.append({"id": t["id"][:8], "symbol": t["symbol"], "status": "still open", "last": exit_})
            continue
        closed = close_trade(t["id"], round(exit_, 2), reason, datetime.fromtimestamp(when, IST).isoformat(),
                             cfg["brokerage"])
        results.append({"id": t["id"][:8], "symbol": t["symbol"], "exit": closed["exit"], "reason": reason,
                        "pnl_net": closed["pnl_net"], "r": closed["r_multiple"]})
    return results
