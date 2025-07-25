# /src/xstate_statemachine/cli.py
# -----------------------------------------------------------------------------
# 🏛️ Command-Line Interface (CLI)
# -----------------------------------------------------------------------------
# This module provides the command-line interface for the xstate-statemachine
# library. It allows users to generate boilerplate code for state machine logic
# and runners directly from JSON configuration files.
#
# The design is centered around the `argparse` library and follows a standard
# subcommand structure (`generate-template`). It acts as a code generation
# factory, taking user-defined options and one or more machine configurations
# to produce ready-to-use Python files. This automates the setup process,
# enforcing best practices and reducing manual effort.
# -----------------------------------------------------------------------------
"""
Command-line interface for generating xstate-statemachine boilerplate.

This tool reads one or more JSON state machine configurations and generates
corresponding logic and runner files. It supports various styles and options
for customization, enabling rapid development and prototyping.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import argparse
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from . import __version__ as package_version

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# Emojis are used to provide quick visual cues for different log levels.
# ℹ️ INFO | ⚠️ WARNING | ❌ ERROR
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Utility Functions
# -----------------------------------------------------------------------------


def camel_to_snake(name: str) -> str:
    """Converts a string from camelCase or PascalCase to snake_case.

    This is a pure function used for normalizing machine and logic names to
    adhere to Python's PEP 8 naming conventions.

    Args:
        name (str): The string in camelCase or PascalCase.

    Returns:
        str: The converted string in snake_case.

    Example:
        >>> camel_to_snake("myCoolMachine")
        'my_cool_machine'
        >>> camel_to_snake("LightSwitch")
        'light_switch'
    """
    name = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()


def normalize_bool(value: str) -> bool:
    """Normalizes a string representation of a boolean to a bool.

    This function handles common string values for true/false (e.g., "yes",
    "no", "1", "0") in a case-insensitive manner. It's used to parse CLI
    arguments that represent boolean flags.

    Args:
        value (str): The string to normalize.

    Returns:
        bool: The corresponding boolean value.

    Raises:
        ValueError: If the input string is not a recognized boolean value.
    """
    true_values = {"true", "yes", "y", "1"}
    false_values = {"false", "no", "n", "0"}
    lower_val = value.lower()

    if lower_val in true_values:
        return True
    if lower_val in false_values:
        return False

    raise ValueError(f"Invalid boolean value: '{value}'")


# -----------------------------------------------------------------------------
# 🧬 Core Logic Extraction
# -----------------------------------------------------------------------------


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


# -------------------------------------------------------------------------
# 🔍  Parent‑vs‑child detection helpers
# -------------------------------------------------------------------------
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
    events = set()

    def traverse(node: Dict[str, Any]):
        if "on" in node and isinstance(node["on"], dict):
            events.update(node["on"].keys())
        if "states" in node and isinstance(node["states"], dict):
            for subnode in node["states"].values():
                traverse(subnode)

    traverse(config)
    return events


# -----------------------------------------------------------------------------
# 📝 Code Generation
# -----------------------------------------------------------------------------


def generate_logic_code(  # noqa: C901 – long but readable, generated code
    actions: Set[str],
    guards: Set[str],
    services: Set[str],
    style: str,
    log: bool,
    is_async: bool,
    machine_name: str,
) -> str:
    """Return the source for ``*_logic.py`` generated from a machine definition.

    The output is **PEP‑8 compliant** and aims to be *warning‑free* in IDEs such
    as PyCharm.  Function / method names are converted to ``snake_case`` and
    sections (Actions / Guards / Services) are emitted **only when non‑empty**.

    Args:
        actions:       Action identifiers collected from the JSON.
        guards:        Guard function identifiers.
        services:      Service names (for ``invoke`` blocks).
        style:         ``"class"`` → one provider class, ``"function"`` → module funcs.
        log:           Insert ``logger.info`` scaffolding when *True*.
        is_async:      Generate ``async def`` stubs instead of sync ones.
        machine_name:  Base name used for the provider class / module.
    """
    # ------------------------------------------------------------------
    # 📑  Imports & logger
    # ------------------------------------------------------------------
    header: List[str] = [
        "# -------------------------------------------------------------------------------",
        "# 📡 Generated Logic File",
        "# -------------------------------------------------------------------------------",
    ]
    if is_async:
        header += ["import asyncio", "from typing import Awaitable"]

    header += [
        "import logging",
        *(["import time"] if (services and not is_async) else []),
        "from typing import Any, Dict, Union",
        "",
        "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition",
        "",
        "# -----------------------------------------------------------------------------",
        "# 🪵 Logger Configuration",
        "# -----------------------------------------------------------------------------",
        "logger = logging.getLogger(__name__)",
        "",
    ]

    # ------------------------------------------------------------------
    # Helper – camelCase → snake_case
    # ------------------------------------------------------------------
    def _snake(identifier: str) -> str:
        """Convert camel/Pascal‑case *identifier* to *snake_case*."""
        try:
            from .cli import camel_to_snake  # type: ignore

            return camel_to_snake(identifier)
        except Exception:  # pragma: no cover – fallback regex path
            import re

            result = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", identifier)
            result = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", result)
            return result.lower()

    # ------------------------------------------------------------------
    # Class / module boilerplate
    # ------------------------------------------------------------------
    indent_cls = ""
    body: List[str] = []

    if style == "class":
        class_name = (
            "".join(p.capitalize() for p in machine_name.split("_")) + "Logic"
        )
        body += [
            "# -----------------------------------------------------------------------------",
            "# 🧠 Class‑based Logic",
            "# -----------------------------------------------------------------------------",
            f"class {class_name}:",
        ]
        indent_cls = "    "

    # ------------------------------------------------------------------
    # ⚙️  ACTIONS
    # ------------------------------------------------------------------
    if actions:
        body.append(f"{indent_cls}# ⚙️ Actions")
        for original in sorted(actions):
            fn = _snake(original)
            async_kw = "async " if is_async else ""
            ret = "Awaitable[None]" if is_async else "None"

            body += [
                f"{indent_cls}{async_kw}def {fn}(  # noqa: ignore IDE static method warning,"
            ]
            if style == "class":
                body.append(f"{indent_cls}        self,")
            body += [
                f"{indent_cls}        interpreter: Union[Interpreter, SyncInterpreter],",
                f"{indent_cls}        context: Dict[str, Any],",
                f"{indent_cls}        event: Event,",
                f"{indent_cls}        action_def: ActionDefinition,  # noqa: D401 – lib callback",
                f"{indent_cls}) -> {ret}:  # noqa : ignore IDE return type hint warning",
                f'{indent_cls}    """Action: `{original}`."""',
            ]
            if log:
                body.append(
                    f'{indent_cls}    logger.info("Executing action {original}")'
                )
            if is_async:
                body.append(
                    f"{indent_cls}    await asyncio.sleep(0.1)  # placeholder"
                )
            body.append(f"{indent_cls}    # TODO: implement\n")

    # ------------------------------------------------------------------
    # 🛡️  GUARDS
    # ------------------------------------------------------------------
    if guards:
        body.append(f"{indent_cls}# 🛡️ Guards")
        for original in sorted(guards):
            fn = _snake(original)
            body += [
                f"{indent_cls}def {fn}(",
            ]
            if style == "class":
                body.append(f"{indent_cls}        self,")
            body += [
                f"{indent_cls}        context: Dict[str, Any],",
                f"{indent_cls}        event: Event,",
                f"{indent_cls}) -> bool:",
                f'{indent_cls}    """Guard: `{original}`."""',
            ]
            if log:
                body.append(
                    f'{indent_cls}    logger.info("Evaluating guard {original}")'
                )
            body.append(
                f"{indent_cls}    # TODO: implement guard logic\n"
                f"{indent_cls}    return True\n"
            )

    # ------------------------------------------------------------------
    # 🔄  SERVICES
    # ------------------------------------------------------------------
    if services:
        body.append(f"{indent_cls}# 🔄 Services")
        for original in sorted(services):
            fn = _snake(original)
            async_kw = "async " if is_async else ""
            ret = "Awaitable[Dict[str, Any]]" if is_async else "Dict[str, Any]"

            body += [
                f"{indent_cls}{async_kw}def {fn}(  # noqa: ignore IDE static method warning,"
            ]
            if style == "class":
                body.append(f"{indent_cls}        self,")
            body += [
                f"{indent_cls}        interpreter: Union[Interpreter, SyncInterpreter],",
                f"{indent_cls}        context: Dict[str, Any],",
                f"{indent_cls}        event: Event,",
                f"{indent_cls}) -> {ret}:",
                f'{indent_cls}    """Service: `{original}`."""',
            ]
            if log:
                body.append(
                    f'{indent_cls}    logger.info("Running service {original}")'
                )
            if is_async:
                body.append(f"{indent_cls}    await asyncio.sleep(1)")
            else:
                body.append(f"{indent_cls}    time.sleep(1)")
            body.append(
                f"{indent_cls}    # TODO: implement service\n"
                f"{indent_cls}    return {{'result': 'done'}}  # noqa : ignore IDE return type hint warning\n"
            )
            # keep the original (camel‑case) name available for the loader
            if fn != original:
                body.append(
                    f"{indent_cls}{original} = {fn}  # alias for JSON name\n"
                )

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    return "\n".join(header + body)


def generate_runner_code(  # noqa: C901 – function is long but readable
    machine_names: List[str],
    is_async: bool,
    style: str,
    loader: bool,
    sleep: bool,
    sleep_time: int,
    log: bool,
    file_count: int,
    configs: List[Dict[str, Any]],
    json_filenames: List[str],
    hierarchy: bool = False,  # NEW ▸ treat first machine as parent
) -> str:
    """Generates the runner file content to execute the state machine(s).

    The function builds the code for the runner module (``*_runner.py``).
    It now supports two operating modes:

    * **Flat / legacy** – every JSON is an independent machine (old behaviour).
    * **Hierarchy** – the *first* machine in *machine_names* is considered the
      **parent**; all remaining machines are actor definitions that can be
      spawned by the parent (selected when *hierarchy* is ``True``).

    Args:
        machine_names:     snake‑cased machine identifiers (order matters).
        is_async:          generate an asynchronous runner if ``True``.
        style:             'class' or 'function' logic style.
        loader:            use auto‑discovery logic loader when ``True``.
        sleep:             insert ``time.sleep`` / ``asyncio.sleep`` calls?
        sleep_time:        seconds to sleep between simulated events.
        log:               configure basic logging output.
        file_count:        1 → combined file, 2 → separate logic/runner files.
        configs:           list with the parsed JSON machine configs.
        json_filenames:    filenames of the original JSON files (same order).
        hierarchy:         **NEW**; when ``True`` treat list as parent+actors.

    Returns:
        The generated Python source code as a single string.
    """
    # ------------------------------------------------------------------
    # 📄  Preamble & imports
    # ------------------------------------------------------------------
    base_name = (
        "_".join(machine_names) if len(machine_names) > 1 else machine_names[0]
    )
    logic_file_name = (
        f"{base_name}_logic"  # defined unconditionally (even if unused)
    )

    class_name = (
        "".join(word.capitalize() for word in base_name.split("_")) + "Logic"
    )

    code_lines = [
        "# -------------------------------------------------------------------------------",
        "# 📡 Generated Runner File",
        "# -------------------------------------------------------------------------------",
        "from pathlib import Path",
        "from xstate_statemachine import LoggingInspector",
        "from xstate_statemachine import create_machine, "
        + ("Interpreter" if is_async else "SyncInterpreter"),
        "import json",
        "import logging",
    ]
    if sleep and not is_async:
        code_lines.append("import time")
    if is_async:
        code_lines.append("import asyncio")
    code_lines.append("")

    if log:
        code_lines.extend(
            [
                "logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')",
                "logger = logging.getLogger(__name__)",
                "",
            ]
        )

    # ------------------------------------------------------------------
    # 🧩  Import generated *logic* module (when we have two files)
    # ------------------------------------------------------------------
    if file_count == 2:
        if style == "class":
            code_lines.append(
                f"from {logic_file_name} import {class_name} as LogicProvider"
            )
        else:
            code_lines.append(f"import {logic_file_name}")
        code_lines.append("")

    func_prefix = "async " if is_async else ""
    await_prefix = "await " if is_async else ""
    sleep_cmd = "await asyncio.sleep" if is_async else "time.sleep"

    # ==================================================================
    # 👑  MODE 1 – Hierarchical (parent + actors)
    # ==================================================================
    if hierarchy and len(machine_names) > 1:
        parent_name, *actor_names = machine_names
        parent_json, *actor_jsons = json_filenames
        parent_cfg = configs[0]

        code_lines.extend(
            [
                f"{func_prefix}def main() -> None:",
                '    """Run the *parent* machine together with all actor machines.\n\n'
                "    The runner will:\n"
                "      1. load every JSON config,\n"
                "      2. start the parent interpreter (with logic bound if requested),\n"
                "      3. start an interpreter for **each** actor,\n"
                "      4. replay *all* events discovered in every machine to exercise\n"
                "         every transition path (best‑effort 100 % coverage),\n"
                "      5. stop all interpreters gracefully.\n"
                '    """',
                "",
                "    root_dir = Path(__file__).parent",
                f"    parent_cfg = json.loads((root_dir / '{parent_json}').read_text())",
                "    actor_cfgs = {",
            ]
            + [
                f"        '{actor_names[idx]}': json.loads((root_dir / '{jfn}').read_text()),"
                for idx, jfn in enumerate(actor_jsons)
            ]
            + [
                "    }",
                "",
                "    # -----------------------------------------------------------------------",
                "    # 🧠 Parent machine + logic binding",
                "    # -----------------------------------------------------------------------",
            ]
        )

        if loader:
            if style == "class":
                if file_count == 1:
                    code_lines.append(f"    logic_provider = {class_name}()")
                else:
                    code_lines.append("    logic_provider = LogicProvider()")
                code_lines.append(
                    "    parent_machine = create_machine(parent_cfg, logic_providers=[logic_provider])"
                )
            else:
                if file_count == 2:
                    code_lines.append(
                        f"    parent_machine = create_machine(parent_cfg, logic_modules=[{logic_file_name}])"
                    )
                else:
                    code_lines.append("    import sys")
                    code_lines.append(
                        "    parent_machine = create_machine(parent_cfg, logic_modules=[sys.modules[__name__]])"
                    )
        else:
            code_lines.append(
                "    parent_machine = create_machine(parent_cfg)"
            )

        parent_ctor = "Interpreter" if is_async else "SyncInterpreter"
        code_lines.extend(
            [
                f"    parent = {parent_ctor}(parent_machine)",
                "    parent.use(LoggingInspector())",
                f"    {await_prefix}parent.start()",
                "    logger.info('Parent started – initial state(s): %s', parent.current_state_ids)",
                "",
                "    # -------------------------------------------------------------------",
                "    # 🎭 Spawn & start every actor interpreter",
                "    # -------------------------------------------------------------------",
                f"    actor_ctor = {parent_ctor}  # same sync/async flavour",
                "    actors = {}  # id → interpreter",
            ]
        )

        for a_name in actor_names:
            code_lines.extend(
                [
                    f"    machine_{a_name} = create_machine(actor_cfgs['{a_name}'])",
                    f"    ai_{a_name} = actor_ctor(machine_{a_name})",
                    f"    ai_{a_name}.use(LoggingInspector())",
                    f"    {await_prefix}ai_{a_name}.start()",
                    f"    actors['{a_name}'] = ai_{a_name}",
                ]
            )

        # ---------------------------------------------------------------- Events replay – parent
        code_lines.extend(
            [
                "",
                "    # -------------------------------------------------------------------",
                "    # 🚀 Simulating Parent Machine",
                "    # -------------------------------------------------------------------",
            ]
        )
        parent_events = sorted(extract_events(parent_cfg))
        if parent_events:
            for ev in parent_events:
                human = ev.replace("_", " ").title()
                code_lines.extend(
                    [
                        f"    # {human}",
                        f"    logger.info('Parent → sending %s', '{ev}')",
                        f"    {await_prefix}parent.send('{ev}')",
                    ]
                )
                if sleep:
                    code_lines.append(f"    {sleep_cmd}({sleep_time})")
                code_lines.append("")
        else:
            code_lines.append(
                "    logger.info('No events declared in parent machine.')"
            )
            code_lines.append("")

        # ---------------------------------------------------------------- Events replay – actors
        for idx, a_name in enumerate(actor_names):
            actor_events = sorted(extract_events(configs[idx + 1]))
            code_lines.extend(
                [
                    "    # -------------------------------------------------------------------",
                    f"    # 🚀 Simulating Actor «{a_name}»",
                    "    # -------------------------------------------------------------------",
                ]
            )
            if actor_events:
                for ev in actor_events:
                    human = ev.replace("_", " ").title()
                    code_lines.extend(
                        [
                            f"    # {human}",
                            f"    logger.info('{a_name} → sending %s', '{ev}')",
                            f"    {await_prefix}actors['{a_name}'].send('{ev}')",
                        ]
                    )
                    if sleep:
                        code_lines.append(f"    {sleep_cmd}({sleep_time})")
                    code_lines.append("")
            else:
                code_lines.append(
                    f"    logger.info('No events declared in actor \"{a_name}\".')"
                )
                code_lines.append("")

        # ---------------------------------------------------------------- Shutdown
        code_lines.extend(
            [
                "    # -------------------------------------------------------------------",
                "    # 🛑 Graceful shutdown of actors then parent",
                "    # -------------------------------------------------------------------",
            ]
        )
        for a_name in actor_names:
            code_lines.append(f"    {await_prefix}actors['{a_name}'].stop()")
        code_lines.append(f"    {await_prefix}parent.stop()")
        code_lines.append("")
        if is_async:
            code_lines.extend(
                [
                    "if __name__ == '__main__':",
                    "    asyncio.run(main())",
                ]
            )
        else:
            code_lines.extend(
                [
                    "if __name__ == '__main__':",
                    "    main()",
                ]
            )

        return "\n".join(code_lines)

    # ==================================================================
    # 🟰  MODE 2 – Flat / legacy (original implementation, untouched)
    # ==================================================================
    if len(machine_names) == 1:
        name = machine_names[0]
        config = configs[0]
        json_filename = json_filenames[0]
        events = sorted(extract_events(config))
        code_lines.append(f"{func_prefix}def main() -> None:")
        inner_indent = "    "
        code_lines.append(
            f'{inner_indent}"""Executes the simulation for the {name} machine."""'
        )
        code_lines.append("")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        code_lines.append(f"{inner_indent}# 📂 1. Configuration Loading")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        code_lines.append(
            f"{inner_indent}config_path = Path(__file__).parent / '{json_filename}'"
        )
        code_lines.append(
            f"{inner_indent}with open(config_path, 'r', encoding='utf-8') as f:"
        )
        code_lines.append(f"{inner_indent}    config = json.load(f)")
        code_lines.append("")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        code_lines.append(f"{inner_indent}# 🧠 2. Logic Binding")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        if loader:
            if style == "class":
                code_lines.append(
                    f"{inner_indent}logic_provider = {class_name}()"
                )
                code_lines.append(
                    f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])"
                )
            else:
                code_lines.append(
                    f"{inner_indent}machine = create_machine(config, logic_modules=[{logic_file_name}])"
                )
        else:
            code_lines.append(
                f"{inner_indent}# TODO: Fill actions, guards, services"
            )
            code_lines.append(
                f"{inner_indent}machine_logic = MachineLogic(actions={{}}, guards={{}}, services={{}})"
            )
            code_lines.append(
                f"{inner_indent}machine = create_machine(config, logic=machine_logic)"
            )
        code_lines.append("")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        code_lines.append(f"{inner_indent}# ⚙️  3. Interpreter Setup")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        interp_type = (
            "Interpreter(machine)" if is_async else "SyncInterpreter(machine)"
        )
        code_lines.append(f"{inner_indent}interpreter = {interp_type}")
        code_lines.append(f"{inner_indent}interpreter.use(LoggingInspector())")
        code_lines.append(f"{inner_indent}{await_prefix}interpreter.start()")
        code_lines.append(
            f'{inner_indent}logger.info(f"Initial state: {{interpreter.current_state_ids}}")'
        )
        code_lines.append("")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        code_lines.append(f"{inner_indent}# 🚀 4. Simulation Scenario")
        code_lines.append(
            f"{inner_indent}# ---------------------------------------------------------------------------"
        )
        if events:
            for ev in events:
                human = ev.replace("_", " ").title()
                code_lines.extend(
                    [
                        f"{inner_indent}# {human}",
                        f"{inner_indent}logger.info('→ Sending %s', '{ev}')",
                        f"{inner_indent}{await_prefix}interpreter.send('{ev}')",
                    ]
                )
                if sleep:
                    code_lines.append(
                        f"{inner_indent}{sleep_cmd}({sleep_time})"
                    )
                code_lines.append("")
        else:
            code_lines.append(
                f"{inner_indent}logger.info('No events declared in the machine.')"
            )
            code_lines.append("")
        code_lines.append(f"{inner_indent}{await_prefix}interpreter.stop()")
        code_lines.append("")
        if is_async:
            code_lines.append("if __name__ == '__main__':")
            code_lines.append("    asyncio.run(main())")
        else:
            code_lines.append("if __name__ == '__main__':")
            code_lines.append("    main()")
    else:
        for idx, name in enumerate(machine_names):
            config = configs[idx]
            json_filename = json_filenames[idx]
            events = sorted(extract_events(config))
            code_lines.append(f"{func_prefix}def run_{name}() -> None:")
            inner_indent = "    "
            code_lines.append(
                f'{inner_indent}"""Executes the simulation for the {name} machine."""'
            )
            code_lines.append("")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            code_lines.append(f"{inner_indent}# 📂 1. Configuration Loading")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            code_lines.append(
                f"{inner_indent}config_path = Path(__file__).parent / '{json_filename}'"
            )
            code_lines.append(
                f"{inner_indent}with open(config_path, 'r', encoding='utf-8') as f:"
            )
            code_lines.append(f"{inner_indent}    config = json.load(f)")
            code_lines.append("")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            code_lines.append(f"{inner_indent}# 🧠 2. Logic Binding")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            if loader:
                if style == "class":
                    code_lines.append(
                        f"{inner_indent}logic_provider = LogicProvider()"
                    )
                    code_lines.append(
                        f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])"
                    )
                else:
                    code_lines.append(
                        f"{inner_indent}machine = create_machine(config, logic_modules=[{logic_file_name}])"
                    )
            else:
                code_lines.append(
                    f"{inner_indent}# TODO: Fill actions, guards, services"
                )
                code_lines.append(
                    f"{inner_indent}machine_logic = MachineLogic(actions={{}}, guards={{}}, services={{}})"
                )
                code_lines.append(
                    f"{inner_indent}machine = create_machine(config, logic=machine_logic)"
                )
            code_lines.append("")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            code_lines.append(f"{inner_indent}# ⚙️  3. Interpreter Setup")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            interp_type = (
                "Interpreter(machine)"
                if is_async
                else "SyncInterpreter(machine)"
            )
            code_lines.append(f"{inner_indent}interpreter = {interp_type}")
            code_lines.append(
                f"{inner_indent}interpreter.use(LoggingInspector())"
            )
            code_lines.append(
                f"{inner_indent}{await_prefix}interpreter.start()"
            )
            code_lines.append(
                f'{inner_indent}logger.info(f"Initial state: {{interpreter.current_state_ids}}")'
            )
            code_lines.append("")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            code_lines.append(f"{inner_indent}# 🚀 4. Simulation Scenario")
            code_lines.append(
                f"{inner_indent}# ---------------------------------------------------------------------------"
            )
            if events:
                for ev in events:
                    human = ev.replace("_", " ").title()
                    code_lines.extend(
                        [
                            f"{inner_indent}# {human}",
                            f"{inner_indent}logger.info('→ Sending %s', '{ev}')",
                            f"{inner_indent}{await_prefix}interpreter.send('{ev}')",
                        ]
                    )
                    if sleep:
                        code_lines.append(
                            f"{inner_indent}{sleep_cmd}({sleep_time})"
                        )
                    code_lines.append("")
            else:
                code_lines.append(
                    f"{inner_indent}logger.info('No events declared in this machine.')"
                )
                code_lines.append("")
            code_lines.append(
                f"{inner_indent}{await_prefix}interpreter.stop()"
            )
            code_lines.append("")

        code_lines.append(f"{func_prefix}def main() -> None:")
        inner_indent = "    "
        for name in machine_names:
            code_lines.append(f"{inner_indent}{await_prefix}run_{name}()")
        code_lines.append("")
        if is_async:
            code_lines.append("if __name__ == '__main__':")
            code_lines.append("    asyncio.run(main())")
        else:
            code_lines.append("if __name__ == '__main__':")
            code_lines.append("    main()")

    return "\n".join(code_lines)


