# Grouped delivery plan — open issues of epic #257

Replaces one-PR-per-issue. Each **group** is one branch, one PR, one changelog block, one verification script (`scripts/verify/G<n>_<name>.py`), reviewed and merged as a unit. Issues stay open until the group PR merges (`Closes #a, #b, …` in the body). Group boundaries are drawn so two agents never edit the same files at the same time.

Every group still obeys the programme rules: no release, no version bump, no merge by the implementer, Black 79 / flake8 / mypy clean, coverage ≥ 90 %, both engines, X0 baseline items cited (`docs/_guide/security.md`), integration pages from `docs/_templates/integration-page.md` with Guarantees + Threat-model boxes, changelog ×2, docs executable.

## Shared-file protocol (the only way two agents avoid conflicts)

These files are touched by every group. Edit them **only at the very end** of a group, in a dedicated final commit, after rebasing onto `main`:

- `CHANGELOG.md` + `docs/_guide/changelog.md` — one bullet block per group, newest on top.
- `docs/_layouts/default.html` — sidebar link + `pages_order`.
- `docs/assets/js/search-index.json`.
- `pyproject.toml` extras + `[all]`.
- `.github/workflows/ci.yml` — add matrix cells only; never restructure.
- `tests/test_docs_site.py::INTEGRATION_PAGES`.
- `src/xstate_statemachine/contrib/_registry.py` — already lists every extra; only `modules` tuples may change.

## The groups

| Group | Issues | Owner | Branch | Status |
|:--|:--|:--|:--|:--|
| **G1 Testing** | #268 B1, #270 B3, #271 B4 (+ the `[testing]` `path` fixture of #269) | **agent B** | `feat/b1-testing-plugin`, then `feat/g1b-coverage-hypothesis` | **#268 in review (PR #332)** — needs a rebase and the 6 fixes in the review; B3/B4 not started. Reference implementation on `wip/b1-pytest-plugin-reference` |
| **G1-core Graph** | #269 B2 core | agent A | `feat/g1-graph` | ✅ merged (#333) |
| **G2 EDA core** | #272 B5, #293 F2, #295 F4 | agent B (after G1) | `feat/g2-eda-core` | not started — `HANDOVER_G2_G3_eda_observability.md` |
| **G3 Observability & inspector** | #273 B6, #274 B7 | agent B (after G2) | `feat/g3-observability` | not started |
| **G4 Web** | #275 C1, #276 C2, #278 C4, #279 C5, #277 C3, #309 C7 | agent A | `feat/g4-web` | ✅ merged (#334, #338, #339, #342) |
| **G5 Django** | #280 D1, #281 D2, #282 D3, #283 D4, #310 D9 | agent B (after G3) | `feat/g5-django` | ✅ implemented on `feat/g5-django` (PR pending) |
| **G6 SQLAlchemy & Flask** | #284 D5, #285 D6, #286 D7 | agent A | `feat/g6-sqla-flask` | ✅ #284 (parts 1–2), #285 merged (#349); #286 examples + 3 comparison pages in progress; D5 outbox → #293; Django app → after G5 |
| **G7 Brokers & Celery** | #294 F3, #292 F1 | agent B (after G5) | `feat/g7-brokers` | not started |
| **G8 Agents** | #287 E1, #288 E2, #289 E3, #290 E4, #291 E5 | agent A | `feat/g8-agents` | ✅ merged (#346, #347) |
| **G9 Recipes** | #308 B9 | agent A | `feat/g9-recipes` | in progress |
| **G10 1.0 hardening** | #296 G1 | agent A, last | `feat/g10-hardening` | not started |

Core fixes found by battle-testing along the way (all merged): #337 keyword-named guards, #340 scaffold JSON lookup, #341 idempotency problems, #345 child-snapshot race, #348 sync `send(wait=True)` on a finished machine.

Release-candidate issues (#297 A11, #298 B8, #301 E6, #299 C6, #300 D8, #302 F5) collapse into **two RCs**, cut by agent A only with the maintainer's confirmation. Delivery order diverged from the phase plan (web, SQLAlchemy/Flask and agents shipped before the EDA core and observability), so the RC boundary is defined by **what is on `main` and battle-tested**, not by phase letters:

- **RC 0.11.0** = everything merged so far: persistence foundation, patterns, actor logic, graph, `[pydantic]`, `[redis]`, `[starlette]`/`[fastapi]`/`[litestar]`, `[sqlalchemy]`/`[flask]`, `[agents]`, the adoption kit, recipes and comparison pages — **plus `[testing]` (#332) if it lands in time**. Gate before the RC PR is opened: every open PR closed or explicitly deferred, README / landing page / getting-started "What's New" / API reference / changelog complete, `#307` budgets re-recorded on the reference runner, `#303` items re-verified, the full matrix green, the perf nightly green three nights running, every example app smoke-tested in CI, and every merged group's verify script re-run against the **built wheel in a clean venv** (the battle tests that found #340/#341/#348 stay in `scripts/verify/`).
- **RC 0.12.0** after G2 (EDA core), G3 (observability + inspector), G5 (Django), G7 (brokers/Celery) and G10 (1.0 hardening). Same gate.

The per-phase RC issues are closed by the two RC PRs with a comment pointing here.

> ⚠️ **No release without the maintainer's explicit confirmation.** Neither agent bumps `__version__`, tags, creates a GitHub release or runs `publish.yml`. An RC PR is opened, reviewed and left for the maintainer; the maintainer says go.

## Working agreement per group

1. Rebase onto `main` at start; read the group's issues **and their "Review amendments" blocks** (they supersede the body).
2. Implement in dependency order inside the group; one commit per issue is fine, one PR per group.
3. Cross-group contracts are frozen at the protocol level and named here so neither agent waits on the other:
   - `BrokerAdapter`, `SyncBrokerAdapter`, `Envelope`, `OutboxStore`, `DeadLetterStore` — G2 defines in `xstate_statemachine/eda/`; G4/G5/G6/G7 import, never redefine.
   - `xsm_*` pytest fixtures, `FakeBrokerAdapter` — G1 defines the plugin; G2 adds `contrib/testing/broker.py` and registers nothing new in `pytest_plugin.py` (it re-exports).
   - `PrometheusPlugin`, `OpenTelemetryPlugin` — G3; G4's `instrument_app()` imports them.
   - `StatechartRegistry` (G4) is the model for `DjangoStore`/`SQLAlchemyStore` act-loops (G5/G6); the loop itself is `persisted()` from Phase A.
4. Before opening the PR: full suite locally, `python scripts/verify/G<n>_<name>.py` → `ALL OK`, PR body = Summary / Test plan / deviations / Integrations checklist / `Closes #…` for every issue in the group.
   **Also run the new/changed test files under a real Python 3.9 interpreter** (`py -3.9 -m venv .venv39` or `uv python install 3.9`; `pip install -e ".[<extras>]"` there). mypy cannot pin 3.9 any more, so the 3.9 CI cell is the only compatibility gate — and it has already caught `asyncio.Lock()` at construction (#334) and `Path.write_text(newline=)` (#342), both green on 3.14. Twenty seconds locally beats a red matrix an hour later.
5. Reviewer (agent A) merges group PRs; the maintainer confirms releases only.
