# src/xstate_statemachine/cli/ui/tree.py
# -----------------------------------------------------------------------------
# 🌳 Tree renderer -- used for state trees in inspect / simulate / docs
# -----------------------------------------------------------------------------
"""Render nested nodes with ├── └── connectors (ASCII fallback)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from .style import paint
from .term import Capabilities


@dataclass
class Node:
    """A tree node. *label* is pre-styled text; *note* is dim trailing text."""

    label: str
    children: List["Node"] = field(default_factory=list)
    note: str = ""
    role: Optional[str] = None


def render(
    caps: Capabilities,
    root: Node,
    *,
    show_root: bool = True,
    decorate: Optional[Callable[[Node], str]] = None,
) -> List[str]:
    """Render *root* to lines.

    Args:
        decorate: Optional hook returning extra text appended after a
            node's label (e.g. an "● active" marker in the simulator).
    """
    if caps.unicode:
        tee, last, pipe, blank = "├── ", "└── ", "│   ", "    "
    else:
        tee, last, pipe, blank = "|-- ", "`-- ", "|   ", "    "

    def line_for(node: Node) -> str:
        label = paint(node.label, node.role, caps) if node.role else node.label
        extra = decorate(node) if decorate else ""
        note = paint(f"  {node.note}", "muted", caps) if node.note else ""
        return f"{label}{extra}{note}"

    lines: List[str] = []

    def walk(node: Node, prefix: str, is_last: bool, depth: int) -> None:
        if depth > 0:
            connector = last if is_last else tee
            lines.append(
                paint(prefix + connector, "muted", caps) + line_for(node)
            )
            child_prefix = prefix + (blank if is_last else pipe)
        else:
            if show_root:
                lines.append(line_for(node))
            child_prefix = prefix if show_root else ""
        for i, child in enumerate(node.children):
            walk(child, child_prefix, i == len(node.children) - 1, depth + 1)

    walk(root, "", True, 0)
    return lines
