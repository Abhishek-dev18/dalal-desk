#!/usr/bin/env python3
"""Render the README demo: an animated SVG laid out like a Claude Code session.

It runs the real commands on the synthetic sample data from tests/fixtures.py and
writes every number it shows from that output, so the demo cannot drift from what
the tool prints. The user prompts and Claude's replies are scripted narration.

    python3 tools/make_demo.py            # writes docs/demo.svg
    python3 tools/make_demo.py --static 2 # also writes docs/demo-scene2.svg (no animation)
"""
import argparse
import io
import json
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

TEXT, DIM, GREEN, RED, AMBER, BLUE = "#e6edf3", "#8b949e", "#3fb950", "#f85149", "#d29922", "#79c0ff"
BG, BAR, EDGE = "#0d1117", "#161b22", "#30363d"
W, PAD, LH, TOP, FS = 920, 28, 23, 62, 14
FONT = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'DejaVu Sans Mono', 'Liberation Mono', monospace"


def capture():
    """Run the real pipeline on sample data and return its JSON output by step."""
    import fixtures
    from dalal import cli
    work = Path(tempfile.mkdtemp())
    fixtures.build(work / "data", symbols=("DEMO", "NIFTY", "ALPHA", "BETA"), seed=1)
    (work / "u.txt").write_text("DEMO\nALPHA\nBETA\n")
    (work / "config.json").write_text(json.dumps(
        {"data": ["csv"], "csv_dir": str(work / "data"), "universe": str(work / "u.txt")}))
    os.environ.update(DALAL_STATE=str(work / "trader"), DALAL_CONFIG=str(work / "config.json"))

    def run(clock, *argv):
        os.environ["DALAL_NOW"] = f"2026-11-13T{clock}:00"
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(list(argv))
        return json.loads(buf.getvalue())

    o = {"plan": run("10:02", "plan", "orb", "DEMO", "--r", "3", "--stop-mode", "far")}
    o["scan"] = run("12:32", "scan", "intraday")
    o["size"] = run("12:32", "size")
    o["sim"] = run("12:32", "sim")
    o["gate"] = run("12:32", "gate")
    o["ticket"] = run("12:32", "ticket", "new")
    tid = o["ticket"]["ticket"]
    run("12:32", "ticket", "approve", tid, "--typed", f"YES {tid}")
    o["fill"] = run("12:32", "ticket", "execute", tid)
    o["settle"] = run("15:40", "paper", "settle")[0]
    o["budget"] = run("15:40", "budget")
    return o


def user(text):
    return [("> ", BLUE, True), (text, TEXT, True)]


def tool(cmd):
    return [("● ", GREEN, False), ("Bash", TEXT, True), (f"({cmd})", TEXT, False)]


def out(text, color=DIM, first=False):
    return [("  └ " if first else "    ", DIM, False), (text, color, False)]


def say(text, color=TEXT, cont=False):
    return [("  " if cont else "● ", TEXT, False), (text, color, False)]


def scenes(o):
    p, s, sim, g, t, st, b = o["plan"], o["size"], o["sim"], o["gate"], o["ticket"], o["settle"], o["budget"]
    rows = o["scan"]["results"]
    tid = t["ticket"]
    limit = b["risk_per_trade"]
    scan_lines = [out(f"{'SYMBOL':<8}{'SCORE':>6}   {'RANGE':<14}{'SIDE':<6}{'REL.VOL':>7}", DIM, True)]
    scan_lines += [out(f"{r['symbol']:<8}{r['score']:>6}   {r['or_status']:<14}{r['side'] or '-':<6}{r['rvol']:>7}", TEXT)
                   for r in rows]
    ups = [r["symbol"] for r in rows if r["side"] == "BUY"]
    return [
        [user("find me an intraday setup"), None,
         tool("dd.py scan intraday"), *scan_lines, None,
         say(f"{' and '.join(ups)} closed above their opening range on normal volume."),
         say("A score is a reason to look, not a signal.", DIM, True)],
        [user("plan DEMO and tell me the odds"), None,
         tool("dd.py plan orb DEMO --r 3 --stop-mode far"),
         out(f"entry {p['entry']:.2f}   stop {p['stop']:.2f}   target {p['target']:.2f}   flat by {p['flat_by']}", TEXT, True),
         None,
         tool("dd.py sim"),
         out(f"{sim['runs']:,} replays of the rest of today, from {sim['from']}", DIM, True),
         out(f"target first {sim['target_first_pct']}%   stop first {sim['stop_first_pct']}%   "
             f"still open {sim['still_open_at_flat_by_pct']}%", TEXT),
         out(f"mean result {sim['mean_net_r']} R after charges", AMBER), None,
         say("The simulation is negative after charges. My read: skip this one.", AMBER)],
        [user("take it on paper anyway. how many shares?"), None,
         tool("dd.py size"),
         out(f"{s['qty']} shares   position Rs {s['position_value']:,.0f}", TEXT, True),
         out(f"max loss Rs {s['max_loss']} (limit Rs {limit:.0f})   profit at target Rs {s['net_profit_at_target']}", TEXT),
         None,
         tool("dd.py gate"),
         out(f"{g['verdict']}   {len(g['checks'])} of {len(g['checks'])} checks", GREEN, True), None,
         say(f"{s['qty']} shares. If the stop is hit you lose about Rs {s['max_loss']}, charges included.")],
        [user("place it"), None,
         tool("dd.py ticket new"),
         out(f"BUY {s['qty']} DEMO at Rs {p['entry']} (MIS)   stop Rs {p['stop']}   target Rs {p['target']}", TEXT, True),
         None,
         say(f"Paper ticket ready. To approve it, type: YES {tid}"), None,
         user(f"YES {tid}"), None,
         tool(f"dd.py ticket execute {tid}"),
         out(f"placed   broker {o['fill']['result']['broker']}   filled at {o['fill']['result']['fill_price']:.2f}",
             GREEN, True)],
        [user("how did it go?"), None,
         tool("dd.py paper settle"),
         out(f"exit {st['exit']} ({st['reason']} hit)   net Rs {st['pnl_net']}   {st['r']} R", RED, True), None,
         say("Stopped out, as the simulation warned."),
         say(f"The loss stayed inside the Rs {limit:.0f} limit. "
             f"Rs {b['daily_room_left']} of today's loss budget is left.", TEXT, True)],
    ]


