# Bug: `send(event, wait=True)` hangs forever when the same `Event` instance is in flight twice (receipt keyed on `id()`)


## Summary

`Interpreter.send(event_obj, wait=True)` keys its pending-receipt map on
`id(event_obj)`. Two concurrent sends that pass the **same `Event` instance**
collide on that key: the second `_make_receipt` overwrites the first future,
which is then never resolved and never failed. The first `await` hangs forever —
no exception, no timeout, no log line.

This is a silent hang in the API that 0.8.0 added specifically to make `send`
answerable, in the release whose stated theme is eliminating silent failure.

## Environment

- Library: `xstate-statemachine` 0.8.0, commit `9bf6065`, local clone, `pip install -e .`
- Python: 3.13.7 (CPython, MSC v.1944 64-bit)
- OS: Windows 11 x64 (10.0.26200)

## Minimal reproduction

```python
import asyncio
from xstate_statemachine import Event, Interpreter, create_machine

CFG = {"id": "rc", "initial": "a",
       "states": {"a": {"on": {"T": "b"}}, "b": {"on": {"T": "a"}}}}

async def main():
    i = Interpreter(create_machine(CFG))
    await i.start()
    ev = Event(type="T", payload={})
    await asyncio.gather(i.send(ev, wait=True), i.send(ev, wait=True))   # hangs

asyncio.run(main())
```

Full script with controls: `repro/N-01_send-wait-receipt-id-collision.py`
(exits 1 while present, 0 once fixed).

## Observed

```
OBSERVED control_fresh_2way              : resolved
OBSERVED control_fresh_200way            : resolved
OBSERVED control_same_object_sequential  : resolved
OBSERVED subject_same_object_concurrent  : HUNG
EXPECTED every case                    : resolved
RESULT: DEFECT REPRODUCED
```

The three controls matter, because they rule out the obvious alternative
explanations:

| Control | Result | Rules out |
|---|---|---|
| `send("T", wait=True)` ×2 concurrent (fresh objects) | both resolve | "concurrent `wait=True` is just unsupported" |
| `send("T", wait=True)` ×200 concurrent (fresh objects) | all 200 resolve | `id()` recycling of dead objects |
| Same `Event` object, **sequential** | resolves | "an `Event` is single-use by design" |
| Same `Event` object, **concurrent** | **hangs** | — this is the defect |

## Expected

Both sends resolve with their own `Receipt`. An `Event` instance is an ordinary
value object; nothing in the API signals that it may not be reused, and `send()`
accepts `Event` instances in every documented overload, so passing a pre-built
template is a natural pattern.

If instance reuse genuinely cannot be supported, the second send should raise
immediately at the call site with a clear message — this release's own precedent
(`WrongThreadError` rather than silent loss) is the right one — rather than
hanging.

## Root cause

`interpreter.py`, `_make_receipt` / `_resolve_receipt` (~line 690):

```python
self._receipts[id(event_obj)] = fut          # _make_receipt
fut = self._receipts.pop(id(event_obj), None) # _resolve_receipt
```

`id()` is unique only among *simultaneously live* objects, and is emphatically
not unique across two references to one object. The second `_make_receipt`
replaces the dict entry; the first future loses its only handle and is
unreachable by `_resolve_receipt`, `stop()`'s pending-receipt drain, or anything
else.

## Impact

The awaiting coroutine never completes and never raises, so:

- `asyncio.wait_for` is the only defence, and nothing in the docs suggests it is
  needed;
- the task leaks for the lifetime of the process;
- `stop()` does not resolve it, because the future is no longer in `_receipts`;
- there is no log line and no hook, so it is invisible to monitoring.

Severity is High rather than Medium because the failure mode is *silent* and
sits inside the answer-channel API — the exact combination the 0.8.0 audit set
out to eliminate.

## Suggested fix

Replace the identity key with a monotonic per-send token:

```python
self._receipt_seq += 1
token = self._receipt_seq
event_obj = replace(event_obj, _receipt_token=token)   # or a side table keyed by token
self._receipts[token] = fut
```

Carry the token on the queued envelope rather than on the caller's object, so
caller-side reuse is irrelevant by construction. A regression test asserting that
`asyncio.gather(i.send(ev, wait=True), i.send(ev, wait=True))` resolves twice
would pin it.

## Acceptance criteria

- [ ] `repro/N-01_send-wait-receipt-id-collision.py` exits 0.
- [ ] Two concurrent `send(ev, wait=True)` calls with one `Event` instance both
      resolve, each with a `Receipt` describing its own macrostep.
- [ ] N concurrent sends of one reused instance all resolve (N ≥ 100).
- [ ] `stop()` resolves every outstanding receipt, including duplicates of one
      instance, with `InterpreterStoppedError`.
- [ ] Tests added:
  - `tests/test_interpreter_send_receipt.py::test_reused_event_instance_resolves_both_receipts`
  - `tests/test_interpreter_send_receipt.py::test_many_concurrent_receipts_on_one_instance`
  - `tests/test_interpreter_send_receipt.py::test_stop_resolves_duplicate_instance_receipts`

## Related

- `#39` (LC-42) — the issue that introduced `send(wait=)`. Everything else in it
  verified 13/13 under adversarial probing; this is the one gap.
- `#38` (LC-41) — the bounded inbox that receipts are measured against.

## Verification

Independently verified on 2026-09-17.

- Library: 0.8.0, commit `9bf6065`, local clone, `pip install -e .` into a
  dedicated venv.
- Python 3.13.7, Windows 11 x64.
- Repro run in a fresh process → **exit 1**, output as quoted above.
- Controls re-run three times with identical results; the 200-way control rules
  out `id()` recycling as the mechanism.


---
Found while re-verifying the 0.8.0 release against the adoption-readiness checklist in #26. Self-contained repro attached in the body; exits 1 while the defect is present, 0 once fixed.

