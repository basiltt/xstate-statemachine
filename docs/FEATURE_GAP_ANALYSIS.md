# XState Feature Gap Analysis

**Subject**: `xstate-statemachine` (Python) v0.5.1 vs `xstate` (JS/TS) v5.32.5
**Date**: 2026-08-07
**Method**: 4 parallel research streams over the XState changelog, npm registry and Stately docs; every claimed gap then verified **empirically** by executing Python against this library. 73 features were individually probed.
**Status**: ✅ All gaps resolved in v0.6.0.

> ## ✅ STATUS: RESOLVED IN v0.6.0
>
> Every gap in this document was closed in **v0.6.0** (2026-08-08) and is
> covered by `tests/test_xstate_v5_parity.py` (114 tests). See the `[0.6.0]`
> entry in `CHANGELOG.md` for the full list and for the behaviour changes it
> introduces.
>
> This report is retained as the historical record of *why* each change was
> made — the reasoning and the reproduction evidence remain the best guide to
> the design decisions in the implementation.


---

## 1. Executive Summary

XState v5.0.0 shipped **2023-12-01**; the current stable is **5.32.5** (published 2026-07-14). A v6 alpha line exists (`6.0.0-alpha.27`) but is **not** released.

The single most important finding for planning:

> **The gap is not primarily "the last 2 years". It is the v5.0 big bang.**
> Everything from mid-2024 → 2026-08 (v5.15 → v5.32.5) was **non-breaking minors and patches**. The features this library is missing are overwhelmingly from the **v5.0 rewrite of Dec 2023**, plus a set of **v4-era primitives that were never implemented at all** (history, tags, meta, wildcards).

The second finding is more urgent than any missing feature:

> **Roughly two-thirds of the gaps fail *silently*.** Valid XState JSON — config a user could copy straight from the Stately docs — is accepted without error and then ignored, or it kills the async interpreter with an unretrieved task exception. A user gets wrong behaviour, not a diagnostic.

### Scale

| | Count |
|---|---|
| Features probed | 73 |
| Supported | 1 |
| Partial | 17 |
| **Missing — silent (dangerous)** | **34** |
| Missing — loud error (safe) | 21 |

### Severity

| Impact | Count | Nature |
|---|---|---|
| **CRITICAL** | 8 | Data loss, silent wrong behaviour, or a dead interpreter |
| **HIGH** | 24 | Core statechart semantics or actor-model capability absent |
| **MEDIUM** | 30 | Ergonomics, tooling, introspection |
| **LOW** | 11 | Niche or JS-specific |

---

## 2. The Headline Risk: Silent Failure

This deserves separate billing because it changes the priority order. Five classes of *valid XState config* are accepted and then produce wrong behaviour with no error:

### 2.1 `cond` guards fire unconditionally 🔴 CRITICAL

The v4 spelling `cond` is not read — only `guard` is. A guarded transition written the v4 way **takes the transition regardless of the predicate**.

```python
{"on": {"E": {"target": "b", "cond": "isReady"}}}   # isReady is NEVER called
# Observed: transitions to b even when the guard would return False.
```

This is the worst defect in the library: it silently inverts safety logic. Any machine copied from a v4 codebase or an older tutorial is affected.

### 2.2 Object-form guards kill the async interpreter 🔴 CRITICAL

Standard v5 syntax `{"type": "g", "params": {...}}` — and every higher-order guard (`and`/`or`/`not`/`stateIn`) — is used directly as a dict key:

```
TypeError: cannot use 'dict' as a dict key (unhashable type: 'dict')
  at base_interpreter.py:1478  ->  self.machine.logic.guards.get(guard_name)
```

In `SyncInterpreter` this surfaces to the caller. In the **async `Interpreter` the exception dies inside the event-loop task** ("Task exception was never retrieved"): the machine is permanently dead, every later `send()` is dropped, and `status` still reads `"running"`.

### 2.3 History states strand the machine 🔴 HIGH

`{"type": "history"}` parses as a plain **atomic** state with no warning. Targeting it parks the machine *in the history node itself*:

```
send("OUT"); send("BACK")  ->  {'m.p.h'}    # expected: {'m.p.c1'}
```

### 2.4 Child actors are dropped from snapshots 🔴 CRITICAL

`get_snapshot()` emits only `{status, context, state_ids}`. A parent with a live spawned child serialises to:

```json
{"status":"running","context":{"pn":1},"state_ids":["p.a"]}
```

