author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #50 (LC-38, `SyncInterpreter` timer threads)

**Status:** the reported defect is fixed on 0.8.0 (`9bf6065`). **A new defect of
the same class was introduced in its place.**
**Suggested disposition:** keep open, or close and file the new one (we have
drafted it as `#76`).

---

First, the fix is real and we can confirm the headline claim: `SyncInterpreter` no
longer spawns an OS thread per `after` timer or delayed send. **25 machines with
armed timers → +0 threads.** Deadlines are delivered on the caller's thread at the
top of `send()`, in the macrostep loop, or via the new `tick()`. The unlocked
cross-thread context mutation this issue was about is gone.

The problem is that the deadline has moved somewhere `SyncInterpreter` cannot
reach. `RealClock.set_timeout` branches on the **caller's** context, not on which
engine owns the clock:

```python
try:
    loop = asyncio.get_running_loop()
except RuntimeError:
    loop = None
if loop is not None:
    return loop.call_later(max(0.0, delay_sec), fn)   # asyncio lane
return self._heap.push(self.now() + max(0.0, delay_sec), fn, owner)
```

So a `SyncInterpreter` **constructed from inside a running event loop** parks its
`after` deadlines on `loop.call_later`, leaving `clock._heap` empty. `tick()` and
the pump at the top of `send()` both call `clock.pump()`, which drains only the
heap — they find nothing, and the timer never fires through the sync engine's own
API.

Measured, same machine, `after: {40: "b"}`:

| construction context | `clock.pending` | state after `tick()` |
|---|---:|---|
| off-loop thread (control) | 1 | `{'sy.b'}` |
| inside a running loop | **0** | `{'sy.a'}` |

Partial mitigation, which is why this is not catastrophic: the asyncio
`call_later` callback still enqueues the event, so a *later* `tick()` after enough
loop turns does pick it up. The defect is that **`tick()` is not authoritative** —
it cannot deliver a deadline that is genuinely due, which is the one guarantee the
new synchronous timer lane exists to provide.

Who this bites: any async application that keeps one sync machine for a hot path,
and — more commonly — **any async test that constructs a sync machine**, which is
a very easy way to get a green suite that does not reflect production.

Suggested fix: bind the lane at clock-attachment time rather than at
`set_timeout` time — the `Clock` already knows its `owner`, so a clock owned by a
`SyncInterpreter` should always use the heap regardless of the calling context.
Failing that, have `SyncInterpreter.__init__` raise (or warn loudly) when
constructed inside a running loop with a `RealClock`, the same way `send()` from a
foreign thread now raises `WrongThreadError` — this release's own precedent for
"reject the ambiguous case rather than half-support it" is a good one.

Repro: `probes/v080/e7_sync_timer_in_loop.py` (cases E7a control vs E7b).

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.

--
