# src/xstate_statemachine/cli/args.py
# -----------------------------------------------------------------------------
# ⚙️ Argument Parser Configuration
# -----------------------------------------------------------------------------
# This module centralizes the command-line argument parsing setup using the
# `argparse` library. Defining the parser in a separate module keeps the
# main entry point (`cli.py`) clean and focused on orchestration.
#
# It follows the Single Responsibility Principle by dedicating this file
# solely to defining the CLI's interface (commands, flags, and help messages),
# making it easier to manage and extend the available CLI options.
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import argparse
import logging
import sys
from typing import Optional

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from .. import __version__ as package_version
from .utils import normalize_bool

# -----------------------------------------------------------------------------
# 🪵 Module-level Logger
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Parser Helper Functions
# -----------------------------------------------------------------------------
# These functions encapsulate logical groups of arguments, keeping the main
# `get_parser` function clean and readable. Each function is responsible for
# adding a specific category of arguments to the provided parser.
# -----------------------------------------------------------------------------


def _add_file_input_args(parser: argparse.ArgumentParser) -> None:
    """
    Adds arguments related to file inputs and hierarchy to the parser.

    Args:
        parser (argparse.ArgumentParser): 🏛️ The parser to which arguments will be added.
    """
    # 📂 File & Hierarchy Inputs
    # This argument is now correctly defined as positional
    parser.add_argument(
        "json_files",
        nargs="*",
        help="One or more JSON config files to process as positional arguments.",
    )
    parser.add_argument(
        "-j",
        "--json",
        action="append",
        default=[],
        help="Specify a JSON file via a flag (can be used multiple times).",
    )
    parser.add_argument(
        "-jp",
        "--json-parent",
        metavar="PATH",
        help="Path to the JSON file that represents the *parent* machine in a hierarchy.",
    )
    parser.add_argument(
        "-jc",
        "--json-child",
        metavar="PATH",
        action="append",
        default=[],
        help="Path to a JSON file for a *child* (actor) machine (can be used multiple times).",
    )


def _add_generation_option_args(parser: argparse.ArgumentParser) -> None:
    """
    Adds arguments related to code generation style and output.

    Args:
        parser (argparse.ArgumentParser): 🏛️ The parser to which arguments will be added.
    """
    # 🎨 Code Generation & Output Options
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory for generated files (defaults to the location of the first input JSON).",
    )
    parser.add_argument(
        "-s",
        "--style",
        choices=["class", "function"],
        default=None,
        help=(
            "DEPRECATED: Use --template instead. "
            "Code style for logic: 'class' or 'function'."
        ),
    )
    parser.add_argument(
        "-t",
        "--template",
        choices=[
            "class-json",
            "function-json",
            "pythonic-class",
            "pythonic-builder",
            "pythonic-functional",
        ],
        default=None,
        help=(
            "Code generation template. Default: class-json. "
            "Replaces --style (deprecated)."
        ),
    )
    parser.add_argument(
        "-fc",
        "--file-count",
        type=int,
        choices=[1, 2],
        default=2,
        help="Number of output files: 1 (combined) or 2 (logic/runner). Default: 2.",
    )
    parser.add_argument(
        "-am",
        "--async-mode",
        default=None,
        help=(
            "Generate asynchronous code: 'yes' or 'no'. "
            "Default: 'yes' for JSON templates, 'no' for "
            "Pythonic templates."
        ),
    )
    parser.add_argument(
        "-l",
        "--loader",
        default="yes",
        help="Use the auto-discovery logic loader in the runner: 'yes' or 'no'. Default: yes.",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite of existing generated files without prompting.",
    )


def _add_simulation_option_args(parser: argparse.ArgumentParser) -> None:
    """
    Adds arguments related to the generated runner's simulation behavior.

    Args:
        parser (argparse.ArgumentParser): 🏛️ The parser to which arguments will be added.
    """
    # ⏯️ Simulation Behavior Options
    parser.add_argument(
        "--log",
        default="yes",
        help="Include logging statements in the generated code: 'yes' or 'no'. Default: yes.",
    )
    parser.add_argument(
        "--sleep",
        default="yes",
        help="Add a sleep call between events in the simulation: 'yes' or 'no'. Default: yes.",
    )
    parser.add_argument(
        "--sleep-time",
        type=int,
        default=2,
        help="Sleep duration in seconds for the simulation. Default: 2.",
    )


