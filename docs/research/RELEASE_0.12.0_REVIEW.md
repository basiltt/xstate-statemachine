# 0.12.0 release review: full change summary, breaking changes, XState v5 alignment

**Date:** 2026-11-05
**Subject:** `xstate-statemachine` 0.12.0 (unreleased; branch `xstate-v5-engine-parity`, HEAD `0f5dca2f`) versus the last published release 0.11.0 (tag `v0.11.0` = `origin/main` = `1b215012`, 2026-10-13).
**Method:** commit-by-commit reading of `git log v0.11.0..HEAD` and both changelog blocks; four parallel breaking-change audits of the diff (engine, Pythonic DSL, public API surface, release documentation) with every CRITICAL/HIGH finding adversarially re-checked by two independent reviewers, one reading code and one running the same script against a v0.11.0 worktree and this tree; four parallel XState v5 alignment streams (web research on XState's current state, empirical probes against a real `xstate@5.33.3` under Node, a feature inventory from the Stately docs, and a review of the shared conformance evidence). Sections 3 to 6 are the verified results of those streams.

> **Status, 2026-11-05 (same day, after the review).** Three of the pre-tag items in section 5 were applied on the branch, uncommitted:
> item 1, B2 is fixed in `src/xstate_statemachine/_pythonic_runtime.py` (a legacy-arity callback, extra defaulted parameters after the shape included, is called positionally unless it asks for injection, a default outside the trailing `params` / `action_def` slot, a keyword-only parameter, `**kwargs` or a payload field named like one of its parameters, and every parameter without a default can be supplied by name; a signature with no engine name that asked for injection and whose payload names some parameters but not a required one keeps a loud `TypeError`; 16 regression tests in `tests/test_pythonic_dsl_v2.py::TestLegacyShapesStayPositional`), so B2 is no longer a breaking change and the injection bullet in the changelog describes the rule and its two remaining ambiguities;
> items 2 and 3, `[Unreleased]` is folded into `## [0.12.0] - 2026-11-05` (the date is a placeholder for the publish day) with a behaviour-changes callout, the services bullet rewritten, the revert bullet removed, and new bullets for B3, B10, B12, U1, U2 and the dropped `pythonic` re-exports; `docs/_guide/changelog.md` mirrors it;
> item 4 in part, the five `stop()` sentences in `docs/_guide/interpreters.md`, the "Up to 0.12" wording and the `_invoke_input` docstring. Not applied, left to the maintainer: softening "100 % XState JSON compatible", the deprecation-policy sentence, items 5 to 7.

---

## 1. Scope of the release

| Fact | Value |
|:--|:--|
| Baseline | `v0.11.0` (2026-10-13), the latest release on PyPI |
| Head | `0f5dca2f`, 37 commits ahead of `origin/main` |
| Size | 88 files, +14,528 / -5,891 lines; `src/`: 19 files, +5,589 / -2,448 |
| Version strings | `pyproject.toml` and `__version__` already read `0.12.0` |
| Changelog | Two blocks ship together: `## [0.12.0] - 2026-10-20` (drafted on 2026-10-20, never published) and `## [Unreleased]` (the engine-parity work on top of it) |
| Snapshot layout | v4, unchanged (`SNAPSHOT_VERSION` and `upcast()` untouched in the range) |
| Branch state | Not pushed, no pull request yet |

0.12.0 was prepared once ("chore: prepare 0.12.0 (not published)", `67534cd8`) and then the XState v5 engine-parity series landed on top. Everything below the `[Unreleased]` heading in `CHANGELOG.md` therefore belongs to 0.12.0 too; the release notes have to present both blocks as one release (see section 5).

---

## 2. What changed, by theme

### 2.1 Statechart engine: XState v5 parity (18 behaviour changes and one revert)

Every item was checked against `xstate@5.33.3` through the conformance cases the Rust port shares with this library (`tests/test_xstate_conformance_cases.py` replays the 50 JSON cases). Both engines change together.

| # | Change | Commit | Shared conformance case(s) |
|:--|:--|:--|:--|
| 1 | Exit actions run in reverse document order, one region at a time (descendants before ancestors; the region declared last exits first) | `a5778502` | `020_exit_order_reverse_document` |
| 2 | States are entered in document order (the whole entry set is computed first) | `a773ada9` | `021_parallel_entry_order` |
| 3 | A transition into a sibling region has the parallel state as its domain: every region exits and re-enters, the parallel state itself does not | `83b326a6` | `028_parallel_cross_region_target`, `023_parallel_cross_region_conflict` |
| 4 | `reenter: true` moves the domain above the source even when the target is the source's own child; a re-entering root transition re-runs the root's `exit`/`entry` | `3185562d` | `030_reenter_descendant_target`, `017_reenter_self_transition` |
| 5 | Completing the machine runs the remaining `exit` actions (final state and root included), after `output` is resolved | `9b175644` | `029_exit_actions_on_completion` |
| 6 | `"*"` and `"prefix.*"` descriptors now also match engine events (`done.invoke.*`, `error.platform.*`, `after.*`, `done.state.*`) | `feb75963` | `027_wildcard_vs_engine_events` |
| 7 | Multi-target transitions into different regions of one parallel state (`"target": [..]`); any other list is still `InvalidConfigError`; `TransitionDefinition.target_strs` / `resolved_targets` added | `e941cfa2` | `031_multi_target_parallel_entry` |
| 8 | A JSON `choose` runs its first matching branch (`params.branches`, composite and `stateIn` guards); `stateIn` also reads `params.stateValue` | `4a6ffc25` | `032_choose_and_state_in` |
| 9 | All transitions taken for one event form one microstep (all exits, then all actions, then all entries); conflicting transitions are dropped as XState's `removeConflictingTransitions` does; rollback undoes the whole microstep | `9c34bfcb` | `022_parallel_conflict_preemption`, `038_conflict_document_order_preemption`, `039_microstep_groups_exit_actions_entry`, `040_eventless_descendant_preempts_ancestor` |
| 10 | `done.state.*` is an internal event (handled before queued external events; withdrawn by a rollback; counted by `maxIterations`) | `4666d9b7` | `024_done_state_queue_order`, `041_done_state_before_queued_external_event` |
| 11 | Transition selection and guard evaluation follow XState's `selectTransitions` / `selectEventlessTransitions` (order and count of guard evaluations change; `can()` evaluates exactly what `send()` would; `stub_logic(guard_log=)` added) | `182021cc` | `042_guard_evaluation_order` |
| 12 | One `assign` resolves every property against the context before it (keys can swap without a temporary); consecutive assigns still see each other | `1d4c1c8c` | `043_assign_actions_apply_in_order` |
| 13 | A compound or parallel state targeting itself without `reenter` exits its active children and re-enters its `initial` child; the state itself stays | `c029d485` | `044_compound_self_target_without_reenter` |
| 14 | A JSON `assign` without the `assignment` wrapper (`{"type": "xstate.assign", "params": {"count": 1}}`) updates the context instead of being ignored | `efbc94f7` | `045_assign_without_assignment_wrapper` |
| 15 | `always` transitions are checked in the order their states were entered, not document order (changes which of two conflicting region `always` wins) | `fc935be4` | `046_always_order_follows_entry_order`, `050_always_order_after_reentry` |
| 16 | History is recorded only when the history node's owner state is exited | `0a8e006e` | `047_history_records_only_on_owner_exit` |
| 17 | An eventless microstep that changed nothing is not re-selected (an `always` self-target or a targetless `always` with a plain action runs once per step instead of tripping `RunawayChainError`) | `2dff0dbc` | `048_always_self_target` |
| 18 | `done.state.*` is raised for the states XState notifies: the compound parent, then every parallel ancestor whose regions are all final; a parallel root completes the machine | `0f5dca2f` | `049_done_state_propagation`, `025_nested_final_ondone_propagation` |
| R | **Revert** of the unpublished 0.12.0 shortcut: an `invoke` with no declared `input` passes the actor `{}` again (XState passes `undefined`); a declared `input` factory still sees the triggering event; new `event_payload` helper and `@state.service(input=event_payload)` | `8438aeca` | `018_invoke_ondone`, `026_ancestor_handler_and_payload` |

Supporting commits in the same series: the shared-case replay test (`51aa06c3`), tolerance of a second import of the package in target handling (`45546e0f`), the microstep documentation in `docs/_guide/parallel.md` (`c622a33b`, `2388254d`), and a test fix that treats a string-list target as a valid multi-target (`57bbb167`).

### 2.2 Pythonic DSL, second generation

Commits `7dc822d3`, `64804d72`, `7f1491df`, `88a042cb`, `6fcb610f`; changelog block `[0.12.0]`.

- **Instance facade.** `sm = Light()` is a running machine on the sync engine; `with Light() as sm:` / `async with Light() as sm:` is the recommended lifecycle idiom. `sm.cycle()` / `sm.send("CYCLE", amount=3)` return the actions' return values. `sm.state`, `sm.configuration`, `sm.context`, `sm.status`, `sm.can()`, `sm.matches()`, `sm.allowed_events`, `sm.green.is_active`, a readable `repr()`. `Light.create_machine()` still returns the bare `MachineNode`.
- **Events are named by the attribute** (`cycle = green.to(yellow)` is `CYCLE`); `event=` remains an override. Transitions declared inside nested state classes become event methods (`order.ship()`).
- **Naming-convention hooks**: `on_enter_<state>`, `on_exit_<state>`, `on_<event>`, `before_<event>`, `after_<event>`, and the generic `on_enter_state`, `on_exit_state`, `on_transition`, `before_transition`, `after_transition`. An unmatched suffix logs a warning. `before_*` / `after_*` need the facade and must be plain `def`.
- **Signature-based argument injection** for every callback (`context`, `event`, `event_type`, `interpreter`, `action_def`, `error`, `data`, `input`, `source`, `target`, `state`, payload fields, `**kwargs`); the legacy positional shapes keep working by arity detection.
- **`State.Compound` / `State.Parallel`** aliases; nested classes accept every `State(...)` keyword and are valid sources and targets.
- **`strict = True`** refuses undeclared events (`UnknownEventError`) and declared-but-not-enabled events (new `TransitionNotAllowedError`) at the call site.
- **Build-time logic validation**: instantiating a `StateMachine` raises one `ImplementationMissingError` listing every missing guard/action/service; `validate_logic = False` defers it; `create_machine(validate=True)` opts a bare `MachineNode` in.
- **`MachineNode.to_json(indent=None)`** (advertised since 0.5.0, now real).
- **Inheritance**: a subclass of a `StateMachine` subclass inherits states, transitions and callbacks.
- **`engine = "sync" | "async" | "auto"`**, plus `clock=` and `plugins=` on the facade.
- **Plain methods satisfy string references by name** (`guard="can_pay"` binds an undecorated `def can_pay`), only for names the chart references and no decorated callable provides.
- **`@state.service(on_done=..., on_error=..., id=..., input=...)`** decorator.
- **Lifecycle methods win over `start` / `stop` transitions** (`64804d72`): such transitions stay in the chart, get no `sm.start()` / `sm.stop()` sugar, and a warning is logged at class definition.
- **Reserved attribute names** (`send`, `state`, `configuration`, `context`, `status`, `can`, `matches`, `allowed_events`, `machine`, `interpreter`, `engine`, `strict`, `plugins`, `validate_logic`, and the class settings) raise `InvalidConfigError` when used for a state or transition.
- **`State.to()` / `State.internal()` no longer require `event=`**; a transition that still has no event at build time raises `InvalidConfigError` (functional API, `build_machine()`).
- **Module split**: `xstate_statemachine.pythonic` is a thin public module; the implementation lives in `_pythonic_core`, `_pythonic_builder`, `_pythonic_class`, `_pythonic_runtime`; every public name and the private compiler helpers the tests import are re-exported.

### 2.3 Services, restore and diagrams (`d184b06a`, `f1a0d9c7`)

- An invoked service's `input` factory receives the event whose transition entered the state (XState's `input: ({context, event}) => ...`; it used to receive `None`). The companion shortcut (no declared `input` means the event payload) was reverted in the engine-parity series; the shipped behaviour is `{}`, as in 0.11.0.
- `SyncInterpreter.from_state(machine, state, context=...)` / `Interpreter.from_state(...)` start an interpreter already in a given state without running entry actions (a minimal snapshot handed to `from_snapshot`); `StateMachine(state=...)` exposes the same.
- `MachineNode.to_mermaid()` / `to_plantuml()` draw `after` edges (`after 100ms`, `after TIMEOUT`, with `[guard]`), `--> [*]` for final states, the `--` divider between parallel regions, `invoke onDone` / `invoke onError` edges and `always` labels.

