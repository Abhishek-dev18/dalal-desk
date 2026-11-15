"""Indicators on plain lists. No dependencies."""


def sma(x, n):
    return sum(x[-n:]) / n if len(x) >= n else None


def ema_series(x, n):
    if len(x) < n:
        return []
    k = 2 / (n + 1)
    e = sum(x[:n]) / n
    series = [e]
    for v in x[n:]:
        e = v * k + e * (1 - k)
        series.append(e)
    return series


def ema(x, n):
    s = ema_series(x, n)
    return s[-1] if s else None


def rsi(closes, n=14):
    if len(closes) <= n:
        return None
    gains = losses = 0.0
    for i in range(1, n + 1):
        d = closes[i] - closes[i - 1]
        gains += max(d, 0)
        losses += max(-d, 0)
    ag, al = gains / n, losses / n
    for i in range(n + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        ag = (ag * (n - 1) + max(d, 0)) / n
        al = (al * (n - 1) + max(-d, 0)) / n
    if al == 0:
        return 100.0
    return 100 - 100 / (1 + ag / al)


def atr(bars, n=14):
    if len(bars) <= n:
        return None
    trs = []
    for i in range(1, len(bars)):
        h, l, pc = bars[i]["h"], bars[i]["l"], bars[i - 1]["c"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    a = sum(trs[:n]) / n
    for tr in trs[n:]:
        a = (a * (n - 1) + tr) / n
    return a


def vwap(bars):
    pv = sum((b["h"] + b["l"] + b["c"]) / 3 * b["v"] for b in bars)
    v = sum(b["v"] for b in bars)
    return pv / v if v else None


def pct(a, b):
    return (a / b - 1) * 100 if b else 0.0
