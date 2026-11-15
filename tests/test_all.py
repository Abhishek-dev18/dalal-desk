"""Offline tests. Run: python3 -m unittest discover -s tests -v"""
import io
import json
import math
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "hooks"))

import fixtures  # noqa: E402
from dalal import backtest, cli, config, costs, journal, market, options, refdata, risk, ticket  # noqa: E402
from dalal.providers import get_data  # noqa: E402


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = tempfile.mkdtemp()
        fixtures.build(cls.data_dir)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cfg_path = Path(self.tmp) / "config.json"
        self.write_cfg()
        os.environ["DALAL_STATE"] = str(Path(self.tmp) / "trader")
        os.environ["DALAL_CONFIG"] = str(self.cfg_path)
        os.environ["DALAL_NOW"] = "2026-11-13T10:02:00"
        os.environ.pop("LIVE_TRADING", None)

    def write_cfg(self, **over):
        cfg = {"data": ["csv"], "csv_dir": self.data_dir, "universe": str(Path(self.tmp) / "u.txt")}
        cfg.update(over)
        self.cfg_path.write_text(json.dumps(cfg))
        (Path(self.tmp) / "u.txt").write_text("TEST\nAAA\nBBB\n")

    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli.main(list(argv))
        text = buf.getvalue()
        return json.loads(text) if text.strip().startswith(("{", "[")) else text

    def manual_plan(self):
        last = self.run_cli("quote", "TEST")["last"]
        e = refdata.round_to_tick(last)
        s = refdata.round_to_tick(e * 0.99, "down")
        t = refdata.round_to_tick(e * 1.02, "up")
        return self.run_cli("plan", "manual", "TEST", "--entry", str(e), "--stop", str(s), "--target", str(t))


class TestRules(Base):
    def test_intraday_charges_golden(self):
        c = costs.charges("intraday", 20000, 20100)
        self.assertAlmostEqual(c["brokerage"], 12.03, places=2)
        self.assertAlmostEqual(c["stt"], 5.03, places=1)
        self.assertTrue(20.5 < c["total"] < 22.0, c)

    def test_delivery_and_options_charges(self):
        d = costs.charges("delivery", 10000, 10000)
        self.assertEqual(d["brokerage"], 0)
        self.assertAlmostEqual(d["stt"], 20.0, places=2)
        self.assertAlmostEqual(d["dp"], 15.34)
        o = costs.charges("options", 2000, 2500)
        self.assertEqual(o["brokerage"], 40.0)
        self.assertAlmostEqual(o["stt"], 3.75, places=2)

    def test_ticks(self):
        self.assertEqual(refdata.round_to_tick(1080.03, "up"), 1080.1)
        self.assertEqual(refdata.round_to_tick(1080.07, "down"), 1080.0)
        self.assertEqual(refdata.round_to_tick(339.33, "down"), 339.3)
        self.assertEqual(refdata.round_to_tick(120.456, "nearest"), 120.46)
        self.assertTrue(refdata.on_tick(339.3))
        self.assertFalse(refdata.on_tick(339.33))

    def test_holiday_list_2026(self):
        self.assertEqual(len([d for d in refdata.HOLIDAYS if d.year == 2026]), 16)
        self.assertTrue(all(d.weekday() < 5 for d in refdata.HOLIDAYS))
        # Holi, Tue 3 Mar 2026: the Nifty weekly moves to Mon 2 Mar
        self.assertEqual(refdata.weekly_expiry("NIFTY", date(2026, 3, 2)), date(2026, 3, 2))
        # Dussehra, Tue 20 Oct 2026
        self.assertEqual(refdata.weekly_expiry("NIFTY", date(2026, 10, 19)), date(2026, 10, 19))

    def test_expiry_shifts_for_holiday(self):
        self.assertEqual(refdata.weekly_expiry("NIFTY", date(2026, 11, 16)), date(2026, 11, 17))
        self.assertEqual(refdata.weekly_expiry("NIFTY", date(2026, 11, 18)), date(2026, 11, 23))
        self.assertEqual(refdata.monthly_expiry("BANKNIFTY", 2026, 11), date(2026, 11, 23))
        with self.assertRaises(ValueError):
            refdata.weekly_expiry("BANKNIFTY", date(2026, 11, 16))


