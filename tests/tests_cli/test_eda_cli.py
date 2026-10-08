# tests/tests_cli/test_eda_cli.py
"""#293 `xsm dlq list|show|replay|purge` and #295 `xsm asyncapi` / the
integration-events section of `xsm docs`.

Replay guard rails (X0.8): dry run by default; a real replay needs
``--no-dry-run --yes --reason``; the envelope id is reused (a double
replay is deduplicated); a changed machine is refused without
``--force``; replay and purge are audited."""

from __future__ import annotations

import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import Any, List, Tuple

from src.xstate_statemachine import MachineLogic, create_machine
from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.dlq import open_dlq, parse_age
from src.xstate_statemachine.eda import (
    Envelope,
    InboundDispatcher,
    SQLiteDeadLetterStore,
)
from src.xstate_statemachine.persistence import SQLiteStore

try:
    import jsonschema  # noqa: F401

    HAVE_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    HAVE_JSONSCHEMA = False

CFG = {
    "id": "counter",
    "version": "1",
    "initial": "on",
    "context": {"n": 0},
    "states": {
        "on": {
            "on": {
                "ADD": {
                    "actions": "add",
                    "meta": {
                        "publish": {"type": "counter.added", "data": ["n"]}
                    },
                }
            }
        }
    },
}


def _run(argv: List[str]) -> Tuple[int, str]:
    reset_console()
    saved, sys.argv = sys.argv, ["xsm", "--plain", *argv]
    buf, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(err):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if not isinstance(exc.code, int) and exc.code:
            err.write(str(exc.code))
    finally:
        sys.argv = saved
        reset_console()
    return code, buf.getvalue() + err.getvalue()


