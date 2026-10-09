# Support bot — an LLM agent as a statechart

A customer-support agent built on the `TOOL_LOOP` reference chart from
`xstate-statemachine[agents]`. It looks orders up, proposes refunds, and **cannot
issue a refund until a human approves it**. The model proposes, the machine
decides.

| Piece | Where |
|:--|:--|
| Chart | `machine.json`: `TOOL_LOOP` with `meta.tools` narrowed to `lookup_order` and `refund_order` |
| Tools | `bot.py`: `lookup_order` calls the [FastAPI orders example](https://github.com/basiltt/xstate-statemachine/tree/main/examples/integrations/fastapi_orders) `GET /orders/{id}` through an in-process `TestClient` (or a local stub when it cannot be imported); `refund_order` is `side_effect=True` |
| Human approval | `refund_order` parks the agent in `awaiting_human`, a normal persisted state with a one-hour escalation deadline |
| Budgets | 6 turns, 20k tokens, $0.05 per ticket (`BUDGETS`) |
| Persistence | `SQLiteStore("support.db")`: each ticket is a key, and approval resumes the stored run |
| Trace | `support-trace.jsonl`: one JSON line per model/tool step, `gen_ai.*` field names, no prompt content |

## 2-minute walkthrough (no API key)

```bash
pip install "xstate-statemachine[agents,fastapi]" httpx
cd examples/integrations/agents_support_bot
python run.py --fake --prompt "refund order 42"
```

```text
[ticket:1a2b3c4d] state=supportBot.awaiting_human waiting=True
  needs approval: {"id": "call_9f2a1c3b_2_0", "name": "refund_order", "arguments": {"order_id": 42, "amount_cents": 2400}}
  human reviewer: approved
[ticket:1a2b3c4d] state=supportBot.done
answer: Order 42 has been refunded (24.00).
refunds executed: [{'order_id': 42, 'amount_cents': 2400}]
usage: {'turns': 3, 'input_tokens': 30, 'output_tokens': 15, 'cost_usd': 0.0}
```

What happened:

1. `FakeModel` (scripted and offline) asked for `lookup_order(42)`. That tool is in the state's allow-list, so `run_tool` ran it.
2. It then proposed `refund_order(42, 2400)`, a side-effect tool, so the chart moved to **`awaiting_human`** and `run_agent` returned. The snapshot, including the escalation deadline, is in `support.db`.
3. `run.py` played the reviewer. `bot.decide(key, approve=True)` sent `HUMAN_APPROVED` naming exactly the pending call id, and the refund ran once.

Run it again with `--reject`: the refund never executes, and the model is told it was declined.

In a real deployment, steps 2 and 3 are two HTTP requests, possibly hours apart and on different workers. See the FastAPI recipe in the [LLM agents guide](https://basiltt.github.io/xstate-statemachine/guide/integration-agents/).

## Operate it (the day after)

`run.py` plays a whole ticket in one process. In production the ticket,
the reviewer and the timeout worker are separate processes, often on
different replicas and hours apart. `ops.py` is that day, offline, on the
same `support.db`:

```bash
python ops.py open --key t-1 --prompt "refund order 42"
python ops.py open --key t-2 --order 7
python ops.py pending
python ops.py approve t-1
python ops.py approve t-1
python ops.py scan --at 99999999999
python ops.py pending
```

```text
[t-1] state=supportBot.awaiting_human waiting=True
[t-2] state=supportBot.awaiting_human waiting=True
t-1  refund_order {"order_id": 42, "amount_cents": 2400}
t-2  refund_order {"order_id": 7, "amount_cents": 2400}
[t-1] state=supportBot.done answer=Refund done.
refunds executed: [{'order_id': 42, 'amount_cents': 2400}]
error: t-1 is not waiting for a human
escalated: 1
```

What an operator needs to know:

- **Approval is a later run.** `approve` / `reject` load the ticket from the store and send `HUMAN_APPROVED` naming exactly the pending call ids. A second approval is refused (exit 2), so the refund runs once even if two reviewers click.
- **A resumed run continues the conversation.** The model in `approve` is asked only for the *next* turn, so its script is the closing answer alone.
- **Timeouts need the scanner.** A ticket nobody answers is escalated (to `error`, `kind: "human_timeout"`) by **one** `DueTimerScanner` per store — `python ops.py scan` from cron, or `scanner.run_forever()` in a worker. Reloading the ticket does not escalate it: a reload re-arms the timer. `--at` pretends it is later (here: far past the one-hour deadline); drop it in production.
- **Two replicas** share the store: each ticket is one key, and a concurrent second save loses with `ConflictError` instead of acting twice (`tests/test_battle_287_scenario.py`).
- **Alert on** the oldest `pending` ticket's age, `budget` errors, and bursts of `tool_denied` (prompt-injection attempts). See *Operations* in the [LLM agents guide](https://basiltt.github.io/xstate-statemachine/guide/integration-agents/#operations).

## Real model (opt-in)

```bash
pip install openai        # or anthropic
export OPENAI_API_KEY=... # or ANTHROPIC_API_KEY
python run.py --provider openai --prompt "Where is order 42? Please refund it."
```

Without the SDK or the key, `run.py` exits with status 2 and one line naming
the fix (`pip install openai` / `OPENAI_API_KEY`); no ticket is started.

Only the model changes. The allow-list, budgets and human gate stay exactly as they were.

## Structured intake

A refund request can be collected as a validated object instead of free
text: give the model state a `meta.output_model` and switch on
`structured_output`. A reply that is not valid JSON, has the wrong shape,
or breaks a `Field(...)` range is re-prompted (`RETRY_OUTPUT`, a counted
turn) and never reaches `result`. The battle scenario
`tests/test_battle_289_scenario.py` runs 100 tickets through exactly this
`OrderRef` schema.

```python
import sys
from pydantic import BaseModel, Field
from xstate_statemachine.contrib.agents import FakeModel, load_chart, run_agent_sync, structured_output

class OrderRef(BaseModel):
    order_id: int = Field(gt=0, le=10**6)
    reason: str = Field(min_length=3, max_length=200)

sys.modules["intake"] = sys.modules[__name__]
chart = load_chart()
chart["states"]["awaiting_model"]["meta"]["output_model"] = "intake:OrderRef"
model = FakeModel([{"text": '{"order_id": -1, "reason": "oops"}'},
                   {"text": '{"order_id": 42, "reason": "damaged"}'}], is_async=False)
res = run_agent_sync(chart, model=model, prompt="refund order 42",
                     **structured_output(retries=2, use_instructor=False))
assert res.output == {"order_id": 42, "reason": "damaged"}
assert res.context["output_retries"] == 1
```

See [Structured output per state](https://basiltt.github.io/xstate-statemachine/guide/integration-agents/#structured-output-per-state).

## Supervisor: many tickets, one budget

`load_chart("supervisor")` runs a planner and a worker pool in parallel
regions; `spawn_agent` gives every ticket its own `TOOL_LOOP` sub-agent with
its **own** `max_turns`, and one `BudgetPlugin` caps the **whole tree**.
Workers get `lookup_order` only: a worker can never refund, because its
tools must be a subset of the spawning state's `meta.tools` (the chart ships
`["search", "fetch"]` as placeholders -- replace them with your tools).

<!-- doc-requires: pydantic -->
```python
import bot
from xstate_statemachine import MachineLogic, SyncInterpreter, create_machine
from xstate_statemachine.contrib.agents import (
    BudgetPlugin, FakeModel, handoff_guard, load_chart, spawn_agent, tool_registry)

lookup_only = tool_registry(bot.build_tools(bot.stub_orders(), []).get("lookup_order"))
chart = load_chart("supervisor")
workers = chart["states"]["running"]["states"]["workers"]
workers["meta"]["tools"] = workers["states"]["working"]["meta"]["tools"] = ["lookup_order"]

def store_plan(i, ctx, e, a):
    ctx["tasks"], ctx["outstanding"] = list(e.payload["tasks"]), len(e.payload["tasks"])

def hand_off(i, ctx, e, a):
    for t in ctx["tasks"]:
        i.send({"type": "HANDOFF", "from": "planner", "to": "worker", "task": t})

def collect(key, field):
    return lambda i, ctx, e, a: ctx.update({key: ctx[key] + [e.payload[field]]})

model = FakeModel([{"tool": "lookup_order", "args": {"order_id": 42}},
                   {"text": "order 42 is paid"}] * 3, is_async=False,
                  default_usage={"input_tokens": 100, "output_tokens": 20, "cost_usd": 0.01})
budget = BudgetPlugin(max_total_usd=0.04)               # ONE budget for the tree
logic = MachineLogic(
    actions={"storePlan": store_plan, "handOffTasks": hand_off,
             "collectResult": collect("results", "result"),
             "collectFailure": collect("failures", "error")},
    guards={"allWorkersReported": lambda c, e: 0 < c["outstanding"] <= len(c["results"]) + len(c["failures"])},
).merge(
    spawn_agent(None, model, lookup_only, budget={"max_turns": 3},  # each worker's OWN
                parent_tools=["lookup_order"], name="worker"),
    handoff_guard({"planner": ["worker"]}),
    budget.guards(),
)
sup = SyncInterpreter(create_machine(chart, logic=logic)).use(budget).start()
sup.send("PLAN", tasks=["ticket 1", "ticket 2", "ticket 3"])
print(sup.current_state_ids, sup.context["results"], sup.context["total_usage"]["cost_usd"])
assert sup.context["budget_exceeded"]                   # tripped by worker 2's report...
assert len(sup.context["results"]) == 2                 # ...whose result is still collected
assert sorted(sup.context["usage_by_agent"]) == ["supervisor:worker-1", "supervisor:worker-2"]
```

Worker 2's report crosses `$0.04`, so ticket 3 is **never spawned**
(`spawnWorker` logs `global budget exceeded; not spawning`) and
`BUDGET_EXCEEDED` ends the worker region. `usage_by_agent` tells you who
spent it. The battle scenario `tests/test_battle_290_scenario.py` runs 100
tickets through this shape.

## Drop the bot into a LangGraph graph

Already on LangGraph? Keep your graph and make this bot **one node**: its
snapshot rides in the graph state, so your checkpointer persists the parked
refund, and the allow-list, budgets and human gate still apply inside the
node. Needs `pip install langgraph` (not part of `[agents]`).

<!-- doc-requires: langgraph -->
```python
import json
from typing import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
import bot
from xstate_statemachine import create_machine
from xstate_statemachine.contrib.agents import FakeModel, agent_logic, pending_approval
from xstate_statemachine.contrib.agents.langgraph import route_by_statechart, statechart_node

refunds = []
model = FakeModel([{"tool": "refund_order", "args": {"order_id": 7, "amount_cents": 500}},
                   {"text": "Order 7 refunded."}], is_async=False)
machine = create_machine(
    json.loads((bot.HERE / "machine.json").read_text("utf-8")),
    logic=agent_logic(model, bot.build_tools(bot.stub_orders(), refunds),
                      budgets=bot.BUDGETS, system_prompt=bot.SYSTEM_PROMPT))

class S(TypedDict, total=False):
    xsm: dict
    event: dict

g = StateGraph(S)
g.add_node("bot", statechart_node(machine, event_from_state=lambda s: s.get("event")))
g.set_entry_point("bot")
g.add_conditional_edges("bot", route_by_statechart(machine, {}, default=END))
app = g.compile(checkpointer=MemorySaver())
cfg = {"configurable": {"thread_id": "ticket-7"}}

out = app.invoke({"event": {"type": "START", "prompt": "Refund order 7"}}, cfg)
print(out["xsm"]["value"])                      # awaiting_human -- nothing refunded
ids = [c["id"] for c in pending_approval(out["xsm"]["context"])]
out = app.invoke({"event": {"type": "HUMAN_APPROVED", "call_ids": ids}}, cfg)
print(out["xsm"]["value"], len(refunds))        # done 1
```

`tests/test_battle_288_scenario.py` runs the three-node version
(classify → bot → reply) through a hundred threads and a restart, and shows
a forged snapshot cannot run the refund. Recipes and troubleshooting:
[LangGraph interop](https://basiltt.github.io/xstate-statemachine/guide/integration-agents/#langgraph-interop).

## Tests

```bash
python -m pytest tests -q       # FakeModel only; no key, no network
```

They cover: approval runs the refund exactly once, a rejected refund never runs, a
prompt-injected tool outside the allow-list ends in `error` (`tool_denied`), a looping
model is stopped by the turn budget, lookup goes through the FastAPI example,
`run.py --fake` finishes offline, and every command in this README runs as
written (`tests/test_readme_commands.py`).
