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
        self.assertEqual(
            sorted(COMPANIONS),
            ["fastapi-router", "plugin", "pydantic-models", "pytest", "typed"],
        )


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

    def test_generated_tests_find_the_json_one_level_up(self) -> None:
        """`xsm gt machine.json --with-tests -o generated/` -- the layout the
        docs recommend -- leaves the JSON in the PARENT of the output dir.
        The scaffold used `Path(__file__).with_name(...)`, which only looked
        beside the test module, so the very first real-world run failed with
        FileNotFoundError. Now: beside the module first, then one level up
        (the same lookup the runner template already used)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            fp = next(f for f in FIXTURES if f.endswith("AdvancePayment.json"))
            (root / "payment.json").write_text(
                pathlib.Path(fp).read_text(encoding="utf-8"), encoding="utf-8"
            )
            code, text = _run(
                [
                    "gt",
                    str(root / "payment.json"),
                    "--with-tests",
                    "-o",
                    str(root / "generated"),
                    "--plain",
                    "-f",
                ]
            )
            self.assertEqual(code, 0, text)
            tests = list((root / "generated").glob("test_*.py"))
            self.assertEqual(len(tests), 1, tests)
            self.assertNotIn("payment.json", os.listdir(root / "generated"))
            proc = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    "-q",
                    "-p",
                    "no:cacheprovider",
                    f"--rootdir={root / 'generated'}",
                    str(root / "generated"),
                ],
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "PYTHONPATH": SRC,
                    "PYTHONIOENCODING": "utf-8",
                },
                cwd=str(root / "generated"),
                timeout=600,
            )
            self.assertEqual(
                proc.returncode, 0, proc.stdout[-3000:] + proc.stderr[-1000:]
            )


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


class TestWebCompanions(_Quiet):
    """`fastapi-router` / `pydantic-models` (#279): registered, flagged,
    parse for the WHOLE corpus (they read the raw config, so even exports
    the engine refuses generate), Python 3.9-safe."""

    def test_api_and_models_are_registered_companions(self) -> None:
        for t, flag, suffix in (
            ("fastapi-router", "with_api", "{name}_api.py"),
            ("pydantic-models", "with_models", "{name}_models.py"),
        ):
            self.assertIn(t, STRATEGY_REGISTRY)
            self.assertEqual(get_strategy(t).name, t)
            self.assertTrue(is_companion(t))
            self.assertEqual(COMPANIONS[t], (flag, suffix))

    def test_api_and_models_parse_for_the_whole_corpus(self) -> None:
        for fp in ALL_FIXTURES:
            cfg = json.load(open(fp, encoding="utf-8"))
            cfg.setdefault("id", pathlib.Path(fp).stem)
            for template in ("pydantic-models", "fastapi-router"):
                with self.subTest(
                    fixture=pathlib.Path(fp).name, template=template
                ):
                    code = get_strategy(template).generate_logic(
                        _ctx(cfg, pathlib.Path(fp).name)
                    )
                    tree = ast.parse(code)
                    # 🐍 3.9-safe: no PEP 604 `X | Y` in annotations.
                    for node in ast.walk(tree):
                        self.assertNotIsInstance(
                            getattr(node, "annotation", None), ast.BinOp
                        )

    def test_models_flag_types_the_router_bodies(self) -> None:
        cfg = json.load(open(FIXTURES[0], encoding="utf-8"))
        ctx = _ctx(cfg, "m.json")
        plain = get_strategy("fastapi-router").generate_logic(ctx)
        self.assertNotIn("_models import", plain)
        ctx.companions = ("pydantic-models", "fastapi-router")
        typed = get_strategy("fastapi-router").generate_logic(ctx)
        self.assertIn(f"from {ctx.machine_name}_models import", typed)

    def test_router_emits_a_closed_authorize_stub(self) -> None:
        cfg = json.load(open(FIXTURES[0], encoding="utf-8"))
        code = get_strategy("fastapi-router").generate_logic(
            _ctx(cfg, "m.json")
        )
        self.assertIn("def authorize(", code)
        self.assertIn("raise NotImplementedError(", code)
        self.assertIn("X0.1", code)
        self.assertIn("🔐", code)

    def test_with_api_and_models_flags_write_both(self) -> None:
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
                    "--with-api",
                    "--with-models",
                    "-o",
                    tmp,
                    "-f",
                    "--plain",
                ]
            )
            self.assertEqual(code, 0, out)
            files = sorted(p.name for p in pathlib.Path(tmp).glob("*.py"))
            self.assertTrue(any(f.endswith("_api.py") for f in files), files)
            self.assertTrue(
                any(f.endswith("_models.py") for f in files), files
            )


class TestPytestFixturesFlag(_Quiet):
    """`xsm gt -t pytest --fixtures` (#268): the scaffold on the `[testing]`
    plugin's marker + `xsm_*` fixtures. Without the flag the output is the
    hand-built module, byte for byte."""

    SAMPLE = [
        f
        for f in FIXTURES
        if pathlib.Path(f).name in ("AdvancePayment.json", "kettle.json")
    ] or FIXTURES[:2]

    def test_default_output_is_unchanged_by_the_new_field(self) -> None:
        cfg = json.load(open(FIXTURES[0], encoding="utf-8"))
        name = pathlib.Path(FIXTURES[0]).name
        plain = get_strategy("pytest").generate_logic(_ctx(cfg, name))
        ctx = _ctx(cfg, name)
        ctx.fixtures = False
        self.assertEqual(plain, get_strategy("pytest").generate_logic(ctx))
        self.assertIn("def stub_logic(", plain)
        self.assertNotIn("xstate_machine", plain)

    def test_fixtures_output_uses_the_plugin_surface(self) -> None:
        cfg = json.load(open(FIXTURES[0], encoding="utf-8"))
        name = pathlib.Path(FIXTURES[0]).name
        ctx = _ctx(cfg, name)
        ctx.fixtures = True
        code = get_strategy("pytest").generate_logic(ctx)
        ast.parse(code)
        self.assertIn(
            "pytestmark = pytest.mark.xstate_machine(str(CONFIG_PATH))", code
        )
        for needle in ("xsm_interp", "xsm_clock", "xsm_ran", "xsm_machine"):
            self.assertIn(needle, code)
        self.assertNotIn("def stub_logic(", code)
        self.assertNotIn("MachineLogic", code)
        self.assertNotIn("create_machine", code)
        if extract_logic_names(cfg)[1]:
            self.assertIn("@pytest.mark.xstate_guards_false(*GUARDS)", code)

    def test_cli_flag_is_threaded_through(self) -> None:
        cfg = json.load(open(FIXTURES[0], encoding="utf-8"))
        with tempfile.TemporaryDirectory() as tmp:
            src = pathlib.Path(tmp) / "m.json"
            src.write_text(json.dumps(cfg), encoding="utf-8")
            code, out = _run(
                [
                    "gt",
                    str(src),
                    "-t",
                    "pytest",
                    "--fixtures",
                    "-o",
                    tmp,
                    "-f",
                    "--plain",
                ]
            )
            self.assertEqual(code, 0, out)
            [test_file] = pathlib.Path(tmp).glob("test_*.py")
            text = test_file.read_text(encoding="utf-8")
            self.assertIn("pytest.mark.xstate_machine", text)
            self.assertIn("--fixtures", text)  # provenance in the header

    def test_generated_fixture_tests_are_green(self) -> None:
        """The plugin is loaded by its entry point in the child pytest
        (the package is installed in CI cells); skip cleanly otherwise."""
        from importlib.metadata import entry_points

        eps = entry_points()
        group = (
            eps.select(group="pytest11")
            if hasattr(eps, "select")
            else eps.get("pytest11", [])
        )
        if not any(
            "xstate_statemachine.contrib.testing" in e.value for e in group
        ):
            self.skipTest("plugin entry point not installed in this env")
        with tempfile.TemporaryDirectory() as tmp:
            out = pathlib.Path(tmp)
            for fp in self.SAMPLE:
                cfg = json.load(open(fp, encoding="utf-8"))
                name = pathlib.Path(fp).name
                (out / name).write_text(json.dumps(cfg), encoding="utf-8")
                ctx = _ctx(cfg, name)
                ctx.fixtures = True
                code = get_strategy("pytest").generate_logic(ctx)
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


if __name__ == "__main__":
    unittest.main()
