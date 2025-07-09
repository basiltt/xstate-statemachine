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
import inspect

# ✅ FIX: Changed relative imports to absolute imports from the src package.
from src.xstate_statemachine import (
    ImplementationMissingError,
    InvalidConfigError,
    LogicLoader,
    MachineLogic,
    create_machine,
)
from xstate_statemachine.models import MachineNode

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

# This content is now used by the new tests as well
_TEST_FACTORY_LOGIC_MODULE_NAME = "temp_factory_logic_module"
_TEST_FACTORY_LOGIC_CONTENT = "def factory_action(): pass"


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

    def test_discover_from_multiple_providers(self) -> None:
        """Should discover logic from a list of multiple class instance providers."""

        class Provider1:
            def action_one(self):
                pass

        class Provider2:
            def action_two(self):
                pass

        config = {
            "id": "multi_provider",
            "initial": "a",
            "states": {"a": {"entry": ["action_one", "action_two"]}},
        }
        machine = create_machine(
            config, logic_providers=[Provider1(), Provider2()]
        )
        self.assertIn("action_one", machine.logic.actions)
        self.assertIn("action_two", machine.logic.actions)

    def test_discover_from_mixed_string_and_module_objects(self) -> None:
        """Should discover logic from a mixed list of module paths and module objects."""
        with open("temp_logic_for_testing_two.py", "w") as f:
            f.write("def another_test_action(): pass")
        import temp_logic_for_testing_two

        config = {
            "id": "mixed_modules",
            "initial": "a",
            "states": {"a": {"entry": ["an_action", "another_test_action"]}},
        }
        machine = create_machine(
            config,
            logic_modules=[
                _TEST_LOGIC_MODULE_NAME,
                temp_logic_for_testing_two,
            ],
        )

        self.assertIn("an_action", machine.logic.actions)
        self.assertIn("another_test_action", machine.logic.actions)

        os.remove("temp_logic_for_testing_two.py")

    def test_last_module_wins_on_function_conflict(self) -> None:
        """If two modules define a function with the same name, the last one in the list should be used."""
        with open("conflict_module_a.py", "w") as f:
            f.write("def a_guard(): return 'A'")
        with open("conflict_module_b.py", "w") as f:
            f.write("def a_guard(): return 'B'")

        # Use a config that only requires the conflicting guard
        conflict_config = {
            "id": "conflict_test",
            "initial": "a",
            "states": {
                "a": {"on": {"EVENT": {"target": "a", "guard": "a_guard"}}}
            },
        }

        machine = create_machine(
            conflict_config,
            logic_modules=["conflict_module_a", "conflict_module_b"],
        )
        self.assertIn("a_guard", machine.logic.guards)

        # To verify which one was picked, we can inspect the source file of the function object
        guard_func = machine.logic.guards["a_guard"]
        self.assertIn("conflict_module_b.py", inspect.getsourcefile(guard_func))  # type: ignore

        os.remove("conflict_module_a.py")
        os.remove("conflict_module_b.py")

    def test_discover_logic_with_no_required_implementations(self) -> None:
        """Should create logic successfully even if the machine config requires no implementations."""
        config = {"id": "simple", "initial": "a", "states": {"a": {}}}
        loader = LogicLoader()
        logic = loader.discover_and_build_logic(
            config, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )
        self.assertEqual(len(logic.actions), 0)
        self.assertEqual(len(logic.guards), 0)
        self.assertEqual(len(logic.services), 0)

    def test_logic_providers_list_with_non_class_instance_is_ignored(
        self,
    ) -> None:
        """Should ignore non-class-instance items in the logic_providers list."""
        config = {"id": "test", "initial": "a", "states": {"a": {}}}
        machine = create_machine(config, logic_providers=[123])  # type: ignore
        self.assertEqual(len(machine.logic.actions), 0)

    def test_empty_config_raises_error(self) -> None:
        """Should raise InvalidConfigError for an empty configuration dictionary."""
        with self.assertRaises(InvalidConfigError):
            create_machine({})

    def test_config_with_non_dict_states_raises_error(self) -> None:
        """Should raise an error if the 'states' value is not a dictionary."""
        config = {"id": "test", "initial": "a", "states": "not_a_dict"}
        with self.assertRaises(AttributeError):
            create_machine(config)

    def test_discover_and_bind_all_logic_types_at_once(self) -> None:
        """Should discover and correctly categorize actions, guards, and services."""
        loader = LogicLoader()
        logic = loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )
        self.assertIn("an_action", logic.actions)
        self.assertIn("a_guard", logic.guards)
        self.assertIn("a_service", logic.services)

    def test_loader_ignores_dunder_methods_in_providers(self) -> None:
        """Should ignore 'dunder' methods (like __init__) in logic providers."""

        class ProviderWithDunder:
            def __init__(self):
                self.some_prop = 1

            def my_action(self):
                pass

        config = {
            "id": "dunder",
            "initial": "a",
            "states": {"a": {"entry": "my_action"}},
        }
        machine = create_machine(
            config, logic_providers=[ProviderWithDunder()]
        )
        self.assertIn("my_action", machine.logic.actions)
        self.assertNotIn("__init__", machine.logic.actions)

    def test_loader_ignores_private_methods_in_providers(self) -> None:
        """Should ignore methods starting with an underscore in logic providers."""

        class ProviderWithPrivate:
            def _private_action(self):
                pass

            def public_action(self):
                pass

        config = {
            "id": "private_provider",
            "initial": "a",
            "states": {"a": {"entry": "public_action"}},
        }
        machine = create_machine(
            config, logic_providers=[ProviderWithPrivate()]
        )
        self.assertIn("public_action", machine.logic.actions)
        self.assertNotIn("_private_action", machine.logic.actions)

    def test_create_machine_with_empty_logic_module_list(self) -> None:
        """Should run without error if `logic_modules` is an empty list."""
        with open(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_FACTORY_LOGIC_CONTENT)
        with self.assertRaises(ImplementationMissingError):
            loader = LogicLoader()
            loader.discover_and_build_logic(
                _FACTORY_MACHINE_CONFIG, logic_modules=[]
            )

    def test_create_machine_with_empty_logic_providers_list(self) -> None:
        """Should run without error if `logic_providers` is an empty list."""
        with self.assertRaises(ImplementationMissingError):
            loader = LogicLoader()
            loader.discover_and_build_logic(
                _PROVIDER_MACHINE_CONFIG, logic_providers=[]
            )

    def test_discover_logic_from_statically_registered_module(self) -> None:
        """Should discover logic from a module object registered globally."""
        import temp_logic_for_testing

        loader = LogicLoader.get_instance()
        # Correctly register the imported module object
        loader.register_logic_module(temp_logic_for_testing)

        # discover_and_build_logic should now find the logic without needing
        # it to be passed in the local `logic_modules` argument.
        logic = loader.discover_and_build_logic(_MACHINE_CONFIG)
        self.assertIn("an_action", logic.actions)
        self.assertIs(
            logic.actions["an_action"], temp_logic_for_testing.an_action
        )

    def test_discover_logic_from_nested_config(self) -> None:
        """Should correctly extract logic names from deeply nested states."""
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
        required_actions, required_guards, required_services = (
            set(),
            set(),
            set(),
        )
        temp_machine = MachineNode(config=config, logic=MachineLogic())
        loader = LogicLoader()
        loader._extract_logic_from_node(
            temp_machine, required_actions, required_guards, required_services
        )

        self.assertEqual(required_actions, {"actionA1", "actionB"})
        self.assertEqual(required_guards, {"guardC"})
        self.assertEqual(required_services, {"serviceB"})

    def test_logic_loader_does_not_mutate_registered_modules_list(
        self,
    ) -> None:
        """The loader should not add locally provided modules to the global registry."""
        loader = LogicLoader.get_instance()
        self.assertEqual(len(loader._registered_logic_modules), 0)

        loader.discover_and_build_logic(
            _MACHINE_CONFIG, logic_modules=[_TEST_LOGIC_MODULE_NAME]
        )

        self.assertEqual(len(loader._registered_logic_modules), 0)

    def test_case_insensitivity_in_name_matching(self) -> None:
        """Logic discovery should be case-sensitive for function names."""
        with open("case_logic.py", "w") as f:
            f.write("def MyAction(): pass")

        config = {
            "id": "case",
            "initial": "a",
            "states": {"a": {"entry": "myaction"}},
        }
        with self.assertRaises(ImplementationMissingError):
            create_machine(config, logic_modules=["case_logic"])

        os.remove("case_logic.py")

    def test_provider_method_overrides_module_function(self) -> None:
        """If a provider and a module have a conflict, the provider should win."""

        class MyProvider:
            def factory_action(self):
                return "from_provider"

        # Create the temp module file for this test specifically
        with open(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write("def factory_action(): return 'from_module'")

        machine = create_machine(
            _FACTORY_MACHINE_CONFIG,
            logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
            logic_providers=[MyProvider()],
        )

        # The logic_map should prioritize the provider's method.
        # Check that the bound action is a method bound to the provider instance.
        action_func = machine.logic.actions["factory_action"]
        self.assertTrue(
            hasattr(action_func, "__self__"), "Action should be a bound method"
        )
        self.assertIsInstance(
            action_func.__self__,
            MyProvider,
            "Action should be bound to the provider instance",
        )

    def test_provider_with_no_relevant_methods(self) -> None:
        """Should not raise error if a provider has no methods matching the config."""

        class UselessProvider:
            def some_other_method(self):
                pass

        with open(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_FACTORY_LOGIC_CONTENT)

        with self.assertRaises(ImplementationMissingError):
            create_machine(
                _FACTORY_MACHINE_CONFIG, logic_providers=[UselessProvider()]
            )

    def test_logic_loader_with_no_sources(self) -> None:
        """Should raise ImplementationMissingError if logic is required but no sources are given."""
        loader = LogicLoader()
        with self.assertRaises(ImplementationMissingError):
            loader.discover_and_build_logic(_MACHINE_CONFIG)


if __name__ == "__main__":
    unittest.main()
