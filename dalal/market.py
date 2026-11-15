"""Market context: breadth health score, FII/DII flow log, news headlines."""
import re
import urllib.request
import xml.etree.ElementTree as ET

from . import ta
from .util import now, read_json, state_dir, write_json

DEFAULT_FEEDS = [
    "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "https://www.moneycontrol.com/rss/marketreports.xml",
    "https://www.livemint.com/rss/markets",
]

IMPACT = {
    3: ["fraud", "default", "sebi order", "raid", "ban", "resign", "merger", "acquisition", "delist", "rate hike",
        "rate cut", "insolvency", "downgrade", "upgrade"],
    2: ["results", "profit", "loss", "order win", "bags order", "wins order", "contract", "stake", "buyback",
        "block deal", "bulk deal", "guidance", "q1", "q2", "q3", "q4", "rbi", "inflation", "crude", "fii"],
    1: ["dividend", "bonus", "split", "target price", "brokerage", "record date", "ipo"],
}


def breadth(symbols, data):
    """Health score 0-100 from the universe's own daily bars."""
    above50 = above200 = adv = dec = highs = lows = n = 0
    errors = []
    for s in symbols:
        try:
            d = data.candles(s, "1d", 400)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{s}: {e}")
            continue
        if len(d) < 200:
            errors.append(f"{s}: only {len(d)} daily bars")
            continue
        closes = [b["c"] for b in d]
        c = closes[-1]
        n += 1
        above50 += c > ta.sma(closes, 50)
        above200 += c > ta.sma(closes, 200)
        adv += c > closes[-2]
        dec += c < closes[-2]
        hi, lo = max(b["h"] for b in d[-250:]), min(b["l"] for b in d[-250:])
        highs += c >= hi * 0.98
        lows += c <= lo * 1.02
    if n == 0:
        return {"error": "no data for any symbol", "errors": errors}
    p50, p200 = above50 / n * 100, above200 / n * 100
    ad = adv / max(adv + dec, 1) * 100
    hl = (highs - lows) / n * 50 + 50
    score = 0.30 * p200 + 0.25 * p50 + 0.25 * ad + 0.20 * hl
    if score >= 65:
        regime, ceiling = "Risk-On", 100
    elif score >= 45:
        regime, ceiling = "Cautious", 50
    else:
        regime, ceiling = "Risk-Off", 25
    return {"symbols_used": n, "health_score": round(score, 1), "regime": regime,
            "max_exposure_pct": ceiling, "pct_above_200dma": round(p200, 1), "pct_above_50dma": round(p50, 1),
            "advancers": adv, "decliners": dec, "near_52w_high": highs, "near_52w_low": lows,
            "weights": "above 200DMA 30, above 50DMA 25, advance/decline 25, highs vs lows 20",
            "errors": errors,
            "note": "Measured on your universe file, not the whole market."}


def _flows_path():
    return state_dir() / "flows.json"


def flows_add(day, fii, dii):
    rows = read_json(_flows_path(), {})
    rows[day] = {"fii": fii, "dii": dii}
    write_json(_flows_path(), rows)
    return flows_show()


def flows_show():
    rows = read_json(_flows_path(), {})
    days = sorted(rows)[-10:]
    if not days:
        return {"days": 0, "note": "No flows logged. Look up NSE provisional FII/DII cash figures and add them."}
    f5 = sum(rows[d]["fii"] for d in days[-5:])
    d5 = sum(rows[d]["dii"] for d in days[-5:])
    if f5 > 0 and d5 > 0:
        regime = "Both buying: strong support"
    elif f5 > 0:
        regime = "FII buying, DII selling: foreign-led rally, watch for it to fade when FIIs stop"
    elif d5 > 0:
        regime = "FII selling, DII absorbing: supported but heavy"
    else:
        regime = "Both selling: weak"
    return {"days": len(days), "last_5_fii_cr": round(f5, 2), "last_5_dii_cr": round(d5, 2),
            "last_10_fii_cr": round(sum(rows[d]["fii"] for d in days), 2), "regime": regime,
            "rows": {d: rows[d] for d in days}}


def news(feeds, symbols=None, hours=24, limit=25):
    from email.utils import parsedate_to_datetime
    items, errors = [], []
    cutoff = now().timestamp() - hours * 3600
    for url in feeds:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                root = ET.fromstring(r.read())
        except Exception as e:  # noqa: BLE001
            errors.append(f"{url}: {e}")
            continue
        for it in root.iter("item"):
            title = (it.findtext("title") or "").strip()
            try:
                ts = parsedate_to_datetime(it.findtext("pubDate")).timestamp()
            except (TypeError, ValueError):
                ts = None
            if ts and ts < cutoff:
                continue
            items.append(score_headline(title, it.findtext("link"), ts, symbols))
    seen, unique = set(), []
    for i in sorted(items, key=lambda x: (x["impact"], x["time"] or 0), reverse=True):
        key = re.sub(r"\W+", "", i["title"].lower())[:60]
        if key in seen or (symbols and not i["symbols"]):
            continue
        seen.add(key)
        unique.append(i)
    return {"count": len(unique[:limit]), "items": unique[:limit], "errors": errors,
            "note": "Headlines only. Read the exchange filing before trading on any of them."}


def score_headline(title, link=None, ts=None, symbols=None):
    low = title.lower()
    impact, tags = 0, []
    for weight, words in IMPACT.items():
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"\b", low):
                impact = max(impact, weight)
                tags.append(w)
    hit = [s for s in (symbols or []) if re.search(r"\b" + re.escape(s.lower()) + r"\b", low)]
    return {"title": title, "impact": impact, "tags": tags[:4], "symbols": hit, "link": link, "time": ts}