def render(all_scenes, static=None):
    step, hold, gap = 0.55, 3.4, 0.5
    rows = max(len(sc) for sc in all_scenes)
    H = TOP + rows * LH + 46
    plan, t = [], 0.0
    for sc in all_scenes:
        start = t
        times = []
        for line in sc:
            if line is None:
                times.append(None)
                continue
            times.append(t)
            t += step * (1.6 if line[0][0] == "> " else 1.0)
        t += hold
        plan.append((start, times, t))
        t += gap
    total = t
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" '
        f'aria-label="Dalal Desk in a Claude Code session: scan, plan, simulate, size, risk gate, ticket, paper fill and review">',
        "<title>Dalal Desk in a Claude Code session</title>",
        f'<rect width="{W}" height="{H}" rx="10" fill="{BG}" stroke="{EDGE}"/>',
        f'<path d="M0 10a10 10 0 0 1 10-10h{W - 20}a10 10 0 0 1 10 10v26H0z" fill="{BAR}"/>',
        '<circle cx="22" cy="18" r="6" fill="#ff5f56"/><circle cx="42" cy="18" r="6" fill="#ffbd2e"/>'
        '<circle cx="62" cy="18" r="6" fill="#27c93f"/>',
        f'<text x="{W / 2}" y="23" fill="{DIM}" font-family="{FONT}" font-size="12.5" text-anchor="middle">'
        "Claude Code · dalal-desk · sample data, paper mode</text>",
    ]
    for i, (sc, (start, times, end)) in enumerate(zip(all_scenes, plan)):
        if static is not None and i != static:
            continue
        for n, (line, at) in enumerate(zip(sc, times)):
            if line is None:
                continue
            y = TOP + n * LH
            spans = "".join(
                f'<tspan fill="{c}"{" font-weight=\"700\"" if bold else ""}>{escape(txt)}</tspan>'
                for txt, c, bold in line)
            anim = ""
            if static is None:
                a, b = at / total, end / total
                if a <= 0:
                    vals, keys = "1;0;0", f"0;{b:.5f};1"
                else:
                    vals, keys = "0;1;0;0", f"0;{a:.5f};{b:.5f};1"
                anim = (f'<animate attributeName="opacity" dur="{total:.2f}s" repeatCount="indefinite" '
                        f'calcMode="discrete" values="{vals}" keyTimes="{keys}"/>')
            opacity = "1" if static is not None else "0"
            parts.append(f'<text x="{PAD}" y="{y}" opacity="{opacity}" font-family="{FONT}" font-size="{FS}" '
                         f'xml:space="preserve">{spans}{anim}</text>')
    foot = "Command output is real, from synthetic sample data. Prompts and replies are an illustration."
    parts.append(f'<text x="{PAD}" y="{H - 16}" fill="{DIM}" font-family="{FONT}" font-size="11.5">{foot}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n", total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs" / "demo.svg"))
    ap.add_argument("--static", type=int, help="also write one scene without animation, for checking the layout")
    args = ap.parse_args()
    sc = scenes(capture())
    svg, total = render(sc)
    Path(args.out).write_text(svg, encoding="utf-8")
    print(f"wrote {args.out}: {len(sc)} scenes, {total:.1f}s loop, {len(svg) // 1024} KB")
    if args.static is not None:
        p = Path(args.out).with_name(f"demo-scene{args.static}.svg")
        p.write_text(render(sc, args.static)[0], encoding="utf-8")
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
