# /tests/test_factory.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Machine Factory (`create_machine`)
# -----------------------------------------------------------------------------
# This module provides a comprehensive test suite for the `create_machine`
# factory function located in `src.xstate_statemachine.factory`. The suite's
# primary goal is to rigorously verify the factory's functionality under
# various conditions.
#
# Key areas of testing include:
#   - Correct instantiation of `MachineNode` from valid configurations.
#   - Robust error handling for invalid or incomplete machine configurations.
#   - Validation of explicit logic binding via the `logic` parameter.
#   - Verification of the automatic logic discovery feature using both
#     `logic_modules` and `logic_providers`.
#   - Precedence rules when multiple logic sources are provided.
#   - Handling of edge cases and complex state machine structures like
#     parallel, final, and invoked states.
#
# The tests are designed to be self-contained and clean up after themselves,
# ensuring no side effects between test runs.
# -----------------------------------------------------------------------------
import importlib

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import os
import sys
import textwrap
import unittest
from typing import Any, Callable, Dict

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
# Configures a logger for providing informative output during test execution.
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🛠️ Test Helpers & Mocks
# -----------------------------------------------------------------------------
# These constants and classes are used across multiple tests to provide
# consistent configurations and mock implementations.

# A temporary module name for dynamic module creation during tests.
_TEST_FACTORY_LOGIC_MODULE_NAME = "temp_factory_logic_module"
# The Python code to be written into the temporary module.
_TEST_FACTORY_LOGIC_CONTENT = "def factory_action(): pass"


class MyLogicProvider:
    """A mock class providing a callable method for logic discovery tests.

    This class demonstrates how `create_machine` can discover and bind methods
    from class instances provided in the `logic_providers` list.
    """

    def provider_action(self) -> None:
        """A sample action method to be discovered by the factory."""
        pass


# A simple machine config that references an action from the temp module.
_FACTORY_MACHINE_CONFIG: Dict[str, Any] = {  # noqa
    "id": "factory_test_machine",
    "initial": "active",
    "states": {"active": {"entry": ["factory_action"]}},
}
# A simple machine config that references an action from the provider class.
_PROVIDER_MACHINE_CONFIG: Dict[str, Any] = {
    "id": "provider_test_machine",
    "initial": "active",
    "states": {"active": {"entry": ["provider_action"]}},
}


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestFactory
# -----------------------------------------------------------------------------


