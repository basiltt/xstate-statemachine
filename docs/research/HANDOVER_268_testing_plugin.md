# Handover: implement issue #268 (B1 `[testing]` pytest plugin) — xstate-statemachine

You are picking up **one issue** from a larger programme that another agent is driving. Do exactly this issue, as a single PR, and stop. Do not start other issues, do not touch the release, do not merge.

Your previous hand-back (#307, PR #327) was merged as-is. Same working style, please: follow the codebase over the issue text where they disagree, do the smallest honest version, explain every deviation in the PR body.

## 1. Repository and how to work in it

- Repo: `https://github.com/basiltt/xstate-statemachine` (main branch `main`). Clone it fresh or `git fetch && git checkout main && git pull`; do **not** reuse `basil-tt-hpeprod-project-update` (deleted on merge).
- Read `AGENTS.md` first — it is the contributor contract (imports order, Black 79, flake8 flags, emoji comment conventions `🏛️ 📝 ⚠️ ⚡`, "silent acceptance is a bug", both engines must be covered, CHANGELOG format). Everything below is in addition to it.
- Python floor is **3.9**: no PEP 604 `X | Y` in runtime annotations, no `match`, no `asyncio.Event()` outside a running loop, no `TaskGroup`.
- Windows note: `uv run pytest` / `black.exe` may be blocked by application control. Use `python -m pytest`, `python -m black`, `python -m flake8`, `python -m mypy`. On Linux/macOS `uv run …` from `AGENTS.md` works.
- Install: `python -m pip install -e ".[redis,pydantic]" "fakeredis[lua]>=2.20" pytest pytest-cov pytest-asyncio pytest-socket hypothesis mypy black flake8 flake8-isort`.

## 2. Non-negotiable rules (programme-wide)

1. **No release.** Never bump `__version__`, never tag, never run `publish.yml`, never touch PyPI.
2. **Branch + PR only.** Branch `feat/b1-testing-plugin`. Push to `origin`, `gh pr create` against `main`. **Do not merge.** Do not force-push.
3. **Core stays zero-dependency.** Nothing under `src/xstate_statemachine/` except `contrib/` may import a third-party module. Two guards enforce this and must stay green: `tests/test_zero_dependency.py` (subprocess, every non-stdlib import blocked) and `tests/test_import_surface.py` (**your own** `-X importtime` guard from #307 — `import xstate_statemachine` must not load `contrib.*` or any third-party module). ⚠️ This is the one that bites this issue: a `pytest11` entry point is loaded **by pytest at start-up**, not by `import xstate_statemachine`, so the import guard is unaffected *as long as* `contrib/testing/__init__.py` does not get imported from core. Also `pytest` itself is a third-party module: `contrib/testing/` may import it, nothing else may.
4. **Both engines.** Fixtures ship for `SyncInterpreter` (`xsm_interp`) **and** `Interpreter` (`xsm_ainterp`).
5. **CI must be green on all checks** before you hand back: lint (Black 79 + flake8 `--max-complexity=35 --select=B,C,E,F,W,T4,B9 --ignore=E203,E266,E501,W503,F403,F401,E402` over `src tests benchmarks scripts`), test matrix 3.9–3.14 Linux + Windows 3.9/3.14 + macOS 3.14, coverage ≥ 90 % (`fail_under` in `pyproject.toml`; **never lower it**), build, `core-zero-dep`, `audit` (pip-audit over `[all]`), and the `contrib` extras matrix. `python -m mypy src/xstate_statemachine` must report no issues.
6. **Tests are deterministic.** No wall-clock timing assertions. Use `SimulatedClock`.
7. **No network in tests.** Default job runs `pytest --disable-socket --allow-hosts=127.0.0.1,::1`.
8. **Verification script** `scripts/verify/268_testing_plugin.py` (plain Python, runs on Windows — no shell heredocs, no `/tmp`; use `tempfile`), printing `ALL OK`.
9. **Docs are executable.** Any ```python block in `docs/_guide/*.md` that imports the package runs in `tests/test_docs_executable.py`. Mark a partial snippet with `<!-- doc-fragment -->` on the line above the fence; one needing an extra with `<!-- doc-requires: pytest -->`. A pytest test function in a docs block will *import* fine but not run — that is acceptable; mark it `doc-fragment` if it needs the `xsm_*` fixtures to exist.
10. **Changelog.** Entry under `## [Unreleased]` → `### Added` in **both** `CHANGELOG.md` and `docs/_guide/changelog.md` (kept identical; `tests/test_docs_site.py::TestGuideChangelogMirrorsRoot` checks). Reference `#268`.
11. **Attribution.** Commit messages end with `Co-Authored-By: Claude <noreply@anthropic.com>` (or your agent's line); PR body ends with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Conventional prefix `feat(testing): …`.
12. **PR body** must include Summary, Test plan (checkboxes actually run), the verify-script output, and:
    ```
    - [x] Core stays zero-dependency.
    - [x] Both engines covered.
    - [x] Integration page has the Guarantees and Threat model boxes.
    - [x] Changelog / docs / verification script in this PR.
    - [x] This PR does **not** tag or publish a release.
    Closes #268.
    ```

## 3. The issue: #268 — `[testing]` pytest plugin

Read `gh issue view 268` in full. **The "Review amendments" block at the top supersedes the body** where they conflict. Consolidated:

### 3a. Package: `src/xstate_statemachine/contrib/testing/`
- `__init__.py` follows `contrib/pydantic/__init__.py`: header comment block, docstring with the `pip install "xstate-statemachine[testing]"` line, then `require_extra("testing", "pytest")` **before** any pytest import (raises `MissingExtraError` naming the pip command when pytest is absent — `tests/contrib/test_extras_matrix.py` checks this contract for every subpackage on disk).
- `pytest_plugin.py` — the plugin module. `hypothesis` is **not** needed by B1 (B4 uses it); do not import it here.
- Registry already has `"testing": Extra("testing", ("pytest", "hypothesis"), 268)`. Fill `testing = []` in `pyproject.toml` → `["pytest>=8", "hypothesis>=6.100"]` (registry and pyproject must agree: `test_extras_matrix.py`). **Add the same two requirements to `[all]`** — `tests/test_security_baseline.py::TestActionsArePinned::test_audit_job_covers_every_shipped_extra` fails otherwise, because the `audit` job audits `[all]`.

### 3b. Entry point (review amendment)
`[project.entry-points.pytest11] xstate_statemachine = "xstate_statemachine.contrib.testing.pytest_plugin"` — **registered unconditionally** (hatch has no conditional entry points). Therefore the plugin must be a **complete no-op** in a project that installed the core only:
- The module must import cleanly with only `pytest` present (pytest is loading it, so pytest is present by definition). Do not import `hypothesis`, do not import anything from `contrib.pydantic`.
- Without the `xstate_machine` marker on a test, no fixture does anything and no option is required.
- `-p no:xstate_statemachine` opt-out must work (pytest's own mechanism — just make sure the plugin name is that).
- Consequence for **this repo's own test suite**: once the entry point exists, the editable install registers it, so our suite runs *with* the plugin loaded. Nothing in `tests/` may break because of that. Prefixed fixture names are what make this safe.

### 3c. Fixtures — all prefixed `xsm_` (review amendment)
| Fixture | What |
|:--|:--|
| `xsm_machine` | `MachineNode` built from the marker. Source may be a **JSON path** (relative to the test file, then rootdir), a **dict**, or a `MachineNode`. `logic=` is a dotted `"pkg.module:callable"` returning `MachineLogic`; when omitted, **`stub_logic(cfg)` from `xstate_statemachine.testing_utils`** (promoted to core in #304 — use it, not `cli/strategies/_trace.py`, which no longer exists). Marker kwargs `strict_config=`, `strict=` pass through to `create_machine`. |
| `xsm_clock` | `SimulatedClock()` from `xstate_statemachine.clock`. `clock.increment(ms)` advances; under the async engine it returns an awaitable (`_MustAwait`) — see `clock.py`. |
| `xsm_interp` | `SyncInterpreter(xsm_machine, clock=xsm_clock).start()`, `stop()` at teardown. |
| `xsm_ainterp` | Async twin. Requires pytest-asyncio: if `pytest_asyncio` is not importable, `pytest.skip` with a message naming the package. Use an `async` fixture that `await Interpreter(...).start()`s and `await …stop()`s. |
| `xsm_ran` | The list of executed action names when stub logic is in use. `stub_logic(cfg, ran=<list>)` appends every executed action name to the list you pass — create the list in the fixture, pass it through, return it. If `logic=` was given, `xsm_ran` is an empty list and the docs say so. |
| `xsm_store` | `MemoryStore()` from `xstate_statemachine.persistence`. |
| `xsm_send_all` | `xsm_send_all(interp, "A", "+500", "B")` — the `xsm simulate --events` grammar: `+N` is a clock advance in ms, anything else is an event type. **Reuse `parse_events_arg` from `cli/commands/simulate.py`** (join the args with `,`) rather than reimplementing. Sync only; the async variant `await xsm_asend_all(...)` if cheap, otherwise leave it out and say so. |
| `xsm_snapshot` | `xsm_snapshot(interp, path)`: assert the snapshot matches the file; `--xsm-update-snapshots` rewrites; mismatch fails with a **unified diff**. Compare state ids + context only; strip `version`, `snapshot_version`, `machine_hash`, timestamps, `deadlines` wall times — anything non-deterministic. Files must be byte-identical across runs (`json.dumps(sort_keys=True, indent=2)` + `\n`). |

Markers: `xstate_machine(source, *, logic=None, strict_config=None, strict=None)` and `xstate_guards_false("g1", "g2")`. The second maps directly onto `stub_logic(cfg, guards={"g1": False, "g2": False})` — unlisted guards default to `True`, and the mapping is held **by reference**, so a test can flip a guard between sends by mutating it (expose the mapping as `xsm_guards` if cheap). With `logic=` given, `xstate_guards_false` has nothing to act on: **fail loudly** with `pytest.UsageError` — silent acceptance is a bug. Register both markers in `pytest_configure` so `--strict-markers` projects don't error.

Options: `--xsm-version` (print library version, exit 0), `--xsm-update-snapshots`.

### 3d. Tests: `tests/contrib/testing/`
- `__init__.py` + `test_pytest_plugin.py`, decorated with `requires_extra("testing")` from `tests/contrib/conftest.py` where the module needs pytest… (it always does — pytest is running it; the decorator exists for the matrix cells where a *different* extra is absent, so here it is mostly documentary. Keep it for uniformity.)
- Use **`pytester`** (enable with `pytest_plugins = ["pytester"]` in that test module or a local `conftest.py`) to run inline test files against the plugin: every fixture, both markers, JSON path / dict / MachineNode sources, `logic=` dotted callable, stub default, `--xsm-update-snapshots` write-then-pass and mismatch-diff, `xsm_ainterp` skip message without pytest-asyncio (simulate by `monkeypatch`ing `sys.modules["pytest_asyncio"] = None`), `--xsm-version`, and **"no marker → nothing happens"**.
- `pytester` runs a subprocess or in-process pytest; `runpytest_inprocess` is faster and works with `--disable-socket`. Set `pytester.syspathinsert(ROOT / "src")` if the inline test imports the package.
- Add a **`testing` cell** to the `contrib` matrix in `.github/workflows/ci.yml` (list at ~line 156; the step installs `.[${{ matrix.extra }}]` and runs `tests/contrib/<extra>`). Look at how the `redis` cell adds `fakeredis` for the shape of a per-cell extra install; `testing` needs `pytest-asyncio` in the cell so `xsm_ainterp` is exercised, not skipped.

### 3e. Codegen companion
`xsm gt -t pytest --fixtures` (opt-in flag): the emitted test module uses `@pytest.mark.xstate_machine(...)` + `xsm_interp`/`xsm_clock` instead of building the interpreter by hand. Template is `src/xstate_statemachine/cli/strategies/pytest_scaffold.py`; CLI args in `cli/args.py`; existing CLI tests in `tests/tests_cli/`. Without the flag output is **unchanged** (golden tests there will tell you). Keep this small — if it threatens scope, ship the plugin without it and say so in the PR body; it is the lowest-value bullet.

### 3f. Docs
- `docs/_guide/integration-testing.md` from **`docs/_templates/integration-page.md`**: keep every section (Install / Quick start / Reference / **Guarantees** / **Threat model** / Compatibility / Troubleshooting). `tests/test_docs_site.py::TestIntegrationsSection` enforces the boxes; **add `"integration-testing"` to `INTEGRATION_PAGES`** there, add the sidebar link and `pages_order` entry in `docs/_layouts/default.html` (Integrations section, after Pydantic), and a row in `docs/_guide/integrations.md`'s extras table (the test `test_overview_lists_every_registry_extra` already passes because `testing` is listed as planned — update its status).
- Threat model box for a test plugin is short but real: it imports a user-supplied dotted callable (`logic=`) — trusted code, same as `LogicLoader`; `--xsm-update-snapshots` writes files under the test tree only; snapshot files may contain `context` in clear text.
- Add a search-index entry in `docs/assets/js/search-index.json` (hand-maintained JSON array; copy the shape of the `Pydantic` entry).

## 4. Things you need to know about the codebase (saves you an hour)

- `stub_logic(cfg_or_machine, *, ran=None, guards=True, service_results=None)` and `logic_names(...)` live in `src/xstate_statemachine/testing_utils.py`. `ran` is appended to by reference; `guards` may be a bool or a live mapping; `service_results` lets a test script `onDone` data. Stub services complete synchronously, so `onDone` fires in the same macrostep on both engines.
- `interp.matches("machine.state")`, `interp.can("EVENT")`, `interp.send_events([...])` exist on `BaseInterpreter`. `SyncInterpreter.send()` is **not** thread-safe; fixtures run in the test thread so that is fine.
- `create_machine(cfg, logic=…, strict_config=…, strict=…)` in `factory.py`.
- `SimulatedClock.increment(ms)` — sync engine: returns `None`; async engine: returns an awaitable that must be awaited (`_MustAwait` raises if dropped). `xsm_send_all` on the sync interpreter can call it directly.
- `MemoryStore` is `xstate_statemachine.persistence.MemoryStore`; `persisted(store, key, machine)` is the context manager if you want a `xsm_persisted` bonus — not required.
- `MissingExtraError` / `require_extra` are in `contrib/_compat.py`; the pattern is at the top of `contrib/pydantic/__init__.py`.
- Repo pytest config: `[tool.pytest.ini_options]` in `pyproject.toml`, `testpaths = ["tests"]`, `addopts = "-v --tb=short"`. There is **no** root `tests/conftest.py`; `tests/contrib/conftest.py` has `requires_extra`.
- Snapshot layout is v4 (`get_snapshot()` → JSON string; keys include `snapshot_version`, `machine_hash`, `machine_version`, `state_ids`/`value`, `context`, `deadlines`). Read `base_interpreter.get_snapshot` before choosing what to strip.
- Corpus for tests and the verify script: `tests/tests_cli/stately_machines/*.json`. `AdvancePayment.json` has root id `Advance payment flow` and top-level states `authenticating3DS, challenge, editing, failure, success`, so the issue's `interp.matches("Advance payment flow.success")` is a valid target — but check the event names and `after` delays in the JSON before copying the issue's `send_all(interp, "SUBMIT", "+2001")` literally.
- Full local suite ~11–13 min: `python -m pytest -q -p no:cacheprovider --disable-socket --allow-hosts=127.0.0.1,::1 --cov`. Run it before opening the PR. Expect the count to rise from 4278 + #307's additions.

## 5. Definition of done

- [ ] `contrib/testing/{__init__,pytest_plugin}.py`; `pytest11` entry point; `testing` and `[all]` extras filled in `pyproject.toml`.
- [ ] Fixtures `xsm_machine / xsm_clock / xsm_interp / xsm_ainterp / xsm_ran / xsm_store / xsm_send_all / xsm_snapshot`; markers `xstate_machine`, `xstate_guards_false`; options `--xsm-version`, `--xsm-update-snapshots`; no-op without the marker; `-p no:xstate_statemachine` works.
- [ ] `tests/contrib/testing/` with `pytester`; `testing` cell in the CI `contrib` matrix.
- [ ] `docs/_guide/integration-testing.md` with both boxes, in nav + `INTEGRATION_PAGES` + search index; `integrations.md` row updated.
- [ ] `xsm gt -t pytest --fixtures` (or an explicit deferral in the PR body).
- [ ] Changelog ×2; `scripts/verify/268_testing_plugin.py` → `ALL OK`.
- [ ] Black / flake8 / mypy clean; full suite green locally; PR opened; all CI checks green; PR **not merged**.
- [ ] Hand-back comment on the PR: what the plugin does when pytest-asyncio is absent, anything deferred, and the verify-script output.

If anything in the issue conflicts with the codebase as it exists, follow the codebase, do the smallest honest version, and explain the deviation in the PR body. Do not expand scope (no hypothesis strategies, no graph algorithms, no coverage collector — those are B2–B4).
