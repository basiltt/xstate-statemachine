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
from types import ModuleType
from typing import Any, Dict, List, Optional, Union

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .exceptions import InvalidConfigError
from .logic_loader import LogicLoader
from .logger import logger
from .machine_logic import MachineLogic
from .models import MachineNode


# -----------------------------------------------------------------------------
# 🏭 Factory Function
# -----------------------------------------------------------------------------


def create_machine(
    config: Dict[str, Any],
    *,
    logic: Optional[MachineLogic] = None,
    logic_modules: Optional[List[Union[str, ModuleType]]] = None,
    logic_providers: Optional[List[Any]] = None,
) -> MachineNode:
    """Creates, validates, and assembles a state machine instance.

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
    return MachineNode(config, final_logic)
