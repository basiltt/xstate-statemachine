---
title: "xstate-statemachine vs LangGraph"
description: "An honest comparison of xstate-statemachine's [agents] extra and LangGraph: hierarchy, guards as policy, durable timeouts, human-in-the-loop, persistence, observability, and when to choose which."
permalink: /guide/vs-langgraph/
---

# xstate-statemachine vs LangGraph

LangGraph is the most widely used agent-orchestration library in Python: a graph of nodes over typed state, with checkpointers, `interrupt()` for human input, streaming, LangSmith (tracing, and Studio for debugging). It is excellent at what it does, and the two are not either/or.

{% assign c = site.data.comparisons.competitors.langgraph %}
This table is generated from [`docs/_data/comparisons.json`](https://github.com/basiltt/xstate-statemachine/blob/main/docs/_data/comparisons.json), and corrections are welcome as PRs against that file. Every row carries a source note. It was checked against {{ c.checked }}; see [{{ c.name }}]({{ c.url }}) for the current state.

## Feature table

| Capability | xstate-statemachine | LangGraph | Source |
|:--|:--|:--|:--|
{% for row in site.data.comparisons.rows %}| {{ row.feature }} | {{ row.ours }} | {{ row.langgraph }} | {{ row.source.langgraph }} |
{% endfor %}

<!-- rows (kept in sync by tests/test_comparisons.py): Hierarchy (nested states); Parallel regions; Guards as policy; `after` timeouts; Human-in-the-loop as durable state; Persistence / replay; Visual editor; Typed context / events; Observability; Multi-agent; Incremental adoption -->

## When to choose LangGraph

- You are already on LangChain and want the ecosystem: integrations, prebuilt agents, supervisor and swarm libraries.
- Your control flow is mostly a dataflow graph, and time travel and LangSmith are what you need from persistence and observability.
- You want a hosted platform for deployment (LangSmith Deployment, formerly LangGraph Platform) and LangSmith Studio for debugging.

## When to choose xstate-statemachine

- The risky part of the loop has to be **policy, not prompt**: which tools are legal in which state, re-enforced inside `run_tool` even when a guard is edited out or a snapshot is forged.
- You need **durable timers**: a human approval that escalates after an hour, even if every worker restarted in between.
- You want the control flow as **XState JSON** that product and ops people can read and edit in the Stately editor.
- You want to adopt it **one node at a time**: `statechart_node` drops a chart into your existing graph, and its snapshot rides in your checkpointer.

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
