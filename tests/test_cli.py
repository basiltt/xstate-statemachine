# /tests/test_cli.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: Command-Line Interface (CLI)
# -----------------------------------------------------------------------------
# This module provides a comprehensive test suite for the CLI tool defined in
# `cli.py`. It employs a combination of unit tests for individual functions
# and integration-style tests for the main CLI entry point.
#
# The suite validates all major functionalities, including:
#   -   🧩 Logic Extraction: Correctly parsing actions, guards, and services
#       from various state machine configuration structures.
#   -   📝 Code Generation: Ensuring logic and runner files are generated
#       correctly based on different user-provided options (e.g., async vs.
#       sync, class vs. function style).
#   -   ⚙️ Helper Functions: Verifying utility functions like boolean
#       normalization.
#   -   🚀 CLI Entry Point: Testing the full CLI behavior with argument parsing,
#       file output, error handling, and user feedback messages.
#
# Temporary files and directory mocks are used extensively to isolate tests
# and verify outputs without side effects on the actual filesystem.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import json
import logging
import os
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine.cli import (
    extract_logic_names,
    generate_logic_code,
    generate_runner_code,
    main,
    normalize_bool,
)

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Test Helpers & Fixtures
# -----------------------------------------------------------------------------


def create_temp_json(config: Dict[str, Any]) -> Path:
    """Creates a temporary JSON file with the given configuration.

    This helper function is crucial for CLI tests that require a file path
    as an input argument. It writes a dictionary to a temporary JSON file
    and returns its `Path` object.

    Args:
        config (Dict[str, Any]): The Python dictionary to dump as JSON.

    Returns:
        Path: The `pathlib.Path` object pointing to the created temporary file.
    """
    # 📝 Create a named temporary file that is not deleted on close.
    with tempfile.NamedTemporaryFile(
        dir=os.getcwd(),
        mode="w",
        delete=False,
        suffix=".json",
        encoding="utf-8",
    ) as tmp:
        json.dump(config, tmp)
    # ✅ Return the path to the newly created file.
    return Path(tmp.name)


# --- Test Data Fixtures ---
SAMPLE_CONFIG_SIMPLE: Dict[str, Any] = {
    "id": "simple",
    "initial": "idle",
    "states": {
        "idle": {
            "entry": "enter_action",
            "exit": "exit_action",
            "on": {
                "EVENT": {
                    "target": "active",
                    "actions": "trans_action",
                    "guard": "trans_guard",
                }
            },
        },
        "active": {},
    },
}

SAMPLE_CONFIG_NESTED: Dict[str, Any] = {
    "id": "nested",
    "initial": "parent",
    "states": {
        "parent": {
            "initial": "child",
            "states": {
                "child": {
                    "invoke": {"src": "child_service"},
                    "after": {
                        1000: {"target": "sibling", "actions": "after_action"}
                    },
                },
                "sibling": {"on": {"": {"guard": "always_guard"}}},
            },
        },
    },
}

