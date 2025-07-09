# tests/test_logic_loader.py

# -----------------------------------------------------------------------------
# 🧪 Test Suite: LogicLoader
# -----------------------------------------------------------------------------
# This suite provides comprehensive testing for the `LogicLoader` class, which
# is responsible for the automatic discovery of state machine logic. It verifies
# the singleton pattern, module registration, and the discovery process using
# module paths, class instances, and direct module objects. It also ensures
# correct error handling for missing implementations and invalid inputs.
# -----------------------------------------------------------------------------

import logging
import os
import sys
import unittest
from types import ModuleType
from typing import Any, Dict

# ✅ FIX: Changed relative imports to absolute imports from the src package.
from src.xstate_statemachine import (
    ImplementationMissingError,
    InvalidConfigError,
    LogicLoader,
    MachineLogic,
    create_machine,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🛠️ Test Helpers & Mocks
# -----------------------------------------------------------------------------

_TEST_LOGIC_MODULE_NAME = "temp_logic_for_testing"
_TEST_LOGIC_FILE_CONTENT = """
# Dummy logic functions for discovery tests.
def an_action(): pass
def a_guard(): return True
async def a_service(): return "data"
def anotherActionInCamel(): pass
def action_for_snake_case(): pass
"""
_MACHINE_CONFIG = {
    "id": "test",
    "initial": "idle",
    "states": {
        "idle": {
            "on": {
                "EVENT": {
                    "target": "active",
                    "actions": [
                        "an_action",
                        "anotherActionInCamel",
                        "actionForSnakeCase",
                    ],
                    "guard": "a_guard",
                }
            }
        },
        "active": {"invoke": {"src": "a_service"}},
    },
}


class LogicProvider:
    """A simple class with methods to test instance-based discovery."""

    def provider_action(self):
        pass

    def provider_guard(self):
        return True


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestLogicLoader
# -----------------------------------------------------------------------------


class TestLogicLoader(unittest.TestCase):
    """Test suite for the `LogicLoader` class."""

    @classmethod
    def setUpClass(cls) -> None:
        """Creates a temporary logic module file for all tests."""
        with open(f"{_TEST_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_LOGIC_FILE_CONTENT)
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

    @classmethod
    def tearDownClass(cls) -> None:
        """Removes the temporary logic module file after all tests."""
        os.remove(f"{_TEST_LOGIC_MODULE_NAME}.py")
        if os.getcwd() in sys.path:
            sys.path.pop(0)

    def tearDown(self) -> None:
        """Resets the LogicLoader singleton after each test."""
        LogicLoader._instance = None
        if _TEST_LOGIC_MODULE_NAME in sys.modules:
            del sys.modules[_TEST_LOGIC_MODULE_NAME]

    def test_singleton_instance(self) -> None:
        """Should return the same LogicLoader instance on every call."""
        instance1 = LogicLoader.get_instance()
        instance2 = LogicLoader.get_instance()
        self.assertIs(instance1, instance2)

    def test_discover_logic_from_string_path(self) -> None:
        """Should discover logic from a list of module paths (strings)."""
        loader = LogicLoader()
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )
        self.assertIn("an_action", logic.actions)
        self.assertIn("a_guard", logic.guards)
        self.assertIn("a_service", logic.services)

    def test_discover_logic_from_module_object(self) -> None:
        """Should discover logic from a list of imported module objects."""
        import temp_logic_for_testing

        loader = LogicLoader()
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[temp_logic_for_testing]
        )
        self.assertIn("an_action", logic.actions)

    def test_discover_logic_from_class_instance(self) -> None:
        """Should discover methods from a provided class instance."""
        provider = LogicProvider()
        config = {
            "id": "p",
            "initial": "a",
            "states": {
                "a": {
                    "entry": "provider_action",
                    "on": {"G": {"target": "a", "guard": "provider_guard"}},
                }
            },
        }

        machine = create_machine(config, logic_providers=[provider])

        self.assertIn("provider_action", machine.logic.actions)
        self.assertIn("provider_guard", machine.logic.guards)
        self.assertEqual(
            machine.logic.actions["provider_action"], provider.provider_action
        )

    def test_discover_logic_from_registered_module(self) -> None:
        """Should discover logic from a globally pre-registered module."""
        import temp_logic_for_testing

        loader = LogicLoader.get_instance()
        loader.register_logic_module(temp_logic_for_testing)
        logic = loader.discover_and_build_logic(_MACHINE_CONFIG)
        self.assertIn("an_action", logic.actions)

    def test_name_matching_for_camel_and_snake_case(self) -> None:
        """Should correctly map between camelCase and snake_case names."""
        import temp_logic_for_testing

        loader = LogicLoader()
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[temp_logic_for_testing]
        )
        self.assertIn("anotherActionInCamel", logic.actions)
        self.assertIn("actionForSnakeCase", logic.actions)
        self.assertIs(
            logic.actions["actionForSnakeCase"],
            temp_logic_for_testing.action_for_snake_case,
        )

    def test_raises_error_for_missing_implementation(self) -> None:
        """Should raise error if a referenced function is not found."""
        loader = LogicLoader()
        faulty_config = {
            "id": "faulty",
            "initial": "a",
            "states": {"a": {"entry": ["nonExistentAction"]}},
        }
        with self.assertRaises(ImplementationMissingError):
            loader.discover_and_build_logic(
                faulty_config, logic_modules=[_TEST_LOGIC_MODULE_NAME]
            )

    def test_raises_error_for_invalid_module_path(self) -> None:
        """Should raise ImportError for an invalid module path string."""
        loader = LogicLoader()
        with self.assertRaises(ImportError):
            loader.discover_and_build_logic(
                _MACHINE_CONFIG, logic_modules=["invalid.path.does.not.exist"]
            )

    def test_raises_error_for_invalid_module_list_type(self) -> None:
        """Should raise TypeError if logic_modules list contains an invalid type."""
        loader = LogicLoader()
        with self.assertRaises(TypeError):
            loader.discover_and_build_logic(
                _MACHINE_CONFIG, logic_modules=[123]
            )


if __name__ == "__main__":
    unittest.main()
