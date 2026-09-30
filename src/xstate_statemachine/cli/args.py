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
from typing import Any, Optional

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
            "pytest",
            "typed",
            "plugin",
            "fastapi-router",
            "pydantic-models",
        ],
        default=None,
        help=(
            "Code generation template. Default: class-json. "
            "Replaces --style (deprecated). 'pytest', 'typed', 'plugin', "
            "'fastapi-router' and 'pydantic-models' are single-file "
            "companions (see also --with-*)."
        ),
    )
    parser.add_argument(
        "--with-tests",
        action="store_true",
        help="Also emit test_<machine>.py: a pytest module recorded from the real engine.",
    )
    parser.add_argument(
        "--with-types",
        action="store_true",
        help="Also emit <machine>_types.py: Context TypedDict, event/state Literals, typed stubs.",
    )
    parser.add_argument(
        "--with-plugin",
        action="store_true",
        help="Also emit <machine>_observer.py: a PluginBase wired for the hooks this chart fires.",
    )
    parser.add_argument(
        "--with-api",
        action="store_true",
        help="Also emit <machine>_api.py: an editable FastAPI router, one typed route per event ([fastapi] extra).",
    )
    parser.add_argument(
        "--with-models",
        action="store_true",
        help="Also emit <machine>_models.py: a pydantic context model and one EventModel per event ([pydantic] extra).",
    )
    parser.add_argument(
        "--fixtures",
        action="store_true",
        help=(
            "pytest template only: use the [testing] plugin's "
            "@pytest.mark.xstate_machine marker and xsm_interp / xsm_clock / "
            "xsm_ran fixtures instead of building the interpreter by hand "
            '(pip install "xstate-statemachine[testing]").'
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
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help=(
            "Skip the structural check that generated code rebuilds the "
            "source machine. Syntax is still validated. Use only to "
            "inspect output the generator refuses to write."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Do not write anything. Exit 1 if the files on disk differ "
            "from what would be generated. Intended for CI, so generated "
            "code can be committed and kept honest."
        ),
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help=(
            "Like --check, but also print a unified diff of the "
            "differences. Implies --check."
        ),
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


def _add_live_args(
    parser: argparse.ArgumentParser, *, with_context: bool = True
) -> None:
    """Server flags shared by `inspect --live` and `replay --live` (#274)."""
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default 127.0.0.1). A non-loopback host "
        "requires --token.",
    )
    parser.add_argument(
        "--port", type=int, default=8765, help="Port (default 8765)."
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Access token (default: a fresh random one per run).",
    )
    parser.add_argument(
        "--open", action="store_true", help="Open the page in a browser."
    )
    if with_context:
        parser.add_argument(
            "--context",
            metavar="KEYS",
            help="Comma-separated context keys the page may see "
            "(default: none -- deny by default).",
        )


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
        prog="xsm",
        description="XState-StateMachine CLI — Generate Python code from XState JSON.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,  # Disable partial matching of long options
        epilog="""
examples:
  xsm                                   interactive launcher (on a terminal)
  xsm generate-template my_machine.json
  xsm gt machine.json -t pythonic-class --with-tests --with-types -o ./generated
  xsm inspect machine.json
  xsm simulate machine.json
  xsm diagram machine.json -f mermaid -o docs/
  xsm docs machine.json -o docs/
  xsm asyncapi machine.json -o asyncapi.json
  xsm dlq --dlq sqlite:///dlq.db list
  xsm validate machine.json
  xsm list-templates
  xsm info
  xsm plugins                           list installed third-party plugins  xsm update                            upgrade to the latest release
  python -m xstate_statemachine setup   Windows: fix a blocked xsm.exe launcher
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

    # 🎨 Global presentation flags (#cli-ui). Every command honours them;
    #    the same switches are also read from NO_COLOR / XSM_NO_COLOR /
    #    XSM_NO_ANIM, and a non-TTY stdout implies --plain.
    # 🧬 Declared once on a parent parser and attached to the root AND every
    #    subcommand, so `xsm --plain validate x` and `xsm validate x --plain`
    #    both work. `default=SUPPRESS` on the parents keeps the subcommand's
    #    value from clobbering the root's with False.
    presentation = argparse.ArgumentParser(add_help=False)
    for flag, help_text in (
        (
            "--plain",
            "Plain text: no colour, no box glyphs, no animation (implied when piped).",
        ),
        (
            "--no-color",
            "Keep layout and animation but emit no colour escapes.",
        ),
        ("--no-anim", "Disable spinners and in-place redraws."),
        ("--verbose", "Show the library's INFO log on stderr while running."),
    ):
        parser.add_argument(flag, action="store_true", help=help_text)
        presentation.add_argument(
            flag,
            action="store_true",
            default=argparse.SUPPRESS,
            help=argparse.SUPPRESS,
        )

    # 📋 Sub-command setup. `required=False` so a bare `xsm` on a TTY opens
    #    the interactive launcher (and prints help when piped).
    subparsers = parser.add_subparsers(
        dest="subcommand", required=False, help="Available commands"
    )
    gen_parser = subparsers.add_parser(
        "generate-template",
        aliases=["gt"],
        parents=[presentation],
        help="Generate Python code from an XState JSON file.",
        description="Generates Python code from one or more XState JSON machine definitions.",
    )

    # 🧩 Add argument groups using helpers
    _add_file_input_args(gen_parser)
    _add_generation_option_args(gen_parser)
    _add_simulation_option_args(gen_parser)

    # 📋 list-templates subcommand
    lt_parser = subparsers.add_parser(
        "list-templates",
        aliases=["lt"],
        parents=[presentation],
        help="List all available code generation templates.",
        description="Shows available templates with descriptions.",
    )
    lt_parser.add_argument(
        "--json", action="store_true", help="Emit the catalogue as JSON."
    )

    # ✅ validate subcommand
    val_parser = subparsers.add_parser(
        "validate",
        aliases=["val"],
        parents=[presentation],
        help="Validate an XState JSON config file.",
        description="Validates that JSON files are well-formed XState machine configs.",
    )
    val_parser.add_argument(
        "json_files",
        nargs="+",
        help="One or more JSON config files to validate.",
    )
    val_parser.add_argument(
        "--json", action="store_true", help="Emit findings as JSON."
    )
    val_parser.add_argument(
        "--lenient",
        action="store_true",
        help="Report unknown config keys as warnings instead of errors.",
    )

    # 🗺️ paths subcommand (#269)
    paths_parser = subparsers.add_parser(
        "paths",
        parents=[presentation],
        help="List a path to every reachable configuration of a chart.",
        description=(
            "Explores the chart with the real engine (stub logic, simulated "
            "clock) and prints one shortest path per reachable "
            "configuration, or every simple path with --simple. `+N` in "
            "the events column is a clock advance in ms -- the same "
            "grammar `xsm simulate --events` accepts."
        ),
    )
    paths_parser.add_argument("json_file", help="The machine JSON file.")
    paths_parser.add_argument(
        "--simple",
        action="store_true",
        help="Every acyclic path instead of one shortest path per target.",
    )
    paths_parser.add_argument(
        "--guards",
        choices=["true", "false", "both"],
        default="true",
        help="What stub guards return while exploring (default: true). "
        "'both' also records which assumption each path relies on.",
    )
    paths_parser.add_argument(
        "--max-depth", type=int, default=50, help="Depth bound (50)."
    )
    paths_parser.add_argument(
        "--max-paths",
        type=int,
        default=1000,
        help="Cap for --simple (1000).",
    )
    paths_parser.add_argument(
        "--json", action="store_true", help="Emit the paths as JSON."
    )

    # 📊 coverage subcommand (#270)
    coverage_parser = subparsers.add_parser(
        "coverage",
        parents=[presentation],
        help="Render a statechart coverage report (pytest --xsm-coverage).",
        description=(
            "Renders the version-1 JSON report written by "
            "`pytest --xsm-coverage --xsm-coverage-report=json:PATH` and "
            "exits 1 when any machine is under --fail-under."
        ),
    )
    coverage_parser.add_argument(
        "report_file", help="The JSON coverage report."
    )
    coverage_parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        metavar="N",
        help="Exit 1 if any machine's state or transition coverage is < N%%.",
    )
    coverage_parser.add_argument(
        "--json", action="store_true", help="Re-emit the report as JSON."
    )

    # ℹ️ info subcommand
    info_parser = subparsers.add_parser(
        "info",
        parents=[presentation],
        help="Show library version, Python version, and feature summary.",
        description="Displays information about the xstate-statemachine installation.",
    )
    info_parser.add_argument(
        "--json", action="store_true", help="Emit as JSON."
    )

    # 🔎 plugins subcommand (#296) -- explicit entry-point discovery
    plugins_parser = subparsers.add_parser(
        "plugins",
        parents=[presentation],
        help="List installed third-party plugins, stores and brokers.",
        description=(
            "Loads the entry points declared under the "
            "xstate_statemachine.plugins / .stores / .brokers groups and "
            "lists name, distribution, version, group and the PluginBase "
            "hooks each implements. Listing imports them; set "
            "XSM_DISABLE_PLUGIN_DISCOVERY=1 to disable."
        ),
    )
    plugins_parser.add_argument(
        "--json", action="store_true", help="Emit as JSON."
    )

    # ⬆️ update subcommand -- self-update via the installer that installed us
    update_parser = subparsers.add_parser(
        "update",
        parents=[presentation],
        help="Upgrade xstate-statemachine to the latest release on PyPI.",
        description=(
            "Checks PyPI for the latest release and upgrades with the tool "
            "that installed this copy (pip, pipx or uv tool). Refuses to "
            "touch an editable checkout or a conda-managed environment and "
            "prints the right command instead. On Windows, re-applies the "
            "`xsm setup` shim if it was in place, since pip recreates xsm.exe."
        ),
    )
    update_parser.add_argument(
        "--check",
        action="store_true",
        help="Only report; exit 1 if a newer release exists (for scripts).",
    )
    update_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Do not ask for confirmation.",
    )
    update_parser.add_argument(
        "--json", action="store_true", help="Emit the result as JSON."
    )

    # 📸 snapshots subcommand -- ops view of a persistence store (#263)
    snapshots_parser = subparsers.add_parser(
        "snapshots",
        parents=[presentation],
        help="List persisted snapshots in a store; --stale finds instances written by another machine version.",
        description=(
            "Reads a persistence store (sqlite:///path.db, file:///dir or "
            "memory://) and lists the keys it holds with their record "
            "version, the machine version that wrote them, and age. With "
            "a machine JSON and --stale, lists only the keys whose "
            "machine_version differs from the chart's version -- the "
            "in-flight instances a deploy must migrate or drain."
        ),
    )
    snapshots_parser.add_argument(
        "--store",
        required=True,
        help="Store URL: sqlite:///path/to.db, file:///path/to/dir.",
    )
    snapshots_parser.add_argument(
        "json_file",
        nargs="?",
        help="Machine JSON whose version stale keys are compared against.",
    )
    snapshots_parser.add_argument(
        "--stale",
        action="store_true",
        help="Only keys whose machine_version != the chart's version (needs json_file).",
    )
    snapshots_parser.add_argument(
        "--prefix", default="", help="Only keys starting with this prefix."
    )
    snapshots_parser.add_argument(
        "--limit", type=int, default=1000, help="Maximum keys to list."
    )
    snapshots_parser.add_argument(
        "--json", action="store_true", help="Emit as JSON."
    )

    # 🪟 setup subcommand -- make `xsm` work where pip's launcher is blocked
    _add_eda_parsers(subparsers, presentation)
    setup_parser = subparsers.add_parser(
        "setup",
        parents=[presentation],
        help="Make the `xsm` command work on Windows machines that block pip's xsm.exe launcher.",
        description=(
            "On Windows, pip installs `xsm` as an unsigned Scripts\\xsm.exe "
            "launcher that Application Control / AppLocker / Smart App Control "
            "policies may refuse. `setup` parks that launcher as "
            "xsm.exe.blocked and writes an xsm.cmd batch shim beside it, so "
            "`xsm` runs through the trusted cmd.exe -> python. Run it as "
            "`python -m xstate_statemachine setup`; re-run after "
            "`pip install --upgrade` (which recreates xsm.exe). A no-op on "
            "other operating systems."
        ),
    )
    setup_group = setup_parser.add_mutually_exclusive_group()
    setup_group.add_argument(
        "--undo",
        action="store_true",
        help="Remove the shim and restore pip's xsm.exe launcher.",
    )
    setup_group.add_argument(
        "--check",
        action="store_true",
        help="Report whether the shim is in place; exit 1 if `xsm` still resolves to xsm.exe.",
    )
    setup_parser.add_argument(
        "--json", action="store_true", help="Emit the state as JSON."
    )
    setup_parser.add_argument(
        "--scripts-dir",
        metavar="DIR",
        default=None,
        help="Override the Scripts directory (default: this interpreter's).",
    )

    # 🔍 inspect subcommand
    ins_parser = subparsers.add_parser(
        "inspect",
        aliases=["ins"],
        parents=[presentation],
        help="Show a machine's state tree, transitions, logic and policies.",
        description="Builds the machine with the real library and renders everything about it.",
    )
    ins_parser.add_argument("json_file", help="The machine JSON file.")
    ins_parser.add_argument(
        "--json", action="store_true", help="Emit the facts as JSON."
    )
    ins_parser.add_argument(
        "--no-events", action="store_true", help="Skip the transitions table."
    )
    _add_live_args(ins_parser)
    ins_parser.add_argument(
        "--live",
        action="store_true",
        help="Serve the live inspector (Stately Inspector protocol over SSE) "
        "and drive the machine with the simulator.",
    )
    ins_parser.add_argument(
        "-e",
        "--events",
        help="With --live: run these events (simulate grammar) instead of "
        "the interactive simulator.",
    )
    ins_parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="With --live and --events: seconds to keep serving (default: "
        "until Ctrl-C).",
    )

    # ⏪ replay subcommand (#274)
    rep_parser = subparsers.add_parser(
        "replay",
        parents=[presentation],
        help="Print or stream (--live) a recorded inspector session.",
        description="Reads a JSON Lines file written by `xsm sim --record`.",
    )
    rep_parser.add_argument("jsonl_file", help="The recording (.jsonl).")
    rep_parser.add_argument(
        "--live",
        action="store_true",
        help="Serve it on the live inspector instead of printing.",
    )
    rep_parser.add_argument(
        "--speed",
        type=float,
        default=0.0,
        help="With --live: 1.0 replays at recorded pace, 0 (default) at once.",
    )
    rep_parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="With --live: seconds to keep serving (default: until Ctrl-C).",
    )
    _add_live_args(rep_parser, with_context=False)

    # 🗺️ diagram subcommand
    dia_parser = subparsers.add_parser(
        "diagram",
        aliases=["dia"],
        parents=[presentation],
        help="Export a Mermaid, PlantUML or ASCII diagram.",
        description="Renders the machine as a diagram, to stdout or a file.",
    )
    dia_parser.add_argument("json_file", help="The machine JSON file.")
    dia_parser.add_argument(
        "-f",
        "--format",
        choices=["mermaid", "plantuml", "ascii"],
        default="mermaid",
        help="Diagram syntax. Default: mermaid.",
    )
    dia_parser.add_argument(
        "-o",
        "--output",
        help="Write to this file (or directory) instead of stdout.",
    )

    # 🎮 simulate subcommand
    sim_parser = subparsers.add_parser(
        "simulate",
        aliases=["sim"],
        parents=[presentation],
        help="Run a machine live: pick events, advance the clock, inspect context.",
        description="Interactive on a terminal; scripted with --events / --script / --json for CI.",
    )
    sim_parser.add_argument("json_file", help="The machine JSON file.")
    sim_parser.add_argument(
        "-e",
        "--events",
        help="Comma-separated events to send in order; '+500' advances the clock 500 ms.",
    )
    sim_parser.add_argument(
        "--clock", help="Advance the clock by this many ms at the end."
    )
    sim_parser.add_argument(
        "--script",
        help='JSON file: a list of {"send"}, {"clock"}, {"guard","value"}, {"undo"} commands.',
    )
    sim_parser.add_argument(
        "--guards-false", help="Comma-separated guard names that return False."
    )
    sim_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the final state and history as JSON.",
    )
    sim_parser.add_argument(
        "--record",
        metavar="PATH",
        help="Write the session as inspector protocol messages to a JSON "
        "Lines file (mode 0600); stream it later with `xsm replay`.",
    )
    sim_parser.add_argument(
        "--context",
        metavar="KEYS",
        help="With --record: comma-separated context keys to include "
        "(default: none -- deny by default).",
    )

    # 📄 docs subcommand
    docs_parser = subparsers.add_parser(
        "docs",
        parents=[presentation],
        help="Generate a Markdown reference page per machine.",
        description="Summary, Mermaid diagram, state and transition tables, logic, policies.",
    )
    docs_parser.add_argument(
        "json_files", nargs="+", help="Machine JSON files."
    )
    docs_parser.add_argument(
        "-o",
        "--output",
        help="Directory for <machine-id>.md files (default: stdout).",
    )

    # 🌱 new subcommand
    new_parser = subparsers.add_parser(
        "new",
        parents=[presentation],
        help="Scaffold a minimal project from an example app.",
        description=(
            "Copies a shipped example app (stdlib templating) into DIR, "
            "renamed from --name. `--list` shows the templates."
        ),
    )
    new_parser.add_argument(
        "directory", nargs="?", help="Target directory (created)."
    )
    new_parser.add_argument(
        "-t",
        "--template",
        default="fastapi",
        help="Project template. Default: fastapi. See --list.",
    )
    new_parser.add_argument(
        "-n",
        "--name",
        default="orders",
        help=(
            "lower_snake_case project name: the URL prefix, store "
            "prefix and (camelCased) machine id. Default: orders."
        ),
    )
    new_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Write into a non-empty directory (overwrites same-name files).",
    )
    new_parser.add_argument(
        "--list", action="store_true", help="List the project templates."
    )

    return parser


def _add_eda_parsers(subparsers: Any, presentation: Any) -> None:
    """`xsm dlq` and `xsm asyncapi` (#293, #295)."""
    dlq = subparsers.add_parser(
        "dlq",
        parents=[presentation],
        help="List, show, replay or purge dead-lettered messages.",
        description=(
            "Operates a dead-letter store (sqlite:///dlq.db). `replay` is a "
            "DRY RUN by default; a real replay needs --no-dry-run --yes "
            "--reason, reuses the envelope id (the inbox dedups a double "
            "replay), refuses a changed machine without --force, and is "
            "audited. `purge` needs --yes --reason."
        ),
    )
    dlq.add_argument(
        "--dlq",
        required=True,
        help="Dead-letter store: sqlite:///path.db (or a file path).",
    )
    verbs = dlq.add_subparsers(dest="dlq_command", required=True)
    ls = verbs.add_parser("list", help="List unresolved dead letters.")
    ls.add_argument(
        "--all", action="store_true", help="Include resolved ones."
    )
    ls.add_argument("--limit", type=int, default=1000)
    ls.add_argument("--json", action="store_true", help="Emit as JSON.")
    show = verbs.add_parser("show", help="Print one record as JSON.")
    show.add_argument("record_id")
    rp = verbs.add_parser(
        "replay", help="Re-send a dead-lettered envelope (dry run default)."
    )
    rp.add_argument("record_id")
    rp.add_argument("--store", help="State store URL the machine lives in.")
    rp.add_argument(
        "--machine",
        action="append",
        help="Machine JSON (repeatable); the current, fixed chart.",
    )
    rp.add_argument(
        "--logic", help="Module with the machine's logic (import path)."
    )
    mode = rp.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="no_dry_run",
        action="store_false",
        default=False,
        help="Only report what would happen (the default).",
    )
    mode.add_argument(
        "--no-dry-run",
        dest="no_dry_run",
        action="store_true",
        help="Really replay (also needs --yes and --reason).",
    )
    rp.add_argument("--yes", action="store_true", help="Confirm.")
    rp.add_argument("--reason", help="Why it is safe now (audited).")
    rp.add_argument(
        "--force",
        action="store_true",
        help="Replay even if the machine changed since capture.",
    )
    rp.add_argument("--json", action="store_true", help="Emit as JSON.")
    pg = verbs.add_parser("purge", help="Delete dead letters (audited).")
    pg.add_argument("--id", dest="record_id", help="One record id.")
    pg.add_argument("--older-than", help="Age cutoff, e.g. 30d, 12h, 15m.")
    pg.add_argument("--yes", action="store_true", help="Confirm.")
    pg.add_argument("--reason", help="Why (audited).")
    pg.add_argument("--json", action="store_true", help="Emit as JSON.")

    aa = subparsers.add_parser(
        "asyncapi",
        parents=[presentation],
        help="Generate an AsyncAPI 3.0 document from a machine.",
        description=(
            "Consumed events (the chart's `on` keys) and published events "
            "(`meta.publish` transitions, `publish`-tagged states) as an "
            "AsyncAPI 3.0.0 document with CloudEvents messages."
        ),
    )
    aa.add_argument("json_file", help="The machine JSON file.")
    aa.add_argument("-o", "--output", help="Write to this file.")
    aa.add_argument("--server", help="Broker host, e.g. localhost:9092.")
    aa.add_argument("--protocol", default="kafka", help="Server protocol.")
    aa.add_argument("--inbound", help="Inbound channel address.")
    aa.add_argument(
        "--outbound", default="events", help="Outbound channel address."
    )
    aa.add_argument(
        "--validate",
        action="store_true",
        help="Validate against the vendored schema (needs jsonschema).",
    )


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
    jp_count = sys.argv.count("--json-parent") + sys.argv.count("-jp")
    if jp_count > 1:
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
        mapping = {
            "class": "class-json",
            "function": "function-json",
        }
        resolved = mapping.get(style)
        if resolved is None:
            raise ValueError(
                f"Unknown --style value: {style}. " f"Use --template instead."
            )
        from ..deprecations import deprecated

        # 📝 The notice must always name a FUTURE release (v0.6.0 promised
        #    "removed in v0.7.0" and then kept it). Removal follows the
        #    deprecation policy: no earlier than the next major (1.0).
        deprecated(
            "--style",
            since="0.4.1",
            removal="1.0",
            alternative=f"--template {resolved}",
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
