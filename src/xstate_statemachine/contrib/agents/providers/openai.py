# src/xstate_statemachine/contrib/agents/providers/openai.py
# -----------------------------------------------------------------------------
# 🔌 openai_model -- Chat Completions ↔ ModelResponse
# -----------------------------------------------------------------------------
# 📝 Maps the neutral message shape to Chat Completions messages
#    (`tool_calls` with JSON-string `arguments`, `role: "tool"` results),
#    neutral tool descriptors to `{"type": "function", "function": ...}`,
#    and `choices[0].message` + `usage` back to a `ModelResponse`. The
#    `openai` SDK is imported only to fail early and helpfully.
# -----------------------------------------------------------------------------
"""OpenAI adapter (``pip install openai``)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from ..messages import ModelResponse, ToolCall, Usage
from . import field, price, require_sdk

__all__ = [
    "openai_model",
    "to_openai_messages",
    "to_openai_tools",
    "from_openai_response",
]


def to_openai_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agent messages → OpenAI Chat Completions ``messages``.

    Args:
        messages: Provider-neutral agent messages (``role``/``content``/
            ``tool_calls``/``tool_call_id``).

    Returns:
        The list to pass as ``messages=``.
    """
    out: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        if role == "tool":
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m.get("tool_call_id"),
                    "content": str(m.get("content", "")),
                }
            )
        elif role == "assistant" and m.get("tool_calls"):
            out.append(
                {
                    "role": "assistant",
                    "content": m.get("content") or None,
                    "tool_calls": [
                        {
                            "id": c["id"],
                            "type": "function",
                            "function": {
                                "name": c["name"],
                                "arguments": json.dumps(
                                    c.get("arguments") or {}
                                ),
                            },
                        }
                        for c in m["tool_calls"]
                    ],
                }
            )
        else:
            out.append({"role": role, "content": str(m.get("content", ""))})
    return out


def to_openai_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Tool descriptors → OpenAI ``tools=`` (``{"type": "function"}``).

    Args:
        tools: ``{name, description, parameters}`` from `Tool.schema`.

    Returns:
        The list to pass as ``tools=``.
    """
    return [{"type": "function", "function": dict(t)} for t in tools]


def _arguments(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, Mapping):
        return dict(raw)
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        # 📝 Malformed JSON from the model → an argument the schema will
        #    reject; never guessed at.
        return {"__unparseable__": str(raw)}
    return value if isinstance(value, dict) else {"__unparseable__": value}


def from_openai_response(
    resp: Any, *, prices: Optional[Mapping[str, float]] = None
) -> ModelResponse:
    """An OpenAI chat completion (SDK object or dict) → `ModelResponse`.

    Args:
        resp: The ``chat.completions.create`` result.
        prices: ``{"input_per_mtok", "output_per_mtok"}``; ``None`` → $0.

    Returns:
        Text, tool calls (malformed JSON arguments become an unknown key,
        which the strict schema then denies) and usage.
    """
    choice = (field(resp, "choices") or [None])[0]
    msg = field(choice, "message")
    calls = [
        ToolCall(
            id=str(field(c, "id")),
            name=str(field(field(c, "function"), "name")),
            arguments=_arguments(field(field(c, "function"), "arguments")),
        )
        for c in field(msg, "tool_calls") or []
    ]
    usage = field(resp, "usage")
    tin = int(field(usage, "prompt_tokens", 0) or 0)
    tout = int(field(usage, "completion_tokens", 0) or 0)
    return ModelResponse(
        text=str(field(msg, "content") or ""),
        tool_calls=calls,
        usage=Usage(tin, tout, price(prices, tin, tout)),
        model=str(field(resp, "model") or ""),
    )


def openai_model(
    client: Any,
    model: str = "gpt-4o-mini",
    *,
    prices: Optional[Mapping[str, float]] = None,
    **create_kw: Any,
) -> Any:
    """An async `ModelCall` over ``client.chat.completions.create``.

    Args:
        client: ``openai.AsyncOpenAI()`` (or any object with the same
            ``chat.completions.create`` coroutine).
        model: Model name sent as ``model=``.
        prices: ``{"input_per_mtok", "output_per_mtok"}`` in USD, so cost
            budgets see real numbers.
        create_kw: Extra ``create()`` arguments (``temperature`` ...).

    Raises:
        MissingExtraError: the ``openai`` package is not installed.
    """
    require_sdk("openai")

    async def _call(
        messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]
    ) -> ModelResponse:
        kw: Dict[str, Any] = dict(create_kw)
        if tools:
            kw["tools"] = to_openai_tools(tools)
        resp = await client.chat.completions.create(
            model=model, messages=to_openai_messages(messages), **kw
        )
        return from_openai_response(resp, prices=prices)

    _call.is_async = True  # type: ignore[attr-defined]
    return _call
