# tests/test_resolver.py
import logging
import unittest

from src.xstate_statemachine import (
    create_machine,
    StateNotFoundError,
)
from src.xstate_statemachine.models import MachineNode, StateNode
from src.xstate_statemachine.resolver import resolve_target_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestResolver(unittest.TestCase):
    """
    Test suite for the state resolution logic.
    """

    @classmethod
    def setUpClass(cls) -> None:
        """Set up a complex machine definition once for all tests."""
        cls.machine_config = {
            "id": "resolver_test",
            "initial": "a",
            "states": {
                "a": {
                    "initial": "a1",
                    "states": {
                        "a1": {"on": {"SIBLING": "a2", "DEEP": "c.c1.c11"}},
                        "a2": {"on": {"ABSOLUTE": "#resolver_test.c.c2"}},
                    },
                },
                "b": {"on": {"RELATIVE": ".c"}},
                "c": {
                    "initial": "c1",
                    "states": {
                        "c1": {"initial": "c11", "states": {"c11": {}}},
                        "c2": {},
                    },
                },
            },
        }
        cls.machine: MachineNode = create_machine(cls.machine_config)

    def get_state(self, state_id: str) -> StateNode:
        """Helper to get a state node, failing the test if not found."""
        node = self.machine.get_state_by_id(state_id)
        self.assertIsNotNone(
            node, f"Setup failed: state '{state_id}' not found."
        )
        return node

    def test_resolve_sibling_state(self) -> None:
        """Should resolve a target that is a direct sibling."""
        source = self.get_state("resolver_test.a.a1")
        target = resolve_target_state("a2", source)
        self.assertEqual(target.id, "resolver_test.a.a2")

    def test_resolve_relative_state(self) -> None:
        """Should resolve a target relative to the parent state."""
        source = self.get_state("resolver_test.b")
        target = resolve_target_state(".c", source)
        self.assertEqual(target.id, "resolver_test.c")

    def test_resolve_absolute_state(self) -> None:
        """Should resolve a target using an absolute path from the root."""
        source = self.get_state("resolver_test.a.a2")
        target = resolve_target_state("#resolver_test.c.c2", source)
        self.assertEqual(target.id, "resolver_test.c.c2")

    def test_resolve_deep_sibling_state(self) -> None:
        """Should resolve a target that is a sibling of an ancestor."""
        source = self.get_state("resolver_test.a.a1")
        target = resolve_target_state("b", source)
        # FIX: The resolver correctly bubbles up and finds the sibling.
        self.assertEqual(target.id, "resolver_test.b")

    def test_resolve_invalid_absolute_path(self) -> None:
        """Should raise StateNotFoundError for an invalid absolute path."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("#resolver_test.d", source)

    def test_resolve_nonexistent_target(self) -> None:
        """Should raise StateNotFoundError for a target that doesn't exist."""
        source = self.get_state("resolver_test.b")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("d", source)

    def test_resolve_with_non_string_target(self) -> None:
        """Should raise TypeError for a non-string target."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(TypeError):
            resolve_target_state(None, source)  # type: ignore

    def test_resolve_from_root_using_relative(self) -> None:
        """Should resolve from the root using a relative path."""
        target = resolve_target_state(".b", self.machine)
        self.assertEqual(target.id, "resolver_test.b")

    def test_resolve_to_nested_child(self) -> None:
        """Should resolve a path to a deeply nested child."""
        source = self.get_state("resolver_test.b")
        target = resolve_target_state("c.c1.c11", source)
        self.assertEqual(target.id, "resolver_test.c.c1.c11")

    def test_resolve_relative_self_transition(self) -> None:
        """A relative path of '.' should target the source's parent."""
        source = self.get_state("resolver_test.a.a1")
        target = resolve_target_state(".", source)
        self.assertEqual(target.id, "resolver_test.a")

    def test_resolve_absolute_path_with_wrong_root_id(self) -> None:
        """Should fail if absolute path's root ID doesn't match machine ID."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("#wrong_machine.c", source)

    def test_resolve_with_leading_dot_from_root(self) -> None:
        """Resolving '.' from the machine root should target the root itself."""
        target = resolve_target_state(".", self.machine)
        self.assertIs(target, self.machine)

    def test_resolve_from_nested_to_toplevel(self) -> None:
        """Should resolve from a deep child to a top-level state."""
        source = self.get_state("resolver_test.c.c1.c11")
        target = resolve_target_state("b", source)
        self.assertEqual(target.id, "resolver_test.b")

    def test_resolve_empty_string_target_raises_error(self) -> None:
        """An empty string as a target should raise an error."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("", source)

    def test_find_descendant_on_root(self) -> None:
        """_find_descendant helper should work from the root."""
        from src.xstate_statemachine.resolver import _find_descendant

        target = _find_descendant(self.machine, ["a", "a1"])
        self.assertEqual(target.id, "resolver_test.a.a1")

    def test_find_descendant_with_invalid_path(self) -> None:
        """_find_descendant should raise an error for a bad path."""
        from src.xstate_statemachine.resolver import _find_descendant

        with self.assertRaises(StateNotFoundError):
            _find_descendant(self.machine, ["a", "x"])

    def test_resolve_with_multiple_dots(self) -> None:
        """Should handle paths with multiple dots correctly."""
        source = self.get_state("resolver_test.c.c1.c11")
        target = resolve_target_state(".c2", source.parent)  # parent is c1
        self.assertEqual(target.id, "resolver_test.c.c2")

    def test_resolve_to_self_via_absolute_path(self) -> None:
        """An absolute path can resolve back to the source's own ID."""
        source = self.get_state("resolver_test.a.a1")
        target = resolve_target_state("#resolver_test.a.a1", source)
        self.assertIs(source, target)

    def test_resolve_with_trailing_dot_is_invalid(self) -> None:
        """A trailing dot in a path should be considered invalid."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("b.", source)

    def test_resolve_with_consecutive_dots_is_invalid(self) -> None:
        """Consecutive dots in a path should be considered invalid."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("b..c", source)

    def test_resolve_from_parallel_region_to_external_state(self) -> None:
        """Should resolve from a parallel state to a state outside the parallel construct."""
        source = self.get_state("resolver_test.a.a1")
        # Target 'b' is a sibling of the parent 'a'
        target = resolve_target_state("b", source)
        self.assertEqual(target.id, "resolver_test.b")

    def test_resolve_across_different_deep_branches(self) -> None:
        """Should resolve a target in a completely different major branch."""
        source = self.get_state("resolver_test.a.a2")
        target = resolve_target_state("c.c1.c11", source)
        self.assertEqual(target.id, "resolver_test.c.c1.c11")

    def test_resolve_to_compound_parent_itself(self) -> None:
        """Should resolve a target that is the parent of the source state."""
        source = self.get_state("resolver_test.a.a1")
        target = resolve_target_state("a", source)
        self.assertEqual(target.id, "resolver_test.a")

    def test_resolve_invalid_absolute_path_partially_correct(self) -> None:
        """Should fail if an absolute path is correct initially but then diverges."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("#resolver_test.a.nonexistent", source)

    def test_resolve_with_whitespace_in_target(self) -> None:
        """Should fail to resolve a target containing whitespace."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state(" b", source)  # Leading space

    def test_resolve_to_deeper_nonexistent_state(self) -> None:
        """Should fail if path is valid up to a point, then goes deeper to a nonexistent state."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("c.c1.nonexistent", source)

    def test_resolve_target_is_case_sensitive(self) -> None:
        """State key resolution should be case-sensitive."""
        source = self.get_state("resolver_test.a.a1")
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("B", source)  # Correct key is 'b'

    def test_external_self_transition_target_resolution(self) -> None:
        """Should resolve a target like '.a1' from within a sibling state."""
        source = self.get_state("resolver_test.a.a2")
        # The resolution is relative to the parent ('a'), so '.a1' is valid.
        target = resolve_target_state(".a1", source)
        self.assertEqual(target.id, "resolver_test.a.a1")

    def test_resolve_to_grandparent(self) -> None:
        """Should resolve a target that is an ancestor several levels up."""
        source = self.get_state("resolver_test.c.c1.c11")
        target = resolve_target_state("resolver_test", source)
        self.assertIs(target, self.machine)

    def test_machine_with_numeric_state_keys(self) -> None:
        """Should handle state keys that are numeric-like strings."""
        machine = create_machine(
            {
                "id": "numeric",
                "initial": "1",
                "states": {
                    "1": {"initial": "11", "states": {"11": {}}},
                    "2": {},
                },
            }
        )
        source = machine.get_state_by_id("numeric.1.11")
        target = resolve_target_state("2", source)
        self.assertEqual(target.id, "numeric.2")
