# Bug/Docs: user events named `error.*` or `done.*` are invisible to a `\"*\"` handler and exempt from `onUnhandled: \"error\"`


## Summary

`_matching_descriptors` exempts the prefixes
`("done.", "error.", "after.", "xstate.", "___xstate")` from wildcard and partial
descriptor matching, so the engine can distinguish its own synthesised lifecycle
events from user traffic. That exemption list is now load-bearing in three
places — the matcher, the `onUnhandled` policy, and `_check_strict`.

The user-facing consequence is undocumented and is a silent drop: an application
event that happens to live in one of those namespaces is invisible to a `"*"`
handler and exempt from `onUnhandled: "error"`.

This is the same failure class 0.8.0 set out to eliminate, reachable purely by
choosing an unlucky event name.

## Environment

- Library: `xstate-statemachine` 0.8.0, commit `9bf6065`, local clone, `pip install -e .`
- Python: 3.13.7 (CPython, MSC v.1944 64-bit)
- OS: Windows 11 x64 (10.0.26200)

## Minimal reproduction

```python
import asyncio
from xstate_statemachine import Interpreter, MachineLogic, create_machine

CFG = {"id": "wc", "initial": "a", "context": {"caught": []},
       "states": {"a": {"on": {"*": {"actions": ["note"]}}}}}

def note(interp, ctx, event, action):
    ctx["caught"].append(event.type)

async def main():
    i = Interpreter(create_machine(CFG, logic=MachineLogic(actions={"note": note})))
    await i.start()
    for ev in ("PLAIN", "error.myapp.validation", "done.review", "my.namespaced"):
        await i.send(ev)
    await asyncio.sleep(0.05)
    print(i.context["caught"])
    # -> ['PLAIN', 'my.namespaced']    two events vanished

asyncio.run(main())
```

Full script, including the `onUnhandled: "error"` half:
`repro/N-08_error-done-namespace-invisible.py` (exits 1 while present, 0 once
fixed).

## Observed

```
OBSERVED '*' handler caught        : ['PLAIN', 'my.namespaced']
EXPECTED '*' handler caught        : ['PLAIN', 'error.myapp.validation', 'done.review', 'my.namespaced']
OBSERVED onUnhandled='error' UNKNOWN_PLAIN         : stopped
OBSERVED onUnhandled='error' done.review           : no error
OBSERVED onUnhandled='error' error.validation      : no error
OBSERVED invisible to '*'          : ['error.myapp.validation', 'done.review']
OBSERVED exempt from onUnhandled   : ['done.review', 'error.validation']
RESULT: DEFECT REPRODUCED
```

The `my.namespaced` control is the important one: a dotted user event name is
matched by `"*"` perfectly well. Only the four reserved prefixes are swallowed.
And the `UNKNOWN_PLAIN` control confirms `onUnhandled: "error"` is genuinely
armed on that machine — it stops the interpreter as designed.

## Expected

One of:

1. **Preferred** — the exemption applies only to events the engine actually
   synthesised (which it knows, since it minted them), not to anything whose
   *name* matches a prefix. A user-sent `done.review` is user traffic.
2. Or — `create_machine()` **rejects** user-declared event names in the reserved
   namespaces at build time, with a message naming the reserved prefixes. This
   release's whole direction is build-time rejection over runtime silence, and it
   would be entirely consistent.
3. Or, at minimum — document the reserved prefixes prominently in the events
   guide, the `onUnhandled` section and the strict-mode section, since all three
   depend on the list.

Option 1 is correct; option 2 is a fine pragmatic answer; option 3 alone leaves a
silent drop in place.

## Root cause

`models.py::_matching_descriptors`. The system-event exemption is a **prefix
test on the event name string**, not a check of provenance:

```python
if event_type.startswith(("done.", "error.", "after.", "xstate.", "___xstate")):
    ...  # exempt from wildcard / partial matching
```

0.7.0 had the first four; 0.8.0 added `"___xstate"` (benign and correct — the
init/exit sentinels). The addition itself is fine; the issue is that the
mechanism it extends now also gates `onUnhandled` and `_check_strict`, so one
undocumented string list silently governs three user-visible behaviours.

## Impact

Any domain that naturally names events in these namespaces:

- review/approval workflows — `done.review`, `done.approval`
- validation pipelines — `error.validation`, `error.schema`
- job runners — `done.job`, `error.retry`

all of which are idiomatic, and none of which will produce any diagnostic. The
event is accepted by `send()`, counted as delivered, and dropped. Under
`onUnhandled: "error"` — the setting a user chooses *specifically* to make
unhandled events loud — it stays silent.

For CandleViewer we have banned these names by lint rule, which is a fine
workaround but only because we found it by reading the diff.

## Suggested fix

Tag engine-synthesised events at mint time (an `_internal: bool` on the event
envelope, or a distinct subclass) and test that flag in `_matching_descriptors`,
`_handle_unhandled_event` and `_check_strict`, instead of prefix-matching the
name. The prefix list can remain as a fallback for events restored from a 0.7.x
snapshot.

Add a `create_machine()` warning (not an error, for compatibility) when a machine
declares an `on:` key in a reserved namespace, since that is a strong signal the
author expects user-event semantics.

## Acceptance criteria

- [ ] `repro/N-08_error-done-namespace-invisible.py` exits 0.
- [ ] A user-sent `error.myapp.validation` matches `on: {"*": ...}`.
- [ ] A user-sent, unhandled `done.review` trips `onUnhandled: "error"`.
- [ ] Engine-synthesised `done.invoke.*` / `error.platform.*` / `after.*` /
      `xstate.*` remain exempt — no regression to the 0.8.0 `Fixed` entry about
      `escalate` and `onUnhandled: "error"`.
- [ ] The reserved prefixes are documented in the events guide, the `onUnhandled`
      section and the strict-mode section.
- [ ] Tests added:
  - `tests/test_events.py::test_user_event_in_reserved_namespace_matches_wildcard`
  - `tests/test_events.py::test_user_event_in_reserved_namespace_trips_onunhandled_error`
  - `tests/test_events.py::test_engine_synthesised_events_remain_exempt`

## Related

- `#28` (LC-03) — `onUnhandled`. Verified 9/9 otherwise; this is the one gap, and
  it is in the policy's own exemption logic rather than in the policy.
- `#51` (LC-34) — strict mode, which consults the same list.
- The 0.8.0 `Fixed` entry treating engine-synthesised `xstate.*` events as system
  events for `onUnhandled` — the right fix, built on the wrong mechanism.

## Verification

Independently verified on 2026-09-17.

- Library: 0.8.0, commit `9bf6065`, local clone, `pip install -e .`.
- Python 3.13.7, Windows 11 x64.
- Repro run in a fresh process → **exit 1**, output as quoted.
- Controls in the same run: `PLAIN` and `my.namespaced` both match `"*"`
  (so wildcard matching works and dotted names are not the problem), and
  `UNKNOWN_PLAIN` trips `onUnhandled: "error"` (so the policy is armed).


---
Found while re-verifying the 0.8.0 release against the adoption-readiness checklist in #26. Self-contained repro attached in the body; exits 1 while the defect is present, 0 once fixed.

