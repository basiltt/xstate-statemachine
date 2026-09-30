# src/xstate_statemachine/contrib/cloudevents/__init__.py
# -----------------------------------------------------------------------------
# ☁️ [cloudevents] -- SDK interop for the core `Envelope` (#293)
# -----------------------------------------------------------------------------
# 🏛️ `eda.Envelope` already IS a CloudEvent (1.0 attributes + extensions)
#    and needs nothing to (de)serialise structured-mode JSON. This extra
#    only bridges to the official `cloudevents` SDK objects and its HTTP
#    binary / structured helpers, for services that already speak them.
#
# 📝 SDK layout: 1.x exposes `cloudevents.http`; 2.x moved that legacy API
#    to `cloudevents.v1.http`. Both are supported (`cloudevents>=1.10`).
#
# 🔐 X0.8: headers coming IN (`from_http`) pass through
#    `Envelope.safe_extensions`, so an `Authorization` / `Cookie` header
#    can never become an envelope extension. X0.4: the body is size-capped
#    before the SDK parses it.
# -----------------------------------------------------------------------------
"""CloudEvents SDK interop for `xstate_statemachine.eda.Envelope`.

Install with ``pip install "xstate-statemachine[cloudevents]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("cloudevents", "cloudevents")

from .convert import (  # noqa: E402
    from_cloudevent,
    from_http,
    to_binary,
    to_cloudevent,
    to_structured,
)

__all__ = [
    "from_cloudevent",
    "from_http",
    "to_binary",
    "to_cloudevent",
    "to_structured",
]
