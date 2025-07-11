# /tests/test_resolver.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: State Target Resolution
# -----------------------------------------------------------------------------
# This module provides a comprehensive test suite for the `resolve_target_state`
# function, which is responsible for interpreting state transition targets
# according to XState specifications.
#
# The suite validates the resolver's ability to correctly handle various
# target formats:
#   - Sibling states (e.g., "state2").
#   - Relative paths from the source's parent (e.g., ".state2").
#   - Absolute paths from the machine's root (e.g., "#machine.state.state2").
#   - Deeply nested paths and transitions between different branches.
#
# It also ensures robust error handling for invalid, non-existent, or
# malformed target strings, guaranteeing predictable behavior during state
# machine execution.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.exceptions import StateNotFoundError

from src.xstate_statemachine.models import MachineNode, StateNode
from src.xstate_statemachine.resolver import (
    _find_descendant,
    resolve_target_state,
)
from src.xstate_statemachine import create_machine

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configures a basic logger to show informative messages during test execution.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestResolver
# -----------------------------------------------------------------------------


class TestResolver(unittest.TestCase):
    """A test suite for the state resolution logic.

    This class sets up a single, complex state machine and uses it to test
    various state target resolution scenarios, from simple sibling lookups
    to complex absolute and relative path resolutions.
    """

    machine: MachineNode

    # -------------------------------------------------------------------------
    # ♻️ Test Lifecycle & Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def setUpClass(cls) -> None:
        """Sets up a complex machine definition once for all tests.

        This method creates a shared `MachineNode` instance that serves as
        the foundation for all resolution tests, improving efficiency by
        avoiding repeated machine creation.
        """
        logger.info("🛠️ Creating shared state machine for resolver tests...")
        machine_config = {
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
                "b": {},
                "c": {
                    "initial": "c1",
                    "states": {
                        "c1": {"initial": "c11", "states": {"c11": {}}},
                        "c2": {},
                    },
                },
            },
        }
        cls.machine = create_machine(machine_config)

    def get_state(self, state_id: str) -> StateNode:
        """A helper to retrieve a state node by its full ID.

        This utility simplifies the "Arrange" step of tests by providing a
        consistent way to get state nodes, while also ensuring that test
        setup failures are clearly reported.

        Args:
            state_id: The fully qualified ID of the state to retrieve.

        Returns:
            The `StateNode` instance corresponding to the given ID.

        Raises:
            AssertionError: If the state node cannot be found, failing the test.
        """
        node = self.machine.get_state_by_id(state_id)
        self.assertIsNotNone(
            node, f"❌ Setup failed: state '{state_id}' not found."
        )
        assert node is not None  # Helps the type checker.
        return node

    # -------------------------------------------------------------------------
    # 🎯 Standard Path Resolution Tests
    # -------------------------------------------------------------------------

    def test_resolve_sibling_state(self) -> None:
        """Should resolve a target that is a direct sibling of the source."""
        logger.info("🧪 Testing resolution of a direct sibling state.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act
        target = resolve_target_state("a2", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.a.a2")

    def test_resolve_deep_sibling_state(self) -> None:
        """Should resolve a target that is a sibling of an ancestor state."""
        logger.info("🧪 Testing resolution by bubbling up to find a sibling.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act: Target "b" is a sibling of "a", which is the parent of "a1".
        target = resolve_target_state("b", source)
        # ✅ Assert: The resolver correctly bubbles up and finds the sibling.
        self.assertEqual(target.id, "resolver_test.b")

    def test_resolve_to_nested_child(self) -> None:
        """Should resolve a path to a deeply nested child from an ancestor."""
        logger.info("🧪 Testing resolution of a deeply nested child path.")
        # 📋 Arrange
        source = self.get_state("resolver_test.b")
        # 🚀 Act
        target = resolve_target_state("c.c1.c11", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.c.c1.c11")

    def test_resolve_from_nested_to_toplevel(self) -> None:
        """Should resolve from a deep child to a top-level state."""
        logger.info(
            "🧪 Testing resolution from a deep child to a top-level state."
        )
        # 📋 Arrange
        source = self.get_state("resolver_test.c.c1.c11")
        # 🚀 Act
        target = resolve_target_state("b", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.b")

    def test_resolve_to_compound_parent_itself(self) -> None:
        """Should resolve a target that is the parent of the source state."""
        logger.info("🧪 Testing resolution to the immediate parent.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act
        target = resolve_target_state("a", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.a")

    def test_resolve_to_grandparent(self) -> None:
        """Should resolve a target that is an ancestor several levels up."""
        logger.info("🧪 Testing resolution to a grandparent state.")
        # 📋 Arrange
        source = self.get_state("resolver_test.c.c1.c11")
        # 🚀 Act: The target "resolver_test" is the root machine node.
        target = resolve_target_state("resolver_test", source)
        # ✅ Assert
        self.assertIs(target, self.machine)

    def test_resolve_across_different_deep_branches(self) -> None:
        """Should resolve a target in a completely different major branch."""
        logger.info(
            "🧪 Testing resolution across different top-level branches."
        )
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a2")
        # 🚀 Act
        target = resolve_target_state("c.c1.c11", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.c.c1.c11")

    # -------------------------------------------------------------------------
    # 🏞️ Relative Path Resolution Tests (.)
    # -------------------------------------------------------------------------

    def test_resolve_relative_state(self) -> None:
        """Should resolve a target relative to the source's parent state."""
        logger.info("🧪 Testing relative path resolution (e.g., '.c').")
        # 📋 Arrange
        source = self.get_state("resolver_test.b")
        # 🚀 Act: ".c" means "c" is a child of the source's parent (the root).
        target = resolve_target_state(".c", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.c")

    def test_resolve_from_root_using_relative(self) -> None:
        """Should resolve from the root using a relative path."""
        logger.info(
            "🧪 Testing relative path resolution from the machine root."
        )
        # 🚀 Act: From the root, ".b" resolves to the child "b".
        target = resolve_target_state(".b", self.machine)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.b")

    def test_resolve_relative_self_transition(self) -> None:
        """A relative path of '.' should target the source's parent."""
        logger.info("🧪 Testing relative self-transition ('.').")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act: A single dot refers to the parent state.
        target = resolve_target_state(".", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.a")

    def test_resolve_with_leading_dot_from_root(self) -> None:
        """Resolving '.' from the machine root should target the root itself."""
        logger.info("🧪 Testing resolution of '.' from the machine root.")
        # 🚀 Act: From the root, a single dot refers to the root itself.
        target = resolve_target_state(".", self.machine)
        # ✅ Assert
        self.assertIs(target, self.machine)

    def test_external_self_transition_target_resolution(self) -> None:
        """Should resolve a target like '.a1' from within a sibling state."""
        logger.info("🧪 Testing relative resolution to a sibling's child.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a2")
        # 🚀 Act: The resolution is relative to the parent 'a', so '.a1' is valid.
        target = resolve_target_state(".a1", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.a.a1")

    # -------------------------------------------------------------------------
    # #️⃣ Absolute Path Resolution Tests (#)
    # -------------------------------------------------------------------------

    def test_resolve_absolute_state(self) -> None:
        """Should resolve a target using an absolute path from the root."""
        logger.info("🧪 Testing absolute path resolution (e.g., '#id.state').")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a2")
        # 🚀 Act
        target = resolve_target_state("#resolver_test.c.c2", source)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.c.c2")

    def test_resolve_to_self_via_absolute_path(self) -> None:
        """An absolute path can resolve back to the source's own ID."""
        logger.info("🧪 Testing absolute path resolution to self.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act
        target = resolve_target_state("#resolver_test.a.a1", source)
        # ✅ Assert
        self.assertIs(source, target)

    # -------------------------------------------------------------------------
    # 💥 Error Handling and Invalid Path Tests
    # -------------------------------------------------------------------------

    def test_resolve_invalid_absolute_path(self) -> None:
        """Should raise StateNotFoundError for an invalid absolute path."""
        logger.info("🧪 Testing error for an invalid absolute path.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("#resolver_test.d", source)

    def test_resolve_absolute_path_with_wrong_root_id(self) -> None:
        """Should fail if absolute path's root ID doesn't match machine ID."""
        logger.info(
            "🧪 Testing error for absolute path with wrong machine ID."
        )
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("#wrong_machine.c", source)

    def test_resolve_invalid_absolute_path_partially_correct(self) -> None:
        """Should fail if an absolute path is correct initially but then diverges."""
        logger.info("🧪 Testing error for a partially correct absolute path.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("#resolver_test.a.nonexistent", source)

    def test_resolve_nonexistent_target(self) -> None:
        """Should raise StateNotFoundError for a target that doesn't exist."""
        logger.info("🧪 Testing error for a non-existent target state.")
        # 📋 Arrange
        source = self.get_state("resolver_test.b")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("d", source)

    def test_resolve_to_deeper_nonexistent_state(self) -> None:
        """Should fail if path is valid up to a point, then goes deeper."""
        logger.info(
            "🧪 Testing error for a path to a non-existent deep state."
        )
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("c.c1.nonexistent", source)

    def test_resolve_with_non_string_target(self) -> None:
        """Should raise TypeError for a non-string target."""
        logger.info("🧪 Testing error for a non-string target type.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(TypeError):
            resolve_target_state(None, source)  # type: ignore

    def test_resolve_empty_string_target_raises_error(self) -> None:
        """An empty string as a target should raise a StateNotFoundError."""
        logger.info("🧪 Testing error for an empty string target.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("", source)

    def test_resolve_target_is_case_sensitive(self) -> None:
        """State key resolution should be case-sensitive."""
        logger.info("🧪 Testing that state key resolution is case-sensitive.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert: "B" is not the same as "b".
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("B", source)

    def test_resolve_with_whitespace_in_target(self) -> None:
        """Should fail to resolve a target containing whitespace."""
        logger.info("🧪 Testing error for targets with whitespace.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state(" b", source)  # Leading space

    def test_resolve_with_trailing_dot_is_invalid(self) -> None:
        """A trailing dot in a path should be considered invalid."""
        logger.info("🧪 Testing error for a target path with a trailing dot.")
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("b.", source)

    def test_resolve_with_consecutive_dots_is_invalid(self) -> None:
        """Consecutive dots in a path should be considered invalid."""
        logger.info(
            "🧪 Testing error for a target path with consecutive dots."
        )
        # 📋 Arrange
        source = self.get_state("resolver_test.a.a1")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            resolve_target_state("b..c", source)

    # -------------------------------------------------------------------------
    # ⚙️ Helper Function and Edge Case Tests
    # -------------------------------------------------------------------------

    def test_find_descendant_on_root(self) -> None:
        """The internal `_find_descendant` helper should work from the root."""
        logger.info("🧪 Testing the `_find_descendant` helper function.")
        # 🚀 Act: Test the private helper directly for this unit test.
        target = _find_descendant(self.machine, ["a", "a1"])
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.a.a1")

    def test_find_descendant_with_invalid_path(self) -> None:
        """`_find_descendant` should raise an error for a bad path."""
        logger.info("🧪 Testing `_find_descendant` with an invalid path.")
        # 🚀 Act & Assert
        with self.assertRaises(StateNotFoundError):
            _find_descendant(self.machine, ["a", "x"])

    def test_resolve_with_multiple_dots(self) -> None:
        """Should handle paths with multiple dots correctly."""
        logger.info("🧪 Testing resolution of a path with multiple segments.")
        # 📋 Arrange
        source = self.get_state("resolver_test.c.c1.c11")
        # 🚀 Act: The source's parent is 'c1'. The path '.c2' resolves relative to 'c1's parent, which is 'c'.
        target = resolve_target_state(".c2", source.parent)
        # ✅ Assert
        self.assertEqual(target.id, "resolver_test.c.c2")

    def test_machine_with_numeric_state_keys(self) -> None:
        """Should handle state keys that are numeric-like strings."""
        logger.info("🧪 Testing resolution with numeric string keys.")
        # 📋 Arrange
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
        # 🚀 Act
        target = resolve_target_state("2", source)
        # ✅ Assert
        self.assertEqual(target.id, "numeric.2")


if __name__ == "__main__":
    unittest.main()
