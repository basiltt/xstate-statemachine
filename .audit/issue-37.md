author:	basiltt
association:	owner
edited:	false
status:	none
--
Fixed in #61 (commit a32dd13).

**What changed.** `Interpreter.send()` is now a regular `def` that returns an awaitable (it is still `await`ed exactly as before). The difference is that the owning-thread check runs at the **call site**, before any coroutine is created — so a bare `interp.send(...)` from a foreign thread raises `WrongThreadError` immediately instead of returning a never-awaited coroutine that the GC quietly discards. 500/500 calls in your part-A worker now raise; previously 500/500 were lost.

For legitimate cross-thread delivery there is a new `Interpreter.send_threadsafe(event, **payload) -> concurrent.futures.Future`, built on `asyncio.run_coroutine_threadsafe` against the loop the interpreter was started on. Your part-B worker delivers 500/500 through it.

`repro_37_LC43.py` exits 0 (part B updated to use `send_threadsafe()`, since `run_coroutine_threadsafe(interp.send(...))` now raises by design).

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #37 (LC-43, cross-thread `send()`)

**Status:** core fix verified on 0.8.0 (`9bf6065`). **One undocumented regression
for correct 0.7.x callers.**
**Suggested disposition:** keep open until the break is documented and the error
message is corrected.

---

The reported defect is fixed: a bare `send()` from a foreign thread now raises
`WrongThreadError` instead of returning an un-awaited coroutine and silently
losing the event, and `send_threadsafe()` is the supported replacement. That is
the right shape and we have adopted it.

**The regression.** The original issue text named
`asyncio.run_coroutine_threadsafe(interp.send("F"), loop).result()` as *the only
correct form* for 0.7.0 — the standard asyncio idiom, and the one that actually
worked. On 0.8.0 it **raises `WrongThreadError`**. Verified. The thread check runs
*eagerly* inside `send()` on the calling thread, before the coroutine is ever
handed to `run_coroutine_threadsafe` and scheduled onto the owning loop — so the
one correct 0.7.x cross-thread pattern is rejected along with the broken one.

Two consequences:

1. **It is undocumented.** The changelog covers `send_threadsafe()` and the
   bare-`send()` fix, but nowhere says the `run_coroutine_threadsafe` idiom
   stopped working. Anyone who followed the 0.7.0 advice — including the advice in
   this very issue — gets a runtime exception on upgrade with no deprecation
   window. `docs/_guide/interpreters.md:1010` describes `send_threadsafe` as
   internally doing `run_coroutine_threadsafe`, which actively invites the reader
   to assume the manual form is equivalent.

2. **The error message is wrong for this case.** It says *"Events sent this way
   would be silently lost."* Events sent *that* way were **not** being lost in
   0.7.0 — that pattern was the correct one. A caller who reads the message will
   conclude their working code was always broken. Suggest detecting the
   `run_coroutine_threadsafe` case is not separable, so instead soften the message
   to something like: *"send() must be called on the interpreter's own loop
   thread. Use send_threadsafe() from another thread — note that
   `run_coroutine_threadsafe(interp.send(...))` is also rejected, because the
   thread check runs before the coroutine is scheduled."*

**Related, and the reason we are not closing this:** the replacement,
`send_threadsafe()`, is the one entry point that **bypasses `strict` mode and
registered `event_schemas`** (see our comment on #51). So the API this issue
steers multi-threaded callers toward is simultaneously the one without the new
guardrail. Fixing that would make this a clean close.

Please also consider listing this break under a **Removed / Changed** heading
rather than inside the `send_threadsafe` addition — it is a behavioural break for
code that was correct.

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.
Probe: `probes/v080/f_strict_and_threads.py`.

--
