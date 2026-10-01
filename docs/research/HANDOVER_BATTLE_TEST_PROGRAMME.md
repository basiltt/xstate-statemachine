# HANDOVER — Battle-test programme for the 52 integration issues (#257–#310)

**Audience:** the agent (or team of agents) taking over after the 0.11.0 release candidate.
**Owner on the human side:** the maintainer (basiltt). **Nothing is published without their explicit go — ever.**
**Repository:** `basiltt/xstate-statemachine` · default branch `main` · RC branch `rc/0.11.0` (PR #362).
**Written:** 2026-10-01, at commit `010158b` on `rc/0.11.0`.

---

## 0. Why this document exists

Four days ago 52 issues (#257–#310) were opened: an epic (#257), two programme-wide gates (#303 security baseline, #307 performance budgets), six per-phase release-candidate trackers (#297–#302) and **43 feature issues** spanning persistence, resilience patterns, actor logic, graph algorithms, a pytest plugin, observability, a live inspector, five web frameworks, two ORMs, five message brokers, Celery, LLM agents, recipes, comparisons and 1.0 hardening.

**All 43 features are implemented and merged** (see §3). Every PR passed lint, mypy, the full suite on 3.9–3.14 × Linux/macOS/Windows, a per-extra CI cell, the compat matrix (oldest + newest of every extra), an independent review, and a verify script re-run against the **built wheel in a clean venv**. 0.11.0 is sitting in PR #362 for the maintainer's own review.

That is *done*. It is **not** *battle-tested*. The library competes with `transitions`, `python-statemachine`, `django-fsm`, LangGraph, Burr, Temporal-style workflow engines and hand-rolled code written by very experienced developers. "The tests pass" is table stakes. The next phase is to take **each feature, one at a time**, and try to break it the way a hostile production environment would — then make the documentation good enough that the GitHub Pages site is the single place anyone ever needs to look.

This document gives you the background, the standards already in force, the per-issue work contract, and the order to do it in.

---

## 1. Background you must absorb before touching anything

Read these in order. Budget half a day; it is cheaper than re-learning them from failures.

| # | Read | Why |
|:--|:--|:--|
| 1 | `AGENTS.md` | Project conventions: imports, emoji-prefixed comments (`🏛️ 📝 ⚠️ 💡 🔥 ✅ 🚀`), black 79 / flake8 flags / mypy, where semantics live (`BaseInterpreter` vs engine copies), snapshot-layout rules, `wall_now()` vs `clock.now()`. **Every rule there is enforced by a test.** |
| 2 | `docs/research/GROUPED_DELIVERY_PLAN.md` | How the 43 features were grouped (G1–G10), the **shared-file protocol** (which files only one branch may edit at a time and how conflicts are resolved keep-both), the real-3.9 pre-push rule, the RC definition. |
| 3 | `docs/_guide/security.md` | The **X0 baseline** (#303): closed-by-default authorisation (X0.1), principal-scoped idempotency (X0.2), crash consistency (X0.3), safe deserialisation + size caps (X0.4), redaction (X0.5), telemetry label hygiene (X0.6), web hardening / RFC 9457 problems without exception text (X0.7), poison + backpressure (X0.8, X0.8b Celery serializers), durable-timer generations (X0.9), file modes (X0.10), agent tool safety (X0.13), explicit plugin discovery + supply chain (X0.14). **Every battle test must check the X0 rows that apply.** |
| 4 | `docs/_guide/guarantees.md` + `docs/_guide/deprecation-policy.md` | What the library promises (exactly-once vs at-least-once per path; SemVer for core + persistence, provisional for `contrib`). A battle test that finds the code violating a stated guarantee is a **release blocker**; one that finds an unstated limitation is a **documentation task**. |
| 5 | `docs/_guide/production-characteristics.md` + `benchmarks/` | Measured throughput, memory and latency, the perf budgets (`budgets.json`, ×1.25, nightly on the reference runner, skipped on a different CPU model). |
| 6 | `docs/_templates/integration-page.md` | The mandatory shape of every integration page: Install / Quick start (executable) / Reference (every public name) / **Guarantees** box / **Threat model** box / Compatibility / Troubleshooting. |
| 7 | `tests/test_docs_site.py`, `tests/test_docs_executable.py`, `tests/test_readme.py`, `tests/test_security_baseline.py`, `tests/test_zero_dependency.py`, `tests/test_import_surface.py`, `tests/test_public_api_surface.py`, `tests/contrib/test_extras_matrix.py`, `tests/test_compat_matrix.py` | The **documentation and architecture tests**. Every Python block in the Pages guide and README is executed. Both changelog copies must have byte-identical bodies. `pages_order` must list every guide page. No `contrib` module may load on `import xstate_statemachine`. No mojibake. These are why "docs updated" is checkable, not a claim. |
| 8 | `scripts/verify/` (30 scripts + `wheel_gate.py`) | One end-to-end script per issue/group that re-runs the issue's acceptance criteria against the **installed wheel**. `python scripts/verify/wheel_gate.py` runs all of them in a fresh venv (≈15 min). Your battle tests extend these; they do not replace them. |
| 9 | Prior handovers in `docs/research/HANDOVER_*.md` | The style of brief the other agents worked from; the per-issue "Review amendments" blocks at the top of each GitHub issue **supersede** the issue bodies. |
| 10 | PR #362 description + comments, and the comments on #297 | The RC evidence table, draft release notes, and the three decisions reserved for the maintainer (version — decided: 0.11.0; raising declared extra floors; waiting for the perf nightlies). |

### Environment facts that bit the previous agents (do not relearn them)

- **Windows host, PowerShell primary.** The harness's `Bash` tool resolves `bash` to **WSL** (`C:\Windows\System32\bash.exe`) on this machine; paths like `C:/...` fail inside it and `grep -r` from the repo root sweeps every `.claude/worktrees/*`. **Use the PowerShell tool.** If you must use `bash`, set `CLAUDE_CODE_GIT_BASH_PATH` to Git Bash first.
- PowerShell's `ConvertFrom-Json`/`jq` strings: `+` in `--jq` expressions gets mangled — use `--template` or `ConvertFrom-Json`.
- `[IO.File]` relative paths resolve against the *process* cwd, not the shell's — use `(Resolve-Path x).Path`.
- Editing CRLF files with PowerShell `.Replace` using LF here-strings silently no-ops; prefer the Edit tool or normalise line endings explicitly. Git stores LF (`i/lf`); working copy is CRLF via autocrlf. **Never commit a whole-file line-ending flip** (one agent did; the verifier caught it).
- Editable installs point at whichever worktree last ran `pip install -e .`; after removing a worktree, re-run `pip install -e ".[all]"` from the main checkout. `.venv39` (real CPython 3.9.25) likewise; use `--only-binary :all:` there.
- Emoji in comments/log strings got **double-encoded** (UTF-8 bytes re-read as cp1252, so a warning sign became a four-character `A`-with-circumflex sequence) when files passed through a cp1252 console. `python scripts/verify/_mojibake_scan.py --fix` reverses it; `tests/test_security_baseline.py::TestNoMojibake` blocks it — including in this document, which is why the broken form is not quoted here.
- Hosted GitHub runners are **not pinned to one CPU model**; the perf job skips when the model differs from the baseline's (EPYC 9V74). Do not "fix" a red perf run by raising budgets — read the CPU name in the skip/failure message first.
- GitHub refuses same-account PR approvals (post reviews as comments) and throttles PR creation (`was submitted too quickly` → wait ≥10 min).
- Black is **26.1.0** (25.x rejects `py314`); flake8 7.3.0; mypy ≥1.14 — pins in `.pre-commit-config.yaml` and `ci.yml`.
- `pip-audit` audits `pip freeze --exclude-editable` output, not the editable project (a pre-release version is "not on PyPI").
- Docker Desktop runs its own WSL2 distros; those `wsl.exe` processes are not yours. Live-broker tests need Docker and are opt-in (`XSM_CONTAINERS=1`).

---

## 2. What "battle-tested" means here (the contract per issue)

For **each** feature issue, in order (§3), produce **one PR** titled `battle(<issue>): <feature>` that contains, as applicable, every item below. An item that genuinely does not apply is stated as not applicable **with the reason** in the PR body — never silently skipped. The PR body is the evidence; the maintainer reads it.

### 2.1 Real-time / realistic-project scenario
Build (or extend an existing example app with) a **realistic end-to-end scenario** that a production team would recognise — not a unit test. Use the existing six example apps (`examples/integrations/*`) and nine recipes as hosts where possible; add a new app only when none fits. The scenario must run offline by default (fakes/moto/fakeredis/eager Celery/`SimulatedClock`) and against the real service when an env var is set (`XSM_*_URL`, `DATABASE_URL`, `XSM_CONTAINERS=1`).

### 2.2 Concurrency and race conditions
Threads **and** asyncio where both engines apply. The library has two engines (`Interpreter`, `SyncInterpreter`) and guarantees parity; test both. Known seams to attack: `send_threadsafe()` mailbox; `persisted()` under `OptimisticLock` and `PessimisticLock` with N workers on one key and on many keys; parent snapshot vs child pump step (the TOCTOU already found once — `SnapshotMidStepError`); `after` timers vs state re-entry (one timer per delay — found once); idempotency inbox claim/mark vs crash between them (X0.3); outbox commit vs relay; broker ack vs process kill. Use deterministic interleavings where possible (gates/barriers), then a randomised stress run with a fixed seed, then a long soak.

### 2.3 Memory leaks and resource leaks
`tracemalloc` snapshots across ≥10 000 iterations of the feature's hot path (create → act → persist → discard; spawn → complete → reap; connect → push → disconnect for WebSockets/Channels/SSE; subscribe → deliver → ack for brokers). Assert growth is bounded (compare snapshot N/2 vs N, not 0 vs N). Also: open file descriptors / sockets (`psutil`), threads (`threading.active_count()`), asyncio tasks (`asyncio.all_tasks()`), event-loop handles, SQLite connections, Redis connections, weakrefs (`gc.get_objects()` walk uses `issubclass(type(o), …)`, not `isinstance` — lazy proxies evaluate on `__class__`). The existing `tests/test_actor_lifecycle.py::TestReaping*` show the pattern.

### 2.4 Blockers, deadlocks and hangs
Every blocking call must have a bound. Look for: `Lock.acquire()` without timeout, `queue.get()` without timeout, `asyncio.wait_for` missing on network I/O, `join()` without timeout, SQLite `busy_timeout` paths (now mapped to `LockTimeoutError`), Celery `result.get()` without timeout, broker `fetch` without `timeout`. Write a test that **forces** each path (a holder that never releases, a server that never answers) and asserts the library returns/raises within the documented bound. Run the feature's suite with `pytest-timeout` set low and `faulthandler` on.

### 2.5 Performance
Add or re-record a row in `benchmarks/integrations_characteristics.py` for the feature's hot path (p50 over 7 repetitions, the existing harness), with the budget recorded on the reference runner via a `workflow_dispatch` of the perf job (not your laptop). Compare against the obvious alternative (raw SQLAlchemy / raw Django ORM / raw Celery / `transitions`) in `benchmarks/competitors/` and publish the honest ratio on `production-characteristics.md`. Check big-O behaviour: 1, 100, 10 000 instances; 1, 100, 10 000 events; 1, 50, 500 states; parallel regions; deep history. Profile (`cProfile`/`py-spy` if available) any row more than 2× its alternative and either fix or document why.

### 2.6 Complex scenarios
Per feature, at least: nested + parallel + history states together; guards that raise; actions that raise mid-list; services that time out; `after` and `raise(delay)` interleaved; snapshot taken mid-flight and restored on the other engine; machine version bump with a `SnapshotMigrator` step; a chart from the Stately corpus (`tests/tests_cli/stately_machines/*.json`, 100+ real charts) run through the feature with `stub_logic`.

### 2.7 Stress and soak
A `pytest.mark.stress` test (skipped by default, run in a nightly `workflow_dispatch` job you add if it doesn't exist): ≥100 000 events, ≥1 000 concurrent instances, ≥1 hour soak on the reference runner for stateful features (persistence, brokers, Celery, Channels, inspector SSE). Record peak RSS, p99 latency, error count (must be 0) and GC pauses.

### 2.8 Failure injection
Kill -9 mid-write (subprocess harness), disk full (`FileStore` on a tiny tmpfs or mocked `os.write` ENOSPC), network partition (fake adapter `fail_next`, real broker container stop/start), clock jumps (wall clock backwards; `SimulatedClock(wall_start=)`), corrupt snapshot bytes (every byte position of a small snapshot flipped → must be `SnapshotCorruptError`, never a bare `TypeError`/`KeyError`), oversize payloads at every cap (X0.4), unicode edge cases in keys/ids (NUL, RTL marks, 10 kB keys → `InvalidKeyError`).

### 2.9 Security re-verification
For each X0 row the feature touches: a test that **attacks** it (forged header, replayed idempotency key from another principal, payload carrying reserved `send()` kwargs, pickle in a Celery config, exception text in a 500 body, a label with an order id, a path-traversal store key, a `|safe` in a template). Run `python scripts/verify/303_x0_baseline.py` after. Any new finding is a CRITICAL/HIGH in the PR and is fixed before anything else.

### 2.10 Code quality pass
Read every file the feature owns, in full. Enforce: functions < 50 lines, files < 800 lines (split otherwise), no nesting > 4, explicit error handling, no magic numbers, Google docstrings on every public name, `__all__` complete and matching the API index, type hints complete (`mypy --strict` on the package should be the goal; the repo currently passes default mypy). **Comments:** the repo's convention is emoji-prefixed *why* comments (`🏛️` architecture decisions, `📝` notes, `⚠️` cautions) — add them wherever a reader would otherwise ask "why". The maintainer wants both AI-authored and human-readable rationale comments throughout; a file with no `🏛️`/`📝` comment is almost certainly under-explained. Immutability where practical (return new objects), AAA-structured tests with descriptive names.

### 2.11 Documentation — the Pages site is the bible
After the code work, for each feature:
- **Guide page** follows the template exactly; Reference names **every** public symbol (the API-index audit script in the previous session is the model — enumerate `__all__`, grep the page); Guarantees + Threat-model boxes updated with anything the battle test learned; Troubleshooting gains every error you provoked, with the fix.
- **New pages where necessary**: an "Operations" page per stateful extra (sizing, tuning knobs, metrics to alert on, runbooks for the failure modes you injected); a "Migration from X" page where a competitor exists (`vs-*.md` already exist for transitions, python-statemachine, django-fsm, LangGraph — add Burr, Temporal-lite, raw Celery canvas if relevant).
- **Examples**: the scenario from §2.1 lives under `examples/` with a README (what it shows, exact commands, what is faked, how to go live), is registered in `tests/test_examples_integrations.py` (or the recipes test) and linked from the guide page above Quick start.
- **README**: the Integrations row names the main public symbols; "What you get" / feature cards updated if the pitch changes.
- **Changelog**: a bullet under `[Unreleased]` in **both** `CHANGELOG.md` and `docs/_guide/changelog.md` (bodies byte-identical), stating what the battle test found and changed — honest, reference-style.
- **API index** (`docs/api/index.md`): 100 % of `__all__` (run the per-package script: import each package, diff `__all__` against the file).
- **Nav**: sidebar + `pages_order` for any new page (structural test enforces it).
- **Executed docs**: every Python block you add runs under `tests/test_docs_executable.py` (read its skip/fragment conventions first).
- **Landing page** (`docs/index.html`) only if the feature changes the pitch.

### 2.12 Gates before the PR is opened
```
python -m black --check src tests scripts examples --line-length=79
python -m flake8 src tests scripts examples --max-complexity=35 --select=B,C,E,F,W,T4,B9 --ignore=E203,E266,E501,W503,F403,F401,E402
python -m mypy src/xstate_statemachine
python -m pytest -q -p no:cacheprovider --disable-socket --allow-hosts=127.0.0.1,::1 --cov   # ≥90 %, a ratchet
.venv39\Scripts\python -m pytest <the feature's test folders> -q                             # real 3.9
python scripts/verify/<issue script>.py                                                     # ALL OK
python scripts/verify/wheel_gate.py --only <issue script stem>                              # against the wheel
python scripts/verify/_mojibake_scan.py
```
plus an **independent review agent** (the pattern used this cycle: a read-only reviewer with `opus`, findings ranked CRITICAL/HIGH/MEDIUM/LOW with file:line and a concrete failure scenario, then the implementer fixes each with a regression test). Both the G5 and G7 reviews found HIGHs the implementer had missed; do not skip this.

### 2.13 One at a time
**Finish one issue completely — code, tests, docs, review, merge — before starting the next.** Parallelism inside an issue (fan-out reviewers, parallel scenario authors in isolated worktrees) is fine and encouraged; parallelism *across* issues re-creates the shared-file conflict pain the plan documents. If you use the `Workflow` tool, pass `model` explicitly on every `agent()` (`sonnet` default, `opus` for review/verification, `fable` only for whole-system analysis) per the global model policy.

---

## 3. The inventory and the order

Work in **dependency order** (a flaw in persistence invalidates every battle test above it). Within a tier, follow the number order. Tiers 0–1 are the foundation — spend the most time there.

### Tier 0 — core prerequisites and programme gates (re-verify first)
| Issue | Feature | Owns |
|:--|:--|:--|
| #304 | `on_before_send` / `on_event_processed` hooks, `Receipt.duplicate`, `stub_logic()` | `base_interpreter.py`, `receipts.py`, `interpreter.py`, `sync_interpreter.py` |
| #305 | Snapshot v4, `wall_now()`, global plugin registry, `context_validator`, `send_threadsafe()` (sync) | same + `snapshots.py`, `clock.py` |
| #303 | X0 security baseline | `docs/_guide/security.md`, `tests/test_security_baseline.py`, `scripts/verify/303_x0_baseline.py` |
| #307 | Performance budgets | `benchmarks/`, `tests/test_perf_budgets.py`, perf CI job |

### Tier 1 — persistence and resilience (zero-dep core)
#258 scaffolding/extras · #259 stores (Memory/File/SQLite) · #260 locking (optimistic/pessimistic/none, `persisted()`) · #261 idempotency inbox · #262 audit/transition log + `replay()` · #263 versioning + `SnapshotMigrator` · #264 durable `after` timers + `DueTimerScanner` · #265 patterns (`RetryPolicy`, dead letters, `CircuitBreaker`) · #267 actor logic helpers · #306 `[redis]` stores with fencing.

### Tier 2 — typing, testing, graph, observability
#266 `[pydantic]` · #269 graph algorithms · #268 `[testing]` fixtures · #270 coverage gates · #271 Hypothesis model tests · #272 fake broker + replay helpers · #273 `[observability]` · #274 live inspector.

### Tier 3 — web
#275 `[starlette]` · #276 `[fastapi]` · #277 multi-worker guide + `fastapi_orders` · #278 `[litestar]` · #279 codegen companions · #309 adoption kit.

### Tier 4 — ORMs and Django
#284 `[sqlalchemy]` · #285 `[flask]` · #280 `[django]` field/mixin/store · #281 signals/audit/permissions/outbox · #282 admin + commands · #283 `[drf]` + `[channels]` · #310 `xsm_migrate_fsm` · #286 examples + comparisons.

### Tier 5 — event-driven
#293 EDA core (envelope, dispatcher, outbox, dead letters, `xsm dlq`) · #294 broker adapters (Redis Streams, Kafka, RabbitMQ, NATS, SQS) · #292 `[celery]` · #295 sagas / choreography / AsyncAPI.

### Tier 6 — agents and recipes
#287 `[agents]` TOOL_LOOP + guards · #288 LangGraph interop · #289 pydantic-ai + structured output · #290 multi-agent · #291 comparisons + support-bot · #308 recipes pack.

### Tier 7 — hardening and release
#296 1.0 hardening (discovery, compat matrix, deprecation policy) · #297 RC tracker (stays open until the maintainer publishes; close it with the release) · #257 epic (close last).

**Status at handover:** every issue above is CLOSED as *implemented* except #297 and #257. For the battle-test programme, **re-open nothing**; instead open one tracking issue `Battle-test programme (post-0.11.0)` with a checklist of the 43 features and link each `battle(<issue>)` PR to it. Add a `battle-tested` label and apply it to the original issue when its PR merges.

---

## 4. Known, documented limitations to attack first

These were found during implementation and *documented* rather than fixed. Each is a candidate for either a fix or a hard test that proves the documentation is exactly right:

- `AsyncSQLAlchemyStore` has no shared transaction with the caller's session.
- Dispatcher poison count is per process (a restart resets attempts unless the broker carries them — Kafka does not).
- A sync agent tool that overruns its timeout keeps running (the engine moves on).
- Reusing an async broker adapter from a new event loop closes the old client best-effort; buffered SQS messages keep counting down visibility.
- `lock="none"` + Django audit under concurrency can hit the unique `seq` constraint.
- Celery `connect_signals` can see a completion before the `_xsm_celery` record is saved → parked in `MemoryPendingResults` (per process; `poll_results` is the durable path).
- Redis Streams dead consumers accumulate (`XGROUP DELCONSUMER` documented, not automated).
- SQS FIFO 5-minute dedup window vs `xsm dlq replay` with the same id.
- The Stately Inspector UI was never clicked through manually.
- Live broker suites (`XSM_CONTAINERS=1`) have run only on one laptop with Docker, never in GitHub CI.
- Perf budgets: only `plugins_*` rows re-recorded this cycle; others carry the original baseline.

---

## 5. Working agreement with the maintainer

1. **No publish, tag, version bump or `publish.yml` run without the maintainer's explicit written go.** 0.11.0 is in PR #362 awaiting that go; the battle-test programme targets the release *after* it. Branch from `main` once #362 merges (or from `rc/0.11.0` if it has not).
2. One PR per issue; conventional commits; `Co-Authored-By: Claude <noreply@anthropic.com>` trailer (or the attribution line the session's system reminder specifies).
3. PR body = evidence: what was attacked, what broke, what was fixed (with the regression test name), what was documented, numbers (iterations, soak duration, p50/p99, RSS), and the independent review's findings with their resolutions.
4. Anything that contradicts a stated **Guarantee** is a release blocker: stop, fix, add to the changelog's Fixed section, re-run the X0 script.
5. Shared files (changelogs, `default.html`, `search-index.json`, `pyproject.toml`, `ci.yml`, `INTEGRATION_PAGES`, README, API index, compat matrix) are edited in the **last** commit of a PR, and conflicts are resolved keep-both.
6. Report to the maintainer after each tier with a one-screen summary; ask before changing any public API shape (provisional `contrib` or not — the maintainer decides what users see).

---

## 6. Quick-start for the incoming agent

```
git fetch origin && git checkout main && git pull
python -m pip install -e ".[all]" "fakeredis[lua]>=2.20" "moto[sqs]>=5" "opentelemetry-sdk>=1.20" pytest-django drf-spectacular daphne django-fsm-2 testcontainers psutil pytest-timeout
py -3.9 -m venv .venv39 && .venv39\Scripts\python -m pip install --only-binary :all: -e ".[all]"
python -m pytest -q -p no:cacheprovider --disable-socket --allow-hosts=127.0.0.1,::1      # expect ~5 460 passed
python scripts/verify/wheel_gate.py                                                        # expect 30/30 ALL OK
gh issue create --title "Battle-test programme (post-0.11.0)" --body-file <checklist from §3>
```
Then start with **#304** (Tier 0) and follow §2 to the letter.

---

*Previous handovers for style: `HANDOVER_268_testing_plugin.md`, `HANDOVER_307_perf_budgets.md`, `HANDOVER_G2_G3_eda_observability.md`.*
