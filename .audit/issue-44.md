author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #44 (LC-19, restore does not restart invokes)

**Status:** verified on 0.8.0 (`9bf6065`).
**Suggested disposition:** close, with one ergonomics note.

---

Verified. `pending_invocations()` lists every `PendingInvocation(state_id,
invoke_id, src)` in the active configuration with no live service or child actor,
unconditionally and with no flag — which is the API we actually needed.
`from_snapshot(restart_services=True)` re-invokes each of them from scratch
through the same path `_enter_states` uses. Keeping the static rebuild as the
default is the right call: for an order machine, blanket-re-invoking a submit is a
duplicate-order risk, so our recovery path reconciles each pending invocation
against the venue before restarting it. The fact that entry actions do **not**
re-run is what makes that safe to reason about — worth stating explicitly in the
guide, because it is the property the whole recovery design rests on.

One ergonomics note, which the issue itself raised as a nice-to-have rather than a
criterion: **`status` still reports `"running"` for a statically restored machine
whose services are dormant.** There is no way to distinguish "genuinely live" from
"restored, parked, nothing running" from `status` alone. We have made
`pending_invocations()` mandatory in our health checks, so this is not blocking —
but a health check that trusts `status` is now wrong in a way that is invisible
until an order sits unfilled. A `restored` / `dormant` qualifier on `status`, or
just a sentence in the persistence guide saying **`status` is not a liveness
signal after `from_snapshot`; call `pending_invocations()`**, would close it.

Not independently re-verified this pass, for the record: task cancellation on exit
for *restarted* invokes, and sync-engine parity. Both share the code path, so we
expect them to hold.

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.
Probe: `probes/v080/d_restore_invokes.py` (8/9).

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
Reopening for the remaining criterion: after `from_snapshot()` without `restart_services=True`, `interpreter.status` still reports `"running"` although every invocation listed by `pending_invocations()` is dormant. Any caller using `status` as a liveness signal is misled. Suggested: a distinct `"restored"`/`"dormant"` status (or a `has_dormant_invocations` property) until the pending invocations are resumed or discarded.
--
