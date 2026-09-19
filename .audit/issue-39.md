author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #39 (LC-42, `send(wait=)` / `send(priority=)`)

**Status:** feature verified on 0.8.0 (`9bf6065`). **One high-severity defect in
the new API.**
**Suggested disposition:** keep open until the receipt keying is fixed (drafted
separately as `#75`).

---

The feature is excellent and we attacked it hard — **13/13** on the inbox and
receipt probes, no findings there. Confirmed:

* `send(wait=True)` resolves only after the whole macrostep, including an
  `await`ing action (context observed at its final value, `changed=True`, settled
  `state_ids`);
* it reports the **settled** state after `always` transitions (`al.c`, not
  `al.b`);
* it carries the action error under both `continue` and `rollback`;
* `changed=False` for an unhandled event;
* on a stopped interpreter it resolves with `InterpreterStoppedError` in the
  receipt rather than hanging;
* `priority=True` is exempt from the inbox bound and jumps a 20-deep backlog to
  index 0;
* a `BLOCK` send issued **from inside an action** does not self-deadlock — it is
  correctly rerouted to the internal queue (12/12).

That last one in particular is the kind of thing that usually goes wrong, and it
does not. This closes the "a statechart cannot answer a question" complaint
completely.

**The defect.** `_make_receipt` / `_resolve_receipt` key the receipt map on
`id(event_obj)`:

```python
self._receipts[id(event_obj)] = fut            # ~interpreter.py:690
fut = self._receipts.pop(id(event_obj), None)
```

Two concurrent `send(ev, wait=True)` calls with the **same `Event` instance**
collide on the key. The second `_make_receipt` overwrites the first future, which
is then never resolved and never failed — an awaiting coroutine that hangs
forever, with no error and no timeout.

```python
ev = Event(type="T", payload={})
await asyncio.gather(i.send(ev, wait=True), i.send(ev, wait=True))   # hangs
```

Controls, so this is not misattributed:

* `send("T", wait=True)` twice (fresh objects) → both resolve;
* **200-way** concurrent `send("T", wait=True)` → all 200 resolve, so `id()`
  recycling of dead objects is not the cause;
* sequential reuse of the same object → works.

It is specifically caller-side identity reuse, and reusing a pre-built `Event` as
a template is an obvious pattern — `send()` accepts `Event` instances in every
overload, so nothing signals that the object must be fresh.

We think this is worth treating as high severity precisely because of where it is:
a new silent hang inside the API that was added to make `send` answerable, in the
release whose stated theme is eliminating silent failure. Suggested fix: a
monotonic per-send token as the receipt key instead of `id(event_obj)`.

Two smaller things we did not re-verify: the reserved-payload-key
(`wait`/`priority` in a dict payload) `DeprecationWarning`, and FIFO ordering
*among* priority events in isolation from the aggregate latency measurement.

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.
Probe: `probes/v080/c_inbox_receipts.py` (13/13).

--
