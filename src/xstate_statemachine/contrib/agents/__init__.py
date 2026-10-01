# src/xstate_statemachine/contrib/agents/__init__.py
# -----------------------------------------------------------------------------
# 🤖 [agents] -- LLM agents as statecharts: the model proposes, the machine
#    decides (#287 E1, #290 E4)
# -----------------------------------------------------------------------------
# 🏛️ An agent is the `TOOL_LOOP` chart plus `agent_logic()`. Budgets,
#    per-state tool allow-lists, timeouts and human approval are CHART
#    structure and guards -- inspectable with `xsm inspect`, persisted with
#    any store -- and `run_tool` re-enforces the safety-relevant ones
#    itself (X0.13, docs/_guide/security.md).
#
# 📝 The extra is `[agents]` = `pydantic>=2.5` (tool schemas, structured
#    output). Provider SDKs (`openai`, `anthropic`) are SOFT imports inside
#    `providers.*` factories and never pinned.
# -----------------------------------------------------------------------------
"""LLM agents as statecharts.

Install with ``pip install "xstate-statemachine[agents]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("agents", "pydantic")

from .core import (  # noqa: E402
    AGENT_REDACT_KEYS,
    CHARTS_DIR,
    TOOL_LOOP,
    Budget,
    agent_logic,
    budget_guards,
    load_chart,
    scrub,
    state_tools,
    validate_agent_chart,
)
from .messages import (  # noqa: E402
    AgentConfigError,
    AgentError,
    FakeModel,
    ModelCall,
    ModelResponse,
    ToolCall,
    ToolDeniedError,
    ToolTimeoutError,
    Usage,
)
from .multi import BudgetPlugin, handoff_guard, spawn_agent  # noqa: E402
from .runner import (  # noqa: E402
    WAITING_STATES,
    AgentResult,
    pending_approval,
    run_agent,
    run_agent_sync,
)
from .tools import (  # noqa: E402
    ALL_TOOLS,
    DEFAULT_MAX_OUTPUT_CHARS,
    DEFAULT_TOOL_TIMEOUT_S,
    Tool,
    ToolRegistry,
    tool,
    tool_registry,
)
from .structured import structured_output, validate_structured  # noqa: E402
from .trace import AgentTracePlugin  # noqa: E402

__all__ = [
    "AGENT_REDACT_KEYS",
    "ALL_TOOLS",
    "AgentConfigError",
    "AgentError",
    "AgentResult",
    "AgentTracePlugin",
    "Budget",
    "BudgetPlugin",
    "CHARTS_DIR",
    "DEFAULT_MAX_OUTPUT_CHARS",
    "DEFAULT_TOOL_TIMEOUT_S",
    "FakeModel",
    "ModelCall",
    "ModelResponse",
    "TOOL_LOOP",
    "Tool",
    "ToolCall",
    "ToolDeniedError",
    "ToolRegistry",
    "ToolTimeoutError",
    "Usage",
    "WAITING_STATES",
    "agent_logic",
    "budget_guards",
    "handoff_guard",
    "load_chart",
    "pending_approval",
    "run_agent",
    "run_agent_sync",
    "scrub",
    "spawn_agent",
    "state_tools",
    "structured_output",
    "tool",
    "tool_registry",
    "validate_agent_chart",
    "validate_structured",
]
