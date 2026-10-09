# tests/contrib/agents/test_battle_290_review.py
"""#290 independent review -- regressions.

* **R1** an `inf` usage count never disables the global budget;
* **R2** a report to a STOPPED parent is not charged;
* **R3** a report's payload is released once the parent has dequeued it
  (the de-dup ring does not hold transcripts);
* **R4** a child chart that reports from `exit` / a transition's
  `actions` / `onDone` is accepted, not refused as "never reports";
* **R6** a strict parent chart that does not declare `BUDGET_EXCEEDED`
  is refused at start, not silently un-tripped;
* **R8** the documented debate `storePosition` pattern handles a FAILED
  debater (`result` is None).
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List

import pytest

pytest.importorskip("pydantic")

from src.xstate_statemachine import (  # noqa: E402
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    TOOL_LOOP,
    BudgetPlugin,
    FakeModel,
    load_chart,
    spawn_agent,
)
from src.xstate_statemachine.contrib.agents.messages import (  # noqa: E402
    AgentConfigError,
)
from src.xstate_statemachine.events import Event  # noqa: E402


def _report(i: int, **usage: Any) -> Event:
    return Event(
        "AGENT_DONE",
        {
            "agent_id": f"w-{i}",
            "usage": {"turns": 1, "input_tokens": 10, "output_tokens": 5},
            "result": "x" * 1000,
        },
    )


def _parent(plugin: BudgetPlugin, **cfg: Any) -> Any:
    chart = {
        "id": "p",
        "initial": "a",
        "context": {"total_usage": {}, "usage_by_agent": {}},
        "states": {
            "a": {
                "on": {
                    "AGENT_DONE": {"actions": []},
                    "BUDGET_EXCEEDED": "b",
                }
            },
            "b": {},
        },
        **cfg,
    }
    return SyncInterpreter(create_machine(chart)).use(plugin)


def test_r1_inf_usage_never_disables_the_budget() -> None:
    plugin = BudgetPlugin(max_total_tokens=100)
    p = _parent(plugin).start()
    bad = _report(0)
    bad.payload["usage"]["input_tokens"] = float("inf")
    p.send(bad)
    assert p.context["total_usage"]["input_tokens"] == 0  # ignored, not inf
    for i in range(1, 12):
        p.send(_report(i))
    assert p.context["budget_exceeded"] is True
    assert "p.b" in p.current_state_ids  # BUDGET_EXCEEDED delivered
    p.stop()


def test_r2_report_to_a_stopped_parent_is_not_charged() -> None:
    plugin = BudgetPlugin(max_total_tokens=10**6)
    p = _parent(plugin).start()
    p.send(_report(0))
    assert p.context["total_usage"]["turns"] == 1
    p.stop()
    p.send(_report(1))  # dropped: the machine is not running
    assert p.context["total_usage"]["turns"] == 1


def test_r3_payloads_are_released_after_dequeue() -> None:
    plugin = BudgetPlugin(max_total_tokens=10**9)
    p = _parent(plugin).start()
    for i in range(50):
        p.send(_report(i))
    assert p.context["total_usage"]["turns"] == 50  # each counted once
    assert len(plugin._seen) == 0  # nothing retained after dequeue
    p.stop()


def _chart_reporting_from(where: str) -> Dict[str, Any]:
    child = copy.deepcopy(TOOL_LOOP)
    for state in child["states"].values():
        if state.get("entry") == "notifyParent":
            del state["entry"]
    done = child["states"]["done"]
    if where == "exit":
        child["states"]["awaiting_model"]["exit"] = "notifyParent"
    elif where == "transition":
        for st in child["states"].values():
            for arms in (st.get("on") or {}).values():
                for arm in arms if isinstance(arms, list) else [arms]:
                    if isinstance(arm, dict) and arm.get("target") == "done":
                        arm["actions"] = ["notifyParent"]
                        return child
        done["entry"] = "notifyParent"
    elif where == "ondone":
        inv = child["states"]["awaiting_model"]["invoke"]
        arms = (
            inv["onDone"]
            if isinstance(inv["onDone"], list)
            else [inv["onDone"]]
        )
        for arm in arms:
            acts = arm.get("actions", [])
            arm["actions"] = (acts if isinstance(acts, list) else [acts]) + [
                "notifyParent"
            ]
    return child


@pytest.mark.parametrize("where", ["exit", "transition", "ondone"])
def test_r4_charts_reporting_outside_entry_are_accepted(where: str) -> None:
    spawn_agent(
        _chart_reporting_from(where),
        FakeModel([{"text": "ok"}], is_async=False),
        budget={"max_turns": 2},
        parent_tools=[],
        name="w",
    )


def test_r6_strict_parent_must_declare_budget_exceeded() -> None:
    from src.xstate_statemachine.contrib.agents.multi import (
        check_budget_event_declared,
    )

    plugin = BudgetPlugin(max_total_tokens=1)
    chart = {
        "id": "p",
        "initial": "a",
        "strict": True,
        "actionErrorPolicy": "fail",
        "context": {"total_usage": {}, "task": "t"},
        "states": {
            "a": {
                "on": {
                    "GO": {"actions": "spawnW"},
                    "AGENT_DONE": {"actions": []},
                }
            }
        },
    }
    logic = spawn_agent(
        None,
        FakeModel([{"text": "ok"}] * 3, is_async=False),
        budget={"max_turns": 2},
        parent_tools=[],
        name="w",
    )
    p = SyncInterpreter(create_machine(chart, logic=logic)).use(plugin)
    p.start()  # the hook is fail-open: start() succeeds, the error is logged
    with pytest.raises(AgentConfigError, match="BUDGET_EXCEEDED"):
        check_budget_event_declared(p)
    p.send("GO")  # the spawn action re-checks LOUDLY: the machine stops
    assert p.status == "stopped"
    chart["states"]["a"]["on"]["BUDGET_EXCEEDED"] = "a"
    q = SyncInterpreter(create_machine(chart, logic=logic)).use(plugin)
    q.start()
    check_budget_event_declared(q)
    q.send("GO")
    assert q.status == "running"
    q.stop()


def test_r8_debate_store_position_pattern_handles_a_failed_debater() -> None:
    chart = load_chart("debate")
    chart["context"]["task"] = "topic"
    positions: List[Any] = []

    def store_pos(i, ctx, e, a):
        side = e.payload["agent_id"].rsplit(":", 1)[-1].split("-")[0]
        # the documented pattern: a failed debater states its failure
        ctx["positions"] = {
            **ctx["positions"],
            side: e.payload.get("result") or e.payload.get("error"),
        }
        positions.append(side)

    def agent(name, script):
        return spawn_agent(
            None,
            FakeModel(script, is_async=False),
            budget={"max_turns": 1},
            parent_tools=[],
            name=name,
        )

    logic = MachineLogic(
        actions={
            "storePosition": store_pos,
            "storeVerdict": lambda i, ctx, e, a: ctx.__setitem__(
                "verdict", e.payload["result"]
            ),
            "forwardToJudge": lambda i, ctx, e, a: None,
        },
        guards={
            "fromPro": lambda c, e: ":pro-" in e.payload["agent_id"],
            "fromCon": lambda c, e: ":con-" in e.payload["agent_id"],
        },
    ).merge(
        agent("pro", [{"text": "yes"}]),
        agent("con", [{"tool": "nope", "args": {}}] * 2),
        agent("judge", [{"text": "pro"}]),
    )
    d = SyncInterpreter(create_machine(chart, logic=logic)).start()
    assert d.current_state_ids == {"debate.decided"}
    assert d.context["positions"]["con"]["kind"] == "tool_denied"
    assert sorted(positions) == ["con", "pro"]
    d.stop()
