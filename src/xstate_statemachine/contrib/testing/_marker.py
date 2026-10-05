# src/xstate_statemachine/contrib/testing/_marker.py
# -----------------------------------------------------------------------------
# 🏷️ The `xstate_machine` marker: parsing, logic loading, machine building
# -----------------------------------------------------------------------------
# 🏛️ Split out of `pytest_plugin.py` (#268 battle). Imports only pytest and
#    core; every name is re-exported from `pytest_plugin`, which stays the
#    public import path.
# -----------------------------------------------------------------------------
"""Internal: ``xstate_machine`` marker parsing and machine construction."""

from __future__ import annotations

import importlib
import json
import pathlib
import traceback
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

import pytest

from ...factory import create_machine
from ...machine_logic import MachineLogic
from ...models import MachineNode
from ...testing_utils import logic_names, stub_logic

MARKER = "xstate_machine"
GUARDS_MARKER = "xstate_guards_false"

#: What ``logic=`` accepts: a dotted ``"pkg.mod:factory"`` string, a
#: zero-argument callable returning a `MachineLogic`, or the instance.
LogicArg = Any


class MachineSpec:
    """What the ``xstate_machine`` marker asked for, validated.

    Attributes:
        source: A JSON path, a config dict, or a built `MachineNode`.
        logic: A dotted ``"pkg.module:callable"``, a zero-argument callable
            returning a `MachineLogic`, a `MachineLogic` instance, or
            ``None`` for stub logic.
        strict_config: Passed through to `create_machine`.
        strict: Overrides the config's ``"strict"`` key when not ``None``.
        guards_false: Guard names the ``xstate_guards_false`` marker forces
            to ``False`` (only meaningful with stub logic).
    """

    __slots__ = ("source", "logic", "strict_config", "strict", "guards_false")

    def __init__(
        self,
        source: Union[str, pathlib.Path, Mapping[str, Any], MachineNode[Any]],
        *,
        logic: Optional[LogicArg] = None,
        strict_config: Optional[bool] = None,
        strict: Optional[bool] = None,
        guards_false: Tuple[str, ...] = (),
    ) -> None:
        self.source = source
        self.logic = logic
        self.strict_config = strict_config
        self.strict = strict
        self.guards_false = guards_false


def _usage_error(item: Any, message: str) -> "pytest.UsageError":
    return pytest.UsageError(f"{item.nodeid}: {message}")


def _check_logic_arg(item: Any, logic: Any) -> None:
    if logic is None or isinstance(logic, MachineLogic):
        return
    if isinstance(logic, str):
        if ":" in logic and not logic.startswith(":"):
            return
    elif callable(logic):
        return
    raise _usage_error(
        item,
        f"@pytest.mark.{MARKER}: logic= must be a dotted "
        f"'package.module:callable' string, a callable returning a "
        f"MachineLogic, or a MachineLogic, got {logic!r}",
    )


def _parse_guards(item: Any, logic: Any) -> Tuple[str, ...]:
    guards_marker = item.get_closest_marker(GUARDS_MARKER)
    if guards_marker is None:
        return ()
    if guards_marker.kwargs:
        raise _usage_error(
            item,
            f"@pytest.mark.{GUARDS_MARKER} takes guard names as "
            f"positional arguments only",
        )
    if not guards_marker.args or not all(
        isinstance(g, str) and g for g in guards_marker.args
    ):
        raise _usage_error(
            item,
            f"@pytest.mark.{GUARDS_MARKER} needs one or more guard "
            f"names, e.g. @pytest.mark.{GUARDS_MARKER}('isPaid')",
        )
    if logic is not None:
        # 🛑 Real logic owns its guards; the stub table would be ignored.
        raise _usage_error(
            item,
            f"@pytest.mark.{GUARDS_MARKER} only applies to stub logic; "
            f"this test passes logic={logic!r}. Make the real guard "
            f"return False instead, or drop logic= to use stubs.",
        )
    return tuple(guards_marker.args)


