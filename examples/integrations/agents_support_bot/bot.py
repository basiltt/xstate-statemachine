# examples/integrations/agents_support_bot/bot.py
# -----------------------------------------------------------------------------
# 🎧 Customer-support agent: TOOL_LOOP + order lookup + human-approved refund
# -----------------------------------------------------------------------------
# 🏛️ The model proposes, the machine decides:
#
#      * `machine.json` is TOOL_LOOP with both tool states narrowed to
#        `lookup_order` and `refund_order` -- nothing else can run;
#      * `refund_order` is `side_effect=True`, so the agent PARKS in
#        `awaiting_human` (persisted in SQLiteStore) until a human approves;
#      * budgets cap turns / tokens / dollars; every step goes to a JSONL
#        trace with no prompt content.
#
#    Order lookup calls the FastAPI example's `GET /orders/{id}` through an
#    in-process `TestClient` when that example is importable, else a local
#    stub with the same response shape.
# -----------------------------------------------------------------------------
"""Support-bot wiring: tools, model selection, `run_ticket` / `approve`."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from xstate_statemachine import create_machine
from xstate_statemachine.contrib.agents import (
    AgentTracePlugin,
    FakeModel,
    agent_logic,
    run_agent,
    tool,
    tool_registry,
)
from xstate_statemachine.persistence import SQLiteStore

HERE = Path(__file__).resolve().parent
ORDERS_EXAMPLE = HERE.parent / "fastapi_orders"
BUDGETS = {"max_turns": 6, "max_tokens": 20_000, "max_usd": 0.05}
SYSTEM_PROMPT = (
    "You are a support agent. Look orders up before answering. Refunds "
    "need a human's approval; propose them with refund_order."
)

#: ``(order_id) -> order dict`` -- how the bot reads an order.
OrderFetcher = Callable[[int], Dict[str, Any]]


# -----------------------------------------------------------------------------
# 📦 Order API: the FastAPI example in-process, or a stub
# -----------------------------------------------------------------------------
def stub_orders() -> OrderFetcher:
    """Same shape as ``GET /orders/{id}`` of the FastAPI example."""

    def fetch(order_id: int) -> Dict[str, Any]:
        return {
            "state": "paid",
            "context": {
                "items": [{"sku": "mug", "qty": 2, "unit_cents": 1200}],
                "total_cents": 2400,
            },
        }

    return fetch


def fastapi_orders(db_dir: Optional[str] = None) -> OrderFetcher:
    """`httpx` against the FastAPI orders example via `TestClient`.

    Seeds each looked-up order with one item so there is something to
    refund. Raises `ImportError` when the example or fastapi is missing.
    """
    from fastapi.testclient import TestClient

    if str(ORDERS_EXAMPLE) not in sys.path:
        sys.path.insert(0, str(ORDERS_EXAMPLE))
    import app as orders  # type: ignore[import-not-found]

    from xstate_statemachine.persistence import SQLiteInbox

    path = Path(db_dir or tempfile.mkdtemp()) / "orders.db"
    store = SQLiteStore(str(path))
    client = TestClient(
        orders.create_app(
            orders.build_registry(store, SQLiteInbox(store)), debug=False
        )
    )
    headers = {"x-customer": "support-bot"}

    def fetch(order_id: int) -> Dict[str, Any]:
        client.post(
            f"/orders/{order_id}/events/ADD_ITEM",
            json={"sku": "mug", "qty": 2},
            headers=headers,
        )
        resp = client.get(f"/orders/{order_id}", headers=headers)
        resp.raise_for_status()
        body = resp.json()
        return {"state": body["state"], "context": body["context"]}

    return fetch


def default_orders() -> OrderFetcher:
    try:
        return fastapi_orders()
    except ImportError:
        return stub_orders()


# -----------------------------------------------------------------------------
# 🧰 Tools
# -----------------------------------------------------------------------------
def build_tools(fetch: OrderFetcher, refunds: List[Dict[str, Any]]) -> Any:
    def lookup_order(order_id: int) -> Dict[str, Any]:
        """Look up an order by id: its state, items and total."""
        return fetch(order_id)

    def refund_order(order_id: int, amount_cents: int) -> str:
        """Refund an order (needs human approval)."""
        refunds.append({"order_id": order_id, "amount_cents": amount_cents})
        return f"refunded {amount_cents} cents on order {order_id}"

    return tool_registry(
        tool(lookup_order, timeout_s=5),
        tool(refund_order, timeout_s=5, side_effect=True),
    )


# -----------------------------------------------------------------------------
# 🤖 Models
# -----------------------------------------------------------------------------
def fake_model(order_id: int = 42) -> FakeModel:
    """Scripted, offline: look up → propose refund → confirm."""
    return FakeModel(
        [
            {"tool": "lookup_order", "args": {"order_id": order_id}},
            {
                "tool": "refund_order",
                "args": {"order_id": order_id, "amount_cents": 2400},
            },
            {"text": f"Order {order_id} has been refunded (24.00)."},
        ]
    )


def provider_model(name: str) -> Any:
    """A real model -- opt-in, needs the SDK and an API key."""
    if name == "openai":
        import openai

        from xstate_statemachine.contrib.agents.providers.openai import (
            openai_model,
        )

        return openai_model(openai.AsyncOpenAI(), model="gpt-4o-mini")
    if name == "anthropic":
        import anthropic

        from xstate_statemachine.contrib.agents.providers.anthropic import (
            anthropic_model,
        )

        return anthropic_model(anthropic.AsyncAnthropic())
    raise ValueError(f"unknown provider {name!r}")


# -----------------------------------------------------------------------------
# 🏃 Bot
# -----------------------------------------------------------------------------
class SupportBot:
    """One machine, one store, one trace; tickets are store keys."""

    def __init__(
        self,
        model: Any,
        *,
        fetch: Optional[OrderFetcher] = None,
        db: str = "support.db",
        trace: Optional[str] = "support-trace.jsonl",
    ) -> None:
        self.refunds: List[Dict[str, Any]] = []
        self.tools = build_tools(fetch or default_orders(), self.refunds)
        self.tracer = AgentTracePlugin(trace)
        chart = json.loads((HERE / "machine.json").read_text("utf-8"))
        self.machine = create_machine(
            chart,
            logic=agent_logic(
                model,
                self.tools,
                budgets=BUDGETS,
                system_prompt=SYSTEM_PROMPT,
                tracer=self.tracer,
                human_timeout_s=3600,
            ),
        )
        self.store = SQLiteStore(db)

    async def ticket(self, key: str, prompt: str) -> Any:
        return await run_agent(
            self.machine, store=self.store, key=key, prompt=prompt
        )

    async def decide(self, key: str, approve: bool) -> Any:
        return await run_agent(
            self.machine, store=self.store, key=key, approve=approve
        )

    def close(self) -> None:
        self.store.close()


def env_provider() -> Optional[str]:
    """``openai`` / ``anthropic`` when its API key is set, else ``None``."""
    for name, var in (
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
    ):
        if os.environ.get(var):
            return name
    return None
