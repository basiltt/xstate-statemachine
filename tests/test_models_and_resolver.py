# tests/test_models_and_resolver.py
import unittest
from typing import Any, Dict

from src.xstate_machine import (
    Event,
    InvalidConfigError,
    MachineLogic,
    StateNotFoundError,
    create_machine,
)
from src.xstate_machine.resolver import resolve_target_state


# -----------------------------------------------------------------------------
# 🧪 Test Suite for Static Machine Analysis
# -----------------------------------------------------------------------------
# This suite tests the non-running aspects of the state machine: its creation,
# the correctness of its structure, and its utility methods. These tests are
# synchronous and focus on validating the static machine definition.
# -----------------------------------------------------------------------------


class TestModelsAndResolver(unittest.TestCase):
    """Test suite for model utilities, state resolution, and factory functions."""

    @classmethod
    def setUpClass(cls) -> None:
        """Set up a complex machine definition once for all tests in this class.

        This follows the DRY principle by creating a shared resource for tests
        that analyze the machine's static structure.
        """
        # Ⓐ Arrange: Define a machine with nested states for testing resolution.
        cls.test_machine_config: Dict[str, Any] = {
            "id": "tester",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {
                        "a1": {
                            "on": {"T_SIBLING": "b", "T_CHILD_SIBLING": "a2"}
                        },
                        "a2": {"on": {"T_ABSOLUTE": "#tester.c"}},
                    },
                },
                "b": {
                    "on": {"T_RELATIVE": ".c"}
                },  # From b, .c resolves to tester.c
                "c": {},
            },
        }
        cls.machine = create_machine(cls.test_machine_config)

    # -------------------------------------------------------------------------
    # Factory Tests (`create_machine`)
    # -------------------------------------------------------------------------

    def test_create_machine_invalid_config(self) -> None:
        """Should raise InvalidConfigError for malformed machine definitions."""
        # 🧪 Test case: Config missing the 'states' key.
        with self.assertRaises(InvalidConfigError):
            create_machine({"id": "bad"})

        # 🧪 Test case: Config missing the 'id' key.
        with self.assertRaises(InvalidConfigError):
            create_machine({"states": {}})

    # -------------------------------------------------------------------------
    # Resolver Tests (`resolve_target_state`)
    # -------------------------------------------------------------------------

    def test_resolve_sibling_state(self) -> None:
        """Should correctly resolve a target state that is a sibling."""
        # Ⓐ Arrange: Get the source state 'a.a1'.
        source_state = self.machine.get_state_by_id("tester.a.a1")
        self.assertIsNotNone(source_state)

        # 🚀 Act: Resolve the target string 'b', which is a sibling of 'a'.
        target_state = resolve_target_state("b", source_state)

        # ✅ Assert: The target state ID should be 'tester.b'.
        self.assertEqual(target_state.id, "tester.b")

    def test_resolve_relative_state(self) -> None:
        """Should correctly resolve a relative target using the '.' prefix."""
        # Ⓐ Arrange: Get the source state 'b'.
        source_state = self.machine.get_state_by_id("tester.b")
        self.assertIsNotNone(source_state)

        # 🚀 Act: Resolve the relative target '.c' from state 'b'.
        # The resolver starts from the parent ('tester') and looks for 'c'.
        target_state = resolve_target_state(".c", source_state)

        # ✅ Assert: The target state ID should be 'tester.c'.
        self.assertEqual(target_state.id, "tester.c")

    def test_resolve_absolute_state(self) -> None:
        """Should correctly resolve an absolute target using the '#' prefix."""
        # Ⓐ Arrange: Get the source state 'a.a2'.
        source_state = self.machine.get_state_by_id("tester.a.a2")
        self.assertIsNotNone(source_state)

        # 🚀 Act: Resolve the absolute target '#tester.c'.
        target_state = resolve_target_state("#tester.c", source_state)

        # ✅ Assert: The target state ID should be 'tester.c'.
        self.assertEqual(target_state.id, "tester.c")

    def test_resolve_invalid_state(self) -> None:
        """Should raise StateNotFoundError for an unresolvable target."""
        # Ⓐ Arrange: Get the source state 'a.a1'.
        source_state = self.machine.get_state_by_id("tester.a.a1")

        # 🚀 Act & ✅ Assert: Check that resolving a non-existent state raises the correct error.
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("nonexistent", source_state)

    # -------------------------------------------------------------------------
    # Model Utility Tests (`MachineNode` methods)
    # -------------------------------------------------------------------------

    def test_get_next_state_utility(self) -> None:
        """Should calculate the next state without executing actions."""
        # 🚀 Act: Get the next state from 'a.a1' on event 'T_SIBLING'.
        next_state_ids = self.machine.get_next_state(
            from_state_id="tester.a.a1", event=Event("T_SIBLING")
        )
        # ✅ Assert: The purely calculated next state is correct.
        self.assertEqual(next_state_ids, {"tester.b"})

    def test_visualization_methods(self) -> None:
        """Should generate non-empty visualization strings without errors."""
        # 🚀 Act: Generate diagram strings.
        plantuml_output = self.machine.to_plantuml()
        mermaid_output = self.machine.to_mermaid()

        # ✅ Assert: The outputs are valid strings and contain expected content.
        self.assertIsInstance(plantuml_output, str)
        self.assertIn("@startuml", plantuml_output)
        self.assertIn("a1 --> tester_b : T_SIBLING", plantuml_output)

        self.assertIsInstance(mermaid_output, str)
        self.assertIn("stateDiagram-v2", mermaid_output)
        self.assertIn("a1 --> b : T_SIBLING", mermaid_output)
