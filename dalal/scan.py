"""Scanners. Intraday: gap, opening-range breakout, VWAP, relative volume.
Swing: trend template, tightness, volume dry-up, pivot proximity, relative strength."""
from . import ta
from .util import closed_only, hhmm, sessions

OR_END = {15: "09:30", 30: "09:45"}


def opening_range(day_bars, minutes=15):
    """(high, low) of the first `minutes` of the session from 5m bars, or None if incomplete."""
    need = minutes // 5
    bars = [b for b in day_bars if "09:15" <= hhmm(b["t"]) < OR_END[minutes]]
    if len(bars) < need:
        return None
    return max(b["h"] for b in bars), min(b["l"] for b in bars)


def intraday_row(symbol, bars5, cfg, or_minutes=15):
    bars5 = closed_only(bars5, 300)
    days = sessions(bars5)
    if len(days) < 2:
        return {"symbol": symbol, "error": "need at least 2 sessions of 5m bars"}
    (_, prev), (today_date, today) = days[-2], days[-1]
    prev_close = prev[-1]["c"]
    last = today[-1]
    orng = opening_range(today, or_minutes)
    vw = ta.vwap(today)
    n = len(today)
    past = [sum(b["v"] for b in d[:n]) for _, d in days[:-1][-20:] if len(d) >= n]
    cum = sum(b["v"] for b in today)
    rvol = cum / (sum(past) / len(past)) if past and sum(past) else None
    turnover_cr = sum(b["c"] * b["v"] for b in today) / 1e7
    row = {
        "symbol": symbol, "date": str(today_date), "as_of": hhmm(last["t"] + 300), "last": round(last["c"], 2),
        "gap_pct": round(ta.pct(today[0]["o"], prev_close), 2),
        "day_change_pct": round(ta.pct(last["c"], prev_close), 2),
        "vwap": round(vw, 2) if vw else None,
        "rvol": round(rvol, 2) if rvol else None,
        "turnover_cr": round(turnover_cr, 2),
    }
    status, side = "no_range_yet", None
    if orng:
        hi, lo = orng
        row.update(or_high=round(hi, 2), or_low=round(lo, 2), or_width_pct=round(ta.pct(hi, lo), 2))
        if last["c"] > hi:
            status = "above_range"
            side = "BUY" if vw and last["c"] > vw else None
        elif last["c"] < lo:
            status = "below_range"
            side = "SELL" if vw and last["c"] < vw else None
        else:
            status = "inside_range"
    liquid = turnover_cr >= cfg["min_turnover_cr"]
    score = 0.0
    score += 30 * min((rvol or 0) / 2, 1)
    score += 25 * (status in ("above_range", "below_range"))
    score += 20 * (side is not None)
    score += 15 * min(abs(row["gap_pct"]) / 2, 1)
    score += 10 * liquid
    row.update(or_status=status, side=side, liquid=liquid, score=round(score, 1))
    return row


def swing_row(symbol, daily, index_daily=None):
    if len(daily) < 210:
        return {"symbol": symbol, "error": f"need 210+ daily bars, have {len(daily)}"}
    closes = [b["c"] for b in daily]
    c = closes[-1]
    s50, s150, s200 = ta.sma(closes, 50), ta.sma(closes, 150), ta.sma(closes, 200)
    s200_prev = ta.sma(closes[:-21], 200)
    hi52 = max(b["h"] for b in daily[-250:])
    lo52 = min(b["l"] for b in daily[-250:])
    tests = {
        "close>50dma": c > s50, "50>150dma": s50 > s150, "150>200dma": s150 > s200,
        "200dma_rising": bool(s200_prev and s200 > s200_prev),
        "within_25pct_of_high": c >= hi52 * 0.75, "30pct_above_low": c >= lo52 * 1.30,
    }
    trend = sum(tests.values()) / len(tests)
    atr14 = ta.atr(daily, 14)
    rng10 = max(b["h"] for b in daily[-10:]) - min(b["l"] for b in daily[-10:])
    rng40 = max(b["h"] for b in daily[-40:]) - min(b["l"] for b in daily[-40:])
    tight = max(0.0, min(1.0, 1 - rng10 / rng40)) if rng40 else 0.0
    v10 = ta.sma([b["v"] for b in daily], 10)
    v50 = ta.sma([b["v"] for b in daily], 50)
    dry = max(0.0, min(1.0, 1.5 - v10 / v50)) if v50 else 0.0
    pivot = max(b["h"] for b in daily[-21:-1])
    dist = ta.pct(pivot, c)
    prox = max(0.0, 1 - abs(dist) / 5)
    rs = None
    rs_score = 0.5
    if index_daily and len(index_daily) > 126:
        rs = ta.pct(c, closes[-126]) - ta.pct(index_daily[-1]["c"], index_daily[-126]["c"])
        rs_score = max(0.0, min(1.0, 0.5 + rs / 40))
    score = 25 * trend + 25 * tight + 20 * dry + 15 * prox + 15 * rs_score
    hi55 = max(b["h"] for b in daily[-56:-1])
    e20 = ta.ema(closes, 20)
    signals = []
    if c > pivot:
        signals.append("20-day breakout")
    if c > hi55:
        signals.append("55-day breakout")
    if trend >= 0.8 and e20 and abs(ta.pct(c, e20)) <= 1.5:
        signals.append("pullback to 20 EMA in uptrend")
    return {
        "symbol": symbol, "last": round(c, 2), "score": round(score, 1), "signals": signals,
        "trend_template": f"{sum(tests.values())}/{len(tests)}", "failed": [k for k, v in tests.items() if not v],
        "pivot": round(pivot, 2), "pct_to_pivot": round(dist, 2),
        "tightness": round(tight, 2), "volume_dry_up": round(dry, 2),
        "rs_vs_nifty_6m": round(rs, 1) if rs is not None else None,
        "atr14": round(atr14, 2) if atr14 else None, "rsi14": round(ta.rsi(closes) or 0, 1),
        "from_52w_high_pct": round(ta.pct(c, hi52), 1),
    }


def run(kind, symbols, data, cfg, top=10):
    rows, errors = [], []
    index_daily = None
    if kind == "swing":
        try:
            index_daily = data.candles("NIFTY", "1d", 400)
        except Exception as e:  # noqa: BLE001
            errors.append(f"NIFTY: {e}")
    for s in symbols:
        try:
            if kind == "intraday":
                row = intraday_row(s, data.candles(s, "5m", 30), cfg)
            else:
                row = swing_row(s, data.candles(s, "1d", 400), index_daily)
        except Exception as e:  # noqa: BLE001
            row = {"symbol": s, "error": str(e)}
        (errors if "error" in row else rows).append(row if "error" not in row else f"{s}: {row['error']}")
    rows.sort(key=lambda r: r["score"], reverse=True)
    return {"scan": kind, "scanned": len(symbols), "results": rows[:top], "errors": errors,
            "weights": ("rvol 30, range break 25, vwap agrees 20, gap 15, liquidity 10" if kind == "intraday"
                        else "trend 25, tightness 25, volume dry-up 20, pivot proximity 15, relative strength 15"),
            "note": "A high score is a reason to look, not a reason to buy."}
