"""Tests for `xsm simulate`: the Session engine, the scripted driver, the
JSON output, and the interactive loop driven by an injected key source."""

from __future__ import annotations

import io
import json
import logging
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import List

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import (
    configure_console,
    reset_console,
)
from src.xstate_statemachine.cli.commands.simulate import (
    Session,
    interactive,
    parse_events_arg,
    run_script,
)
from src.xstate_statemachine.cli.ui import Capabilities, Console
from src.xstate_statemachine.cli.ui import keys as K

ROOT = pathlib.Path(__file__).resolve().parents[2]
PAYMENT = (
    ROOT / "tests" / "tests_cli" / "stately_machines" / "AdvancePayment.json"
)

TOGGLE = {
    "id": "t",
    "initial": "off",
    "context": {"n": 0},
    "states": {
        "off": {"on": {"TOGGLE": {"target": "on", "actions": ["count"]}}},
        "on": {
            "on": {"TOGGLE": {"target": "off", "guard": "allowed"}},
            "after": {"300": "off"},
        },
    },
}


def _run(argv: List[str]) -> tuple:
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


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)
        reset_console()
        self.addCleanup(reset_console)


class TestSession(_Quiet):
    def test_send_advance_undo_reset(self) -> None:
        s = Session(TOGGLE)
        self.assertEqual(s.active, {"t.off"})
        self.assertEqual(s.enabled_events, ["TOGGLE"])
        r = s.send("TOGGLE")
        self.assertTrue(r.changed)
        self.assertEqual(r.actions, ["count"])
        self.assertEqual(s.active, {"t.on"})
        self.assertEqual(s.armed_timers, [("t.on", 300)])
        r = s.advance(301)
        self.assertEqual(r.kind, "clock")
        self.assertEqual(s.active, {"t.off"})
        r = s.undo()
        self.assertIsNotNone(r)
        self.assertEqual(s.active, {"t.on"})
        s.reset()
        self.assertEqual(s.active, {"t.off"})
        self.assertEqual(s.clock.now(), 0.0)
        self.assertIsNone(s.undo())  # history cleared by reset
        s.stop()

    def test_guard_override_denies(self) -> None:
        s = Session(TOGGLE, guards={"allowed": False})
        s.send("TOGGLE")
        r = s.send("TOGGLE")
        self.assertTrue(r.denied)
        self.assertFalse(r.changed)
        s.set_guard("allowed", True)
        self.assertTrue(s.send("TOGGLE").changed)
        s.stop()

    def test_to_json_shape(self) -> None:
        s = Session(TOGGLE)
        s.send("TOGGLE")
        d = s.to_json()
        json.dumps(d)
        self.assertEqual(d["active"], ["t.on"])
        self.assertEqual(d["history"][0]["label"], "TOGGLE")
        self.assertIn("enabled_events", d)
        s.stop()


class TestScripted(_Quiet):
    def test_parse_events_arg(self) -> None:
        self.assertEqual(
            parse_events_arg("A, +500,B", "10"),
            [{"send": "A"}, {"clock": 500.0}, {"send": "B"}, {"clock": 10.0}],
        )
        self.assertEqual(parse_events_arg(None, None), [])

    def test_run_script_commands(self) -> None:
        s = Session(TOGGLE)
        run_script(
            s,
            [
                {"send": "TOGGLE"},
                {"guard": "allowed", "value": False},
                {"send": "TOGGLE"},
                {"undo": True},
                {"clock": 301},
            ],
        )
        self.assertEqual(
            [r.label for r in s.history],
            ["TOGGLE", "TOGGLE", "undo", "+301 ms"],
        )
        self.assertEqual(s.active, {"t.off"})
        with self.assertRaises(ValueError):
            run_script(s, [{"bogus": 1}])
        s.stop()

    def test_cli_events_and_json(self) -> None:
        code, out = _run(
            ["simulate", str(PAYMENT), "-e", "SUBMIT,+2001", "--plain"]
        )
        self.assertEqual(code, 0, out)
        self.assertIn("SUBMIT", out)
        self.assertIn("success", out)
        code, out = _run(
            [
                "sim",
                str(PAYMENT),
                "-e",
                "SUBMIT",
                "--guards-false",
                "isFormValid",
                "--json",
            ]
        )
        self.assertEqual(code, 0)
        d = json.loads(out)
        self.assertTrue(d["history"][0]["denied"])
        self.assertEqual(d["active"], ["Advance payment flow.editing"])

    def test_cli_script_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            m = pathlib.Path(tmp) / "t.json"
            m.write_text(json.dumps(TOGGLE), encoding="utf-8")
            sc = pathlib.Path(tmp) / "s.json"
            sc.write_text(
                json.dumps([{"send": "TOGGLE"}, {"clock": 301}]),
                encoding="utf-8",
            )
            code, out = _run(["sim", str(m), "--script", str(sc), "--json"])
            self.assertEqual(code, 0, out)
            self.assertEqual(json.loads(out)["active"], ["t.off"])

    def test_cli_off_tty_with_no_events_is_a_scripted_noop_with_a_hint(
        self,
    ) -> None:
        code, out = _run(["sim", str(PAYMENT), "--plain"])
        self.assertEqual(code, 0)
        self.assertIn("no events given", out)

    def test_cli_bad_file_exits_1(self) -> None:
        code, out = _run(["sim", "/nope.json", "--plain"])
        self.assertEqual(code, 1)


