"""Walk trades over real bars, net of Indian charges. Used by the backtest,
the time machine, and the paper broker."""
from . import costs
from .refdata import round_to_tick, tick_size
from .scan import opening_range
from .util import hhmm


def walk(bars, side, entry, stop, target, flat_by=None):
    """Follow a trade bar by bar. If a bar touches both stop and target, assume the stop came first."""
    sign = 1 if side == "BUY" else -1
    last = None
    for b in bars:
        if flat_by and hhmm(b["t"]) >= flat_by:
            return b["o"], "flat_by", b["t"]
        adverse = b["l"] if sign > 0 else b["h"]
        favour = b["h"] if sign > 0 else b["l"]
        if (adverse - stop) * sign <= 0:
            worse = min(stop, b["o"]) if sign > 0 else max(stop, b["o"])
            return worse, "stop", b["t"]
        if (favour - target) * sign >= 0:
            return target, "target", b["t"]
        last = b
    if last is None:
        return None, "open", None
    return last["c"], "open", last["t"]


def net_r(segment, side, entry, exit_, qty, risk_per_share, profile):
    rt = costs.round_trip(segment, entry, exit_, qty, side, profile)
    return rt["net"] / (risk_per_share * qty)


def orb_trades(days, cfg, side="BUY", r_multiple=2.0, stop_mode="mid", or_minutes=15):
    """Run the opening-range rule on each session. `days` is util.sessions() output."""
    risk_rupees = cfg["capital"] * cfg["risk_per_trade_pct"] / 100
    sign = 1 if side == "BUY" else -1
    end = "09:30" if or_minutes == 15 else "09:45"
    trades = []
    for date_, bars in days:
        orng = opening_range(bars, or_minutes)
        if not orng:
            continue
        hi, lo = orng
        mid = (hi + lo) / 2
        if side == "BUY":
            entry = round_to_tick(hi + tick_size(hi), "up")
            stop = round_to_tick(mid if stop_mode == "mid" else lo - tick_size(lo), "down")
        else:
            entry = round_to_tick(lo - tick_size(lo), "down")
            stop = round_to_tick(mid if stop_mode == "mid" else hi + tick_size(hi), "up")
        risk = (entry - stop) * sign
        if risk <= 0:
            continue
        target = entry + sign * r_multiple * risk
        after = [b for b in bars if hhmm(b["t"]) >= end]
        for i, b in enumerate(after):
            if hhmm(b["t"]) >= cfg["entry_window"][1]:
                break
            touched = b["h"] >= entry if sign > 0 else b["l"] <= entry
            if not touched:
                continue
            fill = max(entry, b["o"]) if sign > 0 else min(entry, b["o"])
            exit_, reason, _ = walk(after[i + 1:], side, fill, stop, target, cfg["flat_by"])
            if exit_ is None:
                break
            qty = max(1, int(risk_rupees / risk))
            trades.append({"date": str(date_), "entry": fill, "stop": stop, "target": round(target, 2),
                           "exit": round(exit_, 2), "reason": reason,
                           "r_gross": round((exit_ - fill) * sign / risk, 2),
                           "r_net": round(net_r("intraday", side, fill, exit_, qty, risk, cfg["brokerage"]), 2)})
            break
    return trades


def evaluate(trades):
    n = len(trades)
    if n == 0:
        return {"trades": 0, "verdict": "No trades fired. Nothing to judge."}
    rs = [t["r_net"] for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r <= 0]
    equity = peak = dd = 0.0
    for r in rs:
        equity += r
        peak = max(peak, equity)
        dd = max(dd, peak - equity)
    pf = sum(wins) / abs(sum(losses)) if losses and sum(losses) else None
    exp = sum(rs) / n
    if n < 30:
        verdict = "Too few trades to judge (need 30+). Treat as anecdote."
    elif exp <= 0:
        verdict = "Abandon: loses money after charges."
    elif exp > 0.1 and (pf or 0) > 1.3:
        verdict = "Worth paper-trading. A backtest is not proof."
    else:
        verdict = "Marginal: edge is too thin to survive real fills."
    return {"trades": n, "win_rate_pct": round(len(wins) / n * 100, 1),
            "avg_win_r": round(sum(wins) / len(wins), 2) if wins else 0,
            "avg_loss_r": round(sum(losses) / len(losses), 2) if losses else 0,
            "expectancy_r": round(exp, 3), "profit_factor": round(pf, 2) if pf else None,
            "total_r": round(sum(rs), 2), "max_drawdown_r": round(dd, 2),
            "exits": {k: sum(t["reason"] == k for t in trades) for k in ("target", "stop", "flat_by")},
            "verdict": verdict}
