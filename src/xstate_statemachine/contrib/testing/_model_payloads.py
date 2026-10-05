# src/xstate_statemachine/contrib/testing/_model_payloads.py
# -----------------------------------------------------------------------------
# 📦 Payload strategies for `model_test` (#271), split out of model.py
# -----------------------------------------------------------------------------
"""Hypothesis payload strategies inferred from pydantic `EventModel`s."""

from __future__ import annotations

import datetime
import decimal
import typing
from typing import Any, Dict, List, Mapping, Sequence, Union

from ...exceptions import MissingExtraError
from ...models import MachineNode


def _hypothesis() -> Any:
    try:
        import hypothesis  # noqa: F401
    except ImportError as exc:
        raise MissingExtraError(
            "testing", "hypothesis", hint=f"(import failed: {exc})"
        ) from exc
    return hypothesis


def _annotation_strategy(st: Any, ann: Any) -> Any:
    origin = typing.get_origin(ann)
    args = typing.get_args(ann)
    if ann is Any:
        return st.none()
    if origin is typing.Literal:
        return st.sampled_from(args)
    if origin is Union:
        inner = [_annotation_strategy(st, a) for a in args]
        if any(s is None for s in inner):
            return None
        return st.one_of(*inner)
    if origin in (list, List, Sequence) and args:
        item = _annotation_strategy(st, args[0])
        return None if item is None else st.lists(item, max_size=5)
    if isinstance(ann, type) and isinstance(
        getattr(ann, "model_fields", None), dict
    ):
        return _fields_strategy(st, ann, skip=())  # nested model -> dict
    table = {
        decimal.Decimal: st.decimals(
            -(10**6), 10**6, places=2, allow_nan=False, allow_infinity=False
        ),
        datetime.datetime: st.datetimes(),
        datetime.date: st.dates(),
        type(None): st.none(),
        bool: st.booleans(),
        int: st.integers(-1000, 1000),
        float: st.floats(-1e6, 1e6, allow_nan=False, allow_infinity=False),
        str: st.text(max_size=20),
    }
    return table.get(ann)


def payload_strategy(schema: Any) -> Any:
    """A Hypothesis strategy of payload dicts inferred from a pydantic model
    (an `EventModel`, or a validator built by `events_union`).

    Type mapping: ``bool``, ``int``, ``float``, ``str``, ``None``,
    ``Decimal``, ``datetime``, ``date``, nested pydantic models (as dicts),
    ``Literal[...]``, ``Optional`` / ``Union`` of those and ``List[...]``.
    Draws are filtered through the model's own validation, so field
    constraints (``Field(ge=1)``, validators) are honoured.

    Raises:
        ValueError: A required field whose type is outside that mapping --
            pass ``payloads={EVENT: strategy}`` for it instead.
    """
    hyp = _hypothesis()
    st = hyp.strategies
    model = getattr(schema, "__xsm_event_model__", schema)
    if not isinstance(getattr(model, "model_fields", None), dict):
        return st.just({})
    strategy = _fields_strategy(st, model, skip=("type",))
    validate = getattr(model, "model_validate", None)
    if validate is None:
        return strategy
    event_type = getattr(model.model_fields.get("type"), "default", None)

    def _valid(payload: Dict[str, Any]) -> bool:
        # 📝 Battle #271: constraints (``Field(ge=1)``, ``min_length``,
        #    validators) are not in the annotation -- an unfiltered draw
        #    made every send raise `InvalidEventPayloadError`.
        data = dict(payload)
        if isinstance(event_type, str):
            data["type"] = event_type
        try:
            validate(data)
        except Exception:  # noqa: BLE001 -- pydantic ValidationError
            return False
        return True

    return strategy.filter(_valid)


def _fields_strategy(st: Any, model: Any, skip: Sequence[str]) -> Any:
    required: Dict[str, Any] = {}
    optional: Dict[str, Any] = {}
    for name, info in model.model_fields.items():
        if name in skip:
            continue
        strat = _annotation_strategy(st, info.annotation)
        if strat is None:
            if info.is_required():
                raise ValueError(
                    f"model_test: cannot infer a strategy for "
                    f"{getattr(model, '__name__', model)}.{name}: "
                    f"{info.annotation!r}; pass payloads={{...: strategy}}"
                )
            continue
        (required if info.is_required() else optional)[name] = strat
    return st.fixed_dictionaries(required, optional=optional)


def _payload_strategies(
    machine: MachineNode[Any], events: List[str], payloads: Mapping[str, Any]
) -> Dict[str, Any]:
    st = _hypothesis().strategies
    out: Dict[str, Any] = {}
    unknown = sorted(set(payloads) - set(events))
    if unknown:
        raise ValueError(
            f"model_test: payloads= names events the chart does not "
            f"declare: {unknown}"
        )
    for ev in events:
        if ev in payloads:
            out[ev] = payloads[ev]
        elif ev in machine.event_schemas:
            out[ev] = payload_strategy(machine.event_schemas[ev])
        else:
            out[ev] = st.just({})
    return out