class _Fixture(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.machine_file = self.dir / "counter.json"
        self.machine_file.write_text(json.dumps(CFG), encoding="utf-8")
        self.state_url = f"sqlite:///{(self.dir / 'state.db').as_posix()}"
        self.dlq_url = f"sqlite:///{(self.dir / 'dlq.db').as_posix()}"
        # A broken deploy dead-letters one envelope.
        broken = create_machine(
            dict(CFG, actionErrorPolicy="fail"),
            logic=MachineLogic(actions={"add": lambda i, c, e, a: 1 / 0}),
        )
        self.dlq = SQLiteDeadLetterStore(self.dir / "dlq.db")
        state = SQLiteStore(self.dir / "state.db")
        self.env = Envelope.new(
            type="xsm.counter.ADD", subject="c-1", data={"api_key": "k"}
        )
        InboundDispatcher(
            state,
            lambda t: broken,
            max_attempts=1,
            dead_letters=self.dlq,
        ).handle(self.env, topic="in")
        state.close()
        # 🔒 The CLI opens its OWN connection to dlq.db. The seeding store's
        #    connection stays open only for assertions and is closed before
        #    every CLI call (`_run` below), because the Linux runners
        #    reported `database is locked` when both were open at once.
        self.dlq.close()
        self.dlq = SQLiteDeadLetterStore(self.dir / "dlq.db")
        # logic module for the fixed chart
        (self.dir / "counter_logic.py").write_text(
            "def add(i, ctx, e, a):\n    ctx['n'] += 1\n", encoding="utf-8"
        )
        sys.path.insert(0, str(self.dir))

    def tearDown(self) -> None:
        self.dlq.close()
        sys.path.remove(str(self.dir))
        sys.modules.pop("counter_logic", None)

    def replay(self, *extra: str) -> Tuple[int, str]:
        return _run(
            [
                "dlq",
                "--dlq",
                self.dlq_url,
                "replay",
                self.env.id,
                "--store",
                self.state_url,
                "--machine",
                str(self.machine_file),
                "--logic",
                "counter_logic",
                *extra,
            ]
        )


class TestDlqList(_Fixture):
    def test_list_show_json(self) -> None:
        code, out = _run(["dlq", "--dlq", self.dlq_url, "list"])
        self.assertEqual(code, 0)
        self.assertIn(self.env.id, out)
        self.assertIn("max_attempts", out)
        code, out = _run(["dlq", "--dlq", self.dlq_url, "list", "--json"])
        data = json.loads(out)
        self.assertEqual(data["count"], 1)
        code, out = _run(["dlq", "--dlq", self.dlq_url, "show", self.env.id])
        rec = json.loads(out)
        self.assertEqual(rec["envelope"]["data"]["api_key"], "***")  # X0.5
        code, out = _run(["dlq", "--dlq", self.dlq_url, "show", "nope"])
        self.assertNotEqual(code, 0)

    def test_empty_and_bare_path(self) -> None:
        empty = str(self.dir / "empty.db")
        SQLiteDeadLetterStore(empty).close()
        code, out = _run(["dlq", "--dlq", empty, "list"])
        self.assertEqual(code, 0)
        self.assertIn("no dead letters", out)
        with self.assertRaises(SystemExit):
            open_dlq("redis://x")


class TestDlqReplay(_Fixture):
    def test_dry_run_by_default(self) -> None:
        code, out = self.replay("--reason", "fixed the bug")
        self.assertEqual(code, 0, out)
        self.assertIn("dry run", out)
        self.assertIsNone(self.dlq.get(self.env.id).resolved_at)

    def test_real_replay_needs_yes_and_reason(self) -> None:
        code, out = self.replay("--no-dry-run", "--reason", "r")
        self.assertNotEqual(code, 0)
        self.assertIn("--yes", out)
        code, out = self.replay("--no-dry-run", "--yes")
        self.assertNotEqual(code, 0)
        self.assertIn("--reason", out)

    def test_replay_resolves_audits_and_dedups(self) -> None:
        code, out = self.replay(
            "--no-dry-run", "--yes", "--reason", "fixed in 1.2.3"
        )
        self.assertEqual(code, 0, out)
        self.assertIn("processed", out)
        self.assertIsNotNone(self.dlq.get(self.env.id).resolved_at)
        state = SQLiteStore(self.dir / "state.db")
        blob = json.loads(state.load("c-1").snapshot)
        self.assertEqual(blob["context"]["n"], 1)
        # the same envelope id again: the SQLite inbox says duplicate
        code, out = self.replay(
            "--no-dry-run", "--yes", "--reason", "again", "--json"
        )
        self.assertEqual(json.loads(out)["outcome"], "duplicate")
        self.assertEqual(
            json.loads(state.load("c-1").snapshot)["context"]["n"], 1
        )
        state.close()
        audit = self.dlq.audit_log()
        self.assertEqual(
            [(a["action"], a["reason"]) for a in audit],
            [("replay", "fixed in 1.2.3"), ("replay", "again")],
        )

    def test_changed_machine_refused_without_force(self) -> None:
        changed = dict(CFG, version="2")
        self.machine_file.write_text(json.dumps(changed), encoding="utf-8")
        code, out = self.replay("--no-dry-run", "--yes", "--reason", "r")
        self.assertEqual(code, 2)
        self.assertIn("--force", out)
        code, out = self.replay(
            "--no-dry-run", "--yes", "--reason", "r", "--force"
        )
        self.assertEqual(code, 0, out)

    def test_replay_needs_store_and_machine(self) -> None:
        code, out = _run(
            [
                "dlq",
                "--dlq",
                self.dlq_url,
                "replay",
                self.env.id,
                "--reason",
                "r",
            ]
        )
        self.assertNotEqual(code, 0)


class TestDlqPurge(_Fixture):
    def test_purge_guard_rails_and_audit(self) -> None:
        base = ["dlq", "--dlq", self.dlq_url, "purge"]
        self.assertNotEqual(_run(base + ["--older-than", "0s"])[0], 0)
        self.assertNotEqual(_run(base + ["--older-than", "0s", "--yes"])[0], 0)
        self.assertNotEqual(_run(base + ["--yes", "--reason", "x"])[0], 0)
        code, out = _run(
            base + ["--older-than", "30d", "--yes", "--reason", "ret"]
        )
        self.assertEqual((code, "purged 0" in out), (0, True))
        code, out = _run(
            base + ["--id", self.env.id, "--yes", "--reason", "gdpr", "--json"]
        )
        self.assertEqual(json.loads(out), {"deleted": 1})
        self.assertEqual(
            [a["reason"] for a in self.dlq.audit_log()], ["ret", "gdpr"]
        )

    def test_parse_age(self) -> None:
        self.assertEqual(parse_age("90s"), 90)
        self.assertEqual(parse_age("1.5h"), 5400)
        self.assertEqual(parse_age("7d"), 7 * 86400)
        with self.assertRaises(SystemExit):
            parse_age("soon")


class TestAsyncAPI(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.file = self.dir / "counter.json"
        self.file.write_text(json.dumps(CFG), encoding="utf-8")

    def test_stdout_and_file(self) -> None:
        code, out = _run(["asyncapi", str(self.file), "--server", "h:9092"])
        self.assertEqual(code, 0, out)
        doc = json.loads(out)
        self.assertEqual(doc["asyncapi"], "3.0.0")
        self.assertEqual(doc["servers"]["default"]["host"], "h:9092")
        target = self.dir / "out.json"
        code, _ = _run(["asyncapi", str(self.file), "-o", str(target)])
        self.assertEqual(code, 0)
        self.assertEqual(
            json.loads(target.read_text("utf-8"))["asyncapi"], "3.0.0"
        )

    @unittest.skipUnless(HAVE_JSONSCHEMA, "jsonschema not installed")
    def test_validate_flag(self) -> None:
        code, out = _run(["asyncapi", str(self.file), "--validate"])
        self.assertEqual(code, 0, out)

    def test_docs_shows_integration_events(self) -> None:
        code, out = _run(["docs", str(self.file)])
        self.assertEqual(code, 0, out)
        self.assertIn("## Integration events", out)
        self.assertIn("`counter.added`", out)
        self.assertIn("`ADD`", out)

    def test_docs_without_publications(self) -> None:
        f = self.dir / "plain.json"
        f.write_text(
            json.dumps({"id": "p", "initial": "a", "states": {"a": {}}}),
            encoding="utf-8",
        )
        code, out = _run(["docs", str(f)])
        self.assertIn("Published: _none_", out)


if __name__ == "__main__":
    unittest.main()
