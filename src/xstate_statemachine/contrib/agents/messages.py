# src/xstate_statemachine/contrib/agents/messages.py
# -----------------------------------------------------------------------------
# 💬 Provider-neutral model I/O: ModelResponse, ToolCall, Usage, FakeModel
# -----------------------------------------------------------------------------
# 🏛️ The chart never sees a provider SDK object. A provider adapter
#    (`providers/openai.py`, `providers/anthropic.py`) maps its SDK's
#    response into a `ModelResponse`; everything downstream -- guards,
#    context, snapshots, traces -- works on the JSON-able `to_dict()` form,
#    so a snapshot taken mid-conversation restores without the SDK
#    installed.
#
# 📝 Messages in `context["messages"]` use one neutral shape:
#      {"role": "system"|"user"|"assistant"|"tool", "content": str,
#       "tool_calls": [ToolCall dicts]   (assistant only, optional),
#       "tool_call_id": str, "name": str (tool only)}
# -----------------------------------------------------------------------------
"""Provider-neutral model responses, the `ModelCall` protocol and
`FakeModel` for offline tests."""

from __future__ import annotations

import asyncio
import copy
from dataclasses import dataclass, field
from typing import (
    Any,
    Awaitable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    Union,
)

from ...exceptions import XStateMachineError

__all__ = [
    "AgentError",
    "ToolDeniedError",
    "ToolTimeoutError",
    "AgentConfigError",
    "ToolCall",
    "Usage",
    "ModelResponse",
    "ModelCall",
    "FakeModel",
    "Message",
]

Message = Dict[str, Any]


# -----------------------------------------------------------------------------
# 🔥 Errors
# -----------------------------------------------------------------------------
class AgentError(XStateMachineError):
    """Base class for `[agents]` failures."""


class ToolDeniedError(AgentError):
    """A tool call was refused and NOT executed (X0.13).

    Raised by `run_tool` when the tool is not registered, not in the active
    state's ``meta.tools`` allow-list, or is a ``side_effect=True`` tool
    without human approval. The chart routes it to ``error`` via
    ``onError`` + the ``isToolDenied`` guard.
    """

    def __init__(self, tool: str, reason: str) -> None:
        self.tool = tool
        self.reason = reason
        super().__init__(f"tool {tool!r} denied: {reason}")


class ToolTimeoutError(AgentError):
    """A tool exceeded its mandatory ``timeout_s``."""

    def __init__(self, tool: str, timeout_s: float) -> None:
        self.tool = tool
        self.timeout_s = timeout_s
        super().__init__(f"tool {tool!r} exceeded timeout_s={timeout_s}")


class AgentConfigError(AgentError, ValueError):
    """Agent wiring is invalid (e.g. a sub-agent tool not in the parent's
    allow-list). Always raised loudly, never silently narrowed."""


# -----------------------------------------------------------------------------
# 📦 Value types
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class ToolCall:
    """One tool invocation the model PROPOSED (not yet authorised)."""

    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        try:
            args = copy.deepcopy(self.arguments)
        except RecursionError:
            # 🔥 #287 battle (A): arguments nested ~1000 deep raised out
            #    of `callModel` as a generic failure, so the turn was
            #    RETRIED (re-billed) instead of denied. Replace them with
            #    a marker the tool schema refuses.
            args = {"__unparseable__": "arguments nested too deeply"}
        return {"id": self.id, "name": self.name, "arguments": args}

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ToolCall":
        # 🔥 #287 battle (A): `dict(arguments)` coerced a list of pairs
        #    into an object (schema bypass) and crashed on a string/int.
        #    A non-object is kept as-is so `Tool.validate` denies it.
        raw = d.get("arguments")
        args: Any = {} if raw is None else raw
        if isinstance(args, Mapping):
            args = dict(args)
        return cls(id=str(d["id"]), name=str(d["name"]), arguments=args)


@dataclass(frozen=True)
class Usage:
    """Token and cost accounting for ONE model call."""

    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_tokens": int(self.input_tokens),
            "output_tokens": int(self.output_tokens),
            "cost_usd": float(self.cost_usd),
        }

    @classmethod
    def from_dict(cls, d: Optional[Mapping[str, Any]]) -> "Usage":
        d = d or {}
        return cls(
            input_tokens=int(d.get("input_tokens", 0) or 0),
            output_tokens=int(d.get("output_tokens", 0) or 0),
            cost_usd=float(d.get("cost_usd", 0.0) or 0.0),
        )


@dataclass(frozen=True)
class ModelResponse:
    """What a `ModelCall` returns: text and/or tool calls, plus usage."""

    text: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    model: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "tool_calls": [c.to_dict() for c in self.tool_calls],
            "usage": self.usage.to_dict(),
            "model": self.model,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ModelResponse":
        return cls(
            text=str(d.get("text") or ""),
            tool_calls=[
                ToolCall.from_dict(c) for c in d.get("tool_calls") or []
            ],
            usage=Usage.from_dict(d.get("usage")),
            model=str(d.get("model") or ""),
        )


