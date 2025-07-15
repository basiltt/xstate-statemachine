# src/xstate_statemachine/cli.py
# -------------------------------------------------------------------------------
# 📡 CLI Tool for Generating Boilerplate Templates
# -------------------------------------------------------------------------------
"""
Command-line interface for generating xstate-statemachine boilerplate.

Usage:
    xstate-statemachine generate-template [OPTIONS] [JSON_FILES...]

This tool reads one or more JSON state machine configurations and generates
corresponding logic and runner files. It supports various styles and options
for customization.

Examples:
    xstate-statemachine generate-template machine.json
    xstate-statemachine generate-template --style function --async-mode no machine1.json machine2.json
    xstate-statemachine generate-template --json machine.json --output ./generated --force
"""

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Set, Any

from . import __version__ as package_version

logger = logging.getLogger(__name__)


def extract_logic_names(  # noqa C901
    config: Dict[str, Any],
) -> tuple[Set[str], Set[str], Set[str]]:
    """Extracts unique action, guard, and service names from a machine config."""
    actions: Set[str] = set()
    guards: Set[str] = set()
    services: Set[str] = set()

    def traverse(node: Dict[str, Any]):
        # Actions from entry/exit
        for key in ["entry", "exit"]:
            if key in node:
                acts = (
                    node[key] if isinstance(node[key], list) else [node[key]]
                )
                for act in acts:
                    if isinstance(act, str):
                        actions.add(act)
                    elif isinstance(act, dict) and "type" in act:
                        actions.add(act["type"])

        # Transitions
        if "on" in node:
            for trans_dict in node["on"].values():
                trans_list = (
                    trans_dict
                    if isinstance(trans_dict, list)
                    else [trans_dict]
                )
                for trans in trans_list:
                    if "actions" in trans:
                        acts = (
                            trans["actions"]
                            if isinstance(trans["actions"], list)
                            else [trans["actions"]]
                        )
                        for act in acts:
                            if isinstance(act, str):
                                actions.add(act)
                            elif isinstance(act, dict) and "type" in act:
                                actions.add(act["type"])
                    guard_key = (
                        "cond"
                        if "cond" in trans
                        else "guard" if "guard" in trans else None
                    )
                    if guard_key:
                        guards.add(trans[guard_key])

        # Invoke
        if "invoke" in node:
            invokes = (
                node["invoke"]
                if isinstance(node["invoke"], list)
                else [node["invoke"]]
            )
            for invoke in invokes:
                if "src" in invoke:
                    services.add(invoke["src"])
                for key in ["onDone", "onError"]:
                    if key in invoke:
                        trans = invoke[key]
                        trans = trans if isinstance(trans, list) else [trans]
                        for t in trans:
                            if "actions" in t:
                                acts = (
                                    t["actions"]
                                    if isinstance(t["actions"], list)
                                    else [t["actions"]]
                                )
                                for act in acts:
                                    if isinstance(act, str):
                                        actions.add(act)
                                    elif (
                                        isinstance(act, dict) and "type" in act
                                    ):
                                        actions.add(act["type"])
                            guard_key = (
                                "cond"
                                if "cond" in t
                                else "guard" if "guard" in t else None
                            )
                            if guard_key:
                                guards.add(t[guard_key])

        # After
        if "after" in node:
            for _, trans_list in node["after"].items():
                trans_list = (
                    trans_list
                    if isinstance(trans_list, list)
                    else [trans_list]
                )
                for trans in trans_list:
                    if "actions" in trans:
                        acts = (
                            trans["actions"]
                            if isinstance(trans["actions"], list)
                            else [trans["actions"]]
                        )
                        for act in acts:
                            if isinstance(act, str):
                                actions.add(act)
                            elif isinstance(act, dict) and "type" in act:
                                actions.add(act["type"])
                    guard_key = (
                        "cond"
                        if "cond" in trans
                        else "guard" if "guard" in trans else None
                    )
                    if guard_key:
                        guards.add(trans[guard_key])

        # Recurse into states
        if "states" in node:
            for subnode in node["states"].values():
                traverse(subnode)

    traverse(config)
    return actions, guards, services


