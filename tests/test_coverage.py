"""`xstate_statemachine.coverage` (#270): the collector, the report and the
renderers, plus the `xsm coverage` CLI."""

from __future__ import annotations

import io
import json
import logging
import sys
import threading
import unittest
from contextlib import redirect_stdout
from typing import List

from src.xstate_statemachine import Interpreter, SyncInterpreter, plugins
from src.xstate_statemachine import create_machine
from src.xstate_statemachine.clock import SimulatedClock
from src.xstate_statemachine.coverage import (
    COVERAGE_SCHEMA_VERSION,
    CoverageCollector,
    CoverageReport,
    machine_key,
    reports_from_json,
    reports_to_html,
    reports_to_json,
    reports_to_text,
)

PARALLEL = {
    "id": "p",
    "initial": "work",
    "states": {
        "work": {
            "type": "parallel",
            "on": {"PAUSE": "paused"},
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {
                        "a1": {"on": {"NEXT": "a2"}},
                        "a2": {},
                        "hist": {"type": "history", "history": "shallow"},
                    },
                },
                "b": {
                    "initial": "b1",
                    "states": {
                        "b1": {"after": {"100": "b2"}},
                        "b2": {"always": "b3"},
                        "b3": {},
                    },
                },
            },
        },
        "paused": {"on": {"RESUME": "#p.work.a.hist", "RESET": "work"}},
    },
}

TOGGLE = {
    "id": "toggle",
    "initial": "off",
    "states": {
        "off": {"on": {"TOGGLE": "on"}},
        "on": {"on": {"TOGGLE": "off", "RESET": "off"}},
    },
}


def _quiet(case: unittest.TestCase) -> None:
    logging.disable(logging.CRITICAL)
    case.addCleanup(logging.disable, logging.NOTSET)


