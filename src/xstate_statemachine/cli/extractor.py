# src/xstate_statemachine/cli/extractor.py
# -----------------------------------------------------------------------------
# 🧬 Core Logic Extractor
# -----------------------------------------------------------------------------
# This module is responsible for parsing a state machine's JSON configuration
# to extract key implementation details. It provides functions to meticulously
# identify all declared actions, guards, services, and events.
#
# A key feature is its ability to analyze multiple machine configurations and
# apply heuristics to infer parent-child relationships. This is crucial for
# generating robust code for complex, hierarchical state machines, enabling
# a more intuitive and powerful development workflow.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import json
import logging
from typing import Any, Dict, List, Set, Tuple

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 🧩 Extractor Helper Functions
# -----------------------------------------------------------------------------
# These helpers recursively traverse the state machine configuration to
# extract specific details like actions, guards, and services. They are
# orchestrated by the main `extract_logic_names` function.
# -----------------------------------------------------------------------------


def _extract_actions(data: Any, actions: Set[str]) -> None:
    """
    Extracts action names from various data formats (string, list, dict).

    Args:
        data (Any): 📝 The data that might contain action definitions.
        actions (Set[str]): 📤 The set to which extracted action names are added.
    """
    action_list = data if isinstance(data, list) else [data]
    for action in action_list:
        if isinstance(action, str):
            actions.add(action)
        elif (
            isinstance(action, dict)
            and "type" in action
            and isinstance(action["type"], str)
        ):
            actions.add(action["type"])


def _extract_from_transition(
    transition_data: Any, actions: Set[str], guards: Set[str]
) -> None:
    """
    Extracts actions and guards from a transition object.

    Args:
        transition_data (Any): 📝 The transition data, which can be a single dict or a list of dicts.
        actions (Set[str]): 📤 The set for extracted action names.
        guards (Set[str]): 🛡️ The set for extracted guard names.
    """
    transitions = (
        transition_data
        if isinstance(transition_data, list)
        else [transition_data]
    )
    for trans in transitions:
        if not isinstance(trans, dict):
            continue

        # ⚙️ Extract actions
        if "actions" in trans:
            _extract_actions(trans["actions"], actions)

        # 🛡️ Extract guards (supports both 'cond' and 'guard' keys)
        guard_key = "cond" if "cond" in trans else "guard"
        if guard_key in trans and isinstance(trans[guard_key], str):
            guards.add(trans[guard_key])


def _traverse_and_extract(
    node: Dict[str, Any],
    actions: Set[str],
    guards: Set[str],
    services: Set[str],
) -> None:
    """
    Recursively traverses a configuration node to extract all logic.

    Args:
        node (Dict[str, Any]): 🌳 A node in the state machine configuration tree.
        actions (Set[str]): 📤 The set for action names.
        guards (Set[str]): 🛡️ The set for guard names.
        services (Set[str]): 🔄 The set for service names.
    """
    # 🚪 Process entry and exit actions
    for key in ("entry", "exit"):
        if key in node:
            _extract_actions(node[key], actions)

    # ↪️ Process event-based transitions
    if "on" in node and isinstance(node["on"], dict):
        for transition_data in node["on"].values():
            _extract_from_transition(transition_data, actions, guards)

    # 🔄 Process invoked services
    if "invoke" in node:
        invokes = (
            node["invoke"]
            if isinstance(node["invoke"], list)
            else [node["invoke"]]
        )
        for invoke in invokes:
            if isinstance(invoke, dict):
                if "src" in invoke and isinstance(invoke["src"], str):
                    services.add(invoke["src"])
                # ↪️ Process transitions within the invoke
                for key in ("onDone", "onError"):
                    if key in invoke:
                        _extract_from_transition(invoke[key], actions, guards)

    # ⏳ Process delayed "after" transitions
    if "after" in node and isinstance(node["after"], dict):
        for transition_data in node["after"].values():
            _extract_from_transition(transition_data, actions, guards)

    # 🌲 Recurse into nested states
    if "states" in node and isinstance(node["states"], dict):
        for sub_node in node["states"].values():
            if isinstance(sub_node, dict):
                _traverse_and_extract(sub_node, actions, guards, services)


