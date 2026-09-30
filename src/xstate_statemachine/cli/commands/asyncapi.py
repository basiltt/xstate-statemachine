# src/xstate_statemachine/cli/commands/asyncapi.py
# -----------------------------------------------------------------------------
# 📜 `xsm asyncapi` -- an AsyncAPI 3.0 document from a machine (#295)
# -----------------------------------------------------------------------------
"""The `asyncapi` subcommand."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from . import get_console

__all__ = ["run_asyncapi"]


def _machine(path: str) -> Any:
    from ...factory import create_machine
    from ...testing_utils import stub_logic

    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    # 📝 Documentation only: stub logic so a chart whose logic lives
    #    elsewhere still builds (no action ever runs here).
    return create_machine(cfg, logic=stub_logic(cfg))


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
    from ...eda.asyncapi import asyncapi_document, validate_asyncapi

    c = get_console()
    doc = asyncapi_document(
        _machine(json_file),
        server={"host": server, "protocol": protocol} if server else None,
        inbound_topic=inbound,
        outbound_topic=outbound,
    )
    if validate:
        validate_asyncapi(doc)
    text = json.dumps(doc, indent=2) + "\n"
    if output is None:
        c.print(text.rstrip("\n"))
        return
    Path(output).write_text(text, encoding="utf-8")
    c.info(f"wrote {output}")
