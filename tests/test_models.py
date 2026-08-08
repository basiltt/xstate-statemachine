# /tests/test_models.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Core Data Models
# -----------------------------------------------------------------------------
# This module provides a comprehensive test suite for the core data models
# of the state machine library, defined in `src.xstate_statememachine.models`.
# It focuses on the structural integrity, parsing logic, and helper methods
# of classes like `MachineNode`, `StateNode`, `ActionDefinition`, and
# `InvokeDefinition`.
#
# The tests verify:
#   - Correct parsing of machine configurations into a valid node tree.
#   - Accurate identification and properties of different state types (atomic,
#     compound, parallel, final).
#   - Proper functioning of utility methods for state lookup and relationship
#     checking (e.g., `get_state_by_id`, `_is_descendant`).
#   - Correct parsing and representation of definition objects for actions,
#     invocations, and transitions.
#   - Robust error handling for invalid configurations.
#   - Correct generation of diagrammatic representations (PlantUML, Mermaid).
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import unittest
from typing import Any, Dict

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    Event,
    InvalidConfigError,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.models import (
    ActionDefinition,
    StateNode,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Configures a basic logger to show informative messages during test execution.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestModels
# -----------------------------------------------------------------------------


class TestModels(unittest.TestCase):
    """A collection of unit tests for the core data models.

    This suite validates the construction, properties, and methods of the
    fundamental data structures that represent a state machine.
    """

    # -------------------------------------------------------------------------
    # 🔩 Core Model Parsing & Structure Tests
    # -------------------------------------------------------------------------

    def test_machine_with_deeply_nested_initial_state(self) -> None:
        """Should correctly parse a machine with a deeply nested initial state."""
        logger.info("🧪 Testing parsing of nested initial states.")
        # 📋 Arrange: A config with an initial state defined at multiple levels.
        config: Dict[str, Any] = {
            "id": "deep",
            "initial": "a",
            "states": {"a": {"initial": "a1", "states": {"a1": {}}}},
        }
        # 🚀 Act: Create the machine from the configuration.
        machine = create_machine(config)

        # ✅ Assert: The initial states at each level should be correctly assigned.
        self.assertEqual(machine.initial, "a")
        self.assertIsInstance(machine.states.get("a"), StateNode)
        self.assertEqual(machine.states["a"].initial, "a1")

    def test_machine_id_is_used_as_key(self) -> None:
        """The machine's ID should also be its top-level key."""
        logger.info("🧪 Testing that the machine's ID is used as its key.")
        # 🚀 Act: Create a machine with a specific ID.
        machine = create_machine({"id": "my-machine", "states": {"a": {}}})
        # ✅ Assert: The `key` attribute should match the `id`.
        self.assertEqual(machine.key, "my-machine")

    def test_root_node_parent_is_none(self) -> None:
        """The parent of the root MachineNode should be None."""
        logger.info("🧪 Testing that the root node has no parent.")
        # 🚀 Act: Create a new machine.
        machine = create_machine({"id": "root", "states": {"a": {}}})
        # ✅ Assert: The `parent` attribute of the root node must be None.
        self.assertIsNone(machine.parent)

    def test_all_nodes_reference_same_machine(self) -> None:
        """All descendant nodes should have a reference to the root machine."""
        logger.info("🧪 Testing that all nodes reference the root machine.")
        # 🚀 Act: Create a machine with nested states.
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"states": {"a1": {}}}},
            }
        )
        # 📋 Arrange: Get references to the descendant nodes.
        node_a = machine.get_state_by_id("tester.a")
        node_a1 = machine.get_state_by_id("tester.a.a1")

        # ✅ Assert: The `machine` attribute of each node should be the root.
        self.assertIs(machine, node_a.machine)
        self.assertIs(machine, node_a1.machine)

    def test_machine_without_initial_state(self) -> None:
        """Should infer the only child when 'initial' is omitted.

        🏛️ Behaviour change (v0.6.0): a compound state with exactly one child
        and no `initial` now infers that child. Previously `initial` stayed
        `None`, the machine started with an **empty** active configuration,
        and every event was silently dropped — a dead machine with no error.
        """
        logger.info(
            "🧪 Testing machine creation without a defined initial state."
        )
        # 🚀 Act: Create a machine where the 'initial' key is omitted.
        machine = create_machine({"id": "m", "states": {"a": {}}})
        # ✅ Assert: The single child is inferred as the initial state.
        self.assertEqual("a", machine.initial)

    # -------------------------------------------------------------------------
    # 🧭 State Types, Navigation, and Relationships
    # -------------------------------------------------------------------------

    def test_get_state_by_id(self) -> None:
        """Should retrieve a state by its fully qualified ID."""
        logger.info("🧪 Testing state retrieval by fully qualified ID.")
        # 📋 Arrange: Create a machine with a known nested structure.
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"initial": "a1", "states": {"a1": {}}}},
            }
        )
        # 🚀 Act: Look up a nested state by its full ID.
        node = machine.get_state_by_id("tester.a.a1")

        # ✅ Assert: The correct node should be found.
        self.assertIsNotNone(node)
        assert node is not None  # Hint for type checker.
        self.assertEqual(node.key, "a1")

    def test_get_state_by_custom_id_is_not_supported(self) -> None:
        """Custom state IDs should not be used for lookup."""
        logger.info("🧪 Testing that custom IDs are ignored for state lookup.")
        # 📋 Arrange: Create a machine where a state has a custom `id`.
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"states": {"a1": {"id": "custom_id"}}}},
            }
        )
        # 🚀 Act: Attempt to look up the node using the custom ID.
        node = machine.get_state_by_id("custom_id")

        # ✅ Assert: The node should not be found, as lookup uses path-based IDs.
        self.assertIsNone(node)

    def test_is_descendant_logic(self) -> None:
        """Should correctly identify descendant relationships between states."""
        logger.info("🧪 Testing the descendant relationship logic.")
        # 📋 Arrange: Create a machine and get references to its nodes.
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {
                    "a": {"initial": "a1", "states": {"a1": {}}},
                    "b": {},
                },
            }
        )
        root = machine
        state_a = machine.get_state_by_id("tester.a")
        state_a1 = machine.get_state_by_id("tester.a.a1")
        state_b = machine.get_state_by_id("tester.b")

        # ✅ Assert: Check various descendant relationships.
        # A node is considered a descendant of its parent and itself.
        self.assertTrue(root._is_descendant(state_a1, root))
        self.assertTrue(state_a._is_descendant(state_a1, state_a))
        self.assertFalse(state_a._is_descendant(state_b, state_a))
        self.assertTrue(state_a._is_descendant(state_a, state_a))

    def test_get_path_to_state(self) -> None:
        """Should compute the correct entry path to a given state."""
        logger.info("🧪 Testing the path computation to a target state.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "t",
                "initial": "a",
                "states": {
                    "a": {"initial": "a1", "states": {"a1": {}}},
                    "b": {},
                },
            }
        )
        state_b = machine.get_state_by_id("t.b")

        # 🚀 Act: Compute the path from the root to the target state.
        path = machine._get_path_to_state(state_b, stop_at=machine)

        # ✅ Assert: The path should contain only the target state itself.
        self.assertEqual([p.id for p in path], ["t.b"])

    def test_final_state_property(self) -> None:
        """Should correctly identify a final state via the `is_final` property."""
        logger.info("🧪 Testing the `is_final` state property.")
        # 🚀 Act
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {"type": "final"}}}
        )
        final_node = machine.get_state_by_id("m.a")
        # ✅ Assert
        self.assertTrue(final_node.is_final)
        self.assertFalse(final_node.is_atomic)

    def test_atomic_state_property(self) -> None:
        """Should correctly identify an atomic state via the `is_atomic` property."""
        logger.info("🧪 Testing the `is_atomic` state property.")
        # 🚀 Act
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        atomic_node = machine.get_state_by_id("m.a")
        # ✅ Assert
        self.assertTrue(atomic_node.is_atomic)
        self.assertFalse(atomic_node.is_final)

    def test_parallel_state_type_parsing(self) -> None:
        """Should correctly parse a parallel state and identify its type."""
        logger.info("🧪 Testing parsing of parallel states.")
        # 🚀 Act
        machine = create_machine(
            {
                "id": "p",
                "type": "parallel",
                "states": {"a": {}, "b": {}},
            }
        )
        # ✅ Assert
        self.assertEqual(machine.type, "parallel")

    def test_invalid_state_type_falls_back_to_compound(self) -> None:
        """An invalid state type should default to 'compound' if it has children."""
        logger.info("🧪 Testing fallback type for invalid state definitions.")
        # 📋 Arrange: A state with an invalid type but with child states.
        machine = create_machine(
            {
                "id": "m",
                "states": {"a": {"type": "invalid_type", "states": {"b": {}}}},
            }
        )
        # 🚀 Act
        node = machine.get_state_by_id("m.a")
        # ✅ Assert: The type should default to 'compound' because it has children.
        self.assertEqual(node.type, "compound")

    def test_get_next_state_utility_with_no_target(self) -> None:
        """`get_next_state` should return None for an internal transition."""
        logger.info("🧪 Testing `get_next_state` for an internal transition.")
        # 📋 Arrange: A transition with no 'target', making it internal.
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {"on": {"EV": {}}}}}
        )
        # 🚀 Act: Get the next state for the event.
        next_state = machine.get_next_state("m.a", Event("EV"))
        # ✅ Assert: Since it's an internal transition, there is no next state.
        self.assertIsNone(next_state)

    # -------------------------------------------------------------------------
    # 📝 Definition Object Tests (Action, Invoke, etc.)
    # -------------------------------------------------------------------------

    def test_action_definition_parsing(self) -> None:
        """Should parse string and dictionary action definitions correctly."""
        logger.info("🧪 Testing ActionDefinition parsing.")
        # 🚀 Act: Parse a simple string action.
        action_str = ActionDefinition("myAction")
        # ✅ Assert
        self.assertEqual(action_str.type, "myAction")
        self.assertIsNone(action_str.params)

        # 🚀 Act: Parse an action defined as a dictionary with parameters.
        action_obj = ActionDefinition(
            {"type": "myActionWithParams", "params": {"value": 42}}
        )
        # ✅ Assert
        self.assertEqual(action_obj.type, "myActionWithParams")
        self.assertEqual(action_obj.params, {"value": 42})

    def test_action_definition_with_empty_dict(self) -> None:
        """Should handle an empty dictionary for an action definition."""
        logger.info("🧪 Testing ActionDefinition with an empty dictionary.")
        # 🚀 Act
        action = ActionDefinition({})
        # ✅ Assert: Type falls back to a known default.
        self.assertEqual(action.type, "UnknownAction")
        self.assertIsNone(action.params)

    def test_action_definition_with_no_type_key(self) -> None:
        """Should handle an action dictionary missing the 'type' key."""
        logger.info("🧪 Testing ActionDefinition missing the 'type' key.")
        # 🚀 Act
        action = ActionDefinition({"params": {"info": "test"}})
        # ✅ Assert: Type falls back, but params are still parsed.
        self.assertEqual(action.type, "UnknownAction")
        self.assertIsNotNone(action.params)
        self.assertEqual(action.params.get("info"), "test")

    def test_invoke_definition_parsing(self) -> None:
        """Should correctly parse an `invoke` definition."""
        logger.info("🧪 Testing InvokeDefinition parsing.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "invoker",
                "initial": "a",
                "states": {
                    "a": {"invoke": {"src": "myService", "onDone": "b"}},
                    "b": {},
                },
            },
            # Provide fake logic to satisfy the parser.
            logic=MachineLogic(services={"myService": lambda: None}),
        )
        # 🚀 Act
        invoke_def = machine.states["a"].invoke[0]
        # ✅ Assert
        self.assertEqual(invoke_def.src, "myService")
        self.assertEqual(invoke_def.on_done[0].target_str, "b")

    def test_invoke_with_multiple_definitions(self) -> None:
        """Should correctly parse a state with a list of invoke definitions."""
        logger.info("🧪 Testing parsing of multiple invoke definitions.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "multi_invoke",
                "initial": "a",
                "states": {
                    "a": {
                        "invoke": [
                            {"src": "service1", "onDone": "b"},
                            {"src": "service2", "onError": "c"},
                        ]
                    },
                    "b": {},
                    "c": {},
                },
            },
            logic=MachineLogic(
                services={"service1": lambda: 1, "service2": lambda: 2}
            ),
        )
        # 🚀 Act
        invoke_defs = machine.states["a"].invoke
        # ✅ Assert
        self.assertEqual(len(invoke_defs), 2)
        self.assertEqual(invoke_defs[0].src, "service1")
        self.assertEqual(invoke_defs[1].src, "service2")

    def test_shorthand_transition_target(self) -> None:
        """Should correctly parse a shorthand string for a transition target."""
        logger.info("🧪 Testing shorthand transition target string.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"EV": "b"}}, "b": {}},
            }
        )
        # 🚀 Act
        transition = machine.states["a"].on["EV"][0]
        # ✅ Assert
        self.assertEqual(transition.target_str, "b")

    def test_on_done_shorthand_string(self) -> None:
        """Should correctly parse an onDone shorthand string target."""
        logger.info("🧪 Testing shorthand `onDone` transition target string.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "initial": "a1",
                        "onDone": "b",
                        "states": {"a1": {"type": "final"}},
                    },
                    "b": {},
                },
            }
        )
        # ✅ Assert
        self.assertIsNotNone(machine.states["a"].on_done)
        self.assertEqual(machine.states["a"].on_done.target_str, "b")

    def test_complex_on_done_parsing(self) -> None:
        """Should correctly parse an onDone transition with actions and a guard."""
        logger.info("🧪 Testing parsing of a complex `onDone` object.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "m",
                "states": {
                    "a": {
                        "invoke": {
                            "src": "s",
                            "onDone": {
                                "target": "b",
                                "actions": ["act"],
                                "guard": "grd",
                            },
                        }
                    },
                    "b": {},
                },
            },
            logic=MachineLogic(
                services={"s": lambda: 1},
                actions={"act": lambda: 1},
                guards={"grd": lambda: True},
            ),
        )
        # 🚀 Act
        on_done_trans = machine.states["a"].invoke[0].on_done[0]
        # ✅ Assert
        self.assertEqual(on_done_trans.target_str, "b")
        self.assertEqual(on_done_trans.guard, "grd")
        self.assertEqual(len(on_done_trans.actions), 1)

    def test_after_transition_parsing(self) -> None:
        """Should correctly parse an 'after' (delayed) transition."""
        logger.info("🧪 Testing `after` transition parsing.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "t",
                "initial": "a",
                "states": {"a": {"after": {"1000": "b"}}, "b": {}},
            }
        )
        # 🚀 Act
        after_def = machine.states["a"].after[1000][0]
        # ✅ Assert: The event name should be automatically generated.
        self.assertEqual(after_def.event, "after.1000.t.a")

    def test_transition_with_empty_list_of_actions(self) -> None:
        """A transition with an empty actions list should parse correctly."""
        logger.info("🧪 Testing a transition with an empty actions list.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"EV": {"target": "b", "actions": []}}},
                    "b": {},
                },
            }
        )
        # 🚀 Act
        transition = machine.states["a"].on["EV"][0]
        # ✅ Assert
        self.assertEqual(len(transition.actions), 0)

    # -------------------------------------------------------------------------
    # 💥 Error Handling and Invalid Configurations
    # -------------------------------------------------------------------------

    def test_invalid_config_with_non_string_id(self) -> None:
        """Should raise InvalidConfigError for a non-string machine ID."""
        logger.info("🧪 Testing error handling for non-string machine ID.")
        with self.assertRaises(InvalidConfigError):
            create_machine({"id": 123, "states": {"a": {}}})

    # -------------------------------------------------------------------------
    # 📝 Representations and Diagram Generation
    # -------------------------------------------------------------------------

    def test_state_node_repr(self) -> None:
        """The `__repr__` of a StateNode should be informative."""
        logger.info("🧪 Testing the `repr` of StateNode.")
        # 📋 Arrange
        machine = create_machine(
            {"id": "tester", "initial": "a", "states": {"a": {}}}
        )
        node = machine.get_state_by_id("tester.a")
        # ✅ Assert
        self.assertEqual(repr(node), "StateNode(id='tester.a', type='atomic')")

    def test_action_definition_repr(self) -> None:
        """The `__repr__` of an ActionDefinition should be informative."""
        logger.info("🧪 Testing the `repr` of ActionDefinition.")
        # 📋 Arrange
        action = ActionDefinition("myTestAction")
        # ✅ Assert
        self.assertEqual(repr(action), "Action(type='myTestAction')")

    def test_transition_definition_repr(self) -> None:
        """The `__repr__` of a TransitionDefinition should be informative."""
        logger.info("🧪 Testing the `repr` of TransitionDefinition.")
        # 📋 Arrange
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"on": {"NEXT": "b"}}},
            }
        )
        transition = machine.states["a"].on["NEXT"][0]
        # ✅ Assert
        self.assertEqual(
            repr(transition),
            "Transition(event='NEXT', target='b', reenter=False)",
        )

    def test_plantuml_output_is_valid_string(self) -> None:
        """Should generate a non-empty and valid PlantUML string."""
        logger.info("🧪 Testing PlantUML diagram generation.")
        # 📋 Arrange
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        # 🚀 Act
        plantuml = machine.to_plantuml()
        # ✅ Assert
        self.assertIsInstance(plantuml, str)
        self.assertIn("@startuml", plantuml)
        self.assertIn("@enduml", plantuml)
        self.assertIn('"a"', plantuml)  # Check for the state name

    def test_mermaid_output_is_valid_string(self) -> None:
        """Should generate a non-empty and valid Mermaid.js string."""
        logger.info("🧪 Testing Mermaid.js diagram generation.")
        # 📋 Arrange
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        # 🚀 Act
        mermaid = machine.to_mermaid()
        # ✅ Assert
        self.assertIsInstance(mermaid, str)
        self.assertIn("stateDiagram-v2", mermaid)
        self.assertIn("[*] --> a", mermaid)


if __name__ == "__main__":
    unittest.main()
