# src/xstate_statemachine/contrib/agents/core.py
# -----------------------------------------------------------------------------
# 🤖 agent_logic -- the MachineLogic that drives the TOOL_LOOP chart (#287)
# -----------------------------------------------------------------------------
# 🏛️ "The model proposes, the machine decides." The model is ONE invoked
#    service (`callModel`); everything that matters for safety is chart
#    structure plus the guards and the `runTool` service below:
#
#      * budgets are guards on the single entry to a model turn
#        (`checking_budget`), so no path reaches the model over budget;
#      * which tools the model is TOLD about and which may RUN are the
#        `meta.tools` allow-lists of `awaiting_model` / `awaiting_tool`;
#      * `runTool` re-checks the allow-list, the argument schema and human
#        approval itself (X0.13) -- a guard is advisory, the service is not;
#      * `awaiting_human` is an ordinary state, so it persists in any store
#        and its `after` escalation is a durable deadline.
#
# 📝 Zero third-party imports beyond pydantic. Provider SDKs live in
#    `providers/` and are imported only inside their factory functions.
# -----------------------------------------------------------------------------
"""Logic, guards and budgets for the `TOOL_LOOP` reference chart."""

from __future__ import annotations

import copy
import inspect
import json
import logging
import re
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Tuple,
    Union,
)

from ...machine_logic import MachineLogic
from ...patterns.retry import RetryPolicy
from ...plugins import redact
from ._output import (
    _meta_output_model,
    _resolve_model,
    _task_of,
    _validate_output,
)
from .budgets import Budget, _spent_tokens, _spent_usd, budget_guards
from .messages import (
    AgentConfigError,
    Message,
    ModelResponse,
    ToolCall,
    ToolDeniedError,
)
from .tools import ALL_TOOLS, ToolRegistry, calls_from

logger = logging.getLogger(__name__)

__all__ = [
    "AGENT_REDACT_KEYS",
    "Budget",
    "CHARTS_DIR",
    "TOOL_LOOP",
    "agent_logic",
    "budget_guards",
    "load_chart",
    "scrub",
    "state_tools",
    "validate_agent_chart",
]

CHARTS_DIR = Path(__file__).resolve().parent / "charts"

#: Keys redacted from tool results before they enter `context` (and so
#: snapshots) and from trace records. Substring, case-insensitive --
#: ``access_token``, ``Authorization`` and ``x-api-key`` all match.
AGENT_REDACT_KEYS: Tuple[str, ...] = (
    "api_key",
    "apikey",
    "api-key",
    "authorization",
    "token",
    "secret",
    "password",
    "bearer",
    "cookie",
    "private_key",
    "credential",
)


#: Best-effort VALUE patterns scrubbed from strings (key-based redaction
#: cannot see a secret inside free text): bearer tokens, ``sk-``/``sk_``
#: style API keys, JWTs.
_SECRET_VALUE = re.compile(
    r"(?i)(bearer\s+[A-Za-z0-9._~+/=-]{8,})"
    r"|\b(sk|pk|rk|xox[abp])[-_][A-Za-z0-9_-]{8,}"
    r"|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"
)


