"""Time machine: replay the rest of today 10,000 times.

Each simulated 5-minute candle is drawn from the stock's own candles at the same
time of day on earlier sessions. The seed is fixed, so the same inputs give the
same answer. This shows the spread of outcomes; it does not predict today.
"""
import random

from . import backtest
from .util import closed_only, hhmm, sessions


def _ratio_table(days):
    table = {}
    for _, bars in days:
        prev = None
        for b in bars:
            base = prev["c"] if prev else b["o"]
            if base:
                table.setdefault(hhmm(b["t"]), []).append((b["o"] / base, b["h"] / base, b["l"] / base, b["c"] / base))
            prev = b
    return table


def run(plan, bars5, cfg, runs=10000, seed=7, start=None, qty=None):
    if plan["segment"] != "intraday":
        raise SystemExit("the time machine only handles intraday plans")
    days = sessions(closed_only(bars5, 300))
    plan_date = plan["basis"].get("date")
    history = [d for d in days if str(d[0]) != plan_date] if plan_date else days[:-1]
    if len(history) < 20:
        raise SystemExit(f"need 20+ earlier sessions of 5m bars, have {len(history)}")
    table = _ratio_table(history)
    slots = sorted(table)
    if start is None:
        today = [d for d in days if str(d[0]) == plan_date]
        start = hhmm(today[0][1][-1]["t"] + 300) if today else "09:30"
    start = max(start, "09:30")
    path = [s for s in slots if start <= s]
    if not path:
        raise SystemExit(f"no session slots after {start}")
    side, entry, stop, target = plan["side"], plan["entry"], plan["stop"], plan["target"]
    sign = 1 if side == "BUY" else -1
    risk = plan["risk_per_share"]
    affordable = cfg["capital"] * cfg["mis_leverage"] / entry
    qty = qty or max(1, int(min(cfg["capital"] * cfg["risk_per_trade_pct"] / 100 / risk, affordable)))
    rng = random.Random(seed)
    counts = {"target": 0, "stop": 0, "flat_by": 0}
    rs = []
    for _ in range(runs):
        p, exit_, reason = entry, None, "flat_by"
        for s in path:
            if s >= cfg["flat_by"]:
                exit_ = p
                break
            ro, rh, rl, rc = rng.choice(table[s])
            adverse = p * (rl if sign > 0 else rh)
            favour = p * (rh if sign > 0 else rl)
            if (adverse - stop) * sign <= 0:
                exit_, reason = stop, "stop"
                break
            if (favour - target) * sign >= 0:
                exit_, reason = target, "target"
                break
            p *= rc
        if exit_ is None:
            exit_ = p
        counts[reason] += 1
        rs.append(backtest.net_r("intraday", side, entry, exit_, qty, risk, cfg["brokerage"]))
    rs.sort()
    result = {
        "symbol": plan["symbol"], "runs": runs, "seed": seed, "from": start, "sessions_used": len(history),
        "target_first_pct": round(counts["target"] / runs * 100, 1),
        "stop_first_pct": round(counts["stop"] / runs * 100, 1),
        "still_open_at_flat_by_pct": round(counts["flat_by"] / runs * 100, 1),
        "mean_net_r": round(sum(rs) / runs, 3), "median_net_r": round(rs[runs // 2], 3),
        "p10_net_r": round(rs[runs // 10], 2), "p90_net_r": round(rs[runs * 9 // 10], 2),
        "qty_assumed": qty,
    }
    if plan["setup"] == "orb":
        b = plan["basis"]
        past = backtest.orb_trades(history, cfg, side, b.get("r_multiple", 2.0), b.get("stop_mode", "mid"),
                                   b.get("or_minutes", 15))
        result["same_rule_on_real_sessions"] = backtest.evaluate(past)
    m = result["mean_net_r"]
    result["read"] = ("Negative after charges: skip." if m < 0 else
                      "Roughly a coin flip after charges." if m < 0.1 else
                      "Positive in simulation. Past candles are not a promise.")
    return result
