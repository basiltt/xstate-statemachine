# src/xstate_statemachine/cli/validation.py
# -----------------------------------------------------------------------------
# 🏛️ Generation-time validation — refuse to emit rather than lie
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the generator must never exit 0 having produced a
# machine that differs from its source.
#
# Root cause RC-5 of the v0.7.0 audit was the absence of exactly this: nothing
# compiled the output, nothing compared the result to the source, and nothing
# exited non-zero. That is *why* every Tier-0 defect was silent. A template
# emitted an inert machine and the CLI reported success.
#
# Two complementary gates live here:
#
#   1. ``check_representable``  — before emitting, refuse constructs a
#      template provably cannot express.
#   2. ``verify_generated``     — after emitting, compile the code and compare
#      the machine it builds against ``create_machine(source_json)``.
#
# Gate 2 is the strong one: it cannot be fooled by an emitter bug, because it
# tests the artifact rather than the intent.
# -----------------------------------------------------------------------------
"""Fail-loudly validation for generated code."""

from __future__ import annotations

import ast
import logging
import sys
from typing import Any, Dict, List, Optional

from .ir import MachineIR

logger = logging.getLogger(__name__)


class GenerationRefused(Exception):
    """Raised when the generator will not emit a faithful machine.

    Carrying a distinct type lets the CLI exit non-zero with a precise
    message instead of writing a file that silently misrepresents the
    source machine.
    """


def check_representable(
    machine: MachineIR,
    template: str,
) -> List[str]:
    """Report constructs *template* cannot faithfully represent.

    Args:
        machine: The parsed source machine.
        template: The template identifier, e.g. ``pythonic-builder``.

    Returns:
        A list of human-readable problems. Empty means safe to emit.
    """
    problems: List[str] = []

    # 🔍 Keys the IR itself did not understand. Anything here would be
    #    dropped silently — precisely the failure mode this release exists
    #    to eliminate.
    unsupported = sorted(set(machine.all_unsupported()))
    if unsupported:
        problems.append(
            "config keys not understood by the generator: "
            + ", ".join(repr(k) for k in unsupported)
        )

    # 🔍 A machine with no states produces a module that cannot build.
    if not machine.states:
        problems.append("machine declares no states; nothing can be generated")

    # 🔍 Placeholder context is a source-data problem the user should know
    #    about: the generated machine will start with an empty context.
    if machine.context_is_placeholder:
        logger.warning(
            "⚠️ Machine '%s' declares a string 'context' (an unresolved "
            "template placeholder). The generated machine will start with "
            "an empty context.",
            machine.id,
        )

    return problems


# 📝 Templates whose generated logic module BUILDS the machine in Python.
#
# 🏛️ The `*-json` templates deliberately do not: their runner calls
#    create_machine(source_json) at runtime, so fidelity is exact by
#    construction and there is nothing to compare. Structural verification
#    applies only to templates that re-express the machine as Python — which
#    is precisely the set that got it wrong.
_STRUCTURAL_TEMPLATES = frozenset(
    {
        "pythonic-functional",
        "pythonic-builder",
        "pythonic-class",
    }
)


def builds_machine_inline(template: str) -> bool:
    """Whether *template*'s logic module constructs the machine in Python."""
    return template in _STRUCTURAL_TEMPLATES


def verify_generated(
    config: Dict[str, Any],
    code: str,
    *,
    template: str,
    strict: bool = True,
) -> List[str]:
    """Compile *code*, build its machine, and compare it to *config*.

    🛡️ This is the gate that would have caught every Tier-0 defect. It does
    not inspect the generated *text*; it executes it and compares the
    resulting machine, so an emitter bug cannot hide behind plausible-looking
    output.

    Args:
        config: The source machine config.
        code: Generated Python source.
        template: Template identifier, for error messages.
        strict: When True, structural differences are reported. When False,
            only hard failures (syntax errors, exceptions) are.

    Returns:
        A list of problems. Empty means the generated code is faithful.
    """
    problems: List[str] = []

    # 1️⃣ Syntax. Catches the `None = none` class of defect outright.
    try:
        ast.parse(code)
    except SyntaxError as exc:
        return [
            f"generated code is not valid Python "
            f"(line {exc.lineno}): {exc.msg}"
        ]

    # 📝 Syntax-only mode: the caller knows this template's logic module
    #    does not build a machine (the *-json templates load JSON at
    #    runtime), so there is nothing further to compare.
    if not strict:
        return problems

    machine = _build_generated(code, template, problems)
    if machine is None:
        return problems

    expected = _build_expected(config, problems)
    if expected is None:
        return problems

    if strict:
        problems.extend(_structural_problems(expected, machine))

    return problems


