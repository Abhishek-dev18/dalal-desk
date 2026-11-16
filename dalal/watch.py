"""Exit watcher: checks every open trade once and says what to do now.

One call = one check, so it works from a terminal loop, the desktop runner or a
scheduler. Each check:
  - stop or target hit -> EXIT NOW / BOOK PROFIT
  - up 1R or more      -> trail the stop (1R: to entry, then +0.5R per extra 0.5R)
  - intraday past flat_by, or within 15 minutes of it -> EXIT / get ready
  - intraday stock below VWAP on a buy (above on a short) -> WEAK
Options: Yahoo has no option prices, so pass the premium with --price SYMBOL=VALUE,
or log the trade with an underlying stop/target and the index level is watched.
The watcher only advises and moves its own trailing stop. It never places orders.
"""
from . import costs, journal, ta
from .util import hhmm, ist, now


def _r(t, price):
    move = price - t["entry"] if t["side"] == "BUY" else t["entry"] - price
    return move / t["risk_per_share"] if t["risk_per_share"] else 0.0


def _trail(t, r_now):
    """Return a new stop if the trade has earned one, else None."""
    if r_now < 1:
        return None
    steps = int((r_now - 1) / 0.5)
    lock_r = steps * 0.5
    rps = t["risk_per_share"]
    new = t["entry"] + lock_r * rps if t["side"] == "BUY" else t["entry"] - lock_r * rps
    cur = t.get("trail_stop", t["stop"])
    better = new > cur if t["side"] == "BUY" else new < cur
    return round(new, 2) if better else None


def check(cfg, data, prices=None, trail=True):
    prices = {k.upper(): v for k, v in (prices or {}).items()}
    trades = journal.load()
    t_now = now()
    clock = hhmm(t_now.timestamp())
    results, changed = [], False
    for t in [x for x in trades if x["status"] == "open"]:
        row = {"id": t["id"][:8], "symbol": t["symbol"], "side": t["side"], "qty": t["qty"],
               "segment": t["segment"], "real": not t.get("paper"), "entry": t["entry"]}
        stop = t.get("trail_stop", t["stop"])
        sym = t["symbol"]
        price, basis = prices.get(sym), "premium" if t["segment"] == "options" else "price"
        try:
            if price is None and t["segment"] != "options":
                price = data.quote(sym)
        except Exception as e:  # noqa: BLE001
            row.update(action="CHECK BY HAND", why=f"no price: {e}")
            results.append(row)
            continue
        alerts = []
        action, why = "HOLD", "between stop and target"
        if price is not None:
            r_now = _r(t, price)
            pnl = costs.round_trip(t["segment"], t["entry"], price, t["qty"], t["side"], cfg["brokerage"])
            row.update(last=price, r_now=round(r_now, 2), pnl_now_net=pnl["net"], stop=stop, target=t["target"])
            hit_stop = price <= stop if t["side"] == "BUY" else price >= stop
            hit_target = price >= t["target"] if t["side"] == "BUY" else price <= t["target"]
            if hit_stop:
                action, why = "EXIT NOW", f"{basis} {price} is through the stop {stop}"
            elif hit_target:
                action, why = "BOOK PROFIT", f"{basis} {price} reached the target {t['target']}"
            elif trail:
                new = _trail(t, r_now)
                if new is not None:
                    t["trail_stop"] = new
                    changed = True
                    row["stop"] = new
                    action, why = "MOVE STOP", (f"up {r_now:.2f}R: move your stop-loss order to {new} "
                                                "(locks in " + ("no loss" if new == t["entry"] else "profit") + ")")
        else:
            row["last"] = None
        und = t.get("underlying")
        if und and action in ("HOLD", "MOVE STOP"):
            try:
                lvl = prices.get(und) or data.quote(und)
                row["underlying"] = {"symbol": und, "last": lvl, "stop": t.get("underlying_stop"),
                                     "target": t.get("underlying_target")}
                call = sym.endswith("CE")
                us, ut = t.get("underlying_stop"), t.get("underlying_target")
                if us is not None and ((call and lvl <= us) or (not call and lvl >= us)):
                    action, why = "EXIT NOW", f"{und} at {lvl} broke the index stop {us}"
                elif ut is not None and ((call and lvl >= ut) or (not call and lvl <= ut)):
                    action, why = "BOOK PROFIT", f"{und} at {lvl} reached the index target {ut}"
            except Exception as e:  # noqa: BLE001
                alerts.append(f"no {und} level: {e}")
        if price is None and not und:
            action, why = "CHECK BY HAND", f"pass the premium with --price {sym}=<value>"
        flat = t.get("flat_by")
        if flat and t["segment"] in ("intraday", "options") and action not in ("EXIT NOW", "BOOK PROFIT"):
            if clock >= flat:
                action, why = "EXIT NOW", f"it is {clock}, past the {flat} exit time"
            else:
                fh, fm = map(int, flat.split(":"))
                ch, cm = map(int, clock.split(":"))
                left = (fh * 60 + fm) - (ch * 60 + cm)
                if left <= 15:
                    alerts.append(f"{left} minutes to the {flat} exit time: get ready to close")
        if t["segment"] == "intraday" and price is not None and action in ("HOLD", "MOVE STOP"):
            try:
                bars = [b for b in data.candles(sym, "5m", 2) if ist(b["t"]).date() == t_now.date()]
                vw = ta.vwap(bars) if bars else None
                if vw:
                    row["vwap"] = round(vw, 2)
                    weak = price < vw if t["side"] == "BUY" else price > vw
                    if weak:
                        alerts.append(f"{'below' if t['side'] == 'BUY' else 'above'} VWAP {vw:.2f}: "
                                      "the move has lost support; consider exiting early")
                        if action == "HOLD":
                            action, why = "WEAK", "price is on the wrong side of VWAP"
            except Exception:  # noqa: BLE001
                pass
        row.update(action=action, why=why)
        if alerts:
            row["alerts"] = alerts
        results.append(row)
    if changed:
        journal.save(trades)
    urgent = [r for r in results if r.get("action") in ("EXIT NOW", "BOOK PROFIT", "MOVE STOP", "WEAK",
                                                         "CHECK BY HAND")]
    return {"checked_at": t_now.isoformat(timespec="seconds"), "open_trades": len(results),
            "needs_action": len(urgent), "trades": results,
            "note": "Advice only. You place or change orders yourself in the broker app."}


def loop(cfg, data, every, minutes, prices=None, trail=True, printer=print):
    """Terminal use: check every `every` seconds for `minutes`, printing only changes."""
    import json
    import time
    end = time.time() + minutes * 60
    last = {}
    while True:
        res = check(cfg, data, prices, trail)
        for r in res["trades"]:
            key = (r["action"], r.get("stop"))
            if last.get(r["id"]) != key:
                printer(json.dumps({"at": res["checked_at"], **r}))
                last[r["id"]] = key
        if not res["open_trades"] or time.time() >= end:
            return res
        time.sleep(every)


def parse_prices(items):
    outp = {}
    for it in items or []:
        if "=" not in it:
            raise SystemExit(f"--price expects SYMBOL=VALUE, got {it}")
        k, v = it.split("=", 1)
        outp[k.strip().upper()] = float(v)
    return outp