Restoring gives `_actors: 0`. **The entire actor hierarchy is lost with no error and no warning** — genuine data loss for anyone persisting a workflow.

### 2.5 Silently ignored keys

Accepted at parse time, dropped entirely, no warning:

| Key | Consequence |
|---|---|
| `always` (top-level v5 spelling) | Eventless transition never fires. Legacy `on: {"": ...}` does work. |
| `tags` | No `hasTag()`; UI-state modelling impossible |
| `meta` | No `getMeta()` |
| `description` | Lost |
| `output` (final/machine) | No done-data; `onDone` carries nothing |
| `delimiter` | IDs always joined with `.` |
| `on: {"*": ...}` | Wildcard never matches |
| `on: {"mouse.*": ...}` | Partial descriptor never matches |
| `on: {E: None}` | Forbidden transition does not block the ancestor |
| dynamic `params` (a function) | Passed through verbatim, never called |
| `context` as a factory function | Runtime context becomes the raw function object |

---

## 3. Missing v5.0 Features (Dec 2023) — The Main Body of Work

### 3.1 Action creators — the largest single gap 🔴 CRITICAL

**None** of the v5 action creators exist. There is no way to express inter-actor messaging declaratively:

| Missing | Purpose |
|---|---|
| `raise` | Send an internal event to self |
| `sendTo` | Send to a specific actor |
| `sendParent` | Send to the parent actor |
| `forwardTo` | Forward the current event onward |
| `escalate` | Escalate an error to the parent |
| `log` | Declarative logging |
| `cancel` | Cancel a delayed send by id |
| `stopChild` | Stop a spawned/invoked child |
| `spawnChild` | Spawn outside an assign |
| `emit` *(v5.9.0)* | Emit an event to external listeners |
| `enqueueActions` | Conditional/imperative action batching (replaced `pure`/`choose`) |

**Today the only mechanism is a user action mutating context directly.** Verified: an action *can* call `interpreter.send()`, so `raise`/`sendTo` are implementable — the primitives exist, the declarative surface does not.

Probing these object forms yields `ImplementationMissingError` on `SyncInterpreter` (safe) but **silently destroys the async `Interpreter`** (`current_state_ids` becomes `set()`).

### 3.2 Guards 🔴 CRITICAL

Only plain named predicates. Missing: `and()` / `or()` / `not()` composition, `stateIn()`, parameterised guards, and dynamic params. All object forms crash (§2.2).

### 3.3 `input` / `output` 🔴 CRITICAL

- `Interpreter(machine, input={...})` → `TypeError: unexpected keyword argument 'input'`
- `context` as a factory receiving input → silently stored as a function object
- Machine-level and final-state `output` → dropped

This blocks the entire "parameterise an actor at spawn, collect a result at completion" workflow — the backbone of v5 actor composition.

### 3.4 Actor system 🟠 HIGH

Missing `systemId`, `system.get()` (receptionist lookup), `system.getAll()` *(v5.23.0)*. Actors can be spawned but not addressed by name, so sibling-to-sibling messaging is impossible.

### 3.5 Actor logic creators 🟠 HIGH

XState treats *actor logic* as the unit of execution. This library only accepts a callable or a `MachineNode` as `src`.

| Creator | Status |
|---|---|
| `fromPromise` | **Partial** — an `async def` service works |
| `fromCallback` | **Partial** — no send-back channel |
| `fromTransition` | Missing |
| `fromObservable` / `fromEventObservable` | Missing |

⚠️ **Asymmetry found**: a *synchronous* function as `src` works in `SyncInterpreter` but **never completes** in the async `Interpreter` — the machine sits in the invoking state forever, silently.

### 3.6 Error snapshots 🔴 CRITICAL

`status` is only ever `uninitialized` / `running` / `stopped` — never `"error"`. An unhandled service failure logs and the machine **keeps running as if nothing happened**. There is no `snapshot.error`, no `subscribe()` error callback, and no `onError` at machine level.

### 3.7 Observation & introspection 🟠 HIGH

Absent: `subscribe()`, `matches()`, `hasTag()`, `can()`, `toPromise()`, `waitFor()`. Also `status` never becomes `"done"` on reaching a top-level final state, so completion is not observable — which blocks even a user-space `toPromise` workaround.

The plugin surface (`PluginBase`) is a reasonable inspection substitute, but it is push-only and this-library-specific.

---

## 4. Features From the Last ~2 Years (v5.15 → v5.32.5)

