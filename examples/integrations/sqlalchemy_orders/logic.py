# examples/integrations/sqlalchemy_orders/logic.py
# -----------------------------------------------------------------------------
# 🧠 The order chart and its logic, shared by the sync and async variants
# -----------------------------------------------------------------------------
# 🏛️ Actions only touch `context` and are idempotent in effect: under
#    `send_with_retry` an action may run once per attempt (X0.3), so nothing
#    here talks to the outside world.
# -----------------------------------------------------------------------------
"""Order chart (`machine.json`) + `MachineLogic`."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from xstate_statemachine import MachineLogic, create_machine

HERE = Path(__file__).resolve().parent
CONFIG: Dict[str, Any] = json.loads((HERE / "machine.json").read_text("utf-8"))
#: The payment window, in seconds (the chart's ``after: 900000``).
PAYMENT_WINDOW_S = 900


def add_item(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["items"] = int(ctx["items"]) + 1
    ctx["total_cents"] = int(ctx["total_cents"]) + int(
        e.payload.get("price_cents", 0)
    )


def record_charge(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
    ctx["charge_id"] = str(e.payload.get("charge_id", "ch_demo"))


def has_items(ctx: Dict[str, Any], e: Any) -> bool:
    return int(ctx["items"]) > 0


LOGIC = MachineLogic(
    actions={"addItem": add_item, "recordCharge": record_charge},
    guards={"hasItems": has_items},
)


def order_machine() -> Any:
    """Build the order `MachineNode` (strict: unknown keys fail loudly)."""
    return create_machine(CONFIG, logic=LOGIC, strict_config=True)
