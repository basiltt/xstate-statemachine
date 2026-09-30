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
    ``"in_review"``; ints become ``"s_3"``)."""
    s = re.sub(r"[^0-9A-Za-z_]", "_", str(value))
    if not s or s[0].isdigit():
        s = f"s_{s}"
    return s


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


def _field(model: Any, field: str) -> Any:
    try:
        from django_fsm import FSMFieldMixin
    except ImportError as exc:  # pragma: no cover - documented
        raise ImportError(
            "xsm_migrate_fsm needs django-fsm-2 (pip install django-fsm-2)"
        ) from exc
    f = model._meta.get_field(field)
    if not isinstance(f, FSMFieldMixin):
        raise TypeError(f"{model.__name__}.{field} is not an FSMField")
    return f


def _transitions(model: Any, f: Any) -> List[Any]:
    out: List[Any] = []
    seen = set()
    for t in f.get_all_transitions(model):
        key = (t.name, t.source, t.target)
        if key not in seen:
            seen.add(key)
            out.append(t)
    return sorted(out, key=lambda t: (t.name, str(t.source)))


def extract_chart(
    model: Any, field: str = "state", *, machine_id: Optional[str] = None
) -> Dict[str, Any]:
    """XState JSON equivalent to *model*'s ``@transition`` methods.

    Event names are the method names upper-cased (``submit`` →
    ``SUBMIT``); each transition's ``meta.method`` records the original
    name, and ``conditions`` / ``permission`` become guard names (all of
    them combined with ``and``). The returned dict builds under
    ``strictConfig`` once the guards are implemented (`stub_logic` for a
    dry run).
    """
    f = _field(model, field)
    transitions = _transitions(model, f)
    states: List[str] = []

    def add(v: Any) -> None:
        if v not in (None, _ANY, _OTHER) and v not in states:
            states.append(v)

    for value, _label in getattr(f, "choices", None) or ():
        add(value)
    add(f.get_default() if f.has_default() else None)
    for t in transitions:
        add(t.source)
        add(t.target)
    if not states:
        raise ValueError(f"{model.__name__}.{field}: no states found")
    initial = f.get_default() if f.has_default() else states[0]
    nodes: Dict[str, Dict[str, Any]] = {state_key(s): {} for s in states}
    for t in transitions:
        if t.target is None:
            continue  # a validating no-op transition keeps the state
        sources = (
            states
            if t.source == _ANY
            else (
                [s for s in states if s != t.target]
                if t.source == _OTHER
                else [t.source]
            )
        )
        guards = [guard_name(c) for c in (t.conditions or [])]
        if t.permission:
            guards.append(guard_name(t.permission))
        spec: Dict[str, Any] = {
            "target": state_key(t.target),
            "meta": {"method": t.name},
        }
        if len(guards) == 1:
            spec["guard"] = guards[0]
        elif guards:
            spec["guard"] = {"type": "and", "children": guards}
        for src in sources:
            on = nodes[state_key(src)].setdefault("on", {})
            existing = on.get(t.name.upper())
            if existing is None:
                on[t.name.upper()] = spec
            elif isinstance(existing, list):
                existing.append(spec)
            else:
                on[t.name.upper()] = [existing, spec]
    return {
        "id": machine_id or model._meta.model_name,
        "initial": state_key(initial),
        "states": nodes,
    }


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
) -> Tuple[int, int]:
    """Step 3: fill empty snapshots from the FSM column.

    Only rows whose *statechart_field* is NULL are touched, one
    transaction per batch, in pk order -- so an interrupted run resumes
    where it stopped and a second run is a no-op. Returns ``(migrated,
    batches)``. ``stop_after_batches`` exists to test the interruption.
    """
    import json as _json

    from ...persistence.adopt import from_state_ids
    from .fields import sibling_values

    if batch < 1:
        raise ValueError("batch must be >= 1")
    if machine is None:
        machine = model().statechart_machine_node()
    mgr = model._base_manager.using(using)
    vcol = f"{statechart_field}_version"
    done = batches = 0
    while stop_after_batches is None or batches < stop_after_batches:
        rows = list(
            mgr.filter(**{f"{statechart_field}__isnull": True})
            .order_by("pk")
            .only("pk", fsm_field)[:batch]
        )
        if not rows:
            break
        with transaction.atomic(using=using):
            for row in rows:
                value = getattr(row, fsm_field)
                snap = _json.loads(
                    from_state_ids(
                        machine,
                        [state_key(value)],
                        context(row) if context else None,
                    )
                )
                values = sibling_values(statechart_field, snap)
                values[statechart_field] = snap
                values[vcol] = 0
                # 🔒 Re-check NULL in the UPDATE: a concurrent run (or a
                #    send that initialised it) is never overwritten.
                done += mgr.filter(
                    pk=row.pk, **{f"{statechart_field}__isnull": True}
                ).update(**values)
        batches += 1
    return done, batches


class FSMDualWriteMixin:
    """Step 4 (dual-read window): after every ``send()`` copy the active
    leaf back into the old FSM column, so readers of ``instance.state``
    keep working for one release. Set ``fsm_dual_write_field`` and an
    optional ``fsm_value_for_state`` mapping (leaf id → FSM value;
    default: the leaf's key)."""

    fsm_dual_write_field: str = "state"
    fsm_value_for_state: Dict[str, Any] = {}

    def _xsm_after_write(self, ctx: Dict[str, Any]) -> None:
        super()._xsm_after_write(ctx)  # type: ignore[misc]
        leaves = sorted(ctx["receipt"].state_ids)
        if len(leaves) != 1:
            return  # parallel: no single FSM value
        leaf = leaves[0]
        value = self.fsm_value_for_state.get(leaf, leaf.rsplit(".", 1)[-1])
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