Accurate answer to "what shipped recently": **no breaking changes in the entire window.** Notable additions:

| Version | Date | Feature | Portable |
|---|---|---|---|
| v5.9.0 | 2024 | **`emit()` + event emitters** (`actor.on()`) | Yes |
| v5.13.0 | 2024 | `fromPromise` receives an `AbortSignal` | Yes |
| v5.13.1 | 2024 | Wildcard emitted-event listener `actor.on('*')` | Yes |
| v5.14.0 | 2024 | `emit()` in all actor logic creators; `actorId` on done/error | Partial |
| v5.19.0 | 2025 | **`transition()` / `initialTransition()`** — pure, actor-free reducers | Yes |
| v5.19.3 | 2025 | History value persistence/restoration | Yes |
| v5.20.0 | 2025 | **`xstate/graph` moved into core** (model-based testing) | Yes |
| v5.20.2 | 2025 | emit listener errors no longer crash the actor | Yes |
| v5.21–24 | 2025 | `setup.extend()`, `createAction()`, type-bound helpers | JS-specific |
| v5.23.0 | 2025 | `system.getAll()` | Yes |
| v5.26.0 | 2025 | `getNextTransitions(state)` | Yes |
| v5.27.0 | 2025 | `getMicrosteps()` / `getInitialMicrosteps()` | Yes |
| v5.28.0 | 2026 | **Routable states** (`xstate.route`) | Partial |
| v5.29.0 | 2026 | `actor.select(selector, equalityFn?)` | Yes |
| v5.31.0 | 2026 | `mapState()`, **`maxIterations`** infinite-loop detection | Yes |
| v5.32.4 | 2026 | History into parallel states fixed | Yes |

**Most valuable recent items for a Python port**, in order:

1. **`transition()` / `initialTransition()`** (v5.19.0) — pure functions mapping `(state, event) → (nextState, actions)` with no running actor. Trivially portable, hugely useful for testing, and would let this library expose a reducer-style API.
2. **`emit()` + listeners** (v5.9.0) — a clean way for a machine to talk to the outside world without a plugin.
3. **`maxIterations`** (v5.31.0) — cheap safety net; this library's `always` loop can currently spin forever.
4. **`xstate/graph`** (v5.20.0) — shortest/simple path generation for model-based testing.

---

## 5. Older Features Never Implemented (pre-v5)

These are **not** recent — they predate v5 and were simply never built:

| Feature | Era | Status |
|---|---|---|
| **History states** (shallow + deep) | v3/v4 | Parses as atomic; strands the machine |
| **Wildcard `*` descriptors** | v4 | Never matches |
| **Partial descriptors** (`mouse.*`) | v4 | Never matches |
| **Forbidden transitions** (`E: undefined`) | v4 | Ancestor still fires |
| **`tags`** | v4 | Dropped |
| **`meta`** | v4 | Dropped |
| **`cond` (guard spelling)** | v4 | Ignored → fires unconditionally 🔴 |
| **`delimiter`** | v4 | Ignored |
| **Named/expression delays** (`after: {DELAY: ...}`) | v4 | Raises `ValueError` |
| **`state.matches()` / `.can()` / `.nextEvents`** | v4 | Absent |
| **`assign()` helper** | v4 | Direct mutation only |

---

## 6. What This Library Does Well

Worth stating plainly, because the gap list is long:

- **Transition selection is now SCXML-correct** — one transition per parallel region, deepest-source-first, with guard memoisation. (Fixed in the v0.5.1 correctness pass.)
- Atomic / compound / parallel / final states, `initial`, `entry`/`exit`, targetless and internal transitions, `reenter`.
- `after` timers (integer ms) in **both** engines, cancelled correctly on exit.
- `invoke` with `onDone`/`onError`/`input`; `onDone` for compound and parallel.
- Actor spawning with cascading `stop()`.
- **Dual sync/async engines** — XState has no threaded equivalent.
- **Beyond XState**: a Pythonic DSL (`StateMachine`/`MachineBuilder`/decorators), `LogicLoader` camelCase↔snake_case auto-discovery, a plugin surface, Mermaid/PlantUML export, and an `xsm` codegen CLI with 5 templates.

Safe (loud) failure modes already in place: `NotSupportedError` for async services under `SyncInterpreter`, `ImplementationMissingError` for missing logic, `StateNotFoundError` for bad targets, `InvalidConfigError` for malformed configs.

---

## 7. Recommended Priority

