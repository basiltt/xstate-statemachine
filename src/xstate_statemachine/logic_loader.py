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
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    Union,
)

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .exceptions import ImplementationMissingError, InvalidConfigError
from .machine_logic import MachineLogic
from .models import MachineNode, StateNode

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


def _snake_to_camel(snake_str: str) -> str:
    """Converts a snake_case string to camelCase.

    This utility function is a key part of the "Convention over Configuration"
    strategy. It allows developers to define Python functions using the
    standard PEP 8 snake_case naming convention, while seamlessly matching them
    against the conventional camelCase naming used in JSON/JavaScript
    environments like XState.

    Args:
        snake_str: The string in snake_case format (e.g., "my_action_name").

    Returns:
        The converted string in camelCase format (e.g., "myActionName").

    Example:
        >>> _snake_to_camel("hello_world")
        'helloWorld'
        >>> _snake_to_camel("a_b_c")
        'aBC'
    """
    # 🐍 Split the string by underscores.
    components = snake_str.split("_")
    # 📝 Capitalize the first letter of all components after the first one
    # and join them together.
    return components[0] + "".join(x.title() for x in components[1:])


# -----------------------------------------------------------------------------
# 🏛️ LogicLoader Class (Singleton Design Pattern)
# -----------------------------------------------------------------------------


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
        return cls._instance

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
    def _extract_logic_from_node(
        node: StateNode,
        actions: Set[str],
        guards: Set[str],
        services: Set[str],
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
        """
        #  Actions from entry/exit handlers
        all_actions = node.entry + node.exit

        # Actions and guards from `on` and `after` transitions
        all_transitions = [t for tl in node.on.values() for t in tl]
        all_transitions.extend([t for tl in node.after.values() for t in tl])
        if node.on_done:
            all_transitions.append(node.on_done)

        for transition in all_transitions:
            all_actions.extend(transition.actions)
            if transition.guard:
                guards.add(transition.guard)

        # Categorize actions vs. spawnable services
        for action_def in all_actions:
            if action_def.type.startswith("spawn_"):
                service_name = action_def.type.replace("spawn_", "")
                services.add(service_name)
            else:
                actions.add(action_def.type)

        # Logic from `invoke` definitions
        for invoke_def in node.invoke:
            if invoke_def.src:
                services.add(invoke_def.src)
            # Also check for logic within the `onDone` and `onError` transitions
            for transition in invoke_def.on_done + invoke_def.on_error:
                for action_def in transition.actions:
                    if action_def.type.startswith("spawn_"):
                        service_name = action_def.type.replace("spawn_", "")
                        services.add(service_name)
                    else:
                        actions.add(action_def.type)
                if transition.guard:
                    guards.add(transition.guard)

        # 🌳 Recurse into child states
        for child_node in node.states.values():
            LogicLoader._extract_logic_from_node(
                child_node, actions, guards, services
            )

    def discover_and_build_logic(
        self,
        machine_config: Dict[str, Any],
        logic_modules: Optional[List[Union[str, ModuleType]]] = None,
        logic_providers: Optional[List[Any]] = None,
    ) -> MachineLogic:
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

        # 🔎 Scan all modules for functions
        for module in all_modules:
            logger.debug(
                "  -> 🐍 Scanning module: '%s' for functions...",
                module.__name__,
            )
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if not name.startswith("_"):
                    logic_map[name] = func
                    logic_map[_snake_to_camel(name)] = func

        # 🔎 Scan all provider instances for methods (overrides module functions)
        if logic_providers:
            for provider in logic_providers:
                cls_name = provider.__class__.__name__
                logger.debug(
                    "  -> 🏛️  Scanning instance of class: '%s' for methods...",
                    cls_name,
                )
                for name, method in inspect.getmembers(
                    provider, inspect.ismethod
                ):
                    if not name.startswith("_"):
                        logic_map[name] = method
                        logic_map[_snake_to_camel(name)] = method

        # ---------------------------------------------------------------------
        # 📋 Step 2: Extract all required logic names from the config.
        # ---------------------------------------------------------------------
        required_actions, required_guards, required_services = (
            set(),
            set(),
            set(),
        )
        # Temporarily create a machine node to traverse its structure
        temp_machine = MachineNode(config=machine_config, logic=MachineLogic())
        LogicLoader._extract_logic_from_node(
            temp_machine, required_actions, required_guards, required_services
        )

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

        for logic_type, required_set, discovered_dict in logic_definitions:
            for name in required_set:
                if name in logic_map:
                    discovered_dict[name] = logic_map[name]
                else:
                    # 💥 Fail-fast if an implementation is missing.
                    raise ImplementationMissingError(
                        f"{logic_type} '{name}' is defined in the machine but "
                        "no implementation was found in the provided modules "
                        "or providers."
                    )

        total = sum(len(d) for d in discovered_logic.values())
        logger.info(
            "✨ Logic discovery complete. Bound %d implementations.", total
        )
        return MachineLogic(**discovered_logic)
