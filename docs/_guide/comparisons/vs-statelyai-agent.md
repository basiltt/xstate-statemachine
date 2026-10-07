---
title: "xstate-statemachine vs @statelyai/agent"
description: "An honest comparison of xstate-statemachine's [agents] extra and @statelyai/agent: hierarchy, guards as policy, durable timeouts, human-in-the-loop, persistence, observability, and when to choose which."
permalink: /guide/vs-statelyai-agent/
---

# xstate-statemachine vs @statelyai/agent

`@statelyai/agent` is Stately's TypeScript library for agents built on XState and the Vercel AI SDK. Same chart model, different runtime.

{% assign c = site.data.comparisons.competitors.statelyai_agent %}
This table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json), and corrections are welcome as PRs against that file. Each cell describes documented behaviour at the time of writing; check [{{ c.name }}]({{ c.url }}) for the current state.

## Feature table

| Capability | xstate-statemachine | @statelyai/agent |
|:--|:--|:--|
{% for row in site.data.comparisons.rows %}| {{ row.feature }} | {{ row.ours }} | {{ row.statelyai_agent }} |
{% endfor %}

<!-- rows (kept in sync by tests/test_comparisons.py): Hierarchy (nested states); Parallel regions; Guards as policy; `after` timeouts; Human-in-the-loop as durable state; Persistence / replay; Visual editor; Typed context / events; Observability; Multi-agent; Incremental adoption -->

## When to choose @statelyai/agent

- Your stack is TypeScript / Node and you want first-party Stately tooling.
- You already run XState in the browser or on Node and want the agent in the same process.

## When to choose xstate-statemachine

- Your stack is **Python**: the same XState JSON runs here, and a chart designed in Stately works in both.
- You want Python-side persistence (SQLite / Redis / Postgres stores), durable timers via `DueTimerScanner`, and FastAPI / Starlette / Litestar integration.
- You want the batteries in this extra: budgets as guards, per-state tool allow-lists re-checked in `run_tool`, `FakeModel`, JSONL traces, LangGraph and pydantic-ai interop.

## Ours, in 20 lines

This is a support agent. The refund tool is legal only in the tool states and needs a human to approve it, and the whole run is capped at 5 turns and 10 cents. It runs offline with `FakeModel`:

<!-- doc-requires: pydantic -->
```python
import asyncio
from xstate_statemachine.contrib.agents import FakeModel, load_chart, run_agent, tool, tool_registry

def lookup(order_id: int) -> str:
    """Look up an order."""
    return f"order {order_id}: shipped"

def refund(order_id: int) -> str:
    """Refund an order."""
    return "refunded"

chart = load_chart()                                            # TOOL_LOOP, plain XState JSON
for s in ("awaiting_model", "awaiting_tool"):
    chart["states"][s]["meta"]["tools"] = ["lookup", "refund"]  # policy lives in the chart
tools = tool_registry(tool(lookup, timeout_s=5), tool(refund, timeout_s=5, side_effect=True))
model = FakeModel([{"tool": "lookup", "args": {"order_id": 42}},
                   {"tool": "refund", "args": {"order_id": 42}}])

res = asyncio.run(run_agent(chart, model=model, tools=tools, prompt="refund 42",
                            budgets={"max_turns": 5, "max_usd": 0.10}))
assert res.waiting and res.final_state == "toolLoop.awaiting_human"   # durable: persist, resume later
```

See [LLM agents](../integration-agents/) for the full reference, including the [LangGraph interop](../integration-agents/#langgraph-interop) and [pydantic-ai](../integration-agents/#pydantic-ai) adapters.

New to the library? Start with the [integrations journey](../integrations/): pick your path, then a fifteen-minute tutorial.
