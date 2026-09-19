author:	basiltt
association:	owner
edited:	false
status:	none
--
Fixed in #61 (commits a8eeb58, f3fc1db).

**What changed.** `MachineLogic` subclass auto-registration now checks the explicit `@action` / `@guard` / `@service` marker **first**; arity inference is only the fallback. So a two-argument callable decorated `@action` is an action, full stop.

For undecorated callables:
- arity 2 or 3 (ambiguous between guard / service / action) emits a `UserWarning` naming the member and suggesting the decorator;
- an arity that fits no category emits a `UserWarning` instead of being silently skipped.

`repro_52_LC30.py` exits 0 (updated to assert the warnings, per its acceptance criteria).

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #52 (LC-37, arity misclassification)

**Status:** verified on 0.8.0 (`9bf6065`) for decorated code.
**Suggested disposition:** close, or keep open only to track `MachineLogic(strict=True)`.

---

Verified: `@action` / `@guard` / `@service` markers now win over arity-based
auto-registration in `MachineLogic` subclasses, and ambiguous arities warn. For
any codebase that decorates — which is the recommendation, and is now what we do —
the misclassification this issue reported is gone.

The undecorated arity fallback is retained, as the issue's own "Backwards
compatibility" section proposed, and it can still misfile: an **undecorated
3-argument method intended as an action lands in `services`**. It is no longer
*silent* — a `UserWarning` always accompanies it — so the worst property is gone.
It is not *prevented*.

That is a defensible place to stop for a 0.x minor. The only thing we would ask
is whether the second half of the plan is still on the roadmap: the issue floated
a `MachineLogic(strict=True)` that upgrades the warning to a hard error, and we
did not find it in 0.8.0. If it is planned for 1.0, a line in the changelog or a
`DeprecationWarning` on the undecorated path would let us set it now and stop
relying on a `UserWarning` filter in CI. If it is not planned, we would suggest
saying so and closing — we can enforce decoration with our own linter, and would
rather know that is the intended answer.

Note for anyone reading the original repro: `repro/LC-37_arity-misclassification.py`
still exits 1. That is the repro being stale, not the fix being absent — it
asserts on the undecorated path, which is the deliberately-retained one. Our
0.8.0 verification script exercises the decorated path and passes.

**Environment:** 0.8.0 @ `9bf6065`, CPython 3.13.7, Windows 11 x64.
Evidence: verification script `LC-37.result.md` (available on request / in the forthcoming conformance-suite PR).

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
Reopening for the unshipped half: decorated methods are now classified correctly, but an undecorated method is still filed by arity (with a `UserWarning`). The issue's proposed fix was `MachineLogic(strict=True)` — refuse undecorated registration outright — so a misfiled guard/action becomes a build-time error rather than a warning that can be missed in a long-lived process. Happy to close once that flag (or an equivalent) lands.
--
