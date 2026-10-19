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
   matches and whose parameter names do not ask for anything by name is
   called positionally, exactly as before.

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

_MISSING = object()


# -------------------------------------------------------------------------
# 🔎 Signature analysis
# -------------------------------------------------------------------------


class _Shape:
    """What a callback's signature tells us, computed once."""

    __slots__ = ("params", "legacy", "ambiguous", "var_kw", "names")

    def __init__(self, fn: Callable[..., Any], kind: str) -> None:
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
        if inspect.Parameter.VAR_POSITIONAL in kinds:
            # ``*args`` wants the raw positional call.
            self.legacy, self.ambiguous = True, False
            return
        has_kw_only = inspect.Parameter.KEYWORD_ONLY in kinds
        has_defaults = any(
            p.default is not inspect.Parameter.empty for p in positional
        )
        arity_ok = len(positional) in LEGACY_ARITIES[kind]
        if not arity_ok or self.var_kw or has_kw_only or has_defaults:
            self.legacy, self.ambiguous = False, False
            return
        # Arity matches. A recognised engine name at the wrong position
        # means the author is naming things -> injection. Names that all
        # sit at their legacy position, or are unrecognised (``i, ctx, e,
        # a``), are legacy -- unless the event payload names one of them,
        # which is decided per call.
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

    Ambiguous shapes (legacy arity, unrecognised names) count as legacy
    here; `adapt_callable` re-checks them against each event's payload.
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
        return getattr(event, "data", None)
    if name == "input":
        payload = getattr(event, "payload", None) or {}
        return payload.get("input") if isinstance(payload, dict) else None
    return _MISSING


def _payload_of(event: Any, kind: str) -> Dict[str, Any]:
    payload = getattr(event, "payload", None)
    payload = dict(payload) if isinstance(payload, dict) else {}
    # 📝 `input` on an invoke event is the natural injection source for a
    #    service: `send("START", url=...)` arrives as the service's input.
    if kind == "service" and isinstance(payload.get("input"), dict):
        payload = {**payload["input"], **payload}
    return payload


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
    asks for their return values). Everything else is wrapped: arguments
    are resolved by name on every call, and a callback with legacy arity
    but a parameter named like a payload field of the current event is
    treated as injection-style for that call.

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

    def _legacy_for(call_args: Tuple[Any, ...]) -> bool:
        if not shape.legacy:
            return False
        if not shape.ambiguous:
            return True
        event = call_args[2] if kind != "guard" else call_args[1]
        payload = _payload_of(event, kind)
        return not any(name in payload for name in shape.names)

    def _legacy_call_args(call_args: Tuple[Any, ...]) -> Tuple[Any, ...]:
        if kind != "guard":
            return call_args
        # A two-argument legacy guard must not receive `params`; a
        # three-argument one always gets it (`None` when the transition
        # declares none) instead of a TypeError.
        if len(shape.names) == 2:
            return call_args[:2]
        if len(shape.names) == 3 and len(call_args) == 2:
            return call_args + (None,)
        return call_args

    if is_async:

        async def async_wrapper(*call_args: Any) -> Any:
            if _legacy_for(call_args):
                return _record(await fn(*_legacy_call_args(call_args)))
            parts = _split(kind, call_args)
            args, kwargs = resolve_arguments(fn, kind, extra=extra, **parts)
            return _record(await fn(*args, **kwargs))

        _copy_metadata(async_wrapper, fn)
        return async_wrapper

    def wrapper(*call_args: Any) -> Any:
        if _legacy_for(call_args):
            return _record(fn(*_legacy_call_args(call_args)))
        parts = _split(kind, call_args)
        args, kwargs = resolve_arguments(fn, kind, extra=extra, **parts)
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
