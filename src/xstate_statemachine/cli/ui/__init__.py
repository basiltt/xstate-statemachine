# src/xstate_statemachine/cli/ui/__init__.py
# -----------------------------------------------------------------------------
# 🎨 `xsm` rendering toolkit -- zero dependencies
# -----------------------------------------------------------------------------
"""Colour, layout, live status and prompts for the CLI, stdlib only.

Import `Console` and build everything through it; the primitives are
public for tests and for anyone embedding the CLI's look.
"""

from .console import Console
from .table import Column, Table
from .term import PLAIN, Capabilities, detect
from .tree import Node

__all__ = [
    "Console",
    "Column",
    "Table",
    "Node",
    "Capabilities",
    "PLAIN",
    "detect",
]
