# /tests/test_logic_loader.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: LogicLoader
# -----------------------------------------------------------------------------
# This module contains the test suite for the `LogicLoader` class, a core
# component responsible for the automatic discovery and binding of state machine
# logic (actions, guards, and services).
#
# The tests are designed to be comprehensive, covering:
#   - The Singleton pattern implementation (`get_instance`).
#   - Logic discovery from various sources:
#       - Module paths (strings).
#       - Imported module objects.
#       - Class instances (providers).
#       - Globally registered modules.
#   - Name resolution strategies, including camelCase to snake_case mapping.
#   - Conflict resolution when logic is defined in multiple sources.
#   - Robust error handling for missing implementations and invalid inputs.
#   - Edge cases to ensure stability and predictability.
#
# Each test is isolated to prevent side effects, with careful management of
# temporary files and the Python import system.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import importlib
import inspect
import logging
import os
import sys
import unittest
from typing import Any, Dict, Set, Tuple

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    ImplementationMissingError,
    InvalidConfigError,
    LogicLoader,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import MachineNode

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Set up a detailed logger to provide insight into the test execution flow.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🛠️ Test Helpers & Mocks
# -----------------------------------------------------------------------------

# A temporary module for general logic discovery tests.
_TEST_LOGIC_MODULE_NAME = "temp_logic_for_testing"
_TEST_LOGIC_FILE_CONTENT = """
# Dummy logic functions for discovery tests.
def an_action(): pass
def a_guard(): return True
async def a_service(): return "data"
def anotherActionInCamel(): pass
def action_for_snake_case(): pass
"""