# -----------------------------------------------------------------------------
# 🏛️ Public API
# -----------------------------------------------------------------------------
# These functions are the primary interface for this module, providing
# organized and reliable extraction of state machine details.
# -----------------------------------------------------------------------------


def extract_logic_names(
    config: Dict[str, Any],
) -> Tuple[Set[str], Set[str], Set[str]]:
    """
    Extracts all unique action, guard, and service names from a machine config.

    This function serves as the entry point for logic extraction. It initializes
    the sets for actions, guards, and services and then starts the recursive
    traversal of the configuration tree.

    Args:
        config (Dict[str, Any]): 📖 The state machine configuration dictionary.

    Returns:
        Tuple[Set[str], Set[str], Set[str]]: A tuple containing three sets:
        one for action names, one for guard names, and one for service names.
    """
    logger.info("🚀 Starting logic extraction from machine config...")
    actions: Set[str] = set()
    guards: Set[str] = set()
    services: Set[str] = set()

    _traverse_and_extract(config, actions, guards, services)

    logger.info(
        f"✅ Extraction complete. Found {len(actions)} actions, {len(guards)} guards, {len(services)} services."
    )
    return actions, guards, services


def _count_invokes(config: Dict[str, Any]) -> int:
    """
    Calculates a heuristic score based on the number of 'invoke' keys.

    This score is used to guess which machine in a set is the most likely
    parent, as parent machines are more likely to invoke other machines (actors).

    Args:
        config (Dict[str, Any]): 📖 The machine configuration to score.

    Returns:
        int: The number of 'invoke' occurrences found.
    """
    count = 0

    def _walk(node: Any) -> None:
        nonlocal count
        if isinstance(node, dict):
            if "invoke" in node:
                count += 1
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(config)
    return count


def guess_hierarchy(
    paths: List[str],
) -> Tuple[str, List[str], List[Tuple[str, int]]]:
    """
    Heuristically identifies a parent machine from a list of configuration files.

    The function scores each machine based on its 'invoke' count. The machine
    with the highest score is designated as the parent. Ties are broken by
    selecting the first machine in the provided list.

    Args:
        paths (List[str]): 📂 A list of file paths to the JSON configurations.

    Returns:
        Tuple[str, List[str], List[Tuple[str, int]]]: A tuple containing:
        - The path of the guessed parent machine.
        - A list of paths for the remaining child machines.
        - A list of all paths with their corresponding scores for display.
    """
    logger.info("🕵️‍♂️ Guessing machine hierarchy based on 'invoke' count...")
    scores: List[Tuple[str, int]] = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)
            scores.append((path, _count_invokes(config)))
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.warning(f"⚠️ Could not read or parse {path}: {e}")
            scores.append((path, 0))

    if not scores:
        return "", [], []

    # 🏆 Sort by score (descending) to find the winner
    scores_sorted = sorted(scores, key=lambda item: item[1], reverse=True)
    parent_path, top_score = scores_sorted[0]
    child_paths = [path for path, _ in scores_sorted[1:]]

    logger.info(f"👑 Guessed parent: '{parent_path}' (Score: {top_score})")
    return parent_path, child_paths, scores_sorted


def extract_events(config: Dict[str, Any]) -> Set[str]:
    """
    Extracts all unique event names declared in a machine configuration.

    Args:
        config (Dict[str, Any]): 📖 The state machine configuration dictionary.

    Returns:
        Set[str]: A set of all unique event names found.
    """
    events: Set[str] = set()

    def _traverse(node: Dict[str, Any]) -> None:
        """Helper to recursively find 'on' blocks."""
        if "on" in node and isinstance(node["on"], dict):
            events.update(node["on"].keys())

        if "states" in node and isinstance(node["states"], dict):
            for sub_node in node["states"].values():
                if isinstance(sub_node, dict):
                    _traverse(sub_node)

    _traverse(config)
    return events
