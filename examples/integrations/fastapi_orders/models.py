# examples/integrations/fastapi_orders/models.py
# -----------------------------------------------------------------------------
# 🧾 Typed events and context for the order chart
# -----------------------------------------------------------------------------
# 🏛️ One `EventModel` per client-sendable event. `events_union()` turns them
#    into the machine's `event_schemas=`, and `StatechartRouter` turns the
#    same models into the OpenAPI discriminated union -- one source of truth
#    for "what may a client send".
# -----------------------------------------------------------------------------
"""Pydantic models: events (`EventModel`) and the order context."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from xstate_statemachine.contrib.pydantic import EventModel, events_union


# -----------------------------------------------------------------------------
# 📨 Events
# -----------------------------------------------------------------------------
class AddItem(EventModel):
    type: Literal["ADD_ITEM"] = "ADD_ITEM"
    sku: str = Field(min_length=1, max_length=64)
    qty: int = Field(ge=1, le=100)


class Checkout(EventModel):
    type: Literal["CHECKOUT"] = "CHECKOUT"


class Pay(EventModel):
    type: Literal["PAY"] = "PAY"
    card_token: str = Field(min_length=1, max_length=128)


class Cancel(EventModel):
    type: Literal["CANCEL"] = "CANCEL"
    reason: str = Field(default="customer request", max_length=200)


class Fulfil(EventModel):
    type: Literal["FULFIL"] = "FULFIL"


class Packed(EventModel):
    type: Literal["PACKED"] = "PACKED"


class LabelPrinted(EventModel):
    type: Literal["LABEL_PRINTED"] = "LABEL_PRINTED"


EVENT_MODELS = (
    AddItem,
    Checkout,
    Pay,
    Cancel,
    Fulfil,
    Packed,
    LabelPrinted,
)
EVENT_SCHEMAS = events_union(*EVENT_MODELS)


# -----------------------------------------------------------------------------
# 📦 Context
# -----------------------------------------------------------------------------
class LineItem(BaseModel):
    sku: str
    qty: int
    unit_cents: int


class OrderContext(BaseModel):
    """Validated after every action that changes context
    (`context_model(OrderContext)`)."""

    items: List[LineItem] = []
    total_cents: int = Field(default=0, ge=0)
    card_token: Optional[str] = None
    attempt: int = Field(default=0, ge=0)
    charge_id: Optional[str] = None
    cancel_reason: Optional[str] = None


def public_context(ctx: dict) -> dict:
    """What the API shows of the context (X0.1: never the card token)."""
    return {
        "items": [
            i if isinstance(i, dict) else i.model_dump()
            for i in ctx.get("items", [])
        ],
        "total_cents": ctx.get("total_cents", 0),
        "attempt": ctx.get("attempt", 0),
        "charge_id": ctx.get("charge_id"),
        "cancel_reason": ctx.get("cancel_reason"),
    }