class ModelCall(Protocol):
    """``async (messages, tools) -> ModelResponse`` (or the sync twin).

    *messages* are neutral message dicts; *tools* are the JSON-schema tool
    descriptors the active state allows (``{"name", "description",
    "parameters"}``). A sync callable is accepted too -- that is what
    lets the same logic run under `SyncInterpreter`.
    """

    def __call__(
        self, messages: List[Message], tools: List[Dict[str, Any]]
    ) -> Union[ModelResponse, Awaitable[ModelResponse]]:
        """Return the model's next response."""


# -----------------------------------------------------------------------------
# 🎭 FakeModel -- deterministic, offline
# -----------------------------------------------------------------------------
ScriptItem = Union[ModelResponse, Mapping[str, Any], BaseException]


class FakeModel:
    """A scripted `ModelCall` for tests, docs and `xsm`-style simulation.

    Each call consumes the next *script* item:

    * ``{"text": "..."}`` -- a final answer;
    * ``{"tool": "name", "args": {...}}`` -- one tool call;
    * ``{"tool_calls": [{"name":..., "arguments":...}, ...]}`` -- several;
    * ``{"hang": True}`` -- never answers (async only; for `after`
      timeout tests on a `SimulatedClock`);
    * a `ModelResponse` or an exception instance (raised).

    Any dict item may carry ``"usage": {"input_tokens":..,
    "output_tokens":.., "cost_usd":..}``; the default is 10 in / 5 out /
    $0.0. ``is_async=False`` makes ``__call__`` a plain function for
    `SyncInterpreter`. Every call's ``(messages, tools)`` is recorded in
    `calls` (deep copies) for assertions.
    """

    def __init__(
        self,
        script: Iterable[ScriptItem],
        *,
        is_async: bool = True,
        name: str = "fake",
        default_usage: Optional[Mapping[str, Any]] = None,
    ) -> None:
        self.script: List[ScriptItem] = list(script)
        self.is_async = is_async
        self.model_name = name
        self.default_usage = dict(
            default_usage
            or {"input_tokens": 10, "output_tokens": 5, "cost_usd": 0.0}
        )
        self.calls: List[Dict[str, Any]] = []
        self._pos = 0

    def __call__(
        self, messages: Sequence[Message], tools: Sequence[Dict[str, Any]]
    ) -> Any:
        if self.is_async:
            return self._acall(messages, tools)
        return self._next(messages, tools)

    async def _acall(
        self, messages: Sequence[Message], tools: Sequence[Dict[str, Any]]
    ) -> ModelResponse:
        item = self._peek()
        if isinstance(item, Mapping) and item.get("hang"):
            self._record(messages, tools)
            self._pos += 1
            await asyncio.Event().wait()  # cancelled by the `after` exit
        return self._next(messages, tools)

    def _peek(self) -> Optional[ScriptItem]:
        return self.script[self._pos] if self._pos < len(self.script) else None

    def _record(
        self, messages: Sequence[Message], tools: Sequence[Dict[str, Any]]
    ) -> None:
        self.calls.append(
            {
                "messages": copy.deepcopy(list(messages)),
                "tools": [t["name"] for t in tools],
            }
        )

    def _next(
        self, messages: Sequence[Message], tools: Sequence[Dict[str, Any]]
    ) -> ModelResponse:
        self._record(messages, tools)
        if self._pos >= len(self.script):
            raise AgentError(
                f"FakeModel script exhausted after {self._pos} call(s)"
            )
        item = self.script[self._pos]
        self._pos += 1
        if isinstance(item, BaseException):
            raise item
        if isinstance(item, ModelResponse):
            return item
        return self._build(dict(item), self._pos)

    def _build(self, item: Dict[str, Any], n: int) -> ModelResponse:
        usage = Usage.from_dict(
            {**self.default_usage, **item.get("usage", {})}
        )
        calls: List[ToolCall] = []
        if "tool" in item:
            calls.append(
                ToolCall(
                    id=item.get("id", f"call_{n}_0"),
                    name=item["tool"],
                    arguments=dict(item.get("args") or {}),
                )
            )
        for k, c in enumerate(item.get("tool_calls") or []):
            calls.append(
                ToolCall(
                    id=c.get("id", f"call_{n}_{k}"),
                    name=c["name"],
                    arguments=dict(c.get("arguments") or {}),
                )
            )
        return ModelResponse(
            text=str(item.get("text", "")),
            tool_calls=calls,
            usage=usage,
            model=self.model_name,
        )
