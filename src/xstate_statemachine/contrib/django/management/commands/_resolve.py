# src/xstate_statemachine/contrib/django/management/commands/_resolve.py
"""Shared argument handling for the ``xsm_*`` management commands."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import tempfile
from typing import Any, Iterator

from django.apps import apps
from django.core.management.base import CommandError

__all__ = ["model_from_label", "machine_json_path", "console", "run_cli"]


def model_from_label(label: str) -> Any:
    """``"shop.Order"`` → the model class (a `StatechartModelMixin`)."""
    try:
        model = apps.get_model(label)
    except (LookupError, ValueError) as exc:
        raise CommandError(f"unknown model {label!r}: {exc}") from None
    from ...mixin import StatechartModelMixin

    if not issubclass(model, StatechartModelMixin):
        raise CommandError(f"{label} is not a StatechartModelMixin model")
    return model


@contextlib.contextmanager
def machine_json_path(model: Any) -> Iterator[str]:
    """A JSON file for *model*'s chart: its own path spec, or a temp copy
    of the parsed config (``source_config``) for dict / callable specs."""
    from ..._machine import machine_source

    spec = model.statechart_machine
    try:
        src = machine_source(spec, model)
    except FileNotFoundError as exc:
        raise CommandError(str(exc)) from None
    if src is not None:
        yield str(src)
        return
    node = model().statechart_machine_node()
    fd, tmp = tempfile.mkstemp(suffix=".json", prefix=f"xsm-{node.id}-")
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            json.dump(node.source_config, fh)
        yield tmp
    finally:
        with contextlib.suppress(OSError):
            os.remove(tmp)


def console(options: Any, stdout: Any = None) -> None:
    """Configure the CLI console exactly as ``xsm --plain / --no-color``
    would, writing to *stdout* (the command's stream)."""
    from .....cli import commands
    from .....cli.ui import Console, detect

    stream = getattr(stdout, "_out", stdout)
    caps = detect(
        stream,
        plain=bool(options.get("plain")),
        no_color=bool(options.get("no_color")),
        no_anim=True,
    )
    commands._console = Console(caps, stream=stream)


def run_cli(fn: Any, *a: Any, **kw: Any) -> None:
    """Run a CLI function; its ``SystemExit(n)`` becomes `CommandError`."""
    from .....cli.commands import reset_console

    try:
        fn(*a, **kw)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code:
            raise CommandError(f"exit status {code}", returncode=code)
    finally:
        reset_console()


def add_console_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--plain", action="store_true", help="No colour, no box glyphs."
    )
    parser.add_argument("--no-color", action="store_true", help="No colour.")
