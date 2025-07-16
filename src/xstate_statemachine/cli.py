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


# -----------------------------------------------------------------------------
# 📝 Code Generation
# -----------------------------------------------------------------------------


def generate_logic_code(
    actions: Set[str],
    guards: Set[str],
    services: Set[str],
    style: str,
    log: bool,
    is_async: bool,
    machine_name: str,
) -> str:
    """Generates the logic file content with placeholders.

    This function constructs the Python code for the logic file (`..._logic.py`)
    based on the extracted names and user-selected options (e.g., class vs.
    function style, async vs. sync).

    Args:
        actions (Set[str]): A set of action names.
        guards (Set[str]): A set of guard names.
        services (Set[str]): A set of service names.
        style (str): The code style, either 'class' or 'function'.
        log (bool): Whether to include logging statements in the stubs.
        is_async (bool): Whether to generate asynchronous function signatures.
        machine_name (str): The base name for the logic class.

    Returns:
        str: The generated Python code as a string.
    """
    code_lines = [
        "# -------------------------------------------------------------------------------",
        "# 📡 Generated Logic File",
        "# -------------------------------------------------------------------------------",
    ]

    # --- Imports ---
    if is_async:
        code_lines.extend(["import asyncio", "from typing import Awaitable"])
    code_lines.extend(["import logging", "from typing import Any, Dict"])
    if not is_async and services:
        code_lines.append("import time")

    code_lines.extend(
        [
            "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition",
            "",
            "# -----------------------------------------------------------------------------",
            "# 🪵 Logger Configuration",
            "# -----------------------------------------------------------------------------",
            "logger = logging.getLogger(__name__)",
            "",
        ]
    )

    class_indent = ""
    func_self = ""
    base_name = (
        "".join(word.capitalize() for word in machine_name.split("_"))
        + "Logic"
    )

    if style == "class":
        code_lines.extend(
            [
                "# -----------------------------------------------------------------------------",
                "# 🧠 Class-based Logic",
                "# -----------------------------------------------------------------------------",
                f"class {base_name}:",
            ]
        )
        class_indent = "    "
        func_self = "self, "

    # --- Actions ---
    code_lines.append(f"{class_indent}# ⚙️ Actions")
    for act in sorted(actions):
        async_prefix = "async " if is_async else ""
        ret_type = "Awaitable[None]" if is_async else "None"
        code_lines.extend(
            [
                f"{class_indent}{async_prefix}def {act}(",
                f"{class_indent}        {func_self}",
                f"{class_indent}        interpreter: Interpreter if {is_async} else SyncInterpreter,",
                f"{class_indent}        context: Dict[str, Any],",
                f"{class_indent}        event: Event,",
                f"{class_indent}        action_def: ActionDefinition",
                f"{class_indent}) -> {ret_type}:",
                f'{class_indent}    """Action: {act}."""',
            ]
        )
        if log:
            code_lines.append(
                f'{class_indent}    logger.info("Executing action {act}")'
            )
        if is_async:
            code_lines.append(
                f"{class_indent}    await asyncio.sleep(0.1)  # Dummy async"
            )
        code_lines.append(
            f"{class_indent}    pass  # TODO: Implement action\n"
        )

    # --- Guards ---
    code_lines.append(f"{class_indent}# 🛡️ Guards")
    for g in sorted(guards):
        code_lines.extend(
            [
                f"{class_indent}def {g}(",
                f"{class_indent}        {func_self}",
                f"{class_indent}        context: Dict[str, Any],",
                f"{class_indent}        event: Event",
                f"{class_indent}) -> bool:",
                f'{class_indent}    """Guard: {g}."""',
            ]
        )
        if log:
            code_lines.append(
                f'{class_indent}    logger.info("Evaluating guard {g}")'
            )
        code_lines.append(
            f"{class_indent}    return True  # TODO: Implement guard\n"
        )

    # --- Services ---
    code_lines.append(f"{class_indent}# 🔄 Services")
    for s in sorted(services):
        async_prefix = "async " if is_async else ""
        ret_type = (
            "Awaitable[Dict[str, Any]]" if is_async else "Dict[str, Any]"
        )
        code_lines.extend(
            [
                f"{class_indent}{async_prefix}def {s}(",
                f"{class_indent}        {func_self}",
                f"{class_indent}        interpreter: Interpreter if {is_async} else SyncInterpreter,",
                f"{class_indent}        context: Dict[str, Any],",
                f"{class_indent}        event: Event",
                f"{class_indent}) -> {ret_type}:",
                f'{class_indent}    """Service: {s}."""',
            ]
        )
        if log:
            code_lines.append(
                f'{class_indent}    logger.info("Running service {s}")'
            )
        if is_async:
            code_lines.append(f"{class_indent}    await asyncio.sleep(1)")
        else:
            code_lines.append(f"{class_indent}    time.sleep(1)")
        code_lines.append(
            f"{class_indent}    return {{'result': 'done'}}  # TODO: Implement service\n"
        )

    return "\n".join(code_lines)


