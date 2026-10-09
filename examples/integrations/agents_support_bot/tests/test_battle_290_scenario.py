# examples/integrations/agents_support_bot/tests/test_battle_290_scenario.py
"""#290 battle: multi-agent on a support day -- the support bot as a
SUPERVISOR that hands each ticket to a worker sub-agent (one `TOOL_LOOP`
actor per ticket with its OWN budget), a PIPELINE of researcher → writer
→ reviewer, and a DEBATE of parallel workers + a judge.

* **a hundred tickets through the supervisor** -- a planner region hands
  100 tasks to the worker region; one sub-agent per task with budget
  `max_turns=3`; every worker reports `AGENT_DONE` / `AGENT_FAILED`
  with usage; `total_usage` is the exact sum; `usage_by_agent` has 100
  distinct ids; the supervisor reaches `reporting`;
* **X0.13 across the tree** -- a worker whose tool list exceeds the
  spawning state's `meta.tools` is refused at construction AND at spawn
  (no sub-agent ever holds `refund_order` when the parent state does
  not); a worker's model proposing a tool outside its own allow-list is
  `tool_denied` in the CHILD and `AGENT_FAILED` in the parent -- the
  parent continues per chart;
* **budgets** -- a sub-agent exhausting ITS budget is `AGENT_FAILED`
  (`kind: budget`) while siblings finish; the global `BudgetPlugin`
  trips once, sends `BUDGET_EXCEEDED`, and `spawnWorker` refuses every
  later spawn (count of children never grows);
* **handoffs are guarded** -- `worker → judge` is `Receipt.denied`;
  a forged `HANDOFF` with no `from` is denied; only `planner → worker`
  passes;
* **pipeline** -- researcher → writer → reviewer with a bounded review
  loop: a reviewer that never approves ends `failed` after exactly
  `max_revisions` extra writer runs (never an infinite loop);
* **debate** -- n debaters in parallel regions + a judge; one debater
  failing does not stall the judge;
* **async engine** -- the same supervisor on `Interpreter` with an async
  model; children cancelled when the parent stops (no leaked tasks);
* **nothing leaks** -- 1,000 sequential worker spawns: bounded memory,
  no thread growth, actor registry does not grow.
"""

from __future__ import annotations

import asyncio
import gc
import json
import logging
import threading
import tracemalloc
from typing import Any, Dict, List

import pytest

pytest.importorskip("pydantic")

import bot  # noqa: E402
from xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.contrib.agents import (  # noqa: E402
    BudgetPlugin,
    FakeModel,
    handoff_guard,
    load_chart,
    spawn_agent,
    tool_registry,
)
from xstate_statemachine.contrib.agents.messages import (  # noqa: E402
    AgentConfigError,
)

LOOKUP_ONLY = ["lookup_order"]


def _lookup_tools(refunds: List[Any]) -> Any:
    reg = bot.build_tools(bot.stub_orders(), refunds)
    return tool_registry(reg.get("lookup_order"))


def _worker_script(n: int, *, fail_every: int = 0) -> List[Dict[str, Any]]:
    script: List[Dict[str, Any]] = []
    for i in range(n):
        if fail_every and i % fail_every == fail_every - 1:
            # a worker that keeps calling tools until its turn budget trips
            script += [{"tool": "lookup_order", "args": {"order_id": 7}}] * 3
        else:
            script += [
                {"tool": "lookup_order", "args": {"order_id": 7}},
                {"text": f"ticket {i} resolved"},
            ]
    return script


def _supervisor_logic(
    worker_model: Any,
    tools: Any,
    *,
    budget: Dict[str, Any],
    plugin: BudgetPlugin,
    parent_tools: Any = ("lookup_order", "refund_order"),
) -> MachineLogic:
    def store_plan(i, ctx, e, a):
        ctx["tasks"] = list(e.payload["tasks"])
        ctx["outstanding"] = len(ctx["tasks"])

    def hand_off(i, ctx, e, a):
        for t in ctx["tasks"]:
            i.send(
                {
                    "type": "HANDOFF",
                    "from": "planner",
                    "to": "worker",
                    "task": t,
                }
            )

    def collect(key):
        def _c(i, ctx, e, a):
            ctx[key] = ctx[key] + [
                {"agent_id": e.payload["agent_id"], **(e.payload or {})}
            ]

        return _c

    return MachineLogic(
        actions={
            "storePlan": store_plan,
            "handOffTasks": hand_off,
            "collectResult": collect("results"),
            "collectFailure": collect("failures"),
        },
        guards={
            "allWorkersReported": lambda c, e: 0
            < c["outstanding"]
            <= len(c["results"]) + len(c["failures"])
        },
    ).merge(
        spawn_agent(
            None,
            worker_model,
            tools,
            budget=budget,
            parent_tools=parent_tools,
            name="worker",
        ),
        handoff_guard({"planner": ["worker"]}),
        plugin.guards(),
    )


