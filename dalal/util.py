"""Small shared helpers: IST time, state folder, JSON I/O."""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))


def now():
    """Current IST time. DALAL_NOW (ISO string) overrides it for replays and tests."""
    forced = os.environ.get("DALAL_NOW")
    if forced:
        d = datetime.fromisoformat(forced)
        return d if d.tzinfo else d.replace(tzinfo=IST)
    return datetime.now(IST)


def ist(ts):
    return datetime.fromtimestamp(ts, IST)


def hhmm(ts):
    return ist(ts).strftime("%H:%M")


def state_dir():
    p = Path(os.environ.get("DALAL_STATE", "trader"))
    p.mkdir(parents=True, exist_ok=True)
    return p


def read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
    os.replace(tmp, path)


def out(obj):
    print(json.dumps(obj, indent=2, default=str))


def sessions(bars):
    """Group intraday bars by IST date, oldest first. Returns list of (date, bars)."""
    days = {}
    for b in bars:
        days.setdefault(ist(b["t"]).date(), []).append(b)
    return [(d, sorted(v, key=lambda b: b["t"])) for d, v in sorted(days.items())]


def closed_only(bars, interval_seconds):
    """Drop a bar that is still forming."""
    cutoff = now().timestamp()
    return [b for b in bars if b["t"] + interval_seconds <= cutoff]
