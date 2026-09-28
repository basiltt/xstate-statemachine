# Handover: implement issue #307 (X2 performance budgets) — xstate-statemachine

You are picking up **one issue** from a larger programme that another agent is driving. Do exactly this issue, as a single PR, and stop. Do not start other issues, do not touch the release, do not merge.

## 1. Repository and how to work in it

- Repo: `https://github.com/basiltt/xstate-statemachine` (main branch `main`). Clone it fresh; do **not** assume any local state.
- Read `AGENTS.md` first — it is the project's contributor contract (imports order, Black 79, flake8 flags, emoji comment conventions `🏛️ 📝 ⚠️ ⚡`, "silent acceptance is a bug", both engines must be covered, CHANGELOG format). Everything below is in addition to it, not instead of it.
- Python floor is **3.9**: no PEP 604 `X | Y` in runtime annotations, no `match`, no `asyncio.Event()` created outside a running loop, no `TaskGroup`.
- Windows note (in case you are on one): `uv run pytest` / `black.exe` may be blocked by application control. Use `python -m pytest`, `python -m black`, `python -m flake8`, `python -m mypy` directly. If you are on Linux/macOS, `uv run …` from `AGENTS.md` works.
- Install for development: `python -m pip install -e ".[redis,pydantic]" "fakeredis[lua]>=2.20" pytest pytest-cov pytest-asyncio pytest-socket mypy black flake8 flake8-isort`.

## 2. Non-negotiable rules (programme-wide)

