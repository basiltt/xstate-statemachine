# tests/tests_cli/test_battle_293_b_dlq.py
"""#293 battle (adversary B): `xsm dlq` / `xsm asyncapi` as an operator
types them. Every refused input is ONE line and exit code 2 -- never a
traceback, never a silently created empty store."""

from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from typing import List, Tuple

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.eda import SQLiteDeadLetterStore


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
    finally:
        sys.argv = saved
        reset_console()
    return code, buf.getvalue() + err.getvalue()


class TestOperatorInput(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.db = self.dir / "dlq.db"
        SQLiteDeadLetterStore(self.db).close()
        self.url = f"sqlite:///{self.db.as_posix()}"
        self.machine = self.dir / "m.json"
        self.machine.write_text(
            json.dumps({"id": "m", "initial": "a", "states": {"a": {}}}),
            encoding="utf-8",
        )
        self.junk = self.dir / "junk.db"
        self.junk.write_text("not a database", encoding="utf-8")

    def assert_refused(self, argv: List[str], needle: str) -> None:
        code, out = _run(argv)
        self.assertEqual(code, 2, out)
        self.assertNotIn("Traceback", out)
        self.assertIn(needle, out)

    def dlq(self, *rest: str) -> List[str]:
        return ["dlq", "--dlq", self.url, *rest]

    def replay(self, *rest: str) -> List[str]:
        return self.dlq(
            "replay", "x", "--reason", "r", "--store", self.url, *rest
        )

    def test_empty_store_lists_and_json_is_stable(self) -> None:
        code, out = _run(self.dlq("list", "--json"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"count": 0, "dead_letters": []})

    def test_missing_file_is_not_silently_created(self) -> None:
        ghost = self.dir / "typo.db"
        self.assert_refused(["dlq", "--dlq", str(ghost), "list"], "no such")
        self.assert_refused(
            ["dlq", "--dlq", f"sqlite:///{ghost.as_posix()}", "list"],
            "no such",
        )
        self.assertFalse(ghost.exists())

    def test_bad_scheme_and_non_sqlite_file(self) -> None:
        self.assert_refused(["dlq", "--dlq", "redis://x", "list"], "sqlite")
        self.assert_refused(
            ["dlq", "--dlq", str(self.junk), "list"], "cannot open"
        )

    def test_show_unknown_id_and_bad_limit(self) -> None:
        self.assert_refused(self.dlq("show", "nope"), "no dead letter")
        self.assert_refused(self.dlq("list", "--limit", "0"), "--limit")

    def test_replay_missing_arguments(self) -> None:
        self.assert_refused(self.dlq("replay", "x"), "--reason")
        self.assert_refused(
            self.dlq("replay", "x", "--reason", "r"), "--store"
        )
        self.assert_refused(
            self.dlq("replay", "x", "--reason", "r", "--store", self.url),
            "--machine",
        )
        self.assert_refused(
            self.dlq("replay", "x", "--no-dry-run", "--reason", "r"), "--yes"
        )

    def test_replay_bad_machine_and_logic(self) -> None:
        self.assert_refused(
            self.replay("--machine", str(self.dir / "none.json")),
            "cannot load machine",
        )
        self.assert_refused(
            self.replay("--machine", str(self.junk)), "cannot load machine"
        )
        self.assert_refused(
            self.replay("--machine", str(self.machine), "--logic", "no.mod"),
            "cannot import --logic",
        )
        self.assert_refused(
            self.replay("--machine", str(self.machine)), "no dead letter"
        )

    def test_purge_bad_age(self) -> None:
        for age in ("7w", "-1d", "d", ""):
            self.assert_refused(
                self.dlq(
                    "purge", "--older-than", age, "--yes", "--reason", "r"
                ),
                "",
            )
        code, out = _run(
            self.dlq(
                "purge",
                "--older-than",
                "7d",
                "--yes",
                "--reason",
                "r",
                "--json",
            )
        )
        self.assertEqual((code, json.loads(out)), (0, {"deleted": 0}))

    def test_asyncapi_bad_files(self) -> None:
        self.assert_refused(
            ["asyncapi", str(self.dir / "none.json")], "cannot load machine"
        )
        self.assert_refused(["asyncapi", str(self.junk)], "cannot load")
        code, out = _run(["asyncapi", str(self.machine)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["asyncapi"], "3.0.0")


if __name__ == "__main__":
    unittest.main()
