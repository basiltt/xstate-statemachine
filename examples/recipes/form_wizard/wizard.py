# examples/recipes/form_wizard/wizard.py
# -----------------------------------------------------------------------------
# 🧙 A multi-step form driven by a chart kept in UI session state (#308)
# -----------------------------------------------------------------------------
# 🏛️ Streamlit reruns the whole script on every click; Gradio calls a
#    function per click. Neither keeps Python objects alive between
#    interactions in a way you control -- so the wizard keeps only the
#    SNAPSHOT (a JSON string) in `st.session_state` / `gr.State`, and each
#    click is restore -> send -> snapshot. BACK / NEXT are events; the chart
#    decides whether NEXT is allowed (guards), not scattered `if`s in the UI.
# -----------------------------------------------------------------------------
"""Framework-free wizard core shared by the Streamlit and Gradio apps."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, MutableMapping, Optional

from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine

HERE = Path(__file__).resolve().parent
PLANS = ("free", "pro", "team")
KEY = "xsm_wizard"


def _merged(ctx: Dict, e: Any) -> Dict:
    return {**ctx, **(getattr(e, "payload", None) or {})}


def build_machine() -> Any:
    def save_fields(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx.update({k: v for k, v in e.payload.items() if k in ctx})

    logic = MachineLogic(
        actions={"saveFields": save_fields},
        guards={
            "accountValid": lambda c, e: "@" in str(_merged(c, e)["email"]),
            "planChosen": lambda c, e: _merged(c, e)["plan"] in PLANS,
            "termsAccepted": lambda c, e: bool(_merged(c, e)["accepted"]),
        },
    )
    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    return create_machine(config, logic=logic)


MACHINE = build_machine()


def diagram() -> str:
    """Mermaid source -- what ``xsm diagram machine.json`` prints."""
    return str(MACHINE.to_mermaid())


class Wizard:
    """A view over one session's snapshot. *session* is any mutable
    mapping: ``st.session_state``, a dict inside ``gr.State``, a test dict.
    """

    def __init__(self, session: MutableMapping[str, Any]) -> None:
        self.session = session

    def _interp(self) -> Any:
        blob: Optional[str] = self.session.get(KEY)
        if blob is None:
            return SyncInterpreter(MACHINE).start()
        return SyncInterpreter.from_snapshot(blob, MACHINE).start()

    def send(self, event: str, **fields: Any) -> bool:
        """Apply *event*; return whether the step changed (a failed
        guard -- invalid input -- returns False and keeps the step)."""
        interp = self._interp()
        receipt = interp.send(event, wait=True, **fields)
        self.session[KEY] = interp.get_snapshot()
        interp.stop()
        return bool(receipt.changed)

    @property
    def step(self) -> str:
        return str(self._view()["value"])

    @property
    def data(self) -> Dict[str, Any]:
        return dict(self._view()["context"])

    def _view(self) -> Dict[str, Any]:
        interp = self._interp()
        out = {"value": interp.value, "context": dict(interp.context)}
        interp.stop()
        return out
