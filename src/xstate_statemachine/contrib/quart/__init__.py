# src/xstate_statemachine/contrib/quart/__init__.py
# -----------------------------------------------------------------------------
# ⚡ contrib.quart -- re-export of the Quart shim that lives in contrib.flask
# -----------------------------------------------------------------------------
# 📦 Not an extra of its own: ``contrib/_registry.py`` has no ``quart``
#    entry. Quart depends on Flask, so install ``[flask]`` plus ``quart``;
#    without Quart this import raises `MissingExtraError` with that hint.
# -----------------------------------------------------------------------------
"""Quart shim: ``from xstate_statemachine.contrib.quart import QuartXState``."""

from __future__ import annotations

from ..flask.quart import (  # noqa: F401
    QuartXState,
    create_quart_statechart_blueprint,
    problem_response,
    receipt_response,
)

__all__ = [
    "QuartXState",
    "create_quart_statechart_blueprint",
    "problem_response",
    "receipt_response",
]
