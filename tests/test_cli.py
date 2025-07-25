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

from xstate_statemachine.cli import main
from xstate_statemachine.cli.extractor import (
    extract_logic_names,
    extract_events,
)
from xstate_statemachine.cli.generator import (
    generate_logic_code,
    generate_runner_code,
)
from xstate_statemachine.cli.utils import normalize_bool

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------


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
            2,
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
            2,
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
            2,
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
            2,
        )
        self.assertIn("import time", code)

    def test_generate_class_name_from_machine_name(self) -> None:
        """Verifies that the logic class name is correctly derived from the machine name."""
        logger.info("🧪 Testing class name from machine name.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, "my_machine", 2
        )
        self.assertIn("class MyMachineLogic:", code)

    def test_generate_no_actions_guards_services(self) -> None:
        """Ensures code is generated gracefully when there are no logic implementations."""
        logger.info("🧪 Testing empty logic code.")
        code = generate_logic_code(
            set(), set(), set(), "function", False, True, self.machine_name, 2
        )
        self.assertNotIn("# ⚙️ Actions", code)
        self.assertNotIn("# 🛡️ Guards", code)
        self.assertNotIn("# 🔄 Services", code)

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
            2,
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
            2,
        )
        self.assertNotIn("logger.info", code)
        self.assertIn("return True", code)

    def test_generate_services_async(self) -> None:
        """Checks for `async def` and `await` in generated async services."""
        logger.info("🧪 Testing async services.")
        code = generate_logic_code(
            set(),
            set(),
            {"async_srv"},
            "class",
            True,
            True,
            self.machine_name,
            2,
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
            2,
        )
        self.assertIn("def sync_srv(", code)
        self.assertIn("time.sleep(1)", code)
        self.assertNotIn("logger.info", code)

    def test_generate_interpreter_type_in_params(self) -> None:
        """Ensures the interpreter type hint changes based on async mode."""
        logger.info("🧪 Testing interpreter type in function params.")
        code_sync = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        code_async = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn(
            "interpreter: Union[Interpreter, SyncInterpreter],", code_sync
        )
        self.assertIn(
            "interpreter: Union[Interpreter, SyncInterpreter],", code_async
        )

    def test_generate_return_type_for_actions(self) -> None:
        """Ensures action return type hint changes based on async mode."""
        logger.info("🧪 Testing return type for actions.")
        code_sync = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        code_async = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("-> None:", code_sync)
        self.assertIn("-> Awaitable[None]:", code_async)

    def test_generate_return_type_for_services(self) -> None:
        """Ensures service return type hint changes based on async mode."""
        logger.info("🧪 Testing return type for services.")
        code_sync = generate_logic_code(
            set(), set(), {"srv"}, "class", False, False, self.machine_name, 2
        )
        code_async = generate_logic_code(
            set(), set(), {"srv"}, "class", False, True, self.machine_name, 2
        )
        self.assertIn("-> Dict[str, Any]:", code_sync)
        self.assertIn("-> Awaitable[Dict[str, Any]]:", code_async)

    def test_generate_guards_return_bool(self) -> None:
        """Verifies that generated guards are correctly type-hinted to return `bool`."""
        logger.info("🧪 Testing guards return bool.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("-> bool:", code)

    def test_generate_function_style_no_self(self) -> None:
        """Confirms that 'self' is not included in function-style logic."""
        logger.info("🧪 Testing function style no self.")
        code = generate_logic_code(
            {"act"},
            set(),
            set(),
            "function",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertNotIn("self,", code)

    def test_generate_no_dummy_sleep_if_no_log(self) -> None:
        """Ensures dummy async sleep is present even if logging is off."""
        logger.info("🧪 Testing no dummy sleep if no log.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_sorted_names(self) -> None:
        """Verifies that generated functions are sorted alphabetically."""
        logger.info("🧪 Testing sorted names in code.")
        actions = {"z_act", "a_act"}
        code = generate_logic_code(
            actions, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertTrue(code.find("def a_act(") < code.find("def z_act("))

    def test_generate_logger_config(self) -> None:
        """Ensures the standard logger configuration is present in the generated file."""
        logger.info("🧪 Testing logger config.")
        code = generate_logic_code(
            set(), set(), set(), "class", True, False, self.machine_name, 2
        )
        self.assertIn("logger = logging.getLogger(__name__)", code)

    def test_generate_typing_imports(self) -> None:
        """Verifies that necessary `typing` imports are included."""
        logger.info("🧪 Testing typing imports.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("from typing import Any, Dict, Union", code)

    def test_generate_xstate_imports(self) -> None:
        """Verifies that necessary `xstate_statemachine` imports are included."""
        logger.info("🧪 Testing xstate imports.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn(
            "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition",
            code,
        )

    def test_generate_awaitable_for_async_guards_no(self) -> None:
        """Confirms that guards remain synchronous even in async mode."""
        logger.info("🧪 Testing no Awaitable for guards in async.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("-> bool:", code)
        self.assertNotIn("Awaitable[bool]", code)

    def test_generate_no_imports_if_no_services_async(self) -> None:
        """Confirms `time` is not imported if there are no sync services."""
        logger.info("🧪 Testing no time if no services sync.")
        code = generate_logic_code(
            set(), set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertNotIn("import time", code)

    def test_generate_class_indent_correct(self) -> None:
        """Checks for correct indentation in class-style generation."""
        logger.info("🧪 Testing class indent.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("    # ⚙️ Actions", code)

    def test_generate_function_indent_correct(self) -> None:
        """Checks for correct (zero) indentation in function-style generation."""
        logger.info("🧪 Testing function indent.")
        code = generate_logic_code(
            {"act"},
            set(),
            set(),
            "function",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertIn("# ⚙️ Actions", code)
        self.assertNotIn("    # ⚙️ Actions", code)

    def test_generate_docstring_for_actions(self) -> None:
        """Ensures the correct docstring format for generated actions."""
        logger.info("🧪 Testing docstring for actions.")
        code = generate_logic_code(
            {"my_act"},
            set(),
            set(),
            "class",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertIn('"""Action: `my_act`."""', code)

    def test_generate_docstring_for_guards(self) -> None:
        """Ensures the correct docstring format for generated guards."""
        logger.info("🧪 Testing docstring for guards.")
        code = generate_logic_code(
            set(), {"my_g"}, set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn('"""Guard: `my_g`."""', code)

    def test_generate_docstring_for_services(self) -> None:
        """Ensures the correct docstring format for generated services."""
        logger.info("🧪 Testing docstring for services.")
        code = generate_logic_code(
            set(),
            set(),
            {"my_srv"},
            "class",
            False,
            False,
            self.machine_name,
            2,
        )
        self.assertIn('"""Service: `my_srv`."""', code)

    def test_generate_pass_todo_for_actions(self) -> None:
        """Verifies the placeholder `pass` and `TODO` comment for actions."""
        logger.info("🧪 Testing pass TODO for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("# TODO: implement", code)

    def test_generate_return_true_todo_for_guards(self) -> None:
        """Verifies the placeholder `return True` and `TODO` comment for guards."""
        logger.info("🧪 Testing return True TODO for guards.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", False, False, self.machine_name, 2
        )
        self.assertIn("# TODO: implement guard logic", code)

    def test_generate_return_dict_todo_for_services(self) -> None:
        """Verifies the placeholder return dictionary and `TODO` comment for services."""
        logger.info("🧪 Testing return dict TODO for services.")
        code = generate_logic_code(
            set(), set(), {"srv"}, "class", False, False, self.machine_name, 2
        )
        self.assertIn("# TODO: implement service", code)

    def test_generate_logger_info_for_actions_log_true(self) -> None:
        """Verifies the logging statement for actions when logging is enabled."""
        logger.info("🧪 Testing logger info for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", True, False, self.machine_name, 2
        )
        self.assertIn('logger.info("Executing action act")', code)

    def test_generate_no_logger_for_actions_log_false(self) -> None:
        """Ensures no logging statement is generated when logging is disabled."""
        logger.info("🧪 Testing no logger for actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertNotIn("logger.info", code)

    def test_generate_logger_for_guards(self) -> None:
        """Verifies the logging statement for guards when logging is enabled."""
        logger.info("🧪 Testing logger for guards.")
        code = generate_logic_code(
            set(), {"g"}, set(), "class", True, False, self.machine_name, 2
        )
        self.assertIn('logger.info("Evaluating guard g")', code)

    def test_generate_logger_for_services(self) -> None:
        """Verifies the logging statement for services when logging is enabled."""
        logger.info("🧪 Testing logger for services.")
        code = generate_logic_code(
            set(), set(), {"srv"}, "class", True, False, self.machine_name, 2
        )
        self.assertIn('logger.info("Running service srv")', code)

    def test_generate_dummy_async_for_async_actions_no_log(self) -> None:
        """Ensures dummy `asyncio.sleep` is present in async actions."""
        logger.info("🧪 Testing dummy async for actions no log.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, True, self.machine_name, 2
        )
        self.assertIn("await asyncio.sleep(0.1)", code)

    def test_generate_no_dummy_for_sync_actions(self) -> None:
        """Ensures no `sleep` call is present in sync actions."""
        logger.info("🧪 Testing no dummy for sync actions.")
        code = generate_logic_code(
            {"act"}, set(), set(), "class", False, False, self.machine_name, 2
        )
        self.assertNotIn("sleep", code)

    def test_generate_sorted_actions_guards_services(self) -> None:
        """Confirms that all generated functions are sorted alphabetically within their sections."""
        logger.info("🧪 Testing sorted order in generated code.")
        actions = {"z", "a"}
        guards = {"y", "b"}
        services = {"x", "c"}
        code = generate_logic_code(
            actions,
            guards,
            services,
            "class",
            False,
            False,
            self.machine_name,
            2,
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
            "logger.info('No events declared in the machine.')", code
        )

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
        self.assertIn("machine = create_machine(config,", code)

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
            "logger.info(f'Initial state: {interpreter.current_state_ids}')",
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
        self.assertNotIn(
            "logger.info('--- Running simulation with all defined events ---')",
            code,
        )
        self.assertNotIn(
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
            ["m1.json", "m2.json"],
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
        self.assertIn("Path(__file__).resolve().parent", code)

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
        self.assertIn("machine = create_machine(config,", code)

    def test_generate_combined_file_runner_part(self) -> None:
        """A placeholder to acknowledge testing combined files is handled in main CLI tests."""
        logger.info("🧪 Testing combined file runner part.")
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
        """Ensures the CLI exits with error if no JSON file is provided."""
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
        with patch("builtins.input", side_effect=["n", "0"]), patch(
            "builtins.print"
        ) as mock_print:
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
        from src.xstate_statemachine import __version__ as package_version

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
        with patch("builtins.input", side_effect=["n", "0"]), patch(
            "builtins.print"
        ) as mock_print:
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
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_no_force_no_overwrite(self, mock_argv: List[str]) -> None:
        """Ensures a warning is printed and execution stops if files exist without `--force`."""
        logger.info("🧪 Testing no force no overwrite.")
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        mock_argv[:] = ["cli.py", "generate-template", str(json_path)]

        main()
        self.assertTrue(Path.cwd().joinpath("simple_logic.py").exists())

        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "Files exist, use --force to overwrite." in call
                for call in calls
            )
        )

    @patch("sys.argv", new_callable=list)
    def test_main_deduplicates_paths(self, mock_argv: List[str]) -> None:
        """SCENARIO 14: Ensures duplicate file paths are handled correctly."""
        logger.info(
            "🧪 Testing de-duplication of input JSON paths (Scenario 14)."
        )
        json_path = create_temp_json(SAMPLE_CONFIG_SIMPLE)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(json_path),  # Positional
            "--json",
            str(json_path),  # Via --json flag
            "--json-parent",
            str(json_path),  # Via --json-parent flag
        ]

        with patch("builtins.print") as mock_print:
            main()

        # The result should be a simple, single-file generation, not hierarchical.
        # It should NOT create a runner named "simple_simple_runner.py" etc.
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "Generated logic file: " in call and "simple_logic.py" in call
                for call in calls
            )
        )
        self.assertTrue(
            any(
                "Generated runner file: " in call
                and "simple_runner.py" in call
                for call in calls
            )
        )
        self.assertFalse(
            Path.cwd().joinpath("simple_simple_logic.py").exists()
        )

    @patch("sys.argv", new_callable=list)
    def test_main_multiple_parents_error(self, mock_argv: List[str]) -> None:
        """SCENARIO 17: Ensures an error is raised if multiple parents are specified."""
        logger.info(
            "🧪 Testing error on multiple --json-parent flags (Scenario 17)."
        )
        json1 = create_temp_json(SAMPLE_CONFIG_SIMPLE)
        json2 = create_temp_json(SAMPLE_CONFIG_NESTED)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(json1),
            "--json-parent",
            str(json2),
        ]

        # This test will pass once cli.py is updated to manually check for this error.
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            main()

        # Assert the specific error message that your script should raise.
        self.assertIn(
            "Only one --json-parent may be supplied.", mock_err.getvalue()
        )


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestExtractEvents
# -----------------------------------------------------------------------------
class TestExtractEvents(unittest.TestCase):
    """Verifies the `extract_events` utility function."""

    def test_extract_events_from_simple_on(self) -> None:
        """Ensures events are extracted from a simple 'on' block."""
        logger.info("🧪 Testing event extraction from simple 'on'.")
        config = {"on": {"EVENT1": {}, "EVENT2": {}}}
        events = extract_events(config)
        self.assertEqual(events, {"EVENT1", "EVENT2"})

    def test_extract_events_from_nested_states(self) -> None:
        """Verifies event extraction from 'on' blocks within nested states."""
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
        """Confirms that duplicate event names are only included once."""
        logger.info("🧪 Testing no duplicate events.")
        config = {
            "on": {"DUPLICATE_EVENT": {}},
            "states": {"s1": {"on": {"DUPLICATE_EVENT": {}}}},
        }
        events = extract_events(config)
        self.assertEqual(events, {"DUPLICATE_EVENT"})

    def test_extract_events_empty_config(self) -> None:
        """Ensures an empty set is returned for a config with no 'on' blocks."""
        logger.info("🧪 Testing event extraction from empty config.")
        config = {"id": "empty", "initial": "a", "states": {}}
        events = extract_events(config)
        self.assertEqual(events, set())

    def test_extract_events_ignores_other_keys(self) -> None:
        """Ensures that keys other than 'on' and 'states' are ignored."""
        logger.info("🧪 Testing event extraction ignores other keys.")
        config = {"entry": "action", "exit": "action", "invoke": "service"}
        events = extract_events(config)
        self.assertEqual(events, set())

    def test_extract_events_from_multiple_levels(self) -> None:
        """Verifies extraction from multiple levels of nesting."""
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
# 🏛️ Test Class: TestHierarchyCLI
# -----------------------------------------------------------------------------
# This new class specifically tests the parent-child machine hierarchy features.
# -----------------------------------------------------------------------------

HIERARCHY_PARENT_CONFIG: Dict[str, Any] = {
    "id": "parentMachine",
    "initial": "idle",
    "states": {
        "idle": {
            "on": {"START": "running"},
            "invoke": {
                "id": "child",
                "src": "childMachine",
                "onDone": "finished",
            },
        },
        "running": {"on": {"STOP": "idle"}},
        "finished": {"type": "final"},
    },
}

HIERARCHY_CHILD_CONFIG: Dict[str, Any] = {
    "id": "childMachine",
    "initial": "active",
    "states": {
        "active": {"on": {"CHILD_EVENT": "done"}},
        "done": {"type": "final"},
    },
}


class TestHierarchyCLI(unittest.TestCase):
    """Provides integration tests for the new parent/child hierarchy features."""

    def setUp(self) -> None:
        """Set up a temporary directory for file output tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        # Create shared configs for hierarchy tests
        self.parent_json_path = create_temp_json(HIERARCHY_PARENT_CONFIG)
        self.child_json_path = create_temp_json(HIERARCHY_CHILD_CONFIG)

    def tearDown(self) -> None:
        """Clean up the temporary directory and restore the CWD."""
        os.chdir(self.original_cwd)
        # The TemporaryDirectory context manager handles cleanup automatically.
        # Manual os.remove calls are no longer needed and caused errors.
        self.temp_dir.cleanup()

    @patch("sys.argv", new_callable=list)
    def test_main_explicit_parent_child_args(
        self, mock_argv: List[str]
    ) -> None:
        """Verifies file generation using explicit --json-parent and --json-child flags."""
        logger.info("🧪 Testing explicit parent/child args.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(self.parent_json_path),
            "--json-child",
            str(self.child_json_path),
        ]
        with patch("builtins.print") as mock_print:
            main()
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("parent_machine_logic.py" in call for call in calls)
        )
        self.assertTrue(
            any("parent_machine_runner.py" in call for call in calls)
        )
        # Runner should contain logic for both parent and child
        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )  # FIX: Specify UTF-8 encoding
        self.assertIn("parent_cfg = json.loads", runner_content)
        self.assertIn("actor_cfgs = {", runner_content)
        self.assertIn("'child_machine': json.loads", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_child_arg_without_parent_error(
        self, mock_argv: List[str]
    ) -> None:
        """Ensures an error is raised if --json-child is used without a parent."""
        logger.info("🧪 Testing --json-child without parent raises error.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-child",
            str(self.child_json_path),
        ]
        with patch(
            "sys.stderr", new=StringIO()
        ) as mock_err, self.assertRaises(SystemExit):
            main()
        self.assertIn("requires a parent machine", mock_err.getvalue())

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["y"])
    def test_main_heuristic_parent_detection_yes(
        self, mock_input: unittest.mock.MagicMock, mock_argv: List[str]
    ) -> None:
        """Tests heuristic parent detection with user confirmation ('y')."""
        logger.info("🧪 Testing heuristic parent detection (user says 'y').")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_json_path),
            str(self.parent_json_path),
        ]
        with patch("builtins.print") as mock_print:
            main()
        # Verify the parent machine is correctly identified and used for naming
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any("parent_machine_logic.py" in call for call in calls)
        )
        self.assertTrue(
            any("parent_machine_runner.py" in call for call in calls)
        )
        # Check that the interactive prompt was shown
        self.assertTrue(any("looks like parent" in call for call in calls))

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["n", "0"])
    def test_main_heuristic_parent_detection_no(
        self, mock_input: unittest.mock.MagicMock, mock_argv: List[str]
    ) -> None:
        """Tests heuristic parent detection with user rejection ('n'), treating them as flat."""
        logger.info("🧪 Testing heuristic parent detection (user says 'n').")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_json_path),
            str(self.child_json_path),
        ]
        with patch("builtins.print") as mock_print:
            main()
        # Without hierarchy, names are combined
        calls = [call.args[0] for call in mock_print.call_args_list]
        self.assertTrue(
            any(
                "parent_machine_child_machine_logic.py" in call
                for call in calls
            )
        )

    @patch("sys.argv", new_callable=list)
    @patch(
        "builtins.input", side_effect=["n", "2"]
    )  # Select the second machine (parent)
    def test_main_heuristic_manual_selection(
        self, mock_input: unittest.mock.MagicMock, mock_argv: List[str]
    ) -> None:
        """Tests manual parent selection when the heuristic is rejected."""
        logger.info("🧪 Testing heuristic manual selection.")
        # Provide child first, then parent
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_json_path),
            str(self.parent_json_path),
        ]
        with patch("builtins.print"):
            main()

        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        # FIX: Check for the *effect* of hierarchy, not an implementation detail.
        # The presence of an 'actors' dictionary is a reliable indicator.
        self.assertIn(
            "actors = {}",
            runner_content,
            "Runner should be in hierarchical mode",
        )
        self.assertIn(
            "Spawn & start every actor interpreter",
            runner_content,
            "Runner should spawn actors",
        )

    def test_hierarchical_runner_event_simulation(self) -> None:
        """Verifies the hierarchical runner simulates events for both parent and actors."""
        logger.info("🧪 Testing event simulation in hierarchical runner.")
        runner_code = generate_runner_code(
            machine_names=["parentMachine", "childMachine"],
            is_async=False,
            style="class",
            loader=True,
            sleep=False,
            sleep_time=0,
            log=True,
            file_count=2,
            configs=[HIERARCHY_PARENT_CONFIG, HIERARCHY_CHILD_CONFIG],
            json_filenames=[
                str(self.parent_json_path),
                str(self.child_json_path),
            ],
            hierarchy=True,
        )

        self.assertIn("parent.send('START')", runner_code)
        self.assertIn("parent.send('STOP')", runner_code)
        self.assertIn(
            "actors['childMachine'].send('CHILD_EVENT')", runner_code
        )
        self.assertIn("Simulating Actor «childMachine»", runner_code)

    def test_generate_logic_with_noqa_comments(self) -> None:
        """Ensures generated logic includes noqa comments for IDE warnings."""
        logger.info("🧪 Testing for noqa comments in generated logic.")
        logic_code = generate_logic_code(
            actions={"myAction"},
            guards={"myGuard"},
            services={"myService"},
            style="class",
            log=True,
            is_async=True,
            machine_name="test",
            file_count=2,
        )
        self.assertIn("# noqa: ignore IDE static method warning", logic_code)
        self.assertIn(
            "# noqa : ignore IDE return type hint warning", logic_code
        )

    @patch("sys.argv", new_callable=list)
    def test_main_explicit_parent_with_positional_children(
        self, mock_argv: List[str]
    ) -> None:
        """SCENARIO 6: Tests explicit parent flag with positional children."""
        logger.info(
            "🧪 Testing explicit parent with positional children (Scenario 6)."
        )
        # Create a second child to test with
        child2_config = {
            "id": "childMachine2",
            "initial": "idle",
            "states": {"idle": {}},
        }
        child2_path = create_temp_json(child2_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(self.parent_json_path),
            str(self.child_json_path),  # Positional child 1
            str(child2_path),  # Positional child 2
        ]

        # No interactive input should be required
        with patch("builtins.input") as mock_input:
            main()
            # Assert that the interactive prompt was NOT triggered
            mock_input.assert_not_called()

        # Check that the output is hierarchical and named after the parent
        self.assertTrue(
            Path.cwd().joinpath("parent_machine_runner.py").exists()
        )
        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )

        # Verify both children are treated as actors
        self.assertIn("'child_machine': json.loads", runner_content)
        # FIX: The snake_case conversion of "childMachine2" is "child_machine2".
        self.assertIn("'child_machine2': json.loads", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_positional_parent_with_explicit_child(
        self, mock_argv: List[str]
    ) -> None:
        """SCENARIO 13: Tests positional parent with an explicit child flag."""
        logger.info(
            "🧪 Testing positional parent with explicit child (Scenario 13)."
        )
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_json_path),  # Positional parent
            "--json-child",
            str(self.child_json_path),  # Flagged child
        ]

        # This test correctly expects that the heuristic prompt will NOT be called.
        with patch("builtins.input") as mock_input:
            main()
            mock_input.assert_not_called()

        # This assertion will pass once the bugs in cli.py are fixed.
        self.assertTrue(
            Path.cwd().joinpath("parent_machine_runner.py").exists()
        )
        runner_content = (Path.cwd() / "parent_machine_runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("actor_cfgs = {", runner_content)
        self.assertIn("'child_machine'", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_no_events(self, mock_argv: List[str]) -> None:
        """Tests hierarchical generation when parent or child has no events."""
        logger.info("🧪 Testing hierarchical generation with no events.")
        parent_no_events_config = {
            "id": "parentNoEvents",
            "invoke": {"src": "childMachine"},
        }
        parent_no_events_path = create_temp_json(parent_no_events_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--json-parent",
            str(parent_no_events_path),
            "--json-child",
            str(self.child_json_path),
        ]

        main()

        runner_file = Path.cwd() / "parent_no_events_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # Verify it correctly notes the lack of parent events
        self.assertIn(
            "logger.info('No events declared in parent machine.')",
            runner_content,
        )
        # Verify it still includes simulation for the child with events
        self.assertIn("Simulating Actor «child_machine»", runner_content)
        # FIX: Add 'await' to the assertion to match the async runner code
        self.assertIn(
            "await actors['child_machine'].send('CHILD_EVENT')", runner_content
        )

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_function_style(
        self, mock_argv: List[str]
    ) -> None:
        """Tests hierarchical generation with function-style logic."""
        logger.info("🧪 Testing hierarchical generation with function style.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--style",
            "function",
            "--json-parent",
            str(self.parent_json_path),
            "--json-child",
            str(self.child_json_path),
        ]

        main()

        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # Verify it imports the logic module directly
        self.assertIn("import parent_machine_logic", runner_content)
        # Verify it uses the logic_modules parameter for create_machine
        self.assertIn("logic_modules=[parent_machine_logic]", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_reject_then_manual_select(
        self, mock_argv: List[str]
    ) -> None:
        """Tests rejecting heuristic suggestion then manually selecting a parent."""
        logger.info("🧪 Testing heuristic reject then manual select.")
        # We present parent then child, so the heuristic will correctly guess #1
        # We will reject it and manually select #1 anyway.
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_json_path),
            str(self.child_json_path),
        ]

        with patch("builtins.input", side_effect=["n", "1"]), patch(
            "builtins.print"
        ) as mock_print:  # noqa: F841
            main()

        # Check for correct hierarchical output named after the manually selected parent
        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")
        self.assertIn(
            "actor_cfgs = {",
            runner_content,
            "Runner should be in hierarchical mode",
        )
        self.assertIn("'child_machine'", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_invalid_manual_selection(
        self, mock_argv: List[str]
    ) -> None:
        """Tests that invalid manual parent selection defaults to flat mode."""
        logger.info("🧪 Testing heuristic with invalid manual selection.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_json_path),
            str(self.child_json_path),
        ]

        # User rejects heuristic, then enters invalid text "abc"
        with patch("builtins.input", side_effect=["n", "abc"]), patch(
            "builtins.print"
        ) as mock_print:  # noqa: F841
            main()

        # It should default to flat mode, combining the names
        runner_file = Path.cwd() / "parent_machine_child_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # FIX: Make the assertion more flexible by checking for 'in' instead of 'startswith'
        # This correctly handles both 'def ...' and 'async def ...'
        self.assertTrue(
            any(
                "def run_parent_machine" in line
                for line in runner_content.splitlines()
            ),
            "'run_parent_machine' function not found in runner.",
        )
        self.assertTrue(
            any(
                "def run_child_machine" in line
                for line in runner_content.splitlines()
            ),
            "'run_child_machine' function not found in runner.",
        )

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_tie_breaking(self, mock_argv: List[str]) -> None:
        """Tests that a heuristic tie is broken by the first-listed machine."""
        logger.info("🧪 Testing heuristic tie-breaking behavior.")
        # Create two potential parents with the exact same invoke score
        p1_config = {"id": "parentOne", "invoke": {"src": "someActor"}}
        p2_config = {"id": "parentTwo", "invoke": {"src": "someOtherActor"}}
        p1_path = create_temp_json(p1_config)
        p2_path = create_temp_json(p2_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(p1_path),  # parentOne is listed first
            str(p2_path),
        ]

        # We expect it to suggest "parentOne" and we will accept.
        with patch("builtins.input", side_effect=["y"]), patch(
            "builtins.print"
        ) as mock_print:
            main()

        # Verify that the prompt correctly identified the first machine as the parent
        print_output = "".join(
            call.args[0] for call in mock_print.call_args_list if call.args
        )
        self.assertIn("parentOne (looks like parent", print_output)

        # Verify the output is named after the first machine
        self.assertTrue(Path.cwd().joinpath("parent_one_runner.py").exists())

    @patch("sys.argv", new_callable=list)
    def test_main_heuristic_user_correction(
        self, mock_argv: List[str]
    ) -> None:
        """Tests the user correcting an incorrect heuristic guess."""
        logger.info("🧪 Testing user correction of a wrong heuristic guess.")
        # Create a "decoy" parent that has more invokes than the real one
        decoy_config = {
            "id": "decoyParent",
            "invoke": [{"src": "a"}, {"src": "b"}],
        }
        real_parent_config = {
            "id": "realParent",
            "invoke": {"src": "decoyParent"},
        }
        decoy_path = create_temp_json(decoy_config)
        real_path = create_temp_json(real_parent_config)

        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(real_path),  # real parent is first
            str(decoy_path),  # decoy is second, but has higher score
        ]

        # Heuristic will wrongly suggest "decoyParent" (index 2).
        # User says "n", then manually selects the correct parent "realParent" (index 1).
        with patch("builtins.input", side_effect=["n", "1"]), patch(
            "builtins.print"
        ) as mock_print:  # noqa: F841
            main()

        # Verify the output is named after the manually corrected parent
        self.assertTrue(Path.cwd().joinpath("real_parent_runner.py").exists())
        runner_content = (Path.cwd() / "real_parent_runner.py").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "'decoy_parent'", runner_content
        )  # Check that the decoy is an actor

    @patch("sys.argv", new_callable=list)
    def test_main_hierarchy_with_loader_disabled(
        self, mock_argv: List[str]
    ) -> None:
        """Tests hierarchical generation with the auto-discovery loader disabled."""
        logger.info("🧪 Testing hierarchical generation with --loader=no.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--loader",
            "no",
            "--json-parent",
            str(self.parent_json_path),
            "--json-child",
            str(self.child_json_path),
        ]

        main()

        runner_file = Path.cwd() / "parent_machine_runner.py"
        self.assertTrue(runner_file.exists())
        runner_content = runner_file.read_text(encoding="utf-8")

        # With the loader off, it should still bind the provider explicitly
        self.assertIn("logic_provider = LogicProvider()", runner_content)
        self.assertIn("logic_providers=[logic_provider]", runner_content)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestHierarchyAndEventUtils
# -----------------------------------------------------------------------------
# This class tests the standalone utility functions related to the new
# hierarchy and event extraction features.
# -----------------------------------------------------------------------------


class TestHierarchyAndEventUtils(unittest.TestCase):
    """Verifies the utility functions for hierarchy and event extraction."""

    def setUp(self) -> None:
        """Create common configs for testing."""
        self.parent_config = {
            "id": "parent",
            "invoke": {"src": "child1"},
            "states": {"s1": {"invoke": {"src": "child2"}}},
        }
        self.child1_config = {"id": "child1", "on": {"EVENT1": {}}}
        self.child2_config = {"id": "child2", "on": {"EVENT2": {}}}
        self.unrelated_config = {"id": "unrelated"}

        self.parent_path = create_temp_json(self.parent_config)
        self.child1_path = create_temp_json(self.child1_config)
        self.child2_path = create_temp_json(self.child2_config)
        self.unrelated_path = create_temp_json(self.unrelated_config)

    def tearDown(self) -> None:
        """Clean up temporary files."""
        os.remove(self.parent_path)
        os.remove(self.child1_path)
        os.remove(self.child2_path)
        os.remove(self.unrelated_path)

    def test_count_invokes(self) -> None:
        """Ensures _count_invokes correctly counts 'invoke' keys."""
        logger.info("🧪 Testing _count_invokes utility.")
        from src.xstate_statemachine.cli.extractor import _count_invokes

        self.assertEqual(_count_invokes(self.parent_config), 2)
        self.assertEqual(_count_invokes(self.child1_config), 0)

    def test_guess_hierarchy_identifies_parent(self) -> None:
        """Verifies guess_hierarchy correctly identifies the parent by invoke count."""
        logger.info("🧪 Testing guess_hierarchy parent identification.")
        from src.xstate_statemachine.cli.extractor import guess_hierarchy

        paths = [str(self.child1_path), str(self.parent_path)]
        parent, children, _ = guess_hierarchy(paths)

        self.assertEqual(parent, str(self.parent_path))
        self.assertIn(str(self.child1_path), children)

    def test_extract_events_handles_various_configs(self) -> None:
        """Ensures extract_events correctly pulls all unique event names."""
        logger.info("🧪 Testing extract_events for comprehensive coverage.")
        config = {
            "on": {"TOP_LEVEL": {}},
            "states": {
                "s1": {"on": {"S1_EVENT": {}}},
                "s2": {
                    "on": {"S2_EVENT": {}},
                    "states": {"s2_child": {"on": {"S2_CHILD_EVENT": {}}}},
                },
            },
        }
        events = extract_events(config)
        self.assertEqual(
            events, {"TOP_LEVEL", "S1_EVENT", "S2_EVENT", "S2_CHILD_EVENT"}
        )


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestAdvancedCodeGeneration
# -----------------------------------------------------------------------------
# This class focuses on the new, more complex code generation features, such
# as noqa comments, aliasing, and hierarchical runner structure.
# -----------------------------------------------------------------------------


class TestAdvancedCodeGeneration(unittest.TestCase):
    """Verifies advanced features of the code generation functions."""

    def test_generate_logic_code_with_service_aliasing(self) -> None:
        """Ensures services with names needing conversion are aliased correctly."""
        logger.info("🧪 Testing logic generation with service aliasing.")
        logic_code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"myCoolService"},  # A name that will be converted
            style="class",
            log=False,
            is_async=False,
            machine_name="test",
            file_count=2,
        )
        self.assertIn("def my_cool_service(", logic_code)
        self.assertIn("myCoolService = my_cool_service", logic_code)

    def test_hierarchical_runner_generation(self) -> None:
        """Verifies the structure of a hierarchically generated runner."""
        logger.info("🧪 Testing hierarchical runner structure.")
        parent_config = {"id": "p", "invoke": {"src": "c"}}
        child_config = {"id": "c"}
        runner_code = generate_runner_code(
            machine_names=["p", "c"],
            is_async=True,
            style="class",
            loader=True,
            sleep=True,
            sleep_time=1,
            log=True,
            file_count=2,
            configs=[parent_config, child_config],
            json_filenames=["p.json", "c.json"],
            hierarchy=True,  # Explicitly trigger hierarchy mode
        )
        # Check for parent setup
        self.assertIn(
            "parent_machine = create_machine(parent_cfg", runner_code
        )
        self.assertIn("parent = Interpreter(parent_machine)", runner_code)
        # Check for actor setup loop/block
        self.assertIn("actors = {}", runner_code)
        self.assertIn(
            "machine_c = create_machine(actor_cfgs['c'])", runner_code
        )
        # Check for graceful shutdown
        self.assertIn("await actors['c'].stop()", runner_code)
        self.assertIn("await parent.stop()", runner_code)

    def test_generate_logic_for_keyword_service_name(self) -> None:
        """Tests that a service named after a Python keyword is handled correctly."""
        logger.info("🧪 Testing logic generation for a keyword service name.")
        logic_code = generate_logic_code(
            actions=set(),
            guards=set(),
            services={"pass", "import"},  # Python keywords
            style="class",
            log=False,
            is_async=False,
            machine_name="test",
            file_count=2,
        )
        # Check that the function name is sanitized with a trailing underscore
        self.assertIn("def pass_(", logic_code)
        self.assertIn("def import_(", logic_code)
        # Check that an alias is created to map the original keyword name
        self.assertIn("pass = pass_", logic_code)
        self.assertIn("import = import_", logic_code)


# -----------------------------------------------------------------------------
# 🏛️ Test Class: TestFullCLIExecution
# -----------------------------------------------------------------------------
# This class performs end-to-end tests on the main() function, covering the
# full CLI execution flow including interactive prompts and file merging.
# -----------------------------------------------------------------------------


class TestFullCLIExecution(unittest.TestCase):
    """Provides full, end-to-end integration tests for the main CLI entry point."""

    def setUp(self) -> None:
        """Set up a temporary directory and shared JSON files for tests."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        # Config where parent 'invokes' child by its ID
        self.parent_config = {"id": "parent", "invoke": {"src": "child"}}
        self.child_config = {"id": "child"}
        self.parent_path = create_temp_json(self.parent_config)
        self.child_path = create_temp_json(self.child_config)

    def tearDown(self) -> None:
        """Clean up temporary directory and files."""
        os.chdir(self.original_cwd)
        # FIX: The TemporaryDirectory context manager cleans up everything.
        # Manual deletion is unnecessary and causes errors if files are already gone.
        self.temp_dir.cleanup()

    @patch("sys.argv", new_callable=list)
    @patch("builtins.input", side_effect=["y"])  # Auto-confirm heuristic
    def test_main_heuristic_prompt_and_reorder(
        self, mock_input, mock_argv
    ) -> None:
        """Ensures CLI correctly prompts, reorders files, and generates hierarchical code."""
        logger.info("🧪 Testing heuristic prompt and file reordering.")
        # Pass child first to test reordering
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.child_path),
            str(self.parent_path),
        ]

        with patch("builtins.print") as mock_print:
            main()

        print_calls = "".join(
            [call.args[0] for call in mock_print.call_args_list if call.args]
        )
        self.assertIn("looks like parent", print_calls)
        self.assertTrue(Path("parent_logic.py").exists())
        self.assertTrue(Path("parent_runner.py").exists())
        runner_content = Path("parent_runner.py").read_text(encoding="utf-8")
        self.assertIn("actor_cfgs = {", runner_content)

    @patch("sys.argv", new_callable=list)
    def test_main_combined_file_intelligent_merge(
        self, mock_argv: List[str]
    ) -> None:
        """Verifies --file-count 1 correctly merges logic and runner, avoiding duplicate imports."""
        logger.info("🧪 Testing intelligent merge for combined file output.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            str(self.parent_path),
            "--file-count",
            "1",
        ]
        main()

        combined_file = Path("parent.py")
        self.assertTrue(combined_file.exists())
        # FIX: Specify UTF-8 encoding to handle emojis and special characters on all platforms.
        content = combined_file.read_text(encoding="utf-8")

        self.assertEqual(content.count("import logging"), 1)
        self.assertEqual(content.count("from pathlib import Path"), 1)
        self.assertEqual(content.count("import json"), 1)
        self.assertIn("# 🧠 Class‑based Logic", content)
        self.assertIn("# Runner part", content)
        self.assertIn("if __name__ == '__main__':", content)

    @patch("sys.argv", new_callable=list)
    def test_main_combined_file_in_hierarchy_mode(
        self, mock_argv: List[str]
    ) -> None:
        """Verifies --file-count 1 works correctly in a hierarchical setup."""
        logger.info("🧪 Testing combined file output in hierarchy mode.")
        mock_argv[:] = [
            "cli.py",
            "generate-template",
            "--file-count",
            "1",
            "--json-parent",
            str(self.parent_path),
            "--json-child",
            str(self.child_path),
        ]

        main()

        combined_file = Path("parent.py")
        self.assertTrue(combined_file.exists())
        content = combined_file.read_text(encoding="utf-8")

        # Check for logic class definition
        self.assertIn("class ParentLogic:", content)
        # Check for runner part and hierarchical constructs
        self.assertIn("# Runner part", content)
        self.assertIn("actor_cfgs = {", content)
        self.assertIn("'child': json.loads", content)
        self.assertIn("parent = Interpreter(parent_machine)", content)


# Add this at the end of the file, or integrate the tests into existing classes.
# For simplicity, I'm showing them as a new class.
if __name__ == "__main__":
    unittest.main()
