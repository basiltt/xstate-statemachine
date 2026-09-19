author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #51 (LC-34, strict mode)

**Status:** verified as FIXED-OPT-IN on 0.8.0 (`9bf6065`), with **two bypass
paths**.
**Suggested disposition:** keep open until the bypasses are closed.

---

Strict mode works as specified where it applies. Confirmed: `send()` of an
undeclared event type raises `UnknownEventError` synchronously at the call site,
before the event is queued, with a difflib suggestion (`Did you mean 'FILL'?`);
`create_machine(event_schemas={...})` validates payloads and raises
`InvalidEventPayloadError` at the call site regardless of the strict setting; the
default (strict unset, no schemas) is unchanged. Dependency-free validator
duck-typing (`validate(payload)` or `__call__`) is a nice touch.

Two paths reach dispatch **without** the guardrail:

**1. `send_threadsafe()` bypasses `strict` and `event_schemas` entirely.**
`_check_strict` is called from `Interpreter.send` (~`interpreter.py:601`),
`SyncInterpreter.send` (~`:474`) and the `raise` built-in
(~`base_interpreter.py:2555`) — but not from `send_threadsafe()`, which calls
`_prepare_event` and then `_enqueue` directly. Verified on a `strict: True`
machine: `send("FIL")` raises with the suggestion; `send_threadsafe("FIL")` is
accepted, its future completes with no exception, and the event is **silently
dropped at dispatch**. Registered `event_schemas` validators are bypassed on the
same path.

This is the sharp one, because after #37 `send_threadsafe()` is the *recommended*
— and now effectively the *only* — API for a foreign thread. So the path a
multi-threaded production app is required to take is the one without the check.
We have had to wrap it ourselves to restore the validation.

**2. A strict violation inside an internal `raise` is invisible under
`actionErrorPolicy: "continue"`.** `_check_strict` does run on the `raise`
built-in, but under the default action-error policy the resulting exception is
caught, logged and skipped, so a typo'd internally-raised event produces no
observable failure and the transition still commits. Strict alone does not close
the typo class — it closes it only when paired with a non-default
`actionErrorPolicy`. We now mandate the pair on our side; worth saying so in the
strict-mode docs, since users will reasonably expect `strict: true` to be
sufficient on its own.

**Not re-verified this pass:** wildcard (`"*"`) and partial (`"mouse.*"`)
descriptor acceptance under strict, `after`/`invoke` event allowlisting, and the
sync engine. All present in source (`base_interpreter.py:1466` `_check_strict`,
called from both the public `send()` path and the internal-raise path); we simply
did not exercise them.

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.
Probe: `probes/v080/f_strict_and_threads.py` (14/15).

--
