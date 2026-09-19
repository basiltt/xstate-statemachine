# /src/xstate_statemachine/machine_logic.py
# -----------------------------------------------------------------------------
# 🧠 Machine Logic Container
# -----------------------------------------------------------------------------
# This module defines the `MachineLogic` class, which serves as a centralized
# container or "registry" for all custom behaviors (actions, guards, and
# services) that a state machine can invoke.
#
# This class is fundamental to the "Separation of Concerns" principle that
# underpins the library. It allows developers to keep the declarative state
# machine definition (the JSON) separate from its imperative implementation
# details (the Python code). This makes both the logic and the state flow
# easier to manage, test, and reason about.
# -----------------------------------------------------------------------------
"""
Provides a data structure for holding a state machine's implementation logic.

This module contains the `MachineLogic` class, which is used to explicitly
bind the string names of actions, guards, and services from a machine's
configuration to their corresponding Python callable functions.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
from __future__ import (
    annotations,
)  # Enables postponed evaluation of type annotations

import inspect
import warnings
import logging
from typing import (
    Iterable,
    Mapping,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    TYPE_CHECKING,
    TypeVar,
    Union,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .events import Event

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# ⚙️ Type Hinting for Forward References
# -----------------------------------------------------------------------------
# This block is used for type hinting to prevent circular import errors at
# runtime, which can occur when two modules depend on each other. The type
# hints are only evaluated by static type checkers.
if TYPE_CHECKING:
    from .models import ActionDefinition, MachineNode  # noqa: F401

# -----------------------------------------------------------------------------
# 🧬 Type Variables & Callable Signatures
# -----------------------------------------------------------------------------
# These generic TypeVars and specific Callable type aliases are used to
# document the ideal function signatures for actions, guards, and services.
# They provide strong typing support for developers implementing machine logic.
# -----------------------------------------------------------------------------

from ._typing import TContext  # noqa: E402

# 🧷 Callable blueprints for user logic.
#
# 🏛️ Architecture decision: these pin the ARITY and the guard's `bool`
#    return -- the two mistakes users actually make -- and leave every
#    parameter as `Any`. Two reasons, both about contravariance:
#      * A user who annotates `interp: SyncInterpreter[MyCtx]` on their
#        action is doing the right thing; naming `BaseInterpreter` here
#        would REJECT that narrower annotation.
#      * A `TContext` in the context slot cannot be inferred from a dict of
#        callables (mypy solves it to `Never`), so it would reject every
#        correctly-typed action. The context type is bound where a user
#        READS it -- `create_machine(context_type=)` -> `interp.context` --
#        not where they write handlers for it.
#    What `Callable[..., Any]` (the previous hint) let through: a
#    two-argument action, a guard returning a string.
ActionCallable = Callable[
    [Any, Any, Any, "ActionDefinition"], Union[None, Awaitable[None]]
]

# A guard is a pure, synchronous predicate: (context, event) -> bool.
GuardCallable = Callable[[Any, Any], bool]

# A service: (interpreter, context, event) -> result | awaitable result.
ServiceCallable = Callable[[Any, Any, Any], Any]

# A `delays` entry: a number of milliseconds, or (context, event) -> ms.
DelayCallable = Callable[[Any, Any], Union[int, float]]


# -----------------------------------------------------------------------------
# 🔤 Name normalisation
# -----------------------------------------------------------------------------


def normalize_logic_name(name: str) -> str:
    """Return the case- and separator-insensitive key for a logic name.

    🏛️ Architecture decision: the library promises that a Python function
    written in PEP 8 ``snake_case`` implements the ``camelCase`` name an
    XState JSON config uses. Two spellings of the same word must therefore
    resolve to ONE key, and the simplest total function with that property
    is "drop every separator, fold case":

        ``logHTTPStatus`` / ``log_http_status`` / ``logHttpStatus``
        -> ``loghttpstatus``

    A forward conversion (``snake -> camel``) cannot do this: acronyms are
    lossy (``log_http_status`` becomes ``logHttpStatus``, which is not the
    ``logHTTPStatus`` the config says) and non-identifier names such as
    ``fetch-data`` or Stately's ``inline:machine.state#entry[0]`` have no
    snake form at all. Normalising BOTH sides instead makes every one of
    those match, and it is what the CLI's ``camel_to_snake`` output rounds
    back to.

    Separators: ``_``, ``-``, ``.``, ``:``, ``#``, ``[``, ``]``, ``/`` and
    whitespace. Everything else (letters, digits, other Unicode) is kept.
    """
    return "".join(ch for ch in name if ch not in _NAME_SEPARATORS).casefold()


_NAME_SEPARATORS = frozenset("_-.:#[]/ \t\n")


def resolve_aliases(
    registry: Dict[str, Any], required: "Iterable[str]"
) -> None:
    """Bind every *required* config name that has a normalised match.

    For each name the machine references but *registry* lacks, look for a
    registered key with the same :func:`normalize_logic_name` and alias it
    in place. Exact keys are never touched, so an explicit
    ``{"logHTTPStatus": fn}`` always wins over a discovered ``log_http_status``.

    Called once when a machine is assembled (``create_machine``), so the
    runtime lookup remains a plain ``dict.get`` on the hot path.

    Raises:
        InvalidConfigError: when two *different* registered callables
            normalise to the same key a required name needs — e.g. both
            ``fetch_data`` and ``fetchData`` are registered — because
            picking one silently would hide a real defect.
    """
    if not registry:
        return
    by_key: Dict[str, "list[str]"] = {}
    for key in registry:
        by_key.setdefault(normalize_logic_name(key), []).append(key)
    for name in required:
        if name in registry:
            # ⚠️ #91: exact key wins BY DESIGN -- but if a DIFFERENT callable
            #    is also registered under a spelling that normalises to this
            #    name, the author almost certainly has two implementations
            #    and does not know which one runs. Say so; silently
            #    preferring one is the exact failure the guard exists for.
            shadows = [
                c
                for c in by_key.get(normalize_logic_name(name), [])
                if c != name and registry[c] is not registry[name]
            ]
            if shadows:
                warnings.warn(
                    f"Logic name '{name}' is registered exactly and also as "
                    f"{sorted(shadows)}, which differ only by case or "
                    f"separators but are DIFFERENT callables. The exact key "
                    f"'{name}' is used; remove the others or make them the "
                    f"same object.",
                    UserWarning,
                    stacklevel=3,
                )
            continue
        candidates = by_key.get(normalize_logic_name(name))
        if not candidates:
            continue
        distinct = {id(registry[c]) for c in candidates}
        if len(distinct) > 1:
            from .exceptions import InvalidConfigError

            raise InvalidConfigError(
                f"Logic name '{name}' is ambiguous: "
                f"{sorted(candidates)} are all registered and differ only "
                "by case or separators. Keep one, or register the exact "
                f"name '{name}' explicitly."
            )
        registry[name] = registry[candidates[0]]
        logger.debug(
            "🔤 Aliased logic name '%s' -> '%s'.", name, candidates[0]
        )


# -----------------------------------------------------------------------------
# 🧠 MachineLogic Class Definition
# -----------------------------------------------------------------------------


# 📢 #52: arities whose contract is not unique. Used by
#    `_register_by_arity` to phrase the ambiguity warning.
_AMBIGUOUS_ARITY_ROLES: Dict[int, str] = {
    2: "guard (or a 2-arg service)",
    3: "service (or a 3-arg action)",
}


class MachineLogic(Generic[TContext]):
    """A container for the implementation logic of a state machine.

    This class serves as a simple registry for custom actions, guards, and
    services. An instance of this class is passed to `create_machine` when
    using the "explicit binding" pattern. It cleanly separates the "what"
    (the machine's JSON definition) from the "how" (the Python code that
    executes the defined behaviors).

    Attributes:
        actions: A dictionary mapping action names to their callable
                 implementations.
        guards: A dictionary mapping guard names to their boolean-returning
                callable implementations.
        services: A dictionary mapping service names to their callable
                  implementations or the `MachineNode`s they spawn.
    """

    def __init__(
        self,
        actions: Optional[Mapping[str, ActionCallable]] = None,
        guards: Optional[Mapping[str, GuardCallable]] = None,
        services: Optional[
            Mapping[str, Union[ServiceCallable, "MachineNode[Any]"]]
        ] = None,
        delays: Optional[
            Mapping[str, Union[int, float, DelayCallable]]
        ] = None,
        *,
        strict: bool = False,
    ) -> None:
        """Initializes the MachineLogic instance.

        This constructor accepts dictionaries of callables typed by the
        aliases above: they pin each callable's ARITY and a guard's `bool`
        return, while leaving the interpreter and event parameters open so
        a user may annotate them as narrowly as they like
        (`SyncInterpreter[MyCtx]`, a `TypedDict` event, ...). A service may
        also be a `MachineNode`, which is the pattern used for spawning
        actors.

        Args:
            actions: A dictionary mapping action names (str) to their
                Python function implementations. Defaults to an empty dict.
            guards: A dictionary mapping guard names (str) to their
                Python function implementations. Defaults to an empty dict.
            services: A dictionary mapping service names (str) to their
                Python function or `MachineNode` implementations. Defaults
                to an empty dict.
            delays: A dictionary mapping named delays (str) to a duration in
                milliseconds, or a callable of `(context, event)` returning
                one. This is what lets `after: {"TIMEOUT": ...}` and
                `send_to(..., delay="TIMEOUT")` resolve a symbolic delay
                instead of raising.
            strict: (#52) When ``True``, a subclass method that is NOT
                decorated with `@action` / `@guard` / `@service` raises
                `InvalidConfigError` at construction instead of being
                filed by arity with a `UserWarning`. Use this to make a
                misclassified method a build-time error rather than a
                warning that can be missed in a long-lived process.
        """
        logger.info("🧠 Initializing MachineLogic container...")
        self.strict: bool = bool(strict)

        # ✅ Use `or {}` as a robust way to default to an empty dictionary
        #    if None is passed.
        # 🧷 Accept any Mapping (a `Dict[str, ServiceCallable]` is not a
        #    `Dict[str, ServiceCallable | MachineNode]` -- dict is invariant
        #    in its value type -- but every Mapping of callables IS one);
        #    store a real dict the interpreter can mutate.
        self.actions: Dict[str, ActionCallable] = dict(actions or {})
        self.guards: Dict[str, GuardCallable] = dict(guards or {})
        self.services: Dict[
            str, Union[ServiceCallable, "MachineNode[Any]"]
        ] = dict(services or {})
        self.delays: Dict[str, Union[int, float, DelayCallable]] = dict(
            delays or {}
        )

        # 🧬 Subclass auto-registration.
        #
        # 🏛️ Architecture decision: the "subclass and define methods" pattern
        #    is documented throughout the guides, but nothing ever collected
        #    those methods, so every such example died with
        #    `ImplementationMissingError`. Registering them here — rather than
        #    teaching each interpreter to fall back to `getattr(logic, name)`
        #    — keeps the resolution path single-sourced: after `__init__`,
        #    `logic.actions` / `.guards` / `.services` are still the ONLY
        #    truth, no matter which authoring style produced them.
        self._register_subclass_methods()

        if logger.isEnabledFor(logging.INFO):  # ⚡ constructed per build
            logger.info(
                "✅ MachineLogic initialized with %d actions, %d guards, "
                "and %d services.",
                len(self.actions),
                len(self.guards),
                len(self.services),
            )

    # -------------------------------------------------------------------------
    # 🧬 Subclass Method Discovery
    # -------------------------------------------------------------------------
    def _register_subclass_methods(self) -> None:
        """Registers methods defined on a `MachineLogic` subclass.

        The guides document an alternative authoring style in which logic is
        written as methods on a subclass rather than passed as dictionaries::

            class AgeLogic(MachineLogic):
                def isAdult(self, context, event):
                    return context.get("age", 0) >= 18

        Those methods are classified by their *arity*, which is unambiguous
        because the three callable contracts have distinct signatures:

        =======  ==========================================  ============
        Params   Signature                                   Registered as
        =======  ==========================================  ============
        2        ``(context, event)``                        guard
        3        ``(interpreter, context, event)``           service
        4        ``(interpreter, context, event, action)``   action
        =======  ==========================================  ============

        ⚠️ Explicitly supplied dictionaries always win. A subclass method is
        only registered when its name is not already bound, so the two styles
        can be mixed and the explicit form remains an escape hatch for any
        method whose arity would otherwise be misread.

        Methods with a leading underscore are treated as private helpers and
        are never registered.
        """
        # 🛑 A plain `MachineLogic()` has nothing to discover; skip the walk.
        if type(self) is MachineLogic:
            return

        for name, member in inspect.getmembers(
            type(self), predicate=inspect.isfunction
        ):
            # 🚫 Skip dunders, private helpers, and our own machinery.
            if name.startswith("_"):
                continue
            bound = getattr(self, name)

            # 🏷️ #52: an EXPLICIT role marker (set by the `@action`,
            #    `@guard`, `@service` decorators) wins outright. Before
            #    0.8.0 the decorator was silently ignored here and arity
            #    decided -- so a decorated 3-arg action became a service.
            explicit = getattr(member, "_xsm_type", None)
            if explicit is not None:
                self._register_by_marker(name, bound, explicit)
            elif self.strict:
                # 🛑 #52: `strict=True` refuses to guess. An undecorated
                #    public method is a build-time error, not a warning.
                from .exceptions import InvalidConfigError

                raise InvalidConfigError(
                    f"MachineLogic subclass '{type(self).__name__}' is "
                    f"strict, but method '{name}' carries no @action / "
                    f"@guard / @service decorator. Decorate it to state "
                    f"its role, prefix it with '_' to mark it as a helper, "
                    f"or construct with strict=False to fall back to "
                    f"arity-based classification."
                )
            else:
                self._register_by_arity(name, bound)

    def _register_by_marker(self, name: str, bound: Any, role: str) -> None:
        """Register *bound* under the role its decorator declared.

        Registration stays keyed by the Python method name: that is what a
        MachineLogic config references. (`pythonic` re-keys to `_xsm_name`;
        the two are deliberately distinct so the camelCase mapping of #17
        does not regress.) An explicitly supplied dictionary entry is never
        clobbered.
        """
        by_role: Dict[str, Dict[str, Any]] = {
            "action": self.actions,
            "guard": self.guards,
            "service": self.services,
        }
        registry = by_role.get(role)
        if registry is None:
            warnings.warn(
                f"MachineLogic subclass method '{name}' carries an "
                f"unknown role marker {role!r}; skipped.",
                UserWarning,
                stacklevel=4,
            )
            return
        if name not in registry:
            registry[name] = bound
            logger.debug("🧬 Registered '%s' as %s (explicit).", name, role)

    def _register_by_arity(self, name: str, bound: Any) -> None:
        """Register *bound* by parameter count, warning where that is lossy.

        🏛️ Architecture decision (#52): arity is kept as the fallback for
        backwards compatibility, but arities 2 and 3 are AMBIGUOUS -- a
        2-arg method is a guard OR the loose ``(context, event)`` service
        form seen in the guides; a 3-arg one is a service OR an action whose
        author dropped the unused 4th param. We register by the arity table
        (unchanged behaviour) but say so, so a misfiled method is visible at
        construction time. An arity matching no contract used to be a
        silent debug line; it is now a `UserWarning`.
        """
        # 🗺️ Arity → the registry that contract belongs to.
        registries: Dict[int, Dict[str, Any]] = {
            2: self.guards,
            3: self.services,
            4: self.actions,
        }
        try:
            arity = len(inspect.signature(bound).parameters)
        except (TypeError, ValueError):  # pragma: no cover
            # 🤷 Un-introspectable callables cannot be classified.
            return

        registry = registries.get(arity)
        if registry is None:
            warnings.warn(
                f"MachineLogic subclass method '{name}' has arity "
                f"{arity}, which matches no logic contract (guard=2, "
                f"service=3, action=4); it was NOT registered. Decorate "
                f"it with @action / @guard / @service to state the role.",
                UserWarning,
                stacklevel=4,
            )
            return

        # ✅ Never clobber an explicitly provided implementation.
        if name in registry:
            return

        registry[name] = bound
        if arity in _AMBIGUOUS_ARITY_ROLES:
            role = _AMBIGUOUS_ARITY_ROLES[arity]
            warnings.warn(
                f"MachineLogic subclass method '{name}' was registered "
                f"as a {role.split(' ')[0]} by arity ({arity}), but that "
                f"arity is ambiguous: {role}. Decorate it with @action / "
                f"@guard / @service to state the role explicitly.",
                UserWarning,
                stacklevel=4,
            )
        logger.debug(
            "🧬 Auto-registered subclass method '%s' by arity %d.",
            name,
            arity,
        )