def _check_shape(item: Any, marker: Any) -> None:
    if len(marker.args) != 1:
        raise _usage_error(
            item,
            f"@pytest.mark.{MARKER} takes exactly one positional argument "
            f"(a JSON path, a config dict or a MachineNode), got "
            f"{len(marker.args)}",
        )
    allowed = {"logic", "strict_config", "strict"}
    unknown = sorted(set(marker.kwargs) - allowed)
    if unknown:
        raise _usage_error(
            item,
            f"@pytest.mark.{MARKER}: unknown keyword(s) {unknown}; "
            f"allowed: {sorted(allowed)}",
        )
    source = marker.args[0]
    if not isinstance(source, (str, pathlib.Path, Mapping, MachineNode)):
        raise _usage_error(
            item,
            f"@pytest.mark.{MARKER}: source must be a JSON path, a dict or "
            f"a MachineNode, got {type(source).__name__}",
        )
    for flag in ("strict_config", "strict"):
        # 🛑 `strict="false"` is truthy; only a real bool (or None) is
        #    unambiguous.
        value = marker.kwargs.get(flag)
        if value is not None and not isinstance(value, bool):
            raise _usage_error(
                item,
                f"@pytest.mark.{MARKER}: {flag}= must be True, False or "
                f"None, got {value!r}",
            )


def parse_marker(item: Any) -> Optional[MachineSpec]:
    """Read the ``xstate_machine`` / ``xstate_guards_false`` markers.

    The marker closest to the test wins (a function marker overrides a
    class or module ``pytestmark``; of two stacked decorators the one
    nearest the ``def`` wins). Returns ``None`` when the test carries no
    ``xstate_machine`` marker -- every ``xsm_*`` fixture stays inert.

    Raises:
        pytest.UsageError: malformed marker arguments, or
            ``xstate_guards_false`` combined with ``logic=``.
    """
    marker = item.get_closest_marker(MARKER)
    if marker is None:
        if item.get_closest_marker(GUARDS_MARKER) is not None:
            raise _usage_error(
                item,
                f"@pytest.mark.{GUARDS_MARKER} needs an "
                f"@pytest.mark.{MARKER}(...) marker on the same test",
            )
        return None
    _check_shape(item, marker)
    logic = marker.kwargs.get("logic")
    _check_logic_arg(item, logic)
    return MachineSpec(
        marker.args[0],
        logic=logic,
        strict_config=marker.kwargs.get("strict_config"),
        strict=marker.kwargs.get("strict"),
        guards_false=_parse_guards(item, logic),
    )


# -----------------------------------------------------------------------------
# 🏗️ Building the machine
# -----------------------------------------------------------------------------
def _resolve_path(item: Any, source: Union[str, pathlib.Path]) -> pathlib.Path:
    """A relative JSON path is tried next to the test file, then rootdir."""
    path = pathlib.Path(source)
    if path.is_absolute():
        if path.is_file():
            return path
        raise _usage_error(item, f"machine file not found: {path}")
    candidates = [pathlib.Path(str(item.path)).parent / path]
    rootdir = getattr(item.config, "rootpath", None)
    if rootdir is not None:
        candidates.append(pathlib.Path(str(rootdir)) / path)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    tried = ", ".join(str(c) for c in candidates)
    raise _usage_error(
        item,
        f"machine file {str(source)!r} not found (tried {tried})",
    )


def _load_config(item: Any, path: pathlib.Path) -> Dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _usage_error(item, f"cannot read machine JSON {path}: {exc}")
    if not isinstance(loaded, dict):
        raise _usage_error(
            item, f"{path}: top level must be a JSON object (the machine)"
        )
    return loaded


def _where(exc: BaseException) -> str:
    """``file:line`` of the innermost frame of ``exc``'s traceback."""
    frames = traceback.extract_tb(exc.__traceback__)
    if not frames:
        return ""
    last = frames[-1]
    return f" (at {last.filename}:{last.lineno})"


def _import_factory(item: Any, dotted: str) -> Any:
    module_name, _, attr = dotted.partition(":")
    try:
        module = importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001 -- surface as a usage error
        # 🛑 #268 battle: only `ImportError` was caught, so a module that
        #    raised anything else while importing escaped as a traceback.
        raise _usage_error(
            item,
            f"logic={dotted!r}: cannot import {module_name!r}: "
            f"{type(exc).__name__}: {exc}{_where(exc)}",
        ) from exc
    factory: Any = module
    for part in attr.split("."):
        factory = getattr(factory, part, None)
        if factory is None:
            raise _usage_error(
                item, f"logic={dotted!r}: {module_name!r} has no {attr!r}"
            )
    if not callable(factory):
        raise _usage_error(item, f"logic={dotted!r}: {attr!r} is not callable")
    return factory


