# src/xstate_statemachine/contrib/django/fsm.py
# -----------------------------------------------------------------------------
# 🔁 Migrating from django-fsm / django-fsm-2 (#310)
# -----------------------------------------------------------------------------
# 🏛️ A mechanical, reversible four-step move -- the ``xsm_migrate_fsm``
#    command drives it:
#
#      1. `extract_chart(Model, "state")` reads the ``@transition``
#         metadata (source → target per decorated method; ``conditions``
#         and ``permission`` preserved as guard NAMES) and emits XState
#         JSON for review. States come from the field's ``choices``, then
#         every source / target seen. ``source="*"`` / ``"+"`` fan out
#         over the known states (``"+"`` skips the target itself).
#      2. Add a `StatechartField` beside the `FSMField` (a normal schema
#         migration -- ``makemigrations``).
#      3. `migrate_rows(Model, "state")` fills the snapshot from the FSM
#         column with `from_state_ids` (nothing runs) -- batched by pk,
#         RESUMABLE (only rows whose snapshot is empty are touched) and
#         idempotent (a second run changes nothing).
#      4. Dual-read for one release: `FSMDualWriteMixin` keeps the old
#         column in sync from the statechart on every ``send()``; code
#         still reading ``order.state`` keeps working. Then drop it.
#
# 📝 Imports ``django_fsm`` lazily: the [django] extra does not depend
#    on it, only this migration path does.
# -----------------------------------------------------------------------------
"""`extract_chart`, `migrate_rows`, `FSMDualWriteMixin`."""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.db import transaction

__all__ = [
    "FSMDualWriteMixin",
    "extract_chart",
    "guard_name",
    "migrate_rows",
    "state_key",
]

_ANY, _OTHER = "*", "+"


def state_key(value: Any) -> str:
    """An FSM value as an XState state key (``"in-review"`` →
    ``"in_review"``; ``"état"`` stays; ints become ``"s_3"``).

    📝 Not injective on its own (``"in-review"`` and ``"in_review"`` share
    a key): `extract_chart` de-duplicates and records the original value
    in the state's ``meta.fsm_value`` -- `fsm_value_index` /
    `fsm_value_of` read that back, so every direction is exact.
    """
    s = re.sub(r"[^\w]", "_", str(value))
    if not s or s[0].isdigit():
        s = f"s_{s}"
    return s


def _node_value(node: Any) -> Any:
    meta = getattr(node, "meta", None) or {}
    return meta["fsm_value"] if "fsm_value" in meta else node.key


def fsm_value_index(machine: Any) -> Dict[Any, str]:
    """FSM column value → top-level state key, from ``meta.fsm_value``
    (a state without one stands for its own key)."""
    return {_node_value(n): k for k, n in machine.states.items()}


def fsm_value_of(
    machine: Any, leaf: str, override: Optional[Dict[str, Any]] = None
) -> Any:
    """The FSM column value for the active *leaf* id (``override`` -- the
    model's ``fsm_value_for_state`` -- wins)."""
    if override and leaf in override:
        return override[leaf]
    node = machine.get_state_by_id(leaf)
    return leaf.rsplit(".", 1)[-1] if node is None else _node_value(node)


def key_for_value(
    machine: Any, value: Any, override: Optional[Dict[str, Any]] = None
) -> Optional[str]:
    """The top-level state key a column *value* adopts, or None."""
    for leaf, v in (override or {}).items():
        if v == value:
            return leaf.split(".", 1)[-1] if "." in leaf else leaf
    return fsm_value_index(machine).get(value)


def guard_name(obj: Any) -> str:
    """A camelCase guard name for a condition callable / permission."""
    if isinstance(obj, str):
        base = obj.split(".")[-1]
    else:
        base = getattr(obj, "__name__", type(obj).__name__)
    parts = [p for p in re.split(r"[^0-9A-Za-z]+", base) if p]
    if not parts:
        return "condition"
    return (
        parts[0][0].lower()
        + parts[0][1:]
        + "".join(p[:1].upper() + p[1:] for p in parts[1:])
    )


