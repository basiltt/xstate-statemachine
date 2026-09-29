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

import itertools
import logging
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
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

__all__ = ["BudgetPlugin", "handoff_guard", "spawn_agent"]

_USAGE_KEYS = ("turns", "input_tokens", "output_tokens", "cost_usd")


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

    service_key = f"agent_{name}"
    action_name = "spawn" + name[:1].upper() + name[1:]
    counter = itertools.count(1)

    def _prepare(i: Any, ctx: Dict[str, Any], e: Any) -> Optional[Any]:
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
        # 🆔 Always unique: a sync child can finish (and free its id)
        #    inside this very action, so "reuse when free" would give
        #    every sequential sub-agent the same id in traces and rollups.
        aid = payload.get("id") or f"{name}-{next(counter)}"
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
            if ad is not None:
                i._spawn_actor(ad, e)

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
    ) -> None:
        if max_total_usd is None and max_total_tokens is None:
            raise AgentConfigError("BudgetPlugin needs at least one limit")
        self.max_total_usd = max_total_usd
        self.max_total_tokens = max_total_tokens

    def exceeded(self, totals: Mapping[str, Any]) -> bool:
        tokens = int(totals.get("input_tokens", 0)) + int(
            totals.get("output_tokens", 0)
        )
        if self.max_total_tokens is not None and (
            tokens >= self.max_total_tokens
        ):
            return True
        return self.max_total_usd is not None and (
            float(totals.get("cost_usd", 0.0)) >= self.max_total_usd
        )

    def guards(self) -> MachineLogic:
        def under(ctx: Dict[str, Any], e: Any) -> bool:
            return not ctx.get("budget_exceeded", False)

        return MachineLogic(guards={"underGlobalBudget": under})

    def on_event_received(self, interpreter: Any, event: Any) -> None:
        if getattr(event, "type", None) not in ("AGENT_DONE", "AGENT_FAILED"):
            return
        usage = (getattr(event, "payload", None) or {}).get("usage") or {}
        ctx = interpreter.context
        totals = dict(ctx.get("total_usage") or {})
        for k in _USAGE_KEYS:
            totals[k] = totals.get(k, 0) + usage.get(k, 0)
        by_agent = dict(ctx.get("usage_by_agent") or {})
        aid = (getattr(event, "payload", None) or {}).get("agent_id")
        if aid:
            by_agent[str(aid)] = dict(usage)
        ctx["total_usage"] = totals
        ctx["usage_by_agent"] = by_agent
        if not ctx.get("budget_exceeded") and self.exceeded(totals):
            ctx["budget_exceeded"] = True
            interpreter.send("BUDGET_EXCEEDED", total_usage=dict(totals))


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
    table = {k: frozenset(v) for k, v in allowed.items()}

    def _guard(ctx: Dict[str, Any], e: Any) -> bool:
        p = getattr(e, "payload", None) or {}
        return p.get("to") in table.get(str(p.get("from")), frozenset())

    return MachineLogic(guards={name: _guard})
