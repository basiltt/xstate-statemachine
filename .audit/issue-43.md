author:	basiltt
association:	owner
edited:	false
status:	none
--
Fixed in #62 (commit dc44130).

**What changed.** The 5 ms status poll is gone. `BaseInterpreter` keeps a list of terminal listeners fired once from a shared `_on_terminal()` tail of `_complete()` / `_fail()`. `Interpreter.wait_done()` returns a future resolved by that hook — or already resolved if the child is terminal, so the "child finished during `start()`" race stays fixed. `_spawn_and_manage_actor` awaits it. `_ACTOR_POLL_INTERVAL` no longer exists.

Measured: median `onDone` latency **< 2 ms** (was a 5 ms floor); idle children cost one manager task plus their own run loop, with zero periodic wake-ups. `onError` semantics and cancellation on parent-state exit are unchanged and pinned.

The same signal is what #41 (blocking spawn) and #57 (reaping) build on, so it landed first.

Tests: `tests/test_actor_lifecycle.py::TestActorCompletionSignal`. `repro_43_LC28.py` exits 0.

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #43 (LC-28, two tasks per invoked child)

**Status:** partially fixed on 0.8.0 (`9bf6065`).
**Suggested disposition:** keep open, retitled to the remaining half.

---

Item 2 of the proposed fix landed and is a real improvement: the 5 ms status poll
is gone, replaced by awaiting a completion future, and `wait_done()` is exposed as
a public API. Completion latency dropped from a 5 ms floor to sub-millisecond. For
our fan-out that alone is worth the upgrade.

Item 3 — "collapse the second task" — did not. The task count per idle invoked
child is **still 2**, not the ≤1 the issue targeted:

```python
child_interpreter = Interpreter(actor_machine, ...)
...
await child_interpreter.start()      # the child's own event-loop task   (task 1)
...
await child_interpreter.wait_done()  # runs inside the task created by
                                     # _invoke_service (task 2) - no longer
                                     # polling, but not collapsed away either
```

So the mechanism changed exactly as promised while the *resource* claim in the
issue title did not. That matters to us specifically because of MUSTNOT-08 on our
side: we cap concurrently invoked children per process on a measured task-growth
budget, and 2N is the number we have to keep budgeting for.

Two options, either of which we would be happy with:

1. Have `_invoke_service` await the child's completion future directly from the
   parent's run loop rather than from a dedicated task, so an idle child costs
   one task; or
2. Close this as "poll removed, task count is by design" and state the 2-tasks-
   per-child figure in the production-characteristics page, so it is a documented
   budget rather than a discovered one.

The second is a perfectly good answer — we just need the number to be published
rather than measured by each user.

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.
Evidence: verification script `LC-28.result.md` (available on request / in the forthcoming conformance-suite PR);
source `interpreter.py::_spawn_and_manage_actor`.

--
