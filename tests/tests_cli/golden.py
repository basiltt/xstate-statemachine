# tests/tests_cli/golden.py
# -----------------------------------------------------------------------------
# 🏛️ Golden round-trip harness for code generation
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the code generator's ONLY promise is that the
# machine you get from the generated Python is the same machine you get from
# ``create_machine(source_json)``. Every Tier-0 defect found in the v0.7.0
# audit — inert machines, dropped nested states, vanished timers — was invisible
# because nothing ever *executed* the generated code and compared it back.
#
# String assertions cannot catch these. A test that asserts
# ``assertIn("green.to(yellow", code)`` passes happily while the emitted
# expression is discarded at runtime and the machine can never move.
#
# So this module works structurally, not textually:
#
#     source JSON ──create_machine──> EXPECTED MachineNode
#          │                                  │
#          └──generate──> Python ──exec──> ACTUAL MachineNode
#                                             │
#                                     structural_diff()
#
# The comparison walks the state tree and reports every divergence as a plain
# string. An empty diff list is the only passing result.
# -----------------------------------------------------------------------------
"""Structural round-trip verification for generated state machine code."""

from __future__ import annotations

import ast
import textwrap
import types
from typing import Any, Dict, List, Optional, Set, Tuple

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.machine_logic import MachineLogic
from src.xstate_statemachine.models import MachineNode, StateNode
from src.xstate_statemachine.resolver import resolve_target_state

# 🛡️ Dual-import guard. The test suite imports ``src.xstate_statemachine``
#    while *generated* code imports ``xstate_statemachine``. Both resolve to
#    the same files, but Python treats them as distinct module objects — so a
#    perfectly correct generated machine would fail ``isinstance`` and be
#    reported as "no MachineNode". Accept both identities.
_MACHINE_TYPES: Tuple[type, ...] = (MachineNode,)
try:  # pragma: no cover — depends on how the package was imported first
    from xstate_statemachine.models import (  # type: ignore[import-not-found]
        MachineNode as _InstalledMachineNode,
    )

    if _InstalledMachineNode is not MachineNode:
        _MACHINE_TYPES = (MachineNode, _InstalledMachineNode)
except ImportError:
    pass


def _is_machine(value: Any) -> bool:
    """Return True if *value* is a MachineNode under either import path."""
    return isinstance(value, _MACHINE_TYPES)

# -----------------------------------------------------------------------------
# 🧬 Structural fingerprinting
# -----------------------------------------------------------------------------


def _resolved_target(trans: Any) -> Optional[str]:
    """Resolve a transition's target to a canonical state id.

    🏛️ Comparing raw target *strings* would flag ``"#n.outerB"`` and
    ``"outerB"`` as different when both name the same state. Fidelity is
    about the machine you get, not the spelling used to describe it — so
    resolve through the engine's own resolver and compare the destination.
    """
    if trans.target_str is None:
        return None
    try:
        return resolve_target_state(trans.target_str, trans.source).id
    except Exception:  # noqa: BLE001 - unresolvable targets compare raw
        return f"<unresolved:{trans.target_str}>"


def _transition_fingerprint(trans: Any) -> Tuple[Any, ...]:
    """Reduce a transition to its behaviourally significant parts.

    Action *names* matter (they are the contract with the logic module);
    the callables behind them do not, since generated code supplies stubs.
    """
    return (
        trans.event,
        _resolved_target(trans),
        tuple(a.type for a in trans.actions),
        trans.guard,
        bool(trans.reenter),
    )


def _state_fingerprint(node: StateNode) -> Dict[str, Any]:
    """Capture everything about a single state that changes behaviour."""
    on_map: Dict[str, List[Tuple[Any, ...]]] = {}
    for event, transitions in sorted(node.on.items()):
        on_map[event] = [_transition_fingerprint(t) for t in transitions]

    after_map: Dict[Any, List[Tuple[Any, ...]]] = {}
    for delay, transitions in sorted(
        node.after.items(), key=lambda kv: str(kv[0])
    ):
        after_map[delay] = [_transition_fingerprint(t) for t in transitions]

    # 📝 `on_done` is a single TransitionDefinition on some nodes and a list
    #    on others; normalise before fingerprinting.
    raw_on_done = node.on_done or []
    if not isinstance(raw_on_done, (list, tuple)):
        raw_on_done = [raw_on_done]

    return {
        "type": node.type,
        "initial": node.initial,
        "history": node.history,
        "entry": [a.type for a in node.entry],
        "exit": [a.type for a in node.exit],
        "on": on_map,
        "after": after_map,
        "invoke": sorted(i.src for i in node.invoke),
        "on_done": [_transition_fingerprint(t) for t in raw_on_done],
        "tags": sorted(node.tags or []),
        "meta": node.meta or {},
    }


