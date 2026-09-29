# src/xstate_statemachine/contrib/testing/_async_fixtures.py
# -----------------------------------------------------------------------------
# ⚡ The async engine behind `xsm_ainterp` (#268)
# -----------------------------------------------------------------------------
# 🏛️ Imports pytest-asyncio, so it is NEVER imported at plugin load: the
#    pytest plugin registers this module from `pytest_configure` only when
#    the pytest-asyncio plugin is active in the session.
# -----------------------------------------------------------------------------
"""Internal: the ``_xsm_ainterp_async`` fixture (needs pytest-asyncio)."""

from __future__ import annotations

from typing import Any

import pytest_asyncio

from ...clock import SimulatedClock
from ...models import MachineNode
from .pytest_plugin import _start_async, _stop_async


@pytest_asyncio.fixture
async def _xsm_ainterp_async(
    xsm_machine: MachineNode, xsm_clock: SimulatedClock
) -> Any:
    """Internal: the async engine behind ``xsm_ainterp``."""
    interp = await _start_async(xsm_machine, xsm_clock)
    try:
        yield interp
    finally:
        await _stop_async(interp)
