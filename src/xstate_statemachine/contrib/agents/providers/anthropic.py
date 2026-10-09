# src/xstate_statemachine/contrib/agents/providers/anthropic.py
# -----------------------------------------------------------------------------
# 🔌 anthropic_model -- Messages API ↔ ModelResponse
# -----------------------------------------------------------------------------
# 📝 Neutral → Messages API: `system` messages become the `system=`
#    parameter; assistant tool calls become `tool_use` content blocks;
#    `role: "tool"` results become `tool_result` blocks inside a `user`
#    turn (consecutive results are merged into one turn, as the API
#    requires). Tool descriptors map `parameters` → `input_schema`.
#    Back: `text` blocks join into `text`, `tool_use` blocks become
#    `ToolCall`s, `usage.input_tokens` / `output_tokens` map directly.
# -----------------------------------------------------------------------------
"""Anthropic adapter (``pip install anthropic``)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Tuple

from ..messages import ModelResponse, ToolCall, Usage
from . import field, price, require_sdk

__all__ = [
    "anthropic_model",
    "to_anthropic_messages",
    "to_anthropic_tools",
    "from_anthropic_response",
]


def to_anthropic_messages(
    messages: List[Dict[str, Any]],
) -> Tuple[str, List[Dict[str, Any]]]:
    """``(system, messages)`` for ``client.messages.create``."""
    system: List[str] = []
    out: List[Dict[str, Any]] = []
    proposed: set = set()
    for m in messages:
        role = m.get("role")
        if role == "system":
            system.append(str(m.get("content", "")))
            continue
        if role == "tool" and m.get("tool_call_id") not in proposed:
            # 🔥 #287 battle (A): `max_messages` trimming can drop the
            #    assistant turn that proposed this call; the provider
            #    400s an orphan tool result -- skip it.
            continue
        if role == "assistant":
            proposed.update(c.get("id") for c in m.get("tool_calls") or [])
        if role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id"),
                "content": str(m.get("content", "")),
            }
            if (
                out
                and out[-1]["role"] == "user"
                and isinstance(out[-1]["content"], list)
            ):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
            continue
        if role == "assistant" and m.get("tool_calls"):
            blocks: List[Dict[str, Any]] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": str(m["content"])})
            for c in m["tool_calls"]:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": c["id"],
                        "name": c["name"],
                        "input": dict(c.get("arguments") or {}),
                    }
                )
            out.append({"role": "assistant", "content": blocks})
            continue
        out.append({"role": role, "content": str(m.get("content", ""))})
    return "\n\n".join(system), out


def to_anthropic_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tool descriptors → Anthropic ``tools=`` (``input_schema``).

    Args:
        tools: ``{name, description, parameters}`` from `Tool.schema`.

    Returns:
        The list to pass as ``tools=``.
    """
    return [
        {
            "name": t["name"],
            "description": t.get("description", ""),
            "input_schema": t.get("parameters") or {"type": "object"},
        }
        for t in tools
    ]


def from_anthropic_response(
    resp: Any, *, prices: Optional[Mapping[str, float]] = None
) -> ModelResponse:
    """An Anthropic message (SDK object or dict) → `ModelResponse`.

    Args:
        resp: The ``messages.create`` result.
        prices: ``{"input_per_mtok", "output_per_mtok"}``; ``None`` → $0.

    Returns:
        Text blocks joined, ``tool_use`` blocks as tool calls, usage.
    """
    texts: List[str] = []
    calls: List[ToolCall] = []
    for block in field(resp, "content") or []:
        kind = field(block, "type")
        if kind == "text":
            texts.append(str(field(block, "text") or ""))
        elif kind == "tool_use":
            raw = field(block, "input")
            raw = {} if raw is None else raw
            if not isinstance(raw, Mapping):
                dump = getattr(raw, "model_dump", None)
                raw = dump() if callable(dump) else raw
            # 🔥 #287 battle (A): a non-object `input` became `{}` -- a
            #    malformed call to a tool with no required parameters
            #    RAN. Now it is kept so the schema check denies it.
            calls.append(
                ToolCall(
                    id=str(field(block, "id")),
                    name=str(field(block, "name")),
                    arguments=(
                        dict(raw)
                        if isinstance(raw, Mapping)
                        else {"__unparseable__": raw}
                    ),
                )
            )
    usage = field(resp, "usage")
    tin = int(field(usage, "input_tokens", 0) or 0)
    tout = int(field(usage, "output_tokens", 0) or 0)
    return ModelResponse(
        text="".join(texts),
        tool_calls=calls,
        usage=Usage(tin, tout, price(prices, tin, tout)),
        model=str(field(resp, "model") or ""),
    )


def anthropic_model(
    client: Any,
    model: str = "claude-sonnet-4-5",
    *,
    max_tokens: int = 1024,
    prices: Optional[Mapping[str, float]] = None,
    **create_kw: Any,
) -> Any:
    """An async `ModelCall` over ``client.messages.create``.

    Args:
        client: ``anthropic.AsyncAnthropic()`` (or any object with the
            same ``messages.create`` coroutine).
        model: Model name sent as ``model=``.
        max_tokens: Required by the Messages API.
        prices: ``{"input_per_mtok", "output_per_mtok"}`` in USD.
        create_kw: Extra ``create()`` arguments.

    Raises:
        MissingExtraError: the ``anthropic`` package is not installed.
    """
    require_sdk("anthropic")

    async def _call(
        messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> ModelResponse:
        system, msgs = to_anthropic_messages(messages)
        kw: Dict[str, Any] = dict(create_kw)
        if system:
            kw["system"] = system
        if tools:
            kw["tools"] = to_anthropic_tools(tools)
        resp = await client.messages.create(
            model=model, max_tokens=max_tokens, messages=msgs, **kw
        )
        return from_anthropic_response(resp, prices=prices)

    _call.is_async = True  # type: ignore[attr-defined]
    return _call
