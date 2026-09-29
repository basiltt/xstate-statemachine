# src/xstate_statemachine/contrib/agents/tools.py
# -----------------------------------------------------------------------------
# 🧰 tool_registry -- Python callables → JSON-schema tools, enforced (X0.13)
# -----------------------------------------------------------------------------
# 🏛️ The model PROPOSES a tool call; this module DECIDES. Every check the
#    chart's `toolAllowed` / `needsHuman` guards make is made AGAIN inside
#    `ToolRegistry.authorise()`, which `run_tool` calls before executing
#    anything -- so a chart edited in Stately that drops a guard, a restored
#    snapshot carrying a forged `pending_tool_calls`, or a prompt-injected
#    tool result cannot get a tool executed that the active state does not
#    allow (docs/_guide/security.md, X0.13):
#
#      1. the tool is REGISTERED;
#      2. it is in the active state's `meta.tools` allow-list ("*" = every
#         registered tool);
#      3. its arguments validate against the schema derived from the
#         Python signature (unknown keys are refused, not dropped);
#      4. `side_effect=True` tools run only for call ids a human approved
#         (`HUMAN_APPROVED` → `approved_call_ids`);
#      5. every tool has a mandatory `timeout_s`;
#      6. the output is truncated to `max_output_chars` before it re-enters
#         the conversation.
#
#    A refusal raises `ToolDeniedError` BEFORE the function is called.
# -----------------------------------------------------------------------------
"""Tool registry with schema validation and per-state allow-lists."""

from __future__ import annotations

import asyncio
import inspect
import json
import threading
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Union,
    get_type_hints,
)

from pydantic import BaseModel, ConfigDict, ValidationError, create_model

from .messages import AgentConfigError, ToolCall, ToolDeniedError
from .messages import ToolTimeoutError

__all__ = [
    "Tool",
    "ToolRegistry",
    "tool",
    "tool_registry",
    "DEFAULT_TOOL_TIMEOUT_S",
    "DEFAULT_MAX_OUTPUT_CHARS",
    "ALL_TOOLS",
]

#: Default per-tool timeout when neither `tool(timeout_s=)` nor
#: `tool_registry(timeout_s=)` sets one. A tool can never run unbounded.
DEFAULT_TOOL_TIMEOUT_S = 30.0
#: Tool output longer than this is truncated before the model sees it.
DEFAULT_MAX_OUTPUT_CHARS = 4000
#: The allow-list wildcard: every REGISTERED tool.
ALL_TOOLS = "*"


