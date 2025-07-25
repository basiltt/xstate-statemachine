# src/xstate_statemachine/cli/args.py
# -----------------------------------------------------------------------------
# ⚙️ Argument Parser Configuration
# -----------------------------------------------------------------------------
# This module centralizes the command-line argument parsing setup using the
# `argparse` library. Defining the parser in a separate module keeps the
# main entry point clean and focused on orchestration. It follows the Single
# Responsibility Principle by dedicating this file solely to defining the
# CLI's interface (commands, flags, and help messages).
# -----------------------------------------------------------------------------
"""
Defines and configures the CLI argument parser.
"""
import argparse
import sys

from .. import __version__ as package_version


def get_parser() -> argparse.ArgumentParser:
    """Creates and configures the argument parser for the CLI."""
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
    return parser


def validate_args(parser: argparse.ArgumentParser) -> None:
    """Performs post-parsing validation of command-line arguments."""
    if sys.argv.count("--json-parent") > 1:
        parser.error("Only one --json-parent may be supplied.")
