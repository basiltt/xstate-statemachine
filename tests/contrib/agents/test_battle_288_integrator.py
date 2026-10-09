# tests/contrib/agents/test_battle_288_integrator.py
"""#288 integrator: a LangGraph graph that calls ``interrupt()`` is PAUSED,
not done (adversary B found ``onDone`` fired with an ``__interrupt__``
key). `langgraph_service` now surfaces it as ``onError`` with
`GraphInterruptedError` (the chart decides), or ``onDone`` when asked
(``on_interrupt="done"``)."""

from __future__ import annotations

import asyncio
from typing import Any, Dict, TypedDict

import pytest

pytest.importorskip("pydantic")
pytest.importorskip("langgraph")

from langgraph.checkpoint.memory import MemorySaver  # noqa: E402
from langgraph.graph import END, StateGraph  # noqa: E402
from langgraph.types import interrupt  # noqa: E402

from src.xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    create_machine,
)
from src.xstate_statemachine.contrib.agents.langgraph import (  # noqa: E402
    GraphInterruptedError,
    langgraph_service,
)
from src.xstate_statemachine.contrib.agents.messages import (  # noqa: E402
    AgentConfigError,
)


class G(TypedDict, total=False):
    n: int
    answer: str


def _paused_graph() -> Any:
    g: Any = StateGraph(G)

    def ask(state: G) -> Dict[str, Any]:
        answer = interrupt({"question": "approve?"})
        return {"answer": answer}

    g.add_node("ask", ask)
    g.set_entry_point("ask")
    g.add_edge("ask", END)
    return g.compile(checkpointer=MemorySaver())


def _host(service: Any) -> Any:
    cfg = {
        "id": "host",
        "initial": "running",
        "context": {"result": None, "error": None},
        "states": {
            "running": {
                "invoke": {
                    "src": "graph",
                    "onDone": {"target": "done", "actions": "keep"},
                    "onError": {"target": "paused", "actions": "fail"},
                }
            },
            "done": {"type": "final"},
            "paused": {"type": "final"},
        },
    }

    def keep(i, ctx, e, a):
        ctx["result"] = e.data

    def fail(i, ctx, e, a):
        ctx["error"] = e.data

    return create_machine(
        cfg,
        logic=MachineLogic(
            services={"graph": service}, actions={"keep": keep, "fail": fail}
        ),
    )


async def _run(machine: Any) -> Any:
    i = await Interpreter(machine).start()
    for _ in range(200):
        if any(s.endswith(("done", "paused")) for s in i.current_state_ids):
            break
        await asyncio.sleep(0.01)
    ids, ctx = set(i.current_state_ids), dict(i.context)
    await i.stop()
    return ids, ctx


def test_interrupt_is_on_error_by_default() -> None:
    svc = langgraph_service(
        _paused_graph(),
        input_from=lambda c, e: {"n": 1},
        config={"configurable": {"thread_id": "t1"}},
    )
    ids, ctx = asyncio.run(_run(_host(svc)))
    assert ids == {"host.paused"}, ids
    err = ctx["error"]
    assert isinstance(err, GraphInterruptedError), type(err)
    assert err.interrupts
    assert "approve?" not in str(err)  # payload stays off the message
    assert "approve?" in repr(err.interrupts[0].value)
    assert ctx["result"] is None


def test_interrupt_can_be_treated_as_done_on_request() -> None:
    svc = langgraph_service(
        _paused_graph(),
        input_from=lambda c, e: {"n": 1},
        config={"configurable": {"thread_id": "t2"}},
        on_interrupt="done",
    )
    ids, ctx = asyncio.run(_run(_host(svc)))
    assert ids == {"host.done"}, ids
    assert "__interrupt__" in ctx["result"]


def test_bad_on_interrupt_is_refused_at_declaration() -> None:
    with pytest.raises(AgentConfigError):
        langgraph_service(
            _paused_graph(), input_from=lambda c, e: {}, on_interrupt="park"
        )
    # a stream mode whose chunks never carry the interrupt is refused too
    with pytest.raises(AgentConfigError, match="stream_mode"):
        langgraph_service(
            _paused_graph(),
            input_from=lambda c, e: {},
            stream=True,
            stream_mode="messages",
        )
    langgraph_service(  # fine: the pause is visible in "updates"
        _paused_graph(),
        input_from=lambda c, e: {},
        stream=True,
        stream_mode="updates",
    )


def test_router_most_specific_key_wins_across_parallel_regions() -> None:
    """Review M2: with parallel regions the exact leaf key in the SECOND
    region beats an ancestor key that the first region matches, and a
    key equal to the machine id never swallows every state."""
    from src.xstate_statemachine import SyncInterpreter
    from src.xstate_statemachine.contrib.agents.langgraph import (
        route_by_statechart,
    )

    m = create_machine(
        {
            "id": "g",
            "initial": "p",
            "states": {
                "p": {
                    "type": "parallel",
                    "states": {
                        "r1": {"initial": "x", "states": {"x": {}}},
                        "r2": {"initial": "y", "states": {"y": {}}},
                    },
                }
            },
        }
    )
    import json

    snap = json.loads(SyncInterpreter(m).start().get_snapshot())
    route = route_by_statechart(m, {"p": "COARSE", "g.p.r2.y": "EXACT"})
    assert route({"xsm": snap}) == "EXACT"
    # the root id is not a match: `default` is still reachable
    route2 = route_by_statechart(m, {"g": "ROOT"}, default="DEF")
    assert route2({"xsm": snap}) == "DEF"
    # a JSON string that does not parse is a config error, not JSONDecode
    with pytest.raises(AgentConfigError, match="not valid snapshot JSON"):
        route({"xsm": "{not json"})
