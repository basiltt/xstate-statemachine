# src/xstate_statemachine/cli/commands/launcher.py
# -----------------------------------------------------------------------------
# 🧭 `xsm` with no arguments on a terminal -- the interactive launcher
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the launcher is a THIN layer of prompts that
#    builds the same `argparse.Namespace` the flag-driven commands consume
#    and then calls the same functions. Nothing is implemented twice: what
#    the wizard can do, `xsm gt --flags` can do, and vice versa. Every
#    prompt takes an injectable key source so the whole launcher is
#    testable without a pty.
# -----------------------------------------------------------------------------
"""Banner, menu, and the generate wizard with a live preview."""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ..ui import keys as K
from . import get_console
from .templates import TEMPLATES

MENU: List[Tuple[str, str, str]] = [
    (
        "generate",
        "Generate code",
        "Pick JSON files and a template; preview before writing",
    ),
    (
        "inspect",
        "Inspect a machine",
        "State tree, events, logic and policies at a glance",
    ),
    (
        "simulate",
        "Simulate",
        "Run a machine live: pick events, advance the clock",
    ),
    (
        "validate",
        "Validate",
        "Build files with the real library and list findings",
    ),
    ("diagram", "Diagram", "Mermaid / PlantUML / ASCII to stdout or a file"),
    ("docs", "Docs", "A Markdown reference page per machine"),
    ("templates", "Templates", "Browse the code generation catalogue"),
    ("info", "About", "Version, environment, links"),
    ("update", "Update", "Check PyPI and upgrade to the latest release"),
    ("quit", "Quit", ""),
]

#: Where the launcher remembers recently used machine files.
RECENT_PATH = (
    Path(os.environ.get("XSM_HOME", str(Path.home() / ".xsm"))) / "recent.json"
)
RECENT_MAX = 8


# =============================================================================
# recent files
# =============================================================================
def load_recent() -> List[str]:
    try:
        data = json.loads(RECENT_PATH.read_text(encoding="utf-8"))
        return [p for p in data if isinstance(p, str) and Path(p).exists()][
            :RECENT_MAX
        ]
    except (OSError, ValueError):
        return []


def remember(paths: List[str]) -> None:
    try:
        current = [p for p in load_recent() if p not in paths]
        RECENT_PATH.parent.mkdir(parents=True, exist_ok=True)
        RECENT_PATH.write_text(
            json.dumps([str(Path(p).resolve()) for p in paths] + current)[
                :100_000
            ],
            encoding="utf-8",
        )
    except OSError:  # pragma: no cover -- read-only home is not our problem
        pass


# =============================================================================
# typed paths
# =============================================================================
def clean_path(text: Optional[str]) -> str:
    """Normalise a path a user typed or pasted into a prompt.

    🪟 Windows Explorer's "Copy as path" wraps the path in double quotes,
       and shells leave single quotes on a dragged file -- passing those
       to `Path()` looks for a file literally named `"C:\\...json"` and
       the picker reports "not found" for a file that plainly exists.
       Also expands `~`, and accepts a `file:///` URI dropped from a
       browser or file manager.
    """
    t = (text or "").strip()
    while len(t) >= 2 and t[0] == t[-1] and t[0] in "\"'":
        t = t[1:-1].strip()
    if t.lower().startswith("file:///"):
        from urllib.parse import unquote
        from urllib.request import url2pathname

        t = url2pathname(unquote(t[len("file://") :]))
    return os.path.expanduser(t)


def expand_glob(pattern: str) -> List[str]:
    """Files matching *pattern*; a directory means its `*.json`."""
    if os.path.isdir(pattern):
        pattern = os.path.join(pattern, "*.json")
    return sorted(glob.glob(pattern))