def _walk(node: StateNode, acc: Dict[str, Dict[str, Any]]) -> None:
    """Depth-first collection of every state keyed by its full id."""
    acc[node.id] = _state_fingerprint(node)
    for child in node.states.values():
        _walk(child, acc)


def fingerprint_machine(machine: MachineNode) -> Dict[str, Dict[str, Any]]:
    """Produce a comparable structural map of an entire machine."""
    acc: Dict[str, Dict[str, Any]] = {}
    _walk(machine, acc)
    return acc


# -----------------------------------------------------------------------------
# 🔍 Diffing
# -----------------------------------------------------------------------------

# 📝 Field-by-field so a diff says *what* diverged, not just "states differ".
_COMPARED_FIELDS = (
    "type",
    "initial",
    "history",
    "entry",
    "exit",
    "on",
    "after",
    "invoke",
    "on_done",
    "tags",
    "meta",
)


def structural_diff(
    expected: MachineNode,
    actual: MachineNode,
    *,
    ignore_root_id: bool = True,
) -> List[str]:
    """Compare two machines and return a list of human-readable differences.

    Args:
        expected: The machine built directly from the source JSON.
        actual: The machine produced by executing generated code.
        ignore_root_id: Compare state paths relative to the machine root, so
            a differing machine ``id`` alone is not reported on every state.

    Returns:
        A list of difference descriptions. Empty means structurally identical.
    """
    exp_map = fingerprint_machine(expected)
    act_map = fingerprint_machine(actual)

    if ignore_root_id:
        exp_map = _strip_root(exp_map, expected.id)
        act_map = _strip_root(act_map, actual.id)

    diffs: List[str] = []

    missing = sorted(set(exp_map) - set(act_map))
    extra = sorted(set(act_map) - set(exp_map))

    for path in missing:
        diffs.append(f"MISSING STATE: {path!r} exists in source but not in generated")
    for path in extra:
        diffs.append(f"EXTRA STATE: {path!r} generated but absent from source")

    for path in sorted(set(exp_map) & set(act_map)):
        exp, act = exp_map[path], act_map[path]
        for field in _COMPARED_FIELDS:
            if exp[field] != act[field]:
                diffs.append(
                    f"{path}: {field} differs\n"
                    f"    expected: {exp[field]!r}\n"
                    f"    actual:   {act[field]!r}"
                )
    return diffs


def _strip_root(
    fmap: Dict[str, Dict[str, Any]], root_id: str
) -> Dict[str, Dict[str, Any]]:
    """Rewrite absolute state ids as root-relative paths."""
    out: Dict[str, Dict[str, Any]] = {}
    for key, value in fmap.items():
        if key == root_id:
            rel = "<root>"
        elif key.startswith(f"{root_id}."):
            rel = key[len(root_id) + 1 :]
        else:
            rel = key
        out[rel] = value
    return out


# -----------------------------------------------------------------------------
# ⚙️ Execution of generated code
# -----------------------------------------------------------------------------


class GeneratedCodeError(AssertionError):
    """Raised when generated code fails to compile, execute, or build."""


def assert_compiles(code: str, *, label: str = "generated") -> None:
    """Fail loudly if *code* is not syntactically valid Python.

    Catches the ``None = none`` class of defect, where a JSON name that is a
    Python keyword is emitted as an assignment target.
    """
    try:
        ast.parse(code)
    except SyntaxError as exc:
        numbered = _with_line_numbers(code, focus=exc.lineno)
        raise GeneratedCodeError(
            f"{label} code is not valid Python: {exc}\n\n{numbered}"
        ) from exc


def exec_generated(
    code: str,
    *,
    label: str = "generated",
    extra_globals: Optional[Dict[str, Any]] = None,
) -> types.ModuleType:
    """Compile and execute generated code in a fresh module namespace.

    Returns:
        The populated module object, so callers can pull out the built
        machine or inspect emitted stubs.

    Raises:
        GeneratedCodeError: On syntax errors or any exception at import time.
    """
    assert_compiles(code, label=label)
    module = types.ModuleType(f"xsm_{label}")
    module.__dict__["__name__"] = f"xsm_{label}"
    if extra_globals:
        module.__dict__.update(extra_globals)
    try:
        exec(compile(code, f"<{label}>", "exec"), module.__dict__)
    except Exception as exc:  # noqa: BLE001 — surfaced with full context
        raise GeneratedCodeError(
            f"{label} code raised {type(exc).__name__} at import: {exc}\n\n"
            f"{_with_line_numbers(code)}"
        ) from exc
    return module