def scrub(value: Any, *, by_key: bool = True) -> Any:
    """`redact()` by key (unless *by_key* is false), then mask
    secret-looking substrings in string values. Best-effort: it cannot
    recognise every secret format."""
    if by_key:
        value = redact(value, AGENT_REDACT_KEYS)
    if isinstance(value, str):
        return _SECRET_VALUE.sub("***", value)
    if isinstance(value, dict):
        return {k: scrub(v, by_key=by_key) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(scrub(v, by_key=by_key) for v in value)
    return value


def load_chart(name: str = "tool_loop") -> Dict[str, Any]:
    """A fresh (deep-copied) reference chart by name: ``tool_loop``,
    ``supervisor``, ``pipeline`` or ``debate``."""
    path = CHARTS_DIR / f"{name}.json"
    if not path.is_file():
        raise AgentConfigError(f"no reference chart named {name!r}")
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


#: The TOOL_LOOP reference chart as a dict. Treat as read-only; call
#: `load_chart()` for a copy to edit.
TOOL_LOOP: Dict[str, Any] = load_chart("tool_loop")


# -----------------------------------------------------------------------------
# 🗺️ Allow-lists (meta.tools)
# -----------------------------------------------------------------------------
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


# -----------------------------------------------------------------------------
# 🏭 agent_logic
# -----------------------------------------------------------------------------
def _is_async_model(model: Any) -> bool:
    flag = getattr(model, "is_async", None)
    if isinstance(flag, bool):
        return flag
    return inspect.iscoroutinefunction(model) or inspect.iscoroutinefunction(
        getattr(model, "__call__", None)
    )


def _usage_totals(ctx: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "turns": int(ctx.get("turns", 0)),
        "input_tokens": int(ctx.get("tokens_in", 0)),
        "output_tokens": int(ctx.get("tokens_out", 0)),
        "cost_usd": round(float(ctx.get("cost_usd", 0.0)), 10),
    }


class _AgentLogic:
    """Closure state for one `agent_logic()` call (split out for size)."""

    def __init__(
        self,
        model: Any,
        tools: ToolRegistry,
        budget: Budget,
        output_model: Any,
        max_messages: int,
        summarise: Optional[Callable[[List[Message]], List[Message]]],
        max_output_retries: int,
        system_prompt: Optional[str],
        tracer: Any = None,
        max_tool_calls: int = 8,
        output_parser: Optional[Callable[[str], Any]] = None,
    ) -> None:
        self.model = model
        self.tools = tools
        self.budget = budget
        self.output_model = _resolve_model(output_model)
        self.max_messages = max_messages
        self.summarise = summarise
        self.max_output_retries = max_output_retries
        self.system_prompt = system_prompt
        self.tracer = tracer
        self.max_tool_calls = max_tool_calls
        self.output_parser = output_parser

    # -- helpers ----------------------------------------------------------
    def _trace(self, i: Any, kind: str, **fields: Any) -> None:
        if self.tracer is not None:
            self.tracer.record(i, kind, **fields)

    def _bound(self, messages: List[Message]) -> List[Message]:
        if len(messages) <= self.max_messages:
            return messages
        if self.summarise is not None:
            out = list(self.summarise(list(messages)))
            if len(out) > self.max_messages:
                raise AgentConfigError(
                    "summarise() must return at most max_messages messages"
                )
            return out
        # 📝 Keep the task (first message) and the most recent tail.
        head = messages[:1]
        return head + messages[-(self.max_messages - 1) :]

    def _append(self, ctx: Dict[str, Any], *msgs: Message) -> None:
        ctx["messages"] = self._bound(
            list(ctx.get("messages") or []) + list(msgs)
        )

    def _output_model_for(self, e: Any) -> Optional[type]:
        """Constructor-level model, else the hosting state's
        ``meta.output_model`` that `callModel` recorded in its result."""
        if self.output_model is not None:
            return self.output_model
        return _resolve_model(self._data(e).get("output_model"))

    # -- services ---------------------------------------------------------
    def _model_request(
        self, i: Any, ctx: Dict[str, Any], e: Any
    ) -> Tuple[List[Message], List[Dict[str, Any]], Dict[str, Any]]:
        allowed = state_tools(i, e)
        schemas = self.tools.schemas(allowed)
        messages = copy.deepcopy(list(ctx.get("messages") or []))
        if self.system_prompt:
            messages.insert(
                0, {"role": "system", "content": self.system_prompt}
            )
        extra: Dict[str, Any] = {
            "allowed_tools": sorted(self.tools.expand(allowed))
        }
        spec = _meta_output_model(i, e)
        if spec is not None:
            _resolve_model(spec)  # fail loudly on a bad spec, before calling
            extra["output_model"] = spec
        return messages, schemas, extra

    @staticmethod
    def _response_data(resp: Any, extra: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(resp, Mapping):
            resp = ModelResponse.from_dict(resp)
        if not isinstance(resp, ModelResponse):
            raise TypeError(
                f"a ModelCall must return ModelResponse, got {type(resp)!r}"
            )
        data = resp.to_dict()
        data.update(extra)
        return data

    def _bounded(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Cap what a (possibly injected) response can put in context:
        text truncated like tool output, arguments scrubbed. Too many tool
        calls is refused outright (flagged, then denied by the guard)."""
        data["text"] = self.tools.truncate(data.get("text") or "")
        calls = data.get("tool_calls") or []
        if len(calls) > self.max_tool_calls:
            data["too_many_tool_calls"] = len(calls)
            calls = calls[: self.max_tool_calls]
        ids = [c.get("id") for c in calls]
        if len(set(ids)) != len(ids):
            data["duplicate_call_ids"] = True
        data["tool_calls"] = [
            # 📝 VALUE patterns only: a parameter legitimately named
            #    `page_token` must not be blanked. Credentials belong in
            #    the tool's closure, never in model-proposed arguments.
            {**c, "arguments": scrub(c.get("arguments") or {}, by_key=False)}
            for c in calls
        ]
        return data

    def call_model_sync(self, i: Any, ctx: Dict[str, Any], e: Any) -> Any:
        messages, schemas, extra = self._model_request(i, ctx, e)
        resp = self.model(messages, schemas)
        if inspect.isawaitable(resp):
            close = getattr(resp, "close", None)
            if callable(close):
                close()
            raise TypeError(
                "the model returned an awaitable under SyncInterpreter; "
                "use a sync ModelCall (FakeModel(is_async=False))"
            )
        raw = self._response_data(resp, extra)
        self._trace(i, "model_call", response=raw, messages=messages)
        data = self._bounded(raw)
        return data

    async def call_model_async(
        self, i: Any, ctx: Dict[str, Any], e: Any
    ) -> Any:
        messages, schemas, extra = self._model_request(i, ctx, e)
        resp = self.model(messages, schemas)
        if inspect.isawaitable(resp):
            resp = await resp
        raw = self._response_data(resp, extra)
        self._trace(i, "model_call", response=raw, messages=messages)
        data = self._bounded(raw)
        return data

    def _authorise_all(
        self, i: Any, ctx: Dict[str, Any], e: Any
    ) -> List[Tuple[ToolCall, Dict[str, Any]]]:
        # 🛡️ X0.13: authorise EVERY pending call before running ANY, so a
        #    batch with one forbidden call executes nothing.
        allowed = state_tools(i, e)
        approved = list(ctx.get("approved_call_ids") or [])
        plan = []
        for call in calls_from(ctx.get("pending_tool_calls") or []):
            try:
                plan.append(
                    (call, self.tools.authorise(call, allowed, approved))
                )
            except ToolDeniedError as exc:
                self._trace(
                    i, "tool_denied", tool=call.name, reason=exc.reason
                )
                raise
        return plan

    def _result(self, i: Any, call: ToolCall, value: Any) -> Dict[str, Any]:
        safe = scrub(value)
        self._trace(
            i,
            "tool_call",
            tool=call.name,
            arguments=call.arguments,
            output=safe,
        )
        return {
            "tool_call_id": call.id,
            "name": call.name,
            "content": self.tools.truncate(safe),
        }

    def run_tool_sync(self, i: Any, ctx: Dict[str, Any], e: Any) -> Any:
        out = []
        for call, args in self._authorise_all(i, ctx, e):
            out.append(self._result(i, call, self.tools.call_sync(call, args)))
        return out

    async def run_tool_async(self, i: Any, ctx: Dict[str, Any], e: Any) -> Any:
        out = []
        for call, args in self._authorise_all(i, ctx, e):
            value = await self.tools.call_async(call, args)
            out.append(self._result(i, call, value))
        return out

    # -- guards -----------------------------------------------------------
    @staticmethod
    def _data(e: Any) -> Dict[str, Any]:
        data = getattr(e, "data", None)
        return data if isinstance(data, dict) else {}

    def g_tool_allowed(self, ctx: Dict[str, Any], e: Any) -> bool:
        d = self._data(e)
        if d.get("too_many_tool_calls") or d.get("duplicate_call_ids"):
            return False
        allowed = d.get("allowed_tools") or []
        for c in calls_from(d.get("tool_calls") or []):
            if c.name not in self.tools or c.name not in allowed:
                return False
            # 🔥 #287 battle: arguments were validated only in `run_tool`,
            #    AFTER the human gate -- a reviewer was asked to approve
            #    `refund_order(amount_cents="all")`, a call that could
            #    never run. Schema-invalid arguments are denied here,
            #    before anything is shown to a human or executed
            #    (`run_tool` re-validates: defence in depth).
            tool = self.tools.get(c.name)
            if tool is not None:
                try:
                    tool.validate(c.arguments)
                except ToolDeniedError:
                    return False
        return True

    def g_needs_human(self, ctx: Dict[str, Any], e: Any) -> bool:
        for c in calls_from(self._data(e).get("tool_calls") or []):
            t = self.tools.get(c.name)
            if t is not None and t.side_effect:
                return True
        return False

    def g_has_tool_calls(self, ctx: Dict[str, Any], e: Any) -> bool:
        return bool(self._data(e).get("tool_calls"))

    def g_can_retry_output(self, ctx: Dict[str, Any], e: Any) -> bool:
        return int(ctx.get("output_retries", 0)) < self.max_output_retries

    @staticmethod
    def g_is_tool_denied(ctx: Dict[str, Any], e: Any) -> bool:
        return isinstance(getattr(e, "error", None), ToolDeniedError)

    def g_output_valid(self, ctx: Dict[str, Any], e: Any) -> bool:
        model = self._output_model_for(e)
        ok, _ = _validate_output(
            model, str(self._data(e).get("text", "")), self.output_parser
        )
        return ok

    @staticmethod
    def g_has_task(ctx: Dict[str, Any], e: Any) -> bool:
        return _task_of(ctx) is not None

    # -- actions ----------------------------------------------------------
    def a_append_user(
        self, i: Any, ctx: Dict[str, Any], e: Any, a: Any
    ) -> None:
        payload = getattr(e, "payload", None) or {}
        prompt = payload.get("prompt")
        if prompt is None:
            prompt = _task_of(ctx)
        if prompt is not None:
            self._append(ctx, {"role": "user", "content": str(prompt)})

    def a_record_response(
        self, i: Any, ctx: Dict[str, Any], e: Any, a: Any
    ) -> None:
        d = self._data(e)
        usage = d.get("usage") or {}
        ctx["turns"] = int(ctx.get("turns", 0)) + 1
        ctx["tokens_in"] = int(ctx.get("tokens_in", 0)) + _spent_tokens(
            usage.get("input_tokens", 0)
        )
        ctx["tokens_out"] = int(ctx.get("tokens_out", 0)) + _spent_tokens(
            usage.get("output_tokens", 0)
        )
        ctx["cost_usd"] = float(ctx.get("cost_usd", 0.0)) + _spent_usd(
            usage.get("cost_usd", 0.0)
        )
        ctx["attempt"] = 0  # a successful call resets the retry counter
        ctx["approved_call_ids"] = []  # approvals never outlive a batch
        calls = list(d.get("tool_calls") or [])
        ctx["pending_tool_calls"] = calls
        msg: Message = {"role": "assistant", "content": d.get("text", "")}
        if calls:
            msg["tool_calls"] = calls
        self._append(ctx, msg)

    def a_append_tool_results(
        self, i: Any, ctx: Dict[str, Any], e: Any, a: Any
    ) -> None:
        results = getattr(e, "data", None) or []
        self._append(ctx, *({"role": "tool", **r} for r in results))
        ctx["pending_tool_calls"] = []
        ctx["approved_call_ids"] = []

    @staticmethod
    def g_approval_matches(ctx: Dict[str, Any], e: Any) -> bool:
        """``HUMAN_APPROVED`` must name EXACTLY the pending call ids, so a
        late or replayed approval for an earlier batch cannot approve a
        later one (it is `Receipt.denied` instead)."""
        ids = (getattr(e, "payload", None) or {}).get("call_ids")
        pending = [c.get("id") for c in ctx.get("pending_tool_calls") or []]
        return isinstance(ids, (list, tuple)) and sorted(
            map(str, ids)
        ) == sorted(map(str, pending))

    def a_approve(self, i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        # 📝 Approval is per CALL ID of what is pending right now (checked
        #    by `approvalMatches`) -- it cannot pre-approve a call the
        #    model has not proposed yet.
        ctx["approved_call_ids"] = [
            c["id"] for c in ctx.get("pending_tool_calls") or []
        ]
        ctx["human_approved"] = True

    def a_reject(self, i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        reason = (getattr(e, "payload", None) or {}).get("reason", "")
        self._append(
            ctx,
            *(
                {
                    "role": "tool",
                    "tool_call_id": c["id"],
                    "name": c["name"],
                    "content": f"rejected by a human reviewer. {reason}".strip(),
                }
                for c in ctx.get("pending_tool_calls") or []
            ),
        )
        ctx["pending_tool_calls"] = []
        ctx["approved_call_ids"] = []
        ctx["human_approved"] = False

    def a_store_result(
        self, i: Any, ctx: Dict[str, Any], e: Any, a: Any
    ) -> None:
        model = self._output_model_for(e)
        _, value = _validate_output(
            model, str(self._data(e).get("text", "")), self.output_parser
        )
        ctx["result"] = value

    def a_retry_output(
        self, i: Any, ctx: Dict[str, Any], e: Any, a: Any
    ) -> None:
        # 🔁 RETRY_OUTPUT: re-prompt with the validation errors (field
        #    names and messages only). The retry costs a model turn, so it
        #    counts against every budget like any other turn.
        model = self._output_model_for(e)
        _, detail = _validate_output(
            model, str(self._data(e).get("text", "")), self.output_parser
        )
        ctx["output_retries"] = int(ctx.get("output_retries", 0)) + 1
        schema = (
            json.dumps(model.model_json_schema())  # type: ignore[attr-defined]
            if model is not None
            else "{}"
        )
        self._append(
            ctx,
            {
                "role": "user",
                "content": (
                    f"RETRY_OUTPUT: your answer did not validate ({detail}). "
                    f"Reply with only JSON matching this schema: {schema}"
                ),
            },
        )

    @staticmethod
    def _fail(ctx: Dict[str, Any], kind: str, message: str) -> None:
        ctx["error"] = {"kind": kind, "message": message}

    def a_fail(self, kind: str, message: str) -> Callable[..., None]:
        def _action(i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
            self._fail(ctx, kind, message)

        return _action

    def a_deny(self, i: Any, ctx: Dict[str, Any], e: Any, a: Any) -> None:
        err = getattr(e, "error", None)
        if isinstance(err, ToolDeniedError):
            self._fail(ctx, "tool_denied", str(err))
            return
        d = self._data(e)
        if d.get("too_many_tool_calls"):
            self._fail(
                ctx,
                "tool_denied",
                f"{d['too_many_tool_calls']} tool calls in one turn "
                f"(max_tool_calls={self.max_tool_calls})",
            )
            ctx["pending_tool_calls"] = []
            return
        if d.get("duplicate_call_ids"):
            self._fail(ctx, "tool_denied", "duplicate tool call ids")
            ctx["pending_tool_calls"] = []
            return
        allowed = d.get("allowed_tools") or []
        bad = [
            c.name
            for c in calls_from(d.get("tool_calls") or [])
            if c.name not in self.tools or c.name not in allowed
        ]
        if bad:
            self._fail(ctx, "tool_denied", f"tool(s) {bad} not allowed here")
            ctx["pending_tool_calls"] = []
            return
        for c in calls_from(d.get("tool_calls") or []):
            tool = self.tools.get(c.name)
            if tool is None:
                continue
            try:
                tool.validate(c.arguments)
            except ToolDeniedError as exc:
                self._fail(ctx, "tool_denied", str(exc))
                break
        ctx["pending_tool_calls"] = []

    def a_record_failure(
        self, i: Any, ctx: Dict[str, Any], e: Any, a: Any
    ) -> None:
        err = getattr(e, "error", None)
        # 📝 Class name only -- an exception message may quote the prompt.
        ctx["last_failure"] = type(err).__name__ if err else "unknown"
        ctx["approved_call_ids"] = []

    def a_notify_parent(
        self, i: Any, ctx: Dict[str, Any], e: Any, a: Any
    ) -> None:
        parent = getattr(i, "parent", None)
        if parent is None:
            return
        failed = ctx.get("error") is not None
        payload = {
            "agent_id": i.id,
            "usage": _usage_totals(ctx),
            "result": ctx.get("result"),
            "error": ctx.get("error"),
        }
        parent.send("AGENT_FAILED" if failed else "AGENT_DONE", **payload)


def agent_logic(
    model: Any,
    tools: Optional[ToolRegistry] = None,
    *,
    budgets: Union[Budget, Mapping[str, Any], None] = None,
    output_model: Any = None,
    max_messages: int = 200,
    summarise: Optional[Callable[[List[Message]], List[Message]]] = None,
    max_output_retries: int = 2,
    system_prompt: Optional[str] = None,
    model_timeout_s: float = 60.0,
    human_timeout_s: float = 24 * 3600.0,
    retry: Optional[RetryPolicy] = None,
    sync: Optional[bool] = None,
    tracer: Any = None,
    max_tool_calls: int = 8,
    output_parser: Optional[Callable[[str], Any]] = None,
) -> MachineLogic:
    """The `MachineLogic` for `TOOL_LOOP` (and charts that reuse its names).

    Args:
        model: A `ModelCall` -- ``async`` for `Interpreter`, sync for
            `SyncInterpreter` (``FakeModel(is_async=False)``).
        tools: A `tool_registry(...)`; ``None`` → no tools.
        budgets: `Budget` or ``{"max_tokens", "max_usd", "max_turns"}``.
        output_model: pydantic model (or ``"module:Model"``) the final
            text must validate against; else a state's
            ``meta.output_model``; else free text.
        max_messages: Bound on ``context["messages"]`` so snapshots stay
            under ``max_snapshot_bytes``; the oldest turns after the task
            are dropped unless *summarise* is given.
        summarise: ``(messages) -> shorter messages`` hook.
        max_output_retries: Output-validation re-prompts before ``error``.
        system_prompt: Prepended to every model request (never stored in
            context, so never in a snapshot).
        model_timeout_s / human_timeout_s: The ``modelTimeout`` /
            ``humanTimeout`` delays. ``toolTimeout`` is the sum of the
            pending calls' ``timeout_s`` plus one second (each tool also
            enforces its own).
        retry: `RetryPolicy` for ``timed_out`` (default 3 attempts, no
            jitter, 1 s base).
        sync: Force the sync (``True``) or async (``False``) service
            flavour; default follows the model.
        tracer: An `AgentTracePlugin` (or anything with ``record(interp,
            kind, **fields)``) that receives model/tool records. Passing
            it here -- not only via ``interp.use()`` -- is what makes
            spawned sub-agents land in the same trace.
        max_tool_calls: More tool calls than this in ONE model turn is
            denied (``error``) -- bounds work and context per turn.
        output_parser: ``(text) -> JSON value`` applied before validating
            structured output (default: strict JSON, code fence allowed);
            `structured_output()` installs instructor's when available.

    Raises:
        AgentConfigError: invalid budgets, output model or bounds.
    """
    if max_messages < 2:
        raise AgentConfigError("max_messages must be >= 2")
    registry = tools if tools is not None else ToolRegistry()
    budget = Budget.coerce(budgets)
    st = _AgentLogic(
        model,
        registry,
        budget,
        output_model,
        max_messages,
        summarise,
        max_output_retries,
        system_prompt,
        tracer,
        max_tool_calls,
        output_parser,
    )
    use_sync = (not _is_async_model(model)) if sync is None else sync
    policy = retry or RetryPolicy(max_attempts=3, base_ms=1000, jitter="none")

    def tool_ms(ctx: Dict[str, Any], e: Any) -> float:
        # ⏱️ The whole batch runs sequentially inside one invoke, so the
        #    state-level bound is the SUM of the pending calls' timeouts.
        total = 0.0
        for c in ctx.get("pending_tool_calls") or []:
            t = registry.get(str(c.get("name")))
            total += t.timeout_s if t is not None else 0.0
        return 1000.0 * (total + 1.0)

    logic: MachineLogic[Any] = MachineLogic(
        actions={
            "appendUserMessage": st.a_append_user,
            "recordModelResponse": st.a_record_response,
            "appendToolResults": st.a_append_tool_results,
            "approveHuman": st.a_approve,
            "rejectPending": st.a_reject,
            "storeResult": st.a_store_result,
            "retryOutput": st.a_retry_output,
            "denyTool": st.a_deny,
            "recordFailure": st.a_record_failure,
            "recordModelTimeout": st.a_fail("timeout", "model call timed out"),
            "recordToolTimeout": st.a_fail("timeout", "tool call timed out"),
            "failTurnLimit": st.a_fail("budget", "turn limit reached"),
            "failTokenBudget": st.a_fail("budget", "token budget exhausted"),
            "failCostBudget": st.a_fail("budget", "cost budget exhausted"),
            "failOutput": st.a_fail(
                "output", "model output failed validation"
            ),
            "failRetries": st.a_fail("retries", "retries exhausted"),
            "escalateHuman": st.a_fail(
                "human_timeout", "no human decision in time"
            ),
            "notifyParent": st.a_notify_parent,
        },
        guards={
            "toolAllowed": st.g_tool_allowed,
            "needsHuman": st.g_needs_human,
            "hasToolCalls": st.g_has_tool_calls,
            "canRetryOutput": st.g_can_retry_output,
            "isToolDenied": st.g_is_tool_denied,
            "outputValid": st.g_output_valid,
            "hasTask": st.g_has_task,
            "approvalMatches": st.g_approval_matches,
        },
        services={
            "callModel": (
                st.call_model_sync if use_sync else st.call_model_async
            ),
            "runTool": st.run_tool_sync if use_sync else st.run_tool_async,
        },
        delays={
            "modelTimeout": model_timeout_s * 1000.0,
            "toolTimeout": tool_ms,
            "humanTimeout": human_timeout_s * 1000.0,
        },
    )
    logic = logic.merge(
        budget_guards(budget.max_tokens, budget.max_usd, budget.max_turns),
        policy.logic(),
    )
    # ✅ Remember the pieces for `run_agent` / `spawn_agent` / validation.
    setattr(logic, "agent_tools", registry)
    setattr(logic, "agent_budget", budget)
    setattr(logic, "agent_state", st)
    setattr(logic, "agent_tracer", tracer)
    return logic
