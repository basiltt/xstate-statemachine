# tests/test_models.py
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    create_machine,
    InvalidConfigError,
    MachineLogic,
)
from src.xstate_statemachine.models import (
    ActionDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
)
from xstate_statemachine import Event

# -----------------------------------------------------------------------------
# Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Test Class for Models
# -----------------------------------------------------------------------------
class TestModels(unittest.TestCase):
    """
    Test suite for the core data models of the state machine library.
    """

    def test_action_definition_parsing(self) -> None:
        """Should parse string and object action definitions correctly."""
        logger.info("🚀 Testing ActionDefinition parsing...")
        action_str = ActionDefinition("myAction")
        self.assertEqual(action_str.type, "myAction")
        self.assertIsNone(action_str.params)

        action_obj = ActionDefinition(
            {"type": "myActionWithParams", "params": {"value": 42}}
        )
        self.assertEqual(action_obj.type, "myActionWithParams")
        self.assertEqual(action_obj.params, {"value": 42})

    def test_get_state_by_id(self) -> None:
        """Should retrieve a state by its fully qualified ID."""
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"initial": "a1", "states": {"a1": {}}}},
            }
        )
        node = machine.get_state_by_id("tester.a.a1")
        self.assertIsNotNone(node)
        self.assertEqual(node.key, "a1")

    def test_get_state_by_custom_id_is_not_supported(self) -> None:
        """Custom IDs should not be used for lookup."""
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"states": {"a1": {"id": "custom_id"}}}},
            }
        )
        node = machine.get_state_by_id("custom_id")
        self.assertIsNone(node)

    def test_machine_with_deeply_nested_initial_state(self) -> None:
        """Should correctly parse a machine with a deeply nested initial state."""
        config = {
            "id": "deep",
            "initial": "a",
            "states": {"a": {"initial": "a1", "states": {"a1": {}}}},
        }
        machine = create_machine(config)
        self.assertEqual(machine.initial, "a")
        self.assertEqual(machine.states["a"].initial, "a1")

    def test_state_node_repr(self) -> None:
        """The __repr__ of StateNode should be informative."""
        machine = create_machine(
            {"id": "tester", "initial": "a", "states": {"a": {}}}
        )
        node = machine.get_state_by_id("tester.a")
        self.assertEqual(repr(node), "StateNode(id='tester.a', type='atomic')")

    def test_action_definition_repr(self) -> None:
        """The __repr__ of ActionDefinition should be informative."""
        action = ActionDefinition("myTestAction")
        self.assertEqual(repr(action), "Action(type='myTestAction')")

    def test_transition_definition_repr(self) -> None:
        """The __repr__ of TransitionDefinition should be informative."""
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"on": {"NEXT": "b"}}, "b": {}},
            }
        )
        transition = machine.states["a"].on["NEXT"][0]
        self.assertEqual(
            repr(transition), "Transition(event='NEXT', target='b')"
        )

    def test_is_descendant_logic(self) -> None:
        """Should correctly identify descendant relationships."""
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

        # ✅ FIX: Call the method on the instance `root`, not the class `StateNode`.
        self.assertTrue(root._is_descendant(state_a1, root))
        self.assertTrue(state_a._is_descendant(state_a1, state_a))
        self.assertFalse(state_a._is_descendant(state_b, state_a))
        self.assertTrue(state_a._is_descendant(state_a, state_a))

    def test_get_path_to_state(self) -> None:
        """Should compute the entry path correctly."""
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

        # ✅ FIX: Call the method on the instance `machine`, not the class `StateNode`.
        path = machine._get_path_to_state(state_b, stop_at=machine)

        self.assertEqual([p.id for p in path], ["t.b"])

    def test_invalid_config_with_non_string_id(self) -> None:
        """Should raise InvalidConfigError for non-string machine ID."""
        with self.assertRaises(InvalidConfigError):
            create_machine({"id": 123, "states": {"a": {}}})

    def test_invoke_definition_parsing(self) -> None:
        """Should correctly parse an invoke definition."""
        machine = create_machine(
            {
                "id": "invoker",
                "initial": "a",
                "states": {
                    "a": {"invoke": {"src": "myService", "onDone": "b"}},
                    "b": {},
                },
            },
            logic=MachineLogic(services={"myService": lambda: None}),
        )  # Provide dummy logic
        invoke_def = machine.states["a"].invoke[0]
        self.assertEqual(invoke_def.src, "myService")
        self.assertEqual(invoke_def.on_done[0].target_str, "b")

    def test_after_transition_parsing(self) -> None:
        """Should correctly parse an 'after' transition."""
        machine = create_machine(
            {
                "id": "t",
                "initial": "a",
                "states": {"a": {"after": {"1000": "b"}}, "b": {}},
            }
        )
        after_def = machine.states["a"].after[1000][0]
        self.assertEqual(after_def.event, "after.1000.t.a")

    def test_machine_id_is_used_as_key(self) -> None:
        """The machine's ID should also be its top-level key."""
        machine = create_machine({"id": "my-machine", "states": {"a": {}}})
        self.assertEqual(machine.key, "my-machine")

    def test_root_node_parent_is_none(self) -> None:
        """The parent of the root MachineNode should be None."""
        machine = create_machine({"id": "root", "states": {"a": {}}})
        self.assertIsNone(machine.parent)

    def test_all_nodes_reference_same_machine(self) -> None:
        """All descendant nodes should have a reference to the root machine."""
        machine = create_machine(
            {
                "id": "tester",
                "initial": "a",
                "states": {"a": {"states": {"a1": {}}}},
            }
        )
        node_a = machine.get_state_by_id("tester.a")
        node_a1 = machine.get_state_by_id("tester.a.a1")
        self.assertIs(machine, node_a.machine)
        self.assertIs(machine, node_a1.machine)

    def test_final_state_property(self) -> None:
        """Should correctly identify a final state."""
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {"type": "final"}}}
        )
        final_node = machine.get_state_by_id("m.a")
        self.assertTrue(final_node.is_final)
        self.assertFalse(final_node.is_atomic)

    def test_atomic_state_property(self) -> None:
        """Should correctly identify an atomic state."""
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        atomic_node = machine.get_state_by_id("m.a")
        self.assertTrue(atomic_node.is_atomic)
        self.assertFalse(atomic_node.is_final)

    def test_on_done_shorthand_string(self) -> None:
        """Should parse onDone shorthand string."""
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
        self.assertIsNotNone(machine.states["a"].on_done)
        self.assertEqual(machine.states["a"].on_done.target_str, "b")

    def test_machine_without_initial_state(self) -> None:
        """Should create a machine successfully if 'initial' is missing."""
        machine = create_machine({"id": "m", "states": {"a": {}}})
        self.assertIsNone(machine.initial)

    def test_shorthand_transition_target(self) -> None:
        """Should correctly parse a shorthand string for a transition target."""
        machine = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"EV": "b"}}, "b": {}},
            }
        )
        transition = machine.states["a"].on["EV"][0]
        self.assertEqual(transition.target_str, "b")

    def test_action_definition_with_empty_dict(self) -> None:
        """Should handle an empty dictionary for an action definition."""
        action = ActionDefinition({})
        self.assertEqual(action.type, "UnknownAction")
        self.assertIsNone(action.params)

    def test_action_definition_with_no_type_key(self) -> None:
        """Should handle an action dictionary missing the 'type' key."""
        action = ActionDefinition({"params": {"info": "test"}})
        self.assertEqual(action.type, "UnknownAction")
        self.assertIsNotNone(action.params)
        self.assertEqual(action.params.get("info"), "test")

    def test_parallel_state_type_parsing(self) -> None:
        """Should correctly parse a parallel state and identify its type."""
        machine = create_machine(
            {
                "id": "p",
                "initial": "a",
                "states": {
                    "a": {"type": "parallel", "states": {"b": {}, "c": {}}}
                },
            }
        )
        parallel_node = machine.get_state_by_id("p.a")
        self.assertEqual(parallel_node.type, "parallel")

    def test_invalid_state_type_falls_back_to_compound(self) -> None:
        """A state with children and an invalid type should default to 'compound'."""
        machine = create_machine(
            {
                "id": "m",
                "states": {"a": {"type": "invalid_type", "states": {"b": {}}}},
            }
        )
        node = machine.get_state_by_id("m.a")
        self.assertEqual(node.type, "compound")

    def test_invoke_with_multiple_definitions(self) -> None:
        """Should correctly parse a state with a list of invoke definitions."""
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
        invoke_defs = machine.states["a"].invoke
        self.assertEqual(len(invoke_defs), 2)
        self.assertEqual(invoke_defs[0].src, "service1")
        self.assertEqual(invoke_defs[1].src, "service2")

    def test_complex_on_done_parsing(self) -> None:
        """Should correctly parse an onDone transition with actions and a guard."""
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
        on_done_trans = machine.states["a"].invoke[0].on_done[0]
        self.assertEqual(on_done_trans.target_str, "b")
        self.assertEqual(on_done_trans.guard, "grd")
        self.assertEqual(len(on_done_trans.actions), 1)

    def test_transition_with_empty_list_of_actions(self) -> None:
        """A transition with an empty list of actions should be parsed correctly."""
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
        transition = machine.states["a"].on["EV"][0]
        self.assertEqual(len(transition.actions), 0)

    def test_plantuml_output_is_valid_string(self) -> None:
        """Should generate a non-empty PlantUML string."""
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        plantuml = machine.to_plantuml()
        self.assertIsInstance(plantuml, str)
        self.assertIn("@startuml", plantuml)
        self.assertIn("@enduml", plantuml)
        # FIX: Check for the state name within quotes, which is more robust
        self.assertIn('"a"', plantuml)

    def test_mermaid_output_is_valid_string(self) -> None:
        """Should generate a non-empty Mermaid.js string."""
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {}}}
        )
        mermaid = machine.to_mermaid()
        self.assertIsInstance(mermaid, str)
        self.assertIn("stateDiagram-v2", mermaid)
        self.assertIn("[*] --> a", mermaid)

    def test_get_next_state_utility_with_no_target(self) -> None:
        """get_next_state should return None for an internal transition without a target."""
        machine = create_machine(
            {"id": "m", "initial": "a", "states": {"a": {"on": {"EV": {}}}}}
        )
        # The `get_next_state` utility returns the target state ID(s),
        # so for an internal transition with no target, it should correctly return None.
        next_state = machine.get_next_state("m.a", Event("EV"))
        self.assertIsNone(next_state)
