"""Position sizing, the PASS/BLOCK gate, the loss budget and the kill switch."""
from . import costs, journal
from .refdata import on_tick
from .util import hhmm, now, state_dir


def kill_path():
    return state_dir() / "KILL"


def is_paper(cfg):
    return cfg["mode"] != "live"


def budget(cfg):
    trades = journal.load()
    paper = is_paper(cfg)
    today = now().date().isoformat()
    cap = cfg["capital"]
    day = journal.realised(trades, paper, today)
    total = journal.realised(trades, paper)
    day_limit = cap * cfg["daily_loss_stop_pct"] / 100
    total_limit = cap * cfg["total_loss_budget_pct"] / 100
    scope = journal._scope(trades, paper)
    return {
        "mode": cfg["mode"], "capital": cap,
        "risk_per_trade": round(cap * cfg["risk_per_trade_pct"] / 100, 2),
        "today_pnl": day, "daily_loss_limit": -day_limit, "daily_room_left": round(day_limit + min(day, 0), 2),
        "total_pnl": total, "total_loss_budget": -total_limit,
        "total_room_left": round(total_limit + min(total, 0), 2),
        "trades_today": sum(1 for t in scope if t["opened"][:10] == today),
        "open_positions": sum(1 for t in scope if t["status"] == "open"),
        "open_value": round(sum(t["entry"] * t["qty"] for t in scope if t["status"] == "open"), 2),
        "locked": day <= -day_limit or total <= -total_limit or kill_path().exists(),
    }


def warn_mode(plan, cfg):
    """Options with option_risk_limit = warn: per-trade risk and the premium cap only warn."""
    return plan["segment"] == "options" and cfg.get("option_risk_limit", "block") == "warn"


def _size_warn(plan, cfg, b):
    """One lot, if the cash is there; every limit it breaks becomes a warning, not a block."""
    entry, stop, side, lot = plan["entry"], plan["stop"], plan["side"], plan.get("lot") or 1
    buying_power = max(cfg["capital"] - b["open_value"], 0)
    result = {"symbol": plan["symbol"], "qty": 0, "lot": lot, "risk_budget": b["risk_per_trade"],
              "buying_power": round(buying_power, 2), "risk_mode": "warn"}
    if entry * lot > buying_power:
        result["reason"] = f"one lot costs Rs {entry * lot:.0f}, more than the Rs {buying_power:.0f} cash left"
        return result
    qty = lot
    buy, sell = (entry, stop) if side == "BUY" else (stop, entry)
    loss_cost = costs.charges("options", buy * qty, sell * qty, cfg["brokerage"])["total"]
    win = costs.round_trip("options", entry, plan["target"], qty, side, cfg["brokerage"])
    max_loss = plan["risk_per_share"] * qty + loss_cost
    cap = cfg["capital"]
    premium = entry * qty
    warnings = []
    if max_loss > b["risk_per_trade"] + 0.01:
        warnings.append(f"Loss at the stop is Rs {max_loss:.0f} ({max_loss / cap * 100:.1f}% of capital), "
                        f"{max_loss / b['risk_per_trade']:.1f}x your Rs {b['risk_per_trade']:.0f} per-trade limit")
    if max_loss > b["daily_room_left"]:
        warnings.append(f"A stop-out alone uses more than today's Rs {b['daily_room_left']:.0f} loss room "
                        "and locks trading for the day")
    premium_cap = cap * cfg["max_option_premium_pct"] / 100
    if premium > premium_cap:
        warnings.append(f"Premium Rs {premium:.0f} is above the {cfg['max_option_premium_pct']:g}% "
                        f"cap (Rs {premium_cap:.0f})")
    warnings.append(f"Worst case: premium goes to zero, Rs {premium:.0f} ({premium / cap * 100:.1f}% of capital)")
    result.update(qty=qty, position_value=round(premium, 2), max_loss=round(max_loss, 2),
                  net_profit_at_target=win["net"], charges_if_stopped=loss_cost, charges_if_target=win["charges"],
                  net_reward_risk=round(win["net"] / max_loss, 2),
                  pct_of_capital_at_risk=round(max_loss / cap * 100, 2),
                  worst_case=round(premium, 2), worst_case_pct=round(premium / cap * 100, 2),
                  warnings=warnings)
    return result