def generate_runner_code(
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
) -> str:
    """Generates the runner file content to execute the state machine.

    This function builds the code for the runner file (`..._runner.py`),
    which sets up and executes a simulation of the state machine(s).

    Args:
        machine_names (List[str]): A list of snake_cased machine names.
        is_async (bool): Whether to generate an asynchronous runner.
        style (str): The code style ('class' or 'function') for logic import.
        loader (bool): Whether to use the auto-discovery loader.
        sleep (bool): Whether to include a `time.sleep` in the simulation.
        sleep_time (int): The duration for the sleep.
        log (bool): Whether to configure and use logging.
        file_count (int): The number of generated files (1 or 2).
        configs (List[Dict[str, Any]]): The list of machine configurations.
        json_filenames (List[str]): The list of original JSON filenames.

    Returns:
        str: The generated Python code for the runner as a string.
    """
    code_lines = [
        "# -------------------------------------------------------------------------------",
        "# 📡 Generated Runner File",
        "# -------------------------------------------------------------------------------",
        "from pathlib import Path",
        "from xstate_statemachine import LoggingInspector",
    ]
    interp_import = "Interpreter" if is_async else "SyncInterpreter"
    code_lines.append(
        f"from xstate_statemachine import create_machine, {interp_import}"
    )
    code_lines.extend(["import json", "import logging"])

    if sleep:
        code_lines.append("import time")
    if is_async:
        code_lines.append("import asyncio")

    # --- Logging Setup ---
    if log:
        code_lines.extend(
            [
                "",
                "logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')",
                "logger = logging.getLogger(__name__)",
            ]
        )

    # --- Logic Import ---
    if file_count == 2:
        base_name = (
            "_".join(machine_names)
            if len(machine_names) > 1
            else machine_names[0]
        )
        logic_file_name = f"{base_name}_logic"
        if style == "class":
            class_name = (
                "".join(word.capitalize() for word in base_name.split("_"))
                + "Logic"
            )
            logic_import = (
                f"from {logic_file_name} import {class_name} as LogicProvider"
            )
        else:
            logic_import = f"import {logic_file_name}"
        code_lines.extend(["", logic_import])

    func_prefix = "async " if is_async else ""
    await_prefix = "await " if is_async else ""

    def _generate_simulation_block(
        config: Dict[str, Any], json_filename: str
    ) -> List[str]:
        """Generates the code for a single machine's simulation."""
        lines = [
            "",
            "# --------------------------------------------------------------------------",
            "# 📂 1. Configuration Loading",
            "# --------------------------------------------------------------------------",
            f"config_path = Path(__file__).parent / '{json_filename}'",
            "with open(config_path, 'r', encoding='utf-8') as f:",  # noqa
            "    config = json.load(f)",
            "",
            "# --------------------------------------------------------------------------",
            "# 🧠 2. Logic Binding",
            "# --------------------------------------------------------------------------",
        ]
        if loader:
            if style == "class":
                lines.extend(
                    [
                        "logic_provider = LogicProvider()",
                        "machine = create_machine(config, logic_providers=[logic_provider])",
                    ]
                )
            else:
                lines.append(
                    f"machine = create_machine(config, logic_modules=[{logic_file_name}])"
                )
        else:
            # Import MachineLogic only when needed to avoid unused import warnings
            lines.insert(4, "from xstate_statemachine import MachineLogic")
            lines.extend(
                [
                    "# TODO: Fill actions, guards, services",
                    "machine_logic = MachineLogic(actions={}, guards={}, services={})",
                    "machine = create_machine(config, logic=machine_logic)",
                ]
            )
        lines.extend(
            [
                "",
                "# --------------------------------------------------------------------------",
                "# ⚙️ 3. Interpreter Setup",
                "# --------------------------------------------------------------------------",
                f"interpreter = {interp_import}(machine)",
                "interpreter.use(LoggingInspector())",
                f"{await_prefix}interpreter.start()",
                'logger.info(f"Initial state: {{interpreter.current_state_ids}}")',
                "",
                "# --------------------------------------------------------------------------",
                "# 🚀 4. Simulation Scenario",
                "# --------------------------------------------------------------------------",
                "logger.info('--- Kicking off simulation... ---')",
            ]
        )
        dummy_event = next(iter(config.get("on", {})), "PEDESTRIAN_WAITING")
        lines.extend(
            [
                f"logger.info('→ Sending initial event: {dummy_event}')",
                f"{await_prefix}interpreter.send('{dummy_event}')",
            ]
        )
        if sleep:
            lines.append(f"time.sleep({sleep_time})")

        lines.extend(
            [
                "logger.info(f'--- ✅ Simulation ended in state: {{interpreter.current_state_ids}} ---')",
                f"{await_prefix}interpreter.stop()",
            ]
        )
        return lines

    if len(machine_names) == 1:
        name = machine_names[0]
        code_lines.extend(
            [
                "",
                f"{func_prefix}def main() -> None:",
                f'    """Executes the simulation for the {name} machine."""',
            ]
        )
        sim_lines = _generate_simulation_block(configs[0], json_filenames[0])
        code_lines.extend([f"    {line}" for line in sim_lines])
    else:  # Multiple machines
        for idx, name in enumerate(machine_names):
            code_lines.extend(
                [
                    "",
                    f"{func_prefix}def run_{name}() -> None:",
                    f'    """Executes the simulation for the {name} machine."""',
                ]
            )
            sim_lines = _generate_simulation_block(
                configs[idx], json_filenames[idx]
            )
            code_lines.extend([f"    {line}" for line in sim_lines])

        code_lines.extend(
            [
                "",
                f"{func_prefix}def main() -> None:",
                '    """Runs all machine simulations."""',
            ]
        )
        for name in machine_names:
            code_lines.append(f"    {await_prefix}run_{name}()")
            code_lines.append("")

    # --- Main execution block ---
    main_runner = "asyncio.run(main())" if is_async else "main()"
    code_lines.extend(["", "if __name__ == '__main__':", f"    {main_runner}"])
    return "\n".join(code_lines)


# -----------------------------------------------------------------------------
# 🚀 Main CLI Entrypoint
# -----------------------------------------------------------------------------


def main():
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
        # 📂 Collect and load all JSON configuration files
        json_paths = args.json_files + args.json
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
        )

        # 💾 Write generated code to file(s)
        if args.file_count == 1:
            if single_file:
                logger.info(f"💾 Writing combined code to: {single_file}")
                combined_code = (
                    f"{logic_code}\n\n\n# Runner part\n{runner_code}"
                )
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