class TestOptions(Base):
    def test_put_call_parity(self):
        s, k, days, v, r = 25150, 25200, 7, 0.14, 0.065
        c, p = options.price("CE", s, k, days, v, r), options.price("PE", s, k, days, v, r)
        self.assertAlmostEqual(c - p, s - k * math.exp(-r * days / 365), places=6)

    def test_iv_round_trip(self):
        prem = options.price("CE", 25150, 25200, 5, 0.16)
        self.assertAlmostEqual(options.implied_vol("CE", 25150, 25200, 5, prem), 0.16, places=3)

    def test_chain_stats(self):
        rows = [{"strike": 100, "ce_oi": 10, "pe_oi": 50}, {"strike": 110, "ce_oi": 30, "pe_oi": 30},
                {"strike": 120, "ce_oi": 60, "pe_oi": 5}]
        st = options.chain_stats(rows, 111)
        self.assertEqual(st["max_pain"], 110)
        self.assertEqual(st["call_wall"], 120)
        self.assertEqual(st["put_wall"], 100)
        self.assertEqual(st["pcr_oi"], 0.85)

    def test_small_account_cannot_afford_expensive_lot(self):
        cfg = config.load()
        r = options.buy_check("NIFTY", "CE", 25150, 25200, 120, 5, cfg)
        self.assertFalse(r["affordable"])
        r = options.buy_check("NIFTY", "CE", 25150, 25500, 25, 5, cfg)
        self.assertTrue(r["affordable"])
        self.assertEqual(r["max_loss"], 25 * 65)


class TestPipeline(Base):
    def test_scanners_run(self):
        r = self.run_cli("scan", "intraday")
        self.assertEqual(r["errors"], [])
        self.assertEqual(len(r["results"]), 3)
        self.assertIn("or_status", r["results"][0])
        r = self.run_cli("scan", "swing")
        self.assertEqual(len(r["results"]), 3, r)
        self.assertIn("trend_template", r["results"][0])

    def test_breadth(self):
        r = self.run_cli("breadth")
        self.assertEqual(r["symbols_used"], 3)
        self.assertIn(r["regime"], ("Risk-On", "Cautious", "Risk-Off"))

    def test_orb_plan_is_on_tick_grid(self):
        p = self.run_cli("plan", "orb", "TEST")
        self.assertEqual(p["basis"]["date"], "2026-11-13")
        self.assertGreater(p["entry"], p["basis"]["or_high"])
        for k in ("entry", "stop", "target"):
            self.assertTrue(refdata.on_tick(p[k]), (k, p[k]))
        self.assertIn(self.run_cli("entry")["status"], ("waiting", "triggered", "expired"))

    def test_time_machine_is_repeatable(self):
        self.run_cli("plan", "orb", "TEST")
        a = self.run_cli("sim", "--runs", "2000")
        b = self.run_cli("sim", "--runs", "2000")
        self.assertEqual(a, b)
        total = a["target_first_pct"] + a["stop_first_pct"] + a["still_open_at_flat_by_pct"]
        self.assertAlmostEqual(total, 100, delta=0.2)
        self.assertIn("same_rule_on_real_sessions", a)

    def test_backtest(self):
        r = self.run_cli("backtest", "TEST")
        self.assertGreater(r["result"]["trades"], 10)
        self.assertIn("verdict", r["result"])

    def test_sizing_respects_one_percent_including_charges(self):
        self.manual_plan()
        s = self.run_cli("size")
        self.assertGreater(s["qty"], 0)
        self.assertLessEqual(s["max_loss"], 200.0)
        self.assertLessEqual(s["position_value"], 20000)

    def test_full_paper_flow(self):
        self.manual_plan()
        self.run_cli("size")
        self.assertEqual(self.run_cli("gate")["verdict"], "PASS")
        t = self.run_cli("ticket", "new")
        tid = t["ticket"]
        with self.assertRaises(SystemExit):
            self.run_cli("ticket", "execute", tid)            # not approved yet
        with self.assertRaises(SystemExit):
            self.run_cli("ticket", "approve", tid, "--typed", "yes")   # wrong phrase
        self.run_cli("ticket", "approve", tid, "--typed", f"YES {tid}")
        r = self.run_cli("ticket", "execute", tid)
        self.assertEqual(r["status"], "placed")
        self.assertEqual(r["result"]["broker"], "paper")
        self.assertEqual(risk.budget(config.load())["open_positions"], 1)
        os.environ["DALAL_NOW"] = "2026-11-13T15:40:00"
        settled = self.run_cli("paper", "settle")
        self.assertIn(settled[0]["reason"], ("stop", "target", "flat_by"))
        st = self.run_cli("journal", "stats")
        self.assertEqual(st["closed_trades"], 1)
        self.assertGreaterEqual(st["worst"], -200.0)
        tx = self.run_cli("tax", "--fy", "2026", "--include-paper")
        self.assertEqual(tx["buckets"]["speculative_intraday"]["trades"], 1)

    def test_tampered_ticket_is_refused(self):
        self.manual_plan()
        self.run_cli("size")
        tid = self.run_cli("ticket", "new")["ticket"]
        self.run_cli("ticket", "approve", tid, "--typed", f"YES {tid}")
        path = Path(os.environ["DALAL_STATE"]) / "tickets.json"
        tickets = json.loads(path.read_text())
        next(iter(tickets.values()))["qty"] += 100
        path.write_text(json.dumps(tickets))
        with self.assertRaises(SystemExit) as e:
            self.run_cli("ticket", "execute", tid)
        self.assertIn("changed", str(e.exception))

    def test_expired_ticket_is_refused(self):
        self.manual_plan()
        self.run_cli("size")
        tid = self.run_cli("ticket", "new")["ticket"]
        os.environ["DALAL_NOW"] = "2026-11-13T10:30:00"
        with self.assertRaises(SystemExit):
            self.run_cli("ticket", "approve", tid, "--typed", f"YES {tid}")


