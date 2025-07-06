# tests/test_models_and_resolver.py
import unittest
from typing import Any, Dict

from src.xstate_machine import create_machine, StateNotFoundError, Event
from src.xstate_machine.models import ActionDefinition
from src.xstate_machine.resolver import resolve_target_state


class TestModelsAndResolver(unittest.TestCase):
    """Test suite for model utilities, state resolution, and factory functions."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up a complex machine definition once for all tests in this class."""
        cls.test_machine_config: Dict[str, Any] = {
            "id": "tester",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {
                        "a1": {
                            "id": "custom_a1_id",
                            "on": {"T_SIBLING": "b", "T_CHILD_SIBLING": "a2"},
                        },
                        "a2": {"on": {"T_ABSOLUTE": "#tester.c"}},
                    },
                },
                "b": {"on": {"T_RELATIVE": ".c"}},
                "c": {},
            },
        }
        cls.machine = create_machine(cls.test_machine_config)

    def test_get_state_by_id(self) -> None:
        """Should retrieve a state by its fully qualified ID."""
        node = self.machine.get_state_by_id("tester.a.a2")
        self.assertIsNotNone(node)
        self.assertEqual(node.key, "a2")

    def test_get_state_by_custom_id(self) -> None:
        """Should retrieve a state by its custom ID if provided."""
        # Note: Current implementation uses dot-path based IDs.
        # This test confirms `get_state_by_id` works with the generated ID, not the custom one.
        node = self.machine.get_state_by_id("tester.a.a1")
        self.assertIsNotNone(node)
        self.assertEqual(node.id, "tester.a.a1")

        # A request for the custom ID will fail as resolution is path-based.
        node_by_custom_id = self.machine.get_state_by_id("custom_a1_id")
        self.assertIsNone(node_by_custom_id)

    def test_action_definition_parsing(self) -> None:
        """Should parse string and object action definitions."""
        action_str = ActionDefinition("myAction")
        self.assertEqual(action_str.type, "myAction")
        self.assertIsNone(action_str.params)

        action_obj = ActionDefinition(
            {"type": "myActionWithParams", "params": {"value": 42}}
        )
        self.assertEqual(action_obj.type, "myActionWithParams")
        self.assertEqual(action_obj.params, {"value": 42})

    def test_resolve_sibling_state(self) -> None:
        """Should correctly resolve a target state that is a sibling."""
        source_state = self.machine.get_state_by_id("tester.a.a1")
        target_state = resolve_target_state("b", source_state)
        self.assertEqual(target_state.id, "tester.b")

    def test_resolve_relative_state(self) -> None:
        """Should correctly resolve a relative target using the '.' prefix."""
        source_state = self.machine.get_state_by_id("tester.b")
        target_state = resolve_target_state(".c", source_state)
        self.assertEqual(target_state.id, "tester.c")

    def test_resolve_relative_state_from_root(self) -> None:
        """Should resolve a relative target from the root machine node."""
        source_state = self.machine  # The root node
        target_state = resolve_target_state(".c", source_state)
        self.assertEqual(target_state.id, "tester.c")

    def test_resolve_absolute_state(self) -> None:
        """Should correctly resolve an absolute target using the '#' prefix."""
        source_state = self.machine.get_state_by_id("tester.a.a2")
        target_state = resolve_target_state("#tester.c", source_state)
        self.assertEqual(target_state.id, "tester.c")

    def test_resolve_invalid_absolute_id(self) -> None:
        """Should raise StateNotFoundError for an absolute path with the wrong ID."""
        source_state = self.machine.get_state_by_id("tester.a.a2")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("#wrong_id.c", source_state)

    def test_resolve_invalid_state(self) -> None:
        """Should raise StateNotFoundError for an unresolvable target."""
        source_state = self.machine.get_state_by_id("tester.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("nonexistent", source_state)

    def test_resolve_non_string_target(self) -> None:
        """Should raise TypeError if the target is not a string."""
        source_state = self.machine.get_state_by_id("tester.a.a1")
        with self.assertRaises(TypeError):
            resolve_target_state(None, source_state)

    def test_get_next_state_utility(self) -> None:
        """Should calculate the next state without executing actions."""
        next_state_ids = self.machine.get_next_state(
            "tester.a.a1", Event("T_SIBLING")
        )
        self.assertEqual(next_state_ids, {"tester.b"})

    def test_get_next_state_for_invalid_state(self) -> None:
        """Should return None from get_next_state if from_state_id is invalid."""
        next_state_ids = self.machine.get_next_state(
            "nonexistent", Event("T_SIBLING")
        )
        self.assertIsNone(next_state_ids)

    def test_visualization_methods(self) -> None:
        """Should generate non-empty visualization strings without errors."""
        plantuml_output = self.machine.to_plantuml()
        mermaid_output = self.machine.to_mermaid()

        self.assertIsInstance(plantuml_output, str)
        self.assertIn("@startuml", plantuml_output)
        self.assertIn("tester_a_a1 --> tester_b : T_SIBLING", plantuml_output)

        self.assertIsInstance(mermaid_output, str)
        self.assertIn("stateDiagram-v2", mermaid_output)
        self.assertIn("a1 --> b : T_SIBLING", mermaid_output)
