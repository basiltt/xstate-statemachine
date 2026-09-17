# /src/xstate_statemachine/_typing.py
# -----------------------------------------------------------------------------
# 🧷 Shared type variables
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `TContext` is imported by `models.py` AND
# `machine_logic.py`, which import each other, so it cannot live in either
# without a cycle. This leaf module has no imports of its own and exists
# solely so there is ONE definition of the library's type parameter.
# -----------------------------------------------------------------------------
"""Type variables shared across the package."""

from typing import Any, Mapping, TypeVar

# 🏛️ ONE type parameter, and it is the context. A `TEvent` parameter used
#    to ride alongside it on every generic class; it appeared in zero
#    signatures, so it constrained nothing and was pure ceremony every user
#    had to spell (`Interpreter[Ctx, Any]`).
#
#    Bound to `Mapping[str, Any]`, not `Dict`: a `TypedDict` is NOT a
#    subtype of `dict` in the type system, so the `Dict` bound rejected the
#    one annotation a careful user would write -- `SyncInterpreter[MyCtx]` --
#    as a type error. With `Mapping` it is accepted, and
#    `interp.context["count"]` types as `int`.
TContext = TypeVar("TContext", bound=Mapping[str, Any])

__all__ = ["TContext"]
