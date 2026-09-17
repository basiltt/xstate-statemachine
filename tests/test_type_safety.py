# tests/test_type_safety.py
# -----------------------------------------------------------------------------
# 🧷 Type safety -- what a USER's type checker sees
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `py.typed` and the `Typing :: Typed` classifier
# promise that a developer who type-checks code USING this library gets
# real errors for real mistakes and NO errors for correct code. That promise
# cannot be verified by type-checking the library itself; it has to be
# verified by type-checking representative user programs. So this module
# does exactly that: each program below is a small, realistic use of the
# public API in which every line tagged `# E:` is a genuine bug a checker
# must flag, and every untagged line is correct code a checker must accept.
#
# A false NEGATIVE (missed bug) means the types are too loose to help. A
# false POSITIVE (error on correct code) is worse: it teaches users to write
# `# type: ignore` and stop trusting the checker. Both fail this test.
#
# mypy is the reference checker (it is the one in `pip install -e .[dev]`);
# pyright is run too when it is installed, because the two disagree in
# instructive ways and a library that claims to be typed should satisfy both.
# -----------------------------------------------------------------------------
"""Type-checks representative user programs against the public API."""

import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from typing import Dict, List, Optional, Set, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Every program imports from the installed name; the test rewrites it.
PROGRAMS: Dict[str, str] = {}

PROGRAMS["typed_context_sync"] = """
    from typing import Optional, TypedDict
    from xstate_statemachine import SyncInterpreter, MachineLogic, create_machine

    class Ctx(TypedDict):
        count: int
        user: Optional[str]

    def inc(interp: "SyncInterpreter[Ctx]", ctx: Ctx, event: object, action_def: object) -> None:
        ctx["count"] += 1
        ctx["cuont"] = 3                                  # E: typeddict-unknown-key

    def ready(ctx: Ctx, event: object) -> bool:
        return ctx["count"] >= 0

    initial: Ctx = {"count": 0, "user": None}
    machine = create_machine(
        {"id": "m", "initial": "a", "context": initial,
         "states": {"a": {"on": {"GO": {"target": "b", "guard": "ready", "actions": ["inc"]}}}, "b": {}}},
        logic=MachineLogic(actions={"inc": inc}, guards={"ready": ready}),
        context_type=Ctx,
    )
    s = SyncInterpreter(machine).start()
    n: int = s.context["count"]
    u: Optional[str] = s.context["user"]
    bad: str = s.context["count"]                         # E: assignment
    s.context["nope"]                                     # E: typeddict-item
    s.send("GO")
    s.send("GO", wait=False)
    r = s.send("GO", wait=True)
    changed: bool = r.changed
    r.changed.upper()                                     # E: attr-defined
    r.state_ids.add("x")                                  # E: attr-defined
    s.send(123)                                           # E: call-overload
    s.send("GO", wait="yes")                              # E: call-overload
    s.stop()
"""

PROGRAMS["typed_context_async"] = """
    import asyncio
    from typing import TypedDict
    from xstate_statemachine import Interpreter, OverflowPolicy, Receipt, SimulatedClock, create_machine

    class Ctx(TypedDict):
        n: int

    machine = create_machine(
        {"id": "m", "initial": "a", "context": {"n": 0}, "states": {"a": {"on": {"GO": "b"}}, "b": {}}},
        context_type=Ctx,
    )

    async def main() -> None:
        a = Interpreter(machine, clock=SimulatedClock(), max_queue_size=10, overflow_policy=OverflowPolicy.BLOCK)
        await a.start()
        await a.send("GO")
        await a.send("GO", n=1)
        r: Receipt = await a.send("GO", wait=True)
        err = r.error
        pr: Receipt = await a.send_priority("GO")
        x: int = a.context["n"]
        y: str = a.context["n"]                           # E: assignment
        a.send("GO", priority="high")                     # E: call-overload
        await a.stop(drain=True, timeout="5")             # E: arg-type
        Interpreter(machine, overflow_policy="raise")     # E: arg-type
        await a.stop()

    asyncio.run(main())
"""

PROGRAMS["untyped_context_is_still_fine"] = """
    from xstate_statemachine import SyncInterpreter, Interpreter, create_machine
    # No context_type: context is Dict[str, Any] -- everything is permitted
    # (this is the 0.7.x experience and must keep type-checking clean).
    m = create_machine({"id": "m", "initial": "a", "context": {"n": 0}, "states": {"a": {}}})
    s = SyncInterpreter(m).start()
    v = s.context["anything"]
    s.context["n"] = "a string is fine when untyped"
    r = s.send("GO", wait=True)
    i = Interpreter(m)
    s.stop()
"""

