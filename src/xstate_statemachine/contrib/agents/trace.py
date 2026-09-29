# src/xstate_statemachine/contrib/agents/trace.py
# -----------------------------------------------------------------------------
# 🧵 AgentTracePlugin -- JSONL trace with gen_ai.* field names (#287, #290)
# -----------------------------------------------------------------------------
# 🏛️ One trace per actor TREE: every record carries `trace_id` (the root
#    interpreter id), `agent_id` and `parent_id`, so a supervisor and the
#    sub-agents it spawned land in one file and `totals()` rolls cost up
#    per agent and overall. Sub-agents are reached because `spawn_agent`
#    hands the SAME tracer to each child's `agent_logic(tracer=...)`.
#
# 🔒 X0.13 hygiene: `record_content=False` (the default) writes NO prompt,
#    completion, tool arguments or tool output -- only names, states,
#    token counts and cost. With `record_content=True` the content is
#    passed through `redact()` first.
#
# 📝 Field names follow the OpenTelemetry GenAI semantic conventions where
#    one exists (`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
#    `gen_ai.request.model`, `gen_ai.tool.name`, `gen_ai.operation.name`).
#    Real OTel SPANS belong to the `[observability]` extra (G3, #273); this
#    plugin leaves the seam: `on_span=callable(record)` is called for every
#    record so an exporter can open/close spans without re-parsing JSONL.
# -----------------------------------------------------------------------------
"""JSONL agent traces with ``gen_ai.*`` fields and cost rollup."""

from __future__ import annotations

import json
import threading
import time
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Union,
)

from ...plugins import PluginBase, redact
from .core import AGENT_REDACT_KEYS

__all__ = ["AgentTracePlugin"]

Sink = Union[str, "IO[str]", Callable[[Dict[str, Any]], None], None]


def _root(interp: Any) -> Any:
    node = interp
    while getattr(node, "parent", None) is not None:
        node = node.parent
    return node


class AgentTracePlugin(PluginBase[Any]):
    """Write one JSON object per agent step to *sink*.

    Args:
        sink: A file path (appended to), a text stream with ``write``, a
            callable receiving each record, or ``None`` (keep in memory
            only -- see `records`).
        record_content: Include prompts / completions / tool I/O
            (redacted). Default ``False``.
        on_span: Optional ``callable(record)`` -- the documented seam for
            an OpenTelemetry exporter (G3). Exceptions are contained.
        clock: ``() -> float`` epoch seconds for the ``ts`` field.

    Attach it with ``interp.use(trace)`` for lifecycle/state records AND
    pass it as ``agent_logic(..., tracer=trace)`` (or
    ``spawn_agent(..., tracer=trace)``) for model/tool records.
    """

    def __init__(
        self,
        sink: Sink = None,
        *,
        record_content: bool = False,
        on_span: Optional[Callable[[Dict[str, Any]], None]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self.sink = sink
        self.record_content = record_content
        self.on_span = on_span
        self.clock = clock or time.time
        self.records: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._attached: Set[int] = set()

    # -- the one write path ----------------------------------------------
    def record(self, interp: Any, kind: str, **fields: Any) -> Dict[str, Any]:
        """Append one record. Called by the agent logic and the hooks."""
        root = _root(interp)
        parent = getattr(interp, "parent", None)
        rec: Dict[str, Any] = {
            "ts": self.clock(),
            "trace_id": getattr(root, "id", None),
            "agent_id": getattr(interp, "id", None),
            "parent_id": getattr(parent, "id", None),
            "kind": kind,
            "gen_ai.operation.name": _OPERATION.get(kind, kind),
            "state": sorted(getattr(interp, "current_state_ids", ()) or ()),
        }
        rec.update(self._fields(kind, fields))
        with self._lock:
            self.records.append(rec)
            self._write(rec)
        if self.on_span is not None:
            try:
                self.on_span(rec)
            except Exception:  # noqa: BLE001 -- an exporter must not
                pass  # break the agent; the JSONL record is already out
        return rec

    def _fields(self, kind: str, f: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        resp = f.get("response")
        if isinstance(resp, dict):
            usage = resp.get("usage") or {}
            out["gen_ai.request.model"] = resp.get("model") or None
            out["gen_ai.usage.input_tokens"] = int(
                usage.get("input_tokens", 0)
            )
            out["gen_ai.usage.output_tokens"] = int(
                usage.get("output_tokens", 0)
            )
            out["cost_usd"] = float(usage.get("cost_usd", 0.0))
            out["gen_ai.response.tool_calls"] = [
                c.get("name") for c in resp.get("tool_calls") or []
            ]
            if self.record_content:
                out["gen_ai.completion"] = redact(
                    resp.get("text", ""), AGENT_REDACT_KEYS
                )
                out["gen_ai.prompt"] = redact(
                    f.get("messages") or [], AGENT_REDACT_KEYS
                )
        if "tool" in f:
            out["gen_ai.tool.name"] = f["tool"]
        if "reason" in f:
            out["reason"] = f["reason"]
        if "usage" in f:
            out["usage"] = f["usage"]
        if self.record_content:
            for key in ("arguments", "output"):
                if key in f:
                    out[f"gen_ai.tool.{key}"] = redact(
                        f[key], AGENT_REDACT_KEYS
                    )
        return out

    def _write(self, rec: Dict[str, Any]) -> None:
        sink = self.sink
        if sink is None:
            return
        if callable(sink) and not hasattr(sink, "write"):
            sink(rec)
            return
        line = json.dumps(rec, default=str, ensure_ascii=False) + "\n"
        if isinstance(sink, str):
            with open(sink, "a", encoding="utf-8") as fh:
                fh.write(line)
        else:
            sink.write(line)  # type: ignore[union-attr]

    # -- rollup -----------------------------------------------------------
    def totals(self) -> Dict[str, Any]:
        """``{"agents": {agent_id: usage}, "total": usage}`` from the
        ``model_call`` records -- the per-tree cost rollup."""
        agents: Dict[str, Dict[str, Any]] = {}
        for r in list(self.records):
            if r["kind"] != "model_call":
                continue
            a = agents.setdefault(
                str(r["agent_id"]),
                {
                    "turns": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                },
            )
            a["turns"] += 1
            a["input_tokens"] += r.get("gen_ai.usage.input_tokens", 0)
            a["output_tokens"] += r.get("gen_ai.usage.output_tokens", 0)
            a["cost_usd"] += r.get("cost_usd", 0.0)
        total = {
            k: sum(a[k] for a in agents.values())
            for k in ("turns", "input_tokens", "output_tokens", "cost_usd")
        }
        return {"agents": agents, "total": total}

    # -- plugin hooks -----------------------------------------------------
    def on_interpreter_start(self, interpreter: Any) -> None:
        self.record(interpreter, "agent_start")

    def on_transition(
        self,
        interpreter: Any,
        from_states: Any,
        to_states: Any,
        transition: Any,
    ) -> None:
        self.record(interpreter, "transition")

    def on_done(self, interpreter: Any, output: Any) -> None:
        self.record(interpreter, "agent_end")

    def on_error(self, interpreter: Any, error: BaseException) -> None:
        self.record(interpreter, "agent_error", reason=type(error).__name__)


_OPERATION = {
    "model_call": "chat",
    "tool_call": "execute_tool",
    "tool_denied": "execute_tool",
}
