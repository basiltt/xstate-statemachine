"""
tests/test_factory.py
---------------------
Refactored test suite for the Machine factory (`create_machine`).
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    InvalidConfigError,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import MachineNode

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# To enable console output, uncomment and configure the handler below:
# handler = logging.StreamHandler()
# handler.setLevel(logging.INFO)
# handler.setFormatter(
#     logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
# )
# logger.addHandler(handler)


# -----------------------------------------------------------------------------
# Test Suite: Machine Factory
# -----------------------------------------------------------------------------
class TestFactory(unittest.TestCase):
    """
    Test suite for the `create_machine` factory function.

    This suite rigorously verifies the correct creation of `MachineNode` instances
    from valid configuration dictionaries and ensures robust error handling
    for various types of invalid configurations. It acts as a gatekeeper for
    the structural integrity of state machine definitions.
    """

    # Type hints for instance variables
    valid_config: Dict[str, Any]
    logic: MachineLogic

    def setUp(self) -> None:
        """
        Initialize a standard valid machine configuration and a `MachineLogic`
        object for reuse across tests.

        This `setUp` method is called before each test method, ensuring a
        fresh and consistent state for the `valid_config` and `logic` attributes.

        Args:
            None

        Returns:
            None
        """
        logger.info(
            "🚀 Setting up valid machine config and logic for tests..."
        )
        # Minimal valid machine configuration required for successful creation
        self.valid_config = {
            "id": "test_machine",
            "initial": "idle",
            "states": {"idle": {}},
        }
        # A default MachineLogic instance for assignment tests
        self.logic = MachineLogic()
        logger.debug(
            "Setup complete. valid_config: %s, logic: %s",
            self.valid_config,
            self.logic,
        )

    def test_create_machine_success(self) -> None:
        """
        Should successfully create a MachineNode instance from a valid configuration.

        This test asserts that when `create_machine` is called with a well-formed
        dictionary and `MachineLogic`, it returns an instance of `MachineNode`
        with the correct ID and that the provided `MachineLogic` object is
        properly assigned to the machine's `logic` attribute.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: If the created object is not a `MachineNode`,
                            if its ID doesn't match, or if the `logic`
                            object is not correctly assigned.
        """
        logger.info(
            "🚀 Testing successful machine creation with provided logic..."
        )
        # 🧪 Act: Call the factory function with valid config and logic
        machine = create_machine(self.valid_config, self.logic)

        # ✅ Verify type: The returned object must be an instance of MachineNode
        self.assertIsInstance(
            machine,
            MachineNode,
            "Created object should be an instance of MachineNode",
        )
        # ✅ Verify ID: The machine's ID should match the one in the config
        self.assertEqual(
            machine.id,
            "test_machine",
            "Machine ID should match 'test_machine'",
        )
        # ✅ Verify Logic Assignment: The machine's logic should be the provided instance
        self.assertIs(
            machine.logic,
            self.logic,
            "Machine's logic should be the provided MachineLogic instance",
        )
        logger.info(
            "✅ Machine created successfully with correct ID and logic assignment."
        )

    def test_create_machine_with_default_logic(self) -> None:
        """
        Should create a default `MachineLogic` object if none is explicitly provided.

        This test ensures the convenience feature of the `create_machine` factory:
        if the `logic` argument is omitted, the factory should automatically
        instantiate and assign a default `MachineLogic` object to the created machine.

        Args:
            None

        Returns:
            None

        Raises:
            AssertionError: If the `logic` attribute is `None` or not an instance
                            of `MachineLogic` when no logic is provided.
        """
        logger.info(
            "🚀 Testing machine creation with automatic default MachineLogic..."
        )
        # 🧪 Act: Call the factory function without providing MachineLogic
        machine = create_machine(self.valid_config)

        # ✅ Verify Default Logic: A default MachineLogic object should be present
        self.assertIsNotNone(
            machine.logic,
            "Machine's logic should not be None when no logic is provided",
        )
        self.assertIsInstance(
            machine.logic,
            MachineLogic,
            "Machine's logic should be an instance of MachineLogic",
        )
        logger.info(
            "✅ Machine created successfully with a default MachineLogic instance."
        )

    def test_raises_error_for_config_missing_id(self) -> None:
        """
        Should raise `InvalidConfigError` if the 'id' key is missing from the configuration.

        This test enforces a critical validation rule: every machine definition
        must have an 'id' for proper identification, state resolution, and
        overall machine functionality.

        Args:
            None

        Returns:
            None

        Raises:
            InvalidConfigError: Specifically when the 'id' key is absent in the config.
        """
        logger.info(
            "🚀 Testing error handling for missing 'id' key in machine configuration..."
        )
        # ❌ Define an invalid configuration missing the 'id' key
        invalid_config = {"initial": "idle", "states": {"idle": {}}}
        logger.debug("Invalid config (missing 'id'): %s", invalid_config)

        # 🔍 Assert: Expect an InvalidConfigError with a specific regex message
        with self.assertRaisesRegex(
            InvalidConfigError, "must be a dict with 'id' and 'states' keys"
        ):
            create_machine(
                invalid_config
            )  # 🧪 Act: Attempt to create machine with invalid config
        logger.info("✅ Correctly raised InvalidConfigError for missing 'id'.")

    def test_raises_error_for_config_missing_states(self) -> None:
        """
        Should raise `InvalidConfigError` if the 'states' key is missing from the configuration.

        This test validates another crucial configuration requirement: a machine
        must define its 'states' for it to have any behavior or structure.

        Args:
            None

        Returns:
            None

        Raises:
            InvalidConfigError: Specifically when the 'states' key is absent in the config.
        """
        logger.info(
            "🚀 Testing error handling for missing 'states' key in machine configuration..."
        )
        # ❌ Define an invalid configuration missing the 'states' key
        invalid_config = {"id": "test_machine", "initial": "idle"}
        logger.debug("Invalid config (missing 'states'): %s", invalid_config)

        # 🔍 Assert: Expect an InvalidConfigError with a specific regex message
        with self.assertRaisesRegex(
            InvalidConfigError, "must be a dict with 'id' and 'states' keys"
        ):
            create_machine(
                invalid_config
            )  # 🧪 Act: Attempt to create machine with invalid config
        logger.info(
            "✅ Correctly raised InvalidConfigError for missing 'states'."
        )
