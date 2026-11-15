"""Settings: defaults, then config.json, then .env for secrets."""
import json
import os
from pathlib import Path

DEFAULTS = {
    "capital": 20000,
    "mode": "paper",                 # research | paper | live
    "broker": "paper",               # paper | manual | upstox | kite
    "data": ["yahoo"],               # tried in order: yahoo | upstox | csv
    "csv_dir": "data",
    "universe": "liquid",            # file in universe/<name>.txt, or a path
    "brokerage": "zerodha",          # zerodha | flat10 (Rs 10 per order)
    "risk_per_trade_pct": 1.0,
    "daily_loss_stop_pct": 2.0,
    "total_loss_budget_pct": 20.0,
    "max_trades_per_day": 3,
    "max_open_positions": 2,
    "min_reward_risk": 1.5,
    "entry_window": ["09:20", "15:00"],
    "flat_by": "15:10",
    "mis_leverage": 1.0,             # 1.0 = never trade more than your cash
    "allow_option_buying": True,
    "max_option_premium_pct": 10.0,  # max premium per option trade, % of capital
    "ticket_ttl_minutes": 15,
    "min_turnover_cr": 5.0,
    "risk_free_rate": 0.065,
}

SEGMENTS = ("intraday", "delivery", "options")


def load_env(path=".env"):
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load():
    load_env()
    cfg = dict(DEFAULTS)
    path = Path(os.environ.get("DALAL_CONFIG", "config.json"))
    if path.exists():
        cfg.update(json.loads(path.read_text(encoding="utf-8")))
    if cfg["mode"] not in ("research", "paper", "live"):
        raise SystemExit("config: mode must be research, paper or live")
    if cfg["mode"] != "live":
        cfg["broker"] = "paper"
    return cfg


def repo_root():
    return Path(__file__).resolve().parent.parent


def universe(cfg, name=None):
    name = name or cfg["universe"]
    p = Path(name)
    if not p.exists():
        p = repo_root() / "universe" / f"{name}.txt"
    if not p.exists():
        raise SystemExit(f"universe file not found: {name}")
    syms = []
    for line in p.read_text(encoding="utf-8").splitlines():
        s = line.split("#")[0].strip().upper()
        if s:
            syms.append(s)
    return syms