### 2.4 Fixes carried in the `[0.12.0]` block

- Transitions declared inside a nested `class paid(State):` body were dropped; children declared both as class attributes and in `states=[...]` compiled twice; a nested class as a `.to()` target raised `AttributeError`.
- Two same-named states under different parents received each other's transitions (now keyed by path).
- A three-argument legacy guard `(context, event, params)` on a transition without `params` now receives `params=None` instead of raising `TypeError` (which evaluated as `False`).
- A strict facade refuses a send to a finished or stopped machine with `InterpreterStoppedError` instead of a silent drop.
- `State(entry="name")`, `State(exit="name")`, `.to(..., actions="name")` with a bare string were iterated character by character.
- Documentation fixes: Getting Started's CLI listing and project tree, supported-Python ranges, search index, the deprecated `event.data` in the `storeError` example, the `FormWizard` references.

### 2.5 Performance, packaging and tooling

- `import xstate_statemachine` is about 25-30 % faster with warm bytecode and loads 47 fewer modules (`691e7f46`): graph algorithms, the pure transition API, testing utilities, the receipt codec and the store backends are imported on first use through PEP 562 module `__getattr__`; `hashlib` and `uuid` are deferred. `__all__` and every `from xstate_statemachine import X` are unchanged; `tests/test_import_time.py` pins the allowed module set.
- README rewritten Python-first (3,234 to 497 lines) and PyPI metadata refreshed (`869106a4`): new description ("State machines and statecharts for Python: define them in plain Python or load XState JSON"), keywords (`finite-state-machine`, `scxml`, `hsm`, `asyncio`), classifier **Development Status :: 5 - Production/Stable** (was 4 - Beta), `Programming Language :: Python :: 3 :: Only`, `Topic :: Software Development :: Libraries`.
- 0.12.0 pins in the pre-commit hook example and the supported-versions table (`8a81f092`); a typing fix for the `_schedule_state_tasks` probe override (`e4590db0`); CLI tests reset the process-wide console (`0a340647`); plain methods are bound on the built `MachineNode` so `cli` stays out of the import graph (`6fcb610f`).

