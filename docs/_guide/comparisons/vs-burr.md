---
title: "xstate-statemachine vs Burr"
description: "An honest comparison of xstate-statemachine's [agents] extra and Burr: hierarchy, guards as policy, durable timeouts, human-in-the-loop, persistence, observability, and when to choose which."
permalink: /guide/vs-burr/
---

# xstate-statemachine vs Burr

Burr (Apache, incubating) models an application as actions and transitions over a state object, with persisters, a tracking UI and OpenTelemetry. It is the closest in spirit: explicit state machines for LLM apps.

{% assign c = site.data.comparisons.competitors.burr %}
This table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json), and corrections are welcome as PRs against that file. Every row carries a source note. It was checked against {{ c.checked }}; see [{{ c.name }}]({{ c.url }}) for the current state. A test (`tests/test_battle_291_a.py`) fails the nightly `comparisons` CI job when this check is more than 180 days old, or when the installed release's major version differs from the one checked, so the table cannot silently go stale (a pull request is never blocked by a competitor's release).

## Feature table

| Capability | xstate-statemachine | Burr | Source |
|:--|:--|:--|:--|
{% for row in site.data.comparisons.rows %}| {{ row.feature }} | {{ row.ours }} | {{ row.burr }} | {{ row.source.burr }} |
{% endfor %}

<!-- rows (kept in sync by tests/test_comparisons.py): Hierarchy (nested states); Parallel regions; Guards as policy; `after` timeouts; Human-in-the-loop as durable state; Persistence / replay; Visual editor; Typed context / events; Observability; Multi-agent; Incremental adoption -->

## When to choose Burr

- You want the Burr UI for step-by-step tracking and replay out of the box.
- A flat action graph with `when` conditions fits your app, and you do not need nested or parallel states.
- You prefer defining the machine with Python decorators over a JSON chart.
- You want Burr's persisters for Postgres, Redis, MongoDB and SQLite, and `MapStates` / `MapActions` for fan-out, without writing a chart.

## When to choose xstate-statemachine

- You need **hierarchy and parallel regions** with standard statechart semantics (XState v5), not only flat transitions.
- You want **durable `after` deadlines**: timeouts and escalations that survive restarts.
- The chart should be **portable XState JSON**, editable in Stately and shareable with a TypeScript frontend.
- You want per-state tool allow-lists that `run_tool` enforces regardless of the guards (X0.13).

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