# =============================================================================
# shared prompts
# =============================================================================
def _pick_files(
    multiple: bool, *, source: Optional[K.KeySource] = None
) -> Optional[List[str]]:
    """Recent files first; otherwise a path or glob typed in."""
    c = get_console()
    recent = load_recent()
    options: List[Tuple[str, str]] = [
        (Path(p).name, str(Path(p).parent)) for p in recent
    ]
    options.append(("Type a path or glob…", "e.g. machines/*.json"))
    while True:
        idx = c.select(
            (
                "Which machine file?"
                if not multiple
                else "Which machine file(s)?"
            ),
            options,
            source=source,
        )
        if idx is None:
            return None
        if idx < len(recent):
            chosen = [recent[idx]]
        else:
            typed = clean_path(c.text("Path or glob:", source=source))
            if not typed:
                return None
            chosen = expand_glob(typed) or [typed]
        missing = [p for p in chosen if not Path(p).exists()]
        if missing:
            c.error("not found: " + ", ".join(missing))
            continue
        if multiple and len(chosen) > 1:
            picked = c.multiselect(
                "Include which files?",
                [(Path(p).name, str(Path(p).parent)) for p in chosen],
                selected=range(len(chosen)),
                source=source,
            )
            if picked is None:
                return None
            chosen = [chosen[i] for i in picked]
        elif not multiple:
            chosen = chosen[:1]
        remember(chosen)
        return chosen


# =============================================================================
# the generate wizard
# =============================================================================
def _default_namespace(files: List[str]) -> argparse.Namespace:
    """The Namespace `run_generation_workflow` expects, with parser defaults."""
    return argparse.Namespace(
        subcommand="generate-template",
        json=[],
        json_files=list(files),
        json_parent=None,
        json_child=[],
        output=None,
        style=None,
        template=None,
        file_count=2,
        async_mode=None,
        loader="yes",
        log="yes",
        sleep="yes",
        sleep_time=2,
        force=False,
        no_verify=False,
        check=False,
        diff=False,
        with_tests=False,
        with_types=False,
        with_plugin=False,
        plain=False,
        no_color=False,
        no_anim=False,
        verbose=False,
    )


def generate_wizard(
    parser: argparse.ArgumentParser, *, source: Optional[K.KeySource] = None
) -> None:
    from ..strategies import GenerationContext, get_strategy
    from ..extractor import extract_logic_names
    from ..utils import camel_to_snake
    from .generate import COMPANIONS

    c = get_console()
    files = _pick_files(multiple=True, source=source)
    if not files:
        return

    primary = [t for t in TEMPLATES if t[3] != "companion"]
    idx = c.select("Template", [(t[0], t[2]) for t in primary], source=source)
    if idx is None:
        return
    template = primary[idx][0]

    add = c.multiselect(
        "Companion files",
        [
            ("tests", "pytest module recorded from the engine"),
            ("types", "TypedDict context, Literal events, typed stubs"),
            ("plugin", "PluginBase wired for this chart's hooks"),
        ],
        source=source,
    )
    if add is None:
        return

    opts = c.multiselect(
        "Options",
        [
            ("single file", "combine logic + runner into one module"),
            ("async runner", "generate an asyncio runner (default: sync)"),
            ("include logging", "log lines in generated actions"),
        ],
        selected=[2],
        source=source,
    )
    if opts is None:
        return

    out_dir = c.text(
        "Output directory:", default=str(Path(files[0]).parent), source=source
    )
    if out_dir is None:
        return
    out_dir = clean_path(out_dir)

    ns = _default_namespace(files)
    ns.template = template
    ns.output = out_dir or None
    ns.with_tests, ns.with_types, ns.with_plugin = (
        (0 in add),
        (1 in add),
        (2 in add),
    )
    ns.file_count = 1 if 0 in opts else 2
    ns.async_mode = "yes" if 1 in opts else None
    ns.log = "yes" if 2 in opts else "no"

    # 👁️ Preview: render the primary logic module for the first file and
    #    show the head of it before anything is written.
    try:
        cfg = json.loads(Path(files[0]).read_text(encoding="utf-8"))
        actions, guards, services = extract_logic_names(cfg)
        name = camel_to_snake(
            str(cfg.get("id", Path(files[0]).stem)).replace(" ", "_")
        )
        ctx = GenerationContext(
            actions=actions,
            guards=guards,
            services=services,
            is_async=bool(ns.async_mode),
            log=ns.log == "yes",
            machine_name=name,
            machine_id=str(cfg.get("id", name)),
            machine_names=[name],
            machine_ids=[str(cfg.get("id", name))],
            file_count=ns.file_count,
            configs=[cfg],
            json_filenames=[Path(files[0]).name],
            hierarchy=False,
            sleep=True,
            sleep_time=2,
            loader=True,
        )
        preview = get_strategy(template).generate_logic(ctx).splitlines()
    except Exception as exc:  # noqa: BLE001 -- preview is best-effort
        preview = [f"(preview unavailable: {type(exc).__name__}: {exc})"]
    head = preview[: min(len(preview), max(8, c.caps.height - 14))]
    c.blank()
    c.panel(
        [c.style(line, "code") for line in head]
        + (
            [c.style(f"… {len(preview) - len(head)} more lines", "muted")]
            if len(preview) > len(head)
            else []
        ),
        title=f"preview · {template}",
        subtitle=f"{Path(files[0]).name} → {out_dir or Path(files[0]).parent}",
    )
    c.blank()
    extras = [
        COMPANIONS[t][1].format(name="<machine>")
        for t, on in (
            ("pytest", ns.with_tests),
            ("typed", ns.with_types),
            ("plugin", ns.with_plugin),
        )
        if on
    ]
    c.print(
        c.style("  will write: ", "muted")
        + ", ".join(
            ["<machine>_logic.py", "<machine>_runner.py"]
            if ns.file_count == 2
            else ["<machine>.py"]
        )
        + (", " + ", ".join(extras) if extras else "")
    )
    go = c.confirm("Write these files?", source=source)
    if not go:
        c.print(c.style("nothing written", "muted"))
        return
    ns.force = True  # the user just confirmed
    from ..__main__ import run_generation_workflow

    run_generation_workflow(ns, parser)