def generate_logic_code(
    actions: Set[str],
    guards: Set[str],
    services: Set[str],
    style: str,
    log: bool,
    is_async: bool,
    machine_name: str,
) -> str:
    """Generates the logic file content based on extracted names and options."""
    code = """# -------------------------------------------------------------------------------
# 📡 Generated Logic File
# -------------------------------------------------------------------------------
"""
    if is_async:
        code += "import asyncio\n"
        code += "from typing import Awaitable\n"
    code += "import logging\nfrom typing import Any, Dict\n\n"
    code += "from xstate_statemachine import Interpreter, SyncInterpreter, Event, ActionDefinition\n\n"
    code += "# -----------------------------------------------------------------------------\n"
    code += "# 🪵 Logger Configuration\n"
    code += "# -----------------------------------------------------------------------------\n"
    code += "logger = logging.getLogger(__name__)\n\n"

    class_indent = ""
    func_self = ""
    base_name = machine_name.replace("_", "").capitalize() + "Logic"
    if style == "class":
        code += "# -----------------------------------------------------------------------------\n"
        code += "# 🧠 Class-based Logic\n"
        code += "# -----------------------------------------------------------------------------\n"
        code += f"class {base_name}:\n"
        class_indent = "    "
        func_self = "self, "

    # Actions section
    code += f"{class_indent}# -----------------------------------------------------------------------------\n"
    code += f"{class_indent}# ⚙️ Actions\n"
    code += f"{class_indent}# -----------------------------------------------------------------------------\n"
    for act in sorted(actions):
        async_prefix = "async " if is_async else ""
        ret_type = " Awaitable[None]" if is_async else " None"
        code += f"{class_indent}{async_prefix}def {act}({func_self}interpreter: Interpreter if {is_async} else SyncInterpreter, context: Dict[str, Any], event: Event, action_def: ActionDefinition) ->{ret_type}:\n"
        inner_indent = class_indent + "    "
        code += f'{inner_indent}"""Action: {act}."""\n'
        if log:
            code += f'{inner_indent}logger.info("Executing action {act}")\n'
        if is_async:
            code += f"{inner_indent}await asyncio.sleep(0.1)  # Dummy async\n"
        code += f"{inner_indent}pass  # TODO: Implement action\n\n"

    # Guards section
    code += f"{class_indent}# -----------------------------------------------------------------------------\n"
    code += f"{class_indent}# 🛡️ Guards\n"
    code += f"{class_indent}# -----------------------------------------------------------------------------\n"
    for g in sorted(guards):
        code += f"{class_indent}def {g}({func_self}context: Dict[str, Any], event: Event) -> bool:\n"
        inner_indent = class_indent + "    "
        code += f'{inner_indent}"""Guard: {g}."""\n'
        if log:
            code += f'{inner_indent}logger.info("Evaluating guard {g}")\n'
        code += f"{inner_indent}return True  # TODO: Implement guard\n\n"

    # Services section
    code += f"{class_indent}# -----------------------------------------------------------------------------\n"
    code += f"{class_indent}# 🔄 Services\n"
    code += f"{class_indent}# -----------------------------------------------------------------------------\n"
    for s in sorted(services):
        async_prefix = "async " if is_async else ""
        ret_type = (
            " Awaitable[Dict[str, Any]]" if is_async else " Dict[str, Any]"
        )
        code += f"{class_indent}{async_prefix}def {s}({func_self}interpreter: Interpreter if {is_async} else SyncInterpreter, context: Dict[str, Any], event: Event) ->{ret_type}:\n"
        inner_indent = class_indent + "    "
        code += f'{inner_indent}"""Service: {s}."""\n'
        if log:
            code += f'{inner_indent}logger.info("Running service {s}")\n'
        if is_async:
            code += f"{inner_indent}await asyncio.sleep(1)\n"
        else:
            code += f"{inner_indent}time.sleep(1)\n"
        code += f"{inner_indent}return {{'result': 'done'}}  # TODO: Implement service\n\n"

    return code


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
    """Generates the runner file content based on options."""
    code = """# -------------------------------------------------------------------------------
# 📡 Generated Runner File
# -------------------------------------------------------------------------------
from pathlib import Path
from xstate_statemachine import LoggingInspector
from xstate_statemachine import create_machine, """
    code += "Interpreter\n" if is_async else "SyncInterpreter\n"
    code += "import json\nimport logging\n"
    if sleep:
        code += "import time\n"
    if is_async:
        code += "import asyncio\n\n"
    if log:
        code += "logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')\n"
        code += "logger = logging.getLogger(__name__)\n\n"

    if file_count == 2:
        if len(machine_names) == 1:
            machine_name = machine_names[0]
            logic_file_name = f"{machine_name}_logic"
            class_name = machine_name.replace("_", "").capitalize() + "Logic"
            if style == "class":
                logic_import = f"from {logic_file_name} import {class_name} as LogicProvider\n"
            else:
                logic_import = f"import {logic_file_name}\n"
        else:
            if style == "class":
                logic_import = "from generated_logic import GeneratedLogic as LogicProvider\n"
            else:
                logic_import = "import generated_logic\n"
        code += logic_import + "\n"

    if len(machine_names) == 1:
        name = machine_names[0]
        config = configs[0]
        json_filename = json_filenames[0]
        code += "def main() -> None:\n"
        inner_indent = "    "
        code += f'{inner_indent}"""Executes the simulation for the {name} machine."""\n\n'
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        code += f"{inner_indent}# 📂 1. Configuration Loading\n"
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        code += f"{inner_indent}config_path = Path(__file__).parent / '{json_filename}'\n"
        code += f"{inner_indent}with open(config_path, 'r', encoding='utf-8') as f:\n"
        code += f"{inner_indent}{inner_indent}config = json.load(f)\n\n"
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        code += f"{inner_indent}# 🧠 2. Logic Binding\n"
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        if loader:
            if style == "class":
                code += f"{inner_indent}logic_provider = LogicProvider()\n"
                code += f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])\n\n"
            else:
                code += f"{inner_indent}machine = create_machine(config, logic_modules=[{logic_file_name}])\n\n"
        else:
            code += f"{inner_indent}# TODO: Fill actions, guards, services\n"
            code += f"{inner_indent}machine_logic = MachineLogic(actions={{}}, guards={{}}, services={{}})\n"
            code += f"{inner_indent}machine = create_machine(config, logic=machine_logic)\n\n"
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        code += f"{inner_indent}# ⚙️ 3. Interpreter Setup\n"
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        interp_type = (
            "Interpreter(machine)" if is_async else "SyncInterpreter(machine)"
        )
        code += f"{inner_indent}interpreter = {interp_type}\n"
        code += f"{inner_indent}interpreter.use(LoggingInspector())\n"
        await_prefix = "await " if is_async else ""
        code += f"{inner_indent}{await_prefix}interpreter.start()\n"
        code += f'{inner_indent}logger.info(f"Initial state: {{interpreter.current_state_ids}}")\n\n'
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        code += f"{inner_indent}# 🚀 4. Simulation Scenario\n"
        code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
        code += (
            f"{inner_indent}logger.info('--- Kicking off simulation... ---')\n"
        )
        dummy_event = next(iter(config.get("on", {})), "PEDESTRIAN_WAITING")
        code += f"{inner_indent}logger.info('→ Sending initial event: {dummy_event}')\n"
        code += f"{inner_indent}interpreter.send('{dummy_event}')\n"
        if sleep:
            code += f"{inner_indent}time.sleep({sleep_time})\n"
        code += f"{inner_indent}logger.info(f'--- ✅ Simulation ended in state: {{interpreter.current_state_ids}} ---')\n"
        code += f"{inner_indent}{await_prefix}interpreter.stop()\n\n"
        if is_async:
            code += "if __name__ == '__main__':\n    asyncio.run(main())\n"
        else:
            code += "if __name__ == '__main__':\n    main()\n"
    else:
        for idx, name in enumerate(machine_names):
            config = configs[idx]
            json_filename = json_filenames[idx]
            func_prefix = "async " if is_async else ""
            code += f"{func_prefix}def run_{name}() -> None:\n"
            inner_indent = "    "
            code += f'{inner_indent}"""Executes the simulation for the {name} machine."""\n\n'
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            code += f"{inner_indent}# 📂 1. Configuration Loading\n"
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            code += f"{inner_indent}config_path = Path(__file__).parent / '{json_filename}'\n"
            code += f"{inner_indent}with open(config_path, 'r', encoding='utf-8') as f:\n"
            code += f"{inner_indent}{inner_indent}config = json.load(f)\n\n"
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            code += f"{inner_indent}# 🧠 2. Logic Binding\n"
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            if loader:
                if style == "class":
                    code += f"{inner_indent}logic_provider = LogicProvider()\n"
                    code += f"{inner_indent}machine = create_machine(config, logic_providers=[logic_provider])\n\n"
                else:
                    code += f"{inner_indent}machine = create_machine(config, logic_modules=[generated_logic])\n\n"
            else:
                code += (
                    f"{inner_indent}# TODO: Fill actions, guards, services\n"
                )
                code += f"{inner_indent}machine_logic = MachineLogic(actions={{}}, guards={{}}, services={{}})\n"
                code += f"{inner_indent}machine = create_machine(config, logic=machine_logic)\n\n"
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            code += f"{inner_indent}# ⚙️ 3. Interpreter Setup\n"
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            interp_type = (
                "Interpreter(machine)"
                if is_async
                else "SyncInterpreter(machine)"
            )
            code += f"{inner_indent}interpreter = {interp_type}\n"
            code += f"{inner_indent}interpreter.use(LoggingInspector())\n"
            await_prefix = "await " if is_async else ""
            code += f"{inner_indent}{await_prefix}interpreter.start()\n"
            code += f'{inner_indent}logger.info(f"Initial state: {{interpreter.current_state_ids}}")\n\n'
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            code += f"{inner_indent}# 🚀 4. Simulation Scenario\n"
            code += f"{inner_indent}# ---------------------------------------------------------------------------\n"
            code += f"{inner_indent}logger.info('--- Kicking off simulation... ---')\n"
            dummy_event = next(iter(config.get("on", {})), "EVENT1")
            code += f"{inner_indent}logger.info('→ Sending initial event: {dummy_event}')\n"
            code += f"{inner_indent}interpreter.send('{dummy_event}')\n"
            if sleep:
                code += f"{inner_indent}time.sleep({sleep_time})\n"
            code += f"{inner_indent}logger.info(f'--- ✅ Simulation ended in state: {{interpreter.current_state_ids}} ---')\n"
            code += f"{inner_indent}{await_prefix}interpreter.stop()\n\n"

        func_prefix = "async " if is_async else ""
        code += f"{func_prefix}def main() -> None:\n"
        inner_indent = "    "
        for name in machine_names:
            await_prefix = "await " if is_async else ""
            code += f"{inner_indent}{await_prefix}run_{name}()\n\n"
        if is_async:
            code += "if __name__ == '__main__':\n    asyncio.run(main())\n"
        else:
            code += "if __name__ == '__main__':\n    main()\n"

    return code