def size(plan, cfg):
    """Largest quantity whose loss at the stop, including charges, fits the per-trade risk."""
    b = budget(cfg)
    if warn_mode(plan, cfg):
        return _size_warn(plan, cfg, b)
    risk_rupees = min(b["risk_per_trade"], max(b["daily_room_left"], 0))
    seg, entry, stop, rps = plan["segment"], plan["entry"], plan["stop"], plan["risk_per_share"]
    lot = plan.get("lot") or 1
    leverage = cfg["mis_leverage"] if seg == "intraday" else 1.0
    buying_power = max(cfg["capital"] * leverage - b["open_value"], 0)
    if seg == "options":
        buying_power = min(buying_power, cfg["capital"] * cfg["max_option_premium_pct"] / 100)
    qty = int(min(risk_rupees / rps, buying_power / entry) // lot * lot)
    while qty > 0:
        buy, sell = (entry, stop) if plan["side"] == "BUY" else (stop, entry)
        cost = costs.charges(seg, buy * qty, sell * qty, cfg["brokerage"])["total"]
        if rps * qty + cost <= risk_rupees:
            break
        qty -= lot
    qty = max(qty, 0)
    result = {"symbol": plan["symbol"], "qty": qty, "lot": lot, "risk_budget": round(risk_rupees, 2),
              "buying_power": round(buying_power, 2)}
    if qty == 0:
        if seg == "options" and entry * lot > buying_power:
            why = f"one lot costs Rs {entry * lot:.0f}, above the Rs {buying_power:.0f} premium cap"
        elif rps * lot > risk_rupees:
            why = f"one {'lot' if lot > 1 else 'share'} risks Rs {rps * lot:.0f}, above the Rs {risk_rupees:.0f} risk budget"
        elif risk_rupees <= 0 or buying_power <= 0:
            why = "no buying power or loss budget left"
        else:
            buy, sell = (entry, stop) if plan["side"] == "BUY" else (stop, entry)
            one = rps * lot + costs.charges(seg, buy * lot, sell * lot, cfg["brokerage"])["total"]
            why = (f"one {'lot' if lot > 1 else 'share'} loses Rs {one:.0f} at the stop including charges, "
                   f"above the Rs {risk_rupees:.0f} risk budget")
        result["reason"] = why
        return result
    buy, sell = (entry, stop) if plan["side"] == "BUY" else (stop, entry)
    loss_cost = costs.charges(seg, buy * qty, sell * qty, cfg["brokerage"])["total"]
    win = costs.round_trip(seg, entry, plan["target"], qty, plan["side"], cfg["brokerage"])
    max_loss = rps * qty + loss_cost
    result.update(position_value=round(entry * qty, 2), max_loss=round(max_loss, 2),
                  net_profit_at_target=win["net"], charges_if_stopped=loss_cost, charges_if_target=win["charges"],
                  net_reward_risk=round(win["net"] / max_loss, 2),
                  pct_of_capital_at_risk=round(max_loss / cfg["capital"] * 100, 2))
    return result


def gate(plan, sized, cfg):
    """Every check must pass. One failure blocks the trade."""
    b = budget(cfg)
    checks = []

    def check(name, ok, detail):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    t = hhmm(now().timestamp())
    seg, side = plan["segment"], plan["side"]
    check("kill_switch", not kill_path().exists(), "trader/KILL exists" if kill_path().exists() else "off")
    check("mode", cfg["mode"] != "research", f"mode is {cfg['mode']}")
    check("segment_allowed", seg in ("intraday", "delivery", "options"), seg)
    check("no_option_selling", not (seg == "options" and side == "SELL"), "only option buying is allowed")
    check("options_enabled", seg != "options" or cfg["allow_option_buying"], "allow_option_buying")
    check("no_delivery_shorts", not (seg == "delivery" and side == "SELL"), "cannot short in delivery")
    check("daily_loss_stop", b["today_pnl"] > b["daily_loss_limit"],
          f"today {b['today_pnl']} vs limit {b['daily_loss_limit']}")
    check("total_loss_budget", b["total_pnl"] > b["total_loss_budget"],
          f"total {b['total_pnl']} vs budget {b['total_loss_budget']}")
    check("trades_per_day", b["trades_today"] < cfg["max_trades_per_day"],
          f"{b['trades_today']} of {cfg['max_trades_per_day']} used")
    check("open_positions", b["open_positions"] < cfg["max_open_positions"],
          f"{b['open_positions']} of {cfg['max_open_positions']} open")
    check("quantity", sized.get("qty", 0) > 0, sized.get("reason", f"qty {sized.get('qty')}"))
    if sized.get("qty", 0) > 0:
        if not warn_mode(plan, cfg):
            check("max_loss", sized["max_loss"] <= b["risk_per_trade"] + 0.01,
                  f"Rs {sized['max_loss']} vs Rs {b['risk_per_trade']}")
        check("net_reward_risk", sized["net_reward_risk"] >= cfg["min_reward_risk"],
              f"{sized['net_reward_risk']} after charges vs minimum {cfg['min_reward_risk']}")
        check("position_size", sized["position_value"] <= sized["buying_power"] + 0.01,
              f"Rs {sized['position_value']} vs Rs {sized['buying_power']}")
    if seg == "intraday":
        lo, hi = cfg["entry_window"]
        check("entry_window", lo <= t <= hi, f"now {t}, window {lo}-{hi}")
    if seg != "options":
        check("tick_grid", all(on_tick(plan[k]) for k in ("entry", "stop", "target")), "entry/stop/target on tick")
    blocked = [c for c in checks if not c["ok"]]
    out = {"verdict": "BLOCK" if blocked else "PASS", "failed": [c["check"] for c in blocked], "checks": checks}
    if warn_mode(plan, cfg):
        out["risk_mode"] = "warn"
        out["warnings"] = sized.get("warnings", [])
    return out
