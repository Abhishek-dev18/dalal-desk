"""Indian trading charges for one round trip (or one side)."""
from . import refdata


def _brokerage(segment, value, profile):
    if value <= 0:
        return 0.0
    if profile == "flat10":
        return 10.0
    if segment == "delivery":
        return 0.0
    if segment == "options":
        return 20.0
    return min(value * 0.0003, 20.0)


def charges(segment, buy_value, sell_value, profile="zerodha", on=None):
    """All charges in rupees. Values are price x quantity (premium for options)."""
    if segment not in ("delivery", "intraday", "futures", "options"):
        raise ValueError(f"unknown segment {segment}")
    r = refdata.rates(on)
    turnover = buy_value + sell_value
    brokerage = _brokerage(segment, buy_value, profile) + _brokerage(segment, sell_value, profile)
    stt_b, stt_s = r["stt"][segment]
    stt = buy_value * stt_b / 100 + sell_value * stt_s / 100
    exchange = turnover * r["exchange"][segment] / 100
    sebi = turnover * r["sebi"] / 100
    stamp = buy_value * r["stamp_buy"][segment] / 100
    gst = (brokerage + exchange + sebi) * r["gst"] / 100
    dp = r["dp_sell"] if segment == "delivery" and sell_value > 0 else 0.0
    total = brokerage + stt + exchange + sebi + stamp + gst + dp
    return {
        "segment": segment,
        "brokerage": round(brokerage, 2),
        "stt": round(stt, 2),
        "exchange": round(exchange, 2),
        "sebi": round(sebi, 2),
        "stamp": round(stamp, 2),
        "gst": round(gst, 2),
        "dp": round(dp, 2),
        "total": round(total, 2),
        "pct_of_turnover": round(total / turnover * 100, 4) if turnover else 0.0,
        "rates_effective_from": str(r["effective_from"]),
    }


def round_trip(segment, entry, exit_, qty, side="BUY", profile="zerodha", on=None):
    """Net P&L of a completed trade."""
    buy, sell = (entry, exit_) if side == "BUY" else (exit_, entry)
    c = charges(segment, buy * qty, sell * qty, profile, on)
    gross = (sell - buy) * qty
    return {"gross": round(gross, 2), "charges": c["total"], "net": round(gross - c["total"], 2), "detail": c}


def breakeven_move(segment, price, qty, profile="zerodha"):
    """Price move per share needed just to cover charges."""
    c = charges(segment, price * qty, price * qty, profile)
    return round(c["total"] / qty, 4)