Ordered by **risk × effort**, not by XState version.

### Tier 0 — Correctness bugs (do first; small effort, silent wrongness today)

| # | Item | Effort |
|---|---|---|
| 1 | Support `cond` as an alias for `guard` (or reject it loudly) | XS |
| 2 | Fix object-form guard crash — normalise `{"type","params"}` before lookup | S |
| 3 | Warn or raise on unknown/unsupported config keys (`tags`, `meta`, `always`, `history`, `output`, `delimiter`) — convert silent to loud | S |
| 4 | Compound state missing `initial` → raise instead of starting with an empty active set | XS |
| 5 | Sync function as `src` in async `Interpreter` → currently hangs forever | S |

*Tier 0 alone removes 5 silent-wrongness classes for very little code.*

### Tier 1 — Core statechart parity

| # | Item | Effort |
|---|---|---|
| 6 | **History states** (shallow + deep) incl. persistence | M |
| 7 | **Wildcard + partial event descriptors** | S |
| 8 | Top-level **`always`** key | XS |
| 9 | **`tags`** + `has_tag()`, **`meta`** + `get_meta()` | S |
| 10 | **`output`** / done-data + `status == "done"` | M |
| 11 | Forbidden transitions (`E: None`) | S |
| 12 | Named/expression delays | S |

### Tier 2 — Actions & guards DSL

| # | Item | Effort |
|---|---|---|
| 13 | `raise`, `send_to`, `send_parent`, `forward_to`, `log`, `cancel`, `stop_child` | M |
| 14 | Higher-order guards `and`/`or`/`not` + `state_in` | S |
| 15 | `enqueue_actions()` — subsumes `pure`/`choose` and much of the above | M |
| 16 | Dynamic (callable) params for actions and guards | S |

### Tier 3 — Actor model & lifecycle

| # | Item | Effort |
|---|---|---|
| 17 | **Deep persistence of child actors** (data loss today) | L |
| 18 | `input` at actor creation + context factories | M |
| 19 | Error snapshots — `status == "error"`, `snapshot.error` | M |
| 20 | Actor system: `system_id` + `system.get()` | M |
| 21 | `subscribe()`, `matches()`, `can()`, `wait_for()`, `to_promise()` | M |

### Tier 4 — Recent-era additions

| # | Item | Effort |
|---|---|---|
| 22 | `transition()` / `initial_transition()` pure API | S |
| 23 | `emit()` + listeners | M |
| 24 | `max_iterations` loop guard | XS |
| 25 | Graph/model-based testing helpers | L |

**Explicitly out of scope** (JS/TS-specific): `setup()` type inference, `createStateConfig`, typegen, `setup.extend()`, `@statelyai/inspect` browser adapter. The *runtime* half of `setup()` — a validated registry of named actions/guards/actors — **is** portable and would catch the whole missing-implementation class at build time.

---

## 8. Suggested Release Shape

- **v0.5.2 (patch)** — Tier 0 only. Pure correctness; no new surface.
- **v0.6.0 (minor)** — Tiers 1–2. Statechart parity + action/guard DSL. The `--style` CLI flag is already slated for removal here.
- **v0.7.0** — Tier 3. Actor model, persistence, error snapshots. Biggest architectural lift.
- **v0.8.0** — Tier 4. Modern conveniences and testing tools.

---

## 9. Method & Confidence

**Sources read directly**: `packages/core/CHANGELOG.md` on `main` (raw.githubusercontent.com), the npm registry metadata for `xstate` (exact publish dates and dist-tags), the GitHub Releases API, and `stately.ai/docs`.

**Every gap in this report was verified by running Python against this library**, not inferred from reading source. Where a research claim conflicted with observed behaviour, the observation won — one example: an early claim that `always` never runs at machine start was **disproved** (legacy `on: {"": ...}` *does* fire at start); only the top-level `always` spelling is unsupported.

**Confidence levels**:

- **High** — all local capability findings (directly executed, reproducible).
- **High** — v5.0 feature set and the current version/date (corroborated across changelog + npm + docs).
- **Medium** — individual minor-version attributions for v5.19+ were read via summarising fetch rather than line-by-line; re-verify a specific version before relying on it.
- **Flagged** — v5.28+ items (routable states, `mapState`, `getMicrosteps`) are newer and lightly documented on stately.ai: shipped per changelog, but thinly documented.

**Known limitation**: the 73 probed features are those surfaced by the research streams. Rarely-used v4 corners may exist that were not probed.
