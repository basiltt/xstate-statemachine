# src/xstate_statemachine/contrib/agents/langgraph.py
# -----------------------------------------------------------------------------
# 🔗 LangGraph interop -- both directions, no lock-in (#288 E2)
# -----------------------------------------------------------------------------
# 🏛️ Incremental adoption, not rip-and-replace:
#
#      * `statechart_node`  -- a statechart as ONE LangGraph node. Its
#        snapshot is plain JSON inside the graph state, so every LangGraph
#        checkpointer (MemorySaver, Postgres, ...) persists it for free;
#      * `route_by_statechart` -- a conditional-edge router keyed by the
#        statechart's active state;
#      * `langgraph_service` -- a compiled LangGraph as an `invoke` service
#        inside a statechart (`ainvoke`, or `astream` → `STREAM` events via
#        `from_async_iterator`);
#      * `LangChainCallbackPlugin` -- transitions mirrored into a LangChain
#        callback handler (LangSmith and friends).
#
# 🛡️ X0.13: nothing here executes a tool. A TOOL_LOOP statechart dropped
#    into a graph still runs tools only through `run_tool`, which re-checks
#    the allow-list, schema and approval on every call.
#
# 📝 `langgraph` is a SOFT import (never pinned, churns often). It ships
#    inside `contrib.agents` today; a separate distribution
#    (`xstate-statemachine-langgraph`) is the plan if churn bites -- see
#    the compatibility table in docs/_guide/integration-agents.md.
# -----------------------------------------------------------------------------
"""LangGraph interop: statechart-as-node, router, graph-as-service."""

from __future__ import annotations

import json
import uuid
from importlib import metadata
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from ...actor_logic import from_async_iterator
from ...events import Event
from ...factory import create_machine
from ...models import MachineNode
from ...plugins import PluginBase
from .._compat import require_extra
from .messages import AgentConfigError

__all__ = [
    "LANGGRAPH_TESTED",
    "LangChainCallbackPlugin",
    "check_langgraph_version",
    "langgraph_service",
    "route_by_statechart",
    "statechart_node",
]

#: The LangGraph major versions this adapter is tested against
#: (inclusive lower, exclusive upper). Outside it, import fails loudly.
LANGGRAPH_TESTED: Tuple[Tuple[int, int], Tuple[int, int]] = ((0, 2), (2, 0))


def _parse(version: str) -> Tuple[int, int]:
    parts = []
    for piece in version.split(".")[:2]:
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits or 0))
    while len(parts) < 2:
        parts.append(0)
    return parts[0], parts[1]


def check_langgraph_version(version: str) -> None:
    """Raise `ImportError` naming the tested range when *version* is
    outside `LANGGRAPH_TESTED`."""
    lo, hi = LANGGRAPH_TESTED
    if not (lo <= _parse(version) < hi):
        raise ImportError(
            f"xstate_statemachine.contrib.agents.langgraph is tested with "
            f"langgraph >={lo[0]}.{lo[1]},<{hi[0]}.{hi[1]}; found "
            f"{version}. Pin a tested version (see the compatibility table "
            f"in docs/_guide/integration-agents.md)."
        )


require_extra("agents", "langgraph", hint="or: pip install langgraph")
check_langgraph_version(metadata.version("langgraph"))

EventLike = Union[str, Mapping[str, Any], Event, None]
MachineLike = Union[MachineNode, Mapping[str, Any]]


def _machine(machine: MachineLike, logic: Any) -> MachineNode:
    if isinstance(machine, MachineNode):
        if logic is not None:
            raise AgentConfigError(
                "a built MachineNode already carries its logic; pass the "
                "chart dict to combine it with logic="
            )
        return machine
    return create_machine(dict(machine), logic=logic)


def _snapshot_of(state: Mapping[str, Any], key: str) -> Optional[str]:
    raw = state.get(key) if isinstance(state, Mapping) else None
    if raw is None:
        return None
    if isinstance(raw, str):
        return raw
    if isinstance(raw, Mapping):
        return json.dumps(raw)
    raise AgentConfigError(
        f"state[{key!r}] must be a snapshot dict or JSON string, "
        f"got {type(raw).__name__}"
    )