# -----------------------------------------------------------------------------
# 🚀 Main CLI Entrypoint
# -----------------------------------------------------------------------------


def main():  # noqa: C901 – function is long but readable
    """Parses command-line arguments and orchestrates code generation."""
    # -------------------------------------------------------------------------
    # ⚙️ 1. Argument Parsing Setup
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description="CLI tool for xstate-statemachine boilerplate generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
          # Generate from a single file with default options (async, class-based, 2 files)
          xstate-statemachine generate-template my_machine.json

          # Generate sync, function-style code into a specific directory
          xstate-statemachine generate-template machine.json --async-mode no --style function --output ./generated

          # Force overwrite of existing files
          xstate-statemachine generate-template machine.json --force
        """,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {package_version}"
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    gen_parser = subparsers.add_parser(
        "generate-template",
        help="Generate boilerplate templates from JSON machine configs.",
    )

    # --- File Inputs ---
    gen_parser.add_argument(
        "json_files",
        nargs="*",
        help="One or more JSON config files to process.",
    )
    gen_parser.add_argument(
        "--json",
        action="append",
        default=[],
        help="Specify a JSON file (can be used multiple times).",
    )

    gen_parser.add_argument(
        "--json-parent",
        metavar="PATH",
        help="Path to the JSON file that represents the *parent* machine.",
    )
    gen_parser.add_argument(
        "--json-child",
        metavar="PATH",
        action="append",
        default=[],
        help=(
            "Path to a JSON file that should be treated as a *child* (actor) "
            "machine. Can be supplied multiple times."
        ),
    )

    # --- Generation Options ---
    gen_parser.add_argument(
        "--output",
        help="Output directory (defaults to the first JSON's parent).",
    )
    gen_parser.add_argument(
        "--style",
        choices=["class", "function"],
        default="class",
        help="Code style for logic: 'class' or 'function'. Default: class.",
    )
    gen_parser.add_argument(
        "--file-count",
        type=int,
        choices=[1, 2],
        default=2,
        help="Output files: 1 (combined) or 2 (logic/runner). Default: 2.",
    )
    gen_parser.add_argument(
        "--async-mode",
        default="yes",
        help="Generate async code: 'yes' or 'no'. Default: yes.",
    )
    gen_parser.add_argument(
        "--loader",
        default="yes",
        help="Use auto-discovery loader in runner: 'yes' or 'no'. Default: yes.",
    )
    gen_parser.add_argument(
        "--log",
        default="yes",
        help="Add logging statements in stubs: 'yes' or 'no'. Default: yes.",
    )
    gen_parser.add_argument(
        "--sleep",
        default="yes",
        help="Add a sleep call in runner simulation: 'yes' or 'no'. Default: yes.",
    )
    gen_parser.add_argument(
        "--sleep-time",
        type=int,
        default=2,
        help="Sleep time in seconds for the simulation. Default: 2.",
    )
    gen_parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite of existing generated files.",
    )

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # 🚀 2. Generation Logic
    # -------------------------------------------------------------------------
    if args.subcommand == "generate-template":
        # 📂 Collect and *order* JSON files:
        #    1. explicit --json-parent (if given)
        #    2. explicit --json-child  (repeatable)
        #    3. positional files       (left‑overs)
        #    4. --json flags           (legacy)

        json_paths: List[str] = []

        # 1. parent --------------------------------------------------------
        if args.json_parent:
            json_paths.append(args.json_parent)

        # 2. children ------------------------------------------------------
        json_paths.extend(args.json_child)

        # 3–4. remaining legacy inputs ------------------------------------
        json_paths.extend(args.json_files)
        json_paths.extend(args.json)

        # -----------------------------------------------------------------
        # 🛑 Sanity checks for parent/child flags
        # -----------------------------------------------------------------
        if args.json_parent and len([args.json_parent]) > 1:
            logger.error("❌ Only one --json-parent may be supplied.")
            parser.error("Only one --json-parent may be supplied.")

        # Scenario #7 – child flag without *any* other file ----------------
        if args.json_child and not (
            args.json_parent or args.json_files or args.json
        ):
            logger.error("❌ --json-child requires a parent machine JSON.")
            parser.error("--json-child requires a parent machine JSON.")

        if not json_paths:
            logger.error("❌ No JSON files provided. Aborting.")
            parser.error("At least one JSON file is required.")

        # 🔄  De‑duplicate while preserving order
        seen: Set[str] = set()
        json_paths = [p for p in json_paths if not (p in seen or seen.add(p))]
        if not json_paths:
            logger.error("❌ No JSON files provided. Aborting.")
            parser.error("At least one JSON file is required.")

        logger.info(f"ℹ️ Processing {len(json_paths)} JSON file(s)...")

        configs, machine_names, json_filenames = [], [], []
        all_actions, all_guards, all_services = set(), set(), set()

        for jp in json_paths:
            path = Path(jp)
            if not path.exists():
                logger.error(f"❌ JSON file not found: {jp}")
                parser.error(f"JSON file not found: {jp}")
            with open(path, "r", encoding="utf-8") as f:
                conf = json.load(f)

            raw_name = conf.get("id", path.stem)
            name = camel_to_snake(raw_name)
            machine_names.append(name)
            configs.append(conf)
            json_filenames.append(path.name)

            # 🧬 Extract logic names
            a, g, s = extract_logic_names(conf)
            all_actions.update(a)
            all_guards.update(g)
            all_services.update(s)

        # -----------------------------------------------------------------
        # 🤖  Heuristic parent detection & optional prompt  (#8‒#10)
        # -----------------------------------------------------------------
        hierarchy_flag: bool = False  # default → “flat” mode
        if not args.json_parent and len(json_paths) > 1:
            ids = [
                conf.get("id", fn.stem)
                for conf, fn in zip(configs, map(Path, json_paths))
            ]
            # --- simple reference‑count heuristic ------------------------
            ref_scores: List[int] = []
            for conf in configs:
                refs: Set[str] = set()

                def _walk(node: Dict[str, Any]) -> None:  # inner helper
                    if not isinstance(node, dict):
                        return
                    if "invoke" in node:
                        inv_list = (
                            node["invoke"]
                            if isinstance(node["invoke"], list)
                            else [node["invoke"]]
                        )
                        for inv in inv_list:
                            if isinstance(inv, dict) and isinstance(
                                inv.get("src"), str
                            ):
                                refs.add(inv["src"])
                    if "states" in node and isinstance(node["states"], dict):
                        for sub in node["states"].values():
                            _walk(sub)

                _walk(conf)
                ref_scores.append(len(refs.intersection(set(ids))))

            max_score: int = max(ref_scores)
            candidate_idx: int = -1
            if max_score > 0 and ref_scores.count(max_score) == 1:
                candidate_idx = ref_scores.index(max_score)

            # --- interactive confirmation / selection -------------------
            if candidate_idx != -1:
                confidence = int(round(100 * max_score / (len(ids) - 1)))
                print(
                    "Found two machines:"
                    if len(ids) == 2
                    else f"Found {len(ids)} machines:"
                )
                for i, mid in enumerate(ids, 1):
                    if i - 1 == candidate_idx:
                        print(
                            f"  {i}. {mid} (looks like parent, confidence {confidence} %)"
                        )
                    else:
                        print(f"  {i}. {mid} (looks like child)")
                answer = input("Is this correct?  [Y/n] ").strip().lower()
                if answer in ("", "y", "yes"):
                    hierarchy_flag = True
                else:
                    candidate_idx = -1  # fall through to manual selection

            if candidate_idx == -1:
                print("Multiple machines detected – which one is the parent?")
                for i, mid in enumerate(ids, 1):
                    print(f"  {i}. {mid}")
                sel = input("Enter number (or 0 for none): ").strip()
                try:
                    sel_int = int(sel)
                except ValueError:
                    sel_int = 0
                if 1 <= sel_int <= len(ids):
                    candidate_idx = sel_int - 1
                    hierarchy_flag = True

            # --- reorder lists so that parent is *first* -----------------
            if hierarchy_flag and candidate_idx != 0:
                for lst in (
                    json_paths,
                    configs,
                    machine_names,
                    json_filenames,
                ):
                    lst.insert(0, lst.pop(candidate_idx))

        # Explicit flags always imply hierarchy ---------------------------
        if args.json_parent:
            hierarchy_flag = True

        # 📁 Determine output directory and file paths
        out_dir = (
            Path(args.output) if args.output else Path(json_paths[0]).parent
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        base_name = (
            "_".join(machine_names)
            if len(machine_names) > 1
            else machine_names[0]
        )
        logic_file = out_dir / f"{base_name}_logic.py"
        runner_file = out_dir / f"{base_name}_runner.py"
        single_file = out_dir / f"{base_name}.py"

        # ⚠️ Check for existing files before proceeding
        if not args.force:
            if args.file_count == 1:
                files_to_check = [single_file]
            else:
                files_to_check = [logic_file, runner_file]

            if any(f.exists() for f in files_to_check if f):
                print("Files exist, use --force to overwrite.")
                return

        # ⚙️ Normalize boolean options from strings
        try:
            loader_bool = normalize_bool(args.loader)
            sleep_bool = normalize_bool(args.sleep)
            async_bool = normalize_bool(args.async_mode)
            log_bool = normalize_bool(args.log)
        except ValueError as e:
            logger.error(f"❌ Invalid argument value: {e}")
            parser.error(str(e))

        # 📝 Generate code content
        logic_code = generate_logic_code(
            all_actions,
            all_guards,
            all_services,
            args.style,
            log_bool,
            async_bool,
            base_name,
        )
        runner_code = generate_runner_code(
            machine_names,
            async_bool,
            args.style,
            loader_bool,
            sleep_bool,
            args.sleep_time,
            log_bool,
            args.file_count,
            configs,
            json_filenames,
            hierarchy=hierarchy_flag,  # NEW ▸ informs runner of parent/child
        )

        # 💾 Write generated code to file(s)
        if args.file_count == 1:
            if single_file:
                logger.info(f"💾 Writing combined code to: {single_file}")
                # ---- Merge *intelligently* so imports / logger appear only once -------------
                logic_lines = logic_code.splitlines()
                runner_lines = runner_code.splitlines()

                # 1️⃣  collect all top‑level imports already present in the *logic* part
                seen_imports: Set[str] = {
                    ln
                    for ln in logic_lines
                    if ln.startswith(("import ", "from "))
                }

                # 2️⃣  pull in only *new* imports from the runner header  (avoid duplicates)
                extra_imports: List[str] = [
                    ln
                    for ln in runner_lines
                    if ln.startswith(("import ", "from "))
                    and ln not in seen_imports
                ]

                # 3️⃣  grab runner body (skip its own logging setup / logger) -----------------
                start_body = next(
                    (
                        idx + 1
                        for idx, ln in enumerate(runner_lines)
                        if ln.strip() == "" and idx > 0
                    ),
                    0,
                )
                runner_body_raw: List[str] = runner_lines[start_body:]
                runner_body: List[str] = [
                    ln
                    for ln in runner_body_raw
                    if not ln.lstrip().startswith(
                        ("logging.basicConfig", "logger = logging.getLogger")
                    )
                ]

                # 4️⃣  inject the extra imports right after the last import in *logic*
                merged: List[str] = []
                injected = False
                for idx, ln in enumerate(logic_lines):
                    merged.append(ln)
                    if (
                        not injected
                        and ln.startswith(("import ", "from "))
                        and (
                            idx + 1 == len(logic_lines)
                            or not logic_lines[idx + 1].startswith(
                                ("import ", "from ")
                            )
                        )
                    ):
                        merged.extend(extra_imports)
                        injected = True

                # 5️⃣  ensure `logging.basicConfig` & the *single* logger definition exist once
                if not any("logging.basicConfig" in line for line in merged):
                    for line in runner_lines:
                        if line.startswith("logging.basicConfig"):
                            merged.append(line)
                            break

                if not any(
                    "logger = logging.getLogger" in line_ for line_ in merged
                ):
                    merged.append("logger = logging.getLogger(__name__)")

                # 6️⃣  stitch everything together
                merged.extend(["", "", "# Runner part"])
                merged.extend(runner_body)

                combined_code = "\n".join(merged)
                single_file.write_text(combined_code, encoding="utf-8")
                print(f"Generated combined file: {single_file}")
        else:
            logger.info(f"💾 Writing logic code to: {logic_file}")
            logic_file.write_text(logic_code, encoding="utf-8")
            logger.info(f"💾 Writing runner code to: {runner_file}")
            runner_file.write_text(runner_code, encoding="utf-8")
            print(f"Generated logic file: {logic_file}")
            print(f"Generated runner file: {runner_file}")

    else:
        parser.print_help()


# -----------------------------------------------------------------------------
# 🏁 Script Execution
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
