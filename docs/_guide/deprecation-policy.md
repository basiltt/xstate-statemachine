---
title: "Deprecation Policy"
description: "What SemVer covers, how long a deprecation warns before removal, and every current deprecation."
---

# Deprecation Policy

`xstate-statemachine` follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html). This page says exactly what that promise covers and how a public API is retired.

## What is covered

| Surface | Stability from 1.0 |
|:--|:--|
| **Core**: everything importable from `xstate_statemachine`, the JSON machine format, the `xsm` CLI, `PluginBase` hooks | **SemVer.** Breaking changes only in a new major. |
| **Persistence**: `xstate_statemachine.persistence`, the snapshot layout (`SNAPSHOT_VERSION` + `upcast()`) | **SemVer.** A snapshot written by 1.x loads on every later 1.x. |
| **Contrib**: `xstate_statemachine.contrib.*` (every pip extra) | **Provisional** until 1.0, and still provisional *in* 1.0. A minor release may change a contrib API. It still warns first when it can, and the change is always listed under **Changed** in the changelog. |
| Anything with a leading underscore, and `events.engine_*` | Private. No promise. |

Contrib stays provisional because it tracks third-party frameworks whose own APIs move. Pin a minor range (`xstate-statemachine[fastapi]>=1.0,<1.1`) if you need contrib to stand still.

## How something is retired

1. **Warn for at least one minor release.** The deprecated name keeps working and emits a `DeprecationWarning`. The message names what is deprecated, the release it was deprecated in, the earliest release that removes it, and what to use instead.
2. **Remove it no earlier than the next major.** Something deprecated in 1.3 is removed in 2.0 at the earliest, never in 1.4.
3. **Record it in the changelog.** The **Deprecated** section gets an entry when the warning is added, and **Removed** gets one when the name goes.

Warnings are emitted **once per call site**. A loop that touches a deprecated attribute a million times warns once, but every distinct line of your code that uses it gets its own warning. To find all of them, run your tests with warnings as errors:

```bash
python -W error::DeprecationWarning -m pytest
```

Library code uses a single helper, so every message has the same shape:

```python
import warnings

from xstate_statemachine.deprecations import deprecated, deprecations

def old_name():
    deprecated("old_name()", since="1.2.0", removal="2.0", alternative="new_name()")

with warnings.catch_warnings(record=True) as caught:
    warnings.simplefilter("always")
    for _ in range(3):
        old_name()          # one call site -> one warning
assert len(caught) == 1
assert any(d.what == "ErrorEvent.data" for d in deprecations())
```

## Current deprecations

These are pre-1.0 deprecations. The 1.0 release is the major in which they are removed. `xstate_statemachine.deprecations.deprecations()` returns the same list, and a test keeps this table in sync with it.

| Deprecated | Since | Removed in | Use instead |
|:--|:--|:--|:--|
| `--style` (CLI flag) | 0.4.1 | 1.0 | `--template` |
| `ErrorEvent.data` | 0.9.0 | 1.0 | `ErrorEvent.error` |
| `xstate_statemachine.events.engine_done`, `xstate_statemachine.events.engine_error`, `xstate_statemachine.events.engine_after` | 0.9.0 | 1.0 | Nothing. These are internal, and `_engine_*` is private. |
| `leading-dot sibling target fallback` (`".sibling"` resolving to a sibling) | 0.8.0 | 1.0 | `"#<state id>"`, or `"strictTargets": true` |
| `strict_targets=False` (unresolvable targets as silent no-ops) | 0.8.0 | 1.0 | Fix the unresolvable targets |
| `implicit actionErrorPolicy default 'continue'` | 0.8.0 | 1.0, when the default becomes `'rollback'` | An explicit `"actionErrorPolicy"` on every machine |
| `reserved send() keywords in a dict-form payload` (`wait`, `priority`) | 0.4.1 | 1.0 | Renamed payload keys |

The `actionErrorPolicy` default warning fires once per **process** rather than once per call site. It reports a machine-level default, not a line of your code.