class TestCollector(unittest.TestCase):
    def setUp(self) -> None:
        _quiet(self)

    def test_parallel_marks_every_leaf_and_ancestor(self) -> None:
        m = create_machine(PARALLEL)
        cov = CoverageCollector()
        SyncInterpreter(m).use(cov).start()
        r = cov.report(m)
        self.assertEqual(r.states_total, 9)
        self.assertEqual(
            r.unvisited,
            ("p.paused", "p.work.a.a2", "p.work.b.b2", "p.work.b.b3"),
        )
        self.assertEqual(r.transitions_hit, 0)

    def test_after_always_and_history_restore(self) -> None:
        m = create_machine(PARALLEL)
        cov = CoverageCollector()
        clock = SimulatedClock()
        i = SyncInterpreter(m, clock=clock).use(cov).start()
        i.send("NEXT")
        clock.increment(100)
        i.send("PAUSE")
        i.send("RESUME")
        # shallow history restored a2 (not the initial a1)
        self.assertIn("p.work.a.a2", i.current_state_ids)
        r = cov.report(m)
        self.assertEqual(r.states_visited, r.states_total)
        self.assertEqual(r.unhit, (("p.paused", "on 'RESET'", "p.work"),))
        self.assertEqual((r.transitions_hit, r.transitions_total), (5, 6))

    def test_restored_interpreter_counts_its_configuration_at_start(
        self,
    ) -> None:
        m = create_machine(TOGGLE)
        i = SyncInterpreter(m).start()
        i.send("TOGGLE")
        blob = i.get_snapshot()
        cov = CoverageCollector()
        r = SyncInterpreter.from_snapshot(blob, m).use(cov)
        self.assertEqual(cov.report(m).states_visited, 0)
        r.start()
        self.assertEqual(cov.report(m).unvisited, ("toggle.off",))

    def test_global_registration_collects_direct_and_threaded(self) -> None:
        m = create_machine(TOGGLE)
        cov = CoverageCollector()
        plugins.register_global(cov)
        try:

            def work() -> None:
                SyncInterpreter(m).start().send("TOGGLE")

            threads = [threading.Thread(target=work) for _ in range(8)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
        finally:
            self.assertTrue(plugins.unregister_global(cov))
        r = cov.report(m)
        self.assertEqual(r.transitions_hit, 1)
        self.assertEqual(r.states_visited, 2)

    def test_same_structure_rebuilt_shares_a_key(self) -> None:
        m1, m2 = create_machine(TOGGLE), create_machine(TOGGLE)
        self.assertEqual(machine_key(m1), machine_key(m2))
        cov = CoverageCollector()
        SyncInterpreter(m1).use(cov).start().send("TOGGLE")
        i = SyncInterpreter(m2).use(cov).start()
        i.send("TOGGLE")
        i.send("RESET")
        self.assertEqual(len(cov.reports()), 1)
        self.assertEqual(cov.report(m1).transitions_hit, 2)

    def test_merge_and_unobserved_machine(self) -> None:
        m = create_machine(TOGGLE)
        a, b = CoverageCollector(), CoverageCollector()
        SyncInterpreter(m).use(a).start().send("TOGGLE")
        i = SyncInterpreter(m).use(b).start()
        i.send("TOGGLE")
        i.send("RESET")
        a.merge(b)
        self.assertEqual(a.report(m).transitions_hit, 2)
        empty = CoverageCollector().report(m)
        self.assertEqual((empty.states_visited, empty.transitions_hit), (0, 0))


class TestAsyncEngine(unittest.IsolatedAsyncioTestCase):
    async def test_async_engine_is_collected(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        m = create_machine(TOGGLE)
        cov = CoverageCollector()
        i = await Interpreter(m).use(cov).start()
        await i.send("TOGGLE", wait=True)
        await i.stop()
        r = cov.report(m)
        self.assertEqual((r.states_visited, r.transitions_hit), (2, 1))


class TestRenderers(unittest.TestCase):
    def setUp(self) -> None:
        _quiet(self)
        m = create_machine(TOGGLE)
        cov = CoverageCollector()
        SyncInterpreter(m).use(cov).start().send("TOGGLE")
        self.report = cov.report(m)

    def test_json_schema_v1_round_trips(self) -> None:
        doc = json.loads(self.report.to_json())
        self.assertEqual(doc["version"], COVERAGE_SCHEMA_VERSION)
        self.assertEqual(
            sorted(doc["machines"][0]),
            ["key", "machine", "states", "transitions"],
        )
        self.assertEqual(
            sorted(doc["machines"][0]["transitions"]),
            ["hit", "percent", "total", "unhit"],
        )
        self.assertEqual(
            reports_from_json(self.report.to_json()), [self.report]
        )

    def test_json_rejects_other_versions_and_garbage(self) -> None:
        for bad in ('{"version": 2, "machines": []}', "nope", "[]"):
            with self.assertRaises(ValueError):
                reports_from_json(bad)
        with self.assertRaises(ValueError):
            reports_from_json('{"version": 1, "machines": [{}]}')

    def test_text_shape(self) -> None:
        text = self.report.to_text()
        self.assertEqual(
            text.splitlines(),
            [
                "---- xstate coverage ----",
                "toggle            states 2/2 (100%)  transitions 1/3 (33.3%)",
                "  unhit:     on --RESET--> off, on --TOGGLE--> off",
            ],
        )
        self.assertIn("(no machines observed)", reports_to_text([]))

    def test_html_is_escaped_and_self_contained(self) -> None:
        r = CoverageReport("<m>", "<m>@x", 0, 1, ("<m>.<s>",), 0, 0, ())
        page = reports_to_html([r, self.report])
        self.assertNotIn("<m>", page)
        self.assertIn("&lt;m&gt;", page)
        self.assertNotIn("<script", page)
        self.assertEqual(r.state_percent, 0.0)
        self.assertEqual(r.transition_percent, 100.0)  # nothing to hit
        self.assertTrue(r.to_html().startswith("<!DOCTYPE html>"))


def _cli(argv: List[str]) -> tuple:
    from src.xstate_statemachine.cli.__main__ import main
    from src.xstate_statemachine.cli.commands import reset_console

    reset_console()
    saved, sys.argv = sys.argv, ["xsm", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code or 0
    finally:
        sys.argv = saved
        reset_console()
    return code, buf.getvalue()


class TestCoverageCli(unittest.TestCase):
    def setUp(self) -> None:
        _quiet(self)
        import tempfile
        import pathlib

        m = create_machine(TOGGLE)
        cov = CoverageCollector()
        SyncInterpreter(m).use(cov).start().send("TOGGLE")
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = pathlib.Path(tmp.name) / "cov.json"
        self.path.write_text(reports_to_json(cov.reports()), "utf-8")

    def test_plain(self) -> None:
        code, out = _cli(["coverage", str(self.path), "--plain"])
        self.assertEqual(code, 0, out)
        self.assertIn("toggle", out)
        self.assertIn("1/3 (33.33%)", out)
        self.assertIn("unhit      on --RESET--> off", out)

    def test_json(self) -> None:
        code, out = _cli(["coverage", str(self.path), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["version"], 1)

    def test_fail_under(self) -> None:
        code, _ = _cli(["coverage", str(self.path), "--fail-under", "50"])
        self.assertEqual(code, 1)
        code, _ = _cli(["coverage", str(self.path), "--fail-under", "30"])
        self.assertEqual(code, 0)

    def test_bad_file(self) -> None:
        self.path.write_text("{}", "utf-8")
        code, _ = _cli(["coverage", str(self.path), "--plain"])
        self.assertEqual(code, 1)
        code, _ = _cli(["coverage", str(self.path) + ".missing"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
