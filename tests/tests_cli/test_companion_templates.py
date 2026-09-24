"""Tests for the companion code-generation templates: `pytest`, `typed`,
`plugin` (and their `--with-*` add-on form).

The bar for `pytest` is the real one: the generated test module is
EXECUTED against every Stately fixture and must pass, because the
scaffold's assertions are recorded from the engine at generation time.
"""

from __future__ import annotations

import ast
import glob
import io
import json
import logging
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import Any, Dict, List

from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands.generate import (
    COMPANIONS,
    is_companion,
    requested_companions,
)
from src.xstate_statemachine.cli.extractor import extract_logic_names
from src.xstate_statemachine.cli.strategies import (
    STRATEGY_REGISTRY,
    get_strategy,
)
from src.xstate_statemachine.cli.strategies._trace import record
from src.xstate_statemachine.cli.strategies.base import GenerationContext
from src.xstate_statemachine.cli.utils import camel_to_snake

ROOT = pathlib.Path(__file__).resolve().parents[2]
ALL_FIXTURES = sorted(
    glob.glob(
        str(ROOT / "tests" / "tests_cli" / "stately_machines" / "*.json")
    )
)
SRC = str(ROOT / "src")


def _buildable(path: str) -> bool:
    """The corpus includes exports the LIBRARY refuses somewhere along the
    reachable walk (a compound state with no `initial`, a guard literally
    named `and`, a malformed root). The companion templates record a run
    of the machine, so the probe IS a recording; the files it rejects are
    exercised separately by `TestUnbuildableFixturesFailLoudly`."""
    try:
        record(json.load(open(path, encoding="utf-8")))
        return True
    except Exception:  # noqa: BLE001 -- any refusal disqualifies
        return False


logging.disable(logging.CRITICAL)
FIXTURES = [f for f in ALL_FIXTURES if _buildable(f)]
UNBUILDABLE = [f for f in ALL_FIXTURES if f not in FIXTURES]
logging.disable(logging.NOTSET)


def _ctx(
    config: Dict[str, Any], filename: str, *, is_async: bool = False
) -> GenerationContext:
    actions, guards, services = extract_logic_names(config)
    name = camel_to_snake(config["id"].replace(" ", "_"))
    return GenerationContext(
        actions=actions,
        guards=guards,
        services=services,
        is_async=is_async,
        log=False,
        machine_name=name,
        machine_id=config["id"],
        machine_names=[name],
        machine_ids=[config["id"]],
        file_count=1,
        configs=[config],
        json_filenames=[filename],
        hierarchy=False,
        sleep=False,
        sleep_time=0,
        loader=False,
    )


def _run(argv: List[str]) -> tuple:
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
    return code, buf.getvalue()


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


class TestRegistry(_Quiet):
    def test_companions_are_registered(self) -> None:
        for t in ("pytest", "typed", "plugin"):
            self.assertIn(t, STRATEGY_REGISTRY)
            self.assertEqual(get_strategy(t).name, t)
            self.assertTrue(is_companion(t))
        self.assertFalse(is_companion("pythonic-class"))

    def test_requested_companions_merge_primary_and_flags(self) -> None:
        class A:  # noqa: D401 -- a bare namespace
            with_tests = True
            with_types = False
            with_plugin = True

        self.assertEqual(
            requested_companions(A(), "pythonic-class"), ["pytest", "plugin"]
        )
        self.assertEqual(
            requested_companions(A(), "typed"), ["typed", "pytest", "plugin"]
        )
        self.assertEqual(sorted(COMPANIONS), ["plugin", "pytest", "typed"])


class TestTraceRecorder(_Quiet):
    def test_records_a_walk_with_states_after_each_step(self) -> None:
        cfg = json.load(open(FIXTURES[0], encoding="utf-8"))
        t = record(cfg)
        self.assertTrue(t.initial_state_ids)
        for s in t.steps:
            self.assertIn(s.kind, ("event", "clock"))
            self.assertTrue(s.state_ids)
        self.assertEqual(
            set(t.events) - set(t.unreached_events),
            {s.event for s in t.steps if s.event},
        )


class TestCompanionsCompileForEveryFixture(_Quiet):
    """Every companion, every fixture: valid Python that imports the library."""

    def test_typed_and_plugin_compile_and_exec(self) -> None:
        for fp in FIXTURES:
            cfg = json.load(open(fp, encoding="utf-8"))
            for template in ("typed", "plugin"):
                with self.subTest(
                    fixture=pathlib.Path(fp).name, template=template
                ):
                    code = get_strategy(template).generate_logic(
                        _ctx(cfg, pathlib.Path(fp).name)
                    )
                    ast.parse(code)
                    ns: Dict[str, Any] = {}
                    exec(
                        compile(code, f"<{template}>", "exec"), ns
                    )  # noqa: S102
                    if template == "typed":
                        self.assertIn("EventType", ns)
                        self.assertIn("logic", ns)
                        ns["logic"]()  # binds the stubs
                    else:
                        cls = [
                            v
                            for k, v in ns.items()
                            if k.endswith("Observer") and isinstance(v, type)
                        ]
                        self.assertEqual(len(cls), 1)
                        inst = cls[0]()
                        self.assertTrue(
                            hasattr(inst, "on_chain_budget_exceeded")
                        )

    def test_pytest_scaffold_parses_for_every_fixture(self) -> None:
        for fp in FIXTURES:
            cfg = json.load(open(fp, encoding="utf-8"))
            with self.subTest(fixture=pathlib.Path(fp).name):
                code = get_strategy("pytest").generate_logic(
                    _ctx(cfg, pathlib.Path(fp).name)
                )
                tree = ast.parse(code)
                names = {
                    n.name for n in tree.body if isinstance(n, ast.FunctionDef)
                }
                self.assertIn("test_initial_state", names)
                self.assertIn("test_snapshot_round_trip", names)