# -----------------------------------------------------------------------------
# 🧩 statechart_node
# -----------------------------------------------------------------------------
def statechart_node(
    machine: MachineLike,
    logic: Any = None,
    *,
    state_key: str = "xsm",
    event_from_state: Callable[[Dict[str, Any]], EventLike],
    result_to_state: Optional[
        Callable[[Any, Dict[str, Any]], Mapping[str, Any]]
    ] = None,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """A LangGraph node function that advances a statechart by one event.

    Each call hydrates a `SyncInterpreter` from ``state[state_key]`` (a
    fresh start when absent), sends ``event_from_state(state)`` (``None``
    sends nothing), and returns ``{state_key: <snapshot dict>, **extra}``
    where *extra* is ``result_to_state(interp, state)``. The snapshot is
    plain JSON, so LangGraph checkpointers persist it between invocations.

    Args:
        machine: A chart dict (built with *logic*) or a built `MachineNode`.
        logic: `MachineLogic` for a chart dict -- e.g. `agent_logic(...)`
            with a sync model, so a `TOOL_LOOP` runs inside the node with
            every X0.13 check in `run_tool`.
        state_key: Graph-state key holding the snapshot.
        event_from_state: Graph state → event (type string, event dict,
            `Event`, or ``None``).
        result_to_state: Optional extra graph-state updates.
    """
    built = _machine(machine, logic)

    def node(state: Dict[str, Any]) -> Dict[str, Any]:
        from ...sync_interpreter import SyncInterpreter

        snap = _snapshot_of(state, state_key)
        interp = (
            SyncInterpreter(built)
            if snap is None
            else SyncInterpreter.from_snapshot(snap, built)
        )
        interp.start()
        try:
            ev = event_from_state(state)
            if ev is not None:
                interp.send(ev)  # type: ignore[arg-type]
            updates: Dict[str, Any] = {
                state_key: json.loads(interp.get_snapshot())
            }
            if result_to_state is not None:
                updates.update(dict(result_to_state(interp, state)))
            return updates
        finally:
            interp.stop()

    node.__name__ = f"statechart_{built.id}"
    return node


# -----------------------------------------------------------------------------
# 🧭 route_by_statechart
# -----------------------------------------------------------------------------
def route_by_statechart(
    machine: MachineLike,
    mapping: Mapping[str, str],
    *,
    state_key: str = "xsm",
    default: Optional[str] = None,
) -> Callable[[Dict[str, Any]], str]:
    """A conditional-edge router: active state id → next LangGraph node.

    *mapping* keys are full state ids (``"g.review"``) or leaf keys
    (``"review"``) -- an ancestor key (``"g.a"`` / ``"a"``) routes every
    leaf beneath it, the deepest match winning. Active ids are scanned in
    sorted order, so with parallel regions the result is deterministic
    (alphabetically first region that matches). Without a
    match, *default* -- or a loud `AgentConfigError` (no silent END).
    """
    built = machine if isinstance(machine, MachineNode) else None
    root = (
        built.id
        if built is not None
        else str(dict(machine).get("id"))  # type: ignore[arg-type]
    )
    table = dict(mapping)

    def route(state: Dict[str, Any]) -> str:
        raw = _snapshot_of(state, state_key)
        snap = json.loads(raw) if raw is not None else {}
        if not isinstance(snap, Mapping):
            raise AgentConfigError(
                f"state[{state_key!r}] is not a snapshot object"
            )
        ids = sorted(snap.get("state_ids") or [])
        # 📝 #288-a: deepest match first, then ancestors -- a key naming a
        #    compound state ("a" / "g.a") routes every leaf under it.
        for sid in ids:
            parts = sid.split(".")
            for depth in range(len(parts), 0, -1):
                full = ".".join(parts[:depth])
                if full in table:
                    return table[full]
                if parts[depth - 1] in table:
                    return table[parts[depth - 1]]
        if default is not None:
            return default
        raise AgentConfigError(
            f"route_by_statechart({root!r}): no route for active states "
            f"{ids}; add them to mapping= or pass default="
        )

    return route


# -----------------------------------------------------------------------------
# 🛰️ langgraph_service
# -----------------------------------------------------------------------------
def langgraph_service(
    compiled_graph: Any,
    *,
    input_from: Callable[[Any, Any], Any],
    output_to: Optional[Callable[[Any], Any]] = None,
    stream: bool = False,
    stream_mode: str = "values",
    config: Optional[Mapping[str, Any]] = None,
) -> Callable[..., Any]:
    """A compiled LangGraph as an `invoke` service (async engine).

    ``input_from(ctx, event)`` builds the graph input. Without *stream*
    the service awaits ``ainvoke`` and ``onDone`` receives the final graph
    state (through *output_to* when given). With ``stream=True`` every
    ``astream`` chunk is sent as a ``STREAM`` event (``event.data``) via
    `from_async_iterator`, and ``onDone`` receives the last chunk. An
    exception is ``onError``; exiting the state cancels the graph run.
    """
    cfg = dict(config) if config is not None else None

    if not stream:

        async def run_graph(i: Any, ctx: Any, e: Any) -> Any:
            out = await compiled_graph.ainvoke(input_from(ctx, e), cfg)
            return output_to(out) if output_to is not None else out

        return run_graph

    async def chunks(i: Any, ctx: Any, e: Any) -> AsyncIterator[Any]:
        async for chunk in compiled_graph.astream(
            input_from(ctx, e), cfg, stream_mode=stream_mode
        ):
            yield chunk

    inner = from_async_iterator(chunks)

    async def stream_graph(i: Any, ctx: Any, e: Any) -> Any:
        last = await inner(i, ctx, e)
        return output_to(last) if output_to is not None else last

    return stream_graph


# -----------------------------------------------------------------------------
# 🪝 LangChainCallbackPlugin
# -----------------------------------------------------------------------------
class LangChainCallbackPlugin(PluginBase[Any]):
    """Mirror transitions and service outcomes into a LangChain callback
    handler as custom events (``xsm.transition``, ``xsm.service_done``,
    ``xsm.service_error``) -- they appear in LangSmith traces.

    Payloads carry state ids and event types only, never context.
    """

    def __init__(self, handler: Any, *, run_id: Any = None) -> None:
        require_extra(
            "agents", "langchain_core", hint="or: pip install langchain-core"
        )
        from langchain_core.callbacks import BaseCallbackHandler

        if not isinstance(handler, BaseCallbackHandler):
            raise AgentConfigError(
                "LangChainCallbackPlugin needs a langchain_core "
                "BaseCallbackHandler"
            )
        self.handler = handler
        self.run_id = run_id or uuid.uuid4()

    def _emit(self, name: str, data: Dict[str, Any]) -> None:
        self.handler.on_custom_event(name, data, run_id=self.run_id)

    def on_transition(
        self,
        interpreter: Any,
        from_states: Any,
        to_states: Any,
        transition: Any,
    ) -> None:
        self._emit(
            "xsm.transition",
            {
                "machine": interpreter.id,
                "from": sorted(s.id for s in from_states),
                "to": sorted(s.id for s in to_states),
                "event": getattr(transition, "event", None),
            },
        )

    def on_service_done(
        self, interpreter: Any, invocation: Any, result: Any
    ) -> None:
        self._emit(
            "xsm.service_done",
            {
                "machine": interpreter.id,
                "src": getattr(invocation, "src", None),
            },
        )

    def on_service_error(
        self, interpreter: Any, invocation: Any, error: Exception
    ) -> None:
        self._emit(
            "xsm.service_error",
            {
                "machine": interpreter.id,
                "src": getattr(invocation, "src", None),
                "error": type(error).__name__,
            },
        )
