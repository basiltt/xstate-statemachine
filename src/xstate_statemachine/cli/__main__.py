# src/xstate_statemachine/cli/__main__.py
# -----------------------------------------------------------------------------
# 🏛️ Command-Line Interface (CLI) - Main Entry Point
# -----------------------------------------------------------------------------
# This module serves as the main entry point for the xstate-statemachine CLI.
# It orchestrates the code generation process by following a clean,
# sequential workflow:
#
#   1. ⚙️ Parse and validate command-line arguments.
#   2. 📂 Load, parse, and validate the input JSON machine definitions.
#   3. 🤝 Determine machine hierarchy, either automatically or interactively.
#   4. 📜 Generate the state machine logic and runner code in memory.
#   5. 💾 Write the generated code to the appropriate files on disk.
#
# The logic is decomposed into small, single-responsibility helper functions
# to enhance modularity, testability, and maintainability, following SOLID
# and DRY principles.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
# Assuming these modules exist in the same directory (`.`) as per the original.
from .args import get_parser, validate_args
from .extractor import extract_logic_names, guess_hierarchy
from .generator import generate_logic_code, generate_runner_code
from .utils import camel_to_snake, normalize_bool

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
# A single logger instance for consistent logging across the module.
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 📁 Path & File Helpers
# -----------------------------------------------------------------------------
# Functions responsible for handling file paths, reading from, and writing to
# the filesystem. Each has a distinct, single responsibility.
# -----------------------------------------------------------------------------