def _load_logic(item: Any, logic: Any) -> MachineLogic[Any]:
    """Turn a ``logic=`` argument into a `MachineLogic`.

    📝 A dict of actions is refused, not guessed at: `MachineLogic` is the
    one shape that says which names are actions, guards and services.
    """
    if isinstance(logic, MachineLogic):
        return logic
    shown = (
        logic
        if isinstance(logic, str)
        else getattr(logic, "__qualname__", repr(logic))
    )
    factory = _import_factory(item, logic) if isinstance(logic, str) else logic
    built = _call_logic_factory(item, shown, factory)
    if not isinstance(built, MachineLogic):
        raise _usage_error(
            item,
            f"logic={shown!r}: callable must return a MachineLogic, got "
            f"{type(built).__name__}",
        )
    return built


def _call_logic_factory(item: Any, dotted: str, factory: Any) -> Any:
    """Call the ``logic=`` factory; a raising factory is a usage error."""
    try:
        return factory()
    except Exception as exc:  # noqa: BLE001 -- surface as a usage error
        raise _usage_error(
            item,
            f"logic={dotted!r}: the factory raised "
            f"{type(exc).__name__}: {exc}",
        ) from exc


class _Built:
    """A built machine plus the stub bookkeeping the fixtures hand out."""

    __slots__ = ("machine", "ran", "guards", "stubbed")

    def __init__(
        self,
        machine: MachineNode[Any],
        ran: List[str],
        guards: Dict[str, bool],
        stubbed: bool,
    ) -> None:
        self.machine = machine
        self.ran = ran
        self.guards = guards
        self.stubbed = stubbed


def _built_node(
    item: Any, spec: MachineSpec, node: MachineNode[Any]
) -> _Built:
    if (
        spec.logic is not None
        or spec.strict_config is not None
        or spec.strict is not None
    ):
        # 🛑 Never mutate the caller's node: a module-level MachineNode
        #    would leak `strict` into every later test.
        raise _usage_error(
            item,
            "a MachineNode source is already built; logic=, "
            "strict_config= and strict= cannot be applied to it",
        )
    if spec.guards_false:
        raise _usage_error(
            item,
            f"@pytest.mark.{GUARDS_MARKER} cannot force guards on an "
            f"already-built MachineNode; pass the config dict or JSON "
            f"path instead",
        )
    return _Built(node, [], {}, stubbed=False)


def _check_guard_names(
    item: Any, config: Dict[str, Any], names: Tuple[str, ...]
) -> None:
    # 🛑 #268 battle: a misspelt guard name was silently accepted and the
    #    test exercised the TRUE branch while claiming to force False.
    _, known, _ = logic_names(config)
    unknown = sorted(set(names) - set(known))
    if unknown:
        raise _usage_error(
            item,
            f"@pytest.mark.{GUARDS_MARKER}: the chart declares "
            f"no guard named {unknown}; known guards: {sorted(known)}",
        )


def _build(item: Any, spec: MachineSpec) -> _Built:
    """Build the marker's machine (fresh per test, never shared)."""
    if isinstance(spec.source, MachineNode):
        return _built_node(item, spec, spec.source)
    ran: List[str] = []
    guards: Dict[str, bool] = {name: False for name in spec.guards_false}
    if isinstance(spec.source, Mapping):
        config: Dict[str, Any] = dict(spec.source)
    else:
        config = _load_config(item, _resolve_path(item, spec.source))
    if spec.strict is not None:
        config["strict"] = bool(spec.strict)
    try:
        # 📝 `stub_logic` validates the chart too (battle #304), so an
        #    invalid config surfaces HERE as well as in `create_machine`.
        if spec.logic is None:
            if spec.guards_false:
                _check_guard_names(item, config, spec.guards_false)
            logic = stub_logic(config, ran=ran, guards=guards)
        else:
            logic = _load_logic(item, spec.logic)
        machine = create_machine(
            config, logic=logic, strict_config=spec.strict_config
        )
    except pytest.UsageError:
        raise
    except Exception as exc:  # noqa: BLE001 -- surface as a usage error
        raise _usage_error(
            item, f"create_machine failed: {type(exc).__name__}: {exc}"
        ) from exc
    return _Built(machine, ran, guards, spec.logic is None)
