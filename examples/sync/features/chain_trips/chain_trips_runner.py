# examples/sync/features/chain_trips/chain_trips_runner.py
# -----------------------------------------------------------------------------
# 🔁 Runaway chains are cut, and the cut stays on the record (0.9.0, #222/#226)
# -----------------------------------------------------------------------------
"""Demonstrates ``maxIterations`` and the sticky chain-trip signal.

An action that ``raise``s the very event that re-triggers it, with no delay,
is a self-fed loop. ``maxIterations`` bounds that work *within a step*: the
tail is discarded as a ``RunawayChainError`` and the machine keeps running.

``last_error`` carries the error -- but only until the next cleanly handled
event, because it describes the most recent step. A supervisor polling it
races the machine's own traffic and loses. The sticky signal is
``chain_trips`` (a monotonic count) and ``last_chain_error`` (latched until
``clear_chain_error()``). Both survive a snapshot round-trip, so a restart
is not an implicit acknowledgement that work was discarded.
"""

import json
import logging
import os
import sys
from typing import Any, Dict

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
)
from xstate_statemachine import (
    PluginBase,
    RestoredError,
    RunawayChainError,
    SyncInterpreter,
    create_machine,
)

if hasattr(sys.stdout, "reconfigure"):  # pragma: no cover - platform detail
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.ERROR, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 🌀 `spin` re-enters itself on LAP and raises LAP again on entry: a
#    zero-delay self-cycle. BENIGN is an ordinary, correctly handled event.
CONFIG: Dict[str, Any] = {
    "id": "trip",
    "initial": "spin",
    "maxIterations": 6,
    "states": {
        "spin": {
            "entry": [{"type": "raise", "params": {"event": "LAP"}}],
            "on": {
                "LAP": {"target": "spin", "reenter": True},
                "BENIGN": {"target": "spin", "reenter": False},
            },
        }
    },
}


class TripWatcher(PluginBase):
    """🔔 The push notification: fires ONCE per trip, however many events
    that trip discards (`on_event_dropped` still fires per event)."""

    def __init__(self) -> None:
        self.trips = 0

    def on_chain_budget_exceeded(self, interp, error, event) -> None:
        self.trips += 1
        logger.info(
            f"🔔 trip #{self.trips}: limit={error.limit} first cut='{event.type}'"
        )


def main() -> None:
    """🚀 Trip the budget, watch `last_error` erase, watch the latch hold."""
    print("\n--- 🔁 Chain Trips Simulation ---")

    watcher = TripWatcher()
    interp = SyncInterpreter(create_machine(CONFIG)).use(watcher).start()

    print("\n--- the entry raise loops; maxIterations=6 cuts it ---")
    assert isinstance(interp.last_error, RunawayChainError)
    assert interp.chain_trips == 1
    assert watcher.trips == 1
    logger.info(f"last_error={type(interp.last_error).__name__} chain_trips=1")

    print("\n--- one benign event erases last_error; the latch holds ---")
    interp.send("BENIGN")
    assert interp.last_error is None  # per-step read: reset by a clean step
    assert isinstance(interp.last_chain_error, RunawayChainError)  # latched
    assert interp.chain_trips == 1
    logger.info("last_error=None, last_chain_error still set, chain_trips=1")

    print("\n--- the record crosses a snapshot round-trip ---")
    blob = interp.get_snapshot()
    interp.stop()
    restored = SyncInterpreter.from_snapshot(blob, create_machine(CONFIG))
    assert restored.chain_trips == 1
    assert isinstance(restored.last_chain_error, RestoredError)
    logger.info(
        f"restored: chain_trips={restored.chain_trips} "
        f"last_chain_error={type(restored.last_chain_error).__name__}"
    )
    print(
        "     snapshot keys:",
        sorted(
            k
            for k in json.loads(blob)
            if k in ("chain_trips", "last_chain_error")
        ),
    )

    print("\n--- only clear_chain_error() acknowledges it ---")
    restored.clear_chain_error()
    assert restored.last_chain_error is None
    assert restored.chain_trips == 1  # the count is never cleared
    logger.info("acknowledged; chain_trips stays at 1")

    print("\n--- ✅ Simulation Complete ---")


if __name__ == "__main__":
    main()