def fsm_fields(model: Any) -> List[str]:
    """Names of the model's FSMFields (for error messages / selection)."""
    try:
        from django_fsm import FSMFieldMixin
    except ImportError:  # pragma: no cover - documented
        return []
    return [
        f.name
        for f in model._meta.get_fields()
        if isinstance(f, FSMFieldMixin)
    ]


def _field(model: Any, field: str) -> Any:
    try:
        from django_fsm import FSMFieldMixin
    except ImportError as exc:  # pragma: no cover - documented
        raise ImportError(
            "xsm_migrate_fsm needs django-fsm-2 (pip install django-fsm-2)"
        ) from exc
    from django.core.exceptions import FieldDoesNotExist

    try:
        f = model._meta.get_field(field)
    except FieldDoesNotExist:
        # 📝 #310 battle: name the candidates -- a team with `status`
        #    instead of `state` should not have to read the model.
        found = fsm_fields(model)
        hint = f" FSMFields on the model: {', '.join(found)}." if found else ""
        raise TypeError(
            f"{model.__name__} has no field named {field!r}.{hint}"
        ) from None
    if not isinstance(f, FSMFieldMixin):
        raise TypeError(f"{model.__name__}.{field} is not an FSMField")
    return f


def _transitions(model: Any, f: Any) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for t in f.get_all_transitions(model):
        key = (t.name, t.source, id(t.target))
        if key not in seen:
            seen.add(key)
            out.append(t)
    return sorted(out, key=lambda t: (t.name, str(t.source)))


def _dynamic(t: Any) -> Optional[List[Any]]:
    """The allowed states of a ``RETURN_VALUE`` / ``GET_STATE`` target
    (None for a plain one). An UNBOUNDED dynamic target -- no allowed
    states declared -- cannot be expressed as a chart: refused loudly."""
    if t.target is None or isinstance(t.target, (str, int)):
        return None
    allowed = list(getattr(t.target, "allowed_states", None) or [])
    if not allowed:
        raise ValueError(
            f"@transition {t.name!r}: target "
            f"{type(t.target).__name__}() declares no allowed states, so "
            f"the chart cannot know where it goes. List them -- "
            f"RETURN_VALUE('a', 'b') / GET_STATE(fn, states=['a', 'b'])."
        )
    return allowed


def _assign_keys(states: List[Any]) -> Dict[Any, str]:
    """FSM value → a UNIQUE state key; values that already are their own
    key win it, the rest get ``_2``, ``_3`` … on a clash (#310 battle:
    ``"in-progress"`` and ``"in_progress"`` used to merge into one)."""
    keys: Dict[Any, str] = {}
    used: set = set()
    for exact in (True, False):
        for v in states:
            k = state_key(v)
            if (k == v) != exact:
                continue
            base, n = k, 2
            while k in used:
                k, n = f"{base}_{n}", n + 1
            used.add(k)
            keys[v] = k
    return keys


class _GuardNames:
    """Stable, collision-free guard names (#310 battle: two different
    lambdas were both ``lambda``; ``billing.is_ready`` and
    ``shipping.is_ready`` merged -- one implementation guarding both)."""

    def __init__(self) -> None:
        self.by_obj: Dict[Any, str] = {}
        self.used: Dict[str, Any] = {}

    def name(self, obj: Any, fallback: str) -> str:
        ident = obj if isinstance(obj, str) else id(obj)
        if ident in self.by_obj:
            return self.by_obj[ident]
        base = guard_name(obj)
        if base in ("lambda", "condition"):
            base = guard_name(fallback)
        if base in self.used:
            mod = getattr(obj, "__module__", "") or ""
            base = guard_name(f"{mod.rsplit('.', 1)[-1]}_{base}")
        name, n = base, 2
        while name in self.used:
            name, n = f"{base}{n}", n + 1
        self.used[name] = obj
        self.by_obj[ident] = name
        return name


