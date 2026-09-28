# tests/patterns/test_hook_snapshot_parity.py
"""#265: `get_persisted_snapshot()` is legal from inside
`on_event_processed` on BOTH engines (the step has settled), while it is
still refused from `on_transition` (mid-step). The dead-letter plugin,
audit rows (#262) and the idempotency mark (#261) rely on this."""

from __future__ import annotations

import asyncio
import unittest
from typing import Any, List

from src.xstate_statemachine import (
    Interpreter,
    PluginBase,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.exceptions import SnapshotMidStepError

CFG = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


class Probe(PluginBase):
    def __init__(self) -> None:
        self.processed: List[Any] = []
        self.transition_error: Any = None

    def on_transition(self, i: Any, *_: Any) -> None:
        try:
            i.get_persisted_snapshot()
        except SnapshotMidStepError as exc:
            self.transition_error = exc

    def on_event_processed(self, i: Any, event: Any, receipt: Any) -> None:
        self.processed.append(i.get_persisted_snapshot()["state_ids"])


class TestHookSnapshotParity(unittest.TestCase):
    def test_sync(self) -> None:
        p = Probe()
        i = SyncInterpreter(create_machine(CFG)).use(p).start()
        r = i.send("GO", wait=True)
        i.stop()
        self.assertTrue(r.changed)
        self.assertEqual(p.processed, [["m.b"]])
        self.assertIsInstance(p.transition_error, SnapshotMidStepError)

    def test_async(self) -> None:
        p = Probe()

        async def go() -> Any:
            i = await Interpreter(create_machine(CFG)).use(p).start()
            r = await i.send("GO", wait=True)
            await i.stop()
            return r

        r = asyncio.run(go())
        self.assertTrue(r.changed)
        self.assertEqual(p.processed, [["m.b"]])
        self.assertIsInstance(p.transition_error, SnapshotMidStepError)


if __name__ == "__main__":
    unittest.main()