1. **No release.** Never bump `__version__`, never tag, never run `publish.yml`, never touch PyPI. The maintainer publishes.
2. **Branch + PR only.** Branch name `feat/x2-perf-budgets`. Push to `origin`, open a PR against `main` with `gh pr create`. **Do not merge it** — the maintainer (or the other agent) merges after review. Do not force-push.
3. **Core stays zero-dependency.** Nothing under `src/xstate_statemachine/` except `contrib/` may import a third-party module. `tests/test_zero_dependency.py` enforces this in a subprocess with every non-stdlib import blocked; it must stay green. Benchmarks that need an extra (pydantic, fastapi) must `importorskip` and be skipped cleanly when the extra is absent.
4. **Both engines.** Anything you measure at the `send()` level is measured on `SyncInterpreter` *and* `Interpreter`.
5. **CI must be green on all 38 checks** before you hand back: lint (Black 79 + flake8 with `--max-complexity=35 --select=B,C,E,F,W,T4,B9 --ignore=E203,E266,E501,W503,F403,F401,E402`), full test matrix 3.9–3.14 Linux + Windows 3.9/3.14 + macOS 3.14, coverage ≥ 90 % (gate is `fail_under` in `pyproject.toml`; **never lower it**), build, `core-zero-dep`, and the `contrib` extras matrix. Run `python -m mypy src/xstate_statemachine` locally too — it must report no issues.
6. **Tests are deterministic.** Anything timing-based is **opt-in** behind `XSM_PERF=1` and must not run in the default job. The default job may only assert *what* is imported (import-time guard), never how long.
7. **No network in tests.** The default job runs `pytest --disable-socket --allow-hosts=127.0.0.1,::1`.
8. **Verification script** committed as `scripts/verify/307_perf_budgets.py` (plain Python, runs on Windows — no shell heredocs), printing `ALL OK` at the end. `scripts/verify/` is un-ignored in `.gitignore`; other scripts there show the shape.
9. **Docs are executable.** Any ```python block in `docs/_guide/*.md` that imports the package is executed by `tests/test_docs_executable.py`. Mark an intentionally partial snippet with `<!-- doc-fragment -->` on the line above the fence; mark one that needs an extra with `<!-- doc-requires: pydantic -->`.
10. **Changelog.** Add an entry under `## [Unreleased]` → `### Added` in **both** `CHANGELOG.md` and `docs/_guide/changelog.md` (they are kept identical). Reference `#307`.
11. **Commit message / PR body attribution.** End commit messages with `Co-Authored-By: Claude <noreply@anthropic.com>` (or your own agent's line) and PR bodies with `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Conventional-commit prefix: `perf(...)` or `ci(...)`.
12. **PR body** must include: Summary, Test plan (checkboxes, actually run), and the "Integrations checklist" block:
    ```
    - [x] Core stays zero-dependency.
    - [x] Both engines covered.
    - [x] Changelog / docs / verification script in this PR.
    - [x] This PR does **not** tag or publish a release.
    Closes #307.
    ```

## 3. The issue: #307 — X2 performance budgets

Read the full issue: `gh issue view 307`. Summary of what to build:

### 3a. `benchmarks/integrations_characteristics.py`
Extend the existing harness style (`benchmarks/production_characteristics.py` — same flags, `--json` output for CI). One function per row of the budget table in the issue. Rows that apply **now** (Phase A is done; later phases will add theirs):

| Measurement | Notes for you |
|:--|:--|
| `import xstate_statemachine` wall time | Measure in a **subprocess** (`python -X importtime -c "import xstate_statemachine"` or `time.perf_counter` around `subprocess.run`). Also measure with `[redis,pydantic]` installed but unused — it must not grow (contrib is lazy). |
| `persisted()` round-trip on `MemoryStore`, trivial machine | `from xstate_statemachine.persistence import MemoryStore, persisted`. Compare to a bare `SyncInterpreter.send`. |
| `persisted()` round-trip on `SQLiteStore` (WAL, `tmp_path`) | `SQLiteStore(path)`. |
| `IdempotencyPlugin` + `AuditPlugin` attached, 10k events | `from xstate_statemachine.persistence import IdempotencyPlugin, MemoryInbox, AuditPlugin, MemoryLog`. `IdempotencyPlugin(inbox, principal=lambda e: "p")`. Compare to bare send. (`PrometheusPlugin` does not exist yet — leave that row for the phase that adds it; say so in a comment.) |
| `on_before_send` + `on_event_processed` with **no** plugins | Overhead of the hook seams over a machine with an empty plugin list, both engines. |
| `context_validator` with a 20-field pydantic model per mutating action | `from xstate_statemachine.contrib.pydantic import context_model` — `importorskip("pydantic")`. |
| Snapshot v4 `get_snapshot` / `from_snapshot`, 50-state machine | Generate the machine programmatically. |
| `shortest_paths` on the largest corpus machine | Skip if no such helper exists yet (check `src/xstate_statemachine/`; it may arrive in a later phase) — record `null` and note it. |
| FastAPI row | **Skip** — the FastAPI extra is not shipped yet. Record `null`. |

Print a table; with `--json` emit `{"runner": {...platform info...}, "results": {row: {"p50_us": ..., "n": ...}}}`. Use `time.perf_counter_ns`, 7 repetitions, report p50.

### 3b. `benchmarks/budgets.json`
The first run **records the baseline**; budget = baseline × 1.25 as the issue says. Commit the file with the values from your run and the runner spec (OS, CPU, Python version). Rows you skipped are `null`.

### 3c. `tests/test_perf_budgets.py`
- Skipped entirely unless `os.environ.get("XSM_PERF") == "1"`.
- Runs each benchmark 7×, compares p50 to `budgets.json`, fails with a clear message naming the row, the measured value and the budget.
- Rows whose budget is `null` are skipped.

### 3d. Import-time guard in the **default** job (deterministic)
`tests/test_import_surface.py`: run `python -X importtime -c "import xstate_statemachine"` in a subprocess and assert that **no** module under `xstate_statemachine.contrib` and **no** third-party module (anything not stdlib and not `xstate_statemachine.*`) appears in the imported set. Reuse the stdlib-detection approach from `tests/test_zero_dependency.py` (it handles 3.9's lack of `sys.stdlib_module_names`). This test must run in the normal `test` job.

### 3e. Nightly CI job
Add a `perf` job to `.github/workflows/ci.yml` triggered on `schedule:` (nightly) and `workflow_dispatch:` only — **not** on PRs. Pinned runner (`ubuntu-latest` is acceptable; record the label), installs `.[redis,pydantic]`, runs `XSM_PERF=1 python -m pytest tests/test_perf_budgets.py -q` and uploads `benchmarks/last_run.json` as an artifact. Pin any new action to a commit SHA like the existing ones (`actions/checkout@3d3c42e5…`).

### 3f. Docs
`docs/_guide/production-characteristics.md` gains a §"Integrations" table with the recorded baselines, the runner spec, and one paragraph on how budgets work (baseline × 1.25, changes are reviewed edits to `budgets.json` with a changelog note). Follow the page's existing voice.

## 4. Things you need to know about the codebase (saves you an hour)

- `persisted(store, key, machine)` is a context manager yielding a **started** `SyncInterpreter`; `apersisted` is the async twin. `load_interpreter` / `save_interpreter` are the pieces.
- Plugins attach with `.use(plugin)` and are wrapped in `_SafePlugin`; the engine only pays for `on_event_processed` if some plugin overrides it (`_wants_event_processed`), which is exactly what the "no plugins" row measures.
- `SimulatedClock(wall_start=…)` exists but is irrelevant here; use `RealClock` (default).
- `MachineNode.structure_hash` and `create_machine(cfg, logic=stub_logic(cfg))` (from `xstate_statemachine.testing_utils`) let you run any corpus chart without real logic. Corpus lives in `tests/tests_cli/stately_machines/*.json`.
- `tests/contrib/conftest.py::requires_extra("pydantic")` is the skip decorator for extra-dependent tests.
- Existing perf-sensitive test that will catch a regression in the hot path: `tests/test_perf_hot_path.py` (or grep `test_perf`). Don't break it.
- Full local suite takes ~11 min: `python -m pytest -q -p no:cacheprovider --disable-socket --allow-hosts=127.0.0.1,::1`. Run it before opening the PR.

## 5. Definition of done

- [ ] `benchmarks/integrations_characteristics.py`, `benchmarks/budgets.json` (baseline recorded), `tests/test_perf_budgets.py` (XSM_PERF-gated), `tests/test_import_surface.py` (default job), nightly `perf` CI job, docs table, changelog ×2, `scripts/verify/307_perf_budgets.py`.
- [ ] `python -m black --check src tests benchmarks scripts --line-length=79`, flake8 with the flags above, `python -m mypy src/xstate_statemachine` all clean.
- [ ] Full suite green locally; PR opened; all 38 CI checks green; PR **not merged**.
- [ ] Reply on the PR (or to the maintainer) with: the baseline numbers, the runner spec, and any row you had to skip and why.

If anything in the issue conflicts with the codebase as it exists, follow the codebase, do the smallest honest version, and explain the deviation in the PR body. Do not expand scope.