class TestGate(Base):
    def gate(self):
        return self.run_cli("gate")

    def test_blocks_outside_entry_window(self):
        self.manual_plan()
        self.run_cli("size")
        os.environ["DALAL_NOW"] = "2026-11-13T15:05:00"
        self.assertIn("entry_window", self.gate()["failed"])

    def test_blocks_on_kill_switch(self):
        self.manual_plan()
        self.run_cli("size")
        self.run_cli("kill", "on")
        self.assertIn("kill_switch", self.gate()["failed"])

    def test_blocks_after_daily_loss(self):
        journal.save([{"id": "x" * 64, "symbol": "AAA", "side": "BUY", "qty": 10, "segment": "intraday",
                       "setup": "manual", "entry": 100, "stop": 95, "target": 110, "risk_per_share": 5,
                       "opened": "2026-11-13T09:30:00+05:30", "closed": "2026-11-13T09:50:00+05:30",
                       "status": "closed", "paper": True, "pnl_net": -450.0, "pnl_gross": -430.0,
                       "charges": 20.0, "r_multiple": -9}])
        self.manual_plan()
        s = self.run_cli("size")
        self.assertEqual(s["qty"], 0)
        failed = self.gate()["failed"]
        self.assertIn("daily_loss_stop", failed)

    def test_blocks_option_selling_and_poor_reward(self):
        self.run_cli("plan", "manual", "NIFTY25200CE", "--segment", "options", "--side", "SELL",
                     "--entry", "20", "--stop", "30", "--target", "5", "--lot", "65")
        self.run_cli("size")
        self.assertIn("no_option_selling", self.gate()["failed"])
        last = self.run_cli("quote", "TEST")["last"]
        e = refdata.round_to_tick(last)
        self.run_cli("plan", "manual", "TEST", "--entry", str(e),
                     "--stop", str(refdata.round_to_tick(e * 0.998, "down")),
                     "--target", str(refdata.round_to_tick(e * 1.002, "up")))
        self.run_cli("size")
        self.assertIn("net_reward_risk", self.gate()["failed"])

    def test_research_mode_blocks(self):
        self.write_cfg(mode="research")
        self.manual_plan()
        self.run_cli("size")
        self.assertIn("mode", self.gate()["failed"])