def _spec_list(existing: Any) -> List[Any]:
    if existing is None:
        return []
    return existing if isinstance(existing, list) else [existing]


def _candidates(
    t: Any, targets: List[Any], keys: Dict[Any, str], guards: List[Any]
) -> List[Dict[str, Any]]:
    """The transition specs one ``@transition`` contributes per source."""
    meta: Dict[str, Any] = {"method": t.name}
    if t.on_error is not None:
        meta["on_error"] = keys[t.on_error]
    if t.custom:
        meta["custom"] = t.custom
    dynamic = _dynamic(t) is not None
    specs = []
    for target in targets:
        g = list(guards)
        m = dict(meta)
        if dynamic:
            m["dynamic"] = type(t.target).__name__
            g.append(
                {
                    "type": guard_name(f"{t.name}_returns"),
                    "params": {"value": target},
                }
            )
        spec: Dict[str, Any] = {"target": keys[target], "meta": m}
        if len(g) == 1:
            spec["guard"] = g[0]
        elif g:
            spec["guard"] = {"type": "and", "children": g}
        specs.append(spec)
    return specs


def extract_chart(
    model: Any, field: str = "state", *, machine_id: Optional[str] = None
) -> Dict[str, Any]:
    """XState JSON equivalent to *model*'s ``@transition`` methods.

    Event names are the method names upper-cased (``submit`` →
    ``SUBMIT``); each transition's ``meta.method`` records the original
    name, and ``conditions`` / ``permission`` become guard names (all of
    them combined with ``and``; a lambda is named after its method --
    ``goPermission``, ``goCondition2``; a clash is disambiguated).
    ``custom`` lands in ``meta.custom``; ``on_error`` becomes a state
    and ``meta.on_error``. A ``RETURN_VALUE`` / ``GET_STATE`` target fans
    out into one candidate per allowed state, each guarded by
    ``<method>Returns`` with ``params.value`` (implement it to say which
    one the method picks); an unbounded one is refused. A state whose
    value is not its own key records it in ``meta.fsm_value`` -- the
    migration and the dual write read it back. The result is byte-stable
    across runs and builds under ``strictConfig`` once the guards are
    implemented (`stub_logic` for a dry run).
    """
    f = _field(model, field)
    transitions = _transitions(model, f)
    states: List[Any] = []

    def add(v: Any) -> None:
        if v not in (None, _ANY, _OTHER) and v not in states:
            states.append(v)

    for value, _label in getattr(f, "choices", None) or ():
        add(value)
    add(f.get_default() if f.has_default() else None)
    targets: Dict[int, List[Any]] = {}
    for t in transitions:
        add(t.source)
        dyn = _dynamic(t)
        targets[id(t)] = [] if t.target is None else (dyn or [t.target])
        for v in targets[id(t)] + [t.on_error]:
            add(v)
    if not states:
        raise ValueError(f"{model.__name__}.{field}: no states found")
    initial = f.get_default() if f.has_default() else states[0]
    keys = _assign_keys(states)
    nodes: Dict[str, Dict[str, Any]] = {
        keys[v]: ({} if keys[v] == v else {"meta": {"fsm_value": v}})
        for v in states
    }
    names = _GuardNames()
    for t in transitions:
        if t.target is None:
            continue  # a validating no-op transition keeps the state
        if t.source == _ANY:
            sources = states
        elif t.source == _OTHER:
            sources = [s for s in states if s != t.target]
        else:
            sources = [t.source]
        guards: List[Any] = [
            names.name(c, f"{t.name}_condition_{i + 1}")
            for i, c in enumerate(t.conditions or [])
        ]
        if t.permission:
            guards.append(names.name(t.permission, f"{t.name}_permission"))
        specs = _candidates(t, targets[id(t)], keys, guards)
        for src in sources:
            on = nodes[keys[src]].setdefault("on", {})
            merged = _spec_list(on.get(t.name.upper())) + [
                dict(s) for s in specs
            ]
            on[t.name.upper()] = merged[0] if len(merged) == 1 else merged
    return {
        "id": machine_id or model._meta.model_name,
        "initial": keys[initial],
        "states": nodes,
    }


