# tests/tests_cli/test_extractor.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Logic, Event, and Hierarchy Extractor
# -----------------------------------------------------------------------------
# This module provides a comprehensive suite of unit tests for the functions
# in the `xstate_statemachine.cli.extractor` module. The tests are designed
# to be robust, covering a wide array of valid configurations, edge cases,
# and malformed inputs to ensure the extractor functions are resilient and
# accurate.
#
# The test suite is organized into three main classes:
#   - TestLogicNamesExtractor: Focuses on verifying the correct parsing of
#     actions, guards, and services from state machine configurations.
#   - TestEventExtractor: Ensures the accurate discovery of all unique
#     event names declared within a machine's 'on' transitions.
#   - TestHierarchyUtils: Validates helper functions responsible for
#     detecting parent-child relationships between multiple state machine
#     files, a key feature for handling hierarchical state machines.
#
# The structure follows standard unittest practices, promoting clarity,
# maintainability, and easy extension as new features are added to the
# extractor logic.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import logging
import os
import unittest
from pathlib import Path
from typing import Dict, Any

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.cli.extractor import (
    _count_invokes,  # noqa : Protected method import for testing
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
# Set up a logger to provide detailed output during test execution.
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestLogicNamesExtractor
# -----------------------------------------------------------------------------


class TestLogicNamesExtractor(unittest.TestCase):
    """
    🧪 Verifies the `extract_logic_names` function across diverse configs.

    This suite tests the core logic extraction by providing various machine
    configurations and asserting that the returned sets of actions, guards,
    and services are correct. It covers standard cases, nested structures,
    and numerous edge cases and malformed inputs.
    """

    def test_extract_from_simple_config(self) -> None:
        """
        📄 Ensures logic names are extracted correctly from a basic, flat config.
        """
        logger.info("🧪 Testing extraction from a simple, flat configuration.")
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
        🌳 Ensures logic names are extracted from nested states and special keys.
        """
        logger.info(
            "🧪 Testing extraction from a nested config with 'invoke' and 'after'."
        )
        # 🧠 Run the extractor on a nested fixture.
        actions, guards, services = extract_logic_names(SAMPLE_CONFIG_NESTED)

        # ✅ Assert that nested logic is correctly identified.
        self.assertEqual(actions, {"after_action"})
        self.assertEqual(guards, {"always_guard"})
        self.assertEqual(services, {"child_service"})

    def test_extract_actions_from_list(self) -> None:
        """
        📋 Verifies extraction when actions are defined as a list of strings.
        """
        logger.info("🧪 Testing extraction of actions defined in a list.")
        config: Dict[str, Any] = {
            "id": "list_actions",
            "initial": "a",
            "states": {"a": {"entry": ["act1", "act2"]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act1", "act2"})

    def test_extract_actions_from_dict_type(self) -> None:
        """
        딕셔너리 Verifies extraction for actions defined as dicts with a 'type' key.
        """
        logger.info(
            "🧪 Testing extraction of actions defined as dict objects."
        )
        config: Dict[str, Any] = {
            "id": "dict_actions",
            "initial": "a",
            "states": {"a": {"entry": [{"type": "act_type"}]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act_type"})

    def test_extract_from_compound_state_on_done(self) -> None:
        """`onDone` on a COMPOUND/PARALLEL state (not an invoke) carries a
        transition too. It was skipped, so its guard/actions were never
        emitted and the generated machine failed at create_machine() --
        car_sales.json in the Stately corpus."""
        config = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "a",
                    "states": {"a": {"type": "final"}},
                    "onDone": {
                        "target": "q",
                        "guard": "regionCompleted",
                        "actions": ["recordDone"],
                    },
                },
                "q": {},
            },
        }
        actions, guards, _ = extract_logic_names(config)
        self.assertIn("recordDone", actions)
        self.assertIn("regionCompleted", guards)

    def test_bang_prefixed_guard_extracts_the_positive_name(self) -> None:
        """`"guard": "!ready"` is a negated reference to `ready`; the stub
        the generator must emit is `ready`, never a guard called `!ready`
        (which is not an identifier and cannot be implemented)."""
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "guard": "!ready"}}},
                "b": {},
            },
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"ready"})

    def test_extract_guards_from_cond_key(self) -> None:
        """
        🤔 Ensures guards are correctly extracted from the 'cond' key.
        """
        logger.info("🧪 Testing guard extraction from the 'cond' key.")
        config: Dict[str, Any] = {
            "id": "cond_guard",
            "initial": "a",
            "states": {"a": {"on": {"E": {"cond": "cond_guard"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"cond_guard"})

    def test_extract_guards_from_guard_key(self) -> None:
        """
        🛡️ Ensures guards are correctly extracted from the 'guard' key.
        """
        logger.info("🧪 Testing guard extraction from the 'guard' key.")
        config: Dict[str, Any] = {
            "id": "guard_key",
            "initial": "a",
            "states": {"a": {"on": {"E": {"guard": "g_key"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"g_key"})

    def test_extract_services_from_invoke_src(self) -> None:
        """
        📞 Ensures services are extracted from an 'invoke' object's 'src' key.
        """
        logger.info(
            "🧪 Testing service extraction from an 'invoke' 'src' key."
        )
        config: Dict[str, Any] = {
            "id": "invoke_src",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "my_service"}}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"my_service"})

    def test_extract_from_invoke_list(self) -> None:
        """
        📋 Verifies extraction when 'invoke' is a list of service objects.
        """
        logger.info("🧪 Testing extraction from a list of 'invoke' objects.")
        config: Dict[str, Any] = {
            "id": "invoke_list",
            "initial": "a",
            "states": {"a": {"invoke": [{"src": "srv1"}, {"src": "srv2"}]}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"srv1", "srv2"})

    def test_extract_actions_from_invoke_onDone(self) -> None:
        """
        ✅ Ensures actions are extracted from an 'onDone' transition.
        """
        logger.info(
            "🧪 Testing action extraction from an 'invoke.onDone' block."
        )
        config: Dict[str, Any] = {
            "id": "invoke_done",
            "initial": "a",
            "states": {"a": {"invoke": {"onDone": {"actions": "done_act"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"done_act"})

    def test_extract_guards_from_invoke_onError(self) -> None:
        """
        ❌ Ensures guards are extracted from an 'onError' transition.
        """
        logger.info(
            "🧪 Testing guard extraction from an 'invoke.onError' block."
        )
        config: Dict[str, Any] = {
            "id": "invoke_err",
            "initial": "a",
            "states": {"a": {"invoke": {"onError": {"guard": "err_guard"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"err_guard"})

    def test_extract_from_after_transitions(self) -> None:
        """
        ⏳ Ensures logic is extracted from delayed 'after' transitions.
        """
        logger.info("🧪 Testing logic extraction from 'after' transitions.")
        config: Dict[str, Any] = {
            "id": "after_test",
            "initial": "a",
            "states": {
                "a": {
                    "after": {
                        1000: {
                            "actions": "after_act",
                            "guard": "after_guard",
                        }
                    }
                }
            },
        }
        actions, guards, _ = extract_logic_names(config)
        self.assertEqual(actions, {"after_act"})
        self.assertEqual(guards, {"after_guard"})

    def test_extraction_no_duplicates(self) -> None:
        """
        👯 Confirms that duplicate logic names are de-duplicated into a set.
        """
        logger.info(
            "🧪 Verifying that extracted logic names are de-duplicated."
        )
        config: Dict[str, Any] = {
            "id": "dup",
            "initial": "a",
            "states": {"a": {"entry": "dup_act", "exit": "dup_act"}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"dup_act"})

    def test_extraction_from_parallel_states(self) -> None:
        """
        并行 Ensures logic is extracted from all regions of a parallel state.
        """
        logger.info("🧪 Testing logic extraction from parallel state regions.")
        config: Dict[str, Any] = {
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
        """
        텅텅 Confirms an empty state definition yields no logic names.
        """
        logger.info("🧪 Testing extraction from a functionally empty config.")
        config: Dict[str, Any] = {
            "id": "empty",
            "initial": "a",
            "states": {"a": {}},
        }
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_ignores_unknown_keys(self) -> None:
        """
        ❓ Ensures unknown keys in the config do not cause errors or extraction.
        """
        logger.info(
            "🧪 Verifying that unknown config keys are safely ignored."
        )
        config: Dict[str, Any] = {
            "id": "unknown",
            "initial": "a",
            "states": {"a": {"unknown_key": "value"}},
        }
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_multiple_transitions(self) -> None:
        """
        📜 Verifies extraction from events with multiple transition definitions.
        """
        logger.info(
            "🧪 Testing extraction from an event with multiple transition definitions."
        )
        config: Dict[str, Any] = {
            "id": "multi_trans",
            "initial": "a",
            "states": {
                "a": {"on": {"E": [{"actions": "act1"}, {"actions": "act2"}]}}
            },
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act1", "act2"})

    def test_extraction_actions_from_string_and_dict_mixed(self) -> None:
        """
        🔄 Ensures extraction works with mixed string and dict action definitions.
        """
        logger.info(
            "🧪 Testing extraction from a mix of string and dict actions."
        )
        config: Dict[str, Any] = {
            "id": "mixed_act",
            "initial": "a",
            "states": {"a": {"entry": ["str_act", {"type": "dict_act"}]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"str_act", "dict_act"})

    def test_extraction_guards_from_nested_onDone(self) -> None:
        """
        ✅ Verifies guard extraction from a nested `onDone` transition list.
        """
        logger.info(
            "🧪 Testing guard extraction from a nested 'invoke.onDone' list."
        )
        config: Dict[str, Any] = {
            "id": "nested_guard",
            "initial": "a",
            "states": {"a": {"invoke": {"onDone": [{"guard": "nested_g"}]}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"nested_g"})

    def test_extraction_services_from_nested_invoke(self) -> None:
        """
        🌳 Confirms service extraction from an `invoke` in a nested state.
        """
        logger.info(
            "🧪 Testing service extraction from a deeply nested 'invoke'."
        )
        config: Dict[str, Any] = {
            "id": "nested_srv",
            "initial": "a",
            "states": {
                "a": {"states": {"b": {"invoke": {"src": "nested_srv"}}}}
            },
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"nested_srv"})

    def test_extraction_ignores_non_string_non_dict_actions(self) -> None:
        """
        🚫 Ensures malformed action definitions (e.g., numbers) are ignored.
        """
        logger.info("🧪 Verifying that invalid action data types are ignored.")
        config: Dict[str, Any] = {
            "id": "invalid_act",
            "initial": "a",
            "states": {"a": {"entry": [123]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_after_with_list_trans(self) -> None:
        """
        ⏳ Verifies extraction from an `after` with a list of definitions.
        """
        logger.info(
            "🧪 Testing 'after' transition with a list of definitions."
        )
        config: Dict[str, Any] = {
            "id": "after_list",
            "initial": "a",
            "states": {
                "a": {"after": {1000: [{"actions": "a1"}, {"actions": "a2"}]}}
            },
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"a1", "a2"})

    def test_extraction_from_invoke_onError_list(self) -> None:
        """
        ❌ Verifies extraction from `onError` with a list of definitions.
        """
        logger.info(
            "🧪 Testing 'onError' transition with a list of definitions."
        )
        config: Dict[str, Any] = {
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
        """
        💨 Ensures a config without a 'states' key is handled gracefully.
        """
        logger.info(
            "🧪 Testing graceful handling of a config missing a 'states' key."
        )
        config: Dict[str, Any] = {"id": "no_states", "initial": "a"}
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_invalid_invoke(self) -> None:
        """
        🚫 Ensures a malformed `invoke` definition is ignored.
        """
        logger.info(
            "🧪 Verifying that a malformed 'invoke' definition is ignored."
        )
        config: Dict[str, Any] = {
            "id": "inv_inv",
            "initial": "a",
            "states": {"a": {"invoke": "not_dict"}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, set())

    def test_extraction_from_after_non_dict(self) -> None:
        """
        🚫 Ensures a malformed `after` definition is ignored.
        """
        logger.info(
            "🧪 Verifying that a malformed 'after' definition is ignored."
        )
        config: Dict[str, Any] = {
            "id": "inv_after",
            "initial": "a",
            "states": {"a": {"after": "not_dict"}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_on_non_dict(self) -> None:
        """
        🚫 Ensures a malformed `on` definition is ignored.
        """
        logger.info(
            "🧪 Verifying that a malformed 'on' definition is ignored."
        )
        config: Dict[str, Any] = {
            "id": "inv_on",
            "initial": "a",
            "states": {"a": {"on": "not_dict"}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_entry_non_list_str(self) -> None:
        """
        🚫 Ensures a malformed `entry` definition is ignored.
        """
        logger.info(
            "🧪 Verifying that a malformed 'entry' definition is ignored."
        )
        config: Dict[str, Any] = {
            "id": "inv_entry",
            "initial": "a",
            "states": {"a": {"entry": 123}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_trans_non_list_dict(self) -> None:
        """
        🎯 Verifies extraction when a transition is a single object, not a list.
        """
        logger.info(
            "🧪 Testing extraction from a transition defined as a single object."
        )
        config: Dict[str, Any] = {
            "id": "non_list_trans",
            "initial": "a",
            "states": {"a": {"on": {"E": {"actions": "trans_act"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"trans_act"})

    def test_extraction_from_invoke_src_non_str(self) -> None:
        """
        🚫 Ensures `invoke.src` is ignored if it's not a string.
        """
        logger.info("🧪 Verifying that a non-string 'invoke.src' is ignored.")
        config: Dict[str, Any] = {
            "id": "non_str_src",
            "initial": "a",
            "states": {"a": {"invoke": {"src": 123}}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, set())

    def test_extraction_from_guard_non_str(self) -> None:
        """
        🚫 Ensures `guard` is ignored if it's not a string.
        """
        logger.info("🧪 Verifying that a non-string 'guard' value is ignored.")
        config: Dict[str, Any] = {
            "id": "non_str_g",
            "initial": "a",
            "states": {"a": {"on": {"E": {"guard": 123}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, set())

    def test_extraction_from_after_trans_non_dict(self) -> None:
        """
        🚫 Ensures malformed `after` transition objects are ignored.
        """
        logger.info(
            "🧪 Verifying that a non-dict 'after' transition is ignored."
        )
        config: Dict[str, Any] = {
            "id": "non_dict_after",
            "initial": "a",
            "states": {"a": {"after": {1000: "not_dict"}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, set())

    def test_extraction_from_onDone_actions_list(self) -> None:
        """
        ✅ Verifies extraction from `onDone` when `actions` is a list.
        """
        logger.info(
            "🧪 Testing extraction from 'onDone' with a list of actions."
        )
        config: Dict[str, Any] = {
            "id": "done_list",
            "initial": "a",
            "states": {"a": {"invoke": {"onDone": {"actions": ["d1", "d2"]}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"d1", "d2"})

    def test_extraction_from_onError_guard(self) -> None:
        """
        ❌ Verifies guard extraction from a simple `onError` transition.
        """
        logger.info(
            "🧪 Testing guard extraction from a simple 'onError' transition."
        )
        config: Dict[str, Any] = {
            "id": "err_guard",
            "initial": "a",
            "states": {"a": {"invoke": {"onError": {"guard": "e_g"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"e_g"})

    def test_extraction_from_parallel_nested(self) -> None:
        """
        🌳 Confirms extraction from states nested inside a parallel region.
        """
        logger.info(
            "🧪 Testing extraction from states nested within a parallel region."
        )
        config: Dict[str, Any] = {
            "id": "par_nested",
            "type": "parallel",
            "states": {"p1": {"states": {"c1": {"entry": "p_act"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"p_act"})

    def test_extraction_from_final_state(self) -> None:
        """
        🏁 Ensures that final states, which have no logic, yield no names.
        """
        logger.info("🧪 Verifying no logic is extracted from a 'final' state.")
        config: Dict[str, Any] = {
            "id": "final_state",
            "initial": "a",
            "states": {"a": {"type": "final"}},
        }
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_history_state(self) -> None:
        """
        📜 Ensures that history states, which have no logic, yield no names.
        """
        logger.info(
            "🧪 Verifying no logic is extracted from a 'history' state."
        )
        config: Dict[str, Any] = {
            "id": "hist",
            "initial": "a",
            "states": {"a": {"history": "deep"}},
        }
        actions, guards, services = extract_logic_names(config)
        self.assertEqual(actions, set())
        self.assertEqual(guards, set())
        self.assertEqual(services, set())

    def test_extraction_from_invalid_trans_target(self) -> None:
        """
        🚫 Ensures extraction succeeds even if a transition's target is malformed.
        """
        logger.info(
            "🧪 Verifying extraction ignores an invalid 'target' value."
        )
        config: Dict[str, Any] = {
            "id": "inv_target",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": 123, "actions": "inv_act"}}}
            },
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"inv_act"})

    def test_extraction_from_cond_in_after(self) -> None:
        """
        ⏳ Verifies guard extraction using 'cond' in an `after` transition.
        """
        logger.info(
            "🧪 Testing guard extraction from 'cond' key in an 'after' block."
        )
        config: Dict[str, Any] = {
            "id": "after_cond",
            "initial": "a",
            "states": {"a": {"after": {1000: {"cond": "a_cond"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"a_cond"})

    def test_extraction_from_multiple_invoke_in_list(self) -> None:
        """
        📋 Confirms service extraction from a list of `invoke` definitions.
        """
        logger.info(
            "🧪 Testing extraction from a list of 'invoke' definitions."
        )
        config: Dict[str, Any] = {
            "id": "multi_inv",
            "initial": "a",
            "states": {"a": {"invoke": [{"src": "s1"}, {"src": "s2"}]}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"s1", "s2"})

    def test_extraction_from_onDone_in_after(self) -> None:
        """
        🚫 Ensures `onDone` in `after` is ignored as it's not valid SCXML.
        """
        logger.info(
            "🧪 Verifying 'onDone' inside an 'after' block is ignored (invalid)."
        )
        config: Dict[str, Any] = {
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
    📨 Verifies the `extract_events` utility function.

    This suite tests the recursive discovery of event names from 'on'
    transition blocks at any level of a state machine configuration.
    """

    def test_extract_events_from_simple_on(self) -> None:
        """
        📄 Ensures events are extracted from a simple 'on' block.
        """
        logger.info("🧪 Testing event extraction from a simple 'on' block.")
        config: Dict[str, Any] = {"on": {"EVENT1": {}, "EVENT2": {}}}
        events = extract_events(config)
        self.assertEqual(events, {"EVENT1", "EVENT2"})

    def test_extract_events_from_nested_states(self) -> None:
        """
        🌳 Verifies event extraction from 'on' blocks within nested states.
        """
        logger.info("🧪 Testing event extraction from nested states.")
        config: Dict[str, Any] = {
            "states": {
                "s1": {"on": {"EVENT_S1": {}}},
                "s2": {"states": {"s2_child": {"on": {"EVENT_S2": {}}}}},
            }
        }
        events = extract_events(config)
        self.assertEqual(events, {"EVENT_S1", "EVENT_S2"})

    def test_extract_events_no_duplicates(self) -> None:
        """
        👯 Confirms that duplicate event names are only included once.
        """
        logger.info(
            "🧪 Verifying that extracted event names are de-duplicated."
        )
        config: Dict[str, Any] = {
            "on": {"DUPLICATE_EVENT": {}},
            "states": {"s1": {"on": {"DUPLICATE_EVENT": {}}}},
        }
        events = extract_events(config)
        self.assertEqual(events, {"DUPLICATE_EVENT"})

    def test_extract_events_empty_config(self) -> None:
        """
        텅텅 Ensures an empty set is returned for a config with no 'on' blocks.
        """
        logger.info(
            "🧪 Testing event extraction from a config with no events."
        )
        config: Dict[str, Any] = {
            "id": "empty",
            "initial": "a",
            "states": {},
        }
        events = extract_events(config)
        self.assertEqual(events, set())

    def test_extract_events_from_multiple_levels(self) -> None:
        """
        🌳 Verifies extraction from multiple levels of nesting.
        """
        logger.info(
            "🧪 Testing event extraction from multiple nesting levels."
        )
        config: Dict[str, Any] = {
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
    👨‍👩‍👧‍👦 Verifies utility functions for parent-child hierarchy detection.

    This suite tests the helper functions that are fundamental to the CLI's
    ability to automatically detect and handle hierarchical state machines
    by reading multiple JSON files.
    """

    def setUp(self) -> None:
        """
        📝 Set up the test environment before each test.

        This method creates temporary JSON files for a clear parent-child
        relationship to be used in the hierarchy guessing tests.
        """
        super().setUp()
        logger.info("🛠️ Setting up temporary files for hierarchy tests.")

        # 🧠 Define configs for a clear parent-child relationship.
        self.parent_config: Dict[str, Any] = {
            "id": "parent",
            "invoke": [{"src": "child1"}, {"src": "child2"}],
        }
        self.child_config: Dict[str, Any] = {
            "id": "child1",
            "on": {"EVENT1": {}},
        }

        # 📄 Create the temporary files on disk.
        self.parent_path: Path = create_temp_json(self.parent_config)
        self.child_path: Path = create_temp_json(self.child_config)
        logger.info(f"📄 Created parent at: {self.parent_path}")
        logger.info(f"📄 Created child at: {self.child_path}")

    def tearDown(self) -> None:
        """
        🧹 Clean up the test environment after each test.

        This method removes the temporary JSON files created in `setUp`
        to ensure a clean state for subsequent tests.
        """
        super().tearDown()
        logger.info("🧹 Tearing down temporary files.")
        try:
            os.remove(self.parent_path)
            os.remove(self.child_path)
            logger.info("✅ Successfully removed temporary files.")
        except OSError as e:
            logger.error(f"❌ Error removing temporary files: {e}")

    def test_count_invokes(self) -> None:
        """
        🔢 Ensures _count_invokes correctly counts 'invoke' keys as a heuristic.
        """
        logger.info("🧪 Testing the `_count_invokes` utility.")
        # 🧠 A parent with one "invoke" key (containing two services) has a score of 1.
        # The function counts the 'invoke' key itself, not the number of services.
        parent_invoke_count = _count_invokes(self.parent_config)
        self.assertEqual(
            parent_invoke_count, 1, "Parent should have an invoke count of 1"
        )

        # 🧠 A child with no invokes should have a score of 0.
        child_invoke_count = _count_invokes(self.child_config)
        self.assertEqual(
            child_invoke_count, 0, "Child should have an invoke count of 0"
        )

    def test_guess_hierarchy_identifies_parent(self) -> None:
        """
        🧐 Verifies guess_hierarchy correctly identifies the parent by invoke count.
        """
        logger.info("🧪 Testing `guess_hierarchy` for parent identification.")
        # 🧠 Provide the file paths in a mixed-up order to test the logic.
        paths = [str(self.child_path), str(self.parent_path)]
        parent_result, children_result, _ = guess_hierarchy(paths)

        # ✅ Assert that the heuristic correctly identified the parent and child.
        self.assertEqual(
            parent_result,
            str(self.parent_path),
            "The file with more invokes should be the parent.",
        )
        self.assertIn(
            str(self.child_path),
            children_result,
            "The file with fewer invokes should be in the children list.",
        )
