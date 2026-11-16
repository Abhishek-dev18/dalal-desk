"""The trade card: one fixed, plain format for every trade idea.

Built from trader/plan.json, trader/size.json, the risk gate and (if run) the
simulation in trader/sim.json, so the card always matches what the tool decided.
"""
import re
from datetime import date

from .refdata import LOTS, monthly_expiry, weekly_expiry

OPTION = re.compile(r"^([A-Z&]+?)(\d+(?:\.\d+)?)(CE|PE)$")


def _rs(x):
    return f"Rs {x:,.2f}"


def _verdict(gate, sim):
    if gate["verdict"] != "PASS":
        return "NO TRADE", "risk gate blocked: " + ", ".join(gate["failed"])
    if sim and sim.get("mean_net_r") is not None and sim["mean_net_r"] < 0:
        return "SKIP", "passes the risk gate, but the odds are negative after charges"
    if sim and sim.get("mean_net_r") is not None and sim["mean_net_r"] < 0.1:
        return "SMALL OR SKIP", "passes the risk gate; odds are close to a coin flip"
    return "TRADE OK", "passes every risk check" + ("" if sim else " (no simulation run)")


def build(plan, sized, gate, sim=None):
    """Return the card as a list of (label, value) rows plus a header and verdict."""
    side, seg = plan["side"], plan["segment"]
    exit_side = "SELL" if side == "BUY" else "BUY"
    rows = []
    m = OPTION.match(plan["symbol"]) if seg == "options" else None
    if m:
        und, strike, kind = m.group(1), m.group(2), m.group(3)
        rows.append(("Contract", f"{und} {strike} {kind}"))
        try:
            exp = weekly_expiry(und, date.today())
        except ValueError:
            exp = monthly_expiry(und, date.today().year, date.today().month)
        rows.append(("Nearest expiry", f"{exp:%a %d %b %Y} (check you picked the expiry you meant)"))
        rows.append(("Lot size", str(plan.get("lot") or LOTS.get(und, "?"))))
    else:
        rows.append(("Share", plan["symbol"]))
    rows.append(("Trade type", {"intraday": "Intraday (MIS), sell the same day",
                                "delivery": "Delivery (CNC), swing trade",
                                "options": "Option buy (NRML or MIS)"}.get(seg, seg)))
    if plan["setup"] == "orb":
        b = plan["basis"]
        when = (f"only after a 5-minute candle closes {'above' if side == 'BUY' else 'below'} "
                f"{_rs(plan['entry'])} (opening range {_rs(b['or_low'])} to {_rs(b['or_high'])})")
    elif plan["setup"] == "breakout":
        when = f"only after a daily close above the 20-day high {_rs(plan['basis']['pivot_20d_high'])}"
    else:
        when = f"at or near {_rs(plan['entry'])}; do not chase if it has run more than half the risk past it"
    rows.append(("When to buy" if side == "BUY" else "When to sell short", when))
    rows.append(("Buy at" if side == "BUY" else "Sell short at", f"{_rs(plan['entry'])} (limit order)"))
    qty = sized.get("qty", 0)
    if qty:
        rows.append(("Quantity", f"{qty}" + (f" ({qty // (plan.get('lot') or 1)} lot)" if plan.get("lot") else "")
                     + f" = {_rs(sized['position_value'])}"))
    else:
        rows.append(("Quantity", f"0: {sized.get('reason', 'does not fit the limits')}"))
    rows.append(("Stop-loss", f"{exit_side} at trigger {_rs(plan['stop'])}, limit {_rs(plan['stop_limit'])}. "
                              "Place it right after the buy fills."))
    rows.append(("Target", f"{exit_side} at {_rs(plan['target'])}"))
    if plan.get("flat_by"):
        rows.append(("Exit by", f"{plan['flat_by']} if neither stop nor target is hit"))
    if qty:
        rows.append(("Max loss", f"{_rs(sized['max_loss'])} incl. charges "
                                 f"({sized['pct_of_capital_at_risk']}% of capital)"))
        rows.append(("Max profit", f"{_rs(sized['net_profit_at_target'])} after charges"))
        rows.append(("Reward : risk", f"{sized['net_reward_risk']} after charges"))
    if sim and "target_first_pct" in sim:
        rows.append((f"Odds ({sim['runs']:,} replays)", f"target first {sim['target_first_pct']}%, stop first "
                                              f"{sim['stop_first_pct']}%, still open at exit time "
                                              f"{sim['still_open_at_flat_by_pct']}%; average "
                                              f"{sim['mean_net_r']} R after charges"))
    rows.append(("Risk check", f"{gate['verdict']} ({sum(c['ok'] for c in gate['checks'])} of "
                               f"{len(gate['checks'])} checks)"))
    label, why = _verdict(gate, sim)
    return {"title": f"{plan['symbol']} | {side} | {plan['setup']}", "rows": rows,
            "verdict": label, "why": why}


def markdown(card, mode):
    lines = [f"**{card['title']}**  ({mode} mode)", "", "| | |", "|---|---|"]
    for k, v in card["rows"]:
        lines.append(f"| **{k}** | {v} |")
    lines += ["", f"**Verdict: {card['verdict']}**: {card['why']}",
              "", "_Not investment advice. Check the live price before acting._"]
    return "\n".join(lines)
