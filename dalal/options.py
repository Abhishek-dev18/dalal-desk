"""Options maths: Black-Scholes price, Greeks, implied volatility, option-chain
analytics (PCR, max pain, OI walls) and a small-account check for option buyers."""
import csv
import math

from .refdata import LOTS


def _n(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _pdf(x):
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)


def _d(s, k, t, r, v):
    d1 = (math.log(s / k) + (r + v * v / 2) * t) / (v * math.sqrt(t))
    return d1, d1 - v * math.sqrt(t)


def price(kind, s, k, days, vol, r=0.065):
    t = max(days, 0.01) / 365
    d1, d2 = _d(s, k, t, r, vol)
    if kind.upper() in ("CE", "C", "CALL"):
        return s * _n(d1) - k * math.exp(-r * t) * _n(d2)
    return k * math.exp(-r * t) * _n(-d2) - s * _n(-d1)


def greeks(kind, s, k, days, vol, r=0.065):
    t = max(days, 0.01) / 365
    d1, d2 = _d(s, k, t, r, vol)
    call = kind.upper() in ("CE", "C", "CALL")
    delta = _n(d1) if call else _n(d1) - 1
    gamma = _pdf(d1) / (s * vol * math.sqrt(t))
    vega = s * _pdf(d1) * math.sqrt(t) / 100
    theta = -s * _pdf(d1) * vol / (2 * math.sqrt(t))
    theta += (-r * k * math.exp(-r * t) * _n(d2)) if call else (r * k * math.exp(-r * t) * _n(-d2))
    return {"price": round(price(kind, s, k, days, vol, r), 2), "delta": round(delta, 4), "gamma": round(gamma, 6),
            "theta_per_day": round(theta / 365, 2), "vega_per_1pct": round(vega, 2)}


def implied_vol(kind, s, k, days, premium, r=0.065):
    lo, hi = 0.01, 5.0
    if not price(kind, s, k, days, lo, r) <= premium <= price(kind, s, k, days, hi, r):
        return None
    for _ in range(100):
        mid = (lo + hi) / 2
        if price(kind, s, k, days, mid, r) > premium:
            hi = mid
        else:
            lo = mid
    return round((lo + hi) / 2, 4)


def read_chain(path):
    """CSV with columns: strike,ce_oi,pe_oi and optionally ce_ltp,pe_ltp,ce_oi_chg,pe_oi_chg."""
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            rows.append({k.strip().lower(): float(str(v).replace(",", "") or 0) for k, v in r.items()})
    return sorted(rows, key=lambda r: r["strike"])


def chain_stats(rows, spot):
    ce = sum(r["ce_oi"] for r in rows)
    pe = sum(r["pe_oi"] for r in rows)
    pain = []
    for r in rows:
        k = r["strike"]
        loss = sum(max(k - x["strike"], 0) * x["ce_oi"] + max(x["strike"] - k, 0) * x["pe_oi"] for x in rows)
        pain.append((loss, k))
    atm = min(rows, key=lambda r: abs(r["strike"] - spot))
    out = {
        "spot": spot, "pcr_oi": round(pe / ce, 2) if ce else None, "max_pain": min(pain)[1],
        "call_wall": max(rows, key=lambda r: r["ce_oi"])["strike"],
        "put_wall": max(rows, key=lambda r: r["pe_oi"])["strike"],
        "atm_strike": atm["strike"],
    }
    if atm.get("ce_ltp") and atm.get("pe_ltp"):
        straddle = atm["ce_ltp"] + atm["pe_ltp"]
        out["atm_straddle"] = round(straddle, 2)
        out["implied_range"] = [round(atm["strike"] - straddle, 2), round(atm["strike"] + straddle, 2)]
    if "ce_oi_chg" in rows[0]:
        out["biggest_call_writing"] = max(rows, key=lambda r: r.get("ce_oi_chg", 0))["strike"]
        out["biggest_put_writing"] = max(rows, key=lambda r: r.get("pe_oi_chg", 0))["strike"]
    out["read"] = "Walls are where sellers sit; they often cap moves but break hard when they fail."
    return out


def buy_check(underlying, kind, spot, strike, premium, days, cfg):
    """Can this account afford to buy one lot, and what does it need to work?"""
    lot = LOTS.get(underlying.upper())
    if not lot:
        raise SystemExit(f"no lot size on file for {underlying}; add it to refdata.LOTS")
    cost = premium * lot
    cap = cfg["capital"] * cfg["max_option_premium_pct"] / 100
    iv = implied_vol(kind, spot, strike, days, premium, cfg["risk_free_rate"])
    call = kind.upper() in ("CE", "C", "CALL")
    be = strike + premium if call else strike - premium
    result = {
        "contract": f"{underlying.upper()} {strike:g} {kind.upper()}", "lot": lot, "cost_one_lot": round(cost, 2),
        "premium_cap": round(cap, 2), "affordable": cost <= cap, "max_loss": round(cost, 2),
        "pct_of_capital": round(cost / cfg["capital"] * 100, 1), "breakeven_at_expiry": round(be, 2),
        "move_needed_pct": round(abs(be / spot - 1) * 100, 2), "days_to_expiry": days, "implied_vol": iv,
    }
    if iv:
        g = greeks(kind, spot, strike, days, iv, cfg["risk_free_rate"])
        result["greeks"] = g
        result["theta_cost_per_day_one_lot"] = round(g["theta_per_day"] * lot, 2)
    warnings = []
    if cost > cap:
        warnings.append("One lot costs more than your premium cap. Do not buy.")
    if days <= 1:
        warnings.append("Expiry day or the day before: premium can go to zero within hours.")
    if result["move_needed_pct"] > 1.5 and days <= 3:
        warnings.append("Needs a large move in very few days.")
    decay = abs(result.get("theta_cost_per_day_one_lot", 0))
    if decay and decay >= 0.5 * cost:
        warnings.append(f"Time decay: about Rs {decay:.0f} a day for one lot, {decay / cost * 100:.0f}% of what "
                        "you pay. If the index does not move fast, most of the premium is gone in a day.")
    result["warnings"] = warnings
    return result
