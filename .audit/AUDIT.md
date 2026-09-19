# Open-issue audit — xstate-statemachine (post-0.8.0 `main` @ a12cde6)

Verified 2026-09-17 on Windows 11 / CPython 3.14.6 with `.audit/repro_new.py`,
`.audit/repro_reopened.py`, `.audit/repro_37_51.py`. Every reproduction in every
issue reproduces as described. No fabricated or incorrect defect claims were
found; a handful of *framings/severities* are overstated (called out below).

## 1. New issues (#75–#80)

| # | Claim | Verified | Verdict | Effort | Disposition |
|---|---|---|---|---|---|
| 75 | `send(ev, wait=True)` ×2 with same `Event` instance hangs (receipt keyed on `id()`) | ✅ hung | **Real bug**, High (silent hang) | Small | **Fix** — monotonic token on the queued envelope |
| 76 | `SyncInterpreter` `after` timers unreachable by `tick()` when built inside a running loop | ✅ `pending=0`, stays in `a`; off-loop control moves to `b` | **Real bug**, Med-High (eventually fires via `call_later`, so intermittent not total) | Small | **Fix** — lane chosen by owner, not ambient loop |
| 77 | Sync macrostep budget counts *every* event; >1000 batch silently `clear()`ed | ✅ `seen=1000/1501`, `queue_depth=0`, no exception | **Real bug**, Medium (sync only, batch >1000) — silent data loss | Small-Med | **Fix** — port async `_raise_depth` (count chained raises, not throughput); raise instead of `clear()` on genuine runaway; correct CHANGELOG line |
| 78 | `send_threadsafe()` skips `_check_strict` + `event_schemas` | ✅ typo accepted; `qty=-1` **transitioned** to `st.b` | **Real bug**, Medium — recommended cross-thread path lacks the guardrail | Small | **Fix** — validate synchronously on the calling thread before `_enqueue` |
| 79 | User events named `error.*`/`done.*` invisible to `"*"` and exempt from `onUnhandled:"error"` | ✅ `['PLAIN','my.namespaced']`; `done.review` leaves status `running` | **Real, but design gap not regression**. Overstated: exact-match `on: {"done.review": …}` still works — only wildcard/partial + `onUnhandled` are affected | Med (provenance flag) / Small (build-time warn) | **Fix (cheap path) + docs** — warn at `create_machine()` for `on:` keys in reserved namespaces; document the 5 prefixes. Provenance-tagging is the proper fix; schedule for 0.9 |
| 80 | `error.platform.*` delivered as `DoneEvent` with exception in `.data` | ✅ `('DoneEvent','error.platform.m.a','RuntimeError')` | **Enhancement**, Low. Correct as an XState-v5 parity ask | Small | Accept for 0.9; not a bug |

## 2. Reopened issues

