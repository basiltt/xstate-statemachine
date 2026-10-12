# src/xstate_statemachine/cli/commands/diagram.py
# -----------------------------------------------------------------------------
# 🗺️ `xsm diagram` -- Mermaid / PlantUML / ASCII
# -----------------------------------------------------------------------------
"""The `diagram` subcommand. Mermaid and PlantUML come from the library's
own exporters (`MachineNode.to_mermaid` / `to_plantuml`); ASCII is the
inspect tree plus an arrow list, for a README or a terminal."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ...models import MachineNode
from . import get_console
from .analysis import analyse, event_table
from .inspect import state_tree

FORMATS = ("mermaid", "plantuml", "ascii")


def ascii_diagram(machine: MachineNode[Any], *, unicode: bool) -> str:
    """Render the machine as an ASCII tree plus a transition list.

    Args:
        machine: Machine to draw.
        unicode: Use unicode glyphs instead of plain ASCII.

    Returns:
        The diagram text.
    """
    from ..ui.term import PLAIN, Capabilities
    from ..ui.tree import render as render_tree

    caps = (
        PLAIN
        if not unicode
        else Capabilities(True, False, False, True, False, 100, 30)
    )
    lines = render_tree(caps, state_tree(machine, unicode=unicode))
    arrow = "→" if unicode else "->"
    lines.append("")
    for ev, src, dst, guard, acts in event_table(machine):
        g = f" [{guard}]" if guard else ""
        a = f" / {acts}" if acts else ""
        lines.append(f"{src} --{ev}{g}{a}{arrow} {dst}")
    return "\n".join(lines)


def render_diagram(
    machine: MachineNode[Any], fmt: str, *, unicode: bool = True
) -> str:
    """Render the machine in the requested diagram format.

    Args:
        machine: Machine to draw.
        fmt: One of ``mermaid``, ``plantuml`` or ``ascii``.
        unicode: Use unicode glyphs for the ASCII format.

    Returns:
        The diagram text.

    Raises:
        ValueError: If *fmt* is not a known format.
    """
    if fmt == "mermaid":
        return machine.to_mermaid()
    if fmt == "plantuml":
        return machine.to_plantuml()
    if fmt == "ascii":
        return ascii_diagram(machine, unicode=unicode)
    raise ValueError(f"unknown format {fmt!r}; expected one of {FORMATS}")


def run_diagram(
    path: str, *, fmt: str = "mermaid", output: Optional[str] = None
) -> None:
    """Implement ``xsm diagram``: print or write a machine diagram.

    Args:
        path: Machine JSON file.
        fmt: Diagram format.
        output: File or directory to write to instead of printing.

    Raises:
        SystemExit: If the machine cannot be loaded.
    """
    c = get_console()
    facts = analyse(Path(path), strict_config=False)
    if facts.machine is None:
        for f in facts.findings:
            c.error(f"{path}: {f.message}")
        raise SystemExit(1)
    text = render_diagram(facts.machine, fmt, unicode=c.caps.unicode)
    if output:
        out = Path(output)
        if out.is_dir():
            ext = {"mermaid": ".mmd", "plantuml": ".puml", "ascii": ".txt"}[
                fmt
            ]
            out = out / f"{facts.machine_id}{ext}"
        out.write_text(text + "\n", encoding="utf-8")
        c.ok(f"Wrote {fmt} diagram: {c.style(str(out), 'path')}")
        return
    if fmt == "ascii":
        c.print(text)
    else:
        # 🎨 Syntax-tint the two textual formats lightly: keywords / arrows.
        for line in text.splitlines():
            s = line.strip()
            if s.startswith(
                ("stateDiagram", "@startuml", "@enduml", "state ")
            ):
                c.print(c.style(line, "brand"))
            elif "-->" in line:
                c.print(c.style(line, "event"))
            else:
                c.print(line)
