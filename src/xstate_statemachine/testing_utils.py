# src/xstate_statemachine/testing_utils.py
# -----------------------------------------------------------------------------
# 🧪 stub_logic -- run any machine config with no real implementations
# -----------------------------------------------------------------------------
# 🏛️ Why this is in core (and not in the `[testing]` extra): a machine that
#    declares actions / guards / services fails loudly with
#    `ImplementationMissingError` when built without them -- by design
#    ("silent acceptance is a bug"). Every tool that wants to EXERCISE a
#    chart without owning its business logic -- the CLI's `simulate` and
#    `pytest` template, the graph traversal (#269), coverage (#270), the
#    model-based tester (#271), verification scripts, and users' own
#    exploratory tests -- needs the same stand-in: actions that record, guards
#    that answer a fixed value, services that complete immediately. One
#    zero-dependency helper, promoted from `cli/strategies/_trace.py` (#304).
# -----------------------------------------------------------------------------
"""Stub implementations so a chart can be driven without its real logic."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Set, Tuple, Union

from .machine_logic import MachineLogic
from .models import MachineNode

__all__ = ["stub_logic", "logic_names"]


def _guard_names(guard: Any, out: Set[str]) -> None:
    """Collect leaf guard names; composite `and`/`or`/`not` recurse,
    `stateIn` is engine-provided and needs no implementation."""
    if guard is None:
        return
    if getattr(guard, "is_composite", False):
        for child in getattr(guard, "children", None) or []:
            _guard_names(child, out)
        return
    if getattr(guard, "is_state_in", False):
        return
    name = getattr(guard, "type", None)
    if isinstance(name, str) and name:
        out.add(name)


def logic_names(
    config_or_machine: Union[Mapping[str, Any], MachineNode],
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Return ``(actions, guards, services)`` a chart references by name.

    Accepts the raw JSON config (a mapping) or a built `MachineNode`. For
    a machine the PARSED model is walked -- entry/exit/transition actions,
    leaf guards inside composite guards, every invoke ``src`` -- so the
    result is exactly the set of names the engine will look up. Built-in
    actions (`assign`, `raise`, `sendTo`, …) are excluded; the engine
    provides those.
    """
    if not isinstance(config_or_machine, MachineNode):
        # 📝 The extractor under `cli/` is pure stdlib and works on the raw
        #    config; imported lazily to keep this module's import cost nil.
        from .cli.extractor import extract_logic_names

        a, g, s = extract_logic_names(dict(config_or_machine))
        return set(a), set(g), set(s)

    from .actions import is_builtin
    from .validation import transitions_of, walk

    actions: Set[str] = set()
    guards: Set[str] = set()
    services: Set[str] = set()
    for node in walk(config_or_machine):
        for act in list(node.entry) + list(node.exit):
            if not is_builtin(act.type):
                actions.add(act.type)
        for inv in node.invoke:
            if inv.src:
                services.add(inv.src)
        for _label, t in transitions_of(node):
            for act in t.actions:
                if not is_builtin(act.type):
                    actions.add(act.type)
            _guard_names(t.guard_def, guards)
    return actions, guards, services


def stub_logic(
    config_or_machine: Union[Mapping[str, Any], MachineNode],
    *,
    ran: Optional[List[str]] = None,
    guards: Union[bool, Mapping[str, bool]] = True,
    service_results: Optional[Mapping[str, Any]] = None,
) -> MachineLogic:
    """A `MachineLogic` that satisfies every name the chart declares.

    Args:
        config_or_machine: Raw JSON config or a `MachineNode`.
        ran: If given, every executed action appends its name here -- the
            "what happened" record tests assert on.
        guards: ``True`` / ``False`` for every guard, or a mapping of guard
            name → value (unlisted guards default to ``True``). Guards are
            looked up at call time, so mutating the mapping between sends
            flips them live (what `xsm simulate`'s ``g`` key does).
        service_results: Optional mapping of service name → value the stub
            service returns (becomes ``event.data`` on ``onDone``). Unlisted
            services return ``None``. Services complete synchronously, so
            ``onDone`` fires within the same macrostep on both engines.

    Returns:
        A `MachineLogic` ready for `create_machine(config, logic=...)`.

    Example:
        >>> from xstate_statemachine import create_machine, SyncInterpreter
        >>> from xstate_statemachine.testing_utils import stub_logic
        >>> cfg = {"id": "m", "initial": "a", "states": {
        ...     "a": {"on": {"GO": {"target": "b", "guard": "ok",
        ...                          "actions": "log"}}}, "b": {}}}
        >>> ran: list = []
        >>> m = create_machine(cfg, logic=stub_logic(cfg, ran=ran))
        >>> i = SyncInterpreter(m).start(); i.send("GO"); ran
        ['log']
    """
    action_names, guard_names, service_names = logic_names(config_or_machine)
    record: List[str] = ran if ran is not None else []
    # 📝 Keep the caller's mapping BY REFERENCE (no copy) so flipping a
    #    guard between sends is visible to the stub -- the documented
    #    "live" behaviour `xsm simulate`'s `g` key relies on.
    guard_table: Mapping[str, bool] = (
        guards if isinstance(guards, Mapping) else {}
    )
    default_guard = guards if isinstance(guards, bool) else True
    results: Mapping[str, Any] = service_results or {}

    def mk_action(name: str):
        def _action(i: Any, c: Any, e: Any, ad: Any) -> None:
            record.append(name)

        _action.__name__ = f"stub_action_{name}"
        return _action

    def mk_guard(name: str):
        def _guard(c: Any, e: Any) -> bool:
            return bool(guard_table.get(name, default_guard))

        _guard.__name__ = f"stub_guard_{name}"
        return _guard

    def mk_service(name: str):
        def _service(i: Any, c: Any, e: Any) -> Any:
            return results.get(name)

        _service.__name__ = f"stub_service_{name}"
        return _service

    return MachineLogic(
        actions={a: mk_action(a) for a in action_names},
        guards={g: mk_guard(g) for g in guard_names},
        services={s: mk_service(s) for s in service_names},
    )
