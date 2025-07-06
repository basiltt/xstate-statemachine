# tests/test_factory.py
import unittest
from typing import Any, Dict

from src.xstate_machine import InvalidConfigError, MachineLogic, create_machine
from src.xstate_machine.models import MachineNode


# -----------------------------------------------------------------------------
# 🧪 Test Suite for the Machine Factory
# -----------------------------------------------------------------------------
# This suite focuses exclusively on the `create_machine` function from the
# factory module. It verifies that the factory correctly constructs a machine
# from a valid configuration and rejects malformed configurations with the
# appropriate error, ensuring robust input validation.
# -----------------------------------------------------------------------------


class TestFactory(unittest.TestCase):
    """Test suite for the create_machine factory function."""

    def setUp(self) -> None:
        """Set up common resources for the tests.

        This method runs before each test, providing a clean, valid machine
        configuration and a standard logic object.
        """
        # 📝 Define a minimal, valid machine configuration for reuse.
        self.valid_config: Dict[str, Any] = {
            "id": "test_machine",
            "initial": "idle",
            "states": {"idle": {}},
        }
        # 🧠 Define a logic object to test assignment.
        self.logic = MachineLogic()

    def test_create_machine_success(self) -> None:
        """Should successfully create a MachineNode from a valid configuration.

        This test ensures that given a valid dictionary and logic, the factory
        produces a correctly instantiated `MachineNode` with the logic assigned.
        """
        # 🚀 Act: Call the factory with a valid configuration.
        machine = create_machine(self.valid_config, self.logic)

        # ✅ Assert: The factory returns a valid MachineNode instance.
        self.assertIsInstance(machine, MachineNode)
        self.assertEqual(machine.id, "test_machine")
        self.assertIs(machine.logic, self.logic)

    def test_create_machine_with_default_logic(self) -> None:
        """Should create a default MachineLogic object if none is provided.

        This test verifies that the factory is convenient to use and does not
        require a `MachineLogic` object if the machine has no implemented
        actions, guards, or services.
        """
        # 🚀 Act: Call the factory without providing a logic object.
        machine = create_machine(self.valid_config)

        # ✅ Assert: The resulting machine has a new, default MachineLogic instance.
        self.assertIsNotNone(machine.logic)
        self.assertIsInstance(machine.logic, MachineLogic)

    def test_raises_error_for_config_missing_id(self) -> None:
        """Should raise InvalidConfigError if the 'id' key is missing.

        A machine's ID is mandatory for identification and state resolution.
        This test ensures the factory enforces this requirement.
        """
        # Ⓐ Arrange: Create a configuration that is missing the 'id' key.
        invalid_config = {"initial": "idle", "states": {"idle": {}}}

        # 🚀 Act & ✅ Assert: Check that calling the factory raises the correct error.
        with self.assertRaisesRegex(
            InvalidConfigError, "must be a dict with 'id' and 'states' keys"
        ):
            create_machine(invalid_config)

    def test_raises_error_for_config_missing_states(self) -> None:
        """Should raise InvalidConfigError if the 'states' key is missing.

        A state machine is defined by its states. A configuration without a
        'states' object is fundamentally invalid.

        """
        # Ⓐ Arrange: Create a configuration that is missing the 'states' key.
        invalid_config = {"id": "test_machine", "initial": "idle"}

        # 🚀 Act & ✅ Assert: Check that calling the factory raises the correct error.
        with self.assertRaisesRegex(
            InvalidConfigError, "must be a dict with 'id' and 'states' keys"
        ):
            create_machine(invalid_config)