class _StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class Tool:
    """One registered tool.

    Attributes:
        name: The name the model calls it by (the function name).
        fn: The implementation -- sync or ``async def``.
        description: First docstring paragraph (sent to the model).
        args_model: Pydantic model derived from the signature.
        timeout_s: Mandatory execution bound.
        side_effect: ``True`` → requires human approval per call.
    """

    name: str
    fn: Callable[..., Any]
    description: str
    args_model: type
    timeout_s: float
    side_effect: bool = False

    @property
    def parameters(self) -> Dict[str, Any]:
        schema = self.args_model.model_json_schema()  # type: ignore[attr-defined]
        schema.pop("title", None)
        return schema

    def schema(self) -> Dict[str, Any]:
        """The provider-neutral descriptor ``{name, description,
        parameters}`` (JSON Schema)."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def validate(self, arguments: Mapping[str, Any]) -> Dict[str, Any]:
        """Validate model-proposed *arguments*; `ToolDeniedError` if bad."""
        if not isinstance(arguments, Mapping):
            raise ToolDeniedError(self.name, "arguments must be an object")
        try:
            model = self.args_model.model_validate(  # type: ignore[attr-defined]
                dict(arguments)
            )
        except ValidationError as exc:
            # 📝 Error text names fields only (`include_input=False`) --
            #    never echo the rejected values back into the conversation.
            detail = "; ".join(
                f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                for e in exc.errors(include_input=False, include_url=False)
            )
            raise ToolDeniedError(
                self.name, f"invalid arguments ({detail})"
            ) from None
        return {k: getattr(model, k) for k in type(model).model_fields}


def _description(fn: Callable[..., Any]) -> str:
    doc = inspect.getdoc(fn) or ""
    return doc.split("\n\n", 1)[0].strip()


def _args_model(fn: Callable[..., Any], name: str) -> type:
    sig = inspect.signature(fn)
    try:
        hints = get_type_hints(fn)
    except Exception:  # noqa: BLE001 -- unresolvable forward refs
        hints = {}
    fields: Dict[str, Any] = {}
    for pname, p in sig.parameters.items():
        if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
            raise AgentConfigError(
                f"tool {name!r}: *args/**kwargs cannot be described to a "
                "model; declare every parameter explicitly"
            )
        ann = hints.get(pname, Any)
        default = ... if p.default is inspect.Parameter.empty else p.default
        fields[pname] = (ann, default)
    return create_model(  # type: ignore[call-overload,no-any-return]
        f"{name}_args", __base__=_StrictArgs, **fields
    )


def tool(
    fn: Optional[Callable[..., Any]] = None,
    *,
    name: Optional[str] = None,
    timeout_s: Optional[float] = None,
    side_effect: bool = False,
    description: Optional[str] = None,
) -> Any:
    """Describe one tool; usable bare, with options, or as a decorator.

    ``timeout_s=None`` means "use the registry default" -- it is resolved
    when the tool joins a `tool_registry`, which always has one.
    """

    def _make(f: Callable[..., Any]) -> "_PendingTool":
        return _PendingTool(f, name, timeout_s, side_effect, description)

    return _make(fn) if fn is not None else _make


@dataclass(frozen=True)
class _PendingTool:
    fn: Callable[..., Any]
    name: Optional[str]
    timeout_s: Optional[float]
    side_effect: bool
    description: Optional[str]

    def build(self, default_timeout: float, default_side: bool) -> Tool:
        name = self.name or self.fn.__name__
        timeout = (
            self.timeout_s if self.timeout_s is not None else (default_timeout)
        )
        _check_timeout(name, timeout)
        return Tool(
            name=name,
            fn=self.fn,
            description=(
                self.description
                if self.description is not None
                else _description(self.fn)
            ),
            args_model=_args_model(self.fn, name),
            timeout_s=float(timeout),
            side_effect=self.side_effect or default_side,
        )


def _check_timeout(name: str, timeout: Any) -> None:
    if (
        not isinstance(timeout, (int, float))
        or isinstance(timeout, bool)
        or timeout <= 0
    ):
        raise AgentConfigError(
            f"tool {name!r}: timeout_s must be a positive number "
            f"(got {timeout!r}); every tool is bounded (X0.13)"
        )


@dataclass
class ToolRegistry:
    """Name → `Tool`, plus the enforcement `run_tool` relies on."""

    tools: Dict[str, Tool] = field(default_factory=dict)
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS

    # -- introspection ----------------------------------------------------
    @property
    def names(self) -> List[str]:
        return sorted(self.tools)

    def __contains__(self, name: object) -> bool:
        return name in self.tools

    def __len__(self) -> int:
        return len(self.tools)

    def get(self, name: str) -> Optional[Tool]:
        return self.tools.get(name)

    def expand(self, allowed: Optional[Iterable[str]]) -> Set[str]:
        """The concrete tool names an allow-list admits (``*`` → all)."""
        if allowed is None:
            return set()
        allowed = list(allowed)
        if ALL_TOOLS in allowed:
            return set(self.tools)
        return {n for n in allowed if n in self.tools}

    def schemas(
        self, allowed: Optional[Iterable[str]]
    ) -> List[Dict[str, Any]]:
        """Descriptors for the tools *allowed* admits -- what the model is
        told exists. A tool it is never told about can still be NAMED by
        an injected instruction; `authorise` is what refuses it."""
        admitted = self.expand(allowed)
        return [self.tools[n].schema() for n in sorted(admitted)]

    # -- enforcement ------------------------------------------------------
    def denial(
        self,
        call: ToolCall,
        allowed: Optional[Iterable[str]],
        approved_ids: Iterable[str] = (),
    ) -> Optional[str]:
        """Why *call* may not run, or ``None``. Pure; used by the guards
        AND by `authorise` so the two cannot disagree."""
        t = self.tools.get(call.name)
        if t is None:
            return "not registered"
        if call.name not in self.expand(allowed):
            return "not in this state's meta.tools allow-list"
        if t.side_effect and call.id not in set(approved_ids):
            return "side_effect tool without human approval"
        return None

    def authorise(
        self,
        call: ToolCall,
        allowed: Optional[Iterable[str]],
        approved_ids: Iterable[str] = (),
    ) -> Dict[str, Any]:
        """Run every X0.13 check; return validated arguments or raise
        `ToolDeniedError`. Nothing is executed here."""
        reason = self.denial(call, allowed, approved_ids)
        if reason is not None:
            raise ToolDeniedError(call.name, reason)
        return self.tools[call.name].validate(call.arguments)

    def truncate(self, value: Any) -> str:
        text = value if isinstance(value, str) else _to_text(value)
        limit = self.max_output_chars
        if len(text) <= limit:
            return text
        return f"{text[:limit]}…[truncated {len(text) - limit} chars]"

    # -- execution --------------------------------------------------------
    def call_sync(self, call: ToolCall, args: Dict[str, Any]) -> Any:
        """Execute on a worker thread bounded by ``timeout_s``.

        ⚠️ Python cannot kill a thread: a tool that overruns keeps running
        in the background (daemon) while the machine moves on. Tools with
        external effects should honour their own timeouts too.
        """
        t = self.tools[call.name]
        if inspect.iscoroutinefunction(t.fn):
            return asyncio.run(self._acall(t, args))
        box: Dict[str, Any] = {}

        def _run() -> None:
            try:
                box["value"] = t.fn(**args)
            except BaseException as exc:  # noqa: BLE001 -- re-raised below
                box["error"] = exc

        th = threading.Thread(
            target=_run, name=f"xsm-tool-{t.name}", daemon=True
        )
        th.start()
        th.join(t.timeout_s)
        if th.is_alive():
            raise ToolTimeoutError(t.name, t.timeout_s)
        if "error" in box:
            raise box["error"]
        return box.get("value")

    async def call_async(self, call: ToolCall, args: Dict[str, Any]) -> Any:
        return await self._acall(self.tools[call.name], args)

    @staticmethod
    async def _acall(t: Tool, args: Dict[str, Any]) -> Any:
        if inspect.iscoroutinefunction(t.fn):
            aw = t.fn(**args)
        else:
            loop = asyncio.get_running_loop()
            aw = loop.run_in_executor(None, lambda: t.fn(**args))
        try:
            return await asyncio.wait_for(aw, t.timeout_s)
        except asyncio.TimeoutError:
            raise ToolTimeoutError(t.name, t.timeout_s) from None


def _to_text(value: Any) -> str:
    try:
        return json.dumps(value, default=str, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def tool_registry(
    *fns: Union[Callable[..., Any], _PendingTool, Tool],
    timeout_s: float = DEFAULT_TOOL_TIMEOUT_S,
    side_effect: bool = False,
    max_output_chars: int = DEFAULT_MAX_OUTPUT_CHARS,
) -> ToolRegistry:
    """Build a `ToolRegistry` from plain functions or `tool(...)` specs.

    Args:
        fns: Callables (their signature becomes the JSON schema via
            pydantic) or `tool(fn, timeout_s=..., side_effect=...)`.
        timeout_s: Default timeout for tools that do not set their own.
            Must be positive -- there is no "unbounded".
        side_effect: Default for tools that do not set their own.
        max_output_chars: Output truncation bound.

    Raises:
        AgentConfigError: duplicate names, ``*args``/``**kwargs``
            parameters, or a non-positive timeout.
    """
    _check_timeout("<registry default>", timeout_s)
    if max_output_chars < 1:
        raise AgentConfigError("max_output_chars must be >= 1")
    reg = ToolRegistry(max_output_chars=int(max_output_chars))
    for f in fns:
        if isinstance(f, Tool):
            built = f
        elif isinstance(f, _PendingTool):
            built = f.build(timeout_s, side_effect)
        elif callable(f):
            built = _PendingTool(f, None, None, False, None).build(
                timeout_s, side_effect
            )
        else:
            raise AgentConfigError(f"not a tool: {f!r}")
        if built.name in reg.tools:
            raise AgentConfigError(f"duplicate tool name {built.name!r}")
        if built.name == ALL_TOOLS:
            raise AgentConfigError("'*' is reserved for the wildcard")
        reg.tools[built.name] = built
    return reg


def calls_from(pending: Sequence[Mapping[str, Any]]) -> List[ToolCall]:
    """Rebuild `ToolCall`s from ``context["pending_tool_calls"]``."""
    return [ToolCall.from_dict(c) for c in pending or []]
