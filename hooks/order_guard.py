#!/usr/bin/env python3
"""PreToolUse hook. Blocks any broker order tool call (for example a Kite or
Upstox MCP `place_order`) unless an approved, unexpired Dalal Desk ticket
matches the symbol and quantity. Exit code 2 blocks the call.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ORDER_TOOL = re.compile(r"(place|modify|create).*(order|gtt)|order.*(place|modify)", re.I)


def numbers(obj):
    found = set()
    if isinstance(obj, dict):
        for v in obj.values():
            found |= numbers(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= numbers(v)
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        found.add(int(obj))
    elif isinstance(obj, str) and obj.strip().isdigit():
        found.add(int(obj))
    return found


def decide(event):
    name = event.get("tool_name", "")
    if not name.startswith("mcp__") or not ORDER_TOOL.search(name):
        return 0, ""
    from dalal import risk, ticket
    if risk.kill_path().exists():
        return 2, "Dalal Desk: kill switch is ON (trader/KILL). Order blocked."
    payload = event.get("tool_input", {})
    t = ticket.approved_for(json.dumps(payload).upper(), numbers(payload))
    if t is None:
        return 2, ("Dalal Desk: no approved ticket matches this order. Build a plan, size it, pass the risk "
                   "gate, create a ticket and have the user type the approval phrase first.")
    return 0, ""


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    code, msg = decide(event)
    if msg:
        print(msg, file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
