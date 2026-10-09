# src/xstate_statemachine/cli/commands/asyncapi.py
# -----------------------------------------------------------------------------
# 📜 `xsm asyncapi` -- an AsyncAPI 3.0 document from a machine (#295)
# -----------------------------------------------------------------------------
"""The `asyncapi` subcommand."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Optional

from . import get_console

__all__ = ["run_asyncapi"]


def _fail(msg: str) -> SystemExit:
    """One line on stderr, exit 2 -- never a traceback for bad input."""
    print(f"xsm asyncapi: error: {msg}", file=sys.stderr)
    return SystemExit(2)


def _machine(path: str) -> Any:
    """Build the chart at *path* with stub logic (documentation only)."""
    from ...exceptions import XStateMachineError
    from ...factory import create_machine
    from ...testing_utils import stub_logic

    try:
        cfg = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(cfg, dict):
            raise _fail(f"{path!r} is not a machine (not a JSON object)")
        # 📝 Documentation only: stub logic so a chart whose logic lives
        #    elsewhere still builds (no action ever runs here).
        return create_machine(cfg, logic=stub_logic(cfg))
    except (OSError, ValueError, RecursionError, XStateMachineError) as exc:
        raise _fail(f"cannot load machine {path!r}: {exc}") from None


def _nonblank(flag: str, value: Optional[str]) -> Optional[str]:
    """Refuse an empty / whitespace-only option instead of dropping it."""
    if value is not None and not value.strip():
        raise _fail(f"{flag} must not be empty")
    return value


def _validated(doc: Any) -> None:
    """`validate_asyncapi`, with every failure as one line (exit 2)."""
    from ...eda.asyncapi import validate_asyncapi
    from ...exceptions import MissingExtraError

    try:
        validate_asyncapi(doc)
    except MissingExtraError as exc:
        raise _fail(f"--validate needs jsonschema: {exc}") from None
    except Exception as exc:  # jsonschema.ValidationError (no hard import)
        if not type(exc).__module__.startswith("jsonschema"):
            raise
        msg = getattr(exc, "message", None) or str(exc).splitlines()[0]
        raise _fail(f"document is not valid AsyncAPI 3.0: {msg}") from None


def _write(output: str, text: str) -> None:
    try:
        Path(output).write_text(text, encoding="utf-8")
    except OSError as exc:
        raise _fail(
            f"cannot write {output!r}: {exc.strerror or exc}"
        ) from None


def run_asyncapi(
    json_file: str,
    *,
    output: Optional[str] = None,
    server: Optional[str] = None,
    protocol: str = "kafka",
    inbound: Optional[str] = None,
    outbound: str = "events",
    validate: bool = False,
) -> None:
    """Print (or write to *output*) the AsyncAPI 3.0 document of a chart.

    Exit codes: 0 success; 2 refused input -- a missing, unreadable or
    invalid machine file, an empty ``--server`` / ``--inbound`` /
    ``--outbound``, an unwritable ``-o``, ``--validate`` without
    ``jsonschema`` or a document the schema rejects. Errors are one
    stderr line, never a traceback.

    Args:
        json_file: The machine JSON file.
        output: Write here instead of stdout.
        server: Broker host for the ``servers`` block.
        protocol: Server protocol (default ``kafka``).
        inbound: Topic the machine consumes from.
        outbound: Topic published events go to.
        validate: Validate against the AsyncAPI 3.0 schema.
    """
    from ...eda.asyncapi import asyncapi_document

    _nonblank("--server", server)
    _nonblank("--inbound", inbound)
    _nonblank("--outbound", outbound)
    c = get_console()
    doc = asyncapi_document(
        _machine(json_file),
        server={"host": server, "protocol": protocol} if server else None,
        inbound_topic=inbound,
        outbound_topic=outbound,
    )
    if validate:
        _validated(doc)
    text = json.dumps(doc, indent=2)
    if output is None:
        c.print(text)
        return
    text += "\n"
    _write(output, text)
    c.info(f"wrote {output}")