SAMPLE_CONFIG_MULTIPLE: List[Dict[str, Any]] = [
    SAMPLE_CONFIG_SIMPLE,
    SAMPLE_CONFIG_NESTED,
]


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestExtractLogicNames
# -----------------------------------------------------------------------------
class TestExtractLogicNames(unittest.TestCase):
    """Verifies the `extract_logic_names` function across various configs."""

    def test_extract_from_simple_config(self) -> None:
        """Ensures logic names are extracted correctly from a basic, flat config."""
        logger.info("🧪 Testing extraction from a simple config.")
        actions, guards, services = extract_logic_names(SAMPLE_CONFIG_SIMPLE)
        self.assertEqual(
            actions, {"enter_action", "exit_action", "trans_action"}
        )
        self.assertEqual(guards, {"trans_guard"})
        self.assertEqual(services, set())

    def test_extract_from_nested_config(self) -> None:
        """Ensures logic names are extracted from nested states, `invoke`, and `after`."""
        logger.info("🧪 Testing extraction from a nested config.")
        actions, guards, services = extract_logic_names(SAMPLE_CONFIG_NESTED)
        self.assertEqual(actions, {"after_action"})
        self.assertEqual(guards, {"always_guard"})
        self.assertEqual(services, {"child_service"})

    def test_extract_actions_from_list(self) -> None:
        """Verifies extraction when actions are defined as a list of strings."""
        logger.info("🧪 Testing extraction of list-based actions.")
        config = {
            "id": "list_actions",
            "initial": "a",
            "states": {"a": {"entry": ["act1", "act2"]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act1", "act2"})

    def test_extract_actions_from_dict_type(self) -> None:
        """Verifies extraction when actions are defined as dictionaries with a 'type' key."""
        logger.info("🧪 Testing extraction of dict-type actions.")
        config = {
            "id": "dict_actions",
            "initial": "a",
            "states": {"a": {"entry": [{"type": "act_type"}]}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"act_type"})

    def test_extract_guards_from_cond_key(self) -> None:
        """Ensures guards are correctly extracted from the 'cond' key."""
        logger.info("🧪 Testing extraction of guards via 'cond' key.")
        config = {
            "id": "cond_guard",
            "initial": "a",
            "states": {"a": {"on": {"E": {"cond": "cond_guard"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"cond_guard"})

    def test_extract_guards_from_guard_key(self) -> None:
        """Ensures guards are correctly extracted from the 'guard' key."""
        logger.info("🧪 Testing extraction of guards via 'guard' key.")
        config = {
            "id": "guard_key",
            "initial": "a",
            "states": {"a": {"on": {"E": {"guard": "g_key"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"g_key"})

    def test_extract_services_from_invoke_src(self) -> None:
        """Ensures services are correctly extracted from an 'invoke' object's 'src' key."""
        logger.info("🧪 Testing extraction of services from invoke src.")
        config = {
            "id": "invoke_src",
            "initial": "a",
            "states": {"a": {"invoke": {"src": "my_service"}}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"my_service"})

    def test_extract_from_invoke_list(self) -> None:
        """Verifies extraction when 'invoke' is defined as a list of service objects."""
        logger.info("🧪 Testing extraction from list-based invoke.")
        config = {
            "id": "invoke_list",
            "initial": "a",
            "states": {"a": {"invoke": [{"src": "srv1"}, {"src": "srv2"}]}},
        }
        _, _, services = extract_logic_names(config)
        self.assertEqual(services, {"srv1", "srv2"})

    def test_extract_actions_from_invoke_onDone(self) -> None:
        """Ensures actions are extracted from an 'onDone' transition within an 'invoke'."""
        logger.info("🧪 Testing extraction from invoke onDone actions.")
        config = {
            "id": "invoke_done",
            "initial": "a",
            "states": {"a": {"invoke": {"onDone": {"actions": "done_act"}}}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"done_act"})

    def test_extract_guards_from_invoke_onError(self) -> None:
        """Ensures guards are extracted from an 'onError' transition within an 'invoke'."""
        logger.info("🧪 Testing extraction from invoke onError guards.")
        config = {
            "id": "invoke_err",
            "initial": "a",
            "states": {"a": {"invoke": {"onError": {"guard": "err_guard"}}}},
        }
        _, guards, _ = extract_logic_names(config)
        self.assertEqual(guards, {"err_guard"})

    def test_extract_from_after_transitions(self) -> None:
        """Ensures actions and guards are extracted from delayed 'after' transitions."""
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

    def test_extraction_from_parallel_states(self) -> None:
        """Ensures logic is extracted correctly from all regions of a parallel state."""
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

    def test_extraction_no_duplicates(self) -> None:
        """Confirms that duplicate logic names are only recorded once."""
        logger.info("🧪 Testing no duplicates in extraction.")
        config = {
            "id": "dup",
            "initial": "a",
            "states": {"a": {"entry": "dup_act", "exit": "dup_act"}},
        }
        actions, _, _ = extract_logic_names(config)
        self.assertEqual(actions, {"dup_act"})

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
# 🏛️ Test Class: TestGenerateLogicCode
# -----------------------------------------------------------------------------
class TestGenerateLogicCode(unittest.TestCase):
    """Verifies the `generate_logic_code` function under various options."""

    def setUp(self) -> None:
        """Set up common data for code generation tests."""
        self.actions = {"act1", "act2"}
        self.guards = {"guard1"}
        self.services = {"srv1"}
        self.machine_name = "test_machine"

    def test_generate_class_style_sync_with_log(self) -> None:
        """Ensures correct generation for: class style, sync mode, with logging."""
        logger.info("🧪 Testing class style sync with log.")
        code = generate_logic_code(
            self.actions,
            self.guards,
            self.services,
            "class",
            True,
            False,
            self.machine_name,
        )
        self.assertIn("class TestMachineLogic:", code)
        self.assertIn('logger.info("Executing action act1")', code)
        self.assertIn("time.sleep(1)", code)
        self.assertNotIn("import asyncio", code)
        self.assertIn("import time", code)

    def test_generate_function_style_async_no_log(self) -> None:
        """Ensures correct generation for: function style, async mode, no logging."""
        logger.info("🧪 Testing function style async no log.")
        code = generate_logic_code(
            self.actions,
            self.guards,
            self.services,
            "function",
            False,
            True,
            self.machine_name,
        )
        self.assertNotIn("class ", code)
        self.assertNotIn("logger.info", code)
        self.assertIn("await asyncio.sleep(1)", code)
        self.assertIn("import asyncio", code)
        self.assertNotIn("import time", code)

    def test_generate_no_services_no_time_import(self) -> None:
        """Confirms `time` is not imported in sync mode if there are no services."""
        logger.info("🧪 Testing no services, no time import.")
        code = generate_logic_code(
            self.actions,
            self.guards,
            set(),
            "class",
            True,
            False,
            self.machine_name,
        )
        self.assertNotIn("import time", code)

    def test_generate_with_services_time_import(self) -> None:
        """Confirms `time` is imported in sync mode when services are present."""
        logger.info("🧪 Testing with services, time import.")
        code = generate_logic_code(
            self.actions,
            self.guards,
            self.services,
            "class",
            True,
            False,
            self.machine_name,
        )
        self.assertIn("import time", code)

    def test_generate_class_name_from_machine_name(self) -> None:
        """Verifies that the logic class name is correctly derived from the machine name."""
        logger.info("🧪 Testing class name from machine name.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, "my_machine"
        )
        self.assertIn("class MyMachineLogic:", code)

    def test_generate_no_actions_guards_services(self) -> None:
        """Ensures code is generated gracefully when there are no logic implementations."""
        logger.info("🧪 Testing empty logic code.")
        code = generate_logic_code(
            set(), set(), set(), "function", False, True, self.machine_name
        )
        self.assertIn("# ⚙️ Actions", code)
        self.assertIn("# 🛡️ Guards", code)
        self.assertIn("# 🔄 Services", code)
        self.assertNotIn("def ", code[code.find("# ⚙️ Actions") :])

    def test_generate_async_actions(self) -> None:
        """Checks for `async def` and `await` keywords in generated async actions."""
        logger.info("🧪 Testing async actions.")
        code = generate_logic_code(
            {"async_act"},
            set(),
            set(),
            "class",
            False,
            True,
            self.machine_name,
        )
        self.assertIn("async def async_act(", code)
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_sync_guards_no_log(self) -> None:
        """Verifies a simple sync guard is generated without logging when disabled."""
        logger.info("🧪 Testing sync guards no log.")
        code = generate_logic_code(
            set(),
            {"sync_g"},
            set(),
            "function",
            False,
            False,
            self.machine_name,
        )
        self.assertNotIn("logger.info", code)
        self.assertIn("return True", code)

    def test_generate_services_async(self) -> None:
        """Checks for `async def` and `await` in generated async services."""
        logger.info("🧪 Testing async services.")
        code = generate_logic_code(
            set(), set(), {"async_srv"}, "class", True, True, self.machine_name
        )
        self.assertIn("async def async_srv(", code)
        self.assertIn("await asyncio.sleep(1)", code)
        self.assertIn('logger.info("Running service async_srv")', code)

    def test_generate_services_sync(self) -> None:
        """Checks for `time.sleep` in generated sync services."""
        logger.info("🧪 Testing sync services.")
        code = generate_logic_code(
            set(),
            set(),
            {"sync_srv"},
            "function",
            False,
            False,
            self.machine_name,
        )
        self.assertIn("def sync_srv(", code)
        self.assertIn("time.sleep(1)", code)
        self.assertNotIn("logger.info", code)

    def test_generate_interpreter_type_in_params(self) -> None:
        """Ensures the interpreter type hint changes based on async mode."""
        logger.info("🧪 Testing interpreter type in function params.")
        code_sync = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name
        )
        code_async = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name
        )
        self.assertIn(
            "interpreter: Interpreter if False else SyncInterpreter,",
            code_sync,
        )
        self.assertIn(
            "interpreter: Interpreter if True else SyncInterpreter,",
            code_async,
        )

    def test_generate_return_type_for_actions(self) -> None:
        """Ensures action return type hint changes based on async mode."""
        logger.info("🧪 Testing return type for actions.")
        code_sync = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name
        )
        code_async = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name
        )
        self.assertIn("-> None:", code_sync)
        self.assertIn("-> Awaitable[None]:", code_async)

    def test_generate_return_type_for_services(self) -> None:
        """Ensures service return type hint changes based on async mode."""
        logger.info("🧪 Testing return type for services.")
        code_sync = generate_logic_code(
            set(), set(), {"srv"}, "class", False, False, self.machine_name
        )
        code_async = generate_logic_code(
            set(), set(), {"srv"}, "class", False, True, self.machine_name
        )
        self.assertIn("-> Dict[str, Any]:", code_sync)
        self.assertIn("-> Awaitable[Dict[str, Any]]:", code_async)

    def test_generate_guards_return_bool(self) -> None:
        """Verifies that generated guards are correctly type-hinted to return `bool`."""
        logger.info("🧪 Testing guards return bool.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, False, self.machine_name
        )
        self.assertIn("-> bool:", code)

    def test_generate_function_style_no_self(self) -> None:
        """Confirms that 'self' is not included in function-style logic."""
        logger.info("🧪 Testing function style no self.")
        code = generate_logic_code(
            {"act"}, set(), set(), "function", False, False, self.machine_name
        )
        self.assertNotIn("self, ", code)

    def test_generate_no_dummy_sleep_if_no_log(self) -> None:
        """Ensures dummy async sleep is present even if logging is off."""
        logger.info("🧪 Testing no dummy sleep if no log.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name
        )
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_sorted_names(self) -> None:
        """Verifies that generated functions are sorted alphabetically."""
        logger.info("🧪 Testing sorted names in code.")
        actions = {"z_act", "a_act"}
        code = generate_logic_code(
            actions, set(), set(), "class", False, False, self.machine_name
        )
        self.assertTrue(code.find("a_act") < code.find("z_act"))

    def test_generate_logger_config(self) -> None:
        """Ensures the standard logger configuration is present in the generated file."""
        logger.info("🧪 Testing logger config.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name
        )
        self.assertIn("logger = logging.getLogger(__name__)", code)

    def test_generate_typing_imports(self) -> None:
        """Verifies that necessary `typing` imports are included."""
        logger.info("🧪 Testing typing imports.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name
        )
        self.assertIn("from typing import Any, Dict", code)

    def test_generate_xstate_imports(self) -> None:
        """Verifies that necessary `xstate_statemachine` imports are included."""
        logger.info("🧪 Testing xstate imports.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name
        )
        self.assertIn(
            "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition",
            code,
        )

    def test_generate_awaitable_for_async_guards_no(self) -> None:
        """Confirms that guards remain synchronous even in async mode."""
        logger.info("🧪 Testing no Awaitable for guards in async.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, True, self.machine_name
        )
        self.assertIn("-> bool:", code)
        self.assertNotIn("Awaitable[bool]", code)

    def test_generate_no_imports_if_no_services_async(self) -> None:
        """Confirms `time` is not imported if there are no sync services."""
        logger.info("🧪 Testing no time if no services sync.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name
        )
        self.assertNotIn("import time", code)

    def test_generate_class_indent_correct(self) -> None:
        """Checks for correct indentation in class-style generation."""
        logger.info("🧪 Testing class indent.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name
        )
        self.assertIn("    # ⚙️ Actions", code)

    def test_generate_function_indent_correct(self) -> None:
        """Checks for correct (zero) indentation in function-style generation."""
        logger.info("🧪 Testing function indent.")
        code = generate_logic_code(
            set(), set(), set(), "function", False, False, self.machine_name
        )
        self.assertIn("# ⚙️ Actions", code)
        self.assertNotIn("    # ⚙️ Actions", code)

    def test_generate_docstring_for_actions(self) -> None:
        """Ensures the correct docstring format for generated actions."""
        logger.info("🧪 Testing docstring for actions.")
        code = generate_logic_code(
            {"my_act"}, set(), set(), "class", False, False, self.machine_name
        )
        self.assertIn('"""Action: my_act."""', code)

    def test_generate_docstring_for_guards(self) -> None:
        """Ensures the correct docstring format for generated guards."""
        logger.info("🧪 Testing docstring for guards.")
        code = generate_logic_code(
            set(), {"my_g"}, set(), "class", False, False, self.machine_name
        )
        self.assertIn('"""Guard: my_g."""', code)

    def test_generate_docstring_for_services(self) -> None:
        """Ensures the correct docstring format for generated services."""
        logger.info("🧪 Testing docstring for services.")
        code = generate_logic_code(
            set(), set(), {"my_srv"}, "class", False, False, self.machine_name
        )
        self.assertIn('"""Service: my_srv."""', code)

    def test_generate_pass_todo_for_actions(self) -> None:
        """Verifies the placeholder `pass` and `TODO` comment for actions."""
        logger.info("🧪 Testing pass TODO for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name
        )
        self.assertIn("pass  # TODO: Implement action", code)

    def test_generate_return_true_todo_for_guards(self) -> None:
        """Verifies the placeholder `return True` and `TODO` comment for guards."""
        logger.info("🧪 Testing return True TODO for guards.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, False, self.machine_name
        )
        self.assertIn("return True  # TODO: Implement guard", code)

    def test_generate_return_dict_todo_for_services(self) -> None:
        """Verifies the placeholder return dictionary and `TODO` comment for services."""
        logger.info("🧪 Testing return dict TODO for services.")
        code = generate_logic_code(
            set(), set(), {"srv"}, "class", False, False, self.machine_name
        )
        self.assertIn(
            "return {'result': 'done'}  # TODO: Implement service", code
        )

    def test_generate_logger_info_for_actions_log_true(self) -> None:
        """Verifies the logging statement for actions when logging is enabled."""
        logger.info("🧪 Testing logger info for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", True, False, self.machine_name
        )
        self.assertIn('logger.info("Executing action act")', code)

    def test_generate_no_logger_for_actions_log_false(self) -> None:
        """Ensures no logging statement is generated when logging is disabled."""
        logger.info("🧪 Testing no logger for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name
        )
        self.assertNotIn("logger.info", code)

    def test_generate_logger_for_guards(self) -> None:
        """Verifies the logging statement for guards when logging is enabled."""
        logger.info("🧪 Testing logger for guards.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", True, False, self.machine_name
        )
        self.assertIn('logger.info("Evaluating guard g")', code)

    def test_generate_logger_for_services(self) -> None:
        """Verifies the logging statement for services when logging is enabled."""
        logger.info("🧪 Testing logger for services.")
        code = generate_logic_code(
            set(), set(), {"srv"}, "class", True, False, self.machine_name
        )
        self.assertIn('logger.info("Running service srv")', code)

    def test_generate_dummy_async_for_async_actions_no_log(self) -> None:
        """Ensures dummy `asyncio.sleep` is present in async actions."""
        logger.info("🧪 Testing dummy async for actions no log.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name
        )
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_no_dummy_for_sync_actions(self) -> None:
        """Ensures no `sleep` call is present in sync actions."""
        logger.info("🧪 Testing no dummy for sync actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name
        )
        self.assertNotIn("sleep", code)

    def test_generate_sorted_actions_guards_services(self) -> None:
        """Confirms that all generated functions are sorted alphabetically within their sections."""
        logger.info("🧪 Testing sorted order in generated code.")
        actions = {"z", "a"}
        guards = {"y", "b"}
        services = {"x", "c"}
        code = generate_logic_code(
            actions, guards, services, "class", False, False, self.machine_name
        )
        pos_a = code.find("def a(")
        pos_z = code.find("def z(")
        pos_b = code.find("def b(")
        pos_y = code.find("def y(")
        pos_c = code.find("def c(")
        pos_x = code.find("def x(")
        self.assertTrue(pos_a < pos_z)
        self.assertTrue(pos_b < pos_y)
        self.assertTrue(pos_c < pos_x)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestGenerateRunnerCode
# -----------------------------------------------------------------------------
class TestGenerateRunnerCode(unittest.TestCase):
    """Verifies the `generate_runner_code` function under various options."""

    def setUp(self) -> None:
        """Set up common data for runner code generation tests."""
        self.machine_names = ["test_machine"]
        self.configs = [SAMPLE_CONFIG_SIMPLE]
        self.json_filenames = ["test.json"]
        self.machine_name = "test_machine"

    def test_generate_single_sync_class_loader_sleep_log_file2(self) -> None:
        """Tests the default generation case: single machine, sync, class-style, 2 files."""
        logger.info("🧪 Testing single sync class loader sleep log file2.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn(
            "from test_machine_logic import TestMachineLogic as LogicProvider",
            code,
        )
        self.assertIn("logic_provider = LogicProvider()", code)
        self.assertIn("time.sleep(2)", code)
        self.assertIn("logging.basicConfig", code)
        self.assertIn("SyncInterpreter(machine)", code)
        self.assertNotIn("asyncio.run", code)

    def test_generate_single_async_function_no_loader_no_sleep_no_log_file1(
        self,
    ) -> None:
        """Tests a non-default case: async, function-style, no loader, 1 file."""
        logger.info(
            "🧪 Testing single async function no loader no sleep no log file1."
        )
        code = generate_runner_code(
            self.machine_names,
            True,
            "function",
            False,
            False,
            2,
            False,
            1,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("LogicProvider()", code)
        self.assertNotIn("time.sleep", code)
        self.assertNotIn("logging.basicConfig", code)
        self.assertIn("Interpreter(machine)", code)
        self.assertIn("asyncio.run(main())", code)

    def test_generate_multiple_machines(self) -> None:
        """Ensures code is generated correctly for multiple machine inputs."""
        logger.info("🧪 Testing multiple machines.")
        machine_names = ["m1", "m2"]
        configs = [SAMPLE_CONFIG_SIMPLE, SAMPLE_CONFIG_NESTED]
        json_filenames = ["m1.json", "m2.json"]
        code = generate_runner_code(
            machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            configs,
            json_filenames,
        )
        self.assertIn("def run_m1() -> None:", code)
        self.assertIn("def run_m2() -> None:", code)
        self.assertIn("run_m1()", code)
        self.assertIn("run_m2()", code)

    def test_generate_dummy_event_from_config(self) -> None:
        """Verifies that the initial event is taken from the config if available."""
        logger.info("🧪 Testing dummy event from config.")
        config = {"on": {"CUSTOM_EVENT": {}}}
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            [config],
            self.json_filenames,
        )
        self.assertIn("CUSTOM_EVENT", code)

    def test_generate_default_dummy_event(self) -> None:
        """Verifies the fallback when no events are defined in the config."""
        logger.info("🧪 Testing fallback for no events in config.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            [{}],
            self.json_filenames,
        )
        self.assertIn(
            "# No events defined in the machine. Add manual sends here.", code
        )
        self.assertIn("pass", code)  # Ensures the placeholder is present

    def test_generate_path_config_load(self) -> None:
        """Ensures the correct JSON filename is used for loading the config."""
        logger.info("🧪 Testing config path load.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            ["custom.json"],
        )
        self.assertIn("custom.json", code)

    def test_generate_no_loader_logic(self) -> None:
        """Verifies that manual logic binding code is generated when loader is off."""
        logger.info("🧪 Testing no loader logic.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            False,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("machine_logic = MachineLogic", code)

    def test_generate_file_count_1_combined(self) -> None:
        """Confirms generation for a single combined file runs without error."""
        logger.info("🧪 Testing file count 1.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            1,
            self.configs,
            self.json_filenames,
        )
        # The runner code itself is the same, but it won't import its own logic file.
        self.assertIn("def main() -> None:", code)

    def test_generate_async_await_prefix(self) -> None:
        """Ensures `await` is correctly prefixed to calls in async mode."""
        logger.info("🧪 Testing async await prefix.")
        code = generate_runner_code(
            self.machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("await interpreter.start()", code)

    def test_generate_no_log_no_basicConfig(self) -> None:
        """Verifies that `logging.basicConfig` is absent when logging is off."""
        logger.info("🧪 Testing no log no basicConfig.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            False,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("logging.basicConfig", code)

    def test_generate_import_time_if_sleep(self) -> None:
        """Confirms `time` is imported when `sleep` is enabled."""
        logger.info("🧪 Testing import time if sleep.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("import time", code)

    def test_generate_no_import_time_if_no_sleep(self) -> None:
        """Confirms `time` is not imported when `sleep` is disabled."""
        logger.info("🧪 Testing no import time if no sleep.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            False,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("import time", code)

    def test_generate_async_import_asyncio(self) -> None:
        """Confirms `asyncio` is imported when `async-mode` is enabled."""
        logger.info("🧪 Testing import asyncio if async.")
        code = generate_runner_code(
            self.machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("import asyncio", code)

    def test_generate_no_asyncio_if_sync(self) -> None:
        """Confirms `asyncio` is not imported in sync mode."""
        logger.info("🧪 Testing no asyncio if sync.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("import asyncio", code)

    def test_generate_logging_inspector(self) -> None:
        """Ensures the `LoggingInspector` is included by default."""
        logger.info("🧪 Testing LoggingInspector.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("interpreter.use(LoggingInspector())", code)

    def test_generate_initial_state_log(self) -> None:
        """Verifies the log message for the initial machine state."""
        logger.info("🧪 Testing initial state log.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn(
            'logger.info(f"Initial state: {interpreter.current_state_ids}")',
            code,
        )

    def test_generate_simulation_log_messages(self) -> None:
        """Verifies the standard log messages for starting and ending the simulation."""
        logger.info("🧪 Testing simulation log messages.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn(
            "logger.info('--- Running simulation with all defined events ---')",
            code,
        )
        self.assertIn(
            "logger.info(f'--- ✅ Simulation ended in state: {interpreter.current_state_ids} ---')",
            code,
        )

    def test_generate_main_if_async(self) -> None:
        """Ensures the `asyncio.run(main())` block is present in async mode."""
        logger.info("🧪 Testing main if async.")
        code = generate_runner_code(
            self.machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("asyncio.run(main())", code)

    def test_generate_main_if_sync(self) -> None:
        """Ensures a direct `main()` call is present in sync mode."""
        logger.info("🧪 Testing main if sync.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("if __name__ == '__main__':\n    main()", code)
        self.assertNotIn("asyncio.run", code)

    def test_generate_multiple_async_functions(self) -> None:
        """Checks for correct `async def` and `await` usage with multiple machines."""
        logger.info("🧪 Testing multiple async functions.")
        machine_names = ["m1", "m2"]
        code = generate_runner_code(
            machine_names,
            True,
            "class",
            True,
            True,
            2,
            True,
            2,
            SAMPLE_CONFIG_MULTIPLE,
            ["f1.json", "f2.json"],
        )
        self.assertIn("async def run_m1() -> None:", code)
        self.assertIn("async def run_m2() -> None:", code)
        self.assertIn("async def main() -> None:", code)
        self.assertIn("await run_m1()", code)
        self.assertIn("await run_m2()", code)

    def test_generate_docstring_for_run_functions(self) -> None:
        """Verifies the docstring format for generated runner functions."""
        logger.info("🧪 Testing docstring for run functions.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn(
            '"""Executes the simulation for the test_machine machine."""', code
        )

    def test_generate_config_path_parent(self) -> None:
        """Ensures `Path(__file__).parent` is used to locate the config file."""
        logger.info("🧪 Testing config path using parent.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("Path(__file__).parent", code)

    def test_generate_utf8_encoding(self) -> None:
        """Ensures config files are opened with 'utf-8' encoding."""
        logger.info("🧪 Testing utf8 encoding.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("encoding='utf-8'", code)

    def test_generate_no_sleep_time_sleep_false(self) -> None:
        """Confirms no `time.sleep` call is generated if `sleep` is disabled."""
        logger.info("🧪 Testing no sleep time if sleep false.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            False,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertNotIn("time.sleep", code)

    def test_generate_custom_sleep_time(self) -> None:
        """Verifies that a custom sleep time is correctly used."""
        logger.info("🧪 Testing custom sleep time.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            5,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("time.sleep(5)", code)

    def test_generate_function_style_runner_import(self) -> None:
        """Verifies the correct import statement for function-style logic."""
        logger.info("🧪 Testing function style runner import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "function",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("import test_machine_logic", code)

    def test_generate_multiple_no_loader(self) -> None:
        """Confirms correct code generation for multiple machines without the loader."""
        logger.info("🧪 Testing multiple no loader.")
        machine_names = ["m1", "m2"]
        code = generate_runner_code(
            machine_names,
            False,
            "class",
            False,
            True,
            2,
            True,
            2,
            SAMPLE_CONFIG_MULTIPLE,
            ["f1.json", "f2.json"],
        )
        self.assertIn("machine_logic = MachineLogic", code)

    def test_generate_combined_file_runner_part(self) -> None:
        """A placeholder to acknowledge testing combined files is handled in main CLI tests."""
        logger.info("🧪 Testing combined file runner part.")
        # This is implicitly tested via the main CLI tests which handle file writing.
        pass

    def test_generate_pathlib_import(self) -> None:
        """Ensures `pathlib.Path` is imported."""
        logger.info("🧪 Testing pathlib import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("from pathlib import Path", code)

    def test_generate_logging_inspector_import(self) -> None:
        """Ensures `LoggingInspector` is imported."""
        logger.info("🧪 Testing LoggingInspector import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("from xstate_statemachine import LoggingInspector", code)

    def test_generate_create_machine_import(self) -> None:
        """Ensures `create_machine` is imported."""
        logger.info("🧪 Testing create_machine import.")
        code = generate_runner_code(
            self.machine_names,
            False,
            "class",
            True,
            True,
            2,
            True,
            2,
            self.configs,
            self.json_filenames,
        )
        self.assertIn("from xstate_statemachine import create_machine", code)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestNormalizeBool
# -----------------------------------------------------------------------------
class TestNormalizeBool(unittest.TestCase):
    """Verifies the `normalize_bool` utility function."""

    def test_normalize_true_values(self) -> None:
        """Ensures various 'true' strings are correctly normalized to `True`."""
        logger.info("🧪 Testing true values normalization.")
        self.assertTrue(normalize_bool("true"))
        self.assertTrue(normalize_bool("YES"))
        self.assertTrue(normalize_bool("y"))
        self.assertTrue(normalize_bool("1"))

    def test_normalize_false_values(self) -> None:
        """Ensures various 'false' strings are correctly normalized to `False`."""
        logger.info("🧪 Testing false values normalization.")
        self.assertFalse(normalize_bool("false"))
        self.assertFalse(normalize_bool("NO"))
        self.assertFalse(normalize_bool("n"))
        self.assertFalse(normalize_bool("0"))

    def test_normalize_case_insensitive(self) -> None:
        """Confirms that normalization is case-insensitive."""
        logger.info("🧪 Testing case insensitive normalization.")
        self.assertTrue(normalize_bool("TrUe"))
        self.assertFalse(normalize_bool("FaLsE"))

    def test_normalize_invalid_value(self) -> None:
        """Verifies that an unrecognized string raises a `ValueError`."""
        logger.info("🧪 Testing invalid value raises error.")
        with self.assertRaises(ValueError):
            normalize_bool("invalid")

    def test_normalize_empty_string(self) -> None:
        """Verifies that an empty string raises a `ValueError`."""
        logger.info("🧪 Testing empty string raises error.")
        with self.assertRaises(ValueError):
            normalize_bool("")

    def test_normalize_number_string(self) -> None:
        """Checks normalization of numeric strings beyond '0' and '1'."""
        logger.info("🧪 Testing number string.")
        self.assertTrue(normalize_bool("1"))
        self.assertFalse(normalize_bool("0"))
        with self.assertRaises(ValueError):
            normalize_bool("2")

    def test_normalize_yes_no_variations(self) -> None:
        """Tests single-letter variations of 'yes' and 'no'."""
        logger.info("🧪 Testing yes no variations.")
        self.assertTrue(normalize_bool("yes"))
        self.assertFalse(normalize_bool("no"))
        self.assertTrue(normalize_bool("Y"))
        self.assertFalse(normalize_bool("N"))


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestMainCLI
# -----------------------------------------------------------------------------
class TestMainCLI(unittest.TestCase):
    """Provides integration tests for the `main` CLI entry point."""

    def setUp(self) -> None:
        """Set up a temporary directory for file output tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

    def tearDown(self) -> None:
        """Clean up the temporary directory and restore the CWD."""
        os.chdir(self.original_cwd)
        self.temp_dir.cleanup()

    @patch("sys.argv", new_callable=list)
    def test_main_no_json_error(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits with an error if no JSON file is provided."""
        logger.info("🧪 Testing no json error.")
        mock_argv[:] = ["cli.py", "generate-template"]
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            main()
        self.assertIn(
            "At least one JSON file is required.", mock_err.getvalue()
        )

    @patch("sys.argv", new_callable=list)
    def test_main_json_not_found(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits if a specified JSON file does not exist."""
        logger.info("🧪 Testing json not found.")
        mock_argv[:] = ["cli.py", "generate-template", "nonexistent.json"]
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            main()
        self.assertIn("JSON file not found", mock_err.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_generate_single(self, mock_argv: List[str]) -> None:
        """Verifies that the correct files are generated for a single JSON input."""
        logger.info("🧪 Testing generate single.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = ["cli.py", "generate-template", str(json_path)]
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("simple_logic.py" in call for call in calls))
        self.assertTrue(any("simple_runner.py" in call for call in calls))

    @patch("sys.argv", new_callable=list)
    def test_main_generate_multiple(self, mock_argv: List[str]) -> None:
        """Verifies correct combined filenames for multiple JSON inputs."""
        logger.info("🧪 Testing generate multiple.")
        json1 = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        json2 = create_temp_json(SAMPLE_CONFIG_NESTED)
        mock_argv[:] = ["cli.py", "generate-template", str(json1), str(json2)]
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("simple_nested_logic.py" in call for call in calls)
        )
        self.assertTrue(
            any("simple_nested_runner.py" in call for call in calls)
        )

    @patch("sys.argv", new_callable=list)
    def test_main_force_overwrite(self, mock_argv: List[str]) -> None:
        """Ensures that the `--force` flag correctly overwrites existing files."""
        logger.info("🧪 Testing force overwrite.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        logic_path = Path.cwd() / "simple_logic.py"
        logic_path.write_text("existing")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--force",
        ]
        main()
        self.assertNotEqual(logic_path.read_text(encoding="utf-8"), "existing")

    @patch("sys.argv", new_callable=list)
    def test_main_custom_output_dir(self, mock_argv: List[str]) -> None:
        """Verifies that files are created in the specified `--output` directory."""
        logger.info("🧪 Testing custom output dir.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        out_dir = Path(self.temp_dir.name) / "out"
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--output",
            str(out_dir),
        ]
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("simple_logic.py" in call for call in calls))
        self.assertTrue(out_dir.joinpath("simple_logic.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_bool_value(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits when an invalid boolean-like value is provided."""
        logger.info("🧪 Testing invalid bool value.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--log",
            "invalid",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_version(self, mock_argv: List[str]) -> None:
        """Verifies the `--version` argument prints the package version and exits."""
        logger.info("🧪 Testing version arg.")
        mock_argv[:] = ["cli.py", "--version"]
        from src.xstate_statemachine.cli import package_version

        with patch(
            "sys.stdout", new=StringIO()
        ) as mock_out, self.assertRaises(SystemExit):
            main()
        self.assertIn(package_version, mock_out.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_help(self, mock_argv: List[str]) -> None:
        """Verifies the help message is displayed with `-h` or `--help`."""
        logger.info("🧪 Testing help.")
        mock_argv[:] = ["cli.py", "generate-template", "-h"]
        with patch(
            "sys.stdout", new=StringIO()
        ) as mock_out, self.assertRaises(SystemExit):
            main()
        self.assertIn("usage:", mock_out.getvalue())

    @patch("sys.argv", new_callable=list)
    def test_main_additional_json(self, mock_argv: List[str]) -> None:
        """Ensures the `--json` argument can be used to add config files."""
        logger.info("🧪 Testing --json arg.")
        json1 = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        json2 = create_temp_json(SAMPLE_CONFIG_NESTED)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json",
            str(json1),
            "--json",
            str(json2),
        ]
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("simple_nested_logic.py" in call for call in calls)
        )

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_style(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits for an invalid `--style` choice."""
        logger.info("🧪 Testing invalid style.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--style",
            "invalid",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_invalid_file_count(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits for an invalid `--file-count` choice."""
        logger.info("🧪 Testing invalid file count.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--file-count",
            "3",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_sleep_time_non_int(self, mock_argv: List[str]) -> None:
        """Ensures the CLI exits if `--sleep-time` is not an integer."""
        logger.info("🧪 Testing non int sleep time.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--sleep-time",
            "abc",
        ]
        with self.assertRaises(SystemExit):
            main()

    @patch("sys.argv", new_callable=list)
    def test_main_no_subcommand(self, mock_argv: List[str]) -> None:
        """Ensures the CLI shows an error if no subcommand is provided."""
        logger.info("🧪 Testing no subcommand.")
        mock_argv[:] = ["cli.py"]
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            main()
        self.assertIn(
            "the following arguments are required: subcommand",
            mock_err.getvalue(),
        )

    @patch("sys.argv", new_callable=list)
    def test_main_combined_file(self, mock_argv: List[str]) -> None:
        """Verifies correct filename for a single combined file output."""
        logger.info("🧪 Testing combined file.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--file-count",
            "1",
        ]
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(any("simple.py" in call for call in calls))
        self.assertTrue(Path.cwd().joinpath("simple.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_output_dir_not_exist_create(
        self, mock_argv: List[str]
    ) -> None:
        """Ensures that a non-existent output directory is created."""
        logger.info("🧪 Testing output dir create.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        out_dir = Path(self.temp_dir.name) / "new_dir"
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--output",
            str(out_dir),
        ]
        main()
        self.assertTrue(out_dir.exists())

    @patch("sys.argv", new_callable=list)
    def test_main_force_no_overwrite_if_not_exist(
        self, mock_argv: List[str]
    ) -> None:
        """Confirms `--force` runs without error when files don't already exist."""
        logger.info("🧪 Testing force no effect if not exist.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),
            "--force",
        ]
        main()
        # Test passes if no error is raised and files are created.
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_no_force_no_overwrite(self, mock_argv: List[str]) -> None:
        """Ensures a warning is printed and execution stops if files exist without `--force`."""
        logger.info("🧪 Testing no force no overwrite.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = ["cli.py", "generate-template", str(json_path)]

        # First run creates the files.
        main()
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())

        # Second run should print a warning and exit.
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "Files exist, use --force to overwrite." in call
                for call in calls
            )
        )
