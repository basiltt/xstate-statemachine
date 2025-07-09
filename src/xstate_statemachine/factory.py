# src/xstate_statemachine/factory.py

# -----------------------------------------------------------------------------
# 🏭 Machine Factory
# -----------------------------------------------------------------------------
# This module provides a single entry point for creating a state machine
# instance from its configuration, applying the Factory design pattern.
# -----------------------------------------------------------------------------

from typing import Any, Dict, Optional, List, Union
from types import ModuleType
from .models import MachineNode
from .machine_logic import MachineLogic
from .exceptions import InvalidConfigError
from .logger import logger
from .logic_loader import LogicLoader


def create_machine(
    config: Dict[str, Any],
    logic: Optional[MachineLogic] = None,
    logic_modules: Optional[List[Union[str, ModuleType]]] = None,
    logic_providers: Optional[List[Any]] = None,
) -> MachineNode:
    """
    Creates a state machine instance from a config and implementation logic.

    This factory supports three ways of providing logic, in order of priority:
    1.  **logic**: An explicit, pre-built `MachineLogic` object.
    2.  **logic_modules/logic_providers**: Lists of modules or class instances
        for automatic discovery of implementations.

    Args:
        config (Dict[str, Any]): The state machine's definition.
        logic (Optional[MachineLogic]): An explicit `MachineLogic` object.
        logic_modules (Optional[List[Union[str, ModuleType]]]): A list of modules
            or module paths for auto-discovery of functions.
        logic_providers (Optional[List[Any]]): A list of class instances for
            auto-discovery of methods.

    Returns:
        MachineNode: The root node of the fully constructed state machine graph.
    """
    final_logic: MachineLogic
    if logic:
        logger.info("🧠 Using explicitly provided MachineLogic instance.")
        final_logic = logic
    else:
        logger.info(
            "🤖 No explicit logic provided, attempting auto-discovery..."
        )
        loader = LogicLoader.get_instance()
        final_logic = loader.discover_and_build_logic(
            config,
            logic_modules=logic_modules,
            logic_providers=logic_providers,  # Pass providers to the loader
        )

    machine_id = config.get("id")
    logger.info("🏭 Creating machine with id: '%s'", machine_id)
    if (
        not isinstance(config, dict)
        or "states" not in config
        or not machine_id
    ):
        raise InvalidConfigError(
            "Invalid config: must be a dict with 'id' and 'states' keys."
        )

    return MachineNode(config, final_logic)