def _adopt_blob(
    model: Any, machine: Any, key: str, ctx: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    import json as _json

    from ...persistence.adopt import from_state_ids

    return dict(
        _json.loads(
            from_state_ids(
                machine,
                [key],
                ctx,
                timers=True,
                clock=getattr(model, "statechart_clock", None),
            )
        )
    )


def _write_deadlines(model: Any, using: str, pk: Any, snap: Any) -> None:
    """⏰ An adopted ``after`` state is indexed for the scanner exactly
    like one a ``send()`` entered (the timer starts at migration time --
    the legacy row's own entry time is unknown)."""
    if not snap.get("deadlines") or not model._xsm_has_tables():
        return
    from ...persistence.deadline import Deadline
    from . import _deadlines

    _deadlines.write(
        using,
        model._meta.db_table,
        str(pk),
        [Deadline.from_dict(d) for d in snap["deadlines"]],
    )


def migrate_rows(
    model: Any,
    fsm_field: str = "state",
    *,
    statechart_field: str = "statechart",
    machine: Any = None,
    batch: int = 1000,
    context: Optional[Callable[[Any], Dict[str, Any]]] = None,
    using: str = "default",
    stop_after_batches: Optional[int] = None,
    value_map: Optional[Dict[Any, Any]] = None,
    unknown: Optional[Dict[str, int]] = None,
    failed: Optional[Dict[Any, str]] = None,
) -> Tuple[int, int]:
    """Step 3: fill empty snapshots from the FSM column.

    Only rows whose *statechart_field* is NULL are touched, one
    transaction per batch, walking the pk (keyset) -- so an interrupted
    run resumes where it stopped and a second run is a no-op. Returns
    ``(migrated, batches)``. ``stop_after_batches`` exists to test the
    interruption. An adopted state with an ``after`` timer gets its
    deadline written (the timer starts at migration time).

    🔥 #310 battle: a column holding a value the chart does not know (a
    renamed legacy state, a typo, an empty string, NULL) used to kill
    the run on that row with a traceback, half-migrated. Such rows are
    SKIPPED and counted per value in *unknown* (the caller reports them);
    *value_map* folds renamed values (``{"open": "new"}``) in first.
    A *context* callable that raises for a row fails the run loudly
    (naming the pk; that batch rolls back whole) -- or, given a *failed*
    dict, records ``pk → error`` and moves on.
    """
    if batch < 1:
        raise ValueError("batch must be >= 1")
    if machine is None:
        machine = model().statechart_machine_node()
    index = fsm_value_index(machine)
    value_map = dict(value_map or {})
    for src, dst in value_map.items():
        if dst not in index and dst not in machine.states:
            raise ValueError(
                f"--map {src}={dst}: the chart has no state {dst!r} "
                f"(states: {', '.join(sorted(map(str, index)))})"
            )
    job = _Job(model, machine, index, value_map, fsm_field, statechart_field)
    job.context, job.failed, job.using = context, failed, using
    job.skipped = {} if unknown is None else unknown
    mgr = model._base_manager.using(using)
    done = batches = 0
    # 📝 #310 battle: a KEYSET walk, not `exclude(pk__in=skipped)` -- 40k
    #    unknown rows made ONE query with 40k parameters (SQLite's limit
    #    is 32766, older builds 999) from a list that grew without bound.
    last: Any = None
    while stop_after_batches is None or batches < stop_after_batches:
        qs = mgr.filter(**{f"{statechart_field}__isnull": True})
        if last is not None:
            qs = qs.filter(pk__gt=last)
        rows = list(qs.order_by("pk").only("pk", fsm_field)[:batch])
        if not rows:
            break
        last = rows[-1].pk
        with transaction.atomic(using=using):
            for row in rows:
                done += job.migrate(mgr, row)
        batches += 1
    return done, batches


class _Job:
    """One `migrate_rows` run's settings + the per-row step."""

    context: Optional[Callable[[Any], Dict[str, Any]]] = None
    failed: Optional[Dict[Any, str]] = None
    using: str = "default"
    skipped: Dict[str, int]

    def __init__(
        self,
        model: Any,
        machine: Any,
        index: Dict[Any, str],
        value_map: Dict[Any, Any],
        fsm_field: str,
        statechart_field: str,
    ) -> None:
        self.model, self.machine, self.index = model, machine, index
        self.value_map, self.fsm_field = value_map, fsm_field
        self.name = statechart_field

    def _key(self, raw: Any) -> Optional[str]:
        value = self.value_map.get(raw, raw)
        key = self.index.get(value)
        if key is None and isinstance(value, str):
            if value in self.machine.states:
                key = value  # a --map straight to a state key
        return key

    def _context(self, row: Any) -> Any:
        if self.context is None:
            return None
        try:
            return self.context(row)
        except Exception as exc:
            if self.failed is None:
                raise ValueError(
                    f"context() failed for {self.model.__name__} "
                    f"pk={row.pk!r}: {exc!r} (pass failed={{}} to skip and "
                    f"report instead)"
                ) from exc
            self.failed[row.pk] = repr(exc)
            return _NO_VALUE

    def migrate(self, mgr: Any, row: Any) -> int:
        from .fields import sibling_values

        raw = row.__dict__.get(self.fsm_field)
        key = self._key(raw)
        if key is None:
            self.skipped[str(raw)] = self.skipped.get(str(raw), 0) + 1
            return 0
        ctx = self._context(row)
        if ctx is _NO_VALUE:
            return 0
        snap = _adopt_blob(self.model, self.machine, key, ctx)
        values = sibling_values(self.name, snap)
        values[self.name] = snap
        values[f"{self.name}_version"] = 0
        # 🔒 Re-check NULL AND the FSM value in the UPDATE: a concurrent
        #    run (or a send that initialised it) is never overwritten, and
        #    a row a live writer moved since we read it is left for the
        #    next run (#310 battle: the site is up during the migration).
        n = int(
            mgr.filter(
                pk=row.pk,
                **{f"{self.name}__isnull": True, self.fsm_field: raw},
            ).update(**values)
        )
        if n:
            _write_deadlines(self.model, self.using, row.pk, snap)
        return n


_NO_VALUE: Any = object()


def _top_value(
    machine: Any, leaves: List[str], override: Dict[str, Any]
) -> Any:
    """The ONE FSM value the active *leaves* stand for -- their
    top-level state's (a compound's children all map to it) -- or
    `_NO_VALUE` when they span several (a parallel root)."""
    if not leaves:
        return _NO_VALUE
    vals = set()
    for leaf in leaves:
        if leaf in override:
            vals.add(override[leaf])
            continue
        parts = leaf.split(".")
        vals.add(fsm_value_of(machine, ".".join(parts[:2]), override))
    return vals.pop() if len(vals) == 1 else _NO_VALUE


class FSMDualWriteMixin:
    """Step 4 (dual-read window): after every ``send()`` copy the active
    state back into the old FSM column, so readers of ``instance.state``
    keep working for one release. Set ``fsm_dual_write_field`` and an
    optional ``fsm_value_for_state`` mapping (leaf id → FSM value).
    Without one, the value is the top-level state's ``meta.fsm_value``
    (`extract_chart` records it whenever the value is not its own key:
    ``"in-progress"``, ``3``) or its key -- exact in both directions. A
    configuration spanning several top-level values (a parallel root)
    has no single FSM value: the column is left alone.

    🔥 #310 battle: the window is TWO-WAY. Old code still deployed moves
    the FSM column through its ``@transition`` methods; the snapshot
    must follow or the next ``send()`` starts from a stale state. On
    ``save()``, when the ROW's FSM column disagrees with the ROW's
    snapshot, the snapshot is re-adopted at the column's value (version
    bumped, fenced: a concurrent ``send()`` wins and never sees a
    `ConflictError` from it).
    """

    fsm_dual_write_field: str = "state"
    fsm_value_for_state: Dict[str, Any] = {}

    def save(self, *args: Any, **kwargs: Any) -> None:
        # 📝 the mixin's save() deliberately never rewrites the statechart
        #    columns; the re-adoption is a separate fenced UPDATE after it.
        super().save(*args, **kwargs)  # type: ignore[misc]
        self._xsm_adopt_fsm_value()

    def _xsm_fsm_value(self, machine: Any, leaves: List[str]) -> Any:
        return _top_value(machine, leaves, self.fsm_value_for_state)

    def _xsm_adopt_fsm_value(self) -> None:
        """Re-adopt the snapshot when the FSM column moved without us."""
        from .fields import sibling_values

        field = self.fsm_dual_write_field
        name = self.statechart_field_obj().name  # type: ignore[attr-defined]
        if self.pk is None:  # type: ignore[attr-defined]
            return
        vcol = f"{name}_version"
        using = self._state.db or "default"  # type: ignore[attr-defined]
        mgr = type(self)._base_manager.using(using)  # type: ignore[attr-defined]
        # 📝 #310 battle (live writers): compare the ROW's column with the
        #    ROW's snapshot, read together. The instance may be stale (a
        #    send() committed since it was loaded): adopting its in-memory
        #    value would roll the newer state back.
        row = (
            mgr.filter(pk=self.pk)  # type: ignore[attr-defined]
            .values(field, name, vcol)
            .first()
        )
        if not row or row[name] is None:
            return  # not migrated yet: the migration adopts the column
        value, snap, expected = row[field], row[name], int(row[vcol] or 0)
        self.__dict__[name] = snap
        setattr(self, vcol, expected)
        if value in (None, ""):
            return
        machine = self.statechart_machine_node()  # type: ignore[attr-defined]
        current = self._xsm_fsm_value(
            machine, sorted(snap.get("state_ids") or [])
        )
        if current is _NO_VALUE or current == value:
            return
        key = key_for_value(machine, value, self.fsm_value_for_state)
        if key is None:
            return  # an unknown legacy value: leave the snapshot alone
        new_snap = _adopt_blob(type(self), machine, key, snap.get("context"))
        values = sibling_values(name, new_snap)
        values[name] = new_snap
        values[vcol] = expected + 1
        # 🔒 fenced on the version AND the column: a concurrent send()
        #    wins, we never stomp a newer snapshot with a stale column
        n = mgr.filter(
            pk=self.pk, **{vcol: expected, field: value}  # type: ignore[attr-defined]
        ).update(**values)
        if n:
            _write_deadlines(type(self), using, self.pk, new_snap)  # type: ignore[attr-defined]
            for k, v in values.items():
                setattr(self, k, v)

    def _xsm_after_write(self, ctx: Dict[str, Any]) -> None:
        super()._xsm_after_write(ctx)  # type: ignore[misc]
        machine = self.statechart_machine_node()  # type: ignore[attr-defined]
        value = self._xsm_fsm_value(machine, sorted(ctx["receipt"].state_ids))
        if value is _NO_VALUE:
            return  # parallel: no single FSM value
        field = self.fsm_dual_write_field
        type(self)._base_manager.using(  # type: ignore[attr-defined]
            ctx["using"]
        ).filter(
            pk=self.pk  # type: ignore[attr-defined]
        ).update(
            **{field: value}
        )
        # FSMField(protected=True) refuses setattr: write the raw slot.
        self.__dict__[field] = value