class TestInteractive(_Quiet):
    """Drive the live loop with a scripted key source on a styled (but
    non-animated) console so the prompts render and the branches run."""

    CAPS = Capabilities(
        tty=True,
        color=True,
        truecolor=True,
        unicode=True,
        animate=False,
        width=100,
        height=30,
    )

    def _console(self) -> io.StringIO:
        import src.xstate_statemachine.cli.commands as cmds

        buf = io.StringIO()
        cmds._console = Console(self.CAPS, buf)
        return buf

    def test_send_timer_undo_history_quit(self) -> None:
        buf = self._console()
        s = Session(TOGGLE)
        # enter → send TOGGLE (goes to on); esc → command mode; t → fire timer
        # (back to off); esc; u → undo (on); esc; h → history; esc; q → quit
        keys = "enter esc t esc u esc h esc q"
        interactive(s, source=K.scripted(keys))
        out = buf.getvalue()
        self.assertIn("TOGGLE", out)
        self.assertIn("+301 ms", out)
        self.assertIn("undo", out)
        self.assertIn("bye", out)
        self.assertEqual(
            [r.kind for r in s.history], ["event", "clock", "undo"]
        )
        s.stop()

    def test_guards_menu_and_clock_prompt_and_snapshot(self) -> None:
        buf = self._console()
        s = Session(TOGGLE)
        # enter (TOGGLE → on); esc; g → guards multiselect: space toggles
        # 'allowed' off, enter. With the only guard False, `can("TOGGLE")`
        # is False so the event picker is NOT offered (denied events are
        # never on the menu) and keys go straight to command mode:
        # c → clock prompt (clear the default, type 500, enter). +500 ms
        # fires the 300 ms `after`, so the machine is back in `off` where
        # TOGGLE IS enabled: the picker returns, and `esc` is needed before
        # each command again: s → snapshot; r → reset; q → quit.
        keys = (
            "enter esc g space enter "
            "c backspace backspace backspace backspace 5 0 0 enter "
            "esc s esc r esc q"
        )
        interactive(s, source=K.scripted(keys))
        out = buf.getvalue()
        self.assertIn("Guards returning True", out)
        self.assertNotIn("denied", out)  # the guarded event was never offered
        self.assertIn("+500 ms", out)
        self.assertIn('"state_ids"', out)  # snapshot printed
        self.assertIn("reset", out)
        self.assertEqual(
            [r.kind for r in s.history], ["event", "clock", "reset"]
        )
        s.stop()

    def test_no_enabled_events_falls_through_to_commands(self) -> None:
        buf = self._console()
        final_cfg = {
            "id": "f",
            "initial": "a",
            "states": {"a": {"type": "final"}},
        }
        s = Session(final_cfg)
        interactive(s, source=K.scripted("q"))
        self.assertIn("bye", buf.getvalue())
        s.stop()


if __name__ == "__main__":
    unittest.main()
