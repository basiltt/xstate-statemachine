"""LC-37 repro: `MachineLogic` subclass auto-registration classifies callables
by ARITY, so a callable whose parameter count does not match its intended
contract is silently filed in the wrong registry.

`machine_logic.py:_register_subclass_methods` maps 2 params -> guards,
3 -> services, 4 -> actions. Nothing about the *name*, a decorator, or the
call site is consulted, so:

  * an action written with a default argument (`(i, c, e, a=None)`) still has
    arity 4 and is fine, but an action that omits the unused `action_def`
    parameter -- `(interpreter, context, event)` -- becomes a SERVICE;
  * a guard that takes `*args` is un-classifiable and is dropped entirely;
  * a service written as `(context, event)` becomes a GUARD.

The failure is silent at construction time. The machine only blows up later
with `ImplementationMissingError` -- pointing at the action name, not at the
real cause.

Part 2 shows the sharper half of the bug: the library ALREADY ships
`@action` / `@guard` / `@service` decorators (`pythonic.py`, exported from
`xstate_statemachine.__init__`), which set an explicit `fn._xsm_type` role
marker. `_register_subclass_methods` never reads that marker, so decorating a
`MachineLogic` subclass method -- the obvious way to state the role
explicitly, and the form used by the guides' `@service` examples -- does not
help: arity still wins and the callable is still misfiled.

Exit code 1 if any callable lands in the wrong registry.
"""

from __future__ import annotations

import logging
import sys

from xstate_statemachine import MachineLogic, action, guard, service

logging.disable(logging.CRITICAL)


class OrderLogic(MachineLogic):
    """Trading-OMS logic written in the documented subclass style."""

    # Intended: ACTION. Author omitted the unused `action_def` 4th param.
    def record_fill(self, interpreter, context, event):  # noqa: ANN001
        context["fills"] = context.get("fills", 0) + 1

    # Intended: GUARD, written with *args for forwarding convenience.
    def is_filled(self, *args):  # noqa: ANN001
        return True

    # Intended: SERVICE. Author wrote the 2-arg (context, event) form used by
    # several examples in the guides.
    def submit_order(self, context, event):  # noqa: ANN001
        return {"ok": True}


class DecoratedOrderLogic(MachineLogic):
    """Same logic, but the role is stated EXPLICITLY with the library's own
    already-exported decorators. Arity still overrides the marker."""

    @action
    def record_fill(self, interpreter, context, event):  # noqa: ANN001
        context["fills"] = context.get("fills", 0) + 1

    @guard
    def is_filled(self, interpreter, context, event):  # noqa: ANN001
        return True

    @service
    def submit_order(self, context, event):  # noqa: ANN001
        return {"ok": True}


def registries_of(logic: MachineLogic, names: tuple[str, ...]) -> dict:
    """Map each method name to the registries it actually landed in."""
    return {
        n: [
            k
            for k in ("actions", "guards", "services")
            if n in getattr(logic, k)
        ]
        for n in names
    }


NAMES = ("record_fill", "is_filled", "submit_order")
EXPECTED = {
    "record_fill": ["actions"],
    "is_filled": ["guards"],
    "submit_order": ["services"],
}


def main() -> int:
    # --- 1. undecorated: arity decides, and decides wrong ------------------
    observed = registries_of(OrderLogic(), NAMES)

    print(f"OBSERVED registries (undecorated): {observed}")
    print(f"EXPECTED registries: {EXPECTED}")
    print("OBSERVED: no warning or error was raised at construction time.")
    print(
        "EXPECTED: misclassification is impossible (explicit decorators) or "
        "at minimum warns."
    )
    misfiled = observed != EXPECTED

    # --- 2. decorated: the explicit role marker is ignored -----------------
    decorated = registries_of(DecoratedOrderLogic(), NAMES)
    markers = {
        n: getattr(getattr(DecoratedOrderLogic, n), "_xsm_type", None)
        for n in NAMES
    }

    print()
    print(f"OBSERVED role markers set by @action/@guard/@service: {markers}")
    print(f"OBSERVED registries (decorated): {decorated}")
    print(f"EXPECTED registries: {EXPECTED}")
    print(
        "EXPECTED: an explicit `_xsm_type` marker takes precedence over "
        "arity, so decorating fixes the misclassification."
    )
    decorator_ignored = decorated != EXPECTED

    return 0 if not (misfiled or decorator_ignored) else 1


if __name__ == "__main__":
    sys.exit(main())
