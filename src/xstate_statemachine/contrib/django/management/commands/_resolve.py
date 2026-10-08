# src/xstate_statemachine/contrib/django/management/commands/_resolve.py
"""Shared argument handling for the ``xsm_*`` management commands.

📝 L4 (#361 review): these commands surface ``str(exc)`` in
`CommandError` on purpose -- they run in the OPERATOR's own shell, not
behind an HTTP/WebSocket boundary, so X0.7's class-name-only rule for
problem bodies does not apply.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import tempfile
from typing import Any, Iterator

from django.apps import apps
from django.core.management.base import CommandError

__all__ = [
    "model_from_label",
    "machine_json_path",
    "console",
    "run_cli",
    "field_name",
    "database",
    "get_row",
]


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


def field_name(model: Any) -> str:
    """The model's `StatechartField` name; two fields without
    ``statechart_field_name`` is an operator-facing `CommandError`
    (#282 battle: it was a raw ``TypeError`` traceback)."""
    try:
        return str(model.statechart_field_obj().name)
    except TypeError as exc:
        raise CommandError(str(exc)) from None


def database(alias: str) -> str:
    """Validate a ``--database`` alias up front (#282 battle: an unknown
    alias was a raw ``ConnectionDoesNotExist`` traceback)."""
    from django.db import connections

    if alias not in connections:
        known = ", ".join(sorted(connections))
        raise CommandError(f"unknown --database {alias!r} (known: {known})")
    return alias


def get_row(model: Any, pk: Any, using: str = "default") -> Any:
    """The row *pk* of *model*; a missing or malformed pk is a
    `CommandError` (#282 battle: ``abc`` for an int pk was a raw
    ``ValueError``)."""
    from django.core.exceptions import ValidationError

    label = model._meta.label
    try:
        return model._base_manager.using(using).get(pk=pk)
    except model.DoesNotExist:
        raise CommandError(f"{label} pk={pk} not found") from None
    except (ValueError, TypeError, ValidationError) as exc:
        raise CommandError(f"{label}: bad pk {pk!r}: {exc}") from None


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
    except OSError as exc:
        # 🔥 #282 battle: ``xsm_docs -o /read-only`` / ``xsm_diagram -o``
        #    into a missing or unwritable place was a raw traceback.
        raise CommandError(f"{type(exc).__name__}: {exc}") from None
    finally:
        reset_console()


def add_console_flags(parser: argparse.ArgumentParser) -> None:
    # 📝 ``--no-color`` is Django's own BaseCommand flag; it is honoured
    #    as the CLI's (``options["no_color"]``).
    parser.add_argument(
        "--plain", action="store_true", help="No colour, no box glyphs."
    )