| # | Reopen reason | Verified | Is it a defect in the fix? | Disposition |
|---|---|---|---|---|
| 27 | `rollback` doesn't undo a `raise`/`sendTo` emitted earlier in the same action list; warn-once is per-`MachineNode`; 22% idle cost; `on_transition_failed` fires twice under `continue` | ✅ `state=rs.a`, `seen=['PING']` | **No** — scope limitation, not a bug. XState has no rollback at all; effect-rollback is not tractable for `sendTo`. | **Comment + 2 small tweaks**: (a) doc "rollback = context+configuration only, never emitted effects; put outward effects last"; (b) *do* discard internal-queue `raise`s enqueued during the failed action list — cheap and makes the guarantee honest for the one effect we own; (c) warn once per process (or at `create_machine`); (d) add perf line to production-characteristics; consider skipping the checkpoint when the transition crosses no actions |
| 31 | Sibling fallback still silent by default — no `DeprecationWarning` (was acceptance criterion 2) | ✅ resolved `m.B`, `warnings=[]` | **Yes, minor** — an agreed criterion didn't ship | **Fix** (trivial): `warnings.warn(DeprecationWarning)` on the fallback path naming the `#machine.path` form. Note `InvalidConfigError` vs `StateNotFoundError` naming in the close comment |
| 37 | `run_coroutine_threadsafe(interp.send(..), loop)` — the *correct* 0.7 idiom — now raises `WrongThreadError`; message says events "would be silently lost" (false for that idiom); break undocumented | ✅ `raised WrongThreadError` | **Deliberate trade-off, not a bug** — call-site check can't distinguish the two idioms without reintroducing silent loss | **Comment + trivial fix**: correct the error message (name the `run_coroutine_threadsafe` case explicitly), add a *Changed* CHANGELOG entry, fix `interpreters.md:1025` wording. Then close; strict bypass tracked in #78 |
| 39 | Only the `id()` receipt collision | ✅ (= #75) | Duplicate of #75 | **Comment**: close as fixed-by-#75 once #75 lands |
| 43 | Still 2 tasks per idle child (poll removed, task not collapsed) | ✅ `2.0 tasks/child` | **No** — the perf problem (5 ms poll) is fixed; the second task is the manager (timeout / cancel / onDone dispatch), by design | **Comment + 1 doc line**: publish "2 asyncio tasks per invoked child, zero periodic wake-ups" in production-characteristics. Close. Collapsing to callbacks is possible but low value |
| 44 | `status == "running"` after static `from_snapshot()` with dormant invokes | ✅ `status=running pending=['r.w']` | **Ergonomics gap**, not a bug | **Small fix**: add `has_dormant_invocations` property (avoid a new `status` value — it would break every `status` consumer) + one guide sentence "`status` is not a liveness signal after restore". Close |
| 50 | Timer lane displaced to `call_later` in loop context | ✅ (= #76) | Duplicate of #76 | **Comment**: close → track in #76 |
| 51 | (1) `send_threadsafe` bypass; (2) strict violation inside `raise` swallowed under `continue` | ✅ (1) = #78; (2) `state=s.b status=running last_ok=False` | (1) dup of #78. (2) **Overstated** — it *is* observable (`last_transition_ok=False`, `on_action_error`, `on_transition_failed` fire); just not raised | **Fix (better than docs)**: validate *static* `raise` event names against declared events at `create_machine()` when `strict` — it's a config error, catch it at build time. Then (2) is moot regardless of policy. Close after #78 |
| 52 | `MachineLogic(strict=True)` not shipped | ✅ params: `actions, guards, services, delays` | **Enhancement**, agreed-upon half of the plan | **Small fix** (~20 lines): `strict=True` → undecorated members raise `InvalidConfigError`. Or decline explicitly — reporter is fine either way |

## 3. Incorrect / overstated claims

Nothing is fabricated. Overstatements worth pushing back on in comments:

1. **#79** — "two events vanished": exact-key handlers for `done.review` work fine; only `"*"`/partial matching and `onUnhandled` are affected. Real, narrower.
2. **#51(2)** — "no observable failure": false. `last_transition_ok`, `on_action_error`, `on_transition_failed` all report it. The complaint is really "not *raised*".
3. **#27 reopen** — "behavioural gap in the fix itself": it's a documented-scope question. No rollback implementation can un-send a `sendTo`. The `raise` case *is* cheaply undoable, so do that one.
4. **#43 reopen** — the perf defect in the title is fixed; the reopen is about the resource claim. Design decision, publish the number.
5. **#37 reopen** — "regression": deliberate. But the message and CHANGELOG are genuinely wrong/missing.
6. **#76 severity High** — mitigated by eventual `call_later` delivery; Med-High is fairer. Still a contract break for `tick()`.
7. **#77** — CHANGELOG entry is accurate about deferred replay; only the "two engines now agree" sentence overclaims.

## 4. Recommended work plan

**Wave A — code fixes (all small, ship as 0.8.1 patch):**
- #75 receipt token · #76 clock lane by owner · #77 raise-depth in sync + raise-not-clear · #78 validate in `send_threadsafe` · #31 fallback `DeprecationWarning` · #37 error message + CHANGELOG *Changed* entry · #44 `has_dormant_invocations` · #27 discard in-list `raise`s on rollback + warn-once-per-process · #51 build-time validation of static `raise` names under strict · #52 `MachineLogic(strict=True)`.

**Wave B — docs (same release):**
- Rollback scope (#27) · restore/liveness (#44) · 2 tasks per child (#43) · reserved event prefixes in events/onUnhandled/strict sections (#79) · perf cost of `rollback` in production-characteristics (#27).

**Wave C — 0.9 enhancements:**
- #79 provenance-tagged system events · #80 `ErrorEvent`.

**Comment-and-close now (no code):** #39 → #75, #50 → #76, #51(1) → #78, #43 (after doc line).
