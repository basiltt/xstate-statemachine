# src/xstate_statemachine/logic_loader.py

# -----------------------------------------------------------------------------
# 🧠 Logic Loader
# -----------------------------------------------------------------------------
# This module provides a class-based mechanism for dynamically discovering and
# loading Python implementations (actions, guards, services) that correspond
# to names defined in an XState machine's JSON configuration.
#
# It can discover logic from both functions in modules and methods on class
# instances, promoting flexibility in application architecture and the "Convention
# over Configuration" principle.
#
# The `LogicLoader` class acts as a central registry and factory for `MachineLogic`
# instances. It can be used as a Singleton to maintain a global registry of
# logic throughout an application's lifecycle.
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
_TLogicLoader = TypeVar("_TLogicLoader", bound="LogicLoader")


# -----------------------------------------------------------------------------
# 🛠️ Helper Functions
# -----------------------------------------------------------------------------


def _snake_to_camel(snake_str: str) -> str:
    """Converts a snake_case string to camelCase.

    This utility function allows developers to define Python functions using the
    standard PEP 8 snake_case naming convention, while matching them against
    the conventional camelCase naming used in JSON/JavaScript environments like
    XState.

    Args:
        snake_str (str): The string in snake_case format (e.g., "my_action_name").

    Returns:
        str: The converted string in camelCase format (e.g., "myActionName").
    """
    # 🐍 Split the string by underscores.
    components = snake_str.split("_")
    # 📝 Return the first component as is, and capitalize the first letter
    # of all subsequent components, then join them together.
    return components[0] + "".join(x.title() for x in components[1:])


# -----------------------------------------------------------------------------
# 🏛️ LogicLoader Class (Singleton Design Pattern)
# -----------------------------------------------------------------------------


class LogicLoader:
    """
    Manages dynamic discovery and building of `MachineLogic`.

    This class implements the Singleton design pattern to provide a centralized
    registry for logic modules. It discovers actions, guards, and services
    referenced in an XState machine configuration and binds them to their
    corresponding Python implementations.

    This approach decouples the state machine's definition (the "what") from
    its implementation (the "how"), enhancing modularity and maintainability.

    Attributes:
        _instance (Optional["LogicLoader"]): The private class-level attribute
            that holds the single instance of the class.
        _registered_logic_modules (List[ModuleType]): A list of Python modules
            that have been globally registered with this loader instance.
    """

    _instance: Optional["LogicLoader"] = None

    def __init__(self) -> None:
        """Initializes the LogicLoader instance.

        This constructor is intended to be called only once by the `get_instance`
        class method as part of the Singleton pattern.
        """
        self._registered_logic_modules: List[ModuleType] = []
        logger.debug("✨ LogicLoader instance created.")

    @classmethod
    def get_instance(cls: Type[_TLogicLoader]) -> _TLogicLoader:
        """
        Provides access to the singleton instance of the LogicLoader.

        This method ensures that only one instance of `LogicLoader` exists
        throughout the application's lifecycle, providing a consistent, global
        registry for state machine logic.

        Returns:
            The single, shared instance of the `LogicLoader`.
        """
        if cls._instance is None:
            cls._instance = cls()
            logger.info(
                "📦 Initializing new LogicLoader instance (Singleton)."
            )
        return cls._instance

    def register_logic_module(self, module: ModuleType) -> None:
        """
        Registers a Python module for global logic discovery.

        Args:
            module (ModuleType): The Python module object to register.
        """
        if module not in self._registered_logic_modules:
            self._registered_logic_modules.append(module)
            logger.info("🔌 Registered logic module: '%s'", module.__name__)

    def _extract_logic_from_node(
        self,
        node: StateNode,
        actions: Set[str],
        guards: Set[str],
        services: Set[str],
    ) -> None:
        """
        Recursively traverses a StateNode tree to extract all logic names.

        Args:
            node (StateNode): The state node to inspect.
            actions (Set[str]): A set to populate with required action names.
            guards (Set[str]): A set to populate with required guard names.
            services (Set[str]): A set to populate with required service names.
        """
        all_actions = node.entry + node.exit
        all_transitions = [t for tl in node.on.values() for t in tl]
        all_transitions.extend([t for tl in node.after.values() for t in tl])
        if node.on_done:
            all_transitions.append(node.on_done)

        for transition in all_transitions:
            all_actions.extend(transition.actions)
            if transition.guard:
                guards.add(transition.guard)

        for action_def in all_actions:
            actions.add(action_def.type)

        for invoke_def in node.invoke:
            if invoke_def.src:
                services.add(invoke_def.src)
            for transition in invoke_def.on_done + invoke_def.on_error:
                for action_def in transition.actions:
                    actions.add(action_def.type)
                if transition.guard:
                    guards.add(transition.guard)

        for child_node in node.states.values():
            self._extract_logic_from_node(
                child_node, actions, guards, services
            )

    def discover_and_build_logic(
        self,
        machine_config: Dict[str, Any],
        logic_modules: Optional[List[Union[str, ModuleType]]] = None,
        logic_providers: Optional[List[Any]] = None,
    ) -> MachineLogic:
        """
        Discovers implementations from modules/instances and builds `MachineLogic`.
        """
        logger.info("🔍 Starting logic discovery and binding process...")
        if not isinstance(machine_config, dict):
            raise InvalidConfigError(
                "Machine configuration must be a dictionary."
            )

        all_modules: List[ModuleType] = list(self._registered_logic_modules)
        if logic_modules:
            for item in logic_modules:
                module: ModuleType
                if isinstance(item, str):
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

        for module in all_modules:
            logger.debug(
                "🔎 Scanning module: '%s' for functions...", module.__name__
            )
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("_"):
                    continue
                logic_map[name] = func
                camel_name = _snake_to_camel(name)
                logic_map[camel_name] = func

        # FIX: Process providers *after* modules so their methods can override.
        if logic_providers:
            for provider in logic_providers:
                cls_name = provider.__class__.__name__
                logger.debug(
                    "🔎 Scanning instance of class: '%s' for methods...",
                    cls_name,
                )
                for name, method in inspect.getmembers(
                    provider, inspect.ismethod
                ):
                    if name.startswith("_"):
                        continue
                    logic_map[name] = method
                    camel_name = _snake_to_camel(name)
                    logic_map[camel_name] = method

        required_actions, required_guards, required_services = (
            set(),
            set(),
            set(),
        )
        temp_machine = MachineNode(config=machine_config, logic=MachineLogic())
        self._extract_logic_from_node(
            temp_machine, required_actions, required_guards, required_services
        )

        discovered_logic = {"actions": {}, "guards": {}, "services": {}}
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
                    raise ImplementationMissingError(
                        f"{logic_type} '{name}' is defined in the machine but "
                        "no implementation was found."
                    )

        total = sum(len(d) for d in discovered_logic.values())
        logger.info(
            "✨ Logic discovery complete. Bound %d implementations.", total
        )
        return MachineLogic(**discovered_logic)
