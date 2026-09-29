# src/xstate_statemachine/contrib/testing/__init__.py
# -----------------------------------------------------------------------------
# 🧪 [testing] -- pytest fixtures, markers and snapshot assertions (#268)
# -----------------------------------------------------------------------------
# 🏛️ Users already test machines with `SyncInterpreter` + `SimulatedClock` +
#    a stub `MachineLogic` -- the pattern our own `pytest` codegen template
#    emits. This extra makes that a declarative pytest plugin: point a test
#    at a JSON file (or a dict, or a built `MachineNode`) with the
#    `xstate_machine` marker and receive a started interpreter, its clock, a
#    store and the list of actions that ran.
#
# 📝 The plugin module (`pytest_plugin`) is registered as a `pytest11` entry
#    point UNCONDITIONALLY (hatch has no conditional entry points), so pytest
#    loads it in every project that installed the library -- with or without
#    the extra. It therefore imports nothing but `pytest` and core, is a
#    complete no-op without the marker, and `-p no:xstate_statemachine`
#    disables it. Every fixture is prefixed `xsm_` so it cannot shadow a
#    user's own `machine` / `clock` / `store`.
#
# 🪶 Core never imports this package. `hypothesis` (the other module of the
#    extra) is used by the model-based tester (#271), not here.
# -----------------------------------------------------------------------------
"""pytest integration.

Install with ``pip install "xstate-statemachine[testing]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("testing", "pytest")

from .pytest_plugin import (  # noqa: E402
    PLUGIN_NAME,
    SnapshotMismatchError,
    normalize_snapshot,
    parse_marker,
    render_snapshot,
)

__all__ = [
    "PLUGIN_NAME",
    "SnapshotMismatchError",
    "normalize_snapshot",
    "parse_marker",
    "render_snapshot",
]
