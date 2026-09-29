# src/xstate_statemachine/contrib/agents/runner.py
# -----------------------------------------------------------------------------
# 🏃 run_agent -- drive a TOOL_LOOP machine to a resting state (#287)
# -----------------------------------------------------------------------------
# 🏛️ A convenience loop, not a second runtime. It starts (or restores) an
#    interpreter, sends START with the prompt, and returns when the machine
#    RESTS: a state in *until*, a top-level final state, or a durable wait
#    (`awaiting_human`). With a store it runs inside `apersisted()` /
#    `persisted()`, so the resting snapshot -- including the `after`
#    escalation deadline of `awaiting_human` -- is written before it
#    returns, and a later call with the same key resumes it.
# -----------------------------------------------------------------------------
"""`run_agent` / `run_agent_sync`: start-or-resume and run to rest."""

from __future__ import annotations

import asyncio
import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from ...factory import create_machine
from ...models import MachineNode
from .core import TOOL_LOOP, agent_logic, validate_agent_chart
from .messages import AgentConfigError

__all__ = ["AgentResult", "run_agent", "run_agent_sync", "WAITING_STATES"]

#: States in which the loop returns because a HUMAN (or another process)
#: must act next. They persist; the machine is not finished.
WAITING_STATES: Tuple[str, ...] = ("awaiting_human",)


@dataclass(frozen=True)
class AgentResult:
    """Where the agent came to rest.

    Attributes:
        final_state: The leaf state id (``"toolLoop.done"``).
        status: Interpreter status (``"done"``, ``"running"``, ...).
        context: A deep copy of the context at rest.
        output: ``context["result"]`` (validated output or final text).
        error: ``context["error"]`` (``{"kind", "message"}``) or ``None``.
        waiting: ``True`` when resting in a durable wait state.
    """

    final_state: str
    status: str
    context: Dict[str, Any] = field(repr=False)
    output: Any = None
    error: Optional[Dict[str, Any]] = None
    waiting: bool = False

    @property
    def usage(self) -> Dict[str, Any]:
        c = self.context
        return {
            "turns": int(c.get("turns", 0)),
            "input_tokens": int(c.get("tokens_in", 0)),
            "output_tokens": int(c.get("tokens_out", 0)),
            "cost_usd": float(c.get("cost_usd", 0.0)),
        }


ChartLike = Union[MachineNode, Mapping[str, Any], str, Path, None]


def _looks_like_chart(obj: Any) -> bool:
    return obj is None or isinstance(obj, (MachineNode, Mapping, str, Path))


def _build(
    machine_or_chart: Any,
    logic: Any,
    model: Any,
    tools: Any,
    logic_kw: Dict[str, Any],
) -> MachineNode:
    if not _looks_like_chart(machine_or_chart):
        # 📝 `run_agent(model, tools=..., prompt=...)` -- the issue's
        #    one-liner: the first argument is the model, chart = TOOL_LOOP.
        if model is not None:
            raise AgentConfigError("model given twice")
        model, machine_or_chart = machine_or_chart, None
    if isinstance(machine_or_chart, MachineNode):
        if logic is not None or model is not None:
            raise AgentConfigError(
                "a built MachineNode already carries its logic; pass a "
                "chart dict to combine it with model=/logic="
            )
        return machine_or_chart
    if isinstance(machine_or_chart, (str, Path)):
        chart = json.loads(Path(machine_or_chart).read_text(encoding="utf-8"))
    elif machine_or_chart is None:
        chart = copy.deepcopy(TOOL_LOOP)
    else:
        chart = copy.deepcopy(dict(machine_or_chart))
    if logic is None:
        if model is None:
            raise AgentConfigError("pass logic= or model=")
        logic = agent_logic(model, tools, **logic_kw)
    elif model is not None or tools is not None or logic_kw:
        raise AgentConfigError("pass either logic= or model=/tools=, not both")
    machine = create_machine(chart, logic=logic)
    registry = getattr(logic, "agent_tools", None)
    if registry is not None:
        validate_agent_chart(machine, registry)
    return machine


def _leaf(interp: Any) -> str:
    ids = sorted(interp.current_state_ids)
    return ids[0] if len(ids) == 1 else ",".join(ids)


def _at_rest(interp: Any, until: Sequence[str]) -> bool:
    if interp.status != "running":
        return True
    for sid in interp.current_state_ids:
        key = sid.rsplit(".", 1)[-1]
        if key in until or key in WAITING_STATES:
            return True
    return False


def _result(interp: Any) -> AgentResult:
    ctx = copy.deepcopy(dict(interp.context))
    waiting = any(
        s.rsplit(".", 1)[-1] in WAITING_STATES
        for s in interp.current_state_ids
    )
    return AgentResult(
        final_state=_leaf(interp),
        status=interp.status,
        context=ctx,
        output=ctx.get("result"),
        error=ctx.get("error"),
        waiting=waiting,
    )


def _start_payload(interp: Any, prompt: Optional[str]) -> bool:
    return prompt is not None and any(
        s.rsplit(".", 1)[-1] == "idle" for s in interp.current_state_ids
    )


