# tests/test_factory.py

# -----------------------------------------------------------------------------
# 🧪 Test Suite: Machine Factory (`create_machine`)
# -----------------------------------------------------------------------------
# This suite rigorously verifies the `create_machine` factory function.
# It ensures the correct creation of `MachineNode` instances from valid
# configurations and validates both explicit logic binding and the new
# automatic logic discovery feature via the `logic_modules` parameter.
# -----------------------------------------------------------------------------

import logging
import os
import sys
import unittest
from typing import Any, Callable, Dict

from src.xstate_statemachine import (
    InvalidConfigError,
    LogicLoader,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# -----------------------------------------------------------------------------
# 🛠️ Test Helpers & Mocks
# -----------------------------------------------------------------------------

# Define a temporary Python module for testing the logic discovery feature.
_TEST_FACTORY_LOGIC_MODULE_NAME = "temp_factory_logic_module"
_TEST_FACTORY_LOGIC_CONTENT = "def factory_action(): pass"

# Define a sample machine config that requires the logic from the temp module.
_FACTORY_MACHINE_CONFIG = {
    "id": "factory_test_machine",
    "initial": "active",
    "states": {"active": {"entry": ["factory_action"]}},
}


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestFactory
# -----------------------------------------------------------------------------


class TestFactory(unittest.TestCase):
    """
    Test suite for the `create_machine` factory function, covering basic
    creation, error handling, and logic discovery.
    """

    # Type hints for instance variables
    valid_config: Dict[str, Any]
    explicit_logic: MachineLogic

    def setUp(self) -> None:
        """
        Initialize common test data and create a temporary logic module file.

        This method is called before each test, ensuring a clean state.
        It sets up a minimal valid config for basic tests and writes a
        temporary .py file to disk for testing the logic discovery feature.
        """
        logger.debug("Setting up for a new factory test...")
        # 🧍 A minimal valid machine config for basic tests.
        self.valid_config = {
            "id": "test_machine",
            "initial": "idle",
            "states": {"idle": {}},
        }
        # 🧠 An explicit MachineLogic instance for priority tests.
        self.explicit_logic = MachineLogic()

        # 📝 Create a temporary .py file with a dummy logic function.
        with open(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_FACTORY_LOGIC_CONTENT)

        # 📚 Ensure the current directory is in the Python path to allow importing.
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

    def tearDown(self) -> None:
        """
        Clean up resources after each test.

        This method removes the temporary module file and resets the
        LogicLoader's singleton instance to ensure test isolation.
        """
        logger.debug("Tearing down factory test.")
        # 🗑️ Reset the singleton to prevent state leakage between tests.
        LogicLoader._instance = None

        # 🗑️ Unload the module from memory if it was imported.
        if _TEST_FACTORY_LOGIC_MODULE_NAME in sys.modules:
            del sys.modules[_TEST_FACTORY_LOGIC_MODULE_NAME]

        # 🗑️ Remove the temporary .py file.
        if os.path.exists(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py"):
            os.remove(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py")

    # -------------------------------------------------------------------------
    # 🔩 Core Creation and Validation Tests
    # -------------------------------------------------------------------------

    def test_create_machine_with_explicit_logic(self) -> None:
        """
        Should successfully create a MachineNode with an explicit logic object.

        This test asserts that when `create_machine` is called with a pre-built
        `MachineLogic` object, the resulting machine instance correctly
        references that exact object.
        """
        logger.info(
            "🚀 Testing successful machine creation with explicit logic..."
        )
        # 🧪 Act: Call the factory with a valid config and an explicit logic object.
        machine = create_machine(self.valid_config, self.explicit_logic)

        # ✅ Verify type: The returned object must be an instance of MachineNode.
        self.assertIsInstance(machine, MachineNode)
        # ✅ Verify ID: The machine's ID should match the one in the config.
        self.assertEqual(machine.id, "test_machine")
        # ✅ Verify Logic Assignment: The machine's logic must be the provided instance.
        self.assertIs(machine.logic, self.explicit_logic)

        logger.info("✅ Machine created successfully with explicit logic.")

    def test_create_machine_with_no_logic_falls_back_to_empty(self) -> None:
        """
        Should create an empty `MachineLogic` object if none is provided.

        This test ensures that if the `logic` and `logic_modules` arguments are
        omitted, the factory provides a default, empty `MachineLogic` object,
        allowing machines without any custom logic to be created without error.
        """
        logger.info(
            "🚀 Testing fallback to empty logic when none is provided..."
        )
        # 🧪 Act: Call the factory without providing any logic.
        machine = create_machine(self.valid_config)

        # ✅ Verify Default Logic: A default MachineLogic object should be present.
        self.assertIsNotNone(machine.logic)
        self.assertIsInstance(machine.logic, MachineLogic)
        # ✅ Verify it's empty.
        self.assertEqual(len(machine.logic.actions), 0)
        self.assertEqual(len(machine.logic.guards), 0)
        self.assertEqual(len(machine.logic.services), 0)

        logger.info(
            "✅ Machine created successfully with a default empty MachineLogic."
        )

    def test_raises_error_for_config_missing_id(self) -> None:
        """
        Should raise `InvalidConfigError` if the 'id' key is missing.
        """
        logger.info("🚀 Testing error handling for missing 'id' key...")
        # ❌ Define an invalid configuration missing the 'id' key.
        invalid_config = {"initial": "idle", "states": {"idle": {}}}

        # 🔍 Assert: Expect an InvalidConfigError.
        with self.assertRaisesRegex(
            InvalidConfigError, "'id' and 'states' keys"
        ):
            create_machine(invalid_config)
        logger.info("✅ Correctly raised InvalidConfigError for missing 'id'.")

    def test_raises_error_for_config_missing_states(self) -> None:
        """
        Should raise `InvalidConfigError` if the 'states' key is missing.
        """
        logger.info("🚀 Testing error handling for missing 'states' key...")
        # ❌ Define an invalid configuration missing the 'states' key.
        invalid_config = {"id": "test_machine", "initial": "idle"}

        # 🔍 Assert: Expect an InvalidConfigError.
        with self.assertRaisesRegex(
            InvalidConfigError, "'id' and 'states' keys"
        ):
            create_machine(invalid_config)
        logger.info(
            "✅ Correctly raised InvalidConfigError for missing 'states'."
        )

    # -------------------------------------------------------------------------
    # ✨ Tests for Automatic Logic Discovery Feature
    # -------------------------------------------------------------------------

    def test_create_machine_with_logic_modules_string(self) -> None:
        """
        Should auto-discover logic when `logic_modules` is a list of strings.
        """
        logger.info(
            "🚀 Testing create_machine with logic_modules (string path)..."
        )
        # 🧪 Act: Create a machine using the auto-discovery feature with a string path.
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
        )

        # ✅ Assert that the machine's logic was populated correctly.
        self.assertIn("factory_action", machine.logic.actions)
        self.assertIsInstance(
            machine.logic.actions["factory_action"], Callable
        )
        logger.info(
            "✅ Logic successfully discovered via string path in factory."
        )

    def test_create_machine_with_logic_modules_object(self) -> None:
        """
        Should auto-discover logic when `logic_modules` is a list of module objects.
        """
        logger.info(
            "🚀 Testing create_machine with logic_modules (module object)..."
        )
        # 📚 Import the module object first.
        import temp_factory_logic_module

        # 🧪 Act: Create a machine using the auto-discovery feature with the module object.
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic_modules=[temp_factory_logic_module],
        )

        # ✅ Assert that the machine's logic was populated correctly.
        self.assertIn("factory_action", machine.logic.actions)
        self.assertIs(
            machine.logic.actions["factory_action"],
            temp_factory_logic_module.factory_action,
        )
        logger.info(
            "✅ Logic successfully discovered via module object in factory."
        )

    def test_create_machine_explicit_logic_has_priority(self) -> None:
        """
        Should use explicit `logic` object even if `logic_modules` is provided.
        """
        logger.info(
            "🚀 Testing that explicit logic overrides auto-discovery..."
        )
        # 🧠 Create an explicit logic object with a mock action.
        mock_action = lambda: "mock"  # noqa: E731
        explicit_logic = MachineLogic(actions={"factory_action": mock_action})

        # 🧪 Act: Call create_machine with BOTH explicit logic and logic_modules.
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic=explicit_logic,
            logic_modules=[
                _TEST_FACTORY_LOGIC_MODULE_NAME
            ],  # This should be ignored.
        )

        # ✅ Assert that the machine is using the action from the explicit logic object,
        # not the one from the auto-discovered module.
        self.assertIs(machine.logic, explicit_logic)
        self.assertIs(machine.logic.actions["factory_action"], mock_action)
        logger.info(
            "✅ Factory correctly prioritized explicit logic over logic_modules."
        )
