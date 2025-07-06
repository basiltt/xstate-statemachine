# src/xstate_python/factory.py
from typing import Any, Dict
from .models import MachineNode
from .machine_logic import MachineLogic
from .exceptions import InvalidConfigError
from .logger import logger

# -----------------------------------------------------------------------------
# 🏭 Machine Factory
# -----------------------------------------------------------------------------
# This module provides a single entry point for creating a state machine
# instance from its configuration, applying the Factory design pattern.
# -----------------------------------------------------------------------------


def create_machine(
    config: Dict[str, Any], logic: MachineLogic = None
) -> MachineNode:
    """
    Creates a state machine instance from a JSON-like config and implementation logic.

    Args:
        config: The state machine's definition.
        logic: An object containing the implementations for all actions, guards, etc.

    Returns:
        The root node of the fully constructed state machine graph.

    Raises:
        InvalidConfigError: If the configuration is malformed.
    """
    if logic is None:
        logic = MachineLogic()

    machine_id = config.get("id")
    logger.info(f"🏭 Creating machine with id: '{machine_id}'")
    if (
        not isinstance(config, dict)
        or "states" not in config
        or not machine_id
    ):
        raise InvalidConfigError(
            "Invalid config: must be a dict with 'id' and 'states' keys."
        )

    return MachineNode(config, logic)
