# src/xstate_statemachine/contrib/agents/multi.py
# -----------------------------------------------------------------------------
# 👥 Multi-agent recipes: spawn_agent, BudgetPlugin, handoff_guard (#290)
# -----------------------------------------------------------------------------
# 🏛️ De-scoped per the review amendment: NO supervisor/pipeline/debate
#    runtime. A multi-agent system is an ordinary chart (see `charts/`)
#    whose actions spawn `TOOL_LOOP` actors. Three helpers make that safe:
#
#      * `spawn_agent` -- an action that spawns one sub-agent per sub-task
#        with its OWN budget. Its tool allow-list must be a SUBSET of the
#        parent's (X0.13): a supervisor cannot mint a worker that can do
#        more than it may. Refused with `AgentConfigError` at construction
#        and again at spawn time against the spawning state's meta.tools.
#        The child reports `AGENT_DONE` / `AGENT_FAILED` (with usage) via
#        its `notifyParent` entry action.
#      * `BudgetPlugin` -- aggregates every child's usage into the PARENT
#        context (`total_usage`) before the event is processed, so guards
#        see it, and raises `BUDGET_EXCEEDED` once; `spawn_agent` refuses
#        to spawn after that.
#      * `handoff_guard` -- "who may hand off to whom" as a guard over an
#        explicit table, so an unauthorised handoff is `Receipt.denied`,
#        not prompt text.
# -----------------------------------------------------------------------------
"""`spawn_agent`, `BudgetPlugin` and `handoff_guard`."""

from __future__ import annotations

import inspect
import itertools
import logging
import math
import threading
from collections import OrderedDict
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Set,
    Union,
)

from ...factory import create_machine
from ...machine_logic import MachineLogic
from ...models import ActionDefinition, MachineNode
from ...plugins import PluginBase
from .core import (
    TOOL_LOOP,
    Budget,
    _is_async_model,
    agent_logic,
    state_tools,
    validate_agent_chart,
)
from .messages import AgentConfigError
from .tools import ALL_TOOLS, ToolRegistry

logger = logging.getLogger(__name__)

__all__ = [
    "BudgetPlugin",
    "check_budget_event_declared",
    "handoff_guard",
    "spawn_agent",
]

_USAGE_KEYS = ("turns", "input_tokens", "output_tokens", "cost_usd")
_SEEN_MAX = 10_000  # de-dup ring for reports seen by both hooks


def _names(tools: Union[ToolRegistry, Iterable[str], None]) -> Set[str]:
    if tools is None:
        return set()
    if isinstance(tools, ToolRegistry):
        return set(tools.names)
    return set(tools)


def _check_subset(child: Set[str], parent: Set[str], where: str) -> None:
    if ALL_TOOLS in parent:
        return
    extra = sorted(child - parent)
    if extra:
        raise AgentConfigError(
            f"sub-agent tools {extra} are not in the parent's allow-list "
            f"{sorted(parent)} ({where}); a child may never do more than "
            "its parent (X0.13)"
        )


