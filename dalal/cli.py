"""Command line for every skill. Each command prints JSON."""
import argparse
import sys
from datetime import date

from . import backtest, config, costs, doctor, journal, market, options, plan, refdata, risk, scan, sim, tax, ticket
from .providers import get_data
from .util import now, out, read_json, sessions, state_dir, write_json, closed_only


def _plan_file():
    return state_dir() / "plan.json"


def _size_file():
    return state_dir() / "size.json"


def _need(path, what):
    obj = read_json(path, None)
    if obj is None:
        raise SystemExit(f"no {what} yet ({path}). Build one first.")
    return obj


def main(argv=None):
    p = argparse.ArgumentParser(prog="dd.py", description="Dalal Desk: Indian market trading toolkit")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("doctor"); a.add_argument("--live", action="store_true")
    a = sub.add_parser("costs")
    a.add_argument("--segment", required=True, choices=["delivery", "intraday", "futures", "options"])
    a.add_argument("--buy", type=float, required=True); a.add_argument("--sell", type=float, required=True)
    a.add_argument("--qty", type=int, required=True)
    a = sub.add_parser("expiry"); a.add_argument("underlying"); a.add_argument("--date")
    a = sub.add_parser("quote"); a.add_argument("symbol")
    a = sub.add_parser("scan"); a.add_argument("kind", choices=["intraday", "swing"])
    a.add_argument("--symbols"); a.add_argument("--universe"); a.add_argument("--top", type=int, default=10)
    a = sub.add_parser("breadth"); a.add_argument("--universe")
    a = sub.add_parser("news"); a.add_argument("--symbols"); a.add_argument("--hours", type=int, default=24)
    a = sub.add_parser("flows"); a.add_argument("action", choices=["add", "show"])
    a.add_argument("--date"); a.add_argument("--fii", type=float); a.add_argument("--dii", type=float)

    a = sub.add_parser("plan"); a.add_argument("setup", choices=["orb", "breakout", "manual"])
    a.add_argument("symbol"); a.add_argument("--side", default="BUY", choices=["BUY", "SELL"])
    a.add_argument("--r", type=float, default=2.0); a.add_argument("--stop-mode", default="mid", choices=["mid", "far"])
    a.add_argument("--or-minutes", type=int, default=15, choices=[15, 30])
    a.add_argument("--atr-mult", type=float, default=1.5)
    a.add_argument("--segment", default="intraday", choices=list(config.SEGMENTS))
    a.add_argument("--entry", type=float); a.add_argument("--stop", type=float); a.add_argument("--target", type=float)
    a.add_argument("--lot", type=int)
    sub.add_parser("entry")
    a = sub.add_parser("sim"); a.add_argument("--runs", type=int, default=10000)
    a.add_argument("--seed", type=int, default=7); a.add_argument("--from", dest="start")
    sub.add_parser("size"); sub.add_parser("gate"); sub.add_parser("budget")
    a = sub.add_parser("ticket"); a.add_argument("action", choices=["new", "show", "approve", "execute", "list"])
    a.add_argument("id", nargs="?"); a.add_argument("--typed", default="")
    a = sub.add_parser("paper"); a.add_argument("action", choices=["settle"])
    a = sub.add_parser("journal"); a.add_argument("action", choices=["list", "close", "stats", "export"])
    a.add_argument("id", nargs="?"); a.add_argument("--price", type=float); a.add_argument("--reason", default="manual")
    a = sub.add_parser("kill"); a.add_argument("action", choices=["on", "status"])
    a = sub.add_parser("options")
    a.add_argument("action", choices=["price", "greeks", "iv", "chain", "buycheck"])
    a.add_argument("--kind", default="CE"); a.add_argument("--spot", type=float); a.add_argument("--strike", type=float)
    a.add_argument("--days", type=float); a.add_argument("--vol", type=float); a.add_argument("--premium", type=float)
    a.add_argument("--underlying", default="NIFTY"); a.add_argument("--file")
    a = sub.add_parser("backtest"); a.add_argument("symbol"); a.add_argument("--side", default="BUY")
    a.add_argument("--r", type=float, default=2.0); a.add_argument("--stop-mode", default="mid")
    a.add_argument("--or-minutes", type=int, default=15); a.add_argument("--show-trades", action="store_true")
    a = sub.add_parser("tax"); a.add_argument("--fy", type=int); a.add_argument("--include-paper", action="store_true")

    args = p.parse_args(argv)
    cfg = config.load()
    c = args.cmd

    if c == "doctor":
        return out(doctor.run(cfg, args.live))
    if c == "costs":
        rt = costs.round_trip(args.segment, args.buy, args.sell, args.qty, "BUY", cfg["brokerage"])
        rt["breakeven_move_per_share"] = costs.breakeven_move(args.segment, args.buy, args.qty, cfg["brokerage"])
        return out(rt)
    if c == "expiry":
        on = date.fromisoformat(args.date) if args.date else now().date()
        u = args.underlying.upper()
        res = {"underlying": u, "lot": refdata.LOTS.get(u), "monthly": str(refdata.monthly_expiry(u, on.year, on.month))}
        try:
            w = refdata.weekly_expiry(u, on)
            res.update(weekly=str(w), days_to_weekly=(w - on).days)
        except ValueError as e:
            res["weekly"] = str(e)
        res["note"] = "Computed from the holiday list on file, which may be incomplete. Confirm on NSE."
        return out(res)
    if c == "kill":
        if args.action == "on":
            risk.kill_path().write_text(f"killed {now().isoformat()}\n")
        return out({"kill_switch": "ON" if risk.kill_path().exists() else "off",
                    "to_clear": f"a human deletes {risk.kill_path()} by hand"})
    if c == "budget":
        return out(risk.budget(cfg))
    if c == "flows":
        if args.action == "add":
            if None in (args.date, args.fii, args.dii):
                raise SystemExit("flows add needs --date --fii --dii (Rs crore, net)")
            return out(market.flows_add(args.date, args.fii, args.dii))
        return out(market.flows_show())
    if c == "options":
        return _options(args, cfg)
    if c == "tax":
        fy = args.fy or (now().year if now().month >= 4 else now().year - 1)
        return out(tax.report(fy, args.include_paper))
    if c == "journal":
        if args.action == "list":
            return out(journal.load())
        if args.action == "stats":
            return out(journal.stats(risk.is_paper(cfg)))
        if args.action == "export":
            return journal.export_csv()
        if not args.id or args.price is None:
            raise SystemExit("journal close needs an id (or symbol) and --price")
        return out(journal.close_trade(args.id, args.price, args.reason, profile=cfg["brokerage"]))
    if c == "ticket" and args.action in ("show", "approve", "execute", "list"):
        if args.action == "list":
            return out([ticket.show(t) for t in ticket.load().values()])
        if not args.id:
            raise SystemExit("give a ticket id")
        if args.action == "show":
            return out(ticket.show(ticket.find(ticket.load(), args.id)))
        if args.action == "approve":
            return out(ticket.approve(args.id, args.typed))
        return out(ticket.execute(args.id, cfg))
    if c == "size":
        s = risk.size(_need(_plan_file(), "plan"), cfg)
        write_json(_size_file(), s)
        return out(s)
    if c == "gate":
        return out(risk.gate(_need(_plan_file(), "plan"), _need(_size_file(), "size"), cfg))
    if c == "ticket":
        return out(ticket.create(_need(_plan_file(), "plan"), _need(_size_file(), "size"), cfg))
    if c == "news":
        syms = args.symbols.upper().split(",") if args.symbols else None
        return out(market.news(cfg.get("news_feeds", market.DEFAULT_FEEDS), syms, args.hours))

    data = get_data(cfg)
    if c == "quote":
        return out({"symbol": args.symbol.upper(), "last": data.quote(args.symbol), "sources": cfg["data"]})
    if c == "scan":
        syms = args.symbols.upper().split(",") if args.symbols else config.universe(cfg, args.universe)
        return out(scan.run(args.kind, syms, data, cfg, args.top))
    if c == "breadth":
        return out(market.breadth(config.universe(cfg, args.universe), data))
    if c == "plan":
        sym = args.symbol.upper()
        if args.setup == "orb":
            pl = plan.orb(sym, data.candles(sym, "5m", 5), cfg, args.side, args.r, args.stop_mode, args.or_minutes)
        elif args.setup == "breakout":
            pl = plan.breakout(sym, data.candles(sym, "1d", 120), cfg, args.r, args.atr_mult)
        else:
            if None in (args.entry, args.stop, args.target):
                raise SystemExit("manual plan needs --entry --stop --target")
            pl = plan.manual(sym, args.side, args.segment, args.entry, args.stop, args.target, cfg, args.lot)
        write_json(_plan_file(), pl)
        return out(pl)
    if c == "entry":
        pl = _need(_plan_file(), "plan")
        return out(plan.entry_check(pl, data.candles(pl["symbol"], "5m", 3), cfg))
    if c == "sim":
        pl = _need(_plan_file(), "plan")
        sized = read_json(_size_file(), {})
        qty = sized.get("qty") if sized.get("symbol") == pl["symbol"] else None
        return out(sim.run(pl, data.candles(pl["symbol"], "5m", 59), cfg, args.runs, args.seed, args.start, qty))
    if c == "paper":
        return out(journal.settle_paper(cfg, data))
    if c == "backtest":
        sym = args.symbol.upper()
        days = sessions(closed_only(data.candles(sym, "5m", 59), 300))
        trades = backtest.orb_trades(days, cfg, args.side, args.r, args.stop_mode, args.or_minutes)
        res = {"symbol": sym, "rule": f"ORB {args.or_minutes}m {args.side}, stop {args.stop_mode}, target {args.r}R",
               "sessions": len(days), "result": backtest.evaluate(trades),
               "caveat": "About 60 sessions of one stock is a small sample. Fills are assumed, not real."}
        if args.show_trades:
            res["trades_list"] = trades
        return out(res)
    raise SystemExit(f"unhandled command {c}")


def _options(args, cfg):
    r = cfg["risk_free_rate"]
    need = {"price": ("spot", "strike", "days", "vol"), "greeks": ("spot", "strike", "days", "vol"),
            "iv": ("spot", "strike", "days", "premium"), "chain": ("file", "spot"),
            "buycheck": ("spot", "strike", "days", "premium")}[args.action]
    missing = [n for n in need if getattr(args, n) is None]
    if missing:
        raise SystemExit(f"options {args.action} needs: " + " ".join("--" + m for m in missing))
    if args.action == "price":
        return out({"price": round(options.price(args.kind, args.spot, args.strike, args.days, args.vol, r), 2)})
    if args.action == "greeks":
        return out(options.greeks(args.kind, args.spot, args.strike, args.days, args.vol, r))
    if args.action == "iv":
        return out({"implied_vol": options.implied_vol(args.kind, args.spot, args.strike, args.days, args.premium, r)})
    if args.action == "chain":
        return out(options.chain_stats(options.read_chain(args.file), args.spot))
    return out(options.buy_check(args.underlying, args.kind, args.spot, args.strike, args.premium, args.days, cfg))


if __name__ == "__main__":
    sys.exit(main())
