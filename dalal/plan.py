"""Turn a setup into an exact plan: entry, stop, target, all on the tick grid."""
from . import ta
from .refdata import round_to_tick, tick_size
from .scan import opening_range
from .util import closed_only, hhmm, now, sessions


def _finish(symbol, side, segment, setup, entry, stop, r_multiple, cfg, target=None, basis=None, lot=None):
    sign = 1 if side == "BUY" else -1
    risk = round((entry - stop) * sign, 2)
    if risk <= 0:
        raise SystemExit(f"stop {stop} is on the wrong side of entry {entry} for a {side}")
    if target is None:
        target = round_to_tick(entry + sign * r_multiple * risk, "down" if sign > 0 else "up")
    stop_limit = round_to_tick(stop * (1 - sign * 0.002), "down" if sign > 0 else "up")
    return {
        "symbol": symbol, "side": side, "segment": segment,
        "product": "MIS" if segment == "intraday" else ("NRML" if segment == "options" else "CNC"),
        "setup": setup, "entry": entry, "stop": stop, "stop_limit": stop_limit, "target": target,
        "risk_per_share": risk, "reward_risk": round((target - entry) * sign / risk, 2),
        "flat_by": cfg["flat_by"] if segment == "intraday" else None,
        "lot": lot, "created": now().isoformat(), "basis": basis or {},
    }


def orb(symbol, bars5, cfg, side="BUY", r_multiple=2.0, stop_mode="mid", or_minutes=15):
    days = sessions(closed_only(bars5, 300))
    if not days:
        raise SystemExit("no intraday bars")
    date_, today = days[-1]
    orng = opening_range(today, or_minutes)
    if not orng:
        raise SystemExit(f"opening range for {date_} is not complete yet")
    hi, lo = orng
    mid = (hi + lo) / 2
    if side == "BUY":
        entry = round_to_tick(hi + tick_size(hi), "up")
        stop = round_to_tick(mid if stop_mode == "mid" else lo - tick_size(lo), "down")
    else:
        entry = round_to_tick(lo - tick_size(lo), "down")
        stop = round_to_tick(mid if stop_mode == "mid" else hi + tick_size(hi), "up")
    return _finish(symbol, side, "intraday", "orb", entry, stop, r_multiple, cfg,
                   basis={"date": str(date_), "or_high": hi, "or_low": lo, "or_minutes": or_minutes,
                          "stop_mode": stop_mode, "r_multiple": r_multiple})


def breakout(symbol, daily, cfg, r_multiple=2.0, atr_mult=1.5):
    if len(daily) < 30:
        raise SystemExit("need 30+ daily bars")
    pivot = max(b["h"] for b in daily[-20:])
    a = ta.atr(daily, 14)
    entry = round_to_tick(pivot + tick_size(pivot), "up")
    stop = round_to_tick(entry - atr_mult * a, "down")
    return _finish(symbol, "BUY", "delivery", "breakout", entry, stop, r_multiple, cfg,
                   basis={"pivot_20d_high": pivot, "atr14": round(a, 2), "atr_mult": atr_mult,
                          "r_multiple": r_multiple})


def manual(symbol, side, segment, entry, stop, target, cfg, lot=None, setup="manual"):
    return _finish(symbol, side, segment, setup, entry, stop, 2.0, cfg, target=target, lot=lot)


def entry_check(plan, bars5, cfg):
    """waiting | triggered | expired, decided only on closed 5m bars."""
    days = sessions(closed_only(bars5, 300))
    if not days:
        return {"status": "waiting", "reason": "no bars yet"}
    _, today = days[-1]
    last = today[-1]
    t = hhmm(last["t"] + 300)
    sign = 1 if plan["side"] == "BUY" else -1
    if (last["c"] - plan["stop"]) * sign <= 0:
        return {"status": "expired", "reason": f"price {last['c']} is already through the stop", "as_of": t}
    if plan["segment"] == "intraday" and t > cfg["entry_window"][1]:
        return {"status": "expired", "reason": f"past the entry window ({cfg['entry_window'][1]})", "as_of": t}
    if (last["c"] - plan["entry"]) * sign >= 0:
        chase = abs(last["c"] - plan["entry"]) / plan["risk_per_share"]
        if chase > 0.5:
            return {"status": "expired", "as_of": t,
                    "reason": f"closed {chase:.1f}R past the entry; too late to chase", "last_close": last["c"]}
        return {"status": "triggered", "as_of": t, "last_close": last["c"],
                "reason": "a 5m bar closed beyond the entry level"}
    return {"status": "waiting", "as_of": t, "last_close": last["c"],
            "reason": f"needs a 5m close {'above' if sign > 0 else 'below'} {plan['entry']}"}