def spawn_agent(
    child_chart: Union[Mapping[str, Any], MachineNode, None],
    model: Any,
    tools: Optional[ToolRegistry] = None,
    *,
    budget: Union[Budget, Mapping[str, Any], None],
    parent_tools: Union[ToolRegistry, Iterable[str], None] = None,
    name: str = "agent",
    task_key: str = "task",
    tracer: Any = None,
    **logic_kw: Any,
) -> MachineLogic:
    """A `MachineLogic` providing the action ``spawn<Name>`` (and the
    service it spawns) -- merge it into the parent's logic.

    Each execution spawns one `TOOL_LOOP` child whose ``input.prompt`` is
    the triggering event's ``task`` payload (or ``context[task_key]``),
    with id ``event.id`` or ``<name>-<n>`` (unique per `spawn_agent`).

    Args:
        child_chart: Chart for the child (default `TOOL_LOOP`).
        model / tools: The child's model and `ToolRegistry`.
        budget: The child's OWN `Budget` -- required, never inherited.
        parent_tools: The parent's allow-list (names or a registry). The
            child's tools must be a subset. At spawn time the check is
            repeated against the spawning state's ``meta.tools`` when the
            parent chart declares one.
        name: Action is ``spawn`` + ``Name`` (``spawnAgent``); the child
            actor id is ``name``.
        tracer: An `AgentTracePlugin`; children write into the same trace.

    Raises:
        AgentConfigError: child tools exceed *parent_tools*, or the chart
            lists a tool the registry lacks.
    """
    if budget is None:
        raise AgentConfigError("spawn_agent requires an explicit budget=")
    registry = tools if tools is not None else ToolRegistry()
    child_names = set(registry.names)
    if parent_tools is not None:
        _check_subset(child_names, _names(parent_tools), "spawn_agent()")
    child_logic = agent_logic(
        model, registry, budgets=budget, tracer=tracer, **logic_kw
    )
    if isinstance(child_chart, MachineNode):
        raise AgentConfigError(
            "pass the child chart as a dict: spawn_agent binds its own logic"
        )
    chart = dict(child_chart) if child_chart is not None else TOOL_LOOP
    child_machine = create_machine(chart, logic=child_logic)
    validate_agent_chart(child_machine, registry)
    _require_reporting(child_machine)

    service_key = f"agent_{name}"
    action_name = "spawn" + name[:1].upper() + name[1:]
    counter = itertools.count(1)

    checked: Set[int] = set()

    def _prepare(i: Any, ctx: Dict[str, Any], e: Any) -> Optional[Any]:
        if id(i) not in checked:
            checked.add(id(i))
            if len(checked) > 64:
                checked.clear()
            check_budget_event_declared(i)  # loud: inside an action
        if ctx.get("budget_exceeded"):
            logger.warning(
                "🛑 %s: global budget exceeded; not spawning", action_name
            )
            return None
        # 🛡️ Runtime subset check against the spawning state's allow-list.
        #    Closed by default: with neither `parent_tools=` nor a
        #    `meta.tools` on the spawning state, a child with ANY tool is
        #    refused -- the parent's allow-list is then empty.
        declared = any(
            isinstance(m, dict) and "tools" in m for m in i.get_meta().values()
        )
        if declared:
            _check_subset(
                child_names, set(state_tools(i, e)), "state meta.tools"
            )
        elif parent_tools is None and child_names:
            _check_subset(child_names, set(), "no parent allow-list")
        payload = getattr(e, "payload", None) or {}
        task = payload.get("task", ctx.get(task_key))
        if not task:
            raise AgentConfigError(
                f"{action_name}: no task (event.task or context[{task_key!r}])"
            )
        # 🔥 #290 battle (A): a dict / list task was `str()`-ed into the
        #    prompt (silent acceptance). The prompt is text: refuse.
        if not isinstance(task, str):
            raise AgentConfigError(
                f"{action_name}: task must be a str, "
                f"got {type(task).__name__}"
            )
        # 🆔 Always unique: a sync child can finish (and free its id)
        #    inside this very action, so "reuse when free" would give
        #    every sequential sub-agent the same id in traces and rollups.
        aid = payload.get("id") or f"{name}-{next(counter)}"
        # 🔥 #290 battle (A): a caller-supplied id that is still LIVE was
        #    re-registered over the running child -- the first child was
        #    orphaned (gone from `_actors`, so the parent's `stop()` never
        #    cancelled it and it kept spending after the parent stopped).
        if f"{i.id}:{aid}" in i._actors:
            raise AgentConfigError(
                f"{action_name}: sub-agent id {aid!r} is already running"
            )
        # 📝 Engine-internal spawn leaf: the same path the `spawn_<key>`
        #    action prefix takes, so the child is registered, persisted
        #    and addressable (`sendTo(aid)`) exactly like any actor.
        return ActionDefinition(
            {
                "type": f"spawn_{service_key}",
                "params": {"id": aid, "input": {"prompt": str(task)}},
            }
        )

    if _is_async_model(model):

        async def _spawn_async(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ad = _prepare(i, ctx, e)
            if ad is not None:
                await i._spawn_actor(ad, e)

        action: Callable[..., Any] = _spawn_async
    else:

        def _spawn_sync(i: Any, ctx: Any, e: Any, a: Any) -> None:
            ad = _prepare(i, ctx, e)
            if ad is None:
                return
            done = i._spawn_actor(ad, e)
            # 🔥 #290 battle (A): a SYNC model's action on the ASYNC
            #    engine dropped the `_spawn_actor` coroutine -- nothing
            #    spawned, no error, the parent waited forever. Loud now.
            if inspect.iscoroutine(done):
                done.close()
                raise AgentConfigError(
                    f"{action_name}: a sync model cannot be spawned from "
                    "an async Interpreter; pass an async model"
                )

        action = _spawn_sync

    logic: MachineLogic[Any] = MachineLogic(
        actions={action_name: action},
        services={service_key: child_machine},
    )
    setattr(logic, "agent_tools", registry)
    return logic


# -----------------------------------------------------------------------------
# 💰 BudgetPlugin
# -----------------------------------------------------------------------------
class BudgetPlugin(PluginBase[Any]):
    """Roll child usage into the parent context; enforce a global budget.

    On every ``AGENT_DONE`` / ``AGENT_FAILED`` the parent receives, the
    child's ``usage`` is added to ``context["total_usage"]`` BEFORE the
    event is processed (guards see the new totals). The first time a
    limit is reached, ``context["budget_exceeded"] = True`` and a
    ``BUDGET_EXCEEDED`` event is sent to the parent; `spawn_agent`
    refuses to spawn from then on. `guards()` exposes
    ``underGlobalBudget`` for charts.
    """

    def __init__(
        self,
        max_total_usd: Optional[float] = None,
        max_total_tokens: Optional[int] = None,
        *,
        max_tracked_agents: int = 10_000,
    ) -> None:
        if max_total_usd is None and max_total_tokens is None:
            raise AgentConfigError("BudgetPlugin needs at least one limit")
        # 🔥 #290 battle (A): limits were never validated. "5" made
        #    `exceeded()` raise inside a fail-open hook -- the global
        #    budget was silently never enforced.
        _check_limit("max_total_usd", max_total_usd, int_only=False)
        _check_limit("max_total_tokens", max_total_tokens, int_only=True)
        _check_limit("max_tracked_agents", max_tracked_agents, True)
        self.max_total_usd = max_total_usd
        self.max_total_tokens = max_total_tokens
        self.max_tracked_agents = max_tracked_agents
        # 🔥 #290 battle (A): de-dup was keyed on `id(event)` WITHOUT
        #    holding the event. CPython reuses a freed object's id at once,
        #    so a later, DIFFERENT report looked "seen" and was never
        #    counted (200 reports rolled up as 16 turns). Now keyed on the
        #    report's payload dict, held strongly so its id cannot be
        #    reused while remembered; the payload also survives the async
        #    engine's `wait=True` envelope copy. Bounded FIFO.
        self._seen: "OrderedDict[int, Any]" = OrderedDict()
        self._tripped: Dict[int, Any] = {}
        # 📝 #290 review (5): one plugin may be `.use()`d by several sync
        #    supervisors on different threads; the de-dup maps are shared.
        self._lock = threading.Lock()

    def exceeded(self, totals: Mapping[str, Any]) -> bool:
        tokens = _num(totals.get("input_tokens", 0)) + _num(
            totals.get("output_tokens", 0)
        )
        if self.max_total_tokens is not None and (
            tokens >= self.max_total_tokens
        ):
            return True
        return self.max_total_usd is not None and (
            _num(totals.get("cost_usd", 0.0)) >= self.max_total_usd
        )

    def guards(self) -> MachineLogic:
        def under(ctx: Dict[str, Any], e: Any) -> bool:
            return not ctx.get("budget_exceeded", False)

        return MachineLogic(guards={"underGlobalBudget": under})

    def on_interpreter_start(self, interpreter: Any) -> None:
        # 🔥 #290 review (6): `BUDGET_EXCEEDED` is sent from a hook; under
        #    `strict: true` an undeclared event raises there, the error is
        #    swallowed and the trip is lost while the flag stays True.
        #    Plugin hooks are fail-open, so this cannot stop `start()`
        #    itself -- it logs here and `spawn_agent` re-checks inside
        #    its action (which DOES fail loudly) before the first spawn.
        try:
            check_budget_event_declared(interpreter)
        except AgentConfigError as exc:
            logger.error("🔥 %s", exc)
            raise

    def on_before_send(self, interpreter: Any, event: Any) -> Optional[Any]:
        # 🔥 #290 battle: the rollup ran in `on_event_received`, i.e. when
        #    the parent DEQUEUED the child's report. A planner that hands
        #    off a batch (`handOffTasks` sends N HANDOFFs in one action)
        #    had all N queued before the first AGENT_DONE was processed, so
        #    every worker spawned however small the global budget. The
        #    totals and `budget_exceeded` now land the moment the child
        #    SENDS (this hook fires before the event is queued), so the
        #    next HANDOFF dequeued refuses to spawn. The BUDGET_EXCEEDED
        #    event itself is sent when the report is dequeued (below) so
        #    it queues AFTER the report: the result that tripped the
        #    budget is still collected. Returns None: never blocks.
        # 🔥 #290 review (2): this hook also fires for a report the parent
        #    will DROP (already stopped); counting it inflated the totals
        #    of a finished run. Only a running parent is charged here; a
        #    report that still enters the machine is counted on dequeue.
        if getattr(interpreter, "status", "running") == "running":
            self._rollup(interpreter, event)
        return None

    def on_event_received(self, interpreter: Any, event: Any) -> None:
        # 📝 Reports that bypassed `send()` (a restored queue, a direct
        #    `_process_event`) are still counted exactly once: `_rollup`
        #    remembers the events it has already seen.
        self._rollup(interpreter, event)
        p = getattr(event, "payload", None)
        with self._lock:
            # 📝 #290 review (3): a report that reached the machine needs
            #    no further de-dup -- release its payload (transcripts
            #    may be large) instead of holding 10k of them.
            if self._seen.get(id(p), self) is p:
                del self._seen[id(p)]
            tripped = self._tripped.get(id(p), self) is p
            if tripped:
                del self._tripped[id(p)]
        if tripped:
            interpreter.send(
                "BUDGET_EXCEEDED",
                total_usage=dict(interpreter.context.get("total_usage") or {}),
            )

    def _rollup(self, interpreter: Any, event: Any) -> None:
        """Add the report's usage to the parent context; flag the one
        report that crosses the global limit."""
        if getattr(event, "type", None) not in ("AGENT_DONE", "AGENT_FAILED"):
            return
        payload = getattr(event, "payload", None)
        if not isinstance(payload, Mapping):
            payload = {}
        key = id(payload)
        with self._lock:
            if self._seen.get(key, self) is payload:
                return
            self._seen[key] = payload
            while len(self._seen) > _SEEN_MAX:
                self._seen.popitem(last=False)
        usage = payload.get("usage") if isinstance(payload, Mapping) else {}
        usage = usage if isinstance(usage, Mapping) else {}
        ctx = interpreter.context
        totals = dict(ctx.get("total_usage") or {})
        for k in _USAGE_KEYS:
            totals[k] = totals.get(k, 0) + _num(usage.get(k, 0))
        by_agent = dict(ctx.get("usage_by_agent") or {})
        aid = payload.get("agent_id")
        if aid:
            # 🔥 #290 battle (A): stored raw (NaN / "x" / huge payloads
            #    kept verbatim) and unbounded: a long-lived supervisor grew
            #    forever. Sanitised like the totals; oldest evicted.
            by_agent.pop(str(aid), None)
            by_agent[str(aid)] = {
                k: _num(usage.get(k, 0)) for k in _USAGE_KEYS
            }
            while len(by_agent) > self.max_tracked_agents:
                by_agent.pop(next(iter(by_agent)))
        ctx["total_usage"] = totals
        ctx["usage_by_agent"] = by_agent
        if not ctx.get("budget_exceeded") and self.exceeded(totals):
            ctx["budget_exceeded"] = True
            with self._lock:
                self._tripped[key] = payload


def check_budget_event_declared(interpreter: Any) -> None:
    """Raise `AgentConfigError` when a ``strict`` parent chart does not
    declare ``BUDGET_EXCEEDED`` -- `BudgetPlugin` could never deliver it.
    """
    machine = getattr(interpreter, "machine", None)
    known = getattr(machine, "is_known_event", None)
    if (
        getattr(interpreter, "strict", False)
        and callable(known)
        and not known("BUDGET_EXCEEDED", user_sent=True)
    ):
        raise AgentConfigError(
            "BudgetPlugin: a strict chart must declare the BUDGET_EXCEEDED "
            "event it will receive"
        )


def _check_limit(name: str, v: Any, int_only: bool) -> None:
    if v is None:
        return
    ok = isinstance(v, (int, float)) and not isinstance(v, bool)
    if int_only:
        ok = ok and isinstance(v, int)
    if not ok or not math.isfinite(v) or v < 0:
        raise AgentConfigError(
            f"BudgetPlugin {name} must be a non-negative finite "
            f"{'int' if int_only else 'number'} (got {v!r})"
        )


def _require_reporting(machine: MachineNode) -> None:
    """🔥 #290 battle (A): a child chart with no ``notifyParent`` entry
    never reports, so the parent waited for AGENT_DONE forever (and the
    BudgetPlugin never saw its spend). Refused at construction."""
    # 📝 #290 review (4): `entry` only would wrongly refuse a chart that
    #    reports from `exit`, a transition's `actions`, `onDone`/`onError`
    #    or `always` -- every action list is scanned.
    stack: List[Any] = [machine]
    while stack:
        node = stack.pop()
        for ad in _all_actions(node):
            if getattr(ad, "type", None) == "notifyParent":
                return
        stack.extend((getattr(node, "states", None) or {}).values())
    raise AgentConfigError(
        "spawn_agent: the child chart never runs 'notifyParent', so the "
        "parent would never receive AGENT_DONE / AGENT_FAILED"
    )


def _all_actions(node: Any) -> Iterable[Any]:
    """Every `ActionDefinition` reachable from one state node."""
    yield from getattr(node, "entry", None) or ()
    yield from getattr(node, "exit", None) or ()
    transitions: List[Any] = []
    for attr in ("on", "after", "on_done", "on_error"):
        value = getattr(node, attr, None)
        if isinstance(value, Mapping):  # `on` holds `always` under ""
            for t in value.values():
                transitions.extend(t if isinstance(t, list) else [t])
        elif isinstance(value, list):
            transitions.extend(value)
        elif value is not None:
            transitions.append(value)
    inv = getattr(node, "invoke", None)
    for i in inv if isinstance(inv, list) else ([inv] if inv else []):
        for attr in ("on_done", "on_error"):
            t = getattr(i, attr, None)
            transitions.extend(
                t if isinstance(t, list) else ([t] if t else [])
            )
    for t in transitions:
        yield from getattr(t, "actions", None) or ()


def _num(value: Any) -> Any:
    """A usage number from a child's report: non-numeric / bool / NaN /
    negative counts never reduce or poison the rollup (0)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    # 🔥 #290 review (1): `inf` passed; `exceeded()` then raised
    #    OverflowError inside a fail-open hook on EVERY later report --
    #    the global budget was permanently disabled by one bad number.
    if not math.isfinite(value) or value < 0:
        return 0
    return value


# -----------------------------------------------------------------------------
# 🤝 handoff_guard
# -----------------------------------------------------------------------------
def handoff_guard(
    allowed: Mapping[str, Iterable[str]], *, name: str = "handoffAllowed"
) -> MachineLogic:
    """Guard ``handoffAllowed``: ``event.to in allowed[event.from]``.

    Anything not listed is refused -- closed by default. Use it on the
    handoff transition; an unauthorised handoff yields
    ``Receipt.denied == True``.
    """
    # 🔥 #290 battle (A): `{"planner": "worker"}` became the CHARACTER
    #    set {"w", "o", ...}: "worker" was refused and "w" allowed. Each
    #    value must be a collection of str names; refused at construction.
    table: Dict[str, FrozenSet[str]] = {}
    for k, v in allowed.items():
        if not isinstance(k, str) or isinstance(v, (str, bytes)):
            raise AgentConfigError(
                f"handoff_guard: {k!r} must map a str to a list of str"
            )
        try:
            names = frozenset(v)
        except TypeError:
            raise AgentConfigError(
                f"handoff_guard: allowed[{k!r}] is not iterable"
            ) from None
        if not all(isinstance(n, str) for n in names):
            raise AgentConfigError(
                f"handoff_guard: allowed[{k!r}] must hold str names"
            )
        table[k] = names

    def _guard(ctx: Dict[str, Any], e: Any) -> bool:
        p = getattr(e, "payload", None)
        if not isinstance(p, Mapping):
            return False
        src, dst = p.get("from"), p.get("to")
        # 📝 Exact str match only: None / int never match via `str()`,
        #    and an unhashable list no longer raises inside the guard.
        if not isinstance(src, str) or not isinstance(dst, str):
            return False
        return dst in table.get(src, frozenset())

    return MachineLogic(guards={name: _guard})