def normalize_bool(value: str) -> bool:
    """Normalizes string to bool, case-insensitive."""
    true_values = {"true", "yes", "y", "1"}
    false_values = {"false", "no", "n", "0"}
    lower = value.lower()
    if lower in true_values:
        return True
    if lower in false_values:
        return False
    raise ValueError(f"Invalid bool value: {value}")


def main():
    parser = argparse.ArgumentParser(
        description="xstate-statemachine CLI tool.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {package_version}"
    )

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    gen_parser = subparsers.add_parser(
        "generate-template",
        help="Generate boilerplate templates from JSON configs.",
    )
    gen_parser.add_argument(
        "json_files", nargs="*", help="JSON config files to process."
    )
    gen_parser.add_argument(
        "--json",
        action="append",
        default=[],
        help="Additional JSON config file.",
    )
    gen_parser.add_argument(
        "--style",
        choices=["class", "function"],
        default="class",
        help="Code style: class or function (default: class)",
    )
    gen_parser.add_argument(
        "--loader",
        default="yes",
        help="Use logic loader: yes or no (default: yes)",
    )
    gen_parser.add_argument(
        "--file-count",
        type=int,
        choices=[1, 2],
        default=2,
        help="Number of files: 1 (combined) or 2 (separate) (default: 2)",
    )
    gen_parser.add_argument(
        "--output", help="Output directory (default: same as first JSON)"
    )
    gen_parser.add_argument(
        "--sleep",
        default="yes",
        help="Add sleep in runner: yes or no (default: yes)",
    )
    gen_parser.add_argument(
        "--async-mode",
        default="yes",
        help="Generate async code: yes or no (default: yes)",
    )
    gen_parser.add_argument(
        "--sleep-time",
        type=int,
        default=2,
        help="Sleep time in seconds (default: 2)",
    )
    gen_parser.add_argument(
        "--log",
        default="yes",
        help="Add logging in functions: yes or no (default: yes)",
    )
    gen_parser.add_argument(
        "--force", action="store_true", help="Force overwrite existing files."
    )

    args = parser.parse_args()

    if args.subcommand == "generate-template":

        # Collect all JSON paths
        json_paths = args.json_files + args.json
        if not json_paths:
            parser.error("At least one JSON file is required.")

        # Load configs and extract names
        configs = []
        all_actions = set()
        all_guards = set()
        all_services = set()
        machine_names = []
        json_filenames = []
        for jp in json_paths:
            path = Path(jp)
            if not path.exists():
                parser.error(f"JSON file not found: {jp}")
            with open(path, "r") as f:
                conf = json.load(f)
            name = conf.get("id", path.stem).replace(" ", "_").lower()
            machine_names.append(name)
            configs.append(conf)
            json_filenames.append(path.name)
            a, g, s = extract_logic_names(conf)
            all_actions.update(a)
            all_guards.update(g)
            all_services.update(s)

        # Determine output dir
        out_dir = (
            Path(args.output) if args.output else Path(json_paths[0]).parent
        )
        out_dir.mkdir(parents=True, exist_ok=True)

        # File names
        base_name = (
            "_".join(machine_names)
            if len(machine_names) > 1
            else machine_names[0]
        )
        logic_file = out_dir / f"{base_name}_logic.py"
        runner_file = out_dir / f"{base_name}_runner.py"
        single_file = (
            out_dir / f"{base_name}.py" if args.file_count == 1 else None
        )

        # Normalize options
        loader_bool = normalize_bool(args.loader)
        sleep_bool = normalize_bool(args.sleep)
        async_bool = normalize_bool(args.async_mode)
        log_bool = normalize_bool(args.log)

        # Force overwrite
        if args.force:
            if single_file:
                single_file.unlink(missing_ok=True)
            else:
                logic_file.unlink(missing_ok=True)
                runner_file.unlink(missing_ok=True)

        # Generate code
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

        if args.file_count == 1:
            combined_code = logic_code + "\n\n# Runner part\n" + runner_code
            single_file.write_text(combined_code, encoding="utf-8")
            print(f"Generated combined file: {single_file}")
        else:
            logic_file.write_text(logic_code, encoding="utf-8")
            runner_file.write_text(runner_code, encoding="utf-8")
            print(f"Generated logic file: {logic_file}")
            print(f"Generated runner file: {runner_file}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
