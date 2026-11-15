"""Order tickets: propose -> you approve -> place. Nothing is placed without an
approved, unexpired ticket whose contents still match its hash."""
import hashlib
import json
import os
from datetime import datetime, timedelta

from . import journal, risk
from .providers import get_broker
from .util import now, read_json, state_dir, write_json

FIELDS = ("symbol", "side", "qty", "segment", "product", "setup", "entry", "stop", "stop_limit", "target",
          "risk_per_share", "flat_by", "created")


def _path():
    return state_dir() / "tickets.json"


def load():
    return read_json(_path(), {})


def digest(t):
    body = json.dumps({k: t.get(k) for k in FIELDS}, sort_keys=True)
    return hashlib.sha256(body.encode()).hexdigest()


def find(tickets, key):
    hits = [t for i, t in tickets.items() if i.startswith(key)]
    if len(hits) != 1:
        raise SystemExit(f"'{key}' matches {len(hits)} tickets")
    return hits[0]


def create(plan, sized, cfg):
    g = risk.gate(plan, sized, cfg)
    if g["verdict"] != "PASS":
        return {"error": "risk gate BLOCKED this trade", "failed": g["failed"], "gate": g}
    t = {k: plan.get(k) for k in FIELDS}
    t["qty"] = sized["qty"]
    t["created"] = now().isoformat()
    t["id"] = digest(t)
    t.update(status="proposed", max_loss=sized["max_loss"], net_profit_at_target=sized["net_profit_at_target"],
             expires=(now() + timedelta(minutes=cfg["ticket_ttl_minutes"])).isoformat(),
             mode=cfg["mode"], broker=cfg["broker"])
    tickets = load()
    tickets[t["id"]] = t
    write_json(_path(), tickets)
    return show(t)


def show(t):
    exit_side = "SELL" if t["side"] == "BUY" else "BUY"
    return {
        "ticket": t["id"][:8], "status": t["status"], "mode": t["mode"], "broker": t["broker"],
        "plain": (f"{t['side']} {t['qty']} {t['symbol']} at Rs {t['entry']} ({t['product']}). "
                  f"Stop: {exit_side} at Rs {t['stop']}. Target: Rs {t['target']}. "
                  f"Worst case about Rs {t['max_loss']} lost; about Rs {t['net_profit_at_target']} made at target, "
                  f"after charges."),
        "expires": t["expires"],
        "to_approve": f"the user must type exactly: YES {t['id'][:8]}",
    }


def approve(key, typed):
    tickets = load()
    t = find(tickets, key)
    if t["status"] != "proposed":
        raise SystemExit(f"ticket is {t['status']}, not proposed")
    if now() > datetime.fromisoformat(t["expires"]):
        t["status"] = "expired"
        write_json(_path(), tickets)
        raise SystemExit("ticket expired; build a fresh plan")
    if typed.strip() != f"YES {t['id'][:8]}":
        raise SystemExit(f"approval text must be exactly: YES {t['id'][:8]}")
    t.update(status="approved", approved_at=now().isoformat())
    write_json(_path(), tickets)
    return show(t)


def execute(key, cfg):
    tickets = load()
    t = find(tickets, key)
    if t["status"] != "approved":
        raise SystemExit(f"ticket is {t['status']}; it must be approved first")
    if now() > datetime.fromisoformat(t["expires"]):
        t["status"] = "expired"
        write_json(_path(), tickets)
        raise SystemExit("ticket expired; build a fresh plan")
    if digest(t) != t["id"]:
        raise SystemExit("ticket contents changed after approval; refusing")
    if risk.kill_path().exists():
        raise SystemExit("kill switch is on (trader/KILL); refusing")
    if risk.budget(cfg)["locked"]:
        raise SystemExit("loss budget is locked; no new trades")
    if cfg["mode"] == "research":
        raise SystemExit("mode is research; no orders")
    if cfg["mode"] != t["mode"] or cfg["broker"] != t["broker"]:
        raise SystemExit("mode or broker changed since the ticket was built; refusing")
    if cfg["mode"] == "live" and cfg["broker"] in ("upstox", "kite") and os.environ.get("LIVE_TRADING") != "1":
        raise SystemExit("live API orders need LIVE_TRADING=1 in .env")
    result = get_broker(cfg).place(t)
    t.update(status="placed", placed_at=now().isoformat(), broker_result=result)
    write_json(_path(), tickets)
    journal.open_trade(t, paper=cfg["mode"] != "live")
    return {"ticket": t["id"][:8], "status": "placed", "result": result}


def approved_for(symbol_blob, qty_values):
    """Used by the order-guard hook: is there an approved, live ticket matching this order?"""
    for t in load().values():
        if t["status"] != "approved" or now() > datetime.fromisoformat(t["expires"]):
            continue
        if t["symbol"] in symbol_blob and t["qty"] in qty_values:
            return t
    return None
