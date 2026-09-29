"""#290 E4: multi-agent recipes -- spawn_agent, BudgetPlugin, handoff
guard, actor-tree tracing. Both engines, FakeModel only, offline."""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List

import pytest

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)

from ..conftest import requires_extra

pytestmark = requires_extra("agents")
pytest.importorskip("pydantic")

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    AgentConfigError,
    AgentTracePlugin,
    BudgetPlugin,
    FakeModel,
    agent_logic,
    handoff_guard,
    load_chart,
    spawn_agent,
    tool_registry,
)


def search(q: str) -> str:
    """Search the web."""
    return f"results for {q}"


def fetch(url: str) -> str:
    """Fetch a page."""
    return "page"


def delete_everything() -> str:
    """Not something a worker should have."""
    return "gone"


def worker_script(n: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for k in range(n):
        out += [
            {"tool": "search", "args": {"q": f"t{k}"}},
            {"text": f"answer {k}", "usage": {"cost_usd": 0.01}},
        ]
    return out


# -----------------------------------------------------------------------------
# supervisor recipe logic (what the docs show)
# -----------------------------------------------------------------------------
def supervisor_logic(
    model: Any, *, budget: Any, tracer: Any = None
) -> MachineLogic:
    def store_plan(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        ctx["tasks"] = list(e.payload["tasks"])
        ctx["outstanding"] = len(ctx["tasks"])

    def hand_off(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        for t in ctx["tasks"]:
            i.send(
                {
                    "type": "HANDOFF",
                    "from": "planner",
                    "to": "worker",
                    "task": t,
                }
            )

    def collect(key: str) -> Callable[..., None]:
        def _a(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
            ctx[key] = ctx[key] + [
                {k: e.payload.get(k) for k in ("agent_id", "result", "error")}
            ]

        return _a

    def all_reported(ctx: Dict[str, Any], e: Any) -> bool:
        n = len(ctx["results"]) + len(ctx["failures"])
        return ctx["outstanding"] > 0 and n >= ctx["outstanding"]

    base = MachineLogic(
        actions={
            "storePlan": store_plan,
            "handOffTasks": hand_off,
            "collectResult": collect("results"),
            "collectFailure": collect("failures"),
        },
        guards={"allWorkersReported": all_reported},
    )
    workers = spawn_agent(
        None,
        model,
        tool_registry(search, fetch, timeout_s=2),
        budget=budget,
        parent_tools=["search", "fetch"],
        name="worker",
        tracer=tracer,
    )
    return base.merge(
        workers, handoff_guard({"planner": ["worker"], "worker": []})
    )


async def until(i: Any, pred: Callable[[Any], bool]) -> None:
    ev = asyncio.Event()

    def _check(x: Any) -> None:
        if pred(x):
            ev.set()

    off = i.subscribe(_check)
    try:
        _check(i)
        await asyncio.wait_for(ev.wait(), 5)
    finally:
        off()


class TestSupervisor:
    def test_sync_fan_out_and_aggregate(self) -> None:
        plugin = BudgetPlugin(max_total_usd=10.0)
        logic = supervisor_logic(
            FakeModel(worker_script(3), is_async=False),
            budget={"max_turns": 4},
        ).merge(plugin.guards())
        i = SyncInterpreter(
            create_machine(load_chart("supervisor"), logic=logic)
        )
        i.use(plugin).start()
        i.send("PLAN", tasks=["a", "b", "c"])
        assert i.current_state_ids == {"supervisor.reporting"}
        assert sorted(r["result"] for r in i.context["results"]) == [
            "answer 0",
            "answer 1",
            "answer 2",
        ]
        total = i.context["total_usage"]
        assert total["turns"] == 6 and total["input_tokens"] == 60
        assert total["cost_usd"] == pytest.approx(0.03)
        assert len(i.context["usage_by_agent"]) == 3
        i.stop()

    def test_async_fan_out_and_aggregate(self) -> None:
        async def go() -> Any:
            plugin = BudgetPlugin(max_total_tokens=10_000)
            logic = supervisor_logic(
                FakeModel(worker_script(2)), budget={"max_turns": 4}
            )
            i = Interpreter(
                create_machine(load_chart("supervisor"), logic=logic)
            ).use(plugin)
            await i.start()
            await i.send("PLAN", tasks=["a", "b"])
            await until(i, lambda x: x.status == "done")
            ctx = dict(i.context)
            await i.stop()
            return ctx

        ctx = asyncio.run(go())
        assert len(ctx["results"]) == 2
        assert ctx["total_usage"]["turns"] == 4

    def test_unauthorised_handoff_is_denied(self) -> None:
        logic = supervisor_logic(
            FakeModel([], is_async=False), budget={"max_turns": 2}
        )
        i = SyncInterpreter(
            create_machine(load_chart("supervisor"), logic=logic)
        ).start()
        r = i.send(
            {"type": "HANDOFF", "from": "worker", "to": "judge", "task": "x"},
            wait=True,
        )
        assert r.denied and not r.changed
        assert not i._actors  # nothing spawned
        i.stop()

    def test_unauthorised_handoff_denied_async(self) -> None:
        async def go() -> Any:
            logic = supervisor_logic(FakeModel([]), budget={"max_turns": 2})
            i = Interpreter(
                create_machine(load_chart("supervisor"), logic=logic)
            )
            await i.start()
            r = await i.send(
                {"type": "HANDOFF", "from": "worker", "to": "judge"},
                wait=True,
            )
            await i.stop()
            return r

        assert asyncio.run(go()).denied

    def test_sub_agent_budget_exhaustion_reports_failure(self) -> None:
        # max_turns=1: the worker's tool call uses its only turn
        logic = supervisor_logic(
            FakeModel(worker_script(2), is_async=False),
            budget={"max_turns": 1},
        )
        i = SyncInterpreter(
            create_machine(load_chart("supervisor"), logic=logic)
        ).start()
        i.send("PLAN", tasks=["a"])
        assert i.current_state_ids == {"supervisor.reporting"}
        (failure,) = i.context["failures"]
        assert failure["error"]["kind"] == "budget"
        i.stop()


# -----------------------------------------------------------------------------
# global budget
# -----------------------------------------------------------------------------
FLAT = {
    "id": "boss",
    "initial": "active",
    "context": {"spawned": 0},
    "states": {
        "active": {
            "on": {
                "TASK": {"actions": "spawnWorker"},
                "AGENT_DONE": {},
                "AGENT_FAILED": {},
                "BUDGET_EXCEEDED": {"actions": "noteStop"},
                "MORE": {"guard": "underGlobalBudget", "target": "more"},
            }
        },
        "more": {},
    },
}


class TestGlobalBudget:
    def _logic(self, plugin: BudgetPlugin, model: Any) -> MachineLogic:
        def note(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
            ctx["stopped_with"] = dict(e.payload["total_usage"])

        return (
            MachineLogic(actions={"noteStop": note})
            .merge(
                spawn_agent(
                    None,
                    model,
                    tool_registry(search, timeout_s=2),
                    budget={"max_turns": 3},
                    name="worker",
                )
            )
            .merge(plugin.guards())
        )

    def test_budget_exceeded_stops_spawning(self) -> None:
        plugin = BudgetPlugin(max_total_tokens=25)
        model = FakeModel(worker_script(5), is_async=False)
        i = (
            SyncInterpreter(
                create_machine(FLAT, logic=self._logic(plugin, model))
            )
            .use(plugin)
            .start()
        )
        i.send("TASK", task="one")  # 2 turns → 30 tokens ≥ 25
        assert i.context["budget_exceeded"] is True
        assert i.context["stopped_with"]["input_tokens"] == 20
        calls = len(model.calls)
        i.send("TASK", task="two")
        assert len(model.calls) == calls  # refused: no new sub-agent
        assert i.send("MORE", wait=True).denied  # guard-visible
        i.stop()

    def test_budget_exceeded_once_only(self) -> None:
        plugin = BudgetPlugin(max_total_usd=0.005)
        seen: List[str] = []
        model = FakeModel(worker_script(5), is_async=False)
        i = SyncInterpreter(
            create_machine(FLAT, logic=self._logic(plugin, model))
        ).use(plugin)
        i.start()
        i.subscribe(lambda x: seen.append("tick"))
        i.send("TASK", task="one")
        # a second AGENT_DONE does not raise a second BUDGET_EXCEEDED
        i.send("AGENT_DONE", usage={"cost_usd": 1.0}, agent_id="x")
        assert i.context["total_usage"]["cost_usd"] == pytest.approx(1.01)
        i.stop()

    def test_needs_a_limit(self) -> None:
        with pytest.raises(AgentConfigError):
            BudgetPlugin()

    def test_unrelated_events_ignored(self) -> None:
        plugin = BudgetPlugin(max_total_usd=1)
        ev = type("E", (), {"type": "OTHER", "payload": {}})()
        plugin.on_event_received(object(), ev)  # no context access


# -----------------------------------------------------------------------------
# X0.13: child tools ⊆ parent tools
# -----------------------------------------------------------------------------
class TestSubsetRule:
    def test_refused_at_construction(self) -> None:
        with pytest.raises(AgentConfigError, match="delete_everything"):
            spawn_agent(
                None,
                FakeModel([]),
                tool_registry(search, delete_everything, timeout_s=1),
                budget={"max_turns": 1},
                parent_tools=["search"],
            )

    def test_wildcard_parent_allows_any(self) -> None:
        spawn_agent(
            None,
            FakeModel([]),
            tool_registry(search, delete_everything, timeout_s=1),
            budget={"max_turns": 1},
            parent_tools=["*"],
        )

    def test_refused_at_spawn_against_state_meta(self) -> None:
        chart = {
            "id": "p",
            "initial": "a",
            "actionErrorPolicy": "rollback",
            "states": {
                "a": {
                    "meta": {"tools": ["search"]},
                    "on": {"TASK": {"actions": "spawnAgent"}},
                }
            },
        }
        logic = spawn_agent(
            None,
            FakeModel([], is_async=False),
            tool_registry(search, fetch, timeout_s=1),
            budget={"max_turns": 1},
        )
        i = SyncInterpreter(create_machine(chart, logic=logic)).start()
        r = i.send("TASK", task="x", wait=True)
        assert isinstance(r.error, AgentConfigError)
        assert not i._actors
        i.stop()

    def test_budget_is_required(self) -> None:
        with pytest.raises(AgentConfigError, match="budget"):
            spawn_agent(None, FakeModel([]), budget=None)

    def test_machine_node_child_refused(self) -> None:
        with pytest.raises(AgentConfigError):
            spawn_agent(
                create_machine(load_chart(), logic=agent_logic(FakeModel([]))),
                FakeModel([]),
                budget={},
            )

    def test_task_required(self) -> None:
        chart = {
            "id": "p",
            "initial": "a",
            "actionErrorPolicy": "rollback",
            "states": {"a": {"on": {"TASK": {"actions": "spawnAgent"}}}},
        }
        logic = spawn_agent(
            None, FakeModel([], is_async=False), budget={"max_turns": 1}
        )
        i = SyncInterpreter(create_machine(chart, logic=logic)).start()
        assert isinstance(i.send("TASK", wait=True).error, AgentConfigError)
        i.stop()


# -----------------------------------------------------------------------------
# pipeline / debate recipes
# -----------------------------------------------------------------------------
def pipeline_logic(review_texts: List[str], sync: bool = True) -> Any:
    def store(key: str) -> Callable[..., None]:
        def _a(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
            ctx[key] = e.payload.get("result")

        return _a

    def bump(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        ctx["revisions"] += 1

    def under(ctx: Dict[str, Any], e: Any) -> bool:
        return ctx["revisions"] < ctx["max_revisions"]

    def approved(ctx: Dict[str, Any], e: Any) -> bool:
        return str(e.payload.get("result", "")).startswith("APPROVED")

    reviews = [{"text": t} for t in review_texts]
    writers = [{"text": f"draft {k}"} for k in range(len(reviews))]
    return (
        MachineLogic(
            actions={
                "storeResearch": store("research"),
                "storeDraft": store("draft"),
                "storeReview": store("review"),
                "countRevision": bump,
            },
            guards={"underRevisionLimit": under, "approved": approved},
        )
        .merge(
            spawn_agent(
                None,
                FakeModel(
                    [
                        {"tool": "search", "args": {"q": "x"}},
                        {"text": "facts"},
                    ],
                    is_async=not sync,
                ),
                tool_registry(search, timeout_s=1),
                budget={"max_turns": 3},
                parent_tools=["search"],
                name="researcher",
            )
        )
        .merge(
            spawn_agent(
                None,
                FakeModel(writers, is_async=not sync),
                budget={"max_turns": 2},
                name="writer",
                task_key="research",
            )
        )
        .merge(
            spawn_agent(
                None,
                FakeModel(reviews, is_async=not sync),
                budget={"max_turns": 2},
                name="reviewer",
                task_key="draft",
            )
        )
    )


class TestPipeline:
    def _run(self, reviews: List[str]) -> Any:
        chart = load_chart("pipeline")
        chart["context"]["task"] = "write about X"
        i = SyncInterpreter(
            create_machine(chart, logic=pipeline_logic(reviews))
        ).start()
        state = set(i.current_state_ids)
        ctx = dict(i.context)
        i.stop()
        return state, ctx

    def test_approved_after_one_revision(self) -> None:
        state, ctx = self._run(["needs work", "APPROVED: good"])
        assert state == {"pipeline.published"}
        assert ctx["revisions"] == 1 and ctx["draft"] == "draft 1"

    def test_review_loop_is_bounded(self) -> None:
        state, ctx = self._run(["no", "no", "no", "no"])
        assert state == {"pipeline.failed"}
        assert ctx["revisions"] == 2

    def test_async(self) -> None:
        async def go() -> Any:
            chart = load_chart("pipeline")
            chart["context"]["task"] = "t"
            i = Interpreter(
                create_machine(
                    chart, logic=pipeline_logic(["APPROVED"], sync=False)
                )
            )
            await i.start()
            await until(i, lambda x: x.status == "done")
            s = set(i.current_state_ids)
            await i.stop()
            return s

        assert asyncio.run(go()) == {"pipeline.published"}


class TestDebate:
    def test_parallel_positions_then_judge(self) -> None:
        def store_pos(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
            side = e.payload["agent_id"].rsplit(":", 1)[-1].split("-")[0]
            ctx["positions"] = {**ctx["positions"], side: e.payload["result"]}

        def verdict(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
            ctx["verdict"] = e.payload["result"]

        def from_side(side: str) -> Callable[..., bool]:
            return lambda ctx, e: f":{side}-" in e.payload["agent_id"]

        def forward(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
            ctx["forwarded"] = True

        def agent(name: str, text: str) -> MachineLogic:
            return spawn_agent(
                None,
                FakeModel([{"text": text}], is_async=False),
                budget={"max_turns": 1},
                name=name,
            )

        logic = (
            MachineLogic(
                actions={
                    "storePosition": store_pos,
                    "storeVerdict": verdict,
                    "forwardToJudge": forward,
                },
                guards={
                    "fromPro": from_side("pro"),
                    "fromCon": from_side("con"),
                },
            )
            .merge(agent("pro", "yes"), agent("con", "no"))
            .merge(agent("judge", "pro wins"))
            .merge(handoff_guard({"pro": ["judge"], "con": ["judge"]}))
        )
        chart = load_chart("debate")
        chart["context"]["task"] = "Is X good?"
        i = SyncInterpreter(create_machine(chart, logic=logic)).start()
        assert i.current_state_ids == {"debate.decided"}
        assert i.context["positions"] == {"pro": "yes", "con": "no"}
        assert i.context["verdict"] == "pro wins"
        i.stop()


# -----------------------------------------------------------------------------
# tracing an actor tree
# -----------------------------------------------------------------------------
class TestActorTreeTrace:
    def test_one_trace_per_agent_records_and_rollup(self) -> None:
        trace = AgentTracePlugin()
        logic = supervisor_logic(
            FakeModel(worker_script(2), is_async=False),
            budget={"max_turns": 4},
            tracer=trace,
        )
        i = SyncInterpreter(
            create_machine(load_chart("supervisor"), logic=logic)
        ).use(trace)
        i.start()
        i.send("PLAN", tasks=["a", "b"])
        assert {r["trace_id"] for r in trace.records} == {"supervisor"}
        children = {
            r["agent_id"] for r in trace.records if r["kind"] == "model_call"
        }
        assert len(children) == 2
        assert all(c.startswith("supervisor:worker") for c in children)
        assert {
            r["parent_id"] for r in trace.records if r["kind"] == "model_call"
        } == {"supervisor"}
        totals = trace.totals()
        assert totals["total"]["turns"] == 4
        assert totals["total"]["cost_usd"] == pytest.approx(0.02)
        assert set(totals["agents"]) == children
        i.stop()
