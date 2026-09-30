# src/xstate_statemachine/contrib/django/_machine.py
# -----------------------------------------------------------------------------
# 🧭 Machine / logic resolution for model classes
# -----------------------------------------------------------------------------
# 🏛️ A model names its chart the way settings name things in Django: a
#    JSON path, a config dict, a `MachineNode`, or a dotted callable
#    (``"shop.machines:build"``) returning one. Logic is optional: a
#    `MachineLogic`, a dotted callable returning one, or a dotted MODULE
#    whose functions `LogicLoader` binds by name. Static specs are built
#    once per class and cached; a callable taking the row is resolved per
#    call.
# -----------------------------------------------------------------------------
"""Resolve ``machine=`` / ``logic=`` specs (internal)."""

from __future__ import annotations

import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from ...factory import create_machine
from ...machine_logic import MachineLogic
from ...models import MachineNode

__all__ = ["import_string", "machine_source", "resolve_machine"]


def import_string(spec: str) -> Any:
    """``"pkg.mod:attr"`` / ``"pkg.mod.attr"`` → the attribute, or the
    module itself for ``"pkg.mod"``."""
    if ":" in spec:
        mod, attr = spec.split(":", 1)
        return getattr(importlib.import_module(mod), attr)
    try:
        return importlib.import_module(spec)
    except ImportError:
        mod, _, attr = spec.rpartition(".")
        if not mod:
            raise
        return getattr(importlib.import_module(mod), attr)


def _find_json(path: str, owner: Any) -> Path:
    p = Path(path)
    if p.is_absolute():
        return p
    candidates = []
    module = sys.modules.get(getattr(owner, "__module__", ""), None)
    mod_file = getattr(module, "__file__", None)
    if mod_file:
        here = Path(mod_file).resolve().parent
        candidates += [here / p, here.parent / p]
    try:
        from django.conf import settings

        base = getattr(settings, "BASE_DIR", None)
        if base:
            candidates.append(Path(base) / p)
    except Exception:  # noqa: BLE001 - settings not configured
        pass
    candidates.append(Path.cwd() / p)
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError(
        f"machine JSON {path!r} not found (looked in "
        f"{', '.join(str(c) for c in candidates)})"
    )


def _logic_kwargs(logic: Any, row: Any) -> Dict[str, Any]:
    if logic is None:
        return {}
    if isinstance(logic, str):
        logic = import_string(logic)
    if inspect.ismodule(logic):
        return {"logic_modules": [logic]}
    if isinstance(logic, MachineLogic):
        return {"logic": logic}
    if callable(logic):
        built = _call_maybe_row(logic, row)
        if isinstance(built, MachineLogic):
            return {"logic": built}
        raise TypeError(
            f"logic callable returned {type(built).__name__}, "
            f"expected MachineLogic"
        )
    return {"logic_providers": [logic]}


def _call_maybe_row(fn: Any, row: Any) -> Any:
    try:
        sig = inspect.signature(fn)
        takes = any(
            p.kind
            in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD, p.VAR_POSITIONAL)
            for p in sig.parameters.values()
        )
    except (TypeError, ValueError):  # pragma: no cover - builtins
        takes = False
    return fn(row) if takes else fn()


def resolve_machine(
    spec: Any, *, logic: Any = None, owner: Any = None, row: Any = None
) -> MachineNode[Any]:
    """Build the `MachineNode` a model declares.

    Args:
        spec: JSON path (relative to the model's module, its parent, or
            ``settings.BASE_DIR``), config dict, `MachineNode`, or a
            dotted callable / callable returning a `MachineNode`
            (``(row)`` or ``()``).
        logic: `MachineLogic`, dotted callable / module, or ``None``.
        owner: The model class (for relative paths).
        row: The instance, for callables that depend on it.
    """
    if spec is None:
        raise TypeError(
            f"{getattr(owner, '__name__', 'model')} declares no machine: set "
            f"`machine = 'path/to/chart.json'` (or statechart_machine=)."
        )
    if isinstance(spec, MachineNode):
        if logic is None:
            return spec
        import copy

        kw = _logic_kwargs(logic, row)
        m = copy.copy(spec)
        if "logic" in kw:
            m.logic = kw["logic"]
        return m
    if isinstance(spec, dict):
        return create_machine(spec, **_logic_kwargs(logic, row))
    if isinstance(spec, (str, Path)):
        s = str(spec)
        if s.endswith(".json"):
            cfg = json.loads(_find_json(s, owner).read_text(encoding="utf-8"))
            return create_machine(cfg, **_logic_kwargs(logic, row))
        return resolve_machine(
            import_string(s), logic=logic, owner=owner, row=row
        )
    if callable(spec):
        return resolve_machine(
            _call_maybe_row(spec, row), logic=logic, owner=owner, row=row
        )
    raise TypeError(
        "machine must be a JSON path, config dict, MachineNode or callable; "
        f"got {type(spec).__name__}"
    )


def machine_source(spec: Any, owner: Any = None) -> Optional[Path]:
    """The JSON file behind a path spec, else ``None``."""
    if isinstance(spec, (str, Path)) and str(spec).endswith(".json"):
        return _find_json(str(spec), owner)
    return None