# -----------------------------------------------------------------------------
# 🏛️ Public API
# -----------------------------------------------------------------------------
# These functions are the primary interface for this module.
# -----------------------------------------------------------------------------


def get_parser() -> argparse.ArgumentParser:
    """
    Creates, configures, and returns the main argument parser for the CLI.

    This function orchestrates the entire parser setup by defining the main
    program description, adding the version flag, setting up subparsers, and
    then delegating the addition of specific argument groups to helper functions.

    Returns:
        argparse.ArgumentParser: The fully configured command-line argument parser.
    """
    # 📜 Main parser definition
    parser = argparse.ArgumentParser(
        description="CLI tool for xstate-statemachine boilerplate generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,  # Disable partial matching of long options
        epilog="""
            Examples:
              # Generate from a single file with default options (async, class-based, 2 files)
              xsm generate-template my_machine.json

              # Generate sync, function-style code into a specific directory
              xsm generate-template machine.json --async-mode no --style function --output ./generated

              # Generate a hierarchical machine and force overwrite of existing files
              xsm generate-template --json-parent=p.json --json-child=c.json --force
            """,
    )

    # 🔖 Version argument
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {package_version}",
        help="Show program's version number and exit.",
    )

    # 📋 Sub-command setup
    subparsers = parser.add_subparsers(
        dest="subcommand", required=True, help="Available commands"
    )
    gen_parser = subparsers.add_parser(
        "generate-template",
        aliases=["gt"],
        # MODIFIED LINE: Remove " (alias: gt)" from help string for cleaner output.
        help="Generate boilerplate templates from JSON machine configurations.",
        description="Generates Python code from one or more XState JSON machine definitions.",
    )

    # 🧩 Add argument groups using helpers
    _add_file_input_args(gen_parser)
    _add_generation_option_args(gen_parser)
    _add_simulation_option_args(gen_parser)

    return parser


def validate_args(parser: argparse.ArgumentParser) -> None:
    """
    Performs post-parsing validation of command-line arguments.

    This function checks for specific invalid combinations of arguments that
    `argparse` cannot handle on its own, such as using a flag multiple times
    when it is not allowed. It inspects the raw command-line arguments
    before the main logic proceeds.

    Args:
        parser (argparse.ArgumentParser): The parser instance, used for error reporting.

    Raises:
        SystemExit: Exits the program if validation fails.
    """
    # 🧪 Validate that --json-parent is only supplied once.
    # We check the raw `sys.argv` because `argparse` will have already processed it.
    if sys.argv.count("--json-parent") > 1:
        logger.error(
            "❌ Validation Error: The --json-parent flag can only be specified once."
        )
        parser.error("Only one --json-parent may be supplied.")

    # ✅ If this point is reached, the arguments are valid.
    logger.info("✅ All command-line arguments are valid.")


def resolve_template(
    style: Optional[str],
    template: Optional[str],
) -> str:
    """Resolve the template from --style and --template flags.

    Args:
        style: Value of deprecated --style flag (or None).
        template: Value of --template flag (or None).

    Returns:
        The resolved template string.

    Raises:
        ValueError: If both --style and --template are set.
    """
    if style is not None and template is not None:
        raise ValueError(
            "Cannot use both --style and --template. " "Use --template only."
        )
    if template is not None:
        return template
    if style is not None:
        import warnings

        mapping = {
            "class": "class-json",
            "function": "function-json",
        }
        resolved = mapping[style]
        warnings.warn(
            f"--style is deprecated, use --template "
            f"{resolved} instead. "
            f"Will be removed in v0.6.0",
            DeprecationWarning,
            stacklevel=2,
        )
        return resolved
    return "class-json"


def resolve_async_mode(
    async_mode: Optional[str],
    template: str,
) -> bool:
    """Resolve async mode based on explicit flag and template.

    Args:
        async_mode: The raw --async-mode value (or None).
        template: The resolved template string.

    Returns:
        True for async mode, False for sync mode.
    """
    if async_mode is not None:
        return normalize_bool(async_mode)
    # Template-aware defaults
    if template.startswith("pythonic"):
        return False
    return True