# =============================================================================
# the menu
# =============================================================================
def run_launcher(
    parser: argparse.ArgumentParser,
    *,
    source: Optional[K.KeySource] = None,
    once: bool = False,
) -> None:
    from ... import __version__

    c = get_console()
    c.banner(__version__)
    c.blank()
    while True:
        idx = c.select(
            "What would you like to do?",
            [(label, desc) for _key, label, desc in MENU],
            source=source,
        )
        if idx is None or MENU[idx][0] == "quit":
            c.print(c.style("bye", "muted"))
            return
        key = MENU[idx][0]
        c.blank()
        try:
            if key == "generate":
                generate_wizard(parser, source=source)
            elif key == "inspect":
                files = _pick_files(multiple=False, source=source)
                if files:
                    from .inspect import run_inspect

                    run_inspect(files[0])
            elif key == "simulate":
                files = _pick_files(multiple=False, source=source)
                if files:
                    from .simulate import run_simulate

                    run_simulate(files[0], source=source)
            elif key == "validate":
                files = _pick_files(multiple=True, source=source)
                if files:
                    from .validate import run_validate

                    run_validate(files)
            elif key == "diagram":
                files = _pick_files(multiple=False, source=source)
                if files:
                    fmt = c.select(
                        "Format",
                        [("mermaid", ""), ("plantuml", ""), ("ascii", "")],
                        source=source,
                    )
                    if fmt is not None:
                        from .diagram import run_diagram

                        run_diagram(
                            files[0], fmt=("mermaid", "plantuml", "ascii")[fmt]
                        )
            elif key == "docs":
                files = _pick_files(multiple=True, source=source)
                if files:
                    out = clean_path(
                        c.text(
                            "Output directory (blank = stdout):",
                            source=source,
                        )
                    )
                    from .docs import run_docs

                    run_docs(files, output=out or None)
            elif key == "templates":
                from .templates import run_list_templates

                run_list_templates()
            elif key == "info":
                from .info import run_info

                run_info()
            elif key == "update":
                from .update import run_update

                run_update()
        except SystemExit:
            # A command signalled failure (exit 1); the launcher keeps going.
            pass
        c.blank()
        if once:
            return
