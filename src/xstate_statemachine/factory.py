# src/xstate_statemachine/factory.py

# -----------------------------------------------------------------------------
# 🏭 Machine Factory
# -----------------------------------------------------------------------------
# This module provides a single entry point for creating a state machine
# instance from its configuration, applying the Factory design pattern.
# -----------------------------------------------------------------------------

from typing import Any, Dict, Optional, List, Union
from types import ModuleType  # ✨ NEW
from .models import MachineNode
from .machine_logic import MachineLogic
from .exceptions import InvalidConfigError
from .logger import logger
from .logic_loader import LogicLoader


def create_machine(
    config: Dict[str, Any],
    logic: Optional[MachineLogic] = None,
    # ♻️ REFACTORED: Updated type hint to allow module objects
    logic_modules: Optional[List[Union[str, ModuleType]]] = None,
) -> MachineNode:
    """
    Creates a state machine instance from a config and implementation logic.

    Args:
        config (Dict[str, Any]): The state machine's definition.
        logic (Optional[MachineLogic]): An explicit `MachineLogic` object. If
            provided, `logic_modules` are ignored.
        logic_modules (Optional[List[Union[str, ModuleType]]]): A list of module
            paths (str) or imported module objects for auto-discovery.

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
        logic_loader_instance = LogicLoader.get_instance()
        final_logic = logic_loader_instance.discover_and_build_logic(
            config, logic_modules
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