def _get_validated_json_paths(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> List[str]:
    """Collects, de-duplicates, and validates all input JSON file paths.

    It respects the hierarchy flags (--json-parent, --json-child) to establish
    an initial order before de-duplicating.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
        parser (argparse.ArgumentParser): The parser instance for error reporting.

    Returns:
        List[str]: An ordered, unique list of validated JSON file paths.

    Raises:
        SystemExit: If no JSON files are provided or if a child is specified
                    without a parent.
    """
    logger.info("📂 Validating and collecting input file paths...")
    # 🗂️ Collect paths in order: parent, standard, children
    json_paths: List[str] = []
    if args.json_parent:
        json_paths.append(args.json_parent)
    json_paths.extend(args.json)
    json_paths.extend(args.json_files)
    json_paths.extend(args.json_child)

    # 🛑 Validate that a child machine is not specified without a parent
    has_children = bool(args.json_child)
    has_parent = bool(args.json_parent or args.json or args.json_files)
    if has_children and not has_parent:
        err_msg = "--json-child requires a parent machine JSON."
        logger.error(f"❌ {err_msg}")
        parser.error(err_msg)

    # 🔄 De-duplicate paths while preserving the specified order
    seen: Set[str] = set()
    unique_paths = [p for p in json_paths if not (p in seen or seen.add(p))]

    if not unique_paths:
        logger.error("❌ No JSON files provided. Aborting.")
        parser.error("At least one JSON file is required.")

    logger.info(
        f"✅ Found {len(unique_paths)} unique JSON file(s) to process."
    )
    return unique_paths


def _determine_output_paths(
    args: argparse.Namespace,
    machine_names: List[str],
    hierarchy_flag: bool,
    json_paths: List[str],
) -> Dict[str, Path]:
    """Determines and creates the output directory and file paths.

    Args:
        args (argparse.Namespace): Parsed command-line arguments.
        machine_names (List[str]): List of snake_cased machine names.
        hierarchy_flag (bool): True if generating a hierarchical machine.
        json_paths (List[str]): List of input file paths to infer output dir.

    Returns:
        Dict[str, Path]: A dictionary mapping file types to their output Paths.
    """
    logger.info("🗺️ Determining output file paths...")
    # 📁 Define output directory (or infer it from the first JSON path)
    out_dir = Path(args.output) if args.output else Path(json_paths[0]).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # 📝 Determine the base filename for the output files
    if hierarchy_flag and len(machine_names) > 1:
        base_name = machine_names[0]  # Parent name
    else:
        base_name = "_".join(machine_names)

    paths = {
        "logic_file": out_dir / f"{base_name}_logic.py",
        "runner_file": out_dir / f"{base_name}_runner.py",
        "single_file": out_dir / f"{base_name}.py",
    }
    logger.info(f"✅ Output directory set to: {out_dir.resolve()}")
    return paths


def _write_output_files(
    file_count: int,
    paths: Dict[str, Path],
    logic_code: str,
    runner_code: str,
    log_bool: bool,
) -> None:
    """Writes the generated code strings to the appropriate files.

    Args:
        file_count (int): The number of files to generate (1 or 2).
        paths (Dict[str, Path]): A dictionary of output file paths.
        logic_code (str): The generated logic code.
        runner_code (str): The generated runner code.
        log_bool (bool): Flag indicating if logging is enabled, for merging.
    """
    logger.info("✍️ Writing generated code to disk...")
    if file_count == 1:
        # 🤝 Merge code into a single file
        combined_code = _merge_code_for_single_file(logic_code, runner_code)
        target_path = paths["single_file"]
        logger.info(f"💾 Writing combined code to: {target_path}")
        target_path.write_text(combined_code, encoding="utf-8")
        print(f"✅ Generated combined file: {target_path}")
    else:
        # ✌️ Write to separate logic and runner files
        logic_path, runner_path = paths["logic_file"], paths["runner_file"]
        logger.info(f"💾 Writing logic code to: {logic_path}")
        logic_path.write_text(logic_code, encoding="utf-8")
        logger.info(f"💾 Writing runner code to: {runner_path}")
        runner_path.write_text(runner_code, encoding="utf-8")
        print(f"✅ Generated logic file: {logic_path}")
        print(f"✅ Generated runner file: {runner_path}")


# -----------------------------------------------------------------------------
# ⚙️ Data Processing & Configuration Helpers
# -----------------------------------------------------------------------------
# Functions for loading, parsing, and processing the machine data from JSON.
# -----------------------------------------------------------------------------


def _process_all_configurations(
    json_paths: List[str], parser: argparse.ArgumentParser
) -> Tuple[
    List[Dict[str, Any]],
    List[str],
    List[str],
    List[str],
    Set[str],
    Set[str],
    Set[str],
]:
    """Loads JSON configs, extracts names, and aggregates all logic components.

    This function iterates through each JSON path, loading and processing it
    to build comprehensive lists of configurations and their associated logic.

    Args:
        json_paths (List[str]): The list of file paths to load.
        parser (argparse.ArgumentParser): The parser instance for error reporting.

    Returns:
        Tuple containing:
        - List[Dict[str, Any]]: Raw configurations.
        - List[str]: Original machine IDs.
        - List[str]: snake_cased machine names.
        - List[str]: JSON base filenames.
        - Set[str]: All unique action names.
        - Set[str]: All unique guard names.
        - Set[str]: All unique service names.
    """
    logger.info("📜 Loading and parsing configuration files...")
    configs, machine_ids, machine_names, json_filenames = [], [], [], []
    all_actions, all_guards, all_services = set(), set(), set()

    for jp in json_paths:
        path = Path(jp)
        if not path.exists():
            logger.error(f"❌ JSON file not found: {jp}")
            parser.error(f"JSON file not found: {jp}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                conf = json.load(f)

            # 🧬 Extract logic names and metadata from the config
            raw_name = conf.get("id", path.stem)
            actions, guards, services = extract_logic_names(conf)

            # ➕ Aggregate results
            configs.append(conf)
            machine_ids.append(raw_name)
            machine_names.append(camel_to_snake(raw_name))
            json_filenames.append(path.name)
            all_actions.update(actions)
            all_guards.update(guards)
            all_services.update(services)

        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in file {jp}: {e}")
            parser.error(f"Invalid JSON in file {jp}: {e}")
        except Exception as e:
            logger.error(f"❌ Could not process file {jp}: {e}")
            parser.error(f"Could not process file {jp}: {e}")

    logger.info("✅ Configurations loaded and initial logic extracted.")
    return (
        configs,
        machine_ids,
        machine_names,
        json_filenames,
        all_actions,
        all_guards,
        all_services,
    )


def _parse_boolean_flags(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> Dict[str, bool]:
    """Parses all string boolean arguments into actual booleans.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
        parser (argparse.ArgumentParser): The parser instance for error reporting.

    Returns:
        Dict[str, bool]: A dictionary mapping flag names to their boolean values.
    """
    try:
        return {
            "loader": normalize_bool(args.loader),
            "sleep": normalize_bool(args.sleep),
            "async_mode": normalize_bool(args.async_mode),
            "log": normalize_bool(args.log),
        }
    except ValueError as e:
        parser.error(str(e))


# -----------------------------------------------------------------------------
# 🤝 Hierarchy & Interaction Helpers
# -----------------------------------------------------------------------------
# Functions dedicated to managing machine hierarchy, including interactive
# prompts for user validation.
# -----------------------------------------------------------------------------


def _reorder_lists_by_parent_index(
    data_lists: List[List[Any]], parent_index: int
) -> List[List[Any]]:
    """Reorders a collection of lists to place the parent element first.

    Args:
        data_lists (List[List[Any]]): A list of lists to be reordered in unison.
        parent_index (int): The index of the parent element.

    Returns:
        List[List[Any]]: The reordered lists.
    """
    if parent_index != 0:
        for lst in data_lists:
            lst.insert(0, lst.pop(parent_index))
    return data_lists


def _handle_interactive_hierarchy(
    data_tuple: Tuple[List, ...],
) -> Tuple[bool, Tuple[List, ...]]:
    """Manages the interactive prompt for heuristic parent detection.

    Args:
        data_tuple (Tuple[List, ...]): A tuple containing lists to be managed:
            (configs, machine_ids, machine_names, json_paths, json_filenames)

    Returns:
        A tuple containing:
        - bool: The final hierarchy flag.
        - Tuple[List, ...]: The input lists, potentially reordered.
    """
    configs, machine_ids, machine_names, json_paths, json_filenames = (
        data_tuple
    )
    path_to_id_map = dict(zip(json_paths, machine_ids))
    parent_path, _, scores = guess_hierarchy(json_paths)
    final_parent_path = None

    print(f"Found {len(machine_ids)} machines:")
    # FIX: Use the exact wording the test suite expects for the prompt.
    for i, (path, score) in enumerate(scores):
        display_id = path_to_id_map.get(path, Path(path).stem)
        if path == parent_path:
            print(
                f"  {i + 1}. {display_id} (looks like parent, score: {score})"
            )
        else:
            print(
                f"  {i + 1}. {display_id} (looks like child, score: {score})"
            )

    answer = input("Is this correct? [Y/n] ").strip().lower()

    if answer in ("", "y", "yes"):
        final_parent_path = parent_path
    else:
        print("\nWhich machine is the parent?")
        for i, name in enumerate(machine_ids):
            print(f"  {i + 1}. {name}")
        try:
            selection = int(input("Enter number (or 0 for none): ").strip())
            if 1 <= selection <= len(machine_ids):
                final_parent_path = json_paths[selection - 1]
        except (ValueError, IndexError):
            logger.warning(
                "⚠️ Invalid selection. Proceeding without hierarchy."
            )

    if final_parent_path:
        parent_index = json_paths.index(final_parent_path)
        logger.info(f"👑 Setting '{machine_ids[parent_index]}' as parent.")
        reordered_data = _reorder_lists_by_parent_index(
            list(data_tuple), parent_index
        )
        return True, tuple(reordered_data)

    return False, data_tuple


# -----------------------------------------------------------------------------
# 🧩 Code Generation & Merging Helpers
# -----------------------------------------------------------------------------
# Functions that assist in the final steps of code generation and file merging.
# -----------------------------------------------------------------------------


def _merge_code_for_single_file(logic_code: str, runner_code: str) -> str:
    """Intelligently merges logic and runner code into a single file string.

    It de-duplicates imports and logger configurations to create a clean,
    runnable single-file script.

    Args:
        logic_code (str): The generated logic code.
        runner_code (str): The generated runner code.

    Returns:
        str: The combined and cleaned code as a single string.
    """
    logic_lines = logic_code.splitlines()
    runner_lines = runner_code.splitlines()

    # 🕵️‍♂️ Find all unique import statements from both parts
    imports = sorted(
        list(
            set(
                line
                for line in logic_lines + runner_lines
                if line.strip().startswith(("import ", "from "))
            )
        )
    )

    # 🧠 Extract the logic part, skipping its imports.
    # The logic part should contain the logger definition.
    logic_body = [
        line
        for line in logic_lines
        if not line.strip().startswith(("import ", "from "))
    ]

    # 🏃 Extract the runner part, skipping imports and its own logger setup.
    runner_body = [
        line
        for line in runner_lines
        if not line.strip().startswith(
            ("import ", "from ", "logging.basicConfig")
        )
        and "logger = logging.getLogger" not in line
    ]

    # 🧩 Assemble the final merged code
    # Find header from the logic file
    header_lines = []
    for line in logic_lines:
        if line.strip().startswith("#") or not line.strip():
            header_lines.append(line)
        else:
            # Stop at the first actual code line
            break

    # Remove the header part from the logic body we extracted earlier
    logic_body_clean = logic_body[len(header_lines) :]

    final_lines = (
        header_lines
        + imports
        + [""]
        + logic_body_clean
        + ["", "# Runner part", ""]
        + runner_body
    )
    return "\n".join(final_lines)


# -----------------------------------------------------------------------------
# 🚀 Main Orchestrator
# -----------------------------------------------------------------------------
# The primary functions that drive the CLI execution flow.
# -----------------------------------------------------------------------------


def run_generation_workflow(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> None:
    """Orchestrates the entire code generation workflow from start to finish.

    Args:
        args (argparse.Namespace): The parsed command-line arguments.
        parser (argparse.ArgumentParser): The CLI parser for error handling.
    """
    # 1. 📂 Process and validate input file paths
    json_paths = _get_validated_json_paths(args, parser)

    # 2. ⚙️ Load and process all machine configurations
    (
        configs,
        machine_ids,
        machine_names,
        json_filenames,
        all_actions,
        all_guards,
        all_services,
    ) = _process_all_configurations(json_paths, parser)

    # 3. 🤝 Determine hierarchy
    hierarchy_flag = bool(args.json_parent or args.json_child)
    if not hierarchy_flag and len(json_paths) > 1:
        data_tuple = (
            configs,
            machine_ids,
            machine_names,
            json_paths,
            json_filenames,
        )
        hierarchy_flag, updated_data = _handle_interactive_hierarchy(
            data_tuple
        )
        (
            configs,
            machine_ids,
            machine_names,
            json_paths,
            json_filenames,
        ) = updated_data

    # 4. 🗺️ Determine output paths
    paths = _determine_output_paths(
        args, machine_names, hierarchy_flag, json_paths
    )

    # 5. 🛡️ Check for existing files before proceeding
    files_to_check = (
        [paths["single_file"]]
        if args.file_count == 1
        else [paths["logic_file"], paths["runner_file"]]
    )
    if not args.force and any(f.exists() for f in files_to_check):
        # Prompt the user for confirmation to overwrite existing files.
        answer = (
            input("File(s) already exist. Overwrite? [Y/n] ").strip().lower()
        )
        # If the user enters 'n' or 'no', abort the operation.
        # The default is 'yes', so pressing Enter will proceed.
        if answer in ("n", "no"):
            print("Operation cancelled.")
            return

    # 6. 🔧 Parse boolean settings from args
    settings = _parse_boolean_flags(args, parser)

    # 7. 📜 Generate logic and runner code
    logger.info("🤖 Generating logic and runner code...")
    base_name = Path(paths["single_file"].stem).name
    logic_code = generate_logic_code(
        all_actions,
        all_guards,
        all_services,
        args.style,
        settings["log"],
        settings["async_mode"],
        base_name,
        args.file_count,
    )
    runner_code = generate_runner_code(
        machine_names,
        settings["async_mode"],
        args.style,
        settings["loader"],
        settings["sleep"],
        args.sleep_time,
        settings["log"],
        args.file_count,
        configs,
        json_filenames,
        hierarchy=hierarchy_flag,
    )
    logger.info("✅ Code generation complete.")

    # 8. 💾 Write generated code to files
    _write_output_files(
        args.file_count, paths, logic_code, runner_code, settings["log"]
    )


def main() -> None:
    """Parses CLI arguments and orchestrates the code generation workflow."""
    parser = get_parser()
    args = parser.parse_args()
    validate_args(
        parser
    )  # Note: Assuming this validates args based on the parser state.

    if args.subcommand == "generate-template":
        run_generation_workflow(args, parser)
    else:
        # 🆘 Show help if no valid subcommand is given
        parser.print_help()


# -----------------------------------------------------------------------------
# 🎬 Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()