# A generic machine configuration that requires various logic implementations.
_MACHINE_CONFIG: Dict[str, Any] = {
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

# A temporary module specifically for factory/provider conflict tests.
_TEST_FACTORY_LOGIC_MODULE_NAME = "temp_factory_logic_module"
_TEST_FACTORY_LOGIC_CONTENT = "def factory_action(): pass"

# Machine config referencing the factory action.
_FACTORY_MACHINE_CONFIG: Dict[str, Any] = {  # noqa
    "id": "factory_test_machine",
    "initial": "active",
    "states": {"active": {"entry": ["factory_action"]}},
}

# Machine config referencing the provider action.
_PROVIDER_MACHINE_CONFIG: Dict[str, Any] = {
    "id": "provider_test_machine",
    "initial": "active",
    "states": {"active": {"entry": ["provider_action"]}},
}


class LogicProvider:
    """A simple class with methods to test instance-based logic discovery.

    This class demonstrates how the `LogicLoader` can inspect an object
    and bind its public methods as implementations for actions and guards.
    """

    def provider_action(self) -> None:
        """A sample action method."""
        pass

    def provider_guard(self) -> bool:  # noqa
        """A sample guard method."""
        return True


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestLogicLoader
# -----------------------------------------------------------------------------


class TestLogicLoader(unittest.TestCase):
    """Verifies all functionality of the LogicLoader singleton.

    This test suite ensures the loader correctly implements the Singleton
    pattern, discovers logic from all supported source types, handles naming
    conventions and conflicts, and raises appropriate errors for invalid
    configurations or missing implementations.
    """

    # -------------------------------------------------------------------------
    # ♻️ Test Lifecycle Methods
    # -------------------------------------------------------------------------

    @classmethod
    def setUpClass(cls) -> None:
        """Creates a temporary logic module file available to all tests.

        This runs once before any tests in the class. It writes a temporary
        Python file to disk and ensures its directory is in the system path,
        making it importable by the tests.
        """
        logger.info("🛠️ Creating temporary logic module for the test class...")
        with open(f"{_TEST_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_LOGIC_FILE_CONTENT)
        # Ensure the current directory is on the path for imports.
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

    @classmethod
    def tearDownClass(cls) -> None:
        """Removes the temporary logic module file after all tests are run.

        This runs once after all tests in the class have completed, cleaning
        up the file created in `setUpClass`.
        """
        logger.info("🗑️ Removing temporary logic module for the test class...")
        os.remove(f"{_TEST_LOGIC_MODULE_NAME}.py")
        if os.getcwd() in sys.path:
            # Clean up the path modification.
            sys.path.pop(0)

    def tearDown(self) -> None:
        """Resets the LogicLoader singleton and caches after each test.

        This instance method runs after every single test, ensuring a clean
        slate and preventing state from leaking between tests. It resets the
        singleton instance and unloads the temporary module from memory.
        """
        logger.info("🧹 Resetting LogicLoader singleton for next test...")
        LogicLoader._instance = None
        # Unload the module from Python's cache if it was imported.
        if _TEST_LOGIC_MODULE_NAME in sys.modules:
            del sys.modules[_TEST_LOGIC_MODULE_NAME]

    # -------------------------------------------------------------------------
    # ⚙️ Core Singleton and Discovery Tests
    # -------------------------------------------------------------------------

    def test_singleton_instance(self) -> None:
        """Should return the same LogicLoader instance on every call."""
        logger.info("🧪 Testing LogicLoader follows the Singleton pattern.")
        # 🚀 Act: Get the instance twice.
        instance1 = LogicLoader.get_instance()
        instance2 = LogicLoader.get_instance()
        # ✅ Assert: Both variables should point to the exact same object.
        self.assertIs(instance1, instance2)

    def test_discover_logic_from_string_path(self) -> None:
        """Should discover logic from a list of module paths (strings)."""
        logger.info("🧪 Testing logic discovery from module name strings.")
        # 📋 Arrange
        loader = LogicLoader()
        # 🚀 Act: Discover logic using the temporary module's name.
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )
        # ✅ Assert: All relevant functions from the module should be categorized.
        self.assertIn("an_action", logic.actions)
        self.assertIn("a_guard", logic.guards)
        self.assertIn("a_service", logic.services)

    def test_discover_logic_from_module_object(self) -> None:
        """Should discover logic from a list of imported module objects."""
        logger.info("🧪 Testing logic discovery from module objects.")
        # 📋 Arrange: Import the module directly.
        # ✅ FIX: Ignore the type checker warning. This module is created dynamically
        # by the test suite's setUpClass method and will exist at runtime.
        import temp_logic_for_testing  # type: ignore

        loader = LogicLoader()
        # 🚀 Act: Discover logic passing the module object.
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[temp_logic_for_testing]
        )
        # ✅ Assert: The action is successfully found.
        self.assertIn("an_action", logic.actions)

    def test_discover_logic_from_class_instance(self) -> None:
        """Should discover methods from a provided class instance provider."""
        logger.info("🧪 Testing logic discovery from a class instance.")
        # 📋 Arrange
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

        # 🚀 Act: Create a machine with the provider instance.
        machine = create_machine(config, logic_providers=[provider])

        # ✅ Assert: The provider's methods are bound correctly.
        self.assertIn("provider_action", machine.logic.actions)
        self.assertIn("provider_guard", machine.logic.guards)
        self.assertEqual(
            machine.logic.actions["provider_action"], provider.provider_action
        )

    def test_discover_from_multiple_providers(self) -> None:
        """Should discover logic from a list of multiple class instance providers."""
        logger.info("🧪 Testing discovery from a list of multiple providers.")

        # 📋 Arrange: Define two provider classes.
        class Provider1:
            def action_one(self) -> None:
                pass

        class Provider2:
            def action_two(self) -> None:
                pass

        config = {
            "id": "multi_provider",
            "initial": "a",
            "states": {"a": {"entry": ["action_one", "action_two"]}},
        }
        # 🚀 Act: Create the machine with a list of provider instances.
        machine = create_machine(
            config, logic_providers=[Provider1(), Provider2()]
        )
        # ✅ Assert: Actions from both providers should be discovered.
        self.assertIn("action_one", machine.logic.actions)
        self.assertIn("action_two", machine.logic.actions)

    def test_discover_from_mixed_string_and_module_objects(self) -> None:
        """Should discover logic from a mixed list of module paths and objects."""
        logger.info(
            "🧪 Testing discovery from mixed module strings and objects."
        )
        # 📋 Arrange
        module_path = "temp_logic_for_testing_two.py"
        module_name = "temp_logic_for_testing_two"
        config = {
            "id": "mixed_modules",
            "initial": "a",
            "states": {"a": {"entry": ["an_action", "another_test_action"]}},
        }

        # ⚙️ Use a try...finally block to ensure the temp file is always deleted.
        try:
            with open(module_path, "w") as f:
                f.write("def another_test_action(): pass")

            # Invalidate Python's import caches to ensure it finds the new file.
            importlib.invalidate_caches()
            import temp_logic_for_testing_two  # type: ignore

            # 🚀 Act: Create the machine with a mixed list of sources.
            machine = create_machine(
                config,
                logic_modules=[
                    _TEST_LOGIC_MODULE_NAME,  # By string name
                    temp_logic_for_testing_two,  # As module object
                ],
            )

            # ✅ Assert: Actions from both modules were successfully discovered.
            self.assertIn("an_action", machine.logic.actions)
            self.assertIn("another_test_action", machine.logic.actions)

        finally:
            # 🧹 Clean up the temporary file and module to ensure test isolation.
            if os.path.exists(module_path):
                os.remove(module_path)
            if module_name in sys.modules:
                del sys.modules[module_name]

    def test_discover_and_bind_all_logic_types_at_once(self) -> None:
        """Should discover and correctly categorize actions, guards, and services."""
        logger.info("🧪 Testing discovery of all logic types simultaneously.")
        # 📋 Arrange
        loader = LogicLoader()
        # 🚀 Act
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )
        # ✅ Assert
        self.assertIn("an_action", logic.actions)
        self.assertIn("a_guard", logic.guards)
        self.assertIn("a_service", logic.services)

    def test_discover_logic_from_nested_config(self) -> None:
        """Should extract logic names from deeply nested state nodes."""
        logger.info("🧪 Testing logic extraction from nested configurations.")
        # 📋 Arrange
        config = {
            "id": "deep",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {
                        "a1": {"on": {"NEXT": "b"}, "entry": "actionA1"},
                    },
                },
                "b": {
                    "invoke": {"src": "serviceB"},
                    "onDone": {"target": "c", "actions": "actionB"},
                },
                "c": {"on": {"NEXT": {"target": "a", "guard": "guardC"}}},
            },
        }
        # Create a dummy machine to parse the config.
        temp_machine = MachineNode(config=config, logic=MachineLogic())
        loader = LogicLoader()
        # These sets will be populated by the extraction method.
        required: Tuple[Set[str], Set[str], Set[str]] = (set(), set(), set())

        # 🚀 Act: Call the private extraction method directly for this unit test.
        loader._extract_logic_from_node(temp_machine, *required)

        # ✅ Assert: All logic names were correctly extracted and categorized.
        self.assertEqual(required[0], {"actionA1", "actionB"})  # Actions
        self.assertEqual(required[1], {"guardC"})  # Guards
        self.assertEqual(required[2], {"serviceB"})  # Services

    # -------------------------------------------------------------------------
    # 🌍 Global Registration and Precedence
    # -------------------------------------------------------------------------

    def test_discover_logic_from_registered_module(self) -> None:
        """Should discover logic from a globally pre-registered module."""
        logger.info("🧪 Testing discovery from globally registered modules.")
        # 📋 Arrange: Import the module and register it with the loader instance.
        # ✅ FIX: Ignore the type checker warning for the dynamically created module.
        import temp_logic_for_testing  # type: ignore

        loader = LogicLoader.get_instance()
        loader.register_logic_module(temp_logic_for_testing)
        # 🚀 Act: Discover logic without providing any local sources.
        logic = loader.discover_and_build_logic(_MACHINE_CONFIG)
        # ✅ Assert: The action from the globally registered module is found.
        self.assertIn("an_action", logic.actions)

    def test_last_module_wins_on_function_conflict(self) -> None:
        """If two modules define a function with the same name, the last one wins."""
        logger.info("🧪 Testing conflict resolution between logic modules.")
        # 📋 Arrange
        module_a_path = "conflict_module_a.py"
        module_b_path = "conflict_module_b.py"
        conflict_config = {
            "id": "conflict_test",
            "initial": "a",
            "states": {"a": {"on": {"EVENT": {"guard": "a_guard"}}}},
        }

        with open(module_a_path, "w") as f:
            f.write("def a_guard(): return 'A'")
        with open(module_b_path, "w") as f:
            f.write("def a_guard(): return 'B'")

        importlib.invalidate_caches()

        # 🚀 Act: Create a machine with conflicting modules. 'b' is last.
        machine = create_machine(
            conflict_config,
            logic_modules=["conflict_module_a", "conflict_module_b"],
        )

        # ✅ Assert: The function from the *second* module was used.
        self.assertIn("a_guard", machine.logic.guards)
        guard_func = machine.logic.guards["a_guard"]
        # We can inspect the function's source file to confirm.
        self.assertIn(module_b_path, inspect.getsourcefile(guard_func))

        for path in [module_a_path, module_b_path]:
            if os.path.exists(path):
                os.remove(path)
        for name in ["conflict_module_a", "conflict_module_b"]:
            if name in sys.modules:
                del sys.modules[name]

    def test_provider_method_overrides_module_function(self) -> None:
        """If a provider and a module have a conflict, the provider should win."""
        logger.info("🧪 Testing that provider logic overrides module logic.")

        # ------------------------------------------------------------------ #
        # 🤖 Arrange                                                         #
        # ------------------------------------------------------------------ #
        class MyProvider:
            def factory_action(self) -> str:  # noqa
                return "from_provider"

        module_path = f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py"
        try:
            with open(module_path, "w") as f:
                f.write("def factory_action(): return 'from_module'")

            importlib.invalidate_caches()  # 👈 make the new file importable
            if os.getcwd() not in sys.path:  # 👈 safety: ensure cwd is on path
                sys.path.insert(0, os.getcwd())  # 👈

            # ------------------------------------------------------------------ #
            # ⚡ Act                                                              #
            # ------------------------------------------------------------------ #
            machine = create_machine(
                _FACTORY_MACHINE_CONFIG,
                logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
                logic_providers=[MyProvider()],
            )

            # ------------------------------------------------------------------ #
            # ✨ Assert                                                           #
            # ------------------------------------------------------------------ #
            action_func = machine.logic.actions["factory_action"]
            self.assertTrue(
                hasattr(action_func, "__self__"),
                "Action should be a bound method",
            )
            self.assertIsInstance(action_func.__self__, MyProvider)

        finally:
            # 🧹 Clean-up (file + import cache)
            if os.path.exists(module_path):
                os.remove(module_path)
            if _TEST_FACTORY_LOGIC_MODULE_NAME in sys.modules:
                del sys.modules[_TEST_FACTORY_LOGIC_MODULE_NAME]

    # -------------------------------------------------------------------------
    # 💅 Name Matching Conventions
    # -------------------------------------------------------------------------

    def test_name_matching_for_camel_and_snake_case(self) -> None:
        """Should correctly map between camelCase and snake_case names."""
        logger.info("🧪 Testing camelCase/snake_case name resolution.")
        # 📋 Arrange
        # ✅ FIX: Ignore the type checker warning for the dynamically created module.
        import temp_logic_for_testing  # type: ignore

        loader = LogicLoader()
        # 🚀 Act
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[temp_logic_for_testing]
        )
        # ✅ Assert: Both naming conventions were resolved correctly.
        self.assertIn("anotherActionInCamel", logic.actions)
        self.assertIn("actionForSnakeCase", logic.actions)
        self.assertIs(
            logic.actions["actionForSnakeCase"],
            temp_logic_for_testing.action_for_snake_case,
        )

    def test_case_insensitivity_in_name_matching(self) -> None:
        """Logic discovery should be case-sensitive for function names."""
        logger.info("🧪 Testing that logic discovery is case-sensitive.")
        # 📋 Arrange
        logic_path = "case_logic.py"
        config = {
            "id": "case",
            "initial": "a",
            "states": {"a": {"entry": "myaction"}},  # Lowercase
        }
        with open(logic_path, "w") as f:
            f.write("def MyAction(): pass")  # CamelCase

        # 🚀 Act & Assert: This should fail because 'myaction' != 'MyAction'.
        with self.assertRaises(ImplementationMissingError):
            create_machine(config, logic_modules=["case_logic"])

        # 🧹 Cleanup
        os.remove(logic_path)

    # -------------------------------------------------------------------------
    # 🚫 Ignored Items and Methods
    # -------------------------------------------------------------------------

    def test_loader_ignores_dunder_methods_in_providers(self) -> None:
        """Should ignore 'dunder' methods (like __init__) in logic providers."""
        logger.info("🧪 Testing that dunder methods are ignored in providers.")

        # 📋 Arrange
        class ProviderWithDunder:
            def __init__(self) -> None:
                pass

            def my_action(self) -> None:
                pass

        config = {
            "id": "dunder",
            "initial": "a",
            "states": {"a": {"entry": "my_action"}},
        }
        # 🚀 Act
        machine = create_machine(
            config, logic_providers=[ProviderWithDunder()]
        )
        # ✅ Assert
        self.assertIn("my_action", machine.logic.actions)
        self.assertNotIn("__init__", machine.logic.actions)

    def test_loader_ignores_private_methods_in_providers(self) -> None:
        """Should ignore methods starting with an underscore in logic providers."""
        logger.info(
            "🧪 Testing that private methods are ignored in providers."
        )

        # 📋 Arrange
        class ProviderWithPrivate:
            def _private_action(self) -> None:
                pass

            def public_action(self) -> None:
                pass

        config = {
            "id": "private_provider",
            "initial": "a",
            "states": {"a": {"entry": "public_action"}},
        }
        # 🚀 Act
        machine = create_machine(
            config, logic_providers=[ProviderWithPrivate()]
        )
        # ✅ Assert
        self.assertIn("public_action", machine.logic.actions)
        self.assertNotIn("_private_action", machine.logic.actions)

    def test_logic_loader_does_not_mutate_registered_modules_list(
        self,
    ) -> None:
        """The loader should not add local modules to the global registry."""
        logger.info("🧪 Testing that the global registry is not mutated.")
        # 📋 Arrange
        loader = LogicLoader.get_instance()
        self.assertEqual(len(loader._registered_logic_modules), 0)

        # 🚀 Act: Discover logic with a locally-provided module.
        loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )

        # ✅ Assert: The globally registered list should still be empty.
        self.assertEqual(len(loader._registered_logic_modules), 0)

    # -------------------------------------------------------------------------
    # 💥 Error Handling & Invalid Inputs
    # -------------------------------------------------------------------------

    def test_raises_error_for_missing_implementation(self) -> None:
        """Should raise ImplementationMissingError if a required function is not found."""
        logger.info("🧪 Testing error for a missing implementation.")
        # 📋 Arrange
        loader = LogicLoader()
        faulty_config = {
            "id": "faulty",
            "initial": "a",
            "states": {"a": {"entry": ["nonExistentAction"]}},
        }
        # 🚀 Act & Assert
        with self.assertRaises(ImplementationMissingError):
            loader.discover_and_build_logic(
                faulty_config, logic_modules=[_TEST_LOGIC_MODULE_NAME]
            )

    def test_raises_error_for_invalid_module_path(self) -> None:
        """Should raise ImportError for an invalid module path string."""
        logger.info("🧪 Testing error for an unresolvable module path.")
        # 📋 Arrange
        loader = LogicLoader()
        # 🚀 Act & Assert
        with self.assertRaises(ImportError):
            loader.discover_and_build_logic(
                _MACHINE_CONFIG, logic_modules=["invalid.path.does.not.exist"]
            )

    def test_raises_error_for_invalid_module_list_type(self) -> None:
        """Should raise TypeError if `logic_modules` contains an invalid type."""
        logger.info("🧪 Testing error for invalid type in `logic_modules`.")
        # 📋 Arrange
        loader = LogicLoader()
        # 🚀 Act & Assert
        with self.assertRaises(TypeError):
            # The list contains an integer, which is not a valid source.
            loader.discover_and_build_logic(
                _MACHINE_CONFIG, logic_modules=[123]  # type: ignore
            )

    def test_logic_providers_list_with_non_class_instance_is_ignored(
        self,
    ) -> None:
        """Should ignore non-class-instance items in `logic_providers`."""
        logger.info("🧪 Testing that invalid provider types are ignored.")
        # 📋 Arrange
        config = {"id": "test", "initial": "a", "states": {"a": {}}}
        # 🚀 Act: Create a machine with an invalid item in the providers list.
        machine = create_machine(config, logic_providers=[123])  # type: ignore
        # ✅ Assert: The machine is created with no actions, as the provider was ignored.
        self.assertEqual(len(machine.logic.actions), 0)

    def test_empty_config_raises_error(self) -> None:
        """Should raise InvalidConfigError for an empty configuration dict."""
        logger.info("🧪 Testing error for an empty machine configuration.")
        with self.assertRaises(InvalidConfigError):
            create_machine({})

    def test_config_with_non_dict_states_raises_error(self) -> None:
        """Should raise an error if the 'states' value is not a dictionary."""
        logger.info("🧪 Testing error for a non-dictionary `states` property.")
        config = {"id": "test", "initial": "a", "states": "not_a_dict"}
        with self.assertRaises(AttributeError):
            create_machine(config)

    def test_logic_loader_with_no_sources(self) -> None:
        """Should raise error if logic is required but no sources are given."""
        logger.info(
            "🧪 Testing error when logic is required but no sources provided."
        )
        loader = LogicLoader()
        with self.assertRaises(ImplementationMissingError):
            # _MACHINE_CONFIG requires actions/guards, but no sources are given.
            loader.discover_and_build_logic(_MACHINE_CONFIG)

    # -------------------------------------------------------------------------
    # 🏕️ Edge Case Scenarios
    # -------------------------------------------------------------------------

    def test_discover_logic_with_no_required_implementations(self) -> None:
        """Should succeed if a machine config requires no implementations."""
        logger.info("🧪 Testing discovery for a machine with no logic needs.")
        # 📋 Arrange
        config = {"id": "simple", "initial": "a", "states": {"a": {}}}
        loader = LogicLoader()
        # 🚀 Act: Discover logic, even though none is needed.
        logic = loader.discover_and_build_logic(
            config, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )
        # ✅ Assert: The resulting logic object is empty.
        self.assertEqual(len(logic.actions), 0)
        self.assertEqual(len(logic.guards), 0)
        self.assertEqual(len(logic.services), 0)

    def test_create_machine_with_empty_logic_module_list(self) -> None:
        """Should raise error if logic is needed but `logic_modules` is empty."""
        logger.info("🧪 Testing discovery with an empty `logic_modules` list.")
        # 📋 Arrange
        loader = LogicLoader()
        # This config requires 'factory_action'.
        # 🚀 Act & Assert
        with self.assertRaises(ImplementationMissingError):
            loader.discover_and_build_logic(
                _FACTORY_MACHINE_CONFIG, logic_modules=[]
            )

    def test_create_machine_with_empty_logic_providers_list(self) -> None:
        """Should raise error if logic is needed but `logic_providers` is empty."""
        logger.info(
            "🧪 Testing discovery with an empty `logic_providers` list."
        )
        # 📋 Arrange
        loader = LogicLoader()
        # This config requires 'provider_action'.
        # 🚀 Act & Assert
        with self.assertRaises(ImplementationMissingError):
            loader.discover_and_build_logic(
                _PROVIDER_MACHINE_CONFIG, logic_providers=[]
            )

    def test_provider_with_no_relevant_methods(self) -> None:
        """Should raise error if a provider has no methods matching the config."""
        logger.info("🧪 Testing a provider that lacks required methods.")

        # 📋 Arrange
        class UselessProvider:
            def some_other_method(self) -> None:
                pass

        # 🚀 Act & Assert: The required 'factory_action' is not in the provider.
        with self.assertRaises(ImplementationMissingError):
            create_machine(
                _FACTORY_MACHINE_CONFIG, logic_providers=[UselessProvider()]
            )


if __name__ == "__main__":
    unittest.main()