def _machine_types() -> tuple:
    """Every type that counts as a built machine.

    🛡️ Dual-import guard. Generated code imports ``xstate_statemachine``
    while this module is reached as ``src.xstate_statemachine...`` in a
    source checkout. Both resolve to the same files, but Python treats them
    as distinct module objects, so a perfectly correct generated machine
    would fail ``isinstance`` and be reported as "produced no machine" --
    turning the safety gate into a false alarm that blocks every run.
    """
    from ..models import MachineNode

    types_seen = [MachineNode]
    try:  # pragma: no cover — depends on import path
        from xstate_statemachine.models import (  # type: ignore[import-not-found]
            MachineNode as _Installed,
        )

        if _Installed is not MachineNode:
            types_seen.append(_Installed)
    except ImportError:
        pass
    return tuple(types_seen)


def _build_generated(
    code: str,
    template: str,
    problems: List[str],
) -> Optional[Any]:
    """Execute *code* in a scratch module and return the machine it builds.

    🛡️ SECURITY: this runs generated code in-process, with the CLI's own
    privileges. That is unavoidable — proving the code builds the right
    machine means building it — but the blast radius is worth bounding.

    The module is NOT registered in ``sys.modules``, and ``sys.modules`` is
    snapshotted and restored afterwards, so a module the generated code
    imports (or injects) cannot persist into the CLI process or shadow a
    later import. This is defence in depth, not a sandbox: code that
    reaches here can still touch the filesystem. The real barrier is that
    untrusted JSON cannot become code in the first place — see
    ``naming.docstring_safe`` and the injection tests.
    """
    import types

    machine_types = _machine_types()

    module = types.ModuleType(f"_xsm_verify_{template.replace('-', '_')}")
    saved_modules = dict(sys.modules)
    try:
        exec(compile(code, f"<{template}>", "exec"), module.__dict__)
    except Exception as exc:  # noqa: BLE001 — reported, not swallowed
        problems.append(
            f"generated code raised {type(exc).__name__} on import: {exc}"
        )
        return None
    finally:
        # 🧹 Drop anything the executed code added or replaced.
        for name in set(sys.modules) - set(saved_modules):
            sys.modules.pop(name, None)
        sys.modules.update(saved_modules)

    candidates = [
        v for v in vars(module).values() if isinstance(v, machine_types)
    ]
    if candidates:
        return candidates[0]

    factory = getattr(module, "build", None)
    if callable(factory):
        try:
            built = factory()
        except Exception as exc:  # noqa: BLE001 — reported, not swallowed
            problems.append(
                f"generated build() raised {type(exc).__name__}: {exc}"
            )
            return None
        if isinstance(built, machine_types):
            return built

    for name, value in vars(module).items():
        if name.startswith("_") or not isinstance(value, type):
            continue
        if getattr(value, "__module__", None) != module.__name__:
            continue
        creator = getattr(value, "create_machine", None)
        if callable(creator):
            try:
                built = creator()
            except Exception as exc:  # noqa: BLE001 — reported
                problems.append(
                    f"generated {name}.create_machine() raised "
                    f"{type(exc).__name__}: {exc}"
                )
                return None
            if isinstance(built, machine_types):
                return built

    problems.append("generated code produced no machine")
    return None


def _build_expected(
    config: Dict[str, Any],
    problems: List[str],
) -> Optional[Any]:
    """Build the reference machine directly from the source config."""
    from ..factory import create_machine
    from ..machine_logic import MachineLogic

    try:
        return create_machine(config, logic=MachineLogic())
    except Exception as exc:  # noqa: BLE001 — invalid source, not our bug
        problems.append(
            f"source config is not a valid machine "
            f"({type(exc).__name__}: {exc})"
        )
        return None


