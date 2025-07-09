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
    """Creates a state machine instance from a config and implementation logic."""
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
            logic_providers=logic_providers,
        )

    machine_id = config.get("id")
    # FIX: Add explicit validation for the machine ID type.
    if not isinstance(machine_id, str):
        raise InvalidConfigError(
            "Machine configuration 'id' must be a string."
        )

    logger.info("🏭 Creating machine with id: '%s'", machine_id)
    if "states" not in config:
        raise InvalidConfigError(
            "Invalid config: must be a dict with 'id' and 'states' keys."
        )

    return MachineNode(config, final_logic)
