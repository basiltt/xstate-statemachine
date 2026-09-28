# src/xstate_statemachine/contrib/testing/__init__.py
# -----------------------------------------------------------------------------
# 🧪 [testing] -- pytest fixtures, path generation, coverage, model-based tests
# -----------------------------------------------------------------------------
# 🏛️ Users already test charts with `SyncInterpreter` + `SimulatedClock` +
#    `stub_logic` (the pattern `xsm gt -t pytest` emits). This extra makes
#    that declarative: mark a test with the chart, get `xsm_*` fixtures.
#
# 📝 The pytest plugin itself lives in `pytest_plugin.py` and is registered
#    unconditionally via the `pytest11` entry point (hatch has no
#    conditional entry points). It is therefore written to be a complete
#    no-op in a project that never uses the `xstate_machine` marker, and it
#    imports nothing but pytest and the core. Everything hypothesis-based
#    (#271) is imported lazily so `[testing]` without hypothesis still
#    gives you fixtures, paths and coverage.
# -----------------------------------------------------------------------------
"""pytest integration.

Install with ``pip install "xstate-statemachine[testing]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("testing", "pytest")

from .pytest_plugin import (  # noqa: E402
    MARKER_GUARDS_FALSE,
    MARKER_MACHINE,
    assert_snapshot_matches,
    comparable_snapshot,
    send_all,
)

__all__ = [
    "MARKER_GUARDS_FALSE",
    "MARKER_MACHINE",
    "assert_snapshot_matches",
    "comparable_snapshot",
    "send_all",
]
