"""LC-57 - the two engines duplicate rather than share the core algorithm.

Evidence, all measured from the installed package:

1. The "mode-agnostic" base declares the algorithm as `async def`; `SyncInterpreter`
   re-implements each step as a *separate* sync method, so the base versions are
   dead code for the sync engine. The Template Method pattern is broken.
2. Every core step is written twice, in comparable volume.
3. A live consequence: the duplicated `_is_async_callable` guard in the sync
   engine misclassifies `functools.partial(async_fn)`, so an async action is
   neither rejected nor awaited - it silently no-ops while the transition commits.

Exits 1 when the duplication / the misclassification are present.
"""

from __future__ import annotations

import functools
import inspect
import sys

from xstate_statemachine import (
    Interpreter,
    MachineLogic,
    NotSupportedError,
    SyncInterpreter,
    create_machine,
)
from xstate_statemachine.base_interpreter import BaseInterpreter

STEPS = ("_process_event", "_execute_transition", "_enter_states", "_exit_states",
         "_execute_actions", "_execute_builtin_action")


def sloc(fn) -> int:
    try:
        return len([ln for ln in inspect.getsource(fn).splitlines() if ln.strip()])
    except (TypeError, OSError):
        return 0


broken_template, duplicated = [], []
for name in STEPS:
    base, sync, asy = (getattr(k, name, None) for k in (BaseInterpreter, SyncInterpreter, Interpreter))
    owner = getattr(sync, "__qualname__", "-").split(".")[0]
    if base is not None and inspect.iscoroutinefunction(base) and sync is not base and not inspect.iscoroutinefunction(sync):
        broken_template.append(name)
    if sync is not base and asy is not base and sync is not asy:
        duplicated.append(name)
    print(f"OBSERVED {name:24s} base_async={inspect.iscoroutinefunction(base)!s:5s} "
          f"sync_owner={owner:16s} sync_sloc={sloc(sync):4d} async_sloc={sloc(asy):4d}")

print(f"OBSERVED base async methods shadowed by same-named sync overrides: {broken_template}")
print(f"OBSERVED core steps implemented separately by BOTH engines: {duplicated}")

# The sync engine also forks two steps under *different* names, so the base's
# async originals are never reached at all.
for base_name, sync_name in (("_execute_transition", "_execute_transition_sync"),
                             ("_resolve_target_state_node", "_resolve_target_state_robustly")):
    fork = getattr(SyncInterpreter, sync_name, None)
    print(f"OBSERVED BaseInterpreter.{base_name} (sloc={sloc(getattr(BaseInterpreter, base_name)):3d}) "
          f"forked as SyncInterpreter.{sync_name} (sloc={sloc(fork):3d}) - renamed, so no override, no ABC check")
    if fork is not None:
        duplicated.append(sync_name)

# --- live divergence caused by the duplicated guard -------------------------
async def act(interp, ctx, evt, action_def):  # noqa: ANN001
    ctx["ran"] = True


machine = create_machine(
    {"id": "m", "initial": "a", "context": {},
     "states": {"a": {"on": {"GO": {"target": "b", "actions": ["act"]}}}, "b": {}}},
    logic=MachineLogic(actions={"act": functools.partial(act)}),
)
interp = SyncInterpreter(machine).start()
try:
    interp.send("GO")
    outcome = f"no error; state={sorted(interp.current_state_ids)} context={interp.context}"
    misclassified = True
except NotSupportedError as exc:
    outcome, misclassified = f"NotSupportedError: {exc}", False

print(f"OBSERVED SyncInterpreter._is_async_callable(partial(async_fn)) = "
      f"{bool(SyncInterpreter._is_async_callable(functools.partial(act)))} "
      f"(inspect.iscoroutinefunction says {inspect.iscoroutinefunction(functools.partial(act))})")
print(f"OBSERVED sync engine running an async action wrapped in functools.partial -> {outcome}")
print("EXPECTED one shared sans-io core parameterised over an execution strategy, so each "
      "step (and each guard such as _is_async_callable) exists once and cannot diverge")

sys.exit(1 if (broken_template or duplicated or misclassified) else 0)