def _structural_problems(expected: Any, actual: Any) -> List[str]:
    """Compare two machines and describe any divergence."""
    exp_map: Dict[str, Any] = {}
    act_map: Dict[str, Any] = {}
    _collect(expected, expected.id, exp_map)
    _collect(actual, actual.id, act_map)

    problems: List[str] = []
    for path in sorted(set(exp_map) - set(act_map)):
        problems.append(f"state {path!r} is missing from the generated code")
    for path in sorted(set(act_map) - set(exp_map)):
        problems.append(f"state {path!r} was invented by the generator")

    for path in sorted(set(exp_map) & set(act_map)):
        exp, act = exp_map[path], act_map[path]
        for field, exp_value in exp.items():
            act_value = act.get(field)
            if exp_value != act_value:
                problems.append(
                    f"state {path!r}: {field} differs "
                    f"(source={exp_value!r}, generated={act_value!r})"
                )
    return problems


def _collect(node: Any, root_id: str, acc: Dict[str, Any]) -> None:
    """Fingerprint *node* and every descendant into *acc*."""
    if node.id == root_id:
        path = "<root>"
    elif node.id.startswith(f"{root_id}."):
        path = node.id[len(root_id) + 1 :]
    else:
        path = node.id

    on_done = node.on_done or []
    if not isinstance(on_done, (list, tuple)):
        on_done = [on_done]

    # 🛡️ Transitions are compared in FULL: resolved destination, actions,
    #    guard and reenter -- not merely the set of event names.
    #
    #    Recording only names made this gate structurally blind to the
    #    worst defect class it exists to catch. Generated code sending GO
    #    to 'c' where the source says 'b' is a different machine, yet the
    #    fingerprints matched and the CLI printed "Verified ... exactly".
    acc[path] = {
        "type": node.type,
        "initial": node.initial,
        "history": node.history,
        "entry": [a.type for a in node.entry],
        "exit": [a.type for a in node.exit],
        "on": {
            event: [_transition_fingerprint(t) for t in transitions]
            for event, transitions in sorted(node.on.items())
        },
        "after": {
            str(delay): [_transition_fingerprint(t) for t in transitions]
            for delay, transitions in sorted(
                node.after.items(), key=lambda kv: str(kv[0])
            )
        },
        "invoke": sorted(i.src for i in node.invoke),
        "on_done": [_transition_fingerprint(t) for t in on_done],
        "tags": sorted(node.tags or []),
    }
    for child in node.states.values():
        _collect(child, root_id, acc)


def _transition_fingerprint(trans: Any) -> tuple:
    """Reduce a transition to everything that changes behaviour.

    The target is compared by RESOLVED destination rather than by the raw
    string, so ``"#m.b"`` and ``"b"`` are correctly treated as identical
    when they name the same state — fidelity is about the machine you get,
    not the spelling used to describe it.
    """
    return (
        trans.event,
        _resolved_target(trans),
        tuple(a.type for a in trans.actions),
        trans.guard,
        bool(trans.reenter),
    )


def _resolved_target(trans: Any) -> Optional[str]:
    """Resolve a transition's target to a canonical state id."""
    if trans.target_str is None:
        return None
    from ..resolver import resolve_target_state

    try:
        return resolve_target_state(trans.target_str, trans.source).id
    except Exception:  # noqa: BLE001 — unresolvable targets compare raw
        return f"<unresolved:{trans.target_str}>"


def format_refusal(
    template: str,
    machine_id: str,
    problems: List[str],
) -> str:
    """Build the message shown when generation is refused."""
    bullets = "\n".join(f"  • {p}" for p in problems)
    return (
        f"Refusing to generate '{template}' code for machine "
        f"'{machine_id}'.\n\n"
        f"The generated code would not faithfully reproduce the source "
        f"machine:\n{bullets}\n\n"
        f"Nothing was written. This is deliberate: emitting a machine that "
        f"silently differs from its source is worse than emitting nothing."
    )