def _support_supervisor(tools: List[str] = LOOKUP_ONLY) -> Dict[str, Any]:
    """The SUPERVISOR reference chart with the support bot's allow-list
    on the worker region (the reference chart says search/fetch)."""
    chart = load_chart("supervisor")
    workers = chart["states"]["running"]["states"]["workers"]
    workers["meta"]["tools"] = list(tools)
    workers["states"]["working"]["meta"]["tools"] = list(tools)
    return chart


def _run_supervisor(
    n: int, *, fail_every: int = 0, max_total_tokens: int = 10**9
) -> Any:
    plugin = BudgetPlugin(max_total_tokens=max_total_tokens)
    refunds: List[Any] = []
    logic = _supervisor_logic(
        FakeModel(_worker_script(n, fail_every=fail_every), is_async=False),
        _lookup_tools(refunds),
        budget={"max_turns": 3, "max_usd": 0.10},
        plugin=plugin,
    )
    sup = (
        SyncInterpreter(create_machine(_support_supervisor(), logic=logic))
        .use(plugin)
        .start()
    )
    sup.send("PLAN", tasks=[f"ticket {i}" for i in range(n)])
    ids, ctx = set(sup.current_state_ids), json.loads(sup.get_snapshot())
    sup.stop()
    assert refunds == []
    return ids, ctx["context"], sup


# -----------------------------------------------------------------------------
# 1. a hundred tickets through the supervisor
# -----------------------------------------------------------------------------
def test_hundred_tickets_rollup_is_exact() -> None:
    ids, ctx, sup = _run_supervisor(100)
    assert ids == {"supervisor.reporting"}, ids
    assert len(ctx["results"]) == 100 and ctx["failures"] == []
    by_agent = ctx["usage_by_agent"]
    assert len(by_agent) == 100 and len(set(by_agent)) == 100
    for key in ("turns", "input_tokens", "output_tokens"):
        assert ctx["total_usage"][key] == sum(
            u[key] for u in by_agent.values()
        )
    assert ctx["total_usage"]["turns"] == 200  # 2 model turns per ticket
    # 🔒 no worker result ever carries a conversation
    assert all("messages" not in r for r in ctx["results"])
    # the actor registry does not keep 100 finished children alive
    assert len(getattr(sup, "_actors", {})) <= 1


# -----------------------------------------------------------------------------
# 2. X0.13 across the tree
# -----------------------------------------------------------------------------
def test_child_can_never_exceed_the_parent_allow_list() -> None:
    refunds: List[Any] = []
    full = bot.build_tools(bot.stub_orders(), refunds)
    plugin = BudgetPlugin(max_total_usd=1.0)
    # construction: the worker's registry has refund_order, the parent
    # allow-list does not
    with pytest.raises(AgentConfigError, match="refund_order"):
        spawn_agent(
            None,
            FakeModel([{"text": "x"}], is_async=False),
            full,
            budget={"max_turns": 2},
            parent_tools=LOOKUP_ONLY,
            name="worker",
        )
    # spawn time: parent_tools permissive, but the spawning STATE's
    # meta.tools (supervisor chart: ["search", "fetch"]) does not list
    # lookup_order -> refused at spawn, parent keeps running, no child
    logic = _supervisor_logic(
        FakeModel([{"text": "x"}] * 3, is_async=False),
        _lookup_tools(refunds),
        budget={"max_turns": 2},
        plugin=plugin,
        parent_tools=("lookup_order", "refund_order"),
    )
    chart = load_chart("supervisor")
    sup = SyncInterpreter(create_machine(chart, logic=logic)).use(plugin)
    sup.start()
    sup.send("PLAN", tasks=["t1"])
    # 📝 the reference chart runs `actionErrorPolicy: "fail"`: a refused
    #    spawn is a CONFIG error and stops the supervisor loudly rather
    #    than quietly running the ticket without a worker
    assert sup.status == "stopped", sup.status
    assert sup.context["results"] == [] and refunds == []
    assert not getattr(sup, "_actors", {})
    # a worker's MODEL proposing a tool outside its own allow-list is
    # tool_denied in the child -> AGENT_FAILED in the parent, which goes
    # on to `reporting`
    chart = _support_supervisor()
    logic = _supervisor_logic(
        FakeModel(
            [
                {
                    "tool": "refund_order",
                    "args": {"order_id": 1, "amount_cents": 1},
                }
            ]
            * 3,
            is_async=False,
        ),
        _lookup_tools(refunds),
        budget={"max_turns": 2},
        plugin=plugin,
        parent_tools=LOOKUP_ONLY,
    )
    sup = SyncInterpreter(create_machine(chart, logic=logic)).use(plugin)
    sup.start()
    sup.send("PLAN", tasks=["t1"])
    assert set(sup.current_state_ids) == {"supervisor.reporting"}
    assert len(sup.context["failures"]) == 1
    assert sup.context["failures"][0]["error"]["kind"] == "tool_denied"
    assert refunds == []
    sup.stop()