def find_machine(module: types.ModuleType) -> MachineNode:
    """Obtain the MachineNode a generated module produces.

    Templates differ in shape: some bind a machine at module level, others
    expose a ``build()`` factory or a ``StateMachine`` subclass with
    ``create_machine()``. All three are accepted so the harness measures
    *fidelity*, not house style.
    """
    # 1️⃣ A machine bound directly at module level.
    direct = [v for v in vars(module).values() if _is_machine(v)]
    if len(direct) > 1:
        raise GeneratedCodeError(
            f"generated module defined {len(direct)} machines; expected 1"
        )
    if direct:
        return direct[0]

    # 2️⃣ A factory function, by convention named ``build``.
    factory = getattr(module, "build", None)
    if callable(factory):
        machine = _call_factory(factory, "build()")
        if _is_machine(machine):
            return machine

    # 3️⃣ A ``StateMachine`` subclass exposing ``create_machine()``.
    #    Only classes *defined here* count — the imported ``StateMachine``
    #    base is also in scope and would raise on an empty definition.
    for name, value in vars(module).items():
        if name.startswith("_") or not isinstance(value, type):
            continue
        if getattr(value, "__module__", None) != module.__name__:
            continue
        creator = getattr(value, "create_machine", None)
        if callable(creator):
            machine = _call_factory(creator, f"{name}.create_machine()")
            if _is_machine(machine):
                return machine

    raise GeneratedCodeError(
        "generated module produced no MachineNode via module scope, "
        f"build(), or create_machine(). Names: {sorted(vars(module))}"
    )


def _call_factory(factory: Any, label: str) -> Any:
    """Invoke a machine factory, reporting failures with context."""
    try:
        return factory()
    except Exception as exc:  # noqa: BLE001 — surfaced with full context
        raise GeneratedCodeError(
            f"{label} raised {type(exc).__name__}: {exc}"
        ) from exc


def build_expected(config: Dict[str, Any]) -> MachineNode:
    """Build the reference machine straight from source JSON.

    Uses a permissive ``MachineLogic`` so missing implementations never mask a
    *structural* difference — this harness tests shape, not behaviour.
    """
    return create_machine(config, logic=MachineLogic())


def _with_line_numbers(code: str, focus: Optional[int] = None) -> str:
    """Render code with line numbers, marking *focus* if given."""
    lines = code.splitlines()
    if focus:
        lo, hi = max(0, focus - 6), min(len(lines), focus + 5)
        lines = lines[lo:hi]
        offset = lo + 1
    else:
        offset = 1
    rendered = []
    for i, line in enumerate(lines, start=offset):
        marker = ">>" if focus and i == focus else "  "
        rendered.append(f"{marker} {i:4d} | {line}")
    return textwrap.indent("\n".join(rendered), "    ")


# -----------------------------------------------------------------------------
# 🎯 The single entry point tests should use
# -----------------------------------------------------------------------------


def assert_round_trip(
    config: Dict[str, Any],
    code: str,
    *,
    label: str = "generated",
    allow: Optional[Set[str]] = None,
) -> None:
    """Assert generated *code* rebuilds the machine described by *config*.

    This is the gate: compile → execute → locate machine → structural compare.

    Args:
        config: The source XState JSON config.
        code: Generated Python source claiming to reproduce it.
        label: Name used in error messages.
        allow: Optional set of substrings marking known-acceptable diffs.
            Use sparingly and always with a comment explaining why.

    Raises:
        GeneratedCodeError: If the code fails to run or diverges structurally.
    """
    module = exec_generated(code, label=label)
    actual = find_machine(module)
    expected = build_expected(config)

    diffs = structural_diff(expected, actual)
    if allow:
        diffs = [d for d in diffs if not any(a in d for a in allow)]

    if diffs:
        body = "\n".join(f"  • {d}" for d in diffs)
        raise GeneratedCodeError(
            f"{label}: generated machine diverges from source JSON "
            f"({len(diffs)} difference(s)):\n{body}"
        )
