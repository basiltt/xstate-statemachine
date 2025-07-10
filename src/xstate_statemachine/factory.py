# src/xstate_statemachine/factory.py

# -----------------------------------------------------------------------------
# 🏭 Machine Factory
# -----------------------------------------------------------------------------
# This module provides a single, convenient entry point for creating a state
# machine instance from its configuration and business logic. It applies the
# Factory Method design pattern to decouple the client from the complex
# process of assembling the machine's configuration (`config`) and its
# executable logic (`MachineLogic`).
#
# This simplifies the user experience and centralizes the machine
# creation process, ensuring consistency and validation.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Imports
# -----------------------------------------------------------------------------
from types import ModuleType
from typing import Any, Dict, List, Optional, Union

# Local imports for core components and exceptions
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
            JSON or YAML file. Must contain 'id' and 'states' keys.
        logic: An optional, pre-constructed `MachineLogic` instance
            containing all required actions, guards, and services. If provided,
            this takes precedence over auto-discovery.
        logic_modules: An optional list of Python modules or import
            strings (e.g., 'my_app.logic.actions'). The factory will search
            these modules for functions to satisfy the machine's logic
            requirements.
        logic_providers: An optional list of class instances. The
            factory will search the methods of these objects to find the
            required logic implementations.

    Returns:
        A fully constructed and validated `MachineNode` instance, ready to be
        passed to an interpreter.

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

        >>> # 1. With explicit logic
        >>> from xstate_statemachine.machine_logic import MachineLogic
        >>> my_logic = MachineLogic(actions={"my_action": lambda: print("Action!")})
        >>> machine = create_machine(my_config, logic=my_logic)

        >>> # 2. With auto-discovery from a hypothetical module.
        >>> # Assume you have a file 'my_actions.py' with:
        >>> # def my_action():
        >>> #     print("Action from module!")
        >>> # You could then pass its name as a string:
        >>> # machine = create_machine(my_config, logic_modules=["my_actions"])

        >>> # 3. With auto-discovery from a provider class
        >>> class LogicProvider:
        ...     def my_action(self):
        ...         print(self, "Action from provider!")
        ...         print("Action from provider!")
        ...
        >>> provider = LogicProvider()
        >>> machine = create_machine(my_config, logic_providers=[provider])
    """
    # 🧠 Determine the source of the business logic.
    final_logic: MachineLogic
    if logic:
        # ✅ Use the explicitly provided logic instance. This is the most direct path.
        logger.info("🧠 Using explicitly provided MachineLogic instance.")
        final_logic = logic
    else:
        # 🤖 No explicit logic provided, so we engage the auto-discovery process.
        logger.info(
            "🤖 Attempting auto-discovery of actions, guards, and services..."
        )
        # The LogicLoader uses a Singleton pattern to ensure a single instance.
        loader = LogicLoader.get_instance()
        final_logic = loader.discover_and_build_logic(
            config,
            logic_modules=logic_modules,
            logic_providers=logic_providers,
        )

    # 🧪 Validate the core structure of the provided configuration.
    logger.info("🕵️ Validating machine configuration...")
    machine_id = config.get("id")

    # The machine ID is crucial for identification, logging, and event routing.
    if not isinstance(machine_id, str):
        logger.error(
            "❌ Machine configuration validation failed: 'id' is missing or not a string."
        )
        raise InvalidConfigError(
            "Machine configuration 'id' must be a string."
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
        "✅ Configuration validated successfully for machine '%s'.", machine_id
    )

    # 🏗️ Construct the final MachineNode instance.
    logger.info("🏭 Creating machine with id: '%s'", machine_id)
    return MachineNode(config, final_logic)
