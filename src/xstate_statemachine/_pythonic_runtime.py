# src/xstate_statemachine/_pythonic_runtime.py
"""
🐍 Runtime support for the Pythonic DSL.

Two pieces that the class-based ``StateMachine`` needs at run time and
that are independent of how the chart is *compiled*:

1. **Signature-based argument injection** (`adapt_callable`). A callback
   declares only the parameters it wants -- ``context``, ``event``, a
   payload field such as ``amount`` -- and receives exactly those. The
   legacy positional shapes (``(interpreter, context, event, action_def)``
   for actions, ``(context, event[, params])`` for guards, ``(interpreter,
   context, event)`` for services) keep working: a callback whose arity
   matches one of them is called positionally, a default in the trailing
   ``params`` / ``action_def`` slot included, and is resolved by name only
   when it asks for injection (a default elsewhere, a keyword-only
   parameter, ``**kwargs``, or a parameter named like a field the event
   carries) and every parameter without a default can be supplied.

2. **Convention hooks that cannot be compiled into the chart**
   (`ConventionHooksPlugin`). ``before_<event>`` / ``before_transition``
   run before the exit actions and ``after_<event>`` / ``after_transition``
   after the entry actions. XState has no such slots, so they are driven
   from the plugin hooks of the interpreter the façade owns.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import inspect
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .events import ErrorEvent
from .plugins import PluginBase

#: Positional arities of the legacy callback shapes, per kind. Guards may
#: take an optional third ``params`` argument (parameterised guards).
LEGACY_ARITIES: Dict[str, Tuple[int, ...]] = {
    "action": (4,),
    "guard": (2, 3),
    "service": (3,),
}

#: Engine-provided names a callback may ask for. ``_HARD`` names are never
#: shadowed by an event payload field of the same name (a payload key
#: called ``context`` must not replace the context); ``_SOFT`` names yield
#: to a payload field when the event carries one.
_HARD_NAMES = frozenset(
    {
        "interpreter",
        "interp",
        "machine",
        "context",
        "ctx",
        "event",
        "event_type",
        "action_def",
        "action",
        "params",
    }
)
_SOFT_NAMES = frozenset(
    {"error", "data", "input", "source", "target", "state"}
)
INJECTABLE_NAMES = _HARD_NAMES | _SOFT_NAMES

#: The parameter name at each legacy position, used to tell "legacy by
#: arity" from "injection by name" when the counts coincide.
_LEGACY_ORDER: Dict[str, Tuple[Tuple[str, ...], ...]] = {
    "action": (
        ("interpreter", "interp", "machine"),
        ("context", "ctx"),
        ("event",),
        ("action_def", "action"),
    ),
    "guard": (("context", "ctx"), ("event",), ("params",)),
    "service": (
        ("interpreter", "interp", "machine"),
        ("context", "ctx"),
        ("event",),
    ),
}

#: The last slot of a legacy shape that callers conventionally leave out
#: when they call the callback by hand (a test calling ``my_action(i, ctx,
#: e)`` or ``my_guard(ctx, e)``): an action's ``action_def``, a guard's
#: ``params`` and a service's ``event``. A default there (``a=None``,
#: ``params=None``) is that idiom, not a request for injection.
_TRAILING_OPTIONAL_SLOT: Dict[str, int] = {
    "action": 3,
    "guard": 2,
    "service": 2,
}

_MISSING = object()


# -------------------------------------------------------------------------
# 🔎 Signature analysis
# -------------------------------------------------------------------------


class _Shape:
    """What a callback's signature tells us, computed once.

    Attributes:
        legacy: The positional arity matches a legacy shape (or the
            callback takes ``*args``).
        ambiguous: Legacy arity, but the parameter names do not settle it;
            `adapt_callable` decides per call.
        prefers_injection: The author wrote something the positional call
            cannot honour on its own -- a default outside the trailing
            slot, a keyword-only parameter or ``**kwargs`` -- so by-name
            resolution is tried first.
        defaults: Per positional parameter, whether it has a default.
        engine_named: At least one positional parameter is an engine name
            (for an ambiguous shape, at its legacy position).
        unknown: Positional parameter names that are not engine names.
        unknown_required: The subset of ``unknown`` without a default.
    """

    __slots__ = (
        "params",
        "legacy",
        "ambiguous",
        "var_kw",
        "names",
        "prefers_injection",
        "defaults",
        "engine_named",
        "unknown",
        "unknown_required",
    )

    def __init__(self, fn: Callable[..., Any], kind: str) -> None:
        self.prefers_injection = False
        self.defaults: Tuple[bool, ...] = ()
        self.engine_named = False
        self.unknown: Tuple[str, ...] = ()
        self.unknown_required: Tuple[str, ...] = ()
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):  # pragma: no cover - builtins
            self.params: List[inspect.Parameter] = []
            self.legacy, self.ambiguous, self.var_kw = True, False, False
            self.names: Tuple[str, ...] = ()
            return
        self.params = list(sig.parameters.values())
        kinds = [p.kind for p in self.params]
        self.var_kw = inspect.Parameter.VAR_KEYWORD in kinds
        positional = [
            p
            for p in self.params
            if p.kind
            in (
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            )
        ]
        self.names = tuple(p.name for p in positional)
        self.defaults = tuple(
            p.default is not inspect.Parameter.empty for p in positional
        )
        if inspect.Parameter.VAR_POSITIONAL in kinds:
            # ``*args`` wants the raw positional call.
            self.legacy, self.ambiguous = True, False
            return
        has_kw_only = inspect.Parameter.KEYWORD_ONLY in kinds
        trailing = _TRAILING_OPTIONAL_SLOT[kind]
        default_elsewhere = any(
            p.default is not inspect.Parameter.empty and pos != trailing
            for pos, p in enumerate(positional)
        )
        self.prefers_injection = (
            default_elsewhere or has_kw_only or self.var_kw
        )
        self.unknown = tuple(
            p.name for p in positional if p.name not in INJECTABLE_NAMES
        )
        self.unknown_required = tuple(
            p.name
            for p in positional
            if p.name not in INJECTABLE_NAMES
            and p.default is inspect.Parameter.empty
        )
        self.engine_named = len(self.unknown) < len(self.names)
        required = sum(
            1 for p in positional if p.default is inspect.Parameter.empty
        )
        arities = LEGACY_ARITIES[kind]
        # A legacy shape followed by extra defaulted parameters
        # (``(i, ctx, e, a, level="info")``) is that shape: the positional
        # call leaves the extras at their defaults, as 0.11 did.
        if len(positional) not in arities and not (
            required in arities and required < len(positional)
        ):
            self.legacy, self.ambiguous = False, False
            return
        # Arity matches. A recognised engine name at the wrong position
        # means the author is naming things -> injection. Names that all
        # sit at their legacy position, or are unrecognised (``i, ctx, e,
        # a``), are legacy -- unless, per call, the author asked for
        # injection (a default outside the trailing slot, a keyword-only
        # parameter, ``**kwargs``, or a payload field named like a
        # parameter) AND every parameter without a default can be supplied
        # by name. ``(ctx, e, params=None)`` and ``(i, ctx, e, a=None)``
        # therefore stay positional; ``(context, amount=0)`` is injected.
        order = _LEGACY_ORDER[kind]
        for pos, name in enumerate(self.names):
            if name in INJECTABLE_NAMES and (
                pos >= len(order) or name not in order[pos]
            ):
                self.legacy, self.ambiguous = False, False
                return
        self.legacy, self.ambiguous = True, True


def is_legacy_signature(fn: Callable[..., Any], kind: str) -> bool:
    """``True`` when *fn* is called with the positional engine shape.

    Ambiguous shapes (legacy arity, unrecognised names, with or without
    defaults) count as legacy here; `adapt_callable` re-checks them
    against each event's payload and only switches to by-name resolution
    when every parameter can be satisfied.
    """
    return _Shape(fn, kind).legacy


# -------------------------------------------------------------------------
# 💉 Argument resolution
# -------------------------------------------------------------------------


def _engine_value(
    name: str,
    *,
    kind: str,
    interpreter: Any,
    context: Any,
    event: Any,
    action_def: Any,
    params: Any,
) -> Any:
    """Resolve an engine-provided parameter name, or ``_MISSING``."""
    if name in ("interpreter", "interp", "machine"):
        return interpreter if interpreter is not None else _MISSING
    if name in ("context", "ctx"):
        return context
    if name == "event":
        return event
    if name == "event_type":
        return getattr(event, "type", None)
    if name in ("action_def", "action"):
        return action_def if kind == "action" else _MISSING
    if name == "params":
        if kind == "guard":
            return params
        return getattr(action_def, "params", None)
    if name == "error":
        return getattr(event, "error", None)
    if name == "data":
        # 📝 `ErrorEvent.data` is a deprecated alias of `.error`; ask for
        #    `error` on an error event, `data` means a done-event result.
        if isinstance(event, ErrorEvent):
            return None
        return getattr(event, "data", None)
    if name == "input":
        payload = getattr(event, "payload", None) or {}
        return payload.get("input") if isinstance(payload, dict) else None
    return _MISSING


def _payload_of(event: Any, kind: str) -> Dict[str, Any]:
    payload = getattr(event, "payload", None)
    payload = dict(payload) if isinstance(payload, dict) else {}
    # 📝 `input` on an invoke event is the natural injection source for a
    #    service: with `"input": event_payload` declared, `send("START",
    #    url=...)` arrives as the service's input.
    if kind == "service" and isinstance(payload.get("input"), dict):
        payload = {**payload["input"], **payload}
    return payload


def _supplied_names(
    event: Any,
    kind: str,
    action_def: Any,
    extra: Optional[Mapping[str, Any]],
) -> "set[str]":
    """The names a by-name call could take from outside the engine."""
    payload = getattr(event, "payload", None)
    names = set(payload) if isinstance(payload, dict) else set()
    if kind == "service" and isinstance(payload, dict):
        nested = payload.get("input")
        if isinstance(nested, dict):
            names.update(nested)
    chart = getattr(action_def, "params", None)
    if isinstance(chart, Mapping):
        names.update(chart)
    if extra:
        names.update(extra)
    return names


def _display_name(fn: Callable[..., Any]) -> str:
    inner = getattr(fn, "func", fn)
    return str(getattr(inner, "__qualname__", getattr(inner, "__name__", fn)))


def resolve_arguments(
    fn: Callable[..., Any],
    kind: str,
    *,
    interpreter: Any,
    context: Any,
    event: Any,
    action_def: Any = None,
    params: Any = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Tuple[List[Any], Dict[str, Any]]:
    """Build the call arguments for an injection-style callback.

    Precedence per parameter name: chart-provided values (``extra`` and
    ``action_def.params``) first, then hard engine names, then the event
    payload, then soft engine names, then the parameter's default.

    Raises:
        TypeError: A required parameter cannot be satisfied.
    """
    sig = inspect.signature(fn)
    payload = _payload_of(event, kind)
    chart: Dict[str, Any] = dict(getattr(action_def, "params", None) or {})
    if extra:
        chart.update(extra)

    args: List[Any] = []
    kwargs: Dict[str, Any] = {}
    consumed = set()
    var_kw = False
    for p in sig.parameters.values():
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            var_kw = True
            continue
        if p.kind is inspect.Parameter.VAR_POSITIONAL:
            continue
        name = p.name
        engine_kwargs = dict(
            kind=kind,
            interpreter=interpreter,
            context=context,
            event=event,
            action_def=action_def,
            params=params,
        )
        if name in chart:
            value = chart[name]
        elif name in _HARD_NAMES:
            value = _engine_value(name, **engine_kwargs)
        elif name in payload:
            value = payload[name]
            consumed.add(name)
        else:
            value = _engine_value(name, **engine_kwargs)
        if value is _MISSING:
            if p.default is not inspect.Parameter.empty:
                value = p.default
            else:
                raise TypeError(
                    f"{_display_name(fn)}() needs argument '{name}', but "
                    f"event '{getattr(event, 'type', '?')}' carries no "
                    f"such field and it is not an injectable name "
                    f"({', '.join(sorted(INJECTABLE_NAMES))})."
                )
        if p.kind is inspect.Parameter.KEYWORD_ONLY:
            kwargs[name] = value
        else:
            args.append(value)
    if var_kw:
        bound = {p.name for p in sig.parameters.values()}
        for key, value in payload.items():
            if key not in consumed and key not in bound and key != "input":
                kwargs[key] = value
    return args, kwargs


def _split(kind: str, call_args: Tuple[Any, ...]) -> Dict[str, Any]:
    """Name the positional arguments the engine passed."""
    if kind == "action":
        interpreter, context, event, action_def = call_args
        params = None
    elif kind == "guard":
        context, event = call_args[0], call_args[1]
        params = call_args[2] if len(call_args) > 2 else None
        interpreter, action_def = None, None
    else:
        interpreter, context, event = call_args
        action_def, params = None, None
    return dict(
        interpreter=interpreter,
        context=context,
        event=event,
        action_def=action_def,
        params=params,
    )


def adapt_callable(
    fn: Callable[..., Any],
    kind: str,
    *,
    sink: Optional[Any] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Callable[..., Any]:
    """Wrap *fn* so the engine can call it with the legacy positional shape.

    Unambiguously legacy callables are returned untouched (unless *sink*
    asks for their return values). Everything else is wrapped. A callback
    whose arity does not match a legacy shape has its arguments resolved
    by name on every call. A callback with legacy arity is called
    positionally unless the author asked for injection (a default outside
    the trailing ``params`` / ``action_def`` slot, a keyword-only
    parameter, ``**kwargs``, or a parameter named like a field of the
    current event's payload) AND every parameter without a default can be
    supplied by name for this call: ``(i, ctx, e, a=None)`` and ``(ctx, e,
    params=None)`` stay positional, ``(context, amount=0)`` and
    ``(context, amount)`` with an ``amount`` in the payload are injected.
    A legacy shape followed by extra defaulted parameters (``(i, ctx, e,
    a, level="info")``) counts as that shape. When a callback with no
    engine name asks for injection and the payload names some of its
    parameters but not a required one (``(url, retries=3, timeout=10)``
    sent ``retries=5`` and no ``url``), the missing one raises
    ``TypeError`` instead of falling back to the positional call; a plain
    ``(i, c, e, a)`` sent ``e=1`` stays positional. An engine name in
    another slot than its own (``params`` as an action's fourth parameter)
    always means by-name resolution, and a chart ``params`` key or *extra*
    counts as a supplied field like a payload key. The ambiguity that
    remains: a legacy callback whose non-engine parameters without a default are all named like
    fields the event carries (``(ctx, e)`` with ``send("GO", e=1)``) is
    resolved by name, and a default on its event parameter (``(ctx,
    e=None)``) asks for injection, so ``e`` is ``None`` when the event
    carries no such field.

    Args:
        fn: The (already ``self``-bound) callback.
        kind: ``"action"``, ``"guard"`` or ``"service"``.
        sink: Optional ``append``-able collecting non-``None`` action
            results, so the façade can hand them back from ``send()``.
        extra: Fixed injectables (for example ``state`` for a generic
            ``on_enter_state`` hook).
    """
    shape = _Shape(fn, kind)
    inner = getattr(fn, "func", fn)
    is_async = inspect.iscoroutinefunction(inner)

    if shape.legacy and not shape.ambiguous and sink is None:
        return fn

    def _record(result: Any) -> Any:
        if sink is not None and kind == "action" and result is not None:
            sink.append(result)
        return result

    def _by_name_plan(
        call_args: Tuple[Any, ...],
    ) -> Optional[Tuple[List[Any], Dict[str, Any]]]:
        """The by-name call arguments, or ``None`` for a positional call."""
        if shape.legacy and not shape.ambiguous:
            return None
        if not shape.legacy:
            return resolve_arguments(
                fn, kind, extra=extra, **_split(kind, call_args)
            )
        if not shape.prefers_injection and not shape.unknown:
            # Engine names only, each at its legacy position: the by-name
            # call would hand over the same objects.
            return None
        # 🏛️ Legacy arity. By name only when the author asked for it AND
        #    every parameter without a default can be supplied; a legacy
        #    callback whose ``e`` happens to match a payload key, or whose
        #    ``a=None`` is just a default, keeps receiving the engine's
        #    objects. When a shape with no engine name asked for injection
        #    and the payload names some of its parameters but not a
        #    required one, the author meant injection and the missing
        #    field is an error, not a cue to fall back; a plain ``(i, c, e,
        #    a)`` sent ``e=1`` is resolved positionally.
        event = call_args[1] if kind == "guard" else call_args[2]
        action_def = call_args[3] if kind == "action" else None
        supplied = _supplied_names(event, kind, action_def, extra)
        targeted = any(name in supplied for name in shape.unknown)
        if not (targeted or shape.prefers_injection):
            return None
        parts = _split(kind, call_args)
        if any(name not in supplied for name in shape.unknown_required):
            if targeted and shape.prefers_injection and not shape.engine_named:
                return resolve_arguments(fn, kind, extra=extra, **parts)
            return None
        try:
            return resolve_arguments(fn, kind, extra=extra, **parts)
        except TypeError:
            return None

    def _legacy_call_args(call_args: Tuple[Any, ...]) -> Tuple[Any, ...]:
        if kind != "guard":
            return call_args
        # A two-argument legacy guard must not receive `params`; a
        # three-argument one gets it (`None` when the transition declares
        # none) instead of a TypeError -- unless its third parameter has a
        # default, which then applies.
        if len(shape.names) == 2:
            return call_args[:2]
        if len(shape.names) >= 3 and len(call_args) == 2:
            if shape.defaults and shape.defaults[2]:
                return call_args
            return call_args + (None,)
        return call_args

    if is_async:

        async def async_wrapper(*call_args: Any) -> Any:
            plan = _by_name_plan(call_args)
            if plan is None:
                return _record(await fn(*_legacy_call_args(call_args)))
            args, kwargs = plan
            return _record(await fn(*args, **kwargs))

        _copy_metadata(async_wrapper, fn)
        return async_wrapper

    def wrapper(*call_args: Any) -> Any:
        plan = _by_name_plan(call_args)
        if plan is None:
            return _record(fn(*_legacy_call_args(call_args)))
        args, kwargs = plan
        return _record(fn(*args, **kwargs))

    _copy_metadata(wrapper, fn)
    return wrapper


def _copy_metadata(
    wrapper: Callable[..., Any], fn: Callable[..., Any]
) -> None:
    inner = getattr(fn, "func", fn)
    for attr in ("__name__", "__qualname__", "__doc__", "__module__"):
        value = getattr(inner, attr, None)
        if value is not None:
            try:
                setattr(wrapper, attr, value)
            except (AttributeError, TypeError):  # pragma: no cover
                pass
    # 📝 Point at the underlying function, not the `partial`: the engines'
    #    async detection follows `__wrapped__`, and it must land on a plain
    #    `def` / `async def` to classify the callback correctly.
    setattr(wrapper, "__wrapped__", inner)
    # 📝 `inspect.signature` would otherwise follow `__wrapped__` too and
    #    report the INNER signature; the engine reads it to decide whether
    #    a guard takes `params`. The wrapper accepts whatever is passed.
    setattr(
        wrapper,
        "__signature__",
        inspect.Signature(
            [inspect.Parameter("call_args", inspect.Parameter.VAR_POSITIONAL)]
        ),
    )


# -------------------------------------------------------------------------
# 🔌 before_* / after_* hooks
# -------------------------------------------------------------------------


class ConventionHooksPlugin(PluginBase[Any]):
    """Drive ``before_*`` / ``after_*`` naming-convention hooks.

    Hooks are plain (synchronous) callables already adapted with
    `adapt_callable`; ``async def`` hooks are rejected at class creation
    because plugin callbacks are not awaited.

    Args:
        before: Mapping of event type → callables to run before the event
            is processed (only when the event WILL cause a transition).
            The key ``"*"`` runs for every such event.
        after: Mapping of event type → callables to run after the
            transition completed. ``"*"`` runs for every transition.
    """

    def __init__(
        self,
        before: Mapping[str, List[Callable[..., Any]]],
        after: Mapping[str, List[Callable[..., Any]]],
    ) -> None:
        self._before = {k: list(v) for k, v in before.items()}
        self._after = {k: list(v) for k, v in after.items()}
        self._current_event: Any = None

    def on_event_received(self, interpreter: Any, event: Any) -> None:
        self._current_event = event
        hooks = self._before.get("*", []) + self._before.get(
            getattr(event, "type", ""), []
        )
        if not hooks or not interpreter.can(event):
            return
        for hook in hooks:
            hook(interpreter, interpreter.context, event, None)

    def on_transition(
        self,
        interpreter: Any,
        from_states: Any,
        to_states: Any,
        transition: Any,
    ) -> None:
        event = self._current_event
        if event is None:
            # 🚀 The initial entry at start() is not a user transition.
            return
        hooks = self._after.get("*", []) + self._after.get(
            getattr(event, "type", ""), []
        )
        for hook in hooks:
            hook(interpreter, interpreter.context, event, None)
