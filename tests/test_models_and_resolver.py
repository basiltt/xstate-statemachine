"""
tests/test_models_and_resolver.py
---------------------------------
Refactored test suite for XState machine model utilities and state resolution.
"""

# -----------------------------------------------------------------------------
# Imports
# -----------------------------------------------------------------------------
import logging
import unittest
from typing import Any, Dict, Optional, Set

from src.xstate_statemachine import create_machine, StateNotFoundError, Event
from src.xstate_statemachine.models import ActionDefinition
from src.xstate_statemachine.resolver import resolve_target_state


# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# To enable console output, uncomment and configure the handler:
# ch = logging.StreamHandler()
# ch.setLevel(logging.INFO)
# formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
# ch.setFormatter(formatter)
# logger.addHandler(ch)


# -----------------------------------------------------------------------------
# Test Class
# -----------------------------------------------------------------------------
class TestModelsAndResolver(unittest.TestCase):
    """
    Test suite for model utilities, state resolution, and factory functions.

    This suite validates the creation of machines, parsing of action definitions,
    and resolution of target states under various path formats.
    """

    test_machine_config: Dict[str, Any]
    machine: Any  # Type hint for the Machine instance

    @classmethod
    def setUpClass(cls) -> None:
        """
        Set up a complex machine definition once for all tests in this class.

        Initializes the XState machine used for testing transitions and state lookups.
        """
        logger.info("🚀 Initializing test machine configuration...")
        cls.test_machine_config = {
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
        # Factory pattern: create_machine produces a Machine instance
        cls.machine = create_machine(cls.test_machine_config)
        logger.info("✅ Test machine created with ID '%s'", cls.machine.id)

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def get_state(self, state_id: str) -> Optional[Any]:
        """
        Helper to retrieve a state node by ID.

        Args:
            state_id (str): Fully qualified state ID.

        Returns:
            Optional[Any]: The state node, or None if not found.
        """
        logger.info("🔍 Retrieving state by ID: %s", state_id)
        return self.machine.get_state_by_id(state_id)

    # -------------------------------------------------------------------------
    # Tests: State Retrieval
    # -------------------------------------------------------------------------
    def test_get_state_by_id(self) -> None:
        """
        Should retrieve a state by its fully qualified ID.

        Verifies that the resolved node has the correct key.
        """
        logger.info("🚀 Testing state retrieval by qualified ID...")
        node = self.get_state("tester.a.a2")
        self.assertIsNotNone(
            node, "Node 'tester.a.a2' should exist"
        )  # ✅ Success path
        self.assertEqual(
            node.key, "a2", "State key should be 'a2'"
        )  # 🧪 Validate key

    def test_get_state_by_custom_id(self) -> None:
        """
        Should retrieve states by path-based IDs but not by custom IDs.

        Ensures custom IDs are not used for lookup in current implementation.
        """
        logger.info("🚀 Testing retrieval with custom IDs...")
        node = self.get_state("tester.a.a1")
        self.assertIsNotNone(
            node, "Node 'tester.a.a1' should exist"
        )  # ✅ Success path
        self.assertEqual(
            node.id, "tester.a.a1", "State ID should be 'tester.a.a1'"
        )  # 🧪 Validate ID

        node_custom = self.get_state("custom_a1_id")
        self.assertIsNone(
            node_custom, "Custom ID lookup should return None"
        )  # ❌ Custom ID should not be found

    # -------------------------------------------------------------------------
    # Tests: ActionDefinition Parsing
    # -------------------------------------------------------------------------
    def test_action_definition_parsing(self) -> None:
        """
        Should parse string and object action definitions correctly.

        Validates the type and params attributes of ActionDefinition.
        """
        logger.info("🚀 Testing ActionDefinition parsing...")

        # 🧪 Test string action definition
        action_str = ActionDefinition("myAction")
        self.assertEqual(
            action_str.type, "myAction", "Action type should be 'myAction'"
        )
        self.assertIsNone(
            action_str.params,
            "Action params should be None for string definition",
        )
        logger.debug("✅ String action parsed: %s", action_str.type)

        # 🧪 Test object action definition with parameters
        action_obj = ActionDefinition(
            {"type": "myActionWithParams", "params": {"value": 42}}
        )
        self.assertEqual(
            action_obj.type,
            "myActionWithParams",
            "Action type should be 'myActionWithParams'",
        )
        self.assertEqual(
            action_obj.params,
            {"value": 42},
            "Action params should match provided dictionary",
        )
        logger.debug(
            "✅ Object action parsed: %s with params %s",
            action_obj.type,
            action_obj.params,
        )

    # -------------------------------------------------------------------------
    # Tests: State Resolution
    # -------------------------------------------------------------------------
    def test_resolve_sibling_state(self) -> None:
        """
        Should correctly resolve a target state that is a sibling.

        Uses relative sibling identifier without prefix.
        """
        logger.info("🚀 Testing sibling state resolution...")
        source = self.get_state("tester.a.a1")
        self.assertIsNotNone(
            source, "Source state 'tester.a.a1' should exist"
        )  # 🧪 Validate source
        target = resolve_target_state("b", source)
        self.assertEqual(
            target.id, "tester.b", "Target state should resolve to 'tester.b'"
        )
        logger.debug("✅ Sibling state resolved to: %s", target.id)

    def test_resolve_relative_state(self) -> None:
        """
        Should correctly resolve a relative target using the '.' prefix.

        Ensures resolution moves within the same parent context.
        """
        logger.info("🚀 Testing relative state resolution...")
        source = self.get_state("tester.b")
        self.assertIsNotNone(
            source, "Source state 'tester.b' should exist"
        )  # 🧪 Validate source
        target = resolve_target_state(".c", source)
        self.assertEqual(
            target.id, "tester.c", "Target state should resolve to 'tester.c'"
        )
        logger.debug("✅ Relative state resolved to: %s", target.id)

    def test_resolve_relative_state_from_root(self) -> None:
        """
        Should resolve a relative target from the root machine node.

        Confirms that '.' prefix works at root level.
        """
        logger.info("🚀 Testing relative resolution from root...")
        source = self.machine  # root node
        target = resolve_target_state(".c", source)
        self.assertEqual(
            target.id, "tester.c", "Target state should resolve to 'tester.c'"
        )
        logger.debug("✅ Relative state from root resolved to: %s", target.id)

    def test_resolve_absolute_state(self) -> None:
        """
        Should correctly resolve an absolute target using the '#' prefix.

        Validates absolute resolution syntax.
        """
        logger.info("🚀 Testing absolute state resolution...")
        source = self.get_state("tester.a.a2")
        self.assertIsNotNone(
            source, "Source state 'tester.a.a2' should exist"
        )  # 🧪 Validate source
        target = resolve_target_state("#tester.c", source)
        self.assertEqual(
            target.id, "tester.c", "Target state should resolve to 'tester.c'"
        )
        logger.debug("✅ Absolute state resolved to: %s", target.id)

    def test_resolve_invalid_absolute_id(self) -> None:
        """
        Should raise StateNotFoundError for an absolute path with an incorrect ID.

        Verifies error handling for invalid absolute references.
        """
        logger.info("🚀 Testing invalid absolute state resolution...")
        source = self.get_state("tester.a.a2")
        self.assertIsNotNone(
            source, "Source state 'tester.a.a2' should exist"
        )  # 🧪 Validate source
        with self.assertRaises(StateNotFoundError):
            logger.debug(
                "Attempting to resolve invalid absolute path: #wrong_id.c"
            )
            resolve_target_state(
                "#wrong_id.c", source
            )  # ❌ Expecting StateNotFoundError

    def test_resolve_invalid_state(self) -> None:
        """
        Should raise StateNotFoundError for an unresolvable target.

        Confirms that unknown targets trigger the proper exception.
        """
        logger.info("🚀 Testing resolution of nonexistent target...")
        source = self.get_state("tester.a.a1")
        self.assertIsNotNone(
            source, "Source state 'tester.a.a1' should exist"
        )  # 🧪 Validate source
        with self.assertRaises(StateNotFoundError):
            logger.debug(
                "Attempting to resolve nonexistent state: nonexistent"
            )
            resolve_target_state(
                "nonexistent", source
            )  # ❌ Expecting StateNotFoundError

    def test_resolve_non_string_target(self) -> None:
        """
        Should raise TypeError if the target is not a string.

        Ensures type validation is enforced.
        """
        logger.info("🚀 Testing non-string target resolution...")
        source = self.get_state("tester.a.a1")
        self.assertIsNotNone(
            source, "Source state 'tester.a.a1' should exist"
        )  # 🧪 Validate source
        with self.assertRaises(TypeError):
            logger.debug("Attempting to resolve with non-string target: None")
            resolve_target_state(None, source)  # type: ignore # ❌ Expecting TypeError

    # -------------------------------------------------------------------------
    # Tests: Transition Utility
    # -------------------------------------------------------------------------
    def test_get_next_state_utility(self) -> None:
        """
        Should calculate the next state without executing actions.

        Uses get_next_state to determine possible next states.
        """
        logger.info("🚀 Testing get_next_state utility...")
        next_states: Optional[Set[str]] = self.machine.get_next_state(
            "tester.a.a1", Event("T_SIBLING")
        )
        self.assertEqual(
            next_states, {"tester.b"}, "Next state should be 'tester.b'"
        )
        logger.debug("✅ get_next_state returned: %s", next_states)

    def test_get_next_state_for_invalid_state(self) -> None:
        """
        Should return None from get_next_state if the from_state_id is invalid.

        Confirms graceful handling of missing states.
        """
        logger.info("🚀 Testing get_next_state with invalid state ID...")
        next_states = self.machine.get_next_state(
            "nonexistent", Event("T_SIBLING")
        )
        self.assertIsNone(
            next_states,
            "get_next_state should return None for invalid state ID",
        )
        logger.debug(
            "✅ get_next_state correctly returned None for invalid state."
        )

    # -------------------------------------------------------------------------
    # Tests: Visualization
    # -------------------------------------------------------------------------
    def test_visualization_methods(self) -> None:
        """
        Should generate non-empty visualization strings without errors.

        Verifies PlantUML and Mermaid diagram outputs.
        """
        logger.info("🚀 Testing visualization outputs...")

        # 🧪 Test PlantUML output
        plantuml_output = self.machine.to_plantuml()
        self.assertIsInstance(
            plantuml_output, str, "PlantUML output should be a string"
        )
        self.assertIn(
            "@startuml",
            plantuml_output,
            "PlantUML output should contain '@startuml'",
        )
        self.assertIn(
            "tester_a_a1 --> tester_b : T_SIBLING",
            plantuml_output,
            "PlantUML output should contain a specific transition",
        )
        logger.debug("✅ PlantUML output generated successfully.")

        # 🧪 Test Mermaid output
        mermaid_output = self.machine.to_mermaid()
        self.assertIsInstance(
            mermaid_output, str, "Mermaid output should be a string"
        )
        self.assertIn(
            "stateDiagram-v2",
            mermaid_output,
            "Mermaid output should contain 'stateDiagram-v2'",
        )
        self.assertIn(
            "a1 --> b : T_SIBLING",
            mermaid_output,
            "Mermaid output should contain a specific transition",
        )
        logger.debug("✅ Mermaid output generated successfully.")