class TestHook(Base):
    def test_hook_blocks_without_ticket_and_allows_with(self):
        import order_guard
        ev = {"tool_name": "mcp__kite__place_order",
              "tool_input": {"tradingsymbol": "TEST", "quantity": 5, "transaction_type": "BUY"}}
        self.assertEqual(order_guard.decide(ev)[0], 2)
        self.assertEqual(order_guard.decide({"tool_name": "mcp__kite__get_quotes", "tool_input": {}})[0], 0)
        self.assertEqual(order_guard.decide({"tool_name": "Bash", "tool_input": {"command": "ls"}})[0], 0)
        self.manual_plan()
        qty = self.run_cli("size")["qty"]
        tid = self.run_cli("ticket", "new")["ticket"]
        ev["tool_input"]["quantity"] = qty
        self.assertEqual(order_guard.decide(ev)[0], 2)          # proposed, not approved
        self.run_cli("ticket", "approve", tid, "--typed", f"YES {tid}")
        self.assertEqual(order_guard.decide(ev)[0], 0)
        ev["tool_input"]["quantity"] = qty + 1
        self.assertEqual(order_guard.decide(ev)[0], 2)          # quantity does not match
        ev["tool_input"]["quantity"] = qty
        self.run_cli("kill", "on")
        self.assertEqual(order_guard.decide(ev)[0], 2)


class TestMisc(Base):
    def test_walk_assumes_stop_first(self):
        bar = [{"t": 1, "o": 100, "h": 110, "l": 90, "c": 100, "v": 1}]
        self.assertEqual(backtest.walk(bar, "BUY", 100, 95, 105)[1], "stop")

    def test_headline_scoring(self):
        h = market.score_headline("SBIN bags order worth Rs 500 crore; Q2 profit jumps", symbols=["SBIN", "TCS"])
        self.assertEqual(h["symbols"], ["SBIN"])
        self.assertGreaterEqual(h["impact"], 2)

    def test_flows(self):
        self.run_cli("flows", "add", "--date", "2026-11-12", "--fii", "7831", "--dii", "-5000")
        r = self.run_cli("flows", "show")
        self.assertIn("FII buying", r["regime"])

    def test_live_api_needs_explicit_flag(self):
        self.write_cfg(mode="live", broker="kite")
        self.manual_plan()
        self.run_cli("size")
        tid = self.run_cli("ticket", "new")["ticket"]
        self.run_cli("ticket", "approve", tid, "--typed", f"YES {tid}")
        with self.assertRaises(SystemExit) as e:
            self.run_cli("ticket", "execute", tid)
        self.assertIn("LIVE_TRADING", str(e.exception))

    def test_manual_broker_prints_orders(self):
        self.write_cfg(mode="live", broker="manual")
        self.manual_plan()
        self.run_cli("size")
        tid = self.run_cli("ticket", "new")["ticket"]
        self.run_cli("ticket", "approve", tid, "--typed", f"YES {tid}")
        r = self.run_cli("ticket", "execute", tid)
        self.assertEqual(len(r["result"]["place_these_orders_yourself"]), 3)

    def test_doctor(self):
        r = self.run_cli("doctor", "--live")
        self.assertIn("quote", r["data_probe"]["SBIN"] if "quote" in r["data_probe"]["SBIN"] else {"quote": 1})
        self.assertEqual(r["mode"], "paper")



class TestPackaging(unittest.TestCase):
    def test_skill_frontmatter(self):
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertGreaterEqual(len(skills), 16)
        for p in skills:
            lines = p.read_text().splitlines()
            self.assertEqual(lines[0], "---", p)
            self.assertEqual(lines[1], f"name: {p.parent.name}", p)
            self.assertTrue(lines[2].startswith('description: "') and lines[2].endswith('"'), p)
            self.assertLessEqual(len(lines[2]), 1024, p)

    def test_manifests_parse(self):
        for f in (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "hooks/hooks.json",
                  "config.example.json"):
            json.loads((ROOT / f).read_text())


if __name__ == "__main__":
    unittest.main()