### 2.6 Documentation

New pages: *Coming from python-statemachine* and *Coming from transitions* migration guides; a reworked Quick Start (one recommended path: a `StateMachine` class run with `with Machine() as sm:`); the microstep semantics section of `docs/_guide/parallel.md` (+264 lines); `docs/_guide/actions.md` (+134 lines on `assign`, `choose`, multi-target and conflict rules); the `docs/_guide/changelog.md` mirror; `jekyll-sitemap` and `docs/robots.txt`; `docs/research/COMPETITIVE_RESEARCH_python_statemachine.md`.

### 2.7 Tests added in the range

| File | Lines | Covers |
|:--|--:|:--|
| `tests/test_xstate_v5_ordering_parity.py` | 2,019 | every engine change in 2.1, on both engines |
| `tests/test_pythonic_dsl_v2.py` | 1,759 | the DSL facade, hooks, injection, strict mode, inheritance |
| `tests/test_battle_310_pythonic_dsl.py` | 675 | concurrency, cross-thread sends, deep nesting, snapshots of facade machines |
| `tests/test_mermaid_fidelity.py` | 602 | diagram export |
| `tests/test_import_time.py` | 199 | the lazy-import budget |
| `tests/test_xstate_conformance_cases.py` | 187 | replay of the 50 shared XState v5 cases (skipped when the Rust checkout is absent; **not wired into CI**) |

---

## 3. Are there breaking changes?

**Short answer.** There are no API-level breaking changes: nothing importable was removed or renamed, every public signature only widened, the snapshot layout is still v4 and snapshots load in both directions. There **are** behaviour-breaking changes: twelve changes that alter what an existing chart or DSL class does, silently in most cases. Four of them are not in the changelog at all. Under the project's own policy (SemVer guarantees start at 1.0; `docs/_guide/deprecation-policy.md`) a 0.x minor may carry them, but the release notes have to lead with them, and the policy page should say so (it does not today).

Severity below is the calibrated verdict of the two independent reviewers per finding, not the original auditor's rating (which ran one level hotter across the board).

### 3.1 Confirmed by two independent reviewers (code trace + reproduction on v0.11.0 and this tree)

