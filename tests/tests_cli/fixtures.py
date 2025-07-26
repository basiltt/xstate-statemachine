# tests/tests_cli/fixtures.py
# -----------------------------------------------------------------------------
# 📦 Test Fixtures & Helpers
# -----------------------------------------------------------------------------
# This module centralizes all shared data fixtures and helper functions used
# across the CLI test suite. By adhering to the DRY (Don't Repeat Yourself)
# principle, it ensures consistency and makes tests easier to read and
# maintain.
#
# It provides:
#   -   Sample state machine configurations (e.g., simple, nested, hierarchical).
#   -   A helper function to create temporary JSON files for CLI input.
# -----------------------------------------------------------------------------
"""
Provides shared test data and helper functions for the CLI test suite.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Test Helper Functions
# -----------------------------------------------------------------------------


def create_temp_json(config: Dict[str, Any]) -> Path:
    """
    Creates a temporary JSON file with a given configuration.

    This helper is crucial for CLI tests that require a file path as an input
    argument. It writes a dictionary to a temporary JSON file that is not

    deleted on close, allowing the test runner to access it.

    Args:
        config (Dict[str, Any]): The Python dictionary to dump into the JSON file.

    Returns:
        Path: The `pathlib.Path` object pointing to the created temporary file.
    """
    # 🧪 Create a named temporary file that persists after closing.
    #    Using the current working directory ensures it's cleaned up by the test harness.
    with tempfile.NamedTemporaryFile(
        dir=os.getcwd(),
        mode="w",
        delete=False,
        suffix=".json",
        encoding="utf-8",
    ) as tmp:
        json.dump(config, tmp)
        logger.info("📄 Created temporary JSON file: %s", tmp.name)

    # ✅ Return the path to the newly created file.
    return Path(tmp.name)


# -----------------------------------------------------------------------------
# 💾 Test Data Fixtures
# -----------------------------------------------------------------------------

# A simple, flat state machine configuration.
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

# A configuration with nested states, `invoke`, and `after` transitions.
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

# A list of multiple configurations for testing multi-machine generation.
SAMPLE_CONFIG_MULTIPLE: List[Dict[str, Any]] = [
    SAMPLE_CONFIG_SIMPLE,
    SAMPLE_CONFIG_NESTED,
]

# A configuration for a parent machine that invokes a child.
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

# A configuration for a child machine to be invoked by a parent.
HIERARCHY_CHILD_CONFIG: Dict[str, Any] = {
    "id": "childMachine",
    "initial": "active",
    "states": {
        "active": {"on": {"CHILD_EVENT": "done"}},
        "done": {"type": "final"},
    },
}
