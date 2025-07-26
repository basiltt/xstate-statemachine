# tests_cli/test_extractor.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Logic & Event Extractor
# -----------------------------------------------------------------------------
# This module provides comprehensive unit tests for the functions in
# `xstate_statemachine.cli.extractor`.
#
# The tests are divided into logical groups to verify:
#   -   `extract_logic_names`: Correct parsing of actions, guards, and services
#       from a wide variety of valid and malformed config structures.
#   -   `extract_events`: Accurate discovery of all unique event names.
#   -   Hierarchy Utilities: Correct functioning of `_count_invokes` and
#       `guess_hierarchy` for parent-child machine detection.
# -----------------------------------------------------------------------------
"""
Unit tests for the CLI's logic and event extraction functions.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import os
import unittest

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from xstate_statemachine.cli.extractor import (
    _count_invokes,
    extract_events,
    extract_logic_names,
    guess_hierarchy,
)

from .fixtures import (
    SAMPLE_CONFIG_NESTED,
    SAMPLE_CONFIG_SIMPLE,
    create_temp_json,
)

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestLogicNamesExtractor
# -----------------------------------------------------------------------------


class TestLogicNamesExtractor(unittest.TestCase):
    """
    Verifies the `extract_logic_names` function across diverse configurations.

    This suite tests the core logic extraction by providing various machine
    configurations and asserting that the returned sets of actions, guards,
    and services are correct. It covers standard cases, nested structures,
    and numerous edge cases and malformed inputs.
    """

    def test_extract_from_simple_config(self) -> None:
        """
        Ensures logic names are extracted correctly from a basic, flat config.
        """
        logger.info("🧪 Testing extraction from a simple config.")
        # 🧠 Run the extractor on a simple fixture.
        actions, guards, services = extract_logic_names(SAMPLE_CONFIG_SIMPLE)

        # ✅ Assert that all expected logic names were found.
        self.assertEqual(
            actions, {"enter_action", "exit_action", "trans_action"}
        )
        self.assertEqual(guards, {"trans_guard"})
        self.assertEqual(services, set())

    def test_extract_from_nested_config(self) -> None:
        """
        Ensures logic names are extracted from nested states, `invoke`, and `after`.
        """
        logger.info("🧪 Testing extraction from a nested config.")
        # 🧠 Run the extractor on a nested fixture.
        actions, guards, services = extract_logic_names(SAMPLE_CONFIG_NESTED)

        # ✅ Assert that nested logic is correctly identified.
        self.assertEqual(actions, {"after_action"})
        self.assertEqual(guards, {"always_guard"})
        self.assertEqual(services, {"child_service"})

    def test_extract_actions_from_list(self) -> None:
        """
        Verifies extraction when actions are defined as a list of strings.
        """
        logger.info("🧪 Testing extraction of list-based actions.")
        config = {
            "id": "list_actions",
            "initial": "a",
            "states": {"a": {"entry": ["act1", "act2"]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act1", "act2"})

    def test_extract_actions_from_dict_type(self) -> None:
        """
        Verifies extraction when actions are defined as dictionaries with a 'type' key.
        """
        logger.info("🧪 Testing extraction of dict-type actions.")
        config = {
            "id": "dict_actions",
            "initial": "a",
            "states": {"a": {"entry": [{"type": "act_type"}]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act_type"})

    def test_extract_guards_from_cond_key(self) -> None:
        """
        Ensures guards are correctly extracted from the 'cond' key.
        """
        logger.info("🧪 Testing extraction of guards via 'cond' key.")
        config = {
            "id": "cond_guard",
            "initial": "a",
            "states": {"a": {"on": {"E": {"cond": "cond_guard"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"cond_guard"})

    def test_extract_guards_from_guard_key(self) -> None:
        """
        Ensures guards are correctly extracted from the 'guard' key.
        """
        logger.info("🧪 Testing extraction of guards via 'guard' key.")
        config = {
            "id": "guard_key",
            "initial": "a",
            "states": {"a": {"on": {"E": {"guard": "g_key"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"g_key"})

    def test_extract_services_from_invoke_src(self) -> None:
        """
        Ensures services are correctly extracted from an 'invoke' object's 'src' key.
        """
        logger.info("🧪 Testing extraction of services from invoke src.")
        config = {
            "id": "invoke_src",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "my_service"}}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"my_service"})

    def test_extract_from_invoke_list(self) -> None:
        """
        Verifies extraction when 'invoke' is defined as a list of service objects.
        """
        logger.info("🧪 Testing extraction from list-based invoke.")
        config = {
            "id": "invoke_list",
            "initial": "a",
            "states": {"a": {"invoke": [{"src": "srv1"}, {"src": "srv2"}]}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"srv1", "srv2"})

    def test_extract_actions_from_invoke_onDone(self) -> None:
        """
        Ensures actions are extracted from an 'onDone' transition within an 'invoke'.
        """
        logger.info("🧪 Testing extraction from invoke onDone actions.")
        config = {
            "id": "invoke_done",
            "initial": "a",
            "states": {"a": {"invoke": {"onDone": {"actions": "done_act"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"done_act"})

    def test_extract_guards_from_invoke_onError(self) -> None:
        """
        Ensures guards are extracted from an 'onError' transition within an 'invoke'.
        """
        logger.info("🧪 Testing extraction from invoke onError guards.")
        config = {
            "id": "invoke_err",
            "initial": "a",
            "states": {"a": {"invoke": {"onError": {"guard": "err_guard"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"err_guard"})

    def test_extract_from_after_transitions(self) -> None:
        """
        Ensures actions and guards are extracted from delayed 'after' transitions.
        """
        logger.info("🧪 Testing extraction from after transitions.")
        config = {
            "id": "after_test",
            "initial": "a",
            "states": {
                "a": {
                    "after": {
                        1000: {"actions": "after_act", "guard": "after_guard"}
                    }
                }
            },
        }
        actions, guards, _ = extract_logic_names(config)
        self.assertEqual(actions, {"after_act"})
        self.assertEqual(guards, {"after_guard"})

    def test_extraction_no_duplicates(self) -> None:
        """
        Confirms that duplicate logic names are only recorded once.
        """
        logger.info("🧪 Testing that extraction is de-duplicated.")
        config = {
            "id": "dup",
            "initial": "a",
            "states": {"a": {"entry": "dup_act", "exit": "dup_act"}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"dup_act"})

    def test_extraction_from_parallel_states(self) -> None:
        """
        Ensures logic is extracted correctly from all regions of a parallel state.
        """
        logger.info("🧪 Testing extraction from parallel states.")
        config = {
            "id": "parallel",
            "type": "parallel",
            "states": {
                "p1": {"entry": "p_act"},
                "p2": {"on": {"E": {"guard": "p_guard"}}},
            },
        }
        actions, guards, _ = extract_logic_names(config)
        self.assertEqual(actions, {"p_act"})
        self.assertEqual(guards, {"p_guard"})

    def test_no_extraction_from_empty_config(self) -> None:
        """Confirms that an empty state definition yields no logic names."""
        logger.info("🧪 Testing extraction from empty config.")
        config = {"id": "empty", "initial": "a", "states": {"a": {}}}
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_ignores_unknown_keys(self) -> None:
        """Ensures that unknown keys within the config do not cause errors or extraction."""
        logger.info("🧪 Testing ignore of unknown config keys.")
        config = {
            "id": "unknown",
            "initial": "a",
            "states": {"a": {"unknown_key": "value"}},
        }
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_multiple_transitions(self) -> None:
        """Verifies extraction from events that have multiple transition definitions."""
        logger.info("🧪 Testing extraction from multiple transitions.")
        config = {
            "id": "multi_trans",
            "initial": "a",
            "states": {
                "a": {"on": {"E": [{"actions": "act1"}, {"actions": "act2"}]}}
            },
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act1", "act2"})

    def test_extraction_actions_from_string_and_dict_mixed(self) -> None:
        """Ensures extraction works with a mix of string and dict action definitions."""
        logger.info("🧪 Testing mixed string/dict actions extraction.")
        config = {
            "id": "mixed_act",
            "initial": "a",
            "states": {"a": {"entry": ["str_act", {"type": "dict_act"}]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"str_act", "dict_act"})

    def test_extraction_guards_from_nested_onDone(self) -> None:
        """Verifies guard extraction from a nested `onDone` transition list."""
        logger.info("🧪 Testing guards in nested invoke onDone.")
        config = {
            "id": "nested_guard",
            "initial": "a",
            "states": {"a": {"invoke": {"onDone": [{"guard": "nested_g"}]}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"nested_g"})

    def test_extraction_services_from_nested_invoke(self) -> None:
        """Confirms service extraction from an `invoke` within a nested state."""
        logger.info("🧪 Testing services in nested invoke.")
        config = {
            "id": "nested_srv",
            "initial": "a",
            "states": {
                "a": {"states": {"b": {"invoke": {"src": "nested_srv"}}}}
            },
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"nested_srv"})

    def test_extraction_ignores_non_string_non_dict_actions(self) -> None:
        """Ensures that malformed action definitions (e.g., numbers) are ignored."""
        logger.info("🧪 Testing ignore of invalid action types.")
        config = {
            "id": "invalid_act",
            "initial": "a",
            "states": {"a": {"entry": [123]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_after_with_list_trans(self) -> None:
        """Verifies extraction from an `after` transition with a list of definitions."""
        logger.info("🧪 Testing extraction from after with list trans.")
        config = {
            "id": "after_list",
            "initial": "a",
            "states": {
                "a": {"after": {1000: [{"actions": "a1"}, {"actions": "a2"}]}}
            },
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"a1", "a2"})

    def test_extraction_from_invoke_onError_list(self) -> None:
        """Verifies extraction from an `onError` transition with a list of definitions."""
        logger.info("🧪 Testing extraction from invoke onError list.")
        config = {
            "id": "err_list",
            "initial": "a",
            "states": {
                "a": {
                    "invoke": {"onError": [{"guard": "g1"}, {"guard": "g2"}]}
                }
            },
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"g1", "g2"})

    def test_extraction_from_empty_states(self) -> None:
        """Ensures a config without a 'states' key is handled gracefully."""
        logger.info("🧪 Testing extraction from no states.")
        config = {"id": "no_states", "initial": "a"}
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_invalid_invoke(self) -> None:
        """Ensures a malformed `invoke` definition is ignored."""
        logger.info("🧪 Testing ignore of invalid invoke.")
        config = {
            "id": "inv_inv",
            "initial": "a",
            "states": {"a": {"invoke": "not_dict"}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, set())

    def test_extraction_from_after_non_dict(self) -> None:
        """Ensures a malformed `after` definition is ignored."""
        logger.info("🧪 Testing ignore of invalid after.")
        config = {
            "id": "inv_after",
            "initial": "a",
            "states": {"a": {"after": "not_dict"}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_on_non_dict(self) -> None:
        """Ensures a malformed `on` definition is ignored."""
        logger.info("🧪 Testing ignore of invalid on.")
        config = {
            "id": "inv_on",
            "initial": "a",
            "states": {"a": {"on": "not_dict"}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_entry_non_list_str(self) -> None:
        """Ensures a malformed `entry` definition is ignored."""
        logger.info("🧪 Testing ignore of invalid entry.")
        config = {
            "id": "inv_entry",
            "initial": "a",
            "states": {"a": {"entry": 123}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_trans_non_list_dict(self) -> None:
        """Verifies extraction when a transition is a single object, not a list."""
        logger.info("🧪 Testing extraction from non-list trans.")
        config = {
            "id": "non_list_trans",
            "initial": "a",
            "states": {"a": {"on": {"E": {"actions": "trans_act"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"trans_act"})

    def test_extraction_from_invoke_src_non_str(self) -> None:
        """Ensures `invoke.src` is ignored if it's not a string."""
        logger.info("🧪 Testing ignore non-str invoke src.")
        config = {
            "id": "non_str_src",
            "initial": "a",
            "states": {"a": {"invoke": {"src": 123}}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, set())

    def test_extraction_from_guard_non_str(self) -> None:
        """Ensures `guard` is ignored if it's not a string."""
        logger.info("🧪 Testing ignore non-str guard.")
        config = {
            "id": "non_str_g",
            "initial": "a",
            "states": {"a": {"on": {"E": {"guard": 123}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, set())

    def test_extraction_from_after_trans_non_dict(self) -> None:
        """Ensures malformed `after` transition objects are ignored."""
        logger.info("🧪 Testing ignore non-dict after trans.")
        config = {
            "id": "non_dict_after",
            "initial": "a",
            "states": {"a": {"after": {1000: "not_dict"}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_onDone_actions_list(self) -> None:
        """Verifies extraction from `onDone` when `actions` is a list."""
        logger.info("🧪 Testing extraction from onDone actions list.")
        config = {
            "id": "done_list",
            "initial": "a",
            "states": {"a": {"invoke": {"onDone": {"actions": ["d1", "d2"]}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"d1", "d2"})

    def test_extraction_from_onError_guard(self) -> None:
        """Verifies guard extraction from a simple `onError` transition."""
        logger.info("🧪 Testing extraction from onError guard.")
        config = {
            "id": "err_guard",
            "initial": "a",
            "states": {"a": {"invoke": {"onError": {"guard": "e_g"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"e_g"})

    def test_extraction_from_parallel_nested(self) -> None:
        """Confirms extraction from states nested inside a parallel region."""
        logger.info("🧪 Testing extraction from nested parallel.")
        config = {
            "id": "par_nested",
            "type": "parallel",
            "states": {"p1": {"states": {"c1": {"entry": "p_act"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"p_act"})

    def test_extraction_from_final_state(self) -> None:
        """Ensures that final states, which have no logic, yield no names."""
        logger.info("🧪 Testing no extraction from final state.")
        config = {
            "id": "final_state",
            "initial": "a",
            "states": {"a": {"type": "final"}},
        }
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_history_state(self) -> None:
        """Ensures that history states, which have no logic, yield no names."""
        logger.info("🧪 Testing no extraction from history state.")
        config = {
            "id": "hist",
            "initial": "a",
            "states": {"a": {"history": "deep"}},
        }
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_invalid_trans_target(self) -> None:
        """Ensures extraction succeeds even if a transition's target is malformed."""
        logger.info("🧪 Testing extraction ignores invalid target.")
        config = {
            "id": "inv_target",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": 123, "actions": "inv_act"}}}
            },
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"inv_act"})

    def test_extraction_from_cond_in_after(self) -> None:
        """Verifies guard extraction using the 'cond' key in an `after` transition."""
        logger.info("🧪 Testing 'cond' in after.")
        config = {
            "id": "after_cond",
            "initial": "a",
            "states": {"a": {"after": {1000: {"cond": "a_cond"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"a_cond"})

    def test_extraction_from_multiple_invoke_in_list(self) -> None:
        """Confirms service extraction from a list of `invoke` definitions."""
        logger.info("🧪 Testing multiple invoke in list.")
        config = {
            "id": "multi_inv",
            "initial": "a",
            "states": {"a": {"invoke": [{"src": "s1"}, {"src": "s2"}]}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"s1", "s2"})

    def test_extraction_from_onDone_in_after(self) -> None:
        """Ensures `onDone` in `after` is ignored as it's not a valid SCXML pattern."""
        logger.info("🧪 Testing no onDone in after.")
        config = {
            "id": "after_done",
            "initial": "a",
            "states": {"a": {"after": {1000: {"onDone": "not_valid"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestEventExtractor
# -----------------------------------------------------------------------------


class TestEventExtractor(unittest.TestCase):
    """
    Verifies the `extract_events` utility function.
    """

    def test_extract_events_from_simple_on(self) -> None:
        """
        Ensures events are extracted from a simple 'on' block.
        """
        logger.info("🧪 Testing event extraction from a simple 'on' block.")
        config = {"on": {"EVENT1": {}, "EVENT2": {}}}
        events = extract_events(config)
        self.assertEqual(events, {"EVENT1", "EVENT2"})

    def test_extract_events_from_nested_states(self) -> None:
        """
        Verifies event extraction from 'on' blocks within nested states.
        """
        logger.info("🧪 Testing event extraction from nested states.")
        config = {
            "states": {
                "s1": {"on": {"EVENT_S1": {}}},
                "s2": {"states": {"s2_child": {"on": {"EVENT_S2": {}}}}},
            }
        }
        events = extract_events(config)
        self.assertEqual(events, {"EVENT_S1", "EVENT_S2"})

    def test_extract_events_no_duplicates(self) -> None:
        """
        Confirms that duplicate event names are only included once.
        """
        logger.info("🧪 Testing that event extraction is de-duplicated.")
        config = {
            "on": {"DUPLICATE_EVENT": {}},
            "states": {"s1": {"on": {"DUPLICATE_EVENT": {}}}},
        }
        events = extract_events(config)
        self.assertEqual(events, {"DUPLICATE_EVENT"})

    def test_extract_events_empty_config(self) -> None:
        """
        Ensures an empty set is returned for a config with no 'on' blocks.
        """
        logger.info("🧪 Testing event extraction from an empty config.")
        config = {"id": "empty", "initial": "a", "states": {}}
        events = extract_events(config)
        self.assertEqual(events, set())

    def test_extract_events_from_multiple_levels(self) -> None:
        """
        Verifies extraction from multiple levels of nesting.
        """
        logger.info(
            "🧪 Testing event extraction from multiple nesting levels."
        )
        config = {
            "on": {"LEVEL0": {}},
            "states": {
                "s1": {
                    "on": {"LEVEL1": {}},
                    "states": {"s1_child": {"on": {"LEVEL2": {}}}},
                }
            },
        }
        events = extract_events(config)
        self.assertEqual(events, {"LEVEL0", "LEVEL1", "LEVEL2"})


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestHierarchyUtils
# -----------------------------------------------------------------------------


class TestHierarchyUtils(unittest.TestCase):
    """
    Verifies utility functions related to parent-child hierarchy detection.

    This suite tests the helper functions that are fundamental to the CLI's
    ability to automatically detect and handle hierarchical state machines.
    """

    def setUp(self) -> None:
        """
        Create common temporary JSON files for testing hierarchy utilities.
        """
        # 🧠 Define configs for a clear parent-child relationship.
        self.parent_config = {
            "id": "parent",
            "invoke": [{"src": "child1"}, {"src": "child2"}],
        }
        self.child_config = {"id": "child1", "on": {"EVENT1": {}}}

        # 📄 Create the temporary files on disk.
        self.parent_path = create_temp_json(self.parent_config)
        self.child_path = create_temp_json(self.child_config)

    def tearDown(self) -> None:
        """
        Clean up temporary files created during the test.
        """
        os.remove(self.parent_path)
        os.remove(self.child_path)

    def test_count_invokes(self) -> None:
        """
        Ensures _count_invokes correctly counts 'invoke' keys as a heuristic.
        """
        logger.info("🧪 Testing the _count_invokes utility.")
        # ✅ A parent with one "invoke" key (containing two services) has a score of 1.
        self.assertEqual(_count_invokes(self.parent_config), 1)
        # ✅ A child with no invokes should have a score of 0.
        self.assertEqual(_count_invokes(self.child_config), 0)

    def test_guess_hierarchy_identifies_parent(self) -> None:
        """
        Verifies guess_hierarchy correctly identifies the parent by invoke count.
        """
        logger.info("🧪 Testing guess_hierarchy for parent identification.")
        # 🧠 Provide the file paths in a mixed-up order.
        paths = [str(self.child_path), str(self.parent_path)]
        parent_result, children_result, _ = guess_hierarchy(paths)

        # ✅ Assert that the heuristic correctly identified the parent.
        self.assertEqual(parent_result, str(self.parent_path))
        self.assertIn(str(self.child_path), children_result)
