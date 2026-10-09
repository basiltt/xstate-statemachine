# tests/contrib/agents/test_battle_288_a.py
# -----------------------------------------------------------------------------
# ⚔️ Battle #288 adversary A -- LangGraph interop under real semantics/faults
# -----------------------------------------------------------------------------
"""Adversarial tests for contrib.agents.langgraph (#288-a)."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import gc
import threading
import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from typing import TypedDict

import pytest

pytest.importorskip("langgraph")
pytest.importorskip("langchain_core")

# -------------------------------------------------------------------------
# 📥 Third-party / Project-Specific Imports
# -------------------------------------------------------------------------
from langchain_core.callbacks import BaseCallbackHandler  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402
from langgraph.graph import END, StateGraph  # noqa: E402

from xstate_statemachine import (  # noqa: E402
    Interpreter,
    MachineLogic,
    create_machine,
)
from xstate_statemachine.contrib.agents.langgraph import (  # noqa: E402
    check_langgraph_version,
    langgraph_service,
    LangChainCallbackPlugin,
    route_by_statechart,
    statechart_node,
)
from xstate_statemachine.contrib.agents.messages import (  # noqa: E402
    AgentConfigError,
)
from xstate_statemachine.exceptions import XStateMachineError  # noqa: E402

NESTED = {
    "id": "g",
    "initial": "a",
    "states": {
        "a": {
            "initial": "b",
            "states": {"b": {"on": {"GO": "c"}}, "c": {}},
            "on": {"PAR": "#g.p"},
        },
        "p": {"type": "parallel", "states": {"y": {}, "x": {}}},
    },
}


class _S(TypedDict, total=False):
    m: object


def _message_graph():
    g = StateGraph(_S)
    g.add_node("n", lambda s: {"m": AIMessage(content="hi")})
    g.set_entry_point("n")
    g.add_edge("n", END)
    return g.compile()


# -----------------------------------------------------------------------------
# 🧭 route_by_statechart
# -----------------------------------------------------------------------------
def test_router_ancestor_key_routes_nested_leaf():
    """🔥 Defect: a compound-state key ("a" / "g.a") never matched."""
    snap = statechart_node(NESTED, event_from_state=lambda s: None)({})
    assert snap["xsm"]["state_ids"] == ["g.a.b"]
    assert route_by_statechart(NESTED, {"g.a": "A"})(snap) == "A"
    assert route_by_statechart(NESTED, {"a": "A"})(snap) == "A"
    # ✅ the deepest key still wins over an ancestor
    assert route_by_statechart(NESTED, {"a": "A", "b": "B"})(snap) == "B"


def test_router_parallel_is_deterministic():
    node = statechart_node(NESTED, event_from_state=lambda s: "PAR")
    snap = node({})
    assert set(snap["xsm"]["state_ids"]) == {"g.p.x", "g.p.y"}
    route = route_by_statechart(NESTED, {"x": "X", "y": "Y"})
    assert {route(snap) for _ in range(20)} == {"X"}


def test_router_malformed_snapshot_is_config_error():
    """🔥 Defect: a non-dict snapshot raised a bare AttributeError."""
    route = route_by_statechart(NESTED, {"a": "A"})
    with pytest.raises(AgentConfigError):
        route({"xsm": [1]})
    with pytest.raises(AgentConfigError):
        route({"xsm": "[1]"})
    assert route_by_statechart(NESTED, {}, default="D")({}) == "D"


# -----------------------------------------------------------------------------
# 🧩 statechart_node
# -----------------------------------------------------------------------------
def test_node_drifted_chart_and_bad_event_fail_loudly():
    snap = statechart_node(NESTED, event_from_state=lambda s: None)({})
    edited = dict(NESTED, states=dict(NESTED["states"], z={}))
    with pytest.raises(XStateMachineError, match="structure changed"):
        statechart_node(edited, event_from_state=lambda s: None)(snap)
    with pytest.raises(XStateMachineError):
        statechart_node(NESTED, event_from_state=lambda s: 42)(snap)


def test_node_result_to_state_raising_still_stops_interpreter():
    seen = []

    def boom(interp, state):
        seen.append(interp)
        raise RuntimeError("boom")

    node = statechart_node(
        NESTED, event_from_state=lambda s: None, result_to_state=boom
    )
    with pytest.raises(RuntimeError):
        node({})
    assert seen[0].status == "stopped"


def test_node_concurrent_distinct_threads_are_isolated():
    node = statechart_node(NESTED, event_from_state=lambda s: "GO")
    before = threading.active_count()
    with ThreadPoolExecutor(8) as pool:
        outs = list(pool.map(lambda _: node({}), range(200)))
    assert all(o["xsm"]["state_ids"] == ["g.a.c"] for o in outs)
    assert threading.active_count() <= before + 1


def test_node_calls_do_not_leak():
    node = statechart_node(NESTED, event_from_state=lambda s: "GO")
    for _ in range(300):
        node({})
    gc.collect()
    tracemalloc.start()
    for _ in range(1000):
        node({})
    gc.collect()
    mid = tracemalloc.get_traced_memory()[0]
    for _ in range(1000):
        node({})
    gc.collect()
    end = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    assert end - mid < 512 * 1024


# -----------------------------------------------------------------------------
# 🛰️ langgraph_service
# -----------------------------------------------------------------------------
CHART = {
    "id": "s",
    "initial": "run",
    "states": {
        "run": {
            "invoke": {"src": "g", "onDone": "ok", "onError": "bad"},
            "on": {"STREAM": {"actions": "keep"}},
        },
        "ok": {},
        "bad": {},
    },
}


async def _run(svc, plugin=None):
    seen = []
    logic = MachineLogic(
        services={"g": svc},
        actions={"keep": lambda i, c, e, a: seen.append(e.data)},
    )
    it = Interpreter(create_machine(CHART, logic=logic))
    if plugin is not None:
        it.use(plugin)
    await it.start()
    await asyncio.sleep(0.2)
    state = set(it.current_state_ids)
    it.get_snapshot()  # 💡 a LangChain message in data must not break it
    await it.stop()
    return state, seen


@pytest.mark.parametrize("stream", [False, True])
def test_service_input_from_raising_is_on_error(stream):
    svc = langgraph_service(
        _message_graph(), input_from=lambda c, e: 1 / 0, stream=stream
    )
    assert asyncio.run(_run(svc))[0] == {"s.bad"}


def test_service_streams_non_json_chunks():
    svc = langgraph_service(
        _message_graph(), input_from=lambda c, e: {}, stream=True
    )
    state, seen = asyncio.run(_run(svc))
    assert state == {"s.ok"} and isinstance(seen[-1]["m"], AIMessage)


def test_service_output_to_raising_is_on_error():
    svc = langgraph_service(
        _message_graph(), input_from=lambda c, e: {}, output_to=lambda o: 1 / 0
    )
    assert asyncio.run(_run(svc))[0] == {"s.bad"}


# -----------------------------------------------------------------------------
# 🪝 LangChainCallbackPlugin / version guard
# -----------------------------------------------------------------------------
class _Raising(BaseCallbackHandler):
    def on_custom_event(self, *a, **k):
        raise RuntimeError("handler down")


def test_plugin_raising_handler_is_contained():
    svc = langgraph_service(_message_graph(), input_from=lambda c, e: {})
    plugin = LangChainCallbackPlugin(_Raising())
    assert asyncio.run(_run(svc, plugin))[0] == {"s.ok"}


@pytest.mark.parametrize("v", ["0.1.9", "2.0.0", "garbage", ""])
def test_version_guard_refuses(v):
    with pytest.raises(ImportError, match="tested with"):
        check_langgraph_version(v)


@pytest.mark.parametrize("v", ["0.2.0", "1.0.0a1", "1.9.99"])
def test_version_guard_accepts(v):
    check_langgraph_version(v)
