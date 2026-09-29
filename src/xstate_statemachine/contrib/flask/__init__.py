# src/xstate_statemachine/contrib/flask/__init__.py
# -----------------------------------------------------------------------------
# 🧪 [flask] -- XState extension, statechart blueprint, session wizards, CLI
# -----------------------------------------------------------------------------
# 🏛️ Flask has a very large install base and no state-machine extension.
#    This one follows the canonical `init_app` pattern and reuses the
#    persistence layer end to end:
#
#      * `XState.init_app(app, store, lock=, plugins=, inbox=, principal=)`
#        -- app state in ``app.extensions["xstate"]`` (application-factory
#        safe); `act(name, key)` is `persisted()` with the app's policies;
#        ``g.xsm`` binds it per request.
#      * `create_statechart_blueprint(...)` -- the C2 route table (state,
#        send, per-event, events, history, SSE stream, Mermaid diagram).
#      * `receipt_response()` -- status from the CORE `receipts` table
#        (#305), not from the Starlette extra.
#      * `SessionStore` -- tiny wizard state in the signed cookie, hard
#        3 KiB cap, `SessionStoreTooLargeError`.
#      * ``flask xsm inspect|diagram|docs|simulate <name>``.
#
#    Quart (Flask's async twin) is served by `xstate_statemachine.contrib.
#    quart`, a soft-import shim over the same core -- no separate extra.
#
# 🔐 Security posture (docs/_guide/security.md): X0.1 authorize required,
#    state-only bodies; X0.2 principal-scoped Idempotency-Key; X0.7 JSON
#    only, 413/415, problem+json without exception text, no state change
#    from a safe method; CSRF: JSON endpoints work with Flask-WTF's
#    `CSRFProtect` via ``csrf.exempt(blueprint)`` or the ``X-CSRFToken``
#    header (see the integration page).
# -----------------------------------------------------------------------------
"""Flask integration.

Install with ``pip install "xstate-statemachine[flask]"``.
"""

from __future__ import annotations

from .._compat import require_extra

require_extra("flask", "flask")

from ._core import REQUIRED, allow_all  # noqa: E402
from ._http import (  # noqa: E402
    ForbiddenError,
    HTTPProblemError,
    MethodNotAllowedError,
    PayloadTooLargeError,
    UnprocessableBodyError,
    UnsupportedMediaTypeError,
)
from .blueprint import create_statechart_blueprint  # noqa: E402
from .extension import XState, problem_response, receipt_response  # noqa: E402
from .session_store import (  # noqa: E402
    DEFAULT_SESSION_LIMIT,
    SessionStore,
    SessionStoreTooLargeError,
)

__all__ = [
    "DEFAULT_SESSION_LIMIT",
    "ForbiddenError",
    "HTTPProblemError",
    "MethodNotAllowedError",
    "PayloadTooLargeError",
    "REQUIRED",
    "SessionStore",
    "SessionStoreTooLargeError",
    "UnprocessableBodyError",
    "UnsupportedMediaTypeError",
    "XState",
    "allow_all",
    "create_statechart_blueprint",
    "problem_response",
    "receipt_response",
]
