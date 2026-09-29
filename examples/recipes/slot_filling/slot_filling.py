# examples/recipes/slot_filling/slot_filling.py
# -----------------------------------------------------------------------------
# 💬 Chatbot slot filling as a chart (#308)
# -----------------------------------------------------------------------------
# 🏛️ The NLU (an LLM, a regex, Rasa) only EXTRACTS: it turns a user turn
#    into `{"slot": value}` pairs sent as `USER_SAID`. The chart decides the
#    conversation: each `USER_SAID` re-enters `collecting` (a self-transition
#    that also restarts the 30 s silence timer), `always` + `allSlotsFilled`
#    moves on the moment the last slot lands, and silence nudges twice
#    before abandoning. Pure engine -- no I/O; `say()` is the only output.
# -----------------------------------------------------------------------------
"""Slot-filling logic: guards and actions for `machine.json`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from xstate_statemachine import MachineLogic, create_machine

HERE = Path(__file__).resolve().parent
MAX_NUDGES = 2
PROMPTS = {
    "date": "What day would you like?",
    "party_size": "For how many people?",
    "name": "And the name for the booking?",
}


def missing(ctx: Dict[str, Any]) -> List[str]:
    return [k for k, v in ctx["slots"].items() if v is None]


def build_machine(say: Optional[Callable[[str], None]] = None) -> Any:
    out = say or print

    def fill_slots(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        for k, v in e.payload.items():
            if k in ctx["slots"] and v not in (None, ""):
                ctx["slots"][k] = v
        ctx["nudges"] = 0
        todo = missing(ctx)
        if todo:
            out(PROMPTS[todo[0]])

    def nudge(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["nudges"] += 1
        out(f"Still there? {PROMPTS[missing(ctx)[0]]}")

    def ask_to_confirm(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        s = ctx["slots"]
        out(f"Book {s['party_size']} on {s['date']} for {s['name']}?")

    def clear_slots(i: Any, ctx: Dict, e: Any, a: Any) -> None:
        ctx["slots"] = {k: None for k in ctx["slots"]}
        out(PROMPTS["date"])

    logic = MachineLogic(
        actions={
            "fillSlots": fill_slots,
            "nudge": nudge,
            "askToConfirm": ask_to_confirm,
            "clearSlots": clear_slots,
        },
        guards={
            "allSlotsFilled": lambda ctx, e: not missing(ctx),
            "canNudge": lambda ctx, e: ctx["nudges"] < MAX_NUDGES,
        },
    )
    config = json.loads((HERE / "machine.json").read_text("utf-8"))
    return create_machine(config, logic=logic)
