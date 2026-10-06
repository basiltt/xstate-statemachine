# src/xstate_statemachine/contrib/starlette/_act_helpers.py
"""Small `act()` / `send_event()` helpers split out of `registry.py`."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from ...events import Receipt
from ...plugins import PluginBase

_INTERNAL_PREFIXES = ("done.", "error.", "after.", "xstate.")


class _Recorder(PluginBase):  # type: ignore[type-arg]
    """Collect the changed USER receipts of one `act()` for fan-out."""

    def __init__(self) -> None:
        self.changed: List[Receipt] = []
        #: 🔥 #275 review (H1): actions that RAN. A targetless transition
        #: (``"NOTIFY": {"actions": "email"}``) leaves the snapshot equal
        #: but its side effects -- and the outbox / audit rows other
        #: plugins collected -- happened; skipping the save would discard
        #: those marks. "No-op" means no action ran AND nothing changed.
        self.actions_run = 0

    def on_action_execute(self, interpreter: Any, action: Any) -> None:
        self.actions_run += 1

    def on_event_processed(
        self, interpreter: Any, event: Any, receipt: Receipt
    ) -> None:
        etype = str(getattr(event, "type", ""))
        if receipt.changed and not etype.startswith(_INTERNAL_PREFIXES):
            self.changed.append(receipt)


class _SkipSave(Exception):
    """Raised inside `act()` to leave without persisting (duplicates)."""

    def __init__(self, receipt: Receipt, body: Dict[str, Any]) -> None:
        super().__init__("skip save")
        self.receipt = receipt
        self.body = body


def _comparable(interp: Any) -> Any:
    """The snapshot minus its capture time: equal means nothing changed."""
    try:
        data = json.loads(interp.get_snapshot())
    except Exception:  # noqa: BLE001 -- uncomparable: treat as changed
        return object()
    data.pop("taken_at", None)
    return data