class TestGeneratedPytestSuitesPass(_Quiet):
    """The point of the scaffold: the tests it writes are green against the
    machine they were recorded from. Run a representative slice of fixtures
    in one subprocess (all 104 would take minutes)."""

    SAMPLE = [
        f for f in FIXTURES if pathlib.Path(f).name[0].lower() in "abcdlmpst"
    ][:24]

    def test_generated_tests_are_green(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            for fp in self.SAMPLE:
                cfg = json.load(open(fp, encoding="utf-8"))
                name = pathlib.Path(fp).name
                (out / name).write_text(json.dumps(cfg), encoding="utf-8")
                code = get_strategy("pytest").generate_logic(_ctx(cfg, name))
                (
                    out
                    / f"test_{camel_to_snake(cfg['id'].replace(' ', '_'))}.py"
                ).write_text(code, encoding="utf-8")
            env = {
                **os.environ,
                "PYTHONPATH": SRC,
                "PYTHONIOENCODING": "utf-8",
            }
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    # 📌 Pin the rootdir: with none given the child pytest
                    #    walks up from the temp dir and, on the Windows
                    #    runner, trips over the junction 'C:\Documents and
                    #    Settings' (PermissionError) while probing for ini
                    #    files.
                    f"--rootdir={out}",
                    str(out),
                ],
                capture_output=True,
                text=True,
                env=env,
                cwd=str(out),
                timeout=600,
            )
            self.assertEqual(
                proc.returncode, 0, proc.stdout[-3000:] + proc.stderr[-1000:]
            )
            self.assertIn("passed", proc.stdout)


class TestUnbuildableFixturesFailLoudly(_Quiet):
    """A companion asked for on a machine the library refuses must raise the
    library's own error, not emit a file that cannot import."""

    def test_refused_with_the_library_error(self) -> None:
        self.assertTrue(
            UNBUILDABLE, "corpus should contain a few unbuildable exports"
        )
        for fp in UNBUILDABLE:
            cfg = json.load(open(fp, encoding="utf-8"))
            with self.subTest(fixture=pathlib.Path(fp).name):
                with self.assertRaises(Exception):
                    get_strategy("pytest").generate_logic(
                        _ctx(cfg, pathlib.Path(fp).name)
                    )


class TestCliFlags(_Quiet):
    def test_with_flags_emit_companions_next_to_primary(self) -> None:
        cfg = json.load(open(FIXTURES[0], encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "m.json"
            src.write_text(json.dumps(cfg), encoding="utf-8")
            code, out = _run(
                [
                    "gt",
                    str(src),
                    "-t",
                    "pythonic-class",
                    "--with-tests",
                    "--with-types",
                    "--with-plugin",
                    "-o",
                    tmp,
                    "-f",
                    "--plain",
                ]
            )
            self.assertEqual(code, 0, out)
            files = sorted(p.name for p in pathlib.Path(tmp).glob("*.py"))
            self.assertTrue(any(f.startswith("test_") for f in files), files)
            self.assertTrue(any(f.endswith("_types.py") for f in files), files)
            self.assertTrue(
                any(f.endswith("_observer.py") for f in files), files
            )
            self.assertIn("Generated pytest file", out)
            # --check: everything is up to date
            code, out = _run(
                [
                    "gt",
                    str(src),
                    "-t",
                    "pythonic-class",
                    "--with-tests",
                    "-o",
                    tmp,
                    "--check",
                    "--plain",
                ]
            )
            self.assertEqual(code, 0, out)
            self.assertIn("up to date", out)

    def test_companion_as_primary_writes_only_that_file(self) -> None:
        cfg = json.load(open(FIXTURES[1], encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "m.json"
            src.write_text(json.dumps(cfg), encoding="utf-8")
            code, out = _run(
                ["gt", str(src), "-t", "typed", "-o", tmp, "-f", "--plain"]
            )
            self.assertEqual(code, 0, out)
            files = sorted(p.name for p in pathlib.Path(tmp).glob("*.py"))
            self.assertEqual(len(files), 1)
            self.assertTrue(files[0].endswith("_types.py"))


if __name__ == "__main__":
    unittest.main()
