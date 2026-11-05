# /src/xstate_statemachine/logic_loader.py
# -----------------------------------------------------------------------------
# 🧠 Automatic Logic Discovery and Loader
# -----------------------------------------------------------------------------
# This module provides the `LogicLoader` class, a sophisticated mechanism for
# dynamically discovering and loading Python implementations (actions, guards,
# services) that correspond to names defined in an XState machine's JSON
# configuration.
#
# It embodies the "Convention over Configuration" principle by automatically
# mapping Python's `snake_case` naming to the `camelCase` convention common
# in the XState ecosystem.
#
# The `LogicLoader` implements the Singleton design pattern to act as a
# central, optional registry for logic, promoting a clean and decoupled
# architecture.
# -----------------------------------------------------------------------------
"""
Provides a class-based system for auto-discovering state machine logic.

This module is central to the library's developer experience, as it removes
the need for manually binding every action, guard, and service. The `LogicLoader`
can inspect Python modules and class instances to find the code that implements
the behavior defined in a machine's configuration.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import importlib
import inspect
import logging
from types import ModuleType
from typing import (
    cast,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .exceptions import ImplementationMissingError, InvalidConfigError
from .machine_logic import MachineLogic, normalize_logic_name
from .actions import is_builtin as is_builtin_action
from .models import (
    MachineNode,
    StateNode,
    TransitionDefinition,
    is_spawn_action,
    spawn_service_key,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🧬 Type Variables
# -----------------------------------------------------------------------------
# Defines a TypeVar for use in the singleton's get_instance method, ensuring
# that type checkers understand the return type correctly.
_TLogicLoader = TypeVar("_TLogicLoader", bound="LogicLoader")


# -----------------------------------------------------------------------------
# 🛠️ Helper Functions
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# 🏛️ LogicLoader Class (Singleton Design Pattern)
# -----------------------------------------------------------------------------


def _register_explicit_name(
    logic_map: Dict[str, Callable[..., Any]], func: Callable[..., Any]
) -> Optional[str]:
    """Also key *func* under the name its decorator declared, if any.

    🏛️ Architecture decision: name matching is by Python identifier and
    its camelCase form -- that is the convention-over-configuration promise.
    But a config name need not BE an identifier: Stately exports anonymous
    actions as ``inline:machine.state#entry[0]``, and hand-written configs
    use dots and dashes. ``@action("<original>")`` records the declared
    name as ``_xsm_name``; honouring it here is what lets a generated or
    hand-written provider implement such a name at all. A bound method
    carries the marker on its ``__func__``.
    """
    target = getattr(func, "__func__", func)
    explicit = getattr(target, "_xsm_name", None)
    if isinstance(explicit, str) and explicit:
        logic_map[explicit] = func
        return explicit
    return None


def _is_provider_callable(member: Any) -> bool:
    """Predicate for scanning a logic provider instance.

    🏛️ Review RU-04: `inspect.ismethod` alone skipped ``@staticmethod``s
    -- on an instance they are plain functions -- so a provider could not
    offer a pure guard without a dummy ``self``. Bound methods (including
    ``@classmethod``s) and plain functions are both implementations.
    """
    return inspect.ismethod(member) or inspect.isfunction(member)


class LogicLoader:
    """Manages the dynamic discovery and building of `MachineLogic`.

    This class implements the Singleton design pattern to provide a centralized
    registry for logic modules and providers. It discovers actions, guards,
    and services referenced in an XState machine configuration and binds them
    to their corresponding Python implementations.

    This approach decouples the state machine's definition (the "what") from
    its implementation (the "how"), enhancing modularity and maintainability.

    Attributes:
        _instance: The private class-level attribute that holds the single
                   instance of the class, ensuring a global registry.
        _registered_logic_modules: A list of Python modules that have been
                                   globally registered with this loader.
    """

    _instance: Optional["LogicLoader"] = None

    def __init__(self) -> None:
        """Initializes the LogicLoader instance.

        This constructor is intended to be called only once by the
        `get_instance` class method as part of the Singleton pattern. Direct
        instantiation is discouraged.
        """
        self._registered_logic_modules: List[ModuleType] = []
        logger.debug("✨ LogicLoader singleton instance created.")

    @classmethod
    def get_instance(cls: Type[_TLogicLoader]) -> _TLogicLoader:
        """Provides access to the singleton instance of the LogicLoader.

        This method ensures that only one instance of `LogicLoader` exists
        throughout the application's lifecycle, providing a consistent, global
        registry for state machine logic.

        Returns:
            The single, shared instance of the `LogicLoader`.
        """
        #  Gaurd clause to ensure only one instance is ever created.
        if cls._instance is None:
            # 📦 This is the one and only time the constructor will be called.
            cls._instance = cls()
            logger.info(
                "📦 Initializing new LogicLoader instance (Singleton)."
            )
        return cast(_TLogicLoader, cls._instance)

    def register_logic_module(self, module: ModuleType) -> None:
        """Registers a Python module for global logic discovery.

        This is useful in large applications where logic may be spread across
        many files. Modules can be registered once at application startup,
        and all subsequent calls to `create_machine` will have access to them
        without needing to pass them in `logic_modules` repeatedly.

        Args:
            module: The Python module object to register for discovery.
        """
        if module not in self._registered_logic_modules:
            self._registered_logic_modules.append(module)
            logger.info(
                "🔌 Registered global logic module: '%s'", module.__name__
            )

    @staticmethod
    def _classify_action(
        action_type: str,
        actions: Set[str],
        services: Set[str],
        builtins: Set[str],
    ) -> None:
        """File one referenced action name under the set it is found in.

        🏛️ ONE rule for every place an action can appear (``entry`` /
        ``exit``, ``on``, ``after``, ``onDone``, an invoke's ``onDone`` /
        ``onError``). Review RU-06: the invoke handlers had their own copy
        that forgot the ``spawn_`` routing, so a ``spawn_worker`` in an
        invoke's ``onDone`` demanded an ACTION implementation and
        auto-discovery rejected the machine.

        * ``spawn_<key>`` / ``spawn_blocking_<key>`` are built-in action
          types resolved from ``logic.services[<key>]`` at run time.
        * Other built-in creators (``assign``, ``raise``, ``sendTo``, …) are
          implemented by the interpreter. They are recorded in *builtins*
          so that a user implementation of the same name can still be
          bound -- it wins over the built-in (AGENTS.md).
        * Everything else needs a user implementation.

        Args:
            action_type: The action name as the config spells it.
            actions: Required user actions.
            services: Required services (spawn keys, invoke sources).
            builtins: Built-in action names the machine references.
        """
        if is_spawn_action(action_type):
            services.add(spawn_service_key(action_type))
        elif is_builtin_action(action_type):
            builtins.add(action_type)
        else:
            actions.add(action_type)

    @staticmethod
    def _extract_logic_from_node(
        node: StateNode[Any],
        actions: Set[str],
        guards: Set[str],
        services: Set[str],
        builtins: Optional[Set[str]] = None,
    ) -> None:
        """Recursively traverses a StateNode tree to extract all logic names.

        This static helper method walks the entire machine configuration tree
        and collects the names of all actions, guards, and services that are
        referenced, populating the provided sets.

        Args:
            node: The `StateNode` to start the traversal from.
            actions: A set to be populated with required action names.
            guards: A set to be populated with required guard names.
            services: A set to be populated with required service names.
            builtins: A set to be populated with the built-in action names
                the machine references (``log``, ``cancel``, …); a user
                implementation of one of these wins over the built-in.
                Optional for callers that only need the first three.
        """
        if builtins is None:
            builtins = set()
        classify = LogicLoader._classify_action
        collect = LogicLoader._collect_transition_logic
        # ⚡ No intermediate `all_actions` / `all_transitions` lists: this
        #    runs for every node of every `create_machine()`, and most nodes
        #    own one or two transitions (#307 benchmark).
        for action_def in node.entry:
            classify(action_def.type, actions, services, builtins)
        for action_def in node.exit:
            classify(action_def.type, actions, services, builtins)
        for transitions in node.on.values():
            for transition in transitions:
                collect(transition, actions, guards, services, builtins)
        for transitions in node.after.values():
            for transition in transitions:
                collect(transition, actions, guards, services, builtins)
        # 🏁 Every `onDone` alternative, not just the first (MOD-02).
        for transition in node.on_done_transitions:
            collect(transition, actions, guards, services, builtins)

        # Logic from `invoke` definitions
        for invoke_def in node.invoke:
            if invoke_def.src:
                services.add(invoke_def.src)
            # Also check for logic within the `onDone` and `onError` transitions
            for transition in invoke_def.on_done:
                collect(transition, actions, guards, services, builtins)
            for transition in invoke_def.on_error:
                collect(transition, actions, guards, services, builtins)

        # 🌳 Recurse into child states
        for child_node in node.states.values():
            LogicLoader._extract_logic_from_node(
                child_node, actions, guards, services, builtins
            )

    @staticmethod
    def _collect_transition_logic(
        transition: TransitionDefinition,
        actions: Set[str],
        guards: Set[str],
        services: Set[str],
        builtins: Set[str],
    ) -> None:
        """File one transition's action names and guard leaves."""
        for action_def in transition.actions:
            LogicLoader._classify_action(
                action_def.type, actions, services, builtins
            )
        if transition.guard_def is not None:
            LogicLoader._collect_guard_names(transition.guard_def, guards)

    @staticmethod
    def required_names(
        machine: MachineNode[Any],
    ) -> Tuple[Set[str], Set[str], Set[str]]:
        """The (actions, guards, services) a machine's config references.

        ⚡ Memoised on the `MachineNode`: discovery and alias resolution both
        need this set during `create_machine()`, and the tree is immutable
        once built. Returns COPIES so callers may mutate freely.
        """
        memo = machine._required_logic
        if memo is None:
            a: Set[str] = set()
            g: Set[str] = set()
            s: Set[str] = set()
            b: Set[str] = set()
            LogicLoader._extract_logic_from_node(machine, a, g, s, b)
            memo = machine._required_logic = (a, g, s, b)
        return set(memo[0]), set(memo[1]), set(memo[2])

    @staticmethod
    def builtin_action_names(machine: MachineNode[Any]) -> Set[str]:
        """The built-in action names a machine's config references.

        Spelled as the config spells them (``log``, ``send_to``, ``sendTo``).
        Discovery binds a user implementation of such a name when the
        scanned module defines it or a provider implements it (RU-05); the
        interpreter then runs that instead of the built-in. A COPY.
        """
        memo = machine._required_logic
        if memo is None:
            LogicLoader.required_names(machine)  # fills the memo
            memo = machine._required_logic
        return set(memo[3]) if memo is not None else set()

    @staticmethod
    def _collect_guard_names(guard_def: Any, guards: Set[str]) -> None:
        """Collects the user-implemented guard names a guard depends on.

        🏛️ Architecture decision: composite guards (`and` / `or` / `not`) and
        the built-in `stateIn` are evaluated by the interpreter itself, so
        requiring implementations for them made auto-discovery reject every
        machine using higher-order guards. Only the leaf predicates a user
        must actually supply are collected, recursing through nesting.

        Args:
            guard_def (Any): A `GuardDefinition`, or `None`.
            guards (Set[str]): Accumulator for required guard names.
        """
        if guard_def is None:
            return
        if getattr(guard_def, "is_builtin", False):
            for child in getattr(guard_def, "children", []):
                LogicLoader._collect_guard_names(child, guards)
            return
        guards.add(guard_def.type)

    def discover_and_build_logic(
        self,
        machine_config: Dict[str, Any],
        logic_modules: Optional[List[Union[str, ModuleType]]] = None,
        logic_providers: Optional[List[Any]] = None,
        *,
        machine: Optional[MachineNode[Any]] = None,
    ) -> MachineLogic[Any]:
        """Discovers implementations and builds a `MachineLogic` instance.

        This is the main orchestration method. It performs a three-step process:
        1.  Scans all provided logic sources (modules and class instances)
            and builds a map of available implementations.
        2.  Traverses the `machine_config` to determine all required logic names.
        3.  Matches the required names against the available implementations and
            returns a populated `MachineLogic` object.

        Args:
            machine_config: The state machine's configuration dictionary.
            logic_modules: A list of modules or import paths to scan.
            logic_providers: A list of class instances to scan for methods.

        Returns:
            A `MachineLogic` instance populated with the discovered functions.

        Raises:
            InvalidConfigError: If the machine config is not a dictionary.
            TypeError: If an item in `logic_modules` is not a string or module.
            ImplementationMissingError: If a required implementation is not found.
        """
        _info = logger.isEnabledFor(logging.INFO)  # ⚡ per build
        if _info:
            logger.info("🔍 Starting logic discovery and binding process...")
        if not isinstance(machine_config, dict):
            raise InvalidConfigError(
                "Machine configuration must be a dictionary."
            )

        # ---------------------------------------------------------------------
        # 🗺️ Step 1: Build a map of all available logic implementations.
        # ---------------------------------------------------------------------
        all_modules: List[ModuleType] = list(self._registered_logic_modules)
        if logic_modules:
            for item in logic_modules:
                module: ModuleType
                if isinstance(item, str):
                    # 🐍 Dynamically import the module if a string path is given
                    module = importlib.import_module(item)
                elif isinstance(item, ModuleType):
                    module = item
                else:
                    raise TypeError(
                        f"Items in 'logic_modules' must be a module path (str) "
                        f"or a module object, not {type(item).__name__}"
                    )
                if module not in all_modules:
                    all_modules.append(module)

        logic_map: Dict[str, Callable[..., Any]] = {}
        #: 🏠 RU-05: names whose implementation a scanned module DEFINES
        #: (not merely imports) or a provider implements. Only these may
        #: override a built-in action of the same name; `from x import log`
        #: in a logic module must not hijack the `log` built-in.
        own_names: Set[str] = set()

        # 🔎 Scan all modules for functions
        for module in all_modules:
            logger.debug(
                "  -> 🐍 Scanning module: '%s' for functions...",
                module.__name__,
            )
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith("_"):
                    # 🏛️ #93: register under the REAL name only. The old
                    #    forward `snake->camel` alias wrote `fetchData` for
                    #    `fetch_data`, silently OVERWRITING a genuine
                    #    `fetchData` defined in the same module -- so the
                    #    ambiguity check below never saw two candidates.
                    #    Matching is normalised (case/separator-insensitive)
                    #    at resolution time, which subsumes that alias.
                    logic_map[name] = func
                    explicit = _register_explicit_name(logic_map, func)
                    if getattr(func, "__module__", None) == module.__name__:
                        own_names.add(name)
                        if explicit is not None:
                            own_names.add(explicit)

        # 🔎 Scan all provider instances for methods (overrides module functions)
        if logic_providers:
            for provider in logic_providers:
                cls_name = provider.__class__.__name__
                logger.debug(
                    "  -> 🏛️  Scanning instance of class: '%s' for methods...",
                    cls_name,
                )
                # 🏛️ RU-04: bound methods AND plain functions, so a
                #    `@staticmethod` on the provider is discovered too.
                for name, method in inspect.getmembers(
                    provider, _is_provider_callable
                ):
                    if not name.startswith("_"):
                        logic_map[name] = method
                        own_names.add(name)
                        explicit = _register_explicit_name(logic_map, method)
                        if explicit is not None:
                            own_names.add(explicit)

        # ---------------------------------------------------------------------
        # 📋 Step 2: Extract all required logic names from the config.
        # ---------------------------------------------------------------------
        required_actions: Set[str] = set()
        required_guards: Set[str] = set()
        required_services: Set[str] = set()
        # ⚡ Perf: walk the caller's already-built tree when it hands one in.
        #    `create_machine` used to let this method build a THROWAWAY
        #    `MachineNode` purely to collect names, then build the real one
        #    -- every machine was parsed twice, and the loader was 43% of
        #    construction time. The tree is the same either way; only the
        #    `logic` attribute differs, and it is attached afterwards.
        tree: MachineNode[Any] = (
            machine
            if machine is not None
            else MachineNode(config=machine_config, logic=MachineLogic())
        )
        req_a, req_g, req_s = LogicLoader.required_names(tree)
        required_actions |= req_a
        required_guards |= req_g
        required_services |= req_s
        # ⚡ A chart that names no action, guard, service or built-in has
        #    nothing to bind: hand back an empty, machine-owned container
        #    without building the matching indexes (#307 benchmark).
        if not (
            required_actions or required_guards or required_services
        ) and not LogicLoader.builtin_action_names(tree):
            return MachineLogic()

        # ---------------------------------------------------------------------
        # 🔗 Step 3: Match requirements with implementations.
        # ---------------------------------------------------------------------
        discovered_logic: Dict[str, Dict[str, Callable[..., Any]]] = {
            "actions": {},
            "guards": {},
            "services": {},
        }
        logic_definitions = [
            ("Action", required_actions, discovered_logic["actions"]),
            ("Guard", required_guards, discovered_logic["guards"]),
            ("Service", required_services, discovered_logic["services"]),
        ]

        # 🔤 Normalised index so `log_http_status` satisfies `logHTTPStatus`
        #    (the camelCase forward conversion is lossy for acronyms and
        #    undefined for non-identifier names; see `normalize_logic_name`).
        # 🏛️ #93: the same ambiguity rule `resolve_aliases` applies to an
        #    explicit `MachineLogic`. Two DIFFERENT callables whose names
        #    normalise equal used to resolve by module iteration order with
        #    no error; now that is `InvalidConfigError` -- but only when the
        #    machine actually REQUIRES the name, so unrelated near-duplicates
        #    in a big shared module do not break unrelated machines.
        normalized_map: Dict[str, Callable[..., Any]] = {}
        normalized_candidates: Dict[str, List[str]] = {}
        for key, impl in logic_map.items():
            norm = normalize_logic_name(key)
            normalized_map.setdefault(norm, impl)
            normalized_candidates.setdefault(norm, []).append(key)

        # 🎭 #155: a `spawn_<key>` action name that the user actually
        #    IMPLEMENTS is an action, not a spawn. Discovery routed every
        #    such name to `services["<key>"]` unconditionally; move the ones
        #    with a matching implementation back to `actions` so the runtime
        #    (which now checks `logic.actions` first) finds them.
        for name in list(required_services):
            for candidate in (f"spawn_{name}", f"spawn_blocking_{name}"):
                if candidate in logic_map or (
                    normalize_logic_name(candidate) in normalized_map
                ):
                    required_services.discard(name)
                    required_actions.add(candidate)
                    break

        for logic_type, required_set, discovered_dict in logic_definitions:
            for name in required_set:
                if name in logic_map:
                    discovered_dict[name] = logic_map[name]
                elif normalize_logic_name(name) in normalized_map:
                    norm = normalize_logic_name(name)
                    cands = normalized_candidates[norm]
                    distinct = {id(logic_map[c]) for c in cands}
                    if len(distinct) > 1:
                        raise InvalidConfigError(
                            f"{logic_type} '{name}' is ambiguous: "
                            f"{sorted(cands)} are all discovered and differ "
                            f"only by case or separators, but are DIFFERENT "
                            f"callables. Keep one, or register the exact "
                            f"name '{name}' explicitly."
                        )
                    discovered_dict[name] = normalized_map[norm]
                else:
                    # 💥 Fail-fast if an implementation is missing.
                    raise ImplementationMissingError(
                        f"{logic_type} '{name}' is defined in the machine but "
                        "no implementation was found in the provided modules "
                        "or providers."
                    )

        # 🎬 RU-05: a built-in action name the machine uses (`log`,
        #    `cancel`, `stop`, ...) that the scanned module DEFINES or a
        #    provider implements is the user's own action and wins over the
        #    built-in, exactly as it does in an explicit `MachineLogic`
        #    (AGENTS.md: built-ins resolve after `logic.actions`). Discovery
        #    used to skip these names, so with auto-binding the built-in ran
        #    and the user's function was silently never called. A missing
        #    implementation is fine here: the built-in runs.
        actions_found = discovered_logic["actions"]
        for name in LogicLoader.builtin_action_names(tree):
            if name in actions_found:
                continue
            cands = (
                [name]
                if name in logic_map
                else normalized_candidates.get(normalize_logic_name(name), [])
            )
            own = [c for c in cands if c in own_names]
            if not own:
                continue
            if len({id(logic_map[c]) for c in own}) > 1:
                raise InvalidConfigError(
                    f"Action '{name}' is ambiguous: {sorted(own)} are all "
                    f"discovered and differ only by case or separators, but "
                    f"are DIFFERENT callables. Keep one, or register the "
                    f"exact name '{name}' explicitly."
                )
            actions_found[name] = logic_map[own[0]]
            logger.info(
                "🎬 User implementation '%s' overrides the built-in action "
                "of the same name.",
                own[0],
            )

        if _info:
            total = sum(len(d) for d in discovered_logic.values())
            logger.info(
                "✨ Logic discovery complete. Bound %d implementations.",
                total,
            )
        return MachineLogic(
            actions=discovered_logic["actions"],
            guards=discovered_logic["guards"],
            services=discovered_logic["services"],
        )
