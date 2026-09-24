# src/xstate_statemachine/cli/strategies/plugin_skeleton.py
# -----------------------------------------------------------------------------
# 🔌 `plugin` template -- a PluginBase subclass shaped by the machine
# -----------------------------------------------------------------------------
# Only the hooks this chart can actually fire are emitted, each with a
# structured-log body and a `TODO`, so the reader is not handed 23 empty
# methods. The mapping is deliberate (documented inline): a chart with no
# `invoke` gets no `on_service_*`, one with no `after` gets no timer note,
# and the sticky-signal hooks (`on_chain_budget_exceeded`,
# `on_invocation_stranded`) are always included because any chart with a
# self-send or an invoke can reach them.
# -----------------------------------------------------------------------------
"""The `plugin` code-generation strategy."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Set

from ..extractor import extract_logic_names
from ..utils import camel_to_snake
from ._shared import (
    generate_module_header,
    generate_section_header,
    pascal_case_name,
    safe_identifier,
)
from .base import BaseStrategy, GenerationContext


def _walk(config: Dict[str, Any]):
    for name, st in (config.get("states") or {}).items():
        yield name, st
        yield from _walk(st)


def _features(config: Dict[str, Any]) -> Set[str]:
    """Which engine features the chart uses (drives hook selection)."""
    feats: Set[str] = set()
    for _, st in _walk(config):
        if st.get("invoke"):
            feats.add("invoke")
        if st.get("after"):
            feats.add("after")
        if st.get("always"):
            feats.add("always")
        if st.get("type") == "final":
            feats.add("final")
        for key in ("entry", "exit"):
            for a in st.get(key) or []:
                t = a.get("type") if isinstance(a, dict) else str(a)
                if t in (
                    "raise",
                    "xstate.raise",
                    "sendTo",
                    "xstate.sendTo",
                    "spawnChild",
                    "xstate.spawnChild",
                ):
                    feats.add("self_send")
        for _ev, tr in (st.get("on") or {}).items():
            for t in tr if isinstance(tr, list) else [tr]:
                if isinstance(t, dict) and (t.get("guard") or t.get("cond")):
                    feats.add("guards")
    if config.get("onUnhandled") in ("defer", "error"):
        feats.add("unhandled")
    if config.get("actionErrorPolicy") in ("rollback", "fail"):
        feats.add("policy")
    return feats


HOOKS = [
    # (name, signature, always?, feature, one-line reason, log key)
    (
        "on_interpreter_start",
        "(self, interpreter)",
        True,
        None,
        "lifecycle: boot or resume",
        "start",
    ),
    (
        "on_interpreter_stop",
        "(self, interpreter)",
        True,
        None,
        "lifecycle",
        "stop",
    ),
    (
        "on_transition",
        "(self, interpreter, from_states, to_states, transition)",
        True,
        None,
        "every settled transition",
        "transition",
    ),
    (
        "on_action_error",
        "(self, interpreter, action, error)",
        True,
        None,
        "a user action raised (contained)",
        "action_error",
    ),
    (
        "on_guard_error",
        "(self, interpreter, guard_name, event, error)",
        False,
        "guards",
        "a guard raised instead of returning",
        "guard_error",
    ),
    (
        "on_service_start",
        "(self, interpreter, invocation)",
        False,
        "invoke",
        "an invoke began",
        "service_start",
    ),
    (
        "on_service_done",
        "(self, interpreter, invocation, result)",
        False,
        "invoke",
        "an invoke completed",
        "service_done",
    ),
    (
        "on_service_error",
        "(self, interpreter, invocation, error)",
        False,
        "invoke",
        "an invoke failed",
        "service_error",
    ),
    (
        "on_invocation_stranded",
        "(self, interpreter, state_id, invoke_id, error)",
        False,
        "invoke",
        "a cut left an invoke that will never complete",
        "stranded",
    ),
    (
        "on_unhandled_event",
        "(self, interpreter, event, active_state_ids, disposition)",
        False,
        "unhandled",
        "an event selected no transition",
        "unhandled",
    ),
    (
        "on_transition_failed",
        "(self, interpreter, transition, failed_actions)",
        False,
        "policy",
        "actionErrorPolicy rolled back / stopped",
        "transition_failed",
    ),
    (
        "on_event_dropped",
        "(self, interpreter, event, reason)",
        True,
        None,
        "an accepted event was discarded (see `reason`)",
        "dropped",
    ),
    (
        "on_chain_budget_exceeded",
        "(self, interpreter, error, event)",
        True,
        None,
        "maxIterations cut a self-fed chain -- sticky, page on this",
        "chain_trip",
    ),
    (
        "on_invalid_event",
        "(self, interpreter, error, raw_event)",
        True,
        None,
        "send()/restore refused an event",
        "invalid_event",
    ),
    (
        "on_error",
        "(self, interpreter, error)",
        True,
        None,
        "terminal error status",
        "error",
    ),
    (
        "on_done",
        "(self, interpreter, output)",
        False,
        "final",
        "the machine reached its final state",
        "done",
    ),
    (
        "on_plugin_error",
        "(self, interpreter, plugin, hook, error)",
        True,
        None,
        "another plugin's hook raised",
        "plugin_error",
    ),
]


class PluginSkeletonStrategy(BaseStrategy):
    @property
    def name(self) -> str:
        return "plugin"

    def generate_runner(self, ctx: GenerationContext) -> str:
        return ""

    def generate_logic(self, ctx: GenerationContext) -> str:
        config = ctx.configs[0]
        feats = _features(config)
        cls = (
            pascal_case_name(camel_to_snake(safe_identifier(ctx.machine_name)))
            + "Observer"
        )
        selected = [h for h in HOOKS if h[2] or (h[3] in feats)]
        skipped = [h for h in HOOKS if h not in selected]

        p: List[str] = [
            generate_module_header(
                f"Observer plugin for the {ctx.machine_name}"
            ),
            "# Generated by `xsm generate-template --template plugin`. Only the hooks",
            "# this chart can fire are included; each logs a structured record.",
            "# Attach with `interpreter.use(" + cls + "())` or",
            "# `from_snapshot(..., plugins=["
            + cls
            + "()])` so restore-time refusals",
            "# are seen too.",
            "",
            "from __future__ import annotations",
            "",
            "import json",
            "import logging",
            "from typing import Any",
            "",
            "from xstate_statemachine import PluginBase",
            "",
            f"log = logging.getLogger({json.dumps(ctx.machine_name)})",
            "",
            "",
            "def _record(kind: str, interpreter: Any, **fields: Any) -> None:",
            '    """One JSON line per observation, ready for a log shipper."""',
            "    payload = {'machine': interpreter.id, 'kind': kind, **fields}",
            "    log.info(json.dumps(payload, default=str))",
            "",
            "",
            generate_section_header("Plugin"),
            f"class {cls}(PluginBase):",
            f'    """Observes the {ctx.machine_name}; see the hook docstrings."""',
            "",
        ]
        for name, sig, _always, _feat, reason, key in selected:
            args = [a.strip() for a in sig.strip("()").split(",")][1:]
            fields = ", ".join(f"{a}={a}" for a in args[1:])
            p += [
                f"    def {name}{sig} -> None:",
                f'        """{reason}."""',
                f"        _record({json.dumps(key)}, interpreter{', ' + fields if fields else ''})",
                "        # TODO: your metrics / alerting here",
                "",
            ]
        if skipped:
            p += [
                "",
                "# Hooks NOT emitted because the chart does not use the feature:",
                *[f"#   - {h[0]} ({h[4]})" for h in skipped],
                "",
            ]
        return "\n".join(p)
