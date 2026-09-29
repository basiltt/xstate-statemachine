# src/xstate_statemachine/contrib/agents/pydantic_ai.py
# -----------------------------------------------------------------------------
# 🧪 pydantic-ai interop -- an Agent as an invoke service, a chart as a Tool
# -----------------------------------------------------------------------------
# 🏛️ pydantic-ai is type-safe, single-agent and code-first, with no
#    orchestration graph. The statechart supplies that graph: a
#    `pydantic_ai.Agent` runs as ONE invoked service, its usage lands in the
#    same `tokens_in` / `tokens_out` / `turns` context keys `budget_guards`
#    read, and the inverse direction exposes a whole statechart run as a
#    pydantic-ai `Tool`.
#
# 🛡️ X0.13: tools a pydantic-ai Agent registers run inside pydantic-ai, not
#    through `run_tool`. Give such an agent only tools that are safe in
#    every state that invokes it, or keep tool execution in TOOL_LOOP.
#
# 📝 `pydantic_ai` is a SOFT import (never pinned). Result/usage attribute
#    names moved between releases (`.data` → `.output`, `usage()` →
#    `usage`); both spellings are read.
# -----------------------------------------------------------------------------
"""pydantic-ai interop: `pydantic_ai_service`, `agent_tool_from_machine`."""

from __future__ import annotations

import inspect
from typing import Any, AsyncIterator, Callable, Dict, Optional

from pydantic import BaseModel

from ...actor_logic import from_async_iterator
from ...machine_logic import MachineLogic
from .._compat import require_extra

require_extra("agents", "pydantic_ai", hint="or: pip install pydantic-ai")

__all__ = [
    "agent_tool_from_machine",
    "pydantic_ai_service",
    "usage_logic",
]


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    return value


def _usage(obj: Any) -> Dict[str, int]:
    u = getattr(obj, "usage", None)
    if callable(u):
        u = u()
    out = {"input_tokens": 0, "output_tokens": 0, "requests": 0}
    if u is None:
        return out
    for key, *alts in (
        ("input_tokens", "request_tokens"),
        ("output_tokens", "response_tokens"),
        ("requests",),
    ):
        for name in (key, *alts):
            v = getattr(u, name, None)
            if v:
                out[key] = int(v)
                break
    return out


async def _output(res: Any) -> Any:
    if hasattr(res, "output"):
        out = res.output
    elif hasattr(res, "get_output"):
        out = res.get_output()
    else:  # pragma: no cover -- pydantic-ai < 0.3
        out = res.data
    if inspect.isawaitable(out):
        out = await out
    return _jsonable(out)


def pydantic_ai_service(
    agent: Any,
    *,
    prompt_from: Callable[[Any, Any], str],
    deps_from: Optional[Callable[[Any, Any], Any]] = None,
    stream: bool = False,
) -> Callable[..., Any]:
    """A `pydantic_ai.Agent` as an `invoke` service (async engine).

    ``onDone`` data is ``{"output": <result.output, pydantic models
    dumped>, "usage": {"input_tokens", "output_tokens", "requests"}}``.
    Add `usage_logic()` and ``"actions": "recordAgentUsage"`` on
    ``onDone`` so `budget_guards` see the spend.

    With ``stream=True`` each text delta is sent as a ``STREAM`` event
    (``event.data == {"delta": "..."}``) via `from_async_iterator`, and
    ``onDone`` receives the same ``{"output", "usage"}`` as above.
    Exceptions are ``onError``; exiting the state cancels the run.
    """

    def _args(ctx: Any, e: Any) -> Dict[str, Any]:
        kw: Dict[str, Any] = {}
        if deps_from is not None:
            kw["deps"] = deps_from(ctx, e)
        return kw

    if not stream:

        async def run_pydantic_agent(i: Any, ctx: Any, e: Any) -> Any:
            res = await agent.run(prompt_from(ctx, e), **_args(ctx, e))
            return {"output": await _output(res), "usage": _usage(res)}

        return run_pydantic_agent

    async def deltas(i: Any, ctx: Any, e: Any) -> AsyncIterator[Any]:
        async with agent.run_stream(prompt_from(ctx, e), **_args(ctx, e)) as s:
            async for delta in s.stream_text(delta=True):
                yield {"delta": delta}
            yield {"output": await _output(s), "usage": _usage(s)}

    inner = from_async_iterator(deltas)

    async def stream_pydantic_agent(i: Any, ctx: Any, e: Any) -> Any:
        return await inner(i, ctx, e)

    return stream_pydantic_agent


def usage_logic(name: str = "recordAgentUsage") -> MachineLogic:
    """An action that adds an ``onDone`` usage block to ``tokens_in`` /
    ``tokens_out`` and counts one ``turns`` -- the keys `budget_guards`
    read."""

    def record(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        data = getattr(e, "data", None) or {}
        usage = data.get("usage") or {}
        ctx["tokens_in"] = int(ctx.get("tokens_in", 0)) + int(
            usage.get("input_tokens", 0)
        )
        ctx["tokens_out"] = int(ctx.get("tokens_out", 0)) + int(
            usage.get("output_tokens", 0)
        )
        ctx["turns"] = int(ctx.get("turns", 0)) + 1
        ctx["result"] = data.get("output")

    return MachineLogic(actions={name: record})


def agent_tool_from_machine(
    runner: Callable[[str], Any],
    *,
    name: str = "run_statechart",
    description: str = (
        "Delegate a task to a statechart-governed agent and return its "
        "result."
    ),
) -> Any:
    """Expose a statechart run as a pydantic-ai `Tool`.

    *runner* is ``(prompt) -> AgentResult`` (sync or async) -- typically
    ``lambda p: run_agent(machine, prompt=p)``. The tool returns
    ``{"state", "output", "error"}``; the statechart's own budgets,
    allow-lists and approvals still apply inside it.
    """
    from pydantic_ai import Tool

    async def run_statechart(prompt: str) -> Dict[str, Any]:
        res = runner(prompt)
        if inspect.isawaitable(res):
            res = await res
        return {
            "state": getattr(res, "final_state", None),
            "output": _jsonable(getattr(res, "output", res)),
            "error": getattr(res, "error", None),
        }

    return Tool(run_statechart, name=name, description=description)
