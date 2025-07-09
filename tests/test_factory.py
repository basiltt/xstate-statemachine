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
from typing import Callable

from src.xstate_statemachine import (
    InvalidConfigError,
    LogicLoader,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import MachineNode
from xstate_statemachine import ImplementationMissingError

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

        def test_error_for_non_dict_config(self) -> None:
            """Should raise InvalidConfigError if the config is not a dictionary."""
            with self.assertRaisesRegex(InvalidConfigError, "must be a dict"):
                create_machine([])  # type: ignore

        def test_error_for_non_string_id(self) -> None:
            """Should raise InvalidConfigError if the root 'id' is not a string."""
            invalid_config = {
                "id": 123,
                "initial": "idle",
                "states": {"idle": {}},
            }
            # This error is raised from the MachineNode constructor.
            with self.assertRaises(InvalidConfigError):
                create_machine(invalid_config)

        def test_error_for_non_dict_states(self) -> None:
            """Should raise an error if 'states' is not a dictionary."""
            invalid_config = {
                "id": "test",
                "initial": "idle",
                "states": ["idle"],
            }
            # The parser expects a dict for states to iterate over .items()
            with self.assertRaises(Exception):
                create_machine(invalid_config)

        def test_create_with_nonexistent_initial_state(self) -> None:
            """Should create successfully even if 'initial' state does not exist."""
            config = {
                "id": "test",
                "initial": "nonexistent",
                "states": {"idle": {}},
            }
            # The factory is responsible for creation, not validation of initial state.
            machine = create_machine(config)
            self.assertIsInstance(machine, MachineNode)
            self.assertEqual(machine.initial, "nonexistent")

        def test_create_with_parallel_state_config(self) -> None:
            """Should successfully create a machine with parallel states."""
            config = {
                "id": "parallel_test",
                "type": "parallel",
                "states": {
                    "a": {"initial": "a1", "states": {"a1": {}}},
                    "b": {"initial": "b1", "states": {"b1": {}}},
                },
            }
            machine = create_machine(config)
            self.assertIsInstance(machine, MachineNode)
            self.assertEqual(machine.type, "parallel")

        def test_create_with_final_state_config(self) -> None:
            """Should successfully create a machine containing a final state."""
            config = {
                "id": "final_test",
                "initial": "active",
                "states": {
                    "active": {"on": {"END": "finished"}},
                    "finished": {"type": "final"},
                },
            }
            machine = create_machine(config)
            self.assertIsNotNone(
                machine.get_state_by_id("final_test.finished")
            )
            self.assertTrue(machine.get_state_by_id("final_test.finished").is_final)  # type: ignore

        def test_create_with_invoke_config(self) -> None:
            """Should successfully create a machine with an invoked service."""
            config = {
                "id": "invoke_test",
                "initial": "fetching",
                "states": {
                    "fetching": {
                        "invoke": {"src": "fetchData", "onDone": "idle"}
                    },
                    "idle": {},
                },
            }
            # We only need to provide logic if we run it. Creation should succeed without.
            machine = create_machine(config)
            fetching_state = machine.get_state_by_id("invoke_test.fetching")
            self.assertIsNotNone(fetching_state)
            self.assertEqual(len(fetching_state.invoke), 1)  # type: ignore
            self.assertEqual(fetching_state.invoke[0].src, "fetchData")  # type: ignore

        def test_auto_discovery_with_mixed_providers_and_modules(self) -> None:
            """Should discover logic from both logic_modules and logic_providers."""

            class MixedProvider:
                def mixed_action(self):
                    pass

            config = {
                "id": "mixed_discovery",
                "initial": "active",
                "states": {
                    "active": {"entry": ["factory_action", "mixed_action"]}
                },
            }
            machine = create_machine(
                config,
                logic_modules=[_TEST_FACTORY_LOGIC_MODULE_NAME],
                logic_providers=[MixedProvider()],
            )
            self.assertIn("factory_action", machine.logic.actions)
            self.assertIn("mixed_action", machine.logic.actions)

        def test_auto_discovery_last_provider_wins_on_conflict(self) -> None:
            """If multiple providers have the same method, the last one in the list should be used."""

            class ProviderA:
                def conflict_action(self):
                    return "A"

            class ProviderB:
                def conflict_action(self):
                    return "B"

            config = {
                "id": "conflict",
                "initial": "a",
                "states": {"a": {"entry": "conflict_action"}},
            }
            machine = create_machine(
                config, logic_providers=[ProviderA(), ProviderB()]
            )

            # We can't easily test the return value here, but we can check the bound method's class.
            action_func = machine.logic.actions["conflict_action"]
            self.assertIn("ProviderB", str(action_func.__self__.__class__))  # type: ignore

        def test_auto_discovery_ignores_private_functions(self) -> None:
            """Should ignore functions starting with an underscore and raise ImplementationMissingError."""
            with open("private_logic.py", "w") as f:
                f.write("def _private_action(): pass")

            config = {
                "id": "private",
                "initial": "a",
                "states": {"a": {"entry": "_private_action"}},
            }

            with self.assertRaises(ImplementationMissingError):
                create_machine(config, logic_modules=["private_logic"])

            os.remove("private_logic.py")

        def test_create_with_empty_logic_modules_list(self) -> None:
            """Should create successfully with an empty logic_modules list."""
            machine = create_machine(self.valid_config, logic_modules=[])
            self.assertIsNotNone(machine.logic)
            self.assertEqual(len(machine.logic.actions), 0)

        def test_create_with_empty_logic_providers_list(self) -> None:
            """Should create successfully with an empty logic_providers list."""
            machine = create_machine(self.valid_config, logic_providers=[])
            self.assertIsNotNone(machine.logic)
            self.assertEqual(len(machine.logic.actions), 0)

        def test_uses_globally_registered_module(self) -> None:
            """Should discover logic from a module registered globally with the LogicLoader."""
            import temp_factory_logic_module

            loader = LogicLoader.get_instance()
            loader.register_logic_module(temp_factory_logic_module)

            machine = create_machine(config=_FACTORY_MACHINE_CONFIG)
            self.assertIn("factory_action", machine.logic.actions)

        def test_error_on_empty_string_id(self) -> None:
            """Should raise InvalidConfigError if 'id' is an empty string."""
            config = {"id": "", "initial": "idle", "states": {"idle": {}}}
            with self.assertRaisesRegex(
                InvalidConfigError, "'id' and 'states' keys"
            ):
                create_machine(config)

        def test_create_with_empty_states_dict(self) -> None:
            """Should create a machine successfully if the 'states' dictionary is empty."""
            config = {"id": "empty_states", "initial": "a", "states": {}}
            machine = create_machine(config)
            self.assertIsInstance(machine, MachineNode)
            self.assertEqual(len(machine.states), 0)

        def test_create_with_deeply_nested_states(self) -> None:
            """Should not fail when creating a machine with deeply nested state nodes."""
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
            machine = create_machine(config)
            self.assertIsNotNone(machine.get_state_by_id("deep.a.b.c.d"))

        def test_auto_discovery_with_guards_and_services(self) -> None:
            """Should correctly discover and categorize guards and services."""
            logic_content = """
    def discovered_action(): pass
    def discovered_guard(): return True
    async def discovered_service(): return {}
    """
            with open("full_logic.py", "w") as f:
                f.write(logic_content)

            config = {
                "id": "full",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "NEXT": {
                                "target": "b",
                                "guard": "discovered_guard",
                            }
                        },
                        "invoke": {"src": "discovered_service", "onDone": "c"},
                    },
                    "b": {"entry": "discovered_action"},
                    "c": {},
                },
            }
            machine = create_machine(config, logic_modules=["full_logic"])
            self.assertIn("discovered_action", machine.logic.actions)
            self.assertIn("discovered_guard", machine.logic.guards)
            self.assertIn("discovered_service", machine.logic.services)

            os.remove("full_logic.py")

        def test_error_when_logic_is_not_a_machinelogic_instance(self) -> None:
            """Should raise a TypeError if the explicit logic parameter is not a MachineLogic object."""

            class NotLogic:
                pass

            with self.assertRaises(TypeError):
                # This check happens inside the interpreter, but the factory's type hint should catch it.
                # Let's test the factory's robustness. The factory itself doesn't check the type,
                # but this test documents the expected type contract.
                # A static type checker would flag this.
                create_machine(self.valid_config, logic=NotLogic())  # type: ignore

        def test_machine_with_id_only_is_invalid(self) -> None:
            """Should raise InvalidConfigError if 'states' key is missing."""
            with self.assertRaisesRegex(
                InvalidConfigError, "'id' and 'states' keys"
            ):
                create_machine({"id": "only_id"})

        def test_machine_with_states_only_is_invalid(self) -> None:
            """Should raise InvalidConfigError if 'id' key is missing."""
            with self.assertRaisesRegex(
                InvalidConfigError, "must have a root 'id'"
            ):
                create_machine({"states": {"a": {}}})


if __name__ == "__main__":
    unittest.main(verbosity=2)