PROGRAMS["logic_callable_signatures"] = """
    from typing import Any, Dict
    from xstate_statemachine import MachineLogic, Event, ActionDefinition, BaseInterpreter

    def good_action(interp: BaseInterpreter[Dict[str, Any]], ctx: Dict[str, Any], event: Event, a: ActionDefinition) -> None: ...
    def good_guard(ctx: Dict[str, Any], event: Event) -> bool: return True
    def good_service(interp: BaseInterpreter[Dict[str, Any]], ctx: Dict[str, Any], event: Event) -> dict: return {}
    async def good_async_action(interp: BaseInterpreter[Dict[str, Any]], ctx: Dict[str, Any], event: Event, a: ActionDefinition) -> None: ...
    async def good_async_service(interp: BaseInterpreter[Dict[str, Any]], ctx: Dict[str, Any], event: Event) -> int: return 1

    MachineLogic(actions={"a": good_action, "b": good_async_action}, guards={"g": good_guard}, services={"s": good_service, "t": good_async_service})
    MachineLogic(actions={"a": lambda i, c, e, a: None}, guards={"g": lambda c, e: True})

    def two_arg_action(ctx: Dict[str, Any], event: Event) -> None: ...
    def four_arg_guard(i: object, ctx: Dict[str, Any], event: Event, a: object) -> bool: return True
    def str_guard(ctx: Dict[str, Any], event: Event) -> str: return "yes"

    MachineLogic(actions={"a": two_arg_action})                # E: dict-item
    MachineLogic(guards={"g": four_arg_guard})                 # E: dict-item
    MachineLogic(guards={"g": str_guard})                      # E: dict-item
"""

PROGRAMS["plugins_and_pure_api"] = """
    from typing import Any, Dict
    from xstate_statemachine import (
        PluginBase, BaseInterpreter, ActionDefinition, create_machine,
        get_initial_snapshot, get_next_snapshot, PureSnapshot,
    )

    class Good(PluginBase[BaseInterpreter[Dict[str, Any]]]):
        def on_action_error(self, interpreter: BaseInterpreter[Dict[str, Any]], action: ActionDefinition, error: BaseException) -> None: ...

    class Bad(PluginBase[BaseInterpreter[Dict[str, Any]]]):
        def on_action_error(self, interpreter: BaseInterpreter[Dict[str, Any]], action: ActionDefinition, error: str) -> None: ...   # E: override

    m = create_machine({"id": "m", "initial": "a", "states": {"a": {"on": {"GO": "b"}}, "b": {}}})
    s0: PureSnapshot = get_initial_snapshot(m)
    s1 = get_next_snapshot(m, s0, "GO")
    ok: bool = s1.matches("m.b")
    s1.contxt                                                  # E: attr-defined
"""

PROGRAMS["pythonic_api"] = """
    from typing import Any, Dict
    from xstate_statemachine import State, StateMachine, SyncInterpreter, action, guard, build_machine, assign

    class Light(StateMachine):
        machine_id = "light"
        off = State("off", initial=True, on={"TOGGLE": "on"})
        on = State("on", on={"TOGGLE": "off"})

        @action
        def log(self, interpreter: Any, context: Dict[str, Any], event: Any, action_def: Any) -> None: ...

        @guard
        def always(self, context: Dict[str, Any], event: Any) -> bool:
            return True

    lm = Light.create_machine()
    li = SyncInterpreter(lm).start()
    li.send("TOGGLE")
    fm = build_machine(id="f", states=[State("a", initial=True)], actions=[])
"""

E_TAG = re.compile(r"#\s*E:\s*([a-z-]+(?:\s*,\s*[a-z-]+)*)\s*$")


def _expected(src: str) -> Dict[int, Set[str]]:
    out: Dict[int, Set[str]] = {}
    for i, line in enumerate(src.splitlines(), 1):
        m = E_TAG.search(line)
        if m:
            out[i] = {c.strip() for c in m.group(1).split(",")}
    return out


def _mypy(path: pathlib.Path) -> Dict[int, Set[str]]:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            str(path),
            "--ignore-missing-imports",
            "--show-error-codes",
            "--no-error-summary",
            "--no-color-output",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={
            **os.environ,
            "PYTHONPATH": str(ROOT),
            "MYPY_CACHE_DIR": str(path.parent / ".mypy_cache"),
        },
        timeout=300,
    )
    found: Dict[int, Set[str]] = {}
    for line in proc.stdout.splitlines():
        m = re.match(r".*?:(\d+):(?:\d+:)? error: .*\[([a-z-]+)\]\s*$", line)
        if m:
            found.setdefault(int(m.group(1)), set()).add(m.group(2))
    return found


