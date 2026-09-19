author:	basiltt
association:	owner
edited:	false
status:	none
--
Fixed in #61 (commit 6b1ee7a).

**What changed.** A new per-machine policy, `actionErrorPolicy`, decides what happens when an action raises:

| value | behaviour |
|---|---|
| `"continue"` (default) | 0.7.x behaviour: remaining actions skipped, transition still commits. Now emits a one-shot `DeprecationWarning`. |
| `"rollback"` | Transition aborted; pre-transition **configuration and context** are both restored. |
| `"fail"` | Rolled back, then the interpreter stops with `status == "error"` and `interpreter.error` set to a `TransitionFailedError` whose `__cause__` is the original exception. |

Under every policy the failure is observable: `on_action_error` fires as before, a new `on_transition_failed(interpreter, transition, failed_actions)` hook fires with the `(action, exception)` pairs, and `interpreter.last_transition_ok` is `False`. `on_transition` no longer fires for a rolled-back transition, so a partial transition is now distinguishable from a complete one.

**Why the default did not change.** Per your own recommendation the default stays `"continue"` so 0.7.x machines behave identically on upgrade; the default flips to `"rollback"` in 1.0. Your repro (`tests/regression/candleviewer/repro_27_LC01.py`) therefore still exits 1 under the default — set `"actionErrorPolicy": "rollback"` on the machine and it exits 0 in both engines.

Tests: `tests/test_action_error_policy.py` (11, both engines). Thanks for the precise repro and the policy sketch — the shape landed essentially as you proposed.

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
# Follow-up comment draft — #27 (LC-01, `actionErrorPolicy`)

**Status:** verified on 0.8.0 (commit `9bf6065`), Python 3.13.7, Windows 11.
**Suggested disposition:** close, once the three notes below are acknowledged in docs.

---

Re-verified on 0.8.0. `actionErrorPolicy: "rollback"` restores both configuration
and context; `"fail"` rolls back and stops with `TransitionFailedError`; under the
default `"continue"` the failure is now *observable* through
`interpreter.last_transition_ok` and the `on_transition_failed` hook. That is the
fix, and it covers every action slot we tested including `start()`'s initial entry.
Thank you — this was the defect that shaped our entire mitigation stack.

Three things we found while adopting it that we think belong in the docs rather
than in an open issue:

**1. `rollback` is a context + configuration transaction, not an effect
transaction.** An outward effect emitted by an earlier action in the same list
survives the rollback. Verified with controls (a control run first proved the
effect happens at all):

* a `raise`d event queued before the failing action is still delivered —
  `seen=['PING']` while the configuration correctly rolls back to `rs.a`;
* a `sendTo` to a child invoked on a *surviving* state still lands —
  `hits=1` after a full rollback, against a control that shows one hit is the
  normal delivery count;
* both escape under `"fail"` too (machine reaches `status=error` *and* the event
  was delivered).

This is self-consistent behaviour and arguably the only tractable one — but the
word "rollback" invites the stronger reading. For an order machine the
consequence is concrete: if the failing entry action runs *after* a `sendTo` that
told a risk actor "order is live", the machine returns to `idle` while the risk
actor believes an order exists. A sentence in the guide saying rollback covers
**context and configuration only, never already-emitted effects**, plus the
design rule that the outward-facing action goes last (or on the entry of the
committed state), would have saved us a probe.

**2. The one-shot `DeprecationWarning` is per-`MachineNode`, not per-process.**
`_apply_action_error_policy` sets `machine.action_error_policy_is_default = False`
on the shared node, so a process that builds interpreters per request from a
module-level machine warns exactly once, ever — very likely in a warm-up path
nobody reads. Intentional per the comment, but given that this warning heralds a
**default flip in 1.0**, the signal is much quieter than the migration. Consider
warning once per *process*, or emitting at `create_machine()` time.

**3. `rollback` costs ~22% throughput while armed and idle.** Measured on the
same 5-state machine and event cycle, machinery armed but never triggered (no
action raises, every event handled):

| Variant | ev/s | vs baseline |
|---|---:|---:|
| defaults | 35,532 | 1.00x |
| `actionErrorPolicy="rollback"` | 27,586 | **0.776x** |
| `onUnhandled="defer"` | 34,936 | 0.983x |
| both | 27,469 | 0.773x |

That is the per-transition checkpoint (context deep-copy + configuration
snapshot) running on every event, unamortised. `defer` by contrast is nearly free
when nothing defers. Since 1.0 flips this default, users will take the 22% whether
or not they read the changelog — worth a line in the production-characteristics
page next to the throughput budget, and possibly worth a cheaper checkpoint
(copy-on-write context, or skipping the snapshot when the transition's action
list is empty).

**4. `on_transition_failed` fires twice for one transition under `"continue"`**
when both the transition's own action and the target's entry action raise:
`[('bo.a', 1), ('bo.a', 1)]`, one call per action slot. Under `rollback`/`fail`
it is one, since the first failure raises out. Defensible, but an alerting
consumer has to dedupe, so it is worth stating.

**Environment:** 0.8.0 @ `9bf6065`, `pip install -e .`, CPython 3.13.7, Windows 11
x64. Probes: `probes/v080/a_rollback.py` (15/17), `a_rollback_followup.py` (3/5),
`a12_sendto_redo.py`, `bench_j_policies.py`.

--
author:	basiltt
association:	owner
edited:	false
status:	none
--
Reopening: the follow-up above identifies a behavioural gap in the fix itself — `actionErrorPolicy: "rollback"` restores configuration and context but a `raise` / `sendTo` emitted by an earlier action in the same list is not undone, so a rolled-back machine can leave a live side-effect (child actor, queued internal event) behind. Either the rollback should cancel pending built-in effects raised within the failed action list, or the docs should rename/scope the guarantee explicitly. The per-`MachineNode` one-shot `DeprecationWarning` (fires once per process) is a secondary item.
--
