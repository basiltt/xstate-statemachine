author:	basiltt
association:	owner
edited:	false
status:	none
--
Fixed in #61 (commit c1866e5).

**What changed.** A leading-dot target (`".A2"`) now resolves into the **source state's descendants**, matching XState v5 (verified against 5.33.0). From `A` with children `A1`/`A2`, `{"target": ".A2"}` enters `A.A2` and runs `A1`'s exit and `A2`'s entry actions in order.

For backward compatibility the 0.7.x sibling reading is kept as a fallback when the source has no matching child — so an existing leaf state using `".b"` to mean "sibling b" keeps working. Setting `"strictTargets": true` on the machine disables that fallback and makes the v5 reading the only one.

Together with #30, a `.child` that resolves to nothing is now a build-time `InvalidConfigError` rather than a silent no-op.

`repro_31_LC07.py` exits 0 (the action lambda in the repro was updated from 3 to 4 params to match the documented action signature). Tests: `tests/test_build_time_validation.py::TestRelativeChildTargets`.

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #31 (LC-07, relative `.child` targets)

**Status:** core fix verified on 0.8.0 (`9bf6065`). **Acceptance criterion 2 did
not land.**
**Suggested disposition:** keep open, or close and open a small docs/warning issue.

---

The important half is fixed and we can confirm it: `.child` now resolves into the
**source's** descendants, matching XState v5, and `strictTargets: true` disables
the 0.7.x sibling fallback entirely. With `strictTargets` set we get exactly the
behaviour the issue asked for.

What did not land is criterion 2 of the issue's own acceptance list: **the sibling
fallback is still reachable by default and still silent.** In our run,
`resolve_target_state(".B", node_A)` where `A` has no child `B` still returns the
sibling `m.B` — and no `DeprecationWarning` was observed when `strictTargets` is
simply omitted. So today the options are:

* omit `strictTargets` → 0.7.x fuzzy fallback, **silently**; or
* set `strictTargets: true` → fallback disabled.

There is no "warn but still succeed" middle ground, which is the migration path
the issue proposed and the one that would let an existing 0.7.x codebase find its
own broken targets without a flag day. Given that everywhere else in 0.8.0 the
pattern is *observability is unconditional, recovery is opt-in* — `on_guard_error`
and `on_unhandled_event` both fire under the 0.7.x defaults, which is exactly
right — the silent fallback is the odd one out.

Suggestion: emit a `DeprecationWarning` (or fire `on_transition_failed`) on every
sibling-fallback resolution when `strictTargets` is unset, naming the target and
the absolute `#machine.path` form that would resolve unambiguously. The
unresolvable-target error message already does exactly this and it is genuinely
the best thing in the release; the fallback path deserves the same message.

Related, and not a criticism: the exception type shipped as `InvalidConfigError`
rather than the `StateNotFoundError` named in the issue summary. We have adjusted
on our side — flagging only because the issue text will read as unfulfilled to
anyone matching on the type name.

**Also unverified this pass:** criterion 4 (async/sync error-contract parity for
relative targets). We did not re-test it; given the wave-3 single-core refactor we
would expect it to hold.

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.
Evidence: verification script `LC-07.result.md` (available on request / in the forthcoming conformance-suite PR).

--
