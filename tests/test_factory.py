# tests/test_factory.py

# -----------------------------------------------------------------------------
# 🧪 Test Suite: Machine Factory (`create_machine`)
# -----------------------------------------------------------------------------
# This suite rigorously verifies the `create_machine` factory function.
# It ensures the correct creation of `MachineNode` instances from valid
# configurations and validates both explicit logic binding and the new
# automatic logic discovery features.
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

# -----------------------------------------------------------------------------
# 🛠️ Test Helpers & Mocks
# -----------------------------------------------------------------------------

_TEST_FACTORY_LOGIC_MODULE_NAME = "temp_factory_logic_module"
_TEST_FACTORY_LOGIC_CONTENT = "def factory_action(): pass"


class MyLogicProvider:
    def provider_action(self):
        pass


_FACTORY_MACHINE_CONFIG = {
    "id": "factory_test_machine",
    "initial": "active",
    "states": {"active": {"entry": ["factory_action"]}},
}
_PROVIDER_MACHINE_CONFIG = {
    "id": "provider_test_machine",
    "initial": "active",
    "states": {"active": {"entry": ["provider_action"]}},
}


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestFactory
# -----------------------------------------------------------------------------


class TestFactory(unittest.TestCase):
    """Test suite for the `create_machine` factory function."""

    def setUp(self) -> None:
        """Initialize common test data and create a temporary logic module file."""
        self.valid_config = {
            "id": "test_machine",
            "initial": "idle",
            "states": {"idle": {}},
        }
        self.explicit_logic = MachineLogic()
        with open(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_FACTORY_LOGIC_CONTENT)
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

    def tearDown(self) -> None:
        """Clean up resources after each test."""
        LogicLoader._instance = None
        if _TEST_FACTORY_LOGIC_MODULE_NAME in sys.modules:
            del sys.modules[_TEST_FACTORY_LOGIC_MODULE_NAME]
        if os.path.exists(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py"):
            os.remove(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py")

    # -------------------------------------------------------------------------
    # 🔩 Core Creation and Validation Tests
    # -------------------------------------------------------------------------

    def test_create_machine_with_explicit_logic(self) -> None:
        """Should successfully create a MachineNode with an explicit logic object."""
        machine = create_machine(self.valid_config, logic=self.explicit_logic)
        self.assertIsInstance(machine, MachineNode)
        self.assertEqual(machine.id, "test_machine")
        self.assertIs(machine.logic, self.explicit_logic)

    def test_create_machine_with_no_logic_falls_back_to_empty(self) -> None:
        """Should create an empty `MachineLogic` object if none is provided."""
        machine = create_machine(self.valid_config)
        self.assertIsNotNone(machine.logic)
        self.assertEqual(len(machine.logic.actions), 0)

    def test_raises_error_for_config_missing_id(self) -> None:
        """Should raise `InvalidConfigError` if the 'id' key is missing."""
        invalid_config = {"initial": "idle", "states": {"idle": {}}}
        # ✅ FIX: Updated regex to match the more specific error from MachineNode.
        with self.assertRaisesRegex(
            InvalidConfigError, "Machine configuration must have a root 'id'."
        ):
            create_machine(invalid_config)

    def test_raises_error_for_config_missing_states(self) -> None:
        """Should raise `InvalidConfigError` if the 'states' key is missing."""
        invalid_config = {"id": "test_machine", "initial": "idle"}
        with self.assertRaisesRegex(
            InvalidConfigError, "'id' and 'states' keys"
        ):
            create_machine(invalid_config)

    # -------------------------------------------------------------------------
    # ✨ Tests for Automatic Logic Discovery Feature
    # -------------------------------------------------------------------------

    def test_create_machine_with_logic_modules_string(self) -> None:
        """Should auto-discover logic when `logic_modules` is a list of strings."""
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
        )
        self.assertIn("factory_action", machine.logic.actions)
        self.assertTrue(
            isinstance(machine.logic.actions["factory_action"], Callable)
        )

    def test_create_machine_with_logic_modules_object(self) -> None:
        """Should auto-discover logic when `logic_modules` is a list of module objects."""
        import temp_factory_logic_module

        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic_modules=[temp_factory_logic_module],
        )
        self.assertIn("factory_action", machine.logic.actions)
        self.assertIs(
            machine.logic.actions["factory_action"],
            temp_factory_logic_module.factory_action,
        )

    def test_create_machine_with_logic_providers(self) -> None:
        """✨ NEW: Should auto-discover logic when `logic_providers` is used."""
        logic_provider_instance = MyLogicProvider()
        machine = create_machine(
            config=_PROVIDER_MACHINE_CONFIG,
            logic_providers=[logic_provider_instance],
        )
        self.assertIn("provider_action", machine.logic.actions)
        # ✅ FIX: Use assertEqual to compare bound methods for equivalence.
        self.assertEqual(
            machine.logic.actions["provider_action"],
            logic_provider_instance.provider_action,
        )

    def test_create_machine_explicit_logic_has_priority(self) -> None:
        """Should use explicit `logic` object even if other discoverable logic is provided."""
        mock_action = lambda: "mock"  # noqa: E731
        explicit_logic = MachineLogic(actions={"factory_action": mock_action})
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic=explicit_logic,
            logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
            logic_providers=[MyLogicProvider()],
        )
        self.assertIs(machine.logic, explicit_logic)
        self.assertIs(machine.logic.actions["factory_action"], mock_action)
