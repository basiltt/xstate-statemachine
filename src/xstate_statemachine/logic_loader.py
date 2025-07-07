# src/xstate_statemachine/logic_loader.py

# -----------------------------------------------------------------------------
# 🧠 Logic Loader
# -----------------------------------------------------------------------------
# This module provides a class-based mechanism for dynamically discovering and
# loading Python implementations (actions, guards, services) that correspond
# to names defined in an XState machine's JSON configuration. It promotes the
# "Convention over Configuration" principle by allowing developers to organize
# their logic in modules for automatic binding.
#
# The `LogicLoader` class acts as a central registry and factory for `MachineLogic`
# instances. It can be used as a Singleton to maintain a global registry of
# logic modules throughout an application's lifecycle.
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
# A dedicated logger for this module to provide detailed operational insights.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🧬 Type Variables
# -----------------------------------------------------------------------------
# Define a TypeVar for the LogicLoader instance itself. This is particularly
# useful for class methods that return an instance of the class (`cls`),
# ensuring proper type hinting and IDE autocompletion.
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
    """Manages dynamic discovery and building of `MachineLogic`.

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
        # 📋 Initialize an empty list to store globally registered modules.
        # This instance variable ensures that each loader (though typically one)
        # manages its own set of modules.
        self._registered_logic_modules: List[ModuleType] = []
        logger.debug("✨ LogicLoader instance created.")

    @classmethod
    def get_instance(cls: Type[_TLogicLoader]) -> _TLogicLoader:
        """Provides access to the singleton instance of the LogicLoader.

        This method ensures that only one instance of `LogicLoader` exists
        throughout the application's lifecycle, providing a consistent, global
        registry for state machine logic. This is the factory method for the
        Singleton pattern.

        Returns:
            _TLogicLoader: The single, shared instance of the `LogicLoader`.
        """
        # 🧐 Check if the singleton instance has been created yet.
        if cls._instance is None:
            # 📦 If not, create a new instance and store it.
            cls._instance = cls()
            logger.info(
                "📦 Initializing new LogicLoader instance (Singleton)."
            )
        return cls._instance

    def register_logic_module(self, module: ModuleType) -> None:
        """Registers a Python module for global logic discovery.

        Any functions defined in the provided module become candidates for
        auto-binding to the state machine's actions, guards, and services.
        Modules are stored globally within the singleton instance.

        Args:
            module (ModuleType): The Python module object to register.
        """
        # 🧪 Check if the module is already in the registry to prevent duplicates.
        if module not in self._registered_logic_modules:
            self._registered_logic_modules.append(module)
            logger.info("🔌 Registered logic module: '%s'", module.__name__)
        else:
            logger.debug(
                "🔗 Logic module '%s' is already registered. Skipping.",
                module.__name__,
            )

    def _extract_logic_from_node(
        self,
        node: StateNode,
        actions: Set[str],
        guards: Set[str],
        services: Set[str],
    ) -> None:
        """Recursively traverses a StateNode tree to extract all logic names.

        This internal method systematically walks through the machine's structure,
        aggregating the names of all actions, guards, and services defined in
        entry/exit handlers, transitions, and invocations. Using the `StateNode`
        pydantic models ensures we operate on validated data, adhering to the DRY
        principle by not re-parsing the raw configuration dictionary.

        Args:
            node (StateNode): The state node to inspect.
            actions (Set[str]): A set to populate with required action names.
            guards (Set[str]): A set to populate with required guard names.
            services (Set[str]): A set to populate with required service names.
        """
        # 🚶‍♂️ Collect all actions from entry, exit, and transitions.
        all_actions = node.entry + node.exit
        all_transitions = [t for tl in node.on.values() for t in tl]
        all_transitions.extend([t for tl in node.after.values() for t in tl])
        if node.on_done:
            all_transitions.append(node.on_done)

        for transition in all_transitions:
            all_actions.extend(transition.actions)
            # 🛡️ Add the guard name if it exists.
            if transition.guard:
                guards.add(transition.guard)

        for action_def in all_actions:
            actions.add(action_def.type)

        # 📞 Collect services from 'invoke' definitions.
        for invoke_def in node.invoke:
            if invoke_def.src:
                services.add(invoke_def.src)
            # 🔄 Recursively check for logic within the invocation's own lifecycle
            # (onDone/onError) transitions.
            for transition in invoke_def.on_done + invoke_def.on_error:
                for action_def in transition.actions:
                    actions.add(action_def.type)
                if transition.guard:
                    guards.add(transition.guard)

        # 🌳 Recurse into all child states to ensure complete discovery.
        for child_node in node.states.values():
            self._extract_logic_from_node(
                child_node, actions, guards, services
            )

    def discover_and_build_logic(
        self,
        machine_config: Dict[str, Any],
        user_logic_modules: Optional[List[Union[str, ModuleType]]] = None,
    ) -> MachineLogic:
        """Discovers implementations and builds a `MachineLogic` instance.

        This is the core factory method of the loader. It orchestrates the entire
        process:
        1. Aggregates all available logic modules (global and user-provided).
        2. Extracts all required logic names from the state machine config.
        3. Searches the modules for matching Python functions.
        4. Populates and returns a `MachineLogic` object.

        Args:
            machine_config (Dict[str, Any]): The raw XState machine configuration
                dictionary.
            user_logic_modules (Optional[List[Union[str, ModuleType]]]): A list
                of modules to search for logic, provided for this specific call.
                Can contain module import paths (e.g., "my_app.logic") or
                already-imported module objects.

        Returns:
            MachineLogic: An instantiated `MachineLogic` object populated with all
                          the discovered callable functions.

        Raises:
            InvalidConfigError: If `machine_config` is not a dictionary.
            ImportError: If a module path string in `user_logic_modules` cannot be
                         resolved and imported.
            TypeError: If an item in `user_logic_modules` is not a string or module.
            ImplementationMissingError: If a required action, guard, or service
                                        is defined in the config but no matching
                                        Python function is found in the modules.
        """
        logger.info("🔍 Starting logic discovery and binding process...")
        # ---------------------------------------------------------------------
        # 1. Validate Inputs & Aggregate Modules
        # ---------------------------------------------------------------------
        if not isinstance(machine_config, dict):
            raise InvalidConfigError(
                "Machine configuration must be a dictionary."
            )

        # 🔗 Combine globally registered modules with any user-provided ones.
        all_modules: List[ModuleType] = list(self._registered_logic_modules)
        if user_logic_modules:
            for module_or_path in user_logic_modules:
                module: ModuleType
                if isinstance(module_or_path, str):
                    try:
                        # 📦 Attempt to dynamically import the module from its path.
                        module = importlib.import_module(module_or_path)
                        logger.debug(
                            "✅ Successfully imported module: '%s'",
                            module_or_path,
                        )
                    except ImportError as e:
                        logger.critical(
                            "❌ Failed to import logic module: '%s'.",
                            module_or_path,
                        )
                        raise e
                elif isinstance(module_or_path, ModuleType):
                    module = module_or_path
                else:
                    # 💥 Handle incorrect type for module specification.
                    raise TypeError(
                        f"Items in 'user_logic_modules' must be a module path (str) or a "
                        f"module object, not {type(module_or_path).__name__}"
                    )
                #  deduplicate modules
                if module not in all_modules:
                    all_modules.append(module)

        if not all_modules:
            logger.warning(
                "⚠️ No logic modules were provided. Machine will operate without custom logic."
            )
            return MachineLogic()

        # ---------------------------------------------------------------------
        # 2. Build a Map of All Available Logic Implementations
        # ---------------------------------------------------------------------
        # 🗺️ Create a lookup map of all public functions from all modules.
        # This map supports both snake_case and camelCase names to bridge
        # Python and JSON/XState conventions.
        logic_map: Dict[str, Callable[..., Any]] = {}
        for module in all_modules:
            logger.debug("🔎 Scanning module: '%s'", module.__name__)
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if name.startswith("_"):
                    continue  # 🤫 Skip private functions.

                # 🐍 Register both snake_case and camelCase versions.
                if name not in logic_map:
                    logic_map[name] = func
                camel_name = _snake_to_camel(name)
                if camel_name not in logic_map:
                    logic_map[camel_name] = func

        # ---------------------------------------------------------------------
        # 3. Extract Required Logic Names from Machine Config
        # ---------------------------------------------------------------------
        required_actions, required_guards, required_services = (
            set(),
            set(),
            set(),
        )
        # 🏗️ Build a temporary machine node structure to safely traverse it.
        # This avoids parsing the raw dict and leverages Pydantic model validation.
        temp_machine_node = MachineNode(
            config=machine_config, logic=MachineLogic()
        )
        self._extract_logic_from_node(
            temp_machine_node,
            required_actions,
            required_guards,
            required_services,
        )
        logger.debug("🎯 Required Actions: %s", required_actions or "None")
        logger.debug("🛡️ Required Guards: %s", required_guards or "None")
        logger.debug("📞 Required Services: %s", required_services or "None")

        # ---------------------------------------------------------------------
        # 4. Discover and Bind Implementations
        # ---------------------------------------------------------------------
        # 🚀 Prepare the final logic dictionary.
        discovered_logic = {"actions": {}, "guards": {}, "services": {}}
        logic_definitions = [
            ("Action", required_actions, discovered_logic["actions"]),
            ("Guard", required_guards, discovered_logic["guards"]),
            ("Service", required_services, discovered_logic["services"]),
        ]

        for logic_type, required_set, discovered_dict in logic_definitions:
            for name in required_set:
                # 📌 Look for the required name in our map of available functions.
                if name in logic_map:
                    discovered_dict[name] = logic_map[name]
                else:
                    # 💥 If an implementation is missing, raise a clear error.
                    raise ImplementationMissingError(
                        f"{logic_type} '{name}' is defined in the machine config "
                        "but a corresponding implementation was not found in the provided modules."
                    )

        total_found = sum(len(d) for d in discovered_logic.values())
        logger.info(
            "✨ Logic discovery complete. Bound %d implementations (%d actions, %d guards, %d services).",
            total_found,
            len(discovered_logic["actions"]),
            len(discovered_logic["guards"]),
            len(discovered_logic["services"]),
        )
        # 🎁 Return the fully populated MachineLogic object.
        return MachineLogic(**discovered_logic)
