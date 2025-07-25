# src/xstate_statemachine/cli/extractor.py
# -----------------------------------------------------------------------------
# 🧬 Core Logic Extraction
# -----------------------------------------------------------------------------
# This module is responsible for parsing the state machine's JSON configuration
# and extracting key information. It includes functions to identify all declared
# actions, guards, services, and events. It also contains heuristics to analyze
# multiple machine configurations and infer parent-child relationships, which
# is crucial for generating code for complex, hierarchical state machines.
# -----------------------------------------------------------------------------
"""
Extracts actions, guards, services, and other data from machine configs.
"""

import json
from typing import Any, Dict, List, Set, Tuple


def extract_logic_names(
    config: Dict[str, Any],
) -> Tuple[Set[str], Set[str], Set[str]]:
    """Extracts all unique action, guard, and service names from a machine config.

    This function recursively traverses the state machine configuration dictionary
    to find all declared implementation names. It employs a helper-based traversal
    strategy to keep the logic clean and avoid repetition.

    Args:
        config (Dict[str, Any]): The state machine configuration dictionary.

    Returns:
        Tuple[Set[str], Set[str], Set[str]]: A tuple containing three sets:
        one for action names, one for guard names, and one for service names.
    """
    actions: Set[str] = set()
    guards: Set[str] = set()
    services: Set[str] = set()

    def _process_actions(action_data: Any):
        """Helper to process and extract action names."""
        action_list = (
            action_data if isinstance(action_data, list) else [action_data]
        )
        for act in action_list:
            if isinstance(act, str):
                actions.add(act)
            elif (
                isinstance(act, dict)
                and "type" in act
                and isinstance(act["type"], str)
            ):
                actions.add(act["type"])

    def _process_transition(trans: Any):
        """Helper to process a single transition object."""
        if not isinstance(trans, dict):
            return

        # Extract actions from the transition
        if "actions" in trans:
            _process_actions(trans["actions"])

        # Extract guard from the transition
        guard_key = "cond" if "cond" in trans else "guard"
        if guard_key in trans and isinstance(trans[guard_key], str):
            guards.add(trans[guard_key])

    def traverse(node: Dict[str, Any]):
        """Recursively traverse the configuration tree."""
        # Entry/Exit Actions
        for key in ["entry", "exit"]:
            if key in node:
                _process_actions(node[key])

        # Event-based Transitions
        if "on" in node and isinstance(node["on"], dict):
            for trans_config in node["on"].values():
                trans_list = (
                    trans_config
                    if isinstance(trans_config, list)
                    else [trans_config]
                )
                for t in trans_list:
                    _process_transition(t)

        # Services / Invokes
        if "invoke" in node:
            invoke_list = (
                node["invoke"]
                if isinstance(node["invoke"], list)
                else [node["invoke"]]
            )
            for invoke in invoke_list:
                if isinstance(invoke, dict):
                    if "src" in invoke and isinstance(invoke["src"], str):
                        services.add(invoke["src"])
                    for key in ["onDone", "onError"]:
                        if key in invoke:
                            trans_list = (
                                invoke[key]
                                if isinstance(invoke[key], list)
                                else [invoke[key]]
                            )
                            for t in trans_list:
                                _process_transition(t)

        # Delayed Transitions / After
        if "after" in node and isinstance(node["after"], dict):
            for trans_config in node["after"].values():
                trans_list = (
                    trans_config
                    if isinstance(trans_config, list)
                    else [trans_config]
                )
                for t in trans_list:
                    _process_transition(t)

        # Recurse into nested states
        if "states" in node and isinstance(node["states"], dict):
            for sub_node in node["states"].values():
                traverse(sub_node)

    traverse(config)
    return actions, guards, services


def _count_invokes(cfg: Dict[str, Any]) -> int:
    """Return a crude *actor‑likelihood* score (# of ``invoke`` keys)."""
    cnt = 0

    def _walk(node: Any) -> None:
        nonlocal cnt
        if isinstance(node, dict):
            if "invoke" in node:
                cnt += 1
            for val in node.values():
                _walk(val)
        elif isinstance(node, list):
            for itm in node:
                _walk(itm)

    _walk(cfg)
    return cnt


def guess_hierarchy(
    paths: List[str],
) -> Tuple[str, List[str], List[Tuple[str, int]]]:
    """Heuristically pick *one* parent and return (parent, children, scores).

    The file with the highest ``invoke`` count wins.  Ties fall back to
    *first‑seen*.
    """
    scores: List[Tuple[str, int]] = []
    for pth in paths:
        try:
            with open(pth, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:  # pragma: no cover – handled earlier in main()
            cfg = {}
        scores.append((pth, _count_invokes(cfg)))

    # pick the max score – first element breaks ties
    scores_sorted = sorted(scores, key=lambda kv: kv[1], reverse=True)
    parent, top_score = scores_sorted[0]
    total = sum(sc for _, sc in scores_sorted) or 1
    raw_confidence: float = min(
        100.0, (top_score / total) * 100 + 15
    )  # upper‑bound
    confidence: int = int(raw_confidence)  # cast to int for strong typing

    # attach confidence to first tuple for printing
    printable_scores = [(parent, confidence)] + scores_sorted[1:]
    children = [pth for pth, _ in scores_sorted[1:]]
    return parent, children, printable_scores


def extract_events(config: Dict[str, Any]) -> Set[str]:
    """Extracts all top-level event names from a machine configuration."""
    events = set()

    def traverse(node: Dict[str, Any]):
        if "on" in node and isinstance(node["on"], dict):
            events.update(node["on"].keys())
        if "states" in node and isinstance(node["states"], dict):
            for subnode in node["states"].values():
                traverse(subnode)

    traverse(config)
    return events
