# /src/xstate_statemachine/factory.py
# -----------------------------------------------------------------------------
# 🏭 Machine Factory
# -----------------------------------------------------------------------------
# This module provides a single, convenient entry point for creating a state
# machine instance from its configuration and business logic. It applies the
# "Factory Method" design pattern to decouple the client from the complex
# process of assembling the machine's configuration (`config`) and its
# executable logic (`MachineLogic`).
#
# This simplifies the user experience, centralizes the machine creation
# process, and ensures consistency and validation, making the library more
# scalable and maintainable.
# -----------------------------------------------------------------------------
"""
Provides a centralized factory function for creating state machine instances.

The main export of this module is `create_machine`, which serves as the
primary user-facing function for instantiating a new state machine from a
configuration dictionary and associated business logic.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import copy
from types import ModuleType
from typing import Any, Dict, List, Optional, Type, Union, overload

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .exceptions import InvalidConfigError
from .logic_loader import LogicLoader
from .logger import logger
from .machine_logic import MachineLogic, resolve_aliases
from ._typing import TContext
from .models import MachineNode
from .validation import validate_machine

# -----------------------------------------------------------------------------
# 🏭 Factory Function
# -----------------------------------------------------------------------------


@overload
def create_machine(
    config: Dict[str, Any],
    *,
    logic: Optional[MachineLogic[Any]] = None,
    logic_modules: Optional[List[Union[str, ModuleType]]] = None,
    logic_providers: Optional[List[Any]] = None,
    strict_targets: bool = True,
    event_schemas: Optional[Dict[str, Any]] = None,
) -> MachineNode[Dict[str, Any]]:  # noqa: E704
    ...


@overload
def create_machine(
    config: Dict[str, Any],
    *,
    context_type: Type[TContext],
    logic: Optional[MachineLogic[TContext]] = None,
    logic_modules: Optional[List[Union[str, ModuleType]]] = None,
    logic_providers: Optional[List[Any]] = None,
    strict_targets: bool = True,
    event_schemas: Optional[Dict[str, Any]] = None,
) -> MachineNode[TContext]:  # noqa: E704
    ...


def create_machine(
    config: Dict[str, Any],
    *,
    context_type: Optional[Type[Any]] = None,
    logic: Optional[MachineLogic[Any]] = None,
    logic_modules: Optional[List[Union[str, ModuleType]]] = None,
    logic_providers: Optional[List[Any]] = None,
    strict_targets: bool = True,
    event_schemas: Optional[Dict[str, Any]] = None,
) -> MachineNode[Any]:
    """Creates, validates, and assembles a state machine instance.

    🧷 Type safety: pass ``context_type=MyCtx`` (a ``TypedDict`` or any
    ``Mapping`` subtype) and the returned ``MachineNode[MyCtx]`` carries
    that type into every interpreter built from it -- ``interp.context``
    is then a ``MyCtx``, so a typo'd key or a wrong value type is a checker
    error at the call site. The argument has NO runtime effect (the
    machine's context is still the ``"context"`` in *config*); it exists
    purely so the type flows. Without it the context is ``Dict[str, Any]``,
    exactly as before.

    This function acts as a factory, providing a centralized and simplified
    way to construct a `MachineNode`. It intelligently handles the sourcing
    of business logic (actions, guards, services), either from an explicitly
    provided `MachineLogic` object or by auto-discovering it from specified
    modules or provider classes.

    Args:
        config: The machine's structural definition, typically from a
            JSON or YAML file. Must contain top-level 'id' and 'states' keys.
        logic: An optional, pre-constructed `MachineLogic` instance
            containing all required actions, guards, and services. If provided,
            this takes precedence over auto-discovery via `logic_modules` or
            `logic_providers`.
        logic_modules: An optional list of Python modules or their import
            strings (e.g., 'my_app.logic.actions'). The factory will search
            these modules for functions to satisfy the machine's logic
            requirements.
        logic_providers: An optional list of class instances. The factory
            will search the public methods of these objects to find the
            required logic implementations.

    Returns:
        A fully constructed and validated `MachineNode` instance, ready to be
        passed to an interpreter (`Interpreter` or `SyncInterpreter`).

    Raises:
        InvalidConfigError: If the `config` dictionary is missing the 'id'
            or 'states' keys, or if 'id' is not a string.
        ImplementationMissingError: If auto-discovery is used and a
            required action, guard, or service cannot be found in the
            provided modules or providers.

    Example:
        >>> # The following examples assume a config like this:
        >>> my_config = {
        ...     "id": "light-switch",
        ...     "initial": "off",
        ...     "states": {
        ...         "off": {"on": {"POWER": {"target": "on", "actions": ["my_action"]}}},
        ...         "on": {"on": {"POWER": {"target": "off"}}}
        ...     }
        ... }
        ...
        >>> # 1. With explicit logic binding
        >>> from xstate_statemachine import MachineLogic
        >>> my_logic = MachineLogic(actions={"my_action": lambda i,c,e,a: print("Action!")})
        >>> machine_from_logic = create_machine(my_config, logic=my_logic)
        >>>
        >>> # 2. With auto-discovery from a provider class
        >>> class LogicProvider:
        ...     # FIX: Mark method as static to resolve IDE warning, as it
        ...     # does not use the 'self' instance.
        ...     @staticmethod
        ...     def my_action(i, c, e, a):
        ...         print("Action from provider!")
        ...
        >>> provider = LogicProvider()
        >>> # FIX: Renamed variable to avoid "Redeclared 'machine'..." warning.
        >>> machine_from_provider = create_machine(my_config, logic_providers=[provider])
    """
    # -------------------------------------------------------------------------
    # ☝️ Step 1: Determine the Source of Business Logic
    # -------------------------------------------------------------------------
    final_logic: MachineLogic
    if logic:
        # ✅ Path 1: Use the explicitly provided logic instance.
        # This is the most direct approach, bypassing auto-discovery.
        logger.info("🧠 Using explicitly provided MachineLogic instance.")
        final_logic = logic
    else:
        # ✅ Path 2: No explicit logic provided, so engage auto-discovery.
        logger.info(
            "🤖 Attempting auto-discovery of actions, guards, and services..."
        )
        # The LogicLoader uses a Singleton pattern to ensure a single instance
        # can be used to register global logic modules if desired.
        loader = LogicLoader.get_instance()
        final_logic = loader.discover_and_build_logic(
            config,
            logic_modules=logic_modules,
            logic_providers=logic_providers,
        )

    # -------------------------------------------------------------------------
    # 🧪 Step 2: Validate the Core Machine Configuration
    # -------------------------------------------------------------------------
    logger.info("🕵️  Validating core machine configuration structure...")
    machine_id = config.get("id")

    # The machine ID is crucial for identification, logging, and event routing.
    # It must be a non-empty string.
    if not isinstance(machine_id, str) or not machine_id:
        logger.error(
            "❌ Machine configuration validation failed: 'id' is missing or not a non-empty string."
        )
        raise InvalidConfigError(
            "Machine configuration must have a non-empty 'id' string."
        )

    # The 'states' dictionary is the fundamental building block of any state machine.
    if "states" not in config:
        logger.error(
            "❌ Machine configuration validation failed: 'states' key is missing."
        )
        raise InvalidConfigError(
            "Invalid config: must be a dict with 'id' and 'states' keys."
        )

    logger.info(
        "✅ Configuration structure for machine '%s' is valid.", machine_id
    )

    # -------------------------------------------------------------------------
    # 🏗️ Step 3: Construct and Return the MachineNode
    # -------------------------------------------------------------------------
    # The MachineNode constructor will handle the recursive parsing of the
    # entire statechart configuration.
    logger.info("🏭 Assembling final MachineNode for '%s'...", machine_id)
    # 🏛️ #92: give the MACHINE its own logic container so aliasing (below)
    #    never touches the caller's object. `copy.copy` keeps the subclass
    #    (auto-registered methods stay bound) and shares the callables; only
    #    the three registry dicts are replaced by `_alias_logic_names`.
    owned_logic = (
        copy.copy(final_logic)
        if isinstance(final_logic, MachineLogic)
        else final_logic  # duck-typed: leave as-is
    )
    machine = MachineNode(config, owned_logic)
    # 🔤 Bind snake_case implementations to the camelCase names the config
    #    uses (and vice versa) once, here, so every interpreter lookup stays
    #    a plain dict hit. Exact-name entries are never overridden.
    _alias_logic_names(machine)
    # 🛡️ #51: payload validators. Any object exposing `validate(payload)`
    #    or being callable works -- pydantic models, TypedDict adapters,
    #    hand-written functions -- so the library takes no dependency.
    if event_schemas:
        machine.event_schemas = dict(event_schemas)

    # -------------------------------------------------------------------------
    # 🛡️ Step 4: Validate the built tree (0.8.0)
    # -------------------------------------------------------------------------
    # 🏛️ Unknown ACTIONS already raised here; unknown TARGETS and dead
    #    `always` loops did not -- they became silent runtime no-ops. The
    #    whole tree is needed to resolve cross-branch targets, so this runs
    #    only after construction. `strict_targets=False` is the 0.7.x escape
    #    hatch (warns instead of raising); it is removed in 1.0.
    # 🔀 Two DIFFERENT switches that happen to share a word (review A2):
    #    * this kwarg (default True) -- reject UNRESOLVABLE targets at build
    #      time; False downgrades to a DeprecationWarning (0.7.x hatch).
    #    * the `strictTargets` CONFIG key (default False) -- disable the
    #      `.child` SIBLING fallback, an opt-in stricter reading of relative
    #      targets. It lives on `machine.strict_targets`.
    #    Wiring the kwarg into the config flag would turn the opt-in into the
    #    default and reject every legitimate `.sibling` machine.
    validate_machine(machine, strict_targets=strict_targets)
    return machine


def _alias_logic_names(machine: MachineNode[Any]) -> None:
    """Resolve case/separator-insensitive aliases for a built machine."""
    actions: set = set()
    guards: set = set()
    services: set = set()
    LogicLoader._extract_logic_from_node(machine, actions, guards, services)
    logic = machine.logic
    # 🏛️ #92: `create_machine()` must not modify the object it was handed.
    #    Aliasing used to write into the caller's `MachineLogic` dicts, so a
    #    second machine built from the same logic saw already-aliased keys
    #    (suppressing the ambiguity guard) and an EARLIER machine's
    #    registry was retroactively extended. The machine now owns a
    #    shallow COPY of each registry: identical hot-path cost (still a
    #    plain dict), zero caller mutation, and `create_machine` is a pure
    #    function of its inputs again.
    for attr, required in (
        ("actions", actions),
        ("guards", guards),
        ("services", services),
    ):
        registry = getattr(logic, attr, None)
        # 🦆 `logic` is duck-typed by contract (any object exposing the
        #    three registries); skip a registry that is absent or not a
        #    dict.
        if isinstance(registry, dict):
            owned = dict(registry)
            resolve_aliases(owned, required)
            setattr(logic, attr, owned)
