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

| Group | Issues | Owner | Branch | Why together |
|:--|:--|:--|:--|:--|
| **G1 Testing** | #268 B1, #269 B2, #270 B3, #271 B4 | agent A (this session) | `feat/g1-testing` | One extra `[testing]`, one package `contrib/testing/`, one docs page; B2's graph algorithms live in core `xstate_statemachine/graph.py` and unblock the `shortest_paths` perf row |
| **G2 EDA core** | #272 B5, #293 F2, #295 F4 | agent B | `feat/g2-eda-core` | `Envelope`/`BrokerAdapter` defined once (#272) and extended (#293, #295); all zero-dep core under `xstate_statemachine/eda/` + `patterns/saga.py` + `contrib/testing/broker.py` (**only** that file inside `contrib/testing/`); SQLite outbox instead of waiting on D5 |
| **G3 Observability & inspector** | #273 B6, #274 B7 | agent B (after G2) | `feat/g3-observability` | Both are plugin translations of the same hooks; `[observability]` extra + core `inspect/` package; CLI `xsm inspect --live`, `sim --record`, `replay` |
| **G4 Web** | #275 C1, #276 C2, #278 C4, #279 C5, #277 C3 | agent A (after G1) | `feat/g4-web` | Starlette core → FastAPI → Litestar share `StatechartRegistry`; C5 codegen and C3 example app depend on C2's router. `[starlette] [fastapi] [litestar]` extras. Re-record the FastAPI perf row |
| **G5 Django** | #280 D1, #281 D2, #282 D3, #283 D4, #310 D9 | agent B (after G3) | `feat/g5-django` | One test settings module, one `[django]`/`[drf]`/`[channels]` matrix cell set, one example app |
| **G6 SQLAlchemy & Flask** | #284 D5, #285 D6, #286 D7 | agent A (after G4) | `feat/g6-sqla-flask` | D7's examples/comparison pages need D1–D6 shipped; D5's transactional outbox plugs into G2's `OutboxStore` protocol |
| **G7 Brokers & Celery** | #294 F3, #292 F1 | agent B (after G5) | `feat/g7-brokers` | Adapters over G2's `BrokerAdapter`; testcontainers opt-in job; Celery Beat scheduler over the `DueTimerScanner` |
| **G8 Agents** | #287 E1, #288 E2, #289 E3, #290 E4, #291 E5 | agent A (after G6) | `feat/g8-agents` | One `[agents]` extra; recipes + `BudgetPlugin` + comparison pages |
| **G9 Adoption & recipes** | #308 B9, #309 C7 | whoever finishes first | `feat/g9-adoption` | Docs/CLI/GitHub-Action kit; independent of the extras but reads better once G4 exists |
| **G10 1.0 hardening** | #296 G1 | agent A, last | `feat/g10-hardening` | Entry-point discovery, compatibility-matrix CI, deprecation policy, `[all]` smoke |

Release-candidate issues (#297 A11, #298 B8, #301 E6, #299 C6, #300 D8, #302 F5) collapse into **two RCs**, cut by agent A with the maintainer's confirmation:

- **RC 0.11.0** after G1 + G2 + G3 merge (persistence foundation + testing + EDA core + observability = a coherent "durable, testable, observable" release). Before it: every open PR closed, README / landing page / getting-started "What's New" / API reference / changelog complete, `#307` budgets re-recorded, `#303` items re-verified, and the new surface **battle-tested**: the full matrix green, the perf nightly green three nights running, every example app smoke-tested in CI, and the verify scripts of every merged group re-run against the built wheel in a clean venv.
- **RC 0.12.0** after G4–G8 (+ G9/G10 if ready). Same gate.

The per-phase RC issues are closed by the two RC PRs with a comment pointing here.

## Working agreement per group

1. Rebase onto `main` at start; read the group's issues **and their "Review amendments" blocks** (they supersede the body).
2. Implement in dependency order inside the group; one commit per issue is fine, one PR per group.
3. Cross-group contracts are frozen at the protocol level and named here so neither agent waits on the other:
   - `BrokerAdapter`, `SyncBrokerAdapter`, `Envelope`, `OutboxStore`, `DeadLetterStore` — G2 defines in `xstate_statemachine/eda/`; G4/G5/G6/G7 import, never redefine.
   - `xsm_*` pytest fixtures, `FakeBrokerAdapter` — G1 defines the plugin; G2 adds `contrib/testing/broker.py` and registers nothing new in `pytest_plugin.py` (it re-exports).
   - `PrometheusPlugin`, `OpenTelemetryPlugin` — G3; G4's `instrument_app()` imports them.
   - `StatechartRegistry` (G4) is the model for `DjangoStore`/`SQLAlchemyStore` act-loops (G5/G6); the loop itself is `persisted()` from Phase A.
4. Before opening the PR: full suite locally, `python scripts/verify/G<n>_<name>.py` → `ALL OK`, PR body = Summary / Test plan / deviations / Integrations checklist / `Closes #…` for every issue in the group.
5. Reviewer (agent A) merges group PRs; the maintainer confirms releases only.
