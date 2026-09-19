# Bug: `send_threadsafe()` bypasses `strict` mode and `event_schemas` — the recommended cross-thread API is the one without the guardrail


## Summary

`_check_strict` is called from `Interpreter.send`, `SyncInterpreter.send` and the
`raise` built-in — but **not** from `send_threadsafe()`, which calls
`_prepare_event` and then `_enqueue` directly. On a `strict: True` machine with
registered `event_schemas`, an event delivered from a foreign thread is therefore
neither name-checked nor payload-validated.

This is sharp because 0.8.0 made `send_threadsafe()` the *recommended* — and
effectively the *only* — API for a foreign thread: bare `send()` now raises
`WrongThreadError`, and so does
`asyncio.run_coroutine_threadsafe(interp.send(...), loop)`. So the path a
multi-threaded production application is required to take is the one without the
validation the same release added.

## Environment

- Library: `xstate-statemachine` 0.8.0, commit `9bf6065`, local clone, `pip install -e .`
- Python: 3.13.7 (CPython, MSC v.1944 64-bit)
- OS: Windows 11 x64 (10.0.26200)

## Minimal reproduction

```python
import asyncio, threading
from xstate_statemachine import Interpreter, create_machine

CFG = {"id": "st", "initial": "a", "strict": True,
       "states": {"a": {"on": {"FILL": "b"}}, "b": {}}}

class QtySchema:
    def validate(self, payload):
        qty = (payload or {}).get("qty")
        if not isinstance(qty, int) or qty <= 0:
            raise ValueError(f"qty must be a positive int, got {qty!r}")

async def main():
    i = Interpreter(create_machine(CFG, event_schemas={"FILL": QtySchema()}), strict=True)
    await i.start()

    await i.send("FIL")                       # UnknownEventError: Did you mean 'FILL'?
    threading.Thread(target=lambda: i.send_threadsafe("FIL")).start()   # accepted, dropped
    threading.Thread(target=lambda: i.send_threadsafe("FILL", qty=-1)).start()  # accepted, TRANSITIONS

asyncio.run(main())
```

Full script: `repro/N-04_send-threadsafe-bypasses-strict.py` (exits 1 while
present, 0 once fixed).

## Observed

```
OBSERVED send_typo               : UnknownEventError
OBSERVED send_bad_payload        : InvalidEventPayloadError
OBSERVED threadsafe_typo         : accepted
OBSERVED threadsafe_bad_payload  : accepted
OBSERVED final states           : ['st.b']
RESULT: DEFECT REPRODUCED (bypassed on: threadsafe_typo, threadsafe_bad_payload)
```

Two distinct failures:

1. **`threadsafe_typo`** — `send_threadsafe("FIL")` is accepted, its future
   completes with no exception, and the event is silently dropped at dispatch.
   This is exactly the silent no-op that `strict` mode exists to prevent.
2. **`threadsafe_bad_payload`** — worse. `send_threadsafe("FILL", qty=-1)` skips
   the registered validator *and the machine actually transitions* to `st.b` on
   a payload the schema rejects. The final state is `['st.b']`. A schema that is
   enforced on one entry point and not another is not a schema.

## Expected

`send_threadsafe()` applies the same `_check_strict` and `event_schemas`
validation as `send()`, reporting the failure to the caller — which is
straightforward here, since it already returns a future that can carry the
exception.

## Root cause

`interpreter.py`. `_check_strict` is invoked at `send` (~`:601`),
`SyncInterpreter.send` (~`:474`) and the `raise` built-in
(~`base_interpreter.py:2555`). `send_threadsafe()` takes a shorter path:
`_prepare_event` → `_enqueue`, skipping the check entirely. Payload validation
lives in the same skipped step.

## Impact

Any application that uses `strict: true` and `event_schemas` — that is, any
application that took 0.8.0's own advice — has an unvalidated back door, and it
is the door the library tells multi-threaded callers to use. The failure is
silent for the name case and *actively wrong* for the payload case (an invalid
event drives a real transition).

Severity is Medium rather than High only because the workaround is trivial (wrap
`send_threadsafe` and validate first, which is what we now do). The
recommended-path-lacks-the-guardrail property is what makes it worth filing.

## Suggested fix

Call `_check_strict` and the schema validator inside `send_threadsafe()`, before
`_enqueue`, and surface the exception through the returned future (or raise
synchronously on the calling thread, which is more useful — the caller is on a
foreign thread and can handle it there).

Better still, route `send_threadsafe()` through the same `_prepare_and_validate`
helper that `send()` uses, so the two cannot drift again. The general lesson
matches #60's: one validation path, two delivery strategies.

## Acceptance criteria

- [ ] `repro/N-04_send-threadsafe-bypasses-strict.py` exits 0.
- [ ] `send_threadsafe("FIL")` on a `strict: True` machine raises/reports
      `UnknownEventError` with the difflib suggestion.
- [ ] `send_threadsafe("FILL", qty=-1)` with a registered schema raises/reports
      `InvalidEventPayloadError` **and does not transition**.
- [ ] Validation for `event_schemas` applies regardless of the `strict` setting
      on this path too, matching `send()`.
- [ ] Tests added:
  - `tests/test_strict_mode.py::test_send_threadsafe_rejects_unknown_event`
  - `tests/test_strict_mode.py::test_send_threadsafe_validates_payload_schema`
  - `tests/test_strict_mode.py::test_send_threadsafe_invalid_payload_does_not_transition`

## Related

- `#51` (LC-34) — strict mode. This is a hole in it.
- `#37` (LC-43) — the change that made `send_threadsafe()` the only cross-thread
  option, which is what elevates this from a corner to a main road.

## Verification

Independently verified on 2026-09-17.

- Library: 0.8.0, commit `9bf6065`, local clone, `pip install -e .`.
- Python 3.13.7, Windows 11 x64.
- Repro run in a fresh process → **exit 1**, output as quoted.
- Controls in the same process and run: `send("FIL")` → `UnknownEventError`,
  `send("FILL", qty=-1)` → `InvalidEventPayloadError`, so strict mode and the
  schema are both correctly armed on that machine.


---
Found while re-verifying the 0.8.0 release against the adoption-readiness checklist in #26. Self-contained repro attached in the body; exits 1 while the defect is present, 0 once fixed.