async def _until_rest(
    interp: Any, until: Sequence[str], timeout_s: Optional[float]
) -> None:
    if _at_rest(interp, until):
        return
    rested = asyncio.Event()

    def _check(i: Any) -> None:
        if _at_rest(i, until):
            rested.set()

    unsubscribe = interp.subscribe(_check)
    try:
        _check(interp)
        await asyncio.wait_for(rested.wait(), timeout_s)
    finally:
        unsubscribe()


async def run_agent(
    machine_or_chart: Any = None,
    logic: Any = None,
    *,
    model: Any = None,
    tools: Any = None,
    prompt: Optional[str] = None,
    event: Optional[Mapping[str, Any]] = None,
    store: Any = None,
    key: Optional[str] = None,
    until: Iterable[str] = ("done", "error"),
    clock: Any = None,
    plugins: Iterable[Any] = (),
    timeout_s: Optional[float] = None,
    **logic_kw: Any,
) -> AgentResult:
    """Start (or resume) an agent and run it until it rests.

    Args:
        machine_or_chart: A built `MachineNode`, a chart dict / JSON path
            (default `TOOL_LOOP`), or -- as a shortcut -- the model itself.
        logic: A `MachineLogic` (from `agent_logic`); or pass ``model=``,
            ``tools=`` and any `agent_logic` keyword (``max_turns=`` is
            accepted as a shortcut for ``budgets={"max_turns": ...}``).
        prompt: Sent as ``START`` when the machine is in ``idle``.
        event: Any other event to send on entry (e.g. ``{"type":
            "HUMAN_APPROVED"}`` when resuming a durable wait).
        store / key: Persist via `apersisted` (both or neither).
        until: State keys that end the run (besides final and waiting).
        clock: Forwarded to the interpreter (`SimulatedClock` in tests).
        plugins: Attached to the interpreter (e.g. `AgentTracePlugin`).
        timeout_s: Real-time bound on the whole run; ``None`` = none.
    """
    if (store is None) != (key is None):
        raise AgentConfigError("store= and key= go together")
    if "max_turns" in logic_kw:
        budgets = dict(logic_kw.pop("budgets", None) or {})
        budgets["max_turns"] = logic_kw.pop("max_turns")
        logic_kw["budgets"] = budgets
    machine = _build(machine_or_chart, logic, model, tools, logic_kw)
    stop_at = tuple(until)

    async def _drive(interp: Any) -> AgentResult:
        # 🧾 `wait=True`: the async `send()` only QUEUES; without the
        #    receipt the rest check below could see the pre-event state
        #    (e.g. still `awaiting_human`) and return at once.
        if _start_payload(interp, prompt):
            await interp.send("START", prompt=prompt, wait=True)
        if event is not None:
            await interp.send(dict(event), wait=True)
        await _until_rest(interp, stop_at, timeout_s)
        return _result(interp)

    if store is not None:
        from ...persistence import apersisted

        async with apersisted(
            store, str(key), machine, clock=clock, plugins=list(plugins)
        ) as interp:
            return await _drive(interp)

    from ...interpreter import Interpreter

    interp = Interpreter(machine, clock=clock)
    for p in plugins:
        interp.use(p)
    await interp.start()
    try:
        return await _drive(interp)
    finally:
        await interp.stop()


def run_agent_sync(
    machine_or_chart: Any = None,
    logic: Any = None,
    *,
    model: Any = None,
    tools: Any = None,
    prompt: Optional[str] = None,
    event: Optional[Mapping[str, Any]] = None,
    store: Any = None,
    key: Optional[str] = None,
    until: Iterable[str] = ("done", "error"),
    clock: Any = None,
    plugins: Iterable[Any] = (),
    **logic_kw: Any,
) -> AgentResult:
    """`run_agent` on `SyncInterpreter` (sync model and tools).

    Sync services complete inside the step, so the call returns as soon
    as the machine rests; an `after` timeout needs the caller to advance
    the clock (``clock.increment(ms)`` on a `SimulatedClock`).
    """
    if (store is None) != (key is None):
        raise AgentConfigError("store= and key= go together")
    if "max_turns" in logic_kw:
        budgets = dict(logic_kw.pop("budgets", None) or {})
        budgets["max_turns"] = logic_kw.pop("max_turns")
        logic_kw["budgets"] = budgets
    if logic is None and model is not None:
        logic_kw.setdefault("sync", True)
    machine = _build(machine_or_chart, logic, model, tools, logic_kw)

    def _drive(interp: Any) -> AgentResult:
        if _start_payload(interp, prompt):
            interp.send("START", prompt=prompt)
        if event is not None:
            interp.send(dict(event))
        return _result(interp)

    if store is not None:
        from ...persistence import persisted

        with persisted(
            store, str(key), machine, clock=clock, plugins=list(plugins)
        ) as interp:
            return _drive(interp)

    from ...sync_interpreter import SyncInterpreter

    interp = SyncInterpreter(machine, clock=clock)
    for p in plugins:
        interp.use(p)
    interp.start()
    try:
        return _drive(interp)
    finally:
        interp.stop()