| # | Change | Who is hit | What they observe | Migration | Severity | In changelog? |
|:--|:--|:--|:--|:--|:--|:--|
| B1 | `"*"` and `"prefix.*"` now receive engine events (`done.invoke.*`, `error.platform.*`, `after.*`, `done.state.*`); a wildcard on a deeper state outranks an ancestor's `onDone` / `onError` / `after` | Any chart with a catch-all handler (logging, "ignore everything else", analytics) | (a) A service failure caught only by `"*"` or `"error.*"` is consumed: `status` stays `running` where it was `error`. (b) A `"*"` on a child state swallows the parent's `done.invoke` / `after`: reproduced here, `loading` with `invoke` + `onDone: success` and a child `a: {on: {"*": log}}` reaches `m.success` on 0.11.0 and stays in `m.loading.a` on 0.12.0 with the wildcard logging `done.invoke.m.loading`. (c) A `"*"` with a target fires on `done.invoke`. | Guard the wildcard (`not ev.type.startswith(("done.", "error.", "after.", "xstate."))`; the changelog's suggested guard misses the `xstate.` prefix), or put the explicit `onDone` / `onError` / `after` on the same state as the wildcard or deeper | **HIGH** | yes (`CHANGELOG.md:77-89`) |
| B2 | Signature-based argument injection changes how legacy-shaped DSL callbacks are called when they have a **default argument**, a parameter named like a payload key, or a user-named fourth parameter | Users of `@guard` / `@action` / `@service` and `build_machine()` | `@guard def g(self, ctx, e, params=None)` raises `TypeError` ("needs argument 'e'"), is logged and treated as `False`, so the transition silently stops firing; an action with a default gets payload values bound in place of `Event` / `ActionDefinition`, and the remaining actions in the list are skipped. Cause: `_pythonic_runtime.py:122-129` treats any default, keyword-only parameter or `**kwargs` as "not legacy" and resolves by name. | Preferably fix before tagging (treat a callback whose positional parameters match a legacy arity once defaults are ignored as legacy; never let a payload key flip such a callback into by-name resolution). Otherwise document: remove defaults from legacy-shaped callbacks, rename parameters to the injectable names. | **HIGH** (one reviewer MEDIUM) | **no**; `CHANGELOG.md:317-319` says the legacy shapes "keep working unchanged", which is false |
| B3 | The façade defines `status`, `state`, `context`, `configuration`, `machine`, `interpreter` and `allowed_events` as read-only properties on `StateMachine` | A 0.11.0 class whose `__init__` or methods assign such a name on `self` (a logic holder with `self.status = ...` is plausible) | `AttributeError: property 'status' of 'Order' object has no setter`, **also through `Light.create_machine()`**, which still runs the user's `__init__`. Reproduced here: the same class builds on 0.11.0 and fails on 0.12.0. Inside an action the same error is contained by the action error policy and the rest of the list is skipped. | Rename the instance attribute | **MEDIUM** (loud, at build time) | **no**; the reserved-names entry (`CHANGELOG.md:439-449`) covers only state and transition attributes |
| B4 | `done.state.*` reaches the compound parent and fully-final parallel ancestors only | Charts that relied on completion bubbling through nested compounds; machines with a parallel root | A nested compound that completes no longer triggers the **outer** `onDone` (the inner compound has none): the machine stalls in the inner final state. A parallel-root machine now reaches `done` when every region is final and stops accepting events. A parallel's `onDone` now runs in the same step as its region's. | Put `onDone` on the compound that owns the final child, or transition from there to a final child of the outer state | MEDIUM (silent stall is the serious case) | yes |
| B5 | Reaching a top-level final state runs the remaining `exit` actions (final state, root), after `output` | Charts whose root or final `exit` is cancellation cleanup | Cleanup now also runs on normal completion, including when `start()` lands on a final state | Move cancellation-only cleanup to a non-final state's `exit`, or check the event type | MEDIUM | yes |
| B6 | A compound or parallel state targeting itself without `reenter` resets its children | "Refresh" handlers written as `target: <self>` instead of targetless | The current sub-state, its timers and invokes are discarded; the `initial` child is entered again | Drop `target` to keep the children | MEDIUM | yes |
| B7 | One `assign` resolves all properties against the prior context | Assigns where a later callable reads a key written earlier in the same dict | Derived keys compute from stale values; nothing raises (if a callable raises part-way, 0.12.0 now applies none of the keys where 0.11.0 had written the earlier ones) | Split into two assigns, or one callable returning the whole update | MEDIUM | yes |
| B8 | A target in a sibling parallel region has the parallel state as its domain | Cross-region "poke the other region" transitions | Every region exits and re-enters; the source region goes back to its `initial` (verified against the oracle: XState 5.33.3 gives `{p: {r1: "a", r2: "d"}}`, as 0.12.0 does; 0.11.0 was the divergent one) | Handle the event inside the target region, or `raise` an event it handles | MEDIUM | yes |
| B9 | Transition selection follows XState's `selectTransitions` | Charts with an ancestor or parallel-state handler for an event a region also handles; guards with side effects; `on_guard_evaluated` metrics | The parallel state's own targetless handler no longer runs beside the region's transition; ancestor and later-candidate guards are not evaluated; an `always` guard shared by N regions runs N times | Move "run on every E" actions into each region; do not rely on guard side effects; update count assertions | MEDIUM | yes |
| B10 | Naming-convention hooks bind **pre-existing** undecorated methods named `on_enter_<state>`, `on_exit_<state>`, `on_<event>`, `on_transition`, `on_enter_state`, ... | 0.11.0 classes with helpers that happen to match | The helper is called by the engine; a non-injectable signature raises inside the action list and the explicitly declared entry/transition actions after it are skipped; unmatched `on_*` names warn at class definition | Rename or give the helper an injectable signature | MEDIUM | described as a feature (`CHANGELOG.md:303-312`), not as a change for existing classes |
| B11 | `Light()` builds, validates and starts a sync machine | Code that instantiated its class directly (0.11.0 instances were inert) or defines `__init__` without `super().__init__()` | Entry actions run at construction; missing logic raises `ImplementationMissingError`; a half-initialised façade when `super().__init__()` is skipped. `create_machine()` is unchanged (it still calls the user `__init__`, starts nothing, validates nothing). | Use `create_machine()` for a bare node, `validate_logic = False`, or call `super().__init__()` | LOW to MEDIUM (reviewers split) | as a feature |
| B12 | `internal: false` with a **child** target now exits and re-enters the source (the v4 alias of `reenter: true`, `models.py:600-601`, now does what the alias promises) | v4-style charts | `exit` / `entry` of the source run again, invokes and `after` timers restart; 0.11.0 logged nothing. XState v5 ignores `internal` entirely, so a v5 engine would not re-enter either. | Drop `internal: false` (or accept the v4 semantics) | MEDIUM for v4-style charts | **no** |

### 3.2 Documented behaviour changes, reviewed once (not independently re-verified)

All of these are covered by the shared conformance cases or the ordering-parity suite; they change observable results but mostly in the "update your pinned expectations" way.

- `reenter: true` with a child target exits and re-enters the source; a re-entering root transition re-runs the root's `exit` / `entry` (E8).
- `done.state.*` is handled before external events already queued; a rollback withdraws it; on the async engine it counts toward `maxIterations`. The engine auditor could not confirm that the sync engine counts it the same way (`sync_interpreter.py` `_dispatch_internal`), so the two engines may differ in when `RunawayChainError` trips for long completion chains (E9).
- One microstep per event: exits, then transition actions, then entries; conflicting transitions dropped; `on_transition` fires once per selected transition with the step's before/after configuration (E10, API-2).
- History recorded only on owner exit, so a snapshot taken after an inner transition carries fewer `history` entries (E11).
- `always` visited in entry order; a restored snapshot starts in document order (E12).
- JSON `choose` with `params.branches` and a bare JSON `assign` now execute; `logic_names()` / `stub_logic()` now include names inside `choose` branches, so exact-set assertions change (E13).
- Undocumented: `subscribe()` listeners are notified once per microstep instead of once per transition (U1); a declared falsy `input` (`0`, `[]`, `""`, `False`) now reaches the service verbatim where 0.11.0 coerced it to `{}` (U2); a declared `input` factory receives the triggering event instead of `None`, also for invoked child machines (U4, documented).
- Lazy loading: after a bare `import xstate_statemachine`, `xstate_statemachine.helpers` / `.graph` / `.receipts` / `.testing_utils` are not attributes until imported; every `__all__` name still resolves (API-1, documented).
- Incidental re-exports dropped from `xstate_statemachine.pythonic` (`MachineLogic`, `InvalidConfigError`, `ActionCallable`, `ServiceCallable`, `_StateMachineMeta`); `__module__` of the DSL classes is now `xstate_statemachine._pythonic_core` (API-3, DSL-8, undocumented).
- Reserved state/transition attribute names raise `InvalidConfigError` at import time (DSL-5, documented); Mermaid / PlantUML text changed, so golden files need regenerating (DSL-6, documented as a fix).
- Generated `xsm` code renames a chart state called `state`, `status` or `context` to `state_2`-style identifiers (`cli/emit.py` `RESERVED_BINDINGS` now includes the DSL reserved names); the chart id is kept via `State("state", ...)`.

### 3.3 Checked and cleared

- **Public API surface.** A mechanical dump of `__all__`, `dir()`, every public member, `inspect.signature`, dataclass and `NamedTuple` fields, constants and exception bases for 28 modules on both versions, diffed programmatically: no removal, no rename, no field removed or reordered, no exception base changed, `ENGINE_EVENT_SHAPES` unchanged; `__all__` gained `TransitionNotAllowedError` and `event_payload`, about 71 members were added. `cli/args.py` is untouched (no flag or subcommand removed). The JSON schema and the `[pydantic]` gate accept a list of strings as `target`.
- **Snapshots.** `SNAPSHOT_VERSION` is 4 on both sides; `upcast()` and `check_shape()` unchanged. A 0.11.0 snapshot loads on 0.12.0 and the reverse. A restored machine follows the history the writer recorded (a 0.11.0 snapshot with the extra `history` entry restores the inner state; a 0.12.0 one restores the default). Entry order is not persisted; a restore starts in document order. `PureSnapshot` gained a private `_entry_order` attribute only.
- **`invoke` without `input`.** The service receives `{}` on both engines in 0.11.0 and 0.12.0. The payload-forwarding shortcut was added and reverted inside this unreleased range, so no user can see it. The changelog text about it is wrong in both directions (section 5).
- **`stop()`.** Neither engine runs exit actions on `stop()`, in 0.11.0 or 0.12.0, and XState v5 does not either (its 5.0.0 changelog: "exit actions of all states are no longer called when the machine gets stopped externally"; maintainers closed statelyai/xstate#4630 as working as designed). The five sentences in `docs/_guide/interpreters.md` (lines 25, 131, 222, 240, 802) that say `stop()` runs exit actions are a pre-existing documentation bug, not a 0.12.0 change.
- **Tests on this tree.** Core suite (`tests/`, excluding `tests/contrib`), Python 3.14 on Windows: **7,227 passed, 72 skipped, 0 failed** (39 min). Shared conformance replay plus ordering parity: **107 passed** (51 case tests, 56 parity tests). `tests/test_docs_site.py` (38), `tests/test_deprecations.py` and `tests/test_battle_309_docs_truth.py` (24) pass. Not run here: `tests/contrib/*` (the Django / DRF audit tables and the agents tracing plugins implement `on_transition` and now also see `done.state.*` of every finishing region), Python 3.9, Linux and macOS cells.
- **Second-import fix** (`45546e0f`) only repairs code introduced in this range.

### 3.4 Policy framing for the release notes

- The deprecation policy promises SemVer from 1.0 and says nothing about how a pre-1.0 minor with engine behaviour changes is announced (D10). One sentence there, and a "Behaviour changes" callout at the top of the 0.12.0 entry, closes that gap.
- The same release moves the PyPI classifier from Beta to **Production/Stable** (API-5) while changing eighteen engine semantics. That is defensible (they converge on XState v5), but the two facts should appear together in the notes.

---

## 4. Is 0.12.0 fully aligned with XState v5?

**Short answer.** On **statechart semantics** 0.12.0 matches the current stable XState (5.33.3, published 2026-10-17, still npm `latest` on 2026-11-05; nothing newer exists on the 5.x line; v6 is `6.0.0-alpha.73` and not stable). That is backed by 50 cases recorded from the real engine, all passing, two of them re-run live here with zero diffs. It is **not aligned on the wire and API surface**: engine event names and payload keys are XState v4 spellings, `status` says `running` instead of `active`, default invoke ids differ, v4 keys (`cond`, `internal`) are honoured where v5 ignores them, throwing guards and actions follow a different (documented) policy, and a handful of v5 APIs have no equivalent. "Fully aligned" or "100 % XState JSON compatible" is therefore not a defensible sentence; "XState v5 statechart semantics, with v4-style engine event names" is.

### 4.1 Upstream status (web research, 2026-11-05)

| Item | Finding | Source |
|:--|:--|:--|
| Latest stable | `xstate@5.33.3`, published 2026-10-17; dist-tags `latest=5.33.3`, `alpha=6.0.0-alpha.73`, `beta=5.0.0-beta.54` | npm registry, GitHub release page |
| 5.33.x contents | 5.33.0 (2026-09-12) adds the `transitionMeta` type; 5.33.1 and 5.33.2 widen metadata types; **5.33.3 fixes "child actors not being stopped when a machine errors because of an unhandled error from an invoked actor"** (statelyai/xstate#5792). The last one is a semantic fix on the error path; whether both Python engines stop the remaining invoked and spawned children before settling in `status == "error"` was **not checked** in this review and is worth a conformance case. | `packages/core/CHANGELOG.md` |
| v6 | Alpha only ("APIs may still change between alpha releases. XState v5 is still supported"). The published v5-to-v6 migration page announces: transitions and actions become inline functions with an `enq` side-effect queue; `assign`, `raise`, `sendTo`, `sendParent`, `forwardTo`, `emit`, `log`, `cancel`, `enqueueActions`, `spawnChild`, `stopChild`, `and`/`or`/`not`/`stateIn` are removed as exports; a leftover `cond` throws at construction; `fromPromise` becomes `createAsyncLogic`; done/error events gain `actorId` / `sessionId` / `stateId`; persisted snapshots are incompatible with v5; new features (choice states, state `input`, `timeout` / `onTimeout`, routes, `actor.select`). Its SCXML note (all exits finish before transition content, all transition content before entries) is the ordering 0.12.0 already implements. | stately.ai/docs/xstate/v6/* |
| `stop()` and exit actions | v5.0.0 changelog: exit actions are no longer called when the machine is stopped externally; statelyai/xstate#4630 closed as "working as designed" | changelog, issue |
| Engine event names and keys | `xstate.after.<delay>.<id>`; `xstate.done.state.<id>` with `output`; `xstate.done.actor.<id>` with `output`, `actorId`; `xstate.error.actor.<id>` with `error`, `actorId`; start event `xstate.init` (with `input`) | `packages/core/src/eventUtils.ts`, docs/invoke, docs/input |
| Snapshot status | `'active' | 'done' | 'error' | 'stopped'` (`SnapshotStatus`) | changelog, docs/states |
| `pure()` / `choose()` | "have been removed", replaced by `enqueueActions()`; 5.33.3 does not export them (confirmed on the local package) | docs/migration, oracle probe |
| `reenter` / `internal` | `reenter: true` re-enters on self and descendant targets, restarting invoked actors; "Use `reenter: true`, not `internal: false`"; transitions are internal by default | docs/transitions, docs/migration |
| `in` / `cond` | `stateIn()` replaces `in`; `cond` is deprecated in favour of `guard`; at runtime 5.33.3 **ignores** a `cond` key (confirmed on the local package: the guarded transition fires) | docs/migration, docs/guards, oracle probe |
| `delimiter` | Hard-coded `STATE_DELIMITER = '.'`; 5.33.3 ignores `delimiter` | `constants.ts`, oracle probe |
| Multi-target | Documented for parallel machines (`target: ['.mode.dark', '.theme.custom']`) | docs/transitions |
| `maxIterations` | Added in 5.31.0, default `Infinity`, configured via `createMachine({options: {maxIterations}})` | 5.31.0 release |
| Newer APIs | routable states (`xstate.route`, 5.28), `getNextTransitions` (5.26), `getInitialMicrosteps` / `getMicrosteps` (5.27), `actor.select` (5.29), `mapState` (5.31) | changelog, docs/routes |

### 4.2 Empirical parity: real `xstate@5.33.3` versus Python 0.12.0

Each row was executed on both sides (Node 24 against the Rust repo's oracle `node_modules`, `uv run python` against this tree; several rows also on the v0.11.0 worktree).

| Topic | XState 5.33.3 | Python 0.12.0 | Aligned |
|:--|:--|:--|:--|
| `actor.stop()` | No exit actions run; status `stopped` | Same, both engines (and in 0.11.0) | yes (docs wrong) |
| Root `type: parallel` completion | `done` with `output` once every region is final | Same (0.11.0 stayed `running`) | yes, new in 0.12.0 |
| Shared cases 043 and 047 re-run live | fresh oracle traces | zero diffs on `state_ids`, `context`, `actions`, `status`, `guards` | yes |
| `invoke` without `input` | `input === undefined` | `payload["input"] == {}` | partial |
| Declared `input: ({event}) => event` | receives the triggering event (`xstate.init` on start) | receives the triggering event (the library's init sentinel on start) | yes, except the init name |
| Engine event names and keys | `xstate.init`, `xstate.done.actor.<id>` (`output`, `actorId`), `xstate.error.actor.<id>` (`error`), `xstate.done.state.<id>` (`output`), `xstate.after.<ms>.<id>`; a handler keyed `xstate.done.actor.fetch` fires | `___xstate_statemachine_init___`, `done.invoke.<id>` (`data`, `src`), `error.platform.<id>` (`error`, `data`, `src`), `done.state.<id>` (`data`), `after.<ms>.<id>`; a handler keyed `xstate.done.actor.fetch` **never fires** (unchanged since 0.11.0) | **no** |
| `status` | `active` / `done` / `error` / `stopped` | `uninitialized` / `running` / `done` / `error` / `stopped` | partial (naming) |
| Default invoke id | `0.<state id>`; two id-less invokes get `0.m.l` and `1.m.l` | the state id; two id-less invokes in one state share `m.l` and the same `done.invoke.m.l` | **no** |
| `choose` / `pure` | not exported | exported (v4 compatibility superset) | partial |
| `delimiter` | ignored | ignored | yes |
| v4 `cond` | ignored (transition fires) | honoured as a guard alias (transition blocked) | **no** (deliberate superset) |
| v4 `internal: false`, child target | ignored (no re-entry) | aliased to `reenter: true`, so the source re-enters (new in 0.12.0) | **no** |
| `emit` + `on`, `system.get`, delayed `raise` with id + `cancel`, `spawnChild` + `stopChild` | work | work; emitted payload sits under `.payload`, child keys are `parent:id`, `raise_()` has no `id` kwarg (id via JSON params or `send_to(send_id=)`) | yes (API shape differs) |
| Actor logic creators | `fromPromise`, `fromTransition`, `fromObservable`, `fromEventObservable`, `fromCallback` | callables / `from_coroutine` / `from_callable`, `from_callback` (with send-back and receive), `from_async_iterator` / `from_iterator`, `from_interpreter`; **no `from_transition`, no `fromEventObservable`** | partial |
| Throwing guard / entry action | actor goes to `status: 'error'` with `snapshot.error`; the fallback branch is not taken | guard treated as `False` (fallback branch taken), action logged and skipped, status stays `running` | **no** (documented policy, AGENTS.md) |

### 4.3 Feature inventory against the Stately docs

- **Present with matching semantics:** atomic / compound / parallel / final states and initial inference; shallow and deep history with persistence; `reenter`, multi-target, forbidden, wildcard and partial descriptors; `always`, `after`, named delays, `maxIterations`; every v5 built-in action (`assign`, `raise`, `sendTo`, `sendParent`, `forwardTo`, `escalate`, `log`, `cancel`, `stopChild`, `spawnChild`, `emit`, `enqueueActions`), guards with params and `and` / `or` / `not` / `stateIn`; invoke and spawn with `input` / `output` / `onDone` / `onError`; `systemId`, `system.get` / `get_all`; context factories with `input`; `tags`, `meta`, `description`; machine and final-state `output`; the actor API (`start`, `stop`, `send`, `get_snapshot`, `subscribe`, `on`, `can`, `matches`, `has_tag`); the pure helpers (`transition`, `initial_transition`, `get_next_snapshot`, `get_initial_snapshot`, `wait_for`, `to_promise`); graph algorithms (own shapes).
- **Missing:** `fromTransition` reducer actors, `fromEventObservable`, routable states (`xstate.route`), `getNextTransitions`, `getMicrosteps` / `getInitialMicrosteps`, `mapState`, `actor.select`.
- **Different by design:** persisted snapshots are the library's own v4 layout, not XState's persisted-snapshot format; inspection is a plugin speaking the `@statelyai/inspect` 0.7.2 protocol rather than an `inspect` option; `setup()` / `provide()` map to `MachineLogic` and `create_machine(logic=...)`; `done` payload is `event.data` not `event.output`.
- `docs/FEATURE_GAP_ANALYSIS.md` still marks the 5.26 to 5.31 items as present; it is a 0.5.1-era document and should keep its "historical" banner or be updated.

### 4.4 How strong is the parity evidence?

- The 50 shared cases compare `state_ids`, `context`, user-named `actions`, `status`, `guards` and `output`. They never compare **event names**, plugin hooks, snapshots, timing beyond `SimulatedClock`, built-in action execution (`assign` / `raise` / `emit` are not recorded) or child actors (`oracle.mjs` marks `spawnChild` "not exercised by the fixtures yet"). The event-name divergence above is invisible to them by construction.
- The replay runs **`SyncInterpreter` only**. The async `Interpreter` is never run against the oracle; its parity rests on the traces hand-transcribed into `tests/test_xstate_v5_ordering_parity.py` (every one of its 18 classes maps to a shared case; 8 cite the case number, 8 are matched by name).
- **CI never runs the shared cases**: no workflow checks out `basiltt/xstate-statemachine-rs` or sets `XSM_CONFORMANCE_CASES`, so `test_xstate_conformance_cases.py` is skipped there and the `len >= 37` guard never executes. Only the ordering-parity pins protect the engine on CI; cases without an ordering-parity twin are unprotected.
- `tests/test_xstate_v5_parity.py` (the 0.6.0 feature-gap suite) is author-asserted: nothing checks that XState behaves the same.
- Uncovered semantic areas with zero oracle evidence: spawned actors and `xstate.done.actor`, `systemId`, `sendTo` with delay and `cancel`, `sendParent` / `escalate`, `fromCallback` send-back, errors thrown by actions and guards, machine `input`, `tags` / `meta`, dynamic delays, `maxIterations`, snapshot restore mid-run, the 5.33.3 error-path child shutdown.

---

## 5. Before tagging 0.12.0

In order of importance.

1. **Decide B2 (callback injection).** Recommended: fix in `_pythonic_runtime.py` so a callback whose positional parameters match a legacy arity once defaults are ignored is called positionally, and a payload key never flips such a callback into by-name resolution; add the `params=None` guard and the default-argument action to `tests/test_pythonic_dsl_v2.py`. If it ships as is, the changelog sentence "keep working unchanged" has to go and the shapes must be listed as breaking.
2. **Changelog structure.** Fold `[Unreleased]` into `[0.12.0]`, set the real date, leave an empty `## [Unreleased]`, add the compare link, and turn "Behaviour change: the next release notes must call this section out" into a reader-facing **Behaviour changes** callout. Apply every edit to `docs/_guide/changelog.md` too: `tests/test_battle_309_docs_truth.py` asserts the latest non-empty sections are identical and that an empty Unreleased is empty or exactly "Nothing yet.".
3. **Changelog content.** Rewrite the `[0.12.0]` "Services see the triggering event" bullet (`CHANGELOG.md:346-355`): a declared `input` factory sees the triggering event; no declared `input` gives `{}`; `event_payload` forwards the payload; invoked child machines follow the same rule. Delete the "0.12.0 made ... reverted ... again" Fixed bullet (`CHANGELOG.md:266-283`) after folding `event_payload` and the xstate 5.33.3 verification into the Added bullet. Add the undocumented changes: B2 (or its fix), B3 reserved instance attributes, B10 hooks binding pre-existing helpers, B12 `internal: false` re-entry, U1 `subscribe` per microstep, U2 falsy `input` passthrough, the dropped incidental re-exports from `xstate_statemachine.pythonic`. Extend the B1 migration guard to the `xstate.` prefix.
4. **Stale wording.** `docs/_guide/interpreters.md:25,131,222,240,802` (`stop()` does not run exit actions, as in XState v5); `docs/_guide/core-concepts.md:108` and the comments at `base_interpreter.py:4092` and `:6429` ("Up to 0.12" / "0.12 signature" describe 0.11.0 and earlier); the `_invoke_input` docstring at `base_interpreter.py:3197-3200` ("0.12.0 briefly forwarded ... reverted" describes nothing a user saw); soften "100 % XState JSON compatible" at `docs/_guide/quick-start.md:108`, `docs/index.html:375` and `AGENTS.md` to "XState v5 statechart semantics; engine events keep the v4 spelling (`done.invoke.<id>`, `error.platform.<id>`); `status` is `running|done|error|stopped`"; one sentence in `docs/_guide/deprecation-policy.md` (and a "from 1.0" qualifier in `SECURITY.md`) on pre-1.0 minors that change engine behaviour.
5. **Verification still open.** Run `tests/contrib` on this tree (Django / DRF audit and signals, agents tracing and LangGraph bridges implement `on_transition` and count events); spot-check B4 to B9 on the async `Interpreter` (the reviewers used `SyncInterpreter`); confirm the sync engine's `maxIterations` accounting for `done.state.*` matches the async engine; check the 5.33.3 error-path rule (remaining children stopped before `status == "error"`); let CI cover Python 3.9, Linux and macOS.
6. **CI.** Add a pinned checkout of `basiltt/xstate-statemachine-rs` (`path: xsm-rs`) to one Linux test cell with `XSM_CONFORMANCE_CASES=$GITHUB_WORKSPACE/xsm-rs/conformance/cases`, and make a missing directory fail instead of skip. Otherwise the parity claim rests on local runs only.
7. **Release mechanics** (`CONTRIBUTING.md` steps): push the branch, open the PR to `main`, CI green on the merge commit, tag `v0.12.0` on the verified `main` sha (the `rev: v0.12.0` pre-commit example, the `uses: basiltt/xstate-statemachine@v0.12.0` action and the supported-versions table already point at that tag), publish, `uv lock --check`.

---

## 6. Method and evidence

- **Audit:** four finders over `git diff v0.11.0..HEAD` (engine semantics, Pythonic DSL, public API surface by mechanical introspection diff, release documentation) produced 43 findings; the 14 rated CRITICAL or HIGH were each re-examined by two independent reviewers with different briefs (read the code of both versions; reproduce by running one script against the v0.11.0 worktree and this tree). Thirteen were confirmed with a calibrated severity, one (D7, "stop() runs exit actions") was refuted as a 0.12.0 change and reclassified as a documentation bug. Two findings (B1 case (b) and B3) were additionally reproduced by hand for this report.
- **Research:** web research with sources (section 4.1); 13 empirical probe topics against `xstate@5.33.3` mirrored on Python (section 4.2); a feature inventory from the Stately docs cross-checked by source grep (4.3); a review of the conformance harness, the oracle script and the CI workflows (4.4); a completeness critic over all outputs, whose contradictions (stop semantics, invoke input default, severity calibration, event-name parity) are resolved above.
- **Not covered:** `tests/contrib`, non-Windows platforms, Python 3.9, generated `xsm` templates compiled against the new DSL, the async engine for most engine changes.
- 37 review agents, 269 tool calls, plus the direct checks described above. v0.11.0 was checked out as a detached git worktree for the duration of the review and removed afterwards.
