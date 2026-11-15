#!/usr/bin/env python3
"""Desktop runner: lets Claude run dd.py on your own computer and internet.

Use it when Claude works on your folder from a sandbox that cannot reach market
data (for example Claude Desktop with a connected folder). It watches a queue
folder; Claude drops a command file there, this script runs dd.py with it and
writes the result next to it.

    python tools/runner.py --work C:/path/to/your/trading/folder

Command file  <work>/queue/<id>.cmd.json : {"args": ["scan", "intraday"]}
Result file   <work>/queue/<id>.out.json : {"id", "args", "exit_code", "stdout", "stderr", "seconds"}

Safety: it runs dd.py only, never a shell, and only the subcommands listed in
ALLOWED. All of dd.py's own rules (paper mode, risk gate, typed approval,
kill switch) still apply. Stop it with Ctrl+C.
"""
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DD = ROOT / "dd.py"
ALLOWED = {"doctor", "costs", "expiry", "quote", "scan", "breadth", "news", "flows", "plan", "entry", "sim",
           "size", "gate", "budget", "ticket", "paper", "journal", "kill", "options", "backtest", "tax"}
MAX_SECONDS = 600


def run_one(cmd_path, work):
    out_path = cmd_path.with_name(cmd_path.name.replace(".cmd.json", ".out.json"))
    rid = cmd_path.name[: -len(".cmd.json")]
    try:
        args = json.loads(cmd_path.read_text(encoding="utf-8"))["args"]
        if not isinstance(args, list) or not args or not all(isinstance(a, str) for a in args):
            raise ValueError("args must be a non-empty list of strings")
        if args[0] not in ALLOWED:
            raise ValueError(f"command '{args[0]}' is not allowed")
    except Exception as e:  # noqa: BLE001
        result = {"id": rid, "exit_code": 2, "stdout": "", "stderr": f"bad command file: {e}", "seconds": 0}
    else:
        start = time.time()
        try:
            p = subprocess.run([sys.executable, str(DD), *args], cwd=str(work), capture_output=True,
                               text=True, encoding="utf-8", timeout=MAX_SECONDS)
            result = {"id": rid, "args": args, "exit_code": p.returncode, "stdout": p.stdout, "stderr": p.stderr}
        except subprocess.TimeoutExpired:
            result = {"id": rid, "args": args, "exit_code": 124, "stdout": "",
                      "stderr": f"timed out after {MAX_SECONDS}s"}
        result["seconds"] = round(time.time() - start, 1)
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2), encoding="utf-8")
    tmp.replace(out_path)
    done = cmd_path.with_name(cmd_path.name.replace(".cmd.json", ".done.json"))
    cmd_path.replace(done)
    status = "ok" if result["exit_code"] == 0 else f"exit {result['exit_code']}"
    print(f"[{time.strftime('%H:%M:%S')}] {rid}: {' '.join(result.get('args', []))} -> {status}", flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--work", required=True, help="folder holding config.json, .env and trader/")
    ap.add_argument("--once", action="store_true", help="process the queue once and exit")
    a = ap.parse_args()
    work = Path(a.work).resolve()
    queue = work / "queue"
    queue.mkdir(parents=True, exist_ok=True)
    print(f"Dalal Desk runner: watching {queue}  (Ctrl+C to stop)", flush=True)
    while True:
        for cmd in sorted(queue.glob("*.cmd.json")):
            run_one(cmd, work)
        if a.once:
            return 0
        time.sleep(1)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("runner stopped")
