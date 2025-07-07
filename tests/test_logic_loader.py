# tests/test_logic_loader.py

# -----------------------------------------------------------------------------
# 🧪 Test Suite: LogicLoader
# -----------------------------------------------------------------------------
# This suite provides comprehensive testing for the `LogicLoader` class, which
# is responsible for the automatic discovery of state machine logic. It verifies
# the singleton pattern, module registration, and the discovery process using
# module paths and direct module objects. It also ensures correct error
# handling for missing implementations and invalid inputs.
# -----------------------------------------------------------------------------

import logging
import os
import sys
import unittest
from types import ModuleType
from typing import Any, Dict

from src.xstate_statemachine import (
    ImplementationMissingError,
    InvalidConfigError,
    LogicLoader,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configure a logger for this test module to provide detailed output.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Test Helpers & Mocks
# -----------------------------------------------------------------------------
# These constants define a temporary Python module and a machine configuration
# to be used across multiple tests, adhering to the DRY principle.

# The name of the temporary Python module for testing.
_TEST_LOGIC_MODULE_NAME = "temp_logic_for_testing"

# The content of the temporary module, containing various logic functions.
_TEST_LOGIC_FILE_CONTENT = """
# Dummy logic functions for discovery tests.
def an_action(): pass
def a_guard(): return True
async def a_service(): return "data"
def anotherActionInCamel(): pass
def action_for_snake_case(): pass
"""

# A sample machine config that references all types of logic.
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


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestLogicLoader
# -----------------------------------------------------------------------------


class TestLogicLoader(unittest.TestCase):
    """
    Test suite for the `LogicLoader` class.

    This class contains test methods to validate every feature of the
    `LogicLoader`, including its singleton behavior, module registration,
    logic discovery mechanisms, and error handling paths.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """
        Creates a temporary logic module file once for all tests in this class.

        Args:
            None

        Returns:
            None
        """
        logger.info("Setting up test class: creating temporary module file.")
        # 📝 Create a temporary .py file with dummy logic functions.
        with open(f"{_TEST_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_LOGIC_FILE_CONTENT)
        # 📚 Ensure the current directory is in the Python path to allow importing.
        sys.path.insert(0, os.getcwd())

    @classmethod
    def tearDownClass(cls) -> None:
        """
        Removes the temporary logic module file after all tests are run.

        Args:
            None

        Returns:
            None
        """
        logger.info("Tearing down test class: removing temporary module file.")
        # 🧹 Clean up the temporary .py file and system path.
        os.remove(f"{_TEST_LOGIC_MODULE_NAME}.py")
        sys.path.pop(0)

    def tearDown(self) -> None:
        """
        Resets the LogicLoader singleton and unloads modules after each test.

        This ensures that tests are perfectly isolated and do not interfere
        with each other's state.

        Args:
            None

        Returns:
            None
        """
        # 🗑️ Reset the singleton to prevent state leakage between tests.
        LogicLoader._instance = None
        # 🗑️ Unload the module from memory if it was imported.
        if _TEST_LOGIC_MODULE_NAME in sys.modules:
            del sys.modules[_TEST_LOGIC_MODULE_NAME]

    def test_singleton_instance(self) -> None:
        """
        Should return the same LogicLoader instance on every call to get_instance.
        """
        logger.info("🚀 Testing LogicLoader singleton pattern...")
        # 🧪 Get two instances.
        instance1 = LogicLoader.get_instance()
        instance2 = LogicLoader.get_instance()

        # ✅ Assert that they are the exact same object.
        self.assertIs(instance1, instance2)
        logger.info(
            "✅ Singleton pattern verified: get_instance() returns the same object."
        )

    def test_discover_logic_from_string_path(self) -> None:
        """
        Should discover logic functions from a list of module paths (strings).
        """
        logger.info("🚀 Testing logic discovery via string path...")
        loader = LogicLoader()
        # 🧪 Act: Discover logic using the string path of the temporary module.
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, user_logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )

        # ✅ Assert that all required logic components were found.
        self.assertIn("an_action", logic.actions)
        self.assertIn("a_guard", logic.guards)
        self.assertIn("a_service", logic.services)
        logger.info("✅ Logic successfully discovered from string path.")

    def test_discover_logic_from_module_object(self) -> None:
        """
        Should discover logic functions from a list of imported module objects.
        """
        logger.info("🚀 Testing logic discovery via module object...")
        # 📚 Pre-import the module to get a reference to the object.
        import temp_logic_for_testing

        loader = LogicLoader()

        # 🧪 Act: Discover logic using the imported module object.
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, user_logic_modules=[temp_logic_for_testing]
        )

        # ✅ Assert that all required logic components were found.
        self.assertIn("an_action", logic.actions)
        self.assertIn("a_guard", logic.guards)
        self.assertIn("a_service", logic.services)
        logger.info("✅ Logic successfully discovered from module object.")

    def test_discover_logic_from_registered_module(self) -> None:
        """
        Should discover logic from a module that was pre-registered globally.
        """
        logger.info("🚀 Testing logic discovery via pre-registered module...")
        import temp_logic_for_testing

        loader = LogicLoader.get_instance()

        # 🔌 Register the module first.
        loader.register_logic_module(temp_logic_for_testing)
        # 🧪 Act: Discover logic without passing any modules dynamically.
        logic = loader.discover_and_build_logic(_MACHINE_CONFIG)

        # ✅ Assert logic was found from the global registry.
        self.assertIn("an_action", logic.actions)
        logger.info("✅ Logic successfully discovered from registered module.")

    def test_name_matching_for_camel_and_snake_case(self) -> None:
        """
        Should correctly map camelCase from config to snake_case in Python and vice-versa.
        """
        logger.info("🚀 Testing camelCase/snake_case name mapping...")
        import temp_logic_for_testing

        loader = LogicLoader()
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, user_logic_modules=[temp_logic_for_testing]
        )

        # ✅ camelCase in Python ('anotherActionInCamel') should be found by its direct name.
        self.assertIn("anotherActionInCamel", logic.actions)
        # ✅ camelCase in config ('actionForSnakeCase') should map to snake_case in Python.
        self.assertIn("actionForSnakeCase", logic.actions)
        # ✅ Verify the correct function object was mapped.
        self.assertIs(
            logic.actions["actionForSnakeCase"],
            temp_logic_for_testing.action_for_snake_case,
        )
        logger.info("✅ Naming conventions mapped successfully.")

    def test_raises_error_for_missing_implementation(self) -> None:
        """
        Should raise ImplementationMissingError if a referenced function is not found.
        """
        logger.info("🚀 Testing error for missing implementation...")
        loader = LogicLoader()
        faulty_config = {
            "id": "faulty",
            "initial": "a",
            "states": {"a": {"entry": ["nonExistentAction"]}},
        }

        # ❌ Assert that the correct exception is raised with a descriptive message.
        # ✨ CORRECTION: The expected regex now matches the more descriptive error message.
        with self.assertRaisesRegex(
            ImplementationMissingError,
            "Action 'nonExistentAction' is defined in the machine config",
        ):
            loader.discover_and_build_logic(
                faulty_config, user_logic_modules=[_TEST_LOGIC_MODULE_NAME]
            )
        logger.info("✅ Correctly raised ImplementationMissingError.")

    def test_raises_error_for_invalid_module_path(self) -> None:
        """
        Should raise ImportError if a module path string is invalid.
        """
        logger.info("🚀 Testing error for invalid module path...")
        loader = LogicLoader()

        # ❌ Assert that an ImportError is raised for a bad path.
        with self.assertRaises(ImportError):
            loader.discover_and_build_logic(
                _MACHINE_CONFIG,
                user_logic_modules=["invalid.path.does.not.exist"],
            )
        logger.info("✅ Correctly raised ImportError.")

    def test_raises_error_for_invalid_module_list_type(self) -> None:
        """
        Should raise TypeError if the logic_modules list contains an invalid type.
        """
        logger.info("🚀 Testing error for invalid type in logic_modules...")
        loader = LogicLoader()

        # ❌ Assert that a TypeError is raised when passing an integer instead of a module/string.
        with self.assertRaises(TypeError):
            loader.discover_and_build_logic(
                _MACHINE_CONFIG, user_logic_modules=[123]
            )
        logger.info("✅ Correctly raised TypeError.")