# -----------------------------------------------------------------------------
# 3. budgets: per-agent and global
# -----------------------------------------------------------------------------
def test_sub_agent_budget_fails_only_that_agent() -> None:
    ids, ctx, _ = _run_supervisor(10, fail_every=5)
    assert ids == {"supervisor.reporting"}
    assert len(ctx["results"]) == 8 and len(ctx["failures"]) == 2
    assert {f["error"]["kind"] for f in ctx["failures"]} == {"budget"}
    assert ctx["total_usage"]["turns"] == 8 * 2 + 2 * 3


def test_global_budget_trips_once_and_stops_spawning() -> None:
    # each worker turn costs FakeModel's fixed tokens; cap total so that
    # it trips after a few workers
    ids, ctx, sup = _run_supervisor(20, max_total_tokens=1)
    assert ctx["budget_exceeded"] is True
    spawned = len(ctx["usage_by_agent"])
    # 🔥 the planner hands off all 20 in ONE action; the rollup must land
    #    the moment the first worker reports, not when the parent gets
    #    round to dequeuing it -- otherwise all 20 spawn
    assert spawned == 1, spawned
    assert ids == {"supervisor.reporting"}, ids
    assert len(ctx["results"]) + len(ctx["failures"]) == spawned


# -----------------------------------------------------------------------------
# 4. handoffs are guarded
# -----------------------------------------------------------------------------
def test_unauthorised_handoff_is_denied() -> None:
    plugin = BudgetPlugin(max_total_usd=1.0)
    logic = _supervisor_logic(
        FakeModel([{"text": "x"}], is_async=False),
        _lookup_tools([]),
        budget={"max_turns": 2},
        plugin=plugin,
    )
    sup = SyncInterpreter(create_machine(_support_supervisor(), logic=logic))
    sup.use(plugin).start()
    assert sup.send(
        {"type": "HANDOFF", "from": "worker", "to": "judge", "task": "t"},
        wait=True,
    ).denied
    assert sup.send(
        {"type": "HANDOFF", "to": "worker", "task": "t"}, wait=True
    ).denied
    assert sup.send(
        {"type": "HANDOFF", "from": "planner", "to": "nobody", "task": "t"},
        wait=True,
    ).denied
    assert not getattr(sup, "_actors", {})
    assert sup.status == "running"
    sup.stop()


# -----------------------------------------------------------------------------
# 5. pipeline: bounded review loop
# -----------------------------------------------------------------------------
def test_pipeline_review_loop_is_bounded() -> None:
    chart = load_chart("pipeline")
    chart["context"]["max_revisions"] = 2
    chart["context"]["task"] = "write the refund policy FAQ"
    plugin = BudgetPlugin(max_total_usd=10.0)
    writer_runs = {"n": 0}

    def store(key):
        return lambda i, ctx, e, a: ctx.__setitem__(key, e.payload["result"])

    def count(i, ctx, e, a):
        ctx["revisions"] += 1

    class CountingModel:
        def __init__(self, text):
            self.text = text

        def __call__(self, messages, tools):
            writer_runs["n"] += 1
            return {"text": self.text}

    def search(q: str) -> str:
        """Search."""
        return "facts"

    logic = MachineLogic(
        actions={
            "storeResearch": store("research"),
            "storeDraft": store("draft"),
            "storeReview": store("review"),
            "countRevision": count,
        },
        guards={
            "approved": lambda c, e: "APPROVED"
            in str(e.payload.get("result")),
            "underRevisionLimit": lambda c, e: c["revisions"]
            < c["max_revisions"],
        },
    ).merge(
        spawn_agent(
            None,
            FakeModel(
                [{"tool": "search", "args": {"q": "x"}}, {"text": "facts"}],
                is_async=False,
            ),
            tool_registry(search, timeout_s=5),
            budget={"max_turns": 3},
            parent_tools=["search"],
            name="researcher",
        ),
        spawn_agent(
            None,
            CountingModel("draft v"),
            None,
            budget={"max_turns": 2},
            parent_tools=[],
            name="writer",
        ),
        spawn_agent(
            None,
            FakeModel([{"text": "REJECTED: too short"}] * 10, is_async=False),
            None,
            budget={"max_turns": 2},
            parent_tools=[],
            name="reviewer",
        ),
        plugin.guards(),
    )
    p = SyncInterpreter(create_machine(chart, logic=logic)).use(plugin).start()
    assert set(p.current_state_ids) == {"pipeline.failed"}, p.current_state_ids
    assert p.context["revisions"] == 2
    assert writer_runs["n"] == 3  # first draft + 2 revisions, never more
    assert "REJECTED" in p.context["review"]
    p.stop()


