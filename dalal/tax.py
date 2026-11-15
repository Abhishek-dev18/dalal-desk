"""Rough tax buckets from the journal. An estimate to take to a CA, not a filing."""
from datetime import datetime

from . import journal


def report(fy_start_year, include_paper=False):
    start, end = f"{fy_start_year}-04-01", f"{fy_start_year + 1}-03-31"
    buckets = {k: {"trades": 0, "net": 0.0, "turnover": 0.0, "charges": 0.0}
               for k in ("speculative_intraday", "business_fno", "stcg_delivery", "ltcg_delivery")}
    for t in journal.load():
        if t["status"] != "closed" or (t.get("paper") and not include_paper):
            continue
        if not start <= t["closed"][:10] <= end:
            continue
        if t["segment"] == "intraday":
            k = "speculative_intraday"
        elif t["segment"] in ("options", "futures"):
            k = "business_fno"
        else:
            held = datetime.fromisoformat(t["closed"]) - datetime.fromisoformat(t["opened"])
            k = "ltcg_delivery" if held.days > 365 else "stcg_delivery"
        b = buckets[k]
        b["trades"] += 1
        b["net"] = round(b["net"] + t["pnl_net"], 2)
        b["charges"] = round(b["charges"] + t["charges"], 2)
        b["turnover"] = round(b["turnover"] + abs(t["pnl_gross"]), 2)
    return {
        "tax_year": f"{fy_start_year}-{str(fy_start_year + 1)[2:]}", "include_paper": include_paper,
        "buckets": buckets,
        "how_each_is_taxed": {
            "speculative_intraday": "Business income at slab rates. Losses offset only speculative profit; carry forward 4 years.",
            "business_fno": "Non-speculative business income at slab rates. Losses offset other income except salary; carry forward 8 years.",
            "stcg_delivery": "Short-term capital gains on listed shares: 20%.",
            "ltcg_delivery": "Long-term capital gains: 12.5% above Rs 1.25 lakh a year.",
        },
        "notes": [
            "Turnover here is the sum of absolute profit and loss per trade (ICAI method).",
            "Intraday or F&O income means ITR-3. Keep contract notes.",
            "Rates and section numbers changed with the Income-tax Act 2025. Confirm with a CA before filing.",
        ],
    }
