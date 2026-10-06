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


class _StampIdempotencyKey(PluginBase):  # type: ignore[type-arg]
    """Put a request's ``Idempotency-Key`` on the FIRST user send of an
    `act()` so the inbox plugin (which runs after this one) sees it.

    🔥 #276 review (M2): `get_interpreter` validated the header and then
    left it on `request.state` for the handler to forward -- a handler
    that forgot got a silent 200 without dedup, the very hole the 501
    closed on `/send`. The key is attached once; a second user send in
    the same request is not a retry of the first and is left alone.
    """

    def __init__(self, key: str) -> None:
        self.key = key
        self._done = False

    def on_before_send(self, interpreter: Any, event: Any) -> Any:
        if self._done:
            return None
        payload = getattr(event, "payload", None)
        if isinstance(payload, dict) and "idempotency_key" not in payload:
            payload["idempotency_key"] = self.key
        self._done = True
        return None
