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

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

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
    config_or_machine: Union[Mapping[str, Any], MachineNode[Any]],
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Return ``(actions, guards, services)`` a chart references by name.

    Accepts the raw JSON config (a mapping) or a built `MachineNode`. For
    a machine the PARSED model is walked -- entry/exit/transition actions,
    leaf guards inside composite guards, every invoke ``src`` -- so the
    result is exactly the set of names the engine will look up. Built-in
    actions (`assign`, `raise`, `sendTo`, …) are excluded; the engine
    provides those. A ``spawn_<key>`` / ``spawn_blocking_<key>`` action is
    reported as the SERVICE ``<key>`` (what `LogicLoader` requires and the
    engine looks up), not as an action.

    Args:
        config_or_machine: Raw JSON config or a built `MachineNode`.

    Returns:
        ``(actions, guards, services)`` name sets.

    Raises:
        InvalidConfigError: (and the other `create_machine` build errors)
            for a raw config that is not a valid chart.
    """
    # 🏛️ RU-25: a raw config is BUILT first, so both input forms answer
    #    from the same parsed model. The CLI extractor only understands
    #    `params.guards` composites and returned `{"and"}` where the machine
    #    path returned the leaf guards for the very same chart.
    config_or_machine = _as_machine(config_or_machine)

    from .validation import transitions_of, walk

    actions: Set[str] = set()
    guards: Set[str] = set()
    services: Set[str] = set()
    for node in walk(config_or_machine):
        _action_names(
            list(node.entry) + list(node.exit), actions, guards, services
        )
        for inv in node.invoke:
            if inv.src:
                services.add(inv.src)
        for _label, t in transitions_of(node):
            _action_names(t.actions, actions, guards, services)
            _guard_names(t.guard_def, guards)
    return actions, guards, services


def _as_machine(
    config_or_machine: Union[Mapping[str, Any], MachineNode[Any]],
) -> MachineNode[Any]:
    """Return a parsed `MachineNode` for a raw config or a machine.

    Args:
        config_or_machine: Raw JSON config or a `MachineNode`.

    Returns:
        The machine itself, or one built from the config. A config that is
        valid but declares names with no implementation is built with an
        empty `MachineLogic`; every other build error is the caller's,
        verbatim (not a misleading ``TypeError`` from ``dict(...)``).
    """
    if isinstance(config_or_machine, MachineNode):
        return config_or_machine
    from .exceptions import ImplementationMissingError
    from .factory import create_machine

    # 📝 `create_machine` is typed on `Dict`; a non-mapping (int, list,
    #    None) must still reach it so the caller gets ITS error, hence the
    #    cast rather than a `dict(...)` that would raise first.
    raw: Dict[str, Any] = cast(Dict[str, Any], config_or_machine)
    try:
        return create_machine(raw)
    except ImplementationMissingError:
        # 📝 Expected: the config is VALID but declares names we are about
        #    to stub.
        return MachineNode(dict(raw), MachineLogic())


def _action_names(
    action_defs: Any,
    actions: Set[str],
    guards: Set[str],
    services: Optional[Set[str]] = None,
    depth: int = 0,
) -> None:
    """Collect user action names, descending into static `choose` branches
    (their actions AND their guards) -- the engine looks those up by name
    when the branch runs."""
    from .actions import CHOOSE, choose_branches, is_builtin, resolve_builtin
    from .models import (
        ActionDefinition,
        GuardDefinition,
        is_spawn_action,
        spawn_service_key,
    )

    if depth > 32:  # a hand-built self-referencing choose; stop quietly
        return
    for act in action_defs:
        # 📝 Duck-typed: a parsed action from ANOTHER import of the package
        #    (`src.xstate_statemachine` vs `xstate_statemachine`) is not an
        #    instance of this copy's `ActionDefinition`.
        if isinstance(act, (str, dict)):
            try:
                act = ActionDefinition(act)
            except Exception:  # noqa: BLE001 -- not a static action
                continue
        elif not isinstance(getattr(act, "type", None), str):
            continue
        if is_spawn_action(act.type):
            # 🎭 `spawn_<key>` is resolved from `logic.services`, never from
            #    `logic.actions` (same routing as `LogicLoader`); stubbing it
            #    as an ACTION would shadow the spawn (#155 checks actions
            #    first).
            if services is not None:
                services.add(spawn_service_key(act.type))
            continue
        if not is_builtin(act.type):
            actions.add(act.type)
            continue
        if resolve_builtin(act.type) != CHOOSE:
            continue
        for branch in choose_branches(act.params):
            raw = branch.get("actions", [])
            _action_names(
                raw if isinstance(raw, list) else [raw],
                actions,
                guards,
                services,
                depth + 1,
            )
            guard_cfg = branch.get("guard", branch.get("cond"))
            if guard_cfg is not None and not callable(guard_cfg):
                try:
                    _guard_names(GuardDefinition(guard_cfg), guards)
                except Exception:  # noqa: BLE001 -- not a static guard
                    pass


def stub_logic(
    config_or_machine: Union[Mapping[str, Any], MachineNode[Any]],
    *,
    ran: Optional[List[str]] = None,
    guards: Union[bool, Mapping[str, bool]] = True,
    service_results: Optional[Mapping[str, Any]] = None,
    guard_log: Optional[List[str]] = None,
) -> MachineLogic[Any]:
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
        guard_log: If given, every guard evaluation appends the guard's
            name here, in order -- which guards the engine evaluated, and
            how often (the conformance cases' ``record_guards``).

    Returns:
        A `MachineLogic` ready for `create_machine(config, logic=...)`.

    Example:
        >>> from xstate_statemachine import create_machine, SyncInterpreter
        >>> from xstate_statemachine.testing_utils import stub_logic
        >>> cfg = {"id": "m", "initial": "a", "states": {
        ...     "a": {"on": {"GO": {"target": "b", "guard": "ok",
        ...                          "actions": "save"}}}, "b": {}}}
        >>> ran: list = []
        >>> m = create_machine(cfg, logic=stub_logic(cfg, ran=ran))
        >>> i = SyncInterpreter(m).start(); i.send("GO"); ran
        ['save']
    """
    # 🏛️ Names are read from the PARSED machine, not the raw dict. The raw
    #    extractor only understands the `params.guards` composite shape, so
    #    `{"type": "and", "children": [...]}` (which the engine accepts)
    #    left its leaves unstubbed -> ImplementationMissingError at runtime.
    #    Building also makes an invalid config raise exactly what
    #    `create_machine` raises, instead of a misleading `TypeError`/
    #    `ValueError` from `dict(...)` or a silent empty stub.
    config_or_machine = _as_machine(config_or_machine)
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

    def mk_action(name: str) -> Callable[..., Any]:
        """Build a stub action that records *name* when it runs.

        Args:
            name: The action name to append to the record.

        Returns:
            The stub action callable.
        """

        def _action(i: Any, c: Any, e: Any, ad: Any) -> None:
            record.append(name)

        _action.__name__ = f"stub_action_{name}"
        return _action

    def mk_guard(name: str) -> Callable[..., Any]:
        """Build a stub guard looking *name* up in the guard table.

        Args:
            name: The guard name.

        Returns:
            A guard returning the table entry, or the default verdict.
        """

        def _guard(c: Any, e: Any) -> bool:
            if guard_log is not None:
                guard_log.append(name)
            return bool(guard_table.get(name, default_guard))

        _guard.__name__ = f"stub_guard_{name}"
        return _guard

    def mk_service(name: str) -> Callable[..., Any]:
        """Build a stub service returning the canned result for *name*.

        Args:
            name: The service name.

        Returns:
            A service returning ``service_results[name]`` or ``None``.
        """

        def _service(i: Any, c: Any, e: Any) -> Any:
            return results.get(name)

        _service.__name__ = f"stub_service_{name}"
        return _service

    return MachineLogic(
        actions={a: mk_action(a) for a in action_names},
        guards={g: mk_guard(g) for g in guard_names},
        services={s: mk_service(s) for s in service_names},
    )