# -----------------------------------------------------------------------------
# 6. debate: one failing debater does not stall the judge
# -----------------------------------------------------------------------------
def test_debate_tolerates_one_failing_debater() -> None:
    chart = load_chart("debate")
    chart["context"]["task"] = "Should order 7 be refunded?"
    plugin = BudgetPlugin(max_total_usd=10.0)

    def store_pos(i, ctx, e, a):
        side = e.payload["agent_id"].rsplit(":", 1)[-1].split("-")[0]
        ctx["positions"] = {
            **ctx["positions"],
            side: e.payload.get("result") or e.payload.get("error"),
        }

    def verdict(i, ctx, e, a):
        ctx["verdict"] = e.payload["result"]

    def from_side(side):
        return lambda ctx, e: f":{side}-" in e.payload["agent_id"]

    def agent(name, script):
        return spawn_agent(
            None,
            FakeModel(script, is_async=False),
            None,
            budget={"max_turns": 2},
            parent_tools=[],
            name=name,
        )

    logic = MachineLogic(
        actions={
            "storePosition": store_pos,
            "storeVerdict": verdict,
            "forwardToJudge": lambda i, ctx, e, a: None,
        },
        guards={"fromPro": from_side("pro"), "fromCon": from_side("con")},
    ).merge(
        agent("pro", [{"text": "yes: damaged on arrival"}]),
        # 🔥 the CON debater's model keeps proposing a tool it does not
        #    have -> tool_denied -> AGENT_FAILED; the debate must still
        #    reach the judge
        agent("con", [{"tool": "refund_order", "args": {}}] * 3),
        agent("judge", [{"text": "pro wins"}]),
        handoff_guard({"pro": ["judge"], "con": ["judge"]}),
        plugin.guards(),
    )
    d = SyncInterpreter(create_machine(chart, logic=logic)).use(plugin).start()
    assert d.current_state_ids == {"debate.decided"}, d.current_state_ids
    assert d.context["positions"]["pro"].startswith("yes")
    assert d.context["positions"]["con"]["kind"] == "tool_denied"
    assert d.context["verdict"] == "pro wins"
    assert len(d.context["usage_by_agent"]) == 3
    d.stop()


# -----------------------------------------------------------------------------
# 7. async engine: children die with the parent
# -----------------------------------------------------------------------------
def test_async_supervisor_children_cancelled_on_stop() -> None:
    async def slow_model(messages, tools):
        await asyncio.sleep(3600)

    async def main() -> Any:
        plugin = BudgetPlugin(max_total_usd=1.0)
        logic = _supervisor_logic(
            slow_model,
            _lookup_tools([]),
            budget={"max_turns": 2},
            plugin=plugin,
        )
        sup = Interpreter(create_machine(_support_supervisor(), logic=logic))
        await sup.use(plugin).start()
        await sup.send("PLAN", tasks=["a", "b", "c"])
        await asyncio.sleep(0.2)
        n_actors = len(getattr(sup, "_actors", {}))
        before = len(asyncio.all_tasks())
        await sup.stop()
        await asyncio.sleep(0.1)
        after = len(asyncio.all_tasks())
        return n_actors, before, after

    n_actors, before, after = asyncio.run(main())
    assert n_actors == 3, n_actors
    assert after < before, (before, after)


# -----------------------------------------------------------------------------
# 8. nothing leaks
# -----------------------------------------------------------------------------
def test_thousand_spawns_flat() -> None:
    logging.disable(logging.CRITICAL)
    try:
        threads0 = threading.active_count()

        def batch(n: int) -> None:
            _run_supervisor(n)

        batch(250)
        gc.collect()
        tracemalloc.start()
        batch(250)
        gc.collect()
        mid = tracemalloc.take_snapshot()
        batch(500)
        gc.collect()
        end = tracemalloc.take_snapshot()
        tracemalloc.stop()
        growth = sum(
            s.size_diff
            for s in end.compare_to(mid, "filename")
            if s.size_diff > 0
        )
        assert growth < 32 * 1024 * 1024, growth
        assert threading.active_count() <= threads0 + 1
    finally:
        logging.disable(logging.NOTSET)
