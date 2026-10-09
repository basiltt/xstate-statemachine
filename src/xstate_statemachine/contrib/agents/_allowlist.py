# src/xstate_statemachine/contrib/agents/_allowlist.py
# -----------------------------------------------------------------------------
# 🗺️ Per-state tool allow-lists (``meta.tools``) -- X0.13 (#287)
# -----------------------------------------------------------------------------
# 📝 Split out of `core.py` (over 800 lines after the #287 battle fixes).
#    `state_tools` is what the `toolAllowed` guard and the model request
#    read; `validate_agent_chart` fails loudly on a typo'd allow-list.
# -----------------------------------------------------------------------------
"""`state_tools` / `validate_agent_chart`."""

from __future__ import annotations

from typing import Any, Iterable, List

from .messages import AgentConfigError
from .tools import ALL_TOOLS, ToolRegistry

__all__ = ["state_tools", "validate_agent_chart"]


def _check_tools_meta(state_id: str, value: Any) -> List[str]:
    if not isinstance(value, list) or not all(
        isinstance(v, str) for v in value
    ):
        raise AgentConfigError(
            f"state {state_id!r}: meta.tools must be a list of tool names"
        )
    return list(value)


def state_tools(interp: Any, event: Any = None) -> List[str]:
    """The allow-list governing the current step.

    For an invoked service, the hosting state's ``meta.tools`` (the default
    invoke id IS the state id). Otherwise the union over active states.
    No ``meta.tools`` anywhere → ``[]``: closed by default.
    """
    etype = getattr(event, "type", "") or ""
    if etype.startswith("invoke."):
        node = interp.machine.get_state_by_id(etype[len("invoke.") :])
        if node is not None and "tools" in (node.meta or {}):
            return _check_tools_meta(node.id, node.meta["tools"])
    out: List[str] = []
    for sid, meta in interp.get_meta().items():
        if isinstance(meta, dict) and "tools" in meta:
            out.extend(_check_tools_meta(sid, meta["tools"]))
    return out


def _walk(node: Any) -> Iterable[Any]:
    yield node
    for child in (getattr(node, "states", None) or {}).values():
        yield from _walk(child)


def validate_agent_chart(machine: Any, registry: ToolRegistry) -> None:
    """Fail loudly when a state's ``meta.tools`` names an unregistered tool
    (a typo would otherwise silently narrow the agent)."""
    for node in _walk(machine):
        meta = getattr(node, "meta", None) or {}
        if "tools" not in meta:
            continue
        for name in _check_tools_meta(node.id, meta["tools"]):
            if name != ALL_TOOLS and name not in registry:
                raise AgentConfigError(
                    f"state {node.id!r}: meta.tools lists {name!r}, which is "
                    f"not in the tool registry {registry.names}"
                )