def _pyright_cmd() -> Optional[List[str]]:
    """Locate pyright: the npm shim on Windows is `pyright.cmd`."""
    for name in ("pyright", "pyright.cmd"):
        found = shutil.which(name)
        if found:
            return [found]
    return None


def _pyright_available() -> bool:
    return _pyright_cmd() is not None


def _pyright(path: pathlib.Path) -> Set[int]:
    cfg = path.parent / "pyrightconfig.json"
    cfg.write_text(
        '{"extraPaths": ["%s"], "typeCheckingMode": "standard", '
        '"reportMissingImports": false, "reportMissingModuleSource": false}'
        % str(ROOT).replace("\\", "/"),
        encoding="utf-8",
    )
    cmd = _pyright_cmd()
    assert cmd is not None
    proc = subprocess.run(
        [*cmd, "--outputjson", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=path.parent,
        timeout=300,
    )
    import json

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return set()
    return {
        d["range"]["start"]["line"] + 1
        for d in data.get("generalDiagnostics", [])
        if d.get("severity") == "error"
    }


class TestUserProgramsTypeCheck(unittest.TestCase):
    """For every program: mypy flags exactly the tagged lines, nothing else."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = pathlib.Path(tempfile.mkdtemp(prefix="xsm_types_"))
        cls.files: Dict[str, pathlib.Path] = {}
        for name, src in PROGRAMS.items():
            program = (
                textwrap.dedent(src)
                .lstrip("\n")
                .replace(
                    "from xstate_statemachine", "from src.xstate_statemachine"
                )
            )
            p = cls.tmp / f"{name}.py"
            p.write_text(program, encoding="utf-8")
            cls.files[name] = p

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _check(self, name: str) -> None:
        path = self.files[name]
        expected = _expected(path.read_text(encoding="utf-8"))
        found = _mypy(path)
        missed = {
            ln: codes for ln, codes in expected.items() if ln not in found
        }
        false_pos = {
            ln: codes for ln, codes in found.items() if ln not in expected
        }
        wrong_code = {
            ln: (expected[ln], found[ln])
            for ln in expected
            if ln in found and not (expected[ln] & found[ln])
        }
        src = path.read_text(encoding="utf-8").splitlines()

        def show(d: Dict[int, object]) -> str:
            return "\n".join(
                f"    L{ln}: {src[ln - 1].strip()[:90]}  -> {v}"
                for ln, v in sorted(d.items())
            )

        self.assertFalse(
            missed,
            f"[{name}] real bugs mypy did NOT flag (types too loose):\n{show(missed)}",
        )
        self.assertFalse(
            false_pos,
            f"[{name}] mypy flagged CORRECT code (false positives):\n{show(false_pos)}",
        )
        self.assertFalse(
            wrong_code,
            f"[{name}] flagged with an unexpected error code:\n{show(wrong_code)}",
        )

    def test_typed_context_sync(self) -> None:
        self._check("typed_context_sync")

    def test_typed_context_async(self) -> None:
        self._check("typed_context_async")

    def test_untyped_context_is_still_fine(self) -> None:
        self._check("untyped_context_is_still_fine")

    def test_logic_callable_signatures(self) -> None:
        self._check("logic_callable_signatures")

    def test_plugins_and_pure_api(self) -> None:
        self._check("plugins_and_pure_api")

    def test_pythonic_api(self) -> None:
        self._check("pythonic_api")

    @unittest.skipUnless(_pyright_available(), "pyright not installed")
    def test_pyright_agrees_on_every_program(self) -> None:
        """pyright must flag every tagged line and no untagged line."""
        problems: List[str] = []
        for name, path in self.files.items():
            expected = set(_expected(path.read_text(encoding="utf-8")))
            found = _pyright(path)
            for ln in sorted(expected - found):
                problems.append(f"{name}: L{ln} missed")
            for ln in sorted(found - expected):
                problems.append(f"{name}: L{ln} false positive")
        self.assertEqual(problems, [])


class TestLibraryInternalsTypeCheck(unittest.TestCase):
    """The library's own modules must be clean under mypy's default mode,
    so the annotations users rely on are ones mypy itself believes."""

    def test_src_has_no_mypy_errors(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                "src/xstate_statemachine",
                "--ignore-missing-imports",
                "--no-color-output",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=ROOT,
            timeout=600,
        )
        errors = [ln for ln in proc.stdout.splitlines() if " error: " in ln]
        self.assertEqual(
            errors, [], "mypy errors in src/:\n  " + "\n  ".join(errors[:40])
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
