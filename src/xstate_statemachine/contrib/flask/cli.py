# src/xstate_statemachine/contrib/flask/cli.py
# -----------------------------------------------------------------------------
# ⌨️ `flask xsm inspect|diagram|docs|simulate <name>`
# -----------------------------------------------------------------------------
# 🏛️ Thin delegation: each command resolves the REGISTERED machine's JSON
#    source (the path it was registered from, a config dict, or
#    ``register(source=)``) and calls the same function the standalone
#    `xsm` CLI calls -- so ``flask xsm inspect order --plain`` prints
#    exactly what ``xsm inspect order.json --plain`` prints.
# -----------------------------------------------------------------------------
"""The ``flask xsm`` command group."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator, Optional

import click
from flask import current_app
from flask.cli import with_appcontext

from ._core import EXTENSION_KEY

__all__ = ["xsm_cli"]


@contextlib.contextmanager
def _source_path(name: str) -> Iterator[str]:
    """A JSON file for machine *name* (a temp copy for a dict source)."""
    reg = current_app.extensions.get(EXTENSION_KEY)
    if reg is None:
        raise click.ClickException("XState.init_app(app, ...) was not called")
    try:
        r = reg.reg(name)
    except KeyError:
        known = ", ".join(reg.names()) or "none"
        raise click.ClickException(
            f"no machine registered as {name!r} (registered: {known})"
        )
    src = r.source
    if src is None:
        raise click.ClickException(
            f"{name!r} was registered as a MachineNode without source=; "
            f"pass register(..., source='machine.json') to use flask xsm"
        )
    if isinstance(src, dict):
        fd, tmp = tempfile.mkstemp(suffix=".json", prefix=f"xsm-{name}-")
        try:
            with open(fd, "w", encoding="utf-8") as fh:
                json.dump(src, fh)
            yield tmp
        finally:
            with contextlib.suppress(OSError):
                os.remove(tmp)
        return
    yield str(Path(src))


def _console(plain: bool, no_color: bool) -> None:
    from ...cli.commands import configure_console

    configure_console(
        argparse.Namespace(plain=plain, no_color=no_color, no_anim=True)
    )


def _run(fn: Any, *a: Any, **kw: Any) -> None:
    try:
        fn(*a, **kw)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code:
            raise click.exceptions.Exit(code)


_plain = click.option(
    "--plain", is_flag=True, help="Plain text: no colour, no box glyphs."
)
_no_color = click.option("--no-color", is_flag=True, help="No colour.")


@click.group("xsm", help="Statechart tools for the app's registered machines.")
def xsm_cli() -> None:
    pass


@xsm_cli.command("inspect")
@click.argument("name")
@click.option("--json", "as_json", is_flag=True, help="Emit facts as JSON.")
@click.option("--no-events", is_flag=True, help="Skip the transitions table.")
@_plain
@_no_color
@with_appcontext
def inspect_cmd(
    name: str, as_json: bool, no_events: bool, plain: bool, no_color: bool
) -> None:
    """Show NAME's state tree, transitions, logic and policies."""
    from ...cli.commands.inspect import run_inspect

    _console(plain, no_color)
    with _source_path(name) as path:
        _run(run_inspect, path, as_json=as_json, no_events=no_events)


@xsm_cli.command("diagram")
@click.argument("name")
@click.option(
    "-f",
    "--format",
    "fmt",
    type=click.Choice(["mermaid", "plantuml", "ascii"]),
    default="mermaid",
)
@click.option("-o", "--output", default=None)
@_plain
@_no_color
@with_appcontext
def diagram_cmd(
    name: str, fmt: str, output: Optional[str], plain: bool, no_color: bool
) -> None:
    """Export NAME as a Mermaid, PlantUML or ASCII diagram."""
    from ...cli.commands.diagram import run_diagram

    _console(plain, no_color)
    with _source_path(name) as path:
        _run(run_diagram, path, fmt=fmt, output=output)


@xsm_cli.command("docs")
@click.argument("name")
@click.option("-o", "--output", default=None)
@_plain
@_no_color
@with_appcontext
def docs_cmd(
    name: str, output: Optional[str], plain: bool, no_color: bool
) -> None:
    """Generate a Markdown reference page for NAME."""
    from ...cli.commands.docs import run_docs

    _console(plain, no_color)
    with _source_path(name) as path:
        _run(run_docs, [path], output=output)


@xsm_cli.command("simulate")
@click.argument("name")
@click.option("-e", "--events", default=None)
@click.option("--clock", default=None)
@click.option("--guards-false", default=None)
@click.option("--json", "as_json", is_flag=True)
@_plain
@_no_color
@with_appcontext
def simulate_cmd(
    name: str,
    events: Optional[str],
    clock: Optional[str],
    guards_false: Optional[str],
    as_json: bool,
    plain: bool,
    no_color: bool,
) -> None:
    """Run NAME with stub logic: scripted with --events / --json."""
    from ...cli.commands.simulate import run_simulate

    _console(plain, no_color)
    with _source_path(name) as path:
        _run(
            run_simulate,
            path,
            events=events,
            clock=clock,
            as_json=as_json,
            guards_false=guards_false,
        )
