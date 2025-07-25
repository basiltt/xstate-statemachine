# src/xstate_statemachine/cli/__main__.py
# -----------------------------------------------------------------------------
# 🏛️ Command-Line Interface (CLI) - Main Entry Point
# -----------------------------------------------------------------------------
# This module provides the main entry point for the xstate-statemachine CLI.
# It orchestrates the entire code generation process by:
#   1. Setting up and parsing command-line arguments via the `args` module.
#   2. Loading and validating JSON machine configuration files.
#   3. Calling the `extractor` module to gather necessary data.
#   4. Invoking the `generator` module to produce the final Python source files.
#   5. Writing the generated code to the filesystem.
# This modular approach ensures the main logic is clean, readable, and
# easy to maintain.
# -----------------------------------------------------------------------------
"""
Main entry point for the xstate-statemachine CLI, runnable via `python -m`.
"""
# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Set

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .args import get_parser, validate_args
from .extractor import extract_logic_names
from .generator import generate_logic_code, generate_runner_code
from .utils import camel_to_snake, normalize_bool

# -----------------------------------------------------------------------------
# 🧾Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


def main():  # noqa: C901 - This function orchestrates the entire CLI logic.
    """Parses command-line arguments and orchestrates code generation."""
    parser = get_parser()
    validate_args(parser)
    args = parser.parse_args()

    if args.subcommand == "generate-template":
        # 📂 Collect and *order* JSON files
        json_paths: List[str] = []
        if args.json_parent:
            json_paths.append(args.json_parent)
        else:
            json_paths.extend(args.json_files)

        json_paths.extend(args.json_child)
        if args.json_parent:
            json_paths.extend(args.json_files)
        json_paths.extend(args.json)

        # 🛑 Sanity checks for parent/child flags
        if args.json_child and not (
            args.json_parent or args.json_files or args.json
        ):
            logger.error("❌ --json-child requires a parent machine JSON.")
            parser.error("--json-child requires a parent machine JSON.")

        # 🔄 De-duplicate while preserving order
        seen: Set[str] = set()
        unique_json_paths = [
            p for p in json_paths if not (p in seen or seen.add(p))
        ]
        if not unique_json_paths:
            logger.error("❌ No JSON files provided. Aborting.")
            parser.error("At least one JSON file is required.")

        json_paths = unique_json_paths
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

        # 🤖 Heuristic parent detection & optional prompt
        hierarchy_flag = False
        if (
            not args.json_parent
            and not args.json_child
            and len(json_paths) > 1
        ):
            ids = [
                conf.get("id", fn.stem)
                for conf, fn in zip(configs, map(Path, json_paths))
            ]
            # --- simple reference-count heuristic ---
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

            max_score: int = max(ref_scores) if ref_scores else 0
            candidate_idx: int = -1
            if max_score > 0:
                candidate_idx = ref_scores.index(max_score)
            else:
                candidate_idx = 0  # Tie-breaker: pick first listed

            # --- interactive confirmation / selection ---
            if candidate_idx > -1:
                confidence = int(round(100 * max_score / (len(ids) - 1)))
                print(
                    "Found two machines:"
                    if len(ids) == 2
                    else f"Found {len(ids)} machines:"
                )
                for i, mid in enumerate(ids, 1):
                    if i - 1 == candidate_idx:
                        print(
                            f"  {i}. {mid} (looks like parent, confidence {confidence} %)"
                        )
                    else:
                        print(f"  {i}. {mid} (looks like child)")
                answer = input("Is this correct?  [Y/n] ").strip().lower()
                if answer in ("", "y", "yes"):
                    hierarchy_flag = True
                else:
                    candidate_idx = -1

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

            # --- reorder lists so that parent is *first* ---
            if hierarchy_flag and candidate_idx != 0:
                for lst in (
                    json_paths,
                    configs,
                    machine_names,
                    json_filenames,
                ):
                    lst.insert(0, lst.pop(candidate_idx))

        if args.json_parent or args.json_child:
            hierarchy_flag = True

        # 📁 Determine output directory and file paths
        out_dir = (
            Path(args.output) if args.output else Path(json_paths[0]).parent
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        # 📛 File naming
        if hierarchy_flag and len(machine_names) > 1:
            base_name = machine_names[0]
        else:
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
            files_to_check = (
                [single_file]
                if args.file_count == 1
                else [logic_file, runner_file]
            )
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
            args.file_count,
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
            hierarchy=hierarchy_flag,
        )

        # 💾 Write generated code to file(s)
        if args.file_count == 1:
            if single_file:
                logger.info(f"💾 Writing combined code to: {single_file}")
                # ---- Merge *intelligently* so imports/logger appear only once ----
                logic_lines = logic_code.splitlines()
                runner_lines = runner_code.splitlines()

                seen_imports: Set[str] = {
                    ln
                    for ln in logic_lines
                    if ln.startswith(("import ", "from "))
                }

                extra_imports: List[str] = [
                    ln
                    for ln in runner_lines
                    if ln.startswith(("import ", "from "))
                    and ln not in seen_imports
                ]

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

                if log_bool and not any(
                    "logging.basicConfig" in ln for ln in merged
                ):
                    insert_at = (
                        max(
                            idx
                            for idx, ln in enumerate(merged)
                            if ln.startswith(("import ", "from "))
                        )
                        + 1
                    )
                    for ln in runner_lines:
                        if ln.startswith("logging.basicConfig"):
                            merged.insert(insert_at, ln)
                            break

                if log_bool and not any(
                    "logger = logging.getLogger" in line_ for line_ in merged
                ):
                    merged.append("logger = logging.getLogger(__name__)")

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


if __name__ == "__main__":
    main()