class TestFactory(unittest.TestCase):
    """Test suite for the `create_machine` factory function.

    This class contains a series of tests to validate all aspects of the
    machine creation process, from basic instantiation to complex logic
    discovery and error handling.
    """

    # -------------------------------------------------------------------------
    # 🧪 Test Lifecycle Methods
    # -------------------------------------------------------------------------

    def setUp(self) -> None:
        """Initializes test data and environment before each test.

        This method sets up a fresh `MachineLogic` instance and a valid default
        config. It also creates a temporary Python module file on disk and adds
        the current directory to `sys.path` to make it importable, which is
        essential for testing the `logic_modules` discovery feature.
        """
        logger.info("Setting up for a new test...")
        # ✨ A standard, valid config for simple tests.
        self.valid_config: Dict[str, Any] = {
            "id": "test_machine",
            "initial": "idle",
            "states": {"idle": {}},
        }
        # ✨ An explicit logic object for tests that require it.
        self.explicit_logic = MachineLogic()

        # 📝 Create a temporary module file for logic discovery tests.
        with open(f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py", "w") as f:
            f.write(_TEST_FACTORY_LOGIC_CONTENT)

        # PYTHONPATH modification to ensure the temp module is discoverable.
        if os.getcwd() not in sys.path:
            sys.path.insert(0, os.getcwd())

    def tearDown(self) -> None:
        """Cleans up resources and environment after each test.

        This method ensures the testing environment is clean by:
        1. Resetting the `LogicLoader` singleton.
        2. Unloading the temporary logic module from `sys.modules`.
        3. Deleting the temporary `.py` file created in `setUp`.
        """
        logger.info("Tearing down test resources...")
        # 🧹 Reset the singleton to prevent state leakage between tests.
        LogicLoader._instance = None

        # 🗑️ Unload the module if it was loaded.
        if _TEST_FACTORY_LOGIC_MODULE_NAME in sys.modules:
            del sys.modules[_TEST_FACTORY_LOGIC_MODULE_NAME]

        # 🗑️ Delete the temporary file.
        temp_file_path = f"{_TEST_FACTORY_LOGIC_MODULE_NAME}.py"
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

    # -------------------------------------------------------------------------
    # 🔩 Core Creation and Validation Tests
    # -------------------------------------------------------------------------

    def test_create_machine_with_explicit_logic(self) -> None:
        """Should create a MachineNode with an explicit logic object."""
        logger.info("🧪 Testing machine creation with explicit logic object.")
        # 🚀 Act: Create the machine with a pre-configured logic object.
        machine = create_machine(self.valid_config, logic=self.explicit_logic)

        # ✅ Assert: Verify the machine is created correctly and uses the exact logic object provided.
        self.assertIsInstance(machine, MachineNode)
        self.assertEqual(machine.id, "test_machine")
        self.assertIs(machine.logic, self.explicit_logic)

    def test_create_machine_with_no_logic_falls_back_to_empty(self) -> None:
        """Should create an empty `MachineLogic` if none is provided."""
        logger.info("🧪 Testing machine creation fallback to empty logic.")
        # 🚀 Act: Create the machine without any logic parameters.
        machine = create_machine(self.valid_config)

        # ✅ Assert: A new, empty MachineLogic object should be created and attached.
        self.assertIsNotNone(machine.logic)
        self.assertEqual(len(machine.logic.actions), 0)

    def test_raises_error_for_config_missing_id(self) -> None:
        """Should raise `InvalidConfigError` if the 'id' key is missing."""
        logger.info("🧪 Testing error for configuration missing the 'id' key.")
        # 📋 Arrange: Create a config that lacks the root 'id'.
        invalid_config = {"initial": "idle", "states": {"idle": {}}}

        # 💥 Act & Assert: Expect an InvalidConfigError with a specific message.
        with self.assertRaisesRegex(
            InvalidConfigError, "Machine configuration must have a root 'id'."
        ):
            create_machine(invalid_config)

    def test_raises_error_for_config_missing_states(self) -> None:
        """Should raise `InvalidConfigError` if the 'states' key is missing."""
        logger.info(
            "🧪 Testing error for configuration missing the 'states' key."
        )
        # 📋 Arrange: Create a config that lacks the 'states' dictionary.
        invalid_config = {"id": "test_machine", "initial": "idle"}

        # 💥 Act & Assert: Expect an InvalidConfigError with the updated message.
        # ✅ FIX: Updated the regex to match the actual, more specific error message.
        with self.assertRaisesRegex(
            InvalidConfigError, "must be a dict with 'id' and 'states' keys"
        ):
            create_machine(invalid_config)

    def test_machine_with_id_only_is_invalid(self) -> None:
        """Should raise `InvalidConfigError` if 'states' key is missing."""
        logger.info("🧪 Testing error for config with only an 'id'.")
        # 💥 Act & Assert: A machine with only an ID is not valid.
        # ✅ FIX: Updated the regex to match the actual error message from the source.
        with self.assertRaisesRegex(
            InvalidConfigError, "must be a dict with 'id' and 'states' keys"
        ):
            create_machine({"id": "only_id"})

    def test_machine_with_states_only_is_invalid(self) -> None:
        """Should raise `InvalidConfigError` if 'id' key is missing."""
        logger.info("🧪 Testing error for config with only 'states'.")
        # 💥 Act & Assert: A machine without an ID is not valid.
        with self.assertRaisesRegex(
            InvalidConfigError, "must have a root 'id'"
        ):
            create_machine({"states": {"a": {}}})

    # -------------------------------------------------------------------------
    # ✨ Automatic Logic Discovery Tests
    # -------------------------------------------------------------------------

    def test_create_machine_with_logic_modules_string(self) -> None:
        """Should auto-discover logic when `logic_modules` is a list of strings."""
        logger.info("🧪 Testing logic discovery from module names (strings).")
        # 🚀 Act: Create a machine pointing to the temporary module by its name.
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
        )

        # ✅ Assert: The action from the module should be discovered and loaded.
        self.assertIn("factory_action", machine.logic.actions)
        self.assertTrue(
            isinstance(machine.logic.actions["factory_action"], Callable)
        )

    def test_create_machine_with_logic_modules_object(self) -> None:
        """Should auto-discover logic when `logic_modules` is a list of module objects."""
        logger.info("🧪 Testing logic discovery from imported module objects.")
        # 📋 Arrange: Import the temporary module directly.
        import temp_factory_logic_module

        # 🚀 Act: Create a machine passing the module object itself.
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic_modules=[temp_factory_logic_module],
        )

        # ✅ Assert: The action should be the exact same function object from the module.
        self.assertIn("factory_action", machine.logic.actions)
        self.assertIs(
            machine.logic.actions["factory_action"],
            temp_factory_logic_module.factory_action,
        )

    def test_create_machine_with_logic_providers(self) -> None:
        """✨ NEW: Should auto-discover logic when `logic_providers` is used."""
        logger.info(
            "🧪 Testing logic discovery from provider class instances."
        )
        # 📋 Arrange: Instantiate the logic provider.
        logic_provider_instance = MyLogicProvider()

        # 🚀 Act: Create a machine passing the instance.
        machine = create_machine(
            config=_PROVIDER_MACHINE_CONFIG,
            logic_providers=[logic_provider_instance],
        )

        # ✅ Assert: The bound method from the instance should be loaded as an action.
        self.assertIn("provider_action", machine.logic.actions)
        self.assertEqual(
            machine.logic.actions["provider_action"],
            logic_provider_instance.provider_action,
        )

    def test_auto_discovery_with_mixed_providers_and_modules(self) -> None:
        """Should discover logic from both logic_modules and logic_providers."""
        logger.info("🧪 Testing logic discovery from a mix of sources.")

        # 📋 Arrange: Define a provider and a config that uses actions from both sources.
        class MixedProvider:
            def mixed_action(self) -> None:
                pass

        config = {
            "id": "mixed_discovery",
            "initial": "active",
            "states": {
                "active": {"entry": ["factory_action", "mixed_action"]}
            },
        }
        # 🚀 Act: Create machine with both `logic_modules` and `logic_providers`.
        machine = create_machine(
            config,
            logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
            logic_providers=[MixedProvider()],
        )

        # ✅ Assert: Actions from both sources should be present in the final logic.
        self.assertIn("factory_action", machine.logic.actions)
        self.assertIn("mixed_action", machine.logic.actions)

    def test_auto_discovery_ignores_private_functions(self) -> None:
        """Should ignore functions starting with an underscore and raise error."""
        logger.info("🧪 Testing that private functions are not discovered.")
        # 📋 Arrange: Create a module with a "private" function.
        with open("private_logic.py", "w") as f:
            f.write("def _private_action(): pass")

        config = {
            "id": "private",
            "initial": "a",
            "states": {"a": {"entry": "_private_action"}},
        }

        # 💥 Act & Assert: Creating the machine should fail because the implementation is missing (ignored).
        with self.assertRaises(ImplementationMissingError):
            create_machine(config, logic_modules=["private_logic"])

        # 🧹 Cleanup
        os.remove("private_logic.py")

    def test_auto_discovery_with_guards_and_services(self) -> None:
        """Should correctly discover and categorize guards and services."""
        logger.info("🧪 Testing discovery of actions, guards, and services.")
        # 📋 Arrange: Define the logic content as a multi-line string.
        logic_content = """
        import asyncio

        def discovered_action(): pass
        def discovered_guard(): return True
        async def discovered_service(): return {}
        """
        logic_file_path = "full_logic.py"

        # ✅ FIX: Use `textwrap.dedent` to remove the common leading whitespace
        # from the multi-line string before writing it to the file.
        with open(logic_file_path, "w") as f:
            f.write(textwrap.dedent(logic_content))

        importlib.invalidate_caches()

        config = {
            "id": "full",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "NEXT": {"target": "b", "guard": "discovered_guard"}
                    },
                    "invoke": {"src": "discovered_service", "onDone": "c"},
                },
                "b": {"entry": "discovered_action"},
                "c": {},
            },
        }

        # 🚀 Act: Create the machine. The import should now succeed.
        machine = create_machine(config, logic_modules=["full_logic"])

        # ✅ Assert: Ensure each callable was placed in the correct logic category.
        self.assertIn("discovered_action", machine.logic.actions)
        self.assertIn("discovered_guard", machine.logic.guards)
        self.assertIn("discovered_service", machine.logic.services)

        # 🧹 Cleanup
        os.remove(logic_file_path)

    # -------------------------------------------------------------------------
    # 🚦 Priority and Precedence Tests
    # -------------------------------------------------------------------------

    def test_create_machine_explicit_logic_has_priority(self) -> None:
        """Should use explicit `logic` object even if discoverable logic is provided."""
        logger.info("🧪 Testing that explicit logic has top priority.")
        # 📋 Arrange: Create a mock action and an explicit logic object.
        # Disabling E731 as assigning a lambda is a concise way to create a mock callable for this test.
        mock_action = lambda: "mock"  # noqa: E731
        explicit_logic = MachineLogic(actions={"factory_action": mock_action})

        # 🚀 Act: Provide explicit logic AND discoverable sources.
        machine = create_machine(
            config=_FACTORY_MACHINE_CONFIG,
            logic=explicit_logic,
            logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
            logic_providers=[MyLogicProvider()],
        )

        # ✅ Assert: The machine should use the explicit logic object and its action.
        self.assertIs(machine.logic, explicit_logic)
        self.assertIs(machine.logic.actions["factory_action"], mock_action)

    def test_auto_discovery_last_provider_wins_on_conflict(self) -> None:
        """If providers have same method, the last one in the list is used."""
        logger.info("🧪 Testing conflict resolution among logic providers.")

        # 📋 Arrange: Define two providers with a method of the same name.
        class ProviderA:
            def conflict_action(self) -> str:  # noqa
                return "A"

        class ProviderB:
            def conflict_action(self) -> str:  # noqa
                return "B"

        config = {
            "id": "conflict",
            "initial": "a",
            "states": {"a": {"entry": "conflict_action"}},
        }
        # 🚀 Act: Create the machine with the providers listed in order.
        machine = create_machine(
            config, logic_providers=[ProviderA(), ProviderB()]
        )

        # ✅ Assert: The action should be bound to the instance of the *last* provider (ProviderB).
        action_func = machine.logic.actions["conflict_action"]
        self.assertIn("ProviderB", str(action_func.__self__.__class__))  # noqa

    def test_uses_globally_registered_module(self) -> None:
        """Should discover logic from a module registered globally with LogicLoader."""
        logger.info("🧪 Testing discovery from globally registered module.")
        # 📋 Arrange: Get the loader singleton and register a module globally.
        import temp_factory_logic_module

        loader = LogicLoader.get_instance()
        loader.register_logic_module(temp_factory_logic_module)

        # 🚀 Act: Create the machine without providing any logic sources.
        machine = create_machine(config=_FACTORY_MACHINE_CONFIG)

        # ✅ Assert: The action should be found in the globally registered module.
        self.assertIn("factory_action", machine.logic.actions)

    # -------------------------------------------------------------------------
    # 📉 Edge Case and Invalid Input Tests
    # -------------------------------------------------------------------------

    def test_error_for_non_dict_config(self) -> None:
        """Should raise InvalidConfigError if the config is not a dictionary."""
        logger.info("🧪 Testing error for non-dictionary configuration.")
        # 💥 Act & Assert: Passing a list should raise a specific error.
        with self.assertRaisesRegex(InvalidConfigError, "must be a dict"):
            create_machine([])  # type: ignore

    def test_error_for_non_string_id(self) -> None:
        """Should raise InvalidConfigError if the root 'id' is not a string."""
        logger.info("🧪 Testing error for non-string 'id' value.")
        invalid_config = {"id": 123, "initial": "idle", "states": {"idle": {}}}
        # 💥 Act & Assert: The ID must be a string.
        with self.assertRaises(InvalidConfigError):
            create_machine(invalid_config)

    def test_error_on_empty_string_id(self) -> None:
        """Should raise InvalidConfigError if 'id' is an empty string."""
        logger.info("🧪 Testing error for empty string 'id' value.")
        config = {"id": "", "initial": "idle", "states": {"idle": {}}}
        # 💥 Act & Assert: An empty ID is considered invalid.
        # ✅ FIX: The check for a missing ID (`if not id`) also catches an empty string.
        # The test now correctly asserts the actual error message produced.
        with self.assertRaisesRegex(
            InvalidConfigError, "Machine configuration must have a root 'id'"
        ):
            create_machine(config)

    def test_error_for_non_dict_states(self) -> None:
        """Should raise an actionable error if 'states' is not a dictionary.

        🐛 Regression: this previously asserted a raw `AttributeError`
        ("'list' object has no attribute 'items'") leaking from library
        internals, naming neither the offending state nor the offending key.
        A malformed config is a user error and must be reported as one.
        """
        logger.info("🧪 Testing error for non-dictionary 'states' value.")
        invalid_config = {
            "id": "test",
            "initial": "idle",
            "states": ["idle"],  # This should be a dict
        }
        # 💥 Act & Assert
        with self.assertRaises(InvalidConfigError) as caught:
            create_machine(invalid_config)

        self.assertIn("states", str(caught.exception))

    def test_create_with_empty_logic_modules_list(self) -> None:
        """Should create successfully with an empty logic_modules list."""
        logger.info("🧪 Testing creation with an empty `logic_modules` list.")
        # 🚀 Act: Pass an empty list for modules.
        machine = create_machine(self.valid_config, logic_modules=[])
        # ✅ Assert: Should succeed and result in empty logic.
        self.assertIsNotNone(machine.logic)
        self.assertEqual(len(machine.logic.actions), 0)

    def test_create_with_empty_logic_providers_list(self) -> None:
        """Should create successfully with an empty logic_providers list."""
        logger.info(
            "🧪 Testing creation with an empty `logic_providers` list."
        )
        # 🚀 Act: Pass an empty list for providers.
        machine = create_machine(self.valid_config, logic_providers=[])
        # ✅ Assert: Should succeed and result in empty logic.
        self.assertIsNotNone(machine.logic)
        self.assertEqual(len(machine.logic.actions), 0)

    def test_create_with_empty_states_dict(self) -> None:
        """Should create a machine successfully if 'states' is empty."""
        logger.info("🧪 Testing creation with an empty 'states' dictionary.")
        # 📋 Arrange: Config with an empty but valid states object.
        config = {"id": "empty_states", "initial": "a", "states": {}}
        # 🚀 Act: Create the machine.
        machine = create_machine(config)
        # ✅ Assert: The machine should be created with no state nodes.
        self.assertIsInstance(machine, MachineNode)
        self.assertEqual(len(machine.states), 0)

    def test_accepts_non_machine_logic_instance_at_creation(self) -> None:
        """Should accept a non-MachineLogic object without raising an error at creation."""
        logger.info(
            "🧪 Testing that an invalid `logic` object is accepted without error."
        )

        # 📋 Arrange: A class that is not a `MachineLogic` instance.
        class NotLogic:
            pass

        not_logic_instance = NotLogic()

        # 🚀 Act: Call create_machine with the invalid logic object.
        # No exception is expected here, so we wrap it in a try/fail block
        # to ensure the test fails if any unexpected exception is raised.
        try:
            machine = create_machine(self.valid_config, logic=not_logic_instance)  # type: ignore
        except Exception as e:
            self.fail(f"Factory unexpectedly raised {type(e).__name__}: {e}")

        # ✅ Assert: The machine should be created successfully, and its `logic`
        # attribute should be the exact invalid object that was passed in.
        self.assertIs(machine.logic, not_logic_instance)

    # -------------------------------------------------------------------------
    # ✅ Complex Configuration Tests
    # -------------------------------------------------------------------------

    def test_create_with_nonexistent_initial_state(self) -> None:
        """Should create successfully even if 'initial' state does not exist."""
        logger.info("🧪 Testing creation with a non-existent initial state.")
        config = {
            "id": "test",
            "initial": "nonexistent",
            "states": {"idle": {}},
        }
        # 🚀 Act: The factory's job is creation, not validation of this rule.
        machine = create_machine(config)

        # ✅ Assert: Machine is created, and the `initial` property is set as specified.
        self.assertIsInstance(machine, MachineNode)
        self.assertEqual(machine.initial, "nonexistent")

    def test_create_with_parallel_state_config(self) -> None:
        """Should successfully create a machine with parallel states."""
        logger.info("🧪 Testing creation of a parallel state machine.")
        config = {
            "id": "parallel_test",
            "type": "parallel",
            "states": {
                "a": {"initial": "a1", "states": {"a1": {}}},
                "b": {"initial": "b1", "states": {"b1": {}}},
            },
        }
        # 🚀 Act: Create the parallel machine.
        machine = create_machine(config)

        # ✅ Assert: The root node's type should be 'parallel'.
        self.assertIsInstance(machine, MachineNode)
        self.assertEqual(machine.type, "parallel")

    def test_create_with_final_state_config(self) -> None:
        """Should successfully create a machine containing a final state."""
        logger.info("🧪 Testing creation of a machine with a final state.")
        config = {
            "id": "final_test",
            "initial": "active",
            "states": {
                "active": {"on": {"END": "finished"}},
                "finished": {"type": "final"},
            },
        }
        # 🚀 Act: Create the machine.
        machine = create_machine(config)
        # ✅ Assert: The 'finished' state node should be correctly identified as final.
        finished_state = machine.get_state_by_id("final_test.finished")
        self.assertIsNotNone(finished_state)
        self.assertTrue(finished_state.is_final)

    def test_create_with_invoke_config(self) -> None:
        """Should successfully create a machine with an invoked service."""
        logger.info(
            "🧪 Testing creation of a machine with an invoke definition."
        )
        config = {
            "id": "invoke_test",
            "initial": "fetching",
            "states": {
                "fetching": {"invoke": {"src": "fetchData", "onDone": "idle"}},
                "idle": {},
            },
        }
        # 🚀 Act: The new logic validator requires implementations to be present at creation time.
        # ✅ FIX: Provide a dummy implementation for the 'fetchData' service to satisfy
        # the validator, allowing the test to pass.
        dummy_logic = MachineLogic(services={"fetchData": lambda: None})
        machine = create_machine(config, logic=dummy_logic)

        # ✅ Assert: The 'fetching' state should have the invoke config attached.
        fetching_state = machine.get_state_by_id("invoke_test.fetching")
        self.assertIsNotNone(fetching_state)
        self.assertEqual(len(fetching_state.invoke), 1)  # type: ignore
        self.assertEqual(fetching_state.invoke[0].src, "fetchData")  # type: ignore

    def test_create_with_deeply_nested_states(self) -> None:
        """Should not fail when creating a machine with deeply nested states."""
        logger.info("🧪 Testing creation with deeply nested state nodes.")
        # 📋 Arrange: A config with states nested four levels deep.
        config = {
            "id": "deep",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "b",
                    "states": {
                        "b": {
                            "initial": "c",
                            "states": {
                                "c": {"initial": "d", "states": {"d": {}}}
                            },
                        }
                    },
                }
            },
        }
        # 🚀 Act: Create the machine.
        machine = create_machine(config)
        # ✅ Assert: The deepest state node should be retrievable by its full ID.
        self.assertIsNotNone(machine.get_state_by_id("deep.a.b.c.d"))


if __name__ == "__main__":
    # 🏃‍♂️ To run the tests with verbose output, execute this script directly.
    unittest.main(verbosity=2)
