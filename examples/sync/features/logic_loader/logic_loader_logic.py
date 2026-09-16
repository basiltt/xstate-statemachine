# examples/sync/features/logic_loader/logic_loader_logic.py
# -----------------------------------------------------------------------------
# 🧩 Sibling logic module auto-discovered by name (0.8.0)
# -----------------------------------------------------------------------------
"""Plain functions, matched to the machine config purely by name."""

from typing import Any, Dict


def guard_is_valid(context: Dict[str, Any], event: Any) -> bool:
    """✅ Passes when the submitted amount is positive."""
    return event.payload.get("amount", 0) > 0


def record_from_module(interpreter, context, event, action_def) -> None:
    """📝 Records that the MODULE implementation of this action ran."""
    context["source"] = "module"
