# Why python-statemachine gets 1.4M downloads/month and we get ~14k

**Date:** 2026-10-19
**Subject:** `xstate-statemachine` 0.11.0 vs `python-statemachine` 3.2.2 (fgmacedo), with `transitions` 0.9.3 as a reference point
**Method:** four parallel research streams — (1) competitor feature/API/docs inventory from their docs, PyPI and GitHub; (2) download forensics via pypistats, pepy and the ClickPy ClickHouse dataset, plus reverse-dependency scans; (3) an audit of our own PyPI page, README, docs site, GitHub surface and first-run experience; (4) a hands-on probe writing the same seven scenarios in both libraries and recording code, output and error messages. The three DSL defects listed in §4.2 were re-verified by hand against this checkout.

---

## 1. Executive summary

**The download gap is not a feature gap and it is not a performance gap.** On raw capability we are ahead (persistence, locking, snapshots, actor system, web integrations, XState JSON portability) and on throughput we are roughly 10x faster. The gap comes from three places, in order of weight:

1. **Distribution, not product.** python-statemachine's 1.4M/month is ~98% Linux, ~71% installed by `uv`, with a 3.2x weekday/weekend ratio and five pinned versions (3.2.1, 3.2.0, 2.6.0, 2.5.0, 3.2.2) carrying the bulk. That is CI pipelines, lockfiles and containers re-installing a dependency, not 1.4M humans choosing a library. Our own ~14k/month is the same phenomenon in miniature: one pinned version (0.9.1) is 65% of it and it runs flat on weekends. Genuine human first-installs for them are probably 70–200k/month; for us, a few hundred.
2. **A storefront that repels the median searcher.** Someone who typed "python state machine" wants a 20-line FSM. They land on a 3,234-line README (theirs: 400) that leads with a JSON dict, a Stately screenshot, LLM agents, Stripe webhooks and an event-driven-architecture section, with the Python class API 70% of the way down. The PyPI description is 164 KB with broken relative image links, the GitHub repo has no description and no topics, and the summary line says "parsing and running XState JSON state machines", which reads as "you must know a JavaScript library".
3. **A Pythonic DSL that is a compile-to-JSON layer, not a Pythonic state machine.** Theirs: `cycle = green.to(yellow)`, `sm = TrafficLight(); sm.cycle(amount=3)`, `def on_enter_red(self)`. Ours requires `event="CYCLE"` repeated on every arm, a mandatory 4-argument callback signature, string-named guards/actions, a `create_machine()` call plus a separate interpreter object, and it silently ignores an `on_enter_red` method. Nested compound states in the class body silently drop their transitions (§4.2).

**What they have that we must match** is concentrated in developer experience: dependency-injected callbacks, naming-convention hooks, an instance-level API, event-named methods, definition-time validation of callback references, and docs that are 100% doctested with diagrams generated from the code.

**What we have that they lack** — and should lead with — is everything after the machine leaves memory: versioned snapshots, durable `after` deadlines, optimistic/pessimistic locking, an audit trail, Django/SQLAlchemy/FastAPI/Litestar plumbing, an actor system, and XState/Stately round-tripping. Their users are asking for exactly this (issues #597, #618 request a snapshot/persistence API; HN users describe it as "the tool I kept reaching for" but insufficient for versionable workflows).

---

## 2. Where the 1.4M downloads actually come from

### 2.1 Headline numbers (pypistats, 2026-10-19)

| Package | Last day | Last week | Last month | Stars | Contributors | First release |
|---|---|---|---|---|---|---|
| transitions | 23,287 | 457,665 | 2,479,626 | 6,602 | 64 | 2014 |
| python-statemachine | 17,631 | 368,707 | 1,391,217 | 1,324 | 26 | 2017 |
| xstate-statemachine | 1,024 | 5,431 | ~13,700 (pepy/ClickPy; pypistats month figure is stale) | 18 | 3 | 2025-07 |

Stars do not predict downloads: python-statemachine has one fifth of transitions' stars and 58% of its downloads.

### 2.2 The traffic is automation

| Signal | python-statemachine | transitions | xstate-statemachine |
|---|---|---|---|
| Linux share | 97.9% | 97.4% | — |
| `uv` installer share (30d) | 71% (986k) vs pip 313k, poetry 55k | 69% | — |
| Weekday / weekend daily avg | 58.4k / 18.4k (3.2x) | 108k / 30k | 270 / 260 (flat) |
| Mirror inflation | 0.5% | similar | ~30% |
| Top pinned versions (30d) | 3.2.1: 366k · 3.2.0: 328k · 2.6.0: 243k · 2.5.0: 230k · 3.2.2: 77k | — | 0.9.1: 9,013 of ~13.7k |
| Release-day pull (3.2.2, 2026-10-14) | 14.7k, 43.3k, 13.0k on days 1–3 | — | — |

Reading: a 3.2x weekday ratio is developer and CI activity, not a bot farm, but it is *repeat installs of pinned versions*, not discovery. 2.x pins (released Dec 2024 / Feb 2026) are still 34% of traffic. Growth is almost entirely `uv`: 16k/month in Jan 2025 → 1.10M in Sep 2026, while pip stayed in the 140–470k band. In other words, the same consumers re-resolving lockfiles faster and more often.

### 2.3 Growth history (ClickPy, monthly)

| Month | Downloads |
|---|---|
| Sep 2022 | 23.8k |
| May 2023 | 175k |
| Jan 2025 | 251k |
| Jul 2025 | 597k |
| Feb 2026 | 830k |
| Mar 2026 | 1.05M |
| Jun 2026 | 1.49M (peak) |
| Sep 2026 | 1.44M |

Yearly: 2022 296k · 2023 1.12M · 2024 1.93M · 2025 5.54M · 2026 YTD 11.07M. There is no single step; it is a staircase of lockfile adoption over four years. Nine years of existence matters here — we are fifteen months old.

### 2.4 Who depends on it

Declared PyPI dependents: 47 distinct packages (requires_dist scan); deps.dev 33; libraries.io 59 packages / 37 repos; GitHub dependents graph ~749 repos / 63 packages. Top dependents by their own 30-day downloads:

| Dependent | 30d downloads | Note |
|---|---|---|
| archivebox | 94k | 28.8k stars; `python-statemachine[diagrams]>=2.3.6` |
| ai-parrot family (28 pkgs) | ~238k combined | pins `==2.5.0` — plausibly the whole 2.5.0 bar |
| wandelbots-nova | 23k | robotics SDK |
| gai-sdk | 6k | pins `==2.5.0` |

No Apache project, Home Assistant, Airflow provider, ROS or LLM framework depends on it. Summing every declared dependent's own downloads gives at most ~380k, i.e. **a ceiling of ~27%** of traffic is transitive. The remaining ~70–80% is direct consumers' requirements/lockfiles — public and private repos, CI, containers. GitHub code-search footprint: ~631 `requirements.txt`, ~200 `pyproject.toml`, ~151 `uv.lock` for them; 4, 4 and 0 for us.

**Estimate:** ~1–2% mirror/scanner noise · ~15–25% transitive via dependents · ~70–80% direct lockfile consumers · of which genuine first-time human installs are perhaps 5–15% of the total (70–200k/month).

### 2.5 Discoverability

- **Name.** "python-statemachine" is a near-exact match for the query "python state machine" on PyPI, readthedocs and GitHub. Our name only wins queries containing "xstate".
- **DuckDuckGo "python state machine":** results 1–4 are python-statemachine (PyPI, two readthedocs pages, GitHub), then askpython, then the transitions repo. We are not in the top 9. (Google/Bing could not be scripted; treat as indicative.)
- **awesome-python (328k stars):** python-statemachine is the *only* state-machine entry, added 2026-08-23 "as a challenger to transitions" on the strength of pepy download numbers. transitions was removed 2026-10-02 for inactivity. CONTRIBUTING.md says download counts are the primary evidence and challenger slots need "adoption-trajectory evidence". A slot is open; our numbers are not yet strong enough to take it.
- **Stack Overflow:** no `python-statemachine` tag; `pytransitions` has 55 questions. Title hits: pytransitions 66, python-statemachine 34, xstate-statemachine 4.
- **GitHub repo metadata (verified 2026-10-19 via `gh api`):** ours has `description: null`, `homepage: null`, `topics: []`, Discussions disabled. Theirs: "Expressive statecharts and FSMs for modern Python", 17 topics, Discussions enabled.
- The official `statelyai/xstate-python` is "work in progress" at 198 stars — the "xstate python" query is ours to own.

---

## 3. What python-statemachine does that makes users like it

### 3.1 The DSL (the core of its appeal)

```python
from statemachine import State, StateChart

class TrafficLight(StateChart):
    green = State(initial=True)
    yellow = State()
    red = State()

    cycle = green.to(yellow, cond="can_cycle") | yellow.to(red) | red.to(green)

    def can_cycle(self, amount=1):          # guard; kwargs injected by name
        return amount < 10

    def on_enter_red(self):                 # naming-convention hook
        print("Don't move.")

    def on_cycle(self, amount=1):           # return value comes back from send()
        self.count += amount
        return f"counted {amount}"

sm = TrafficLight()
sm.send("cycle", amount=3)                  # -> [None, 'counted 3']
sm.cycle(amount=2)                          # events are methods
sm.green.is_active                          # True/False
f"{sm:mermaid}"                             # diagram without Graphviz
```

The specific mechanics that produce the "it just feels right" reaction:

| Mechanism | Spelling |
|---|---|
| Event inferred from the attribute name | `cycle = green.to(yellow)` |
| Transition composition | `a.to(b) \| b.to(c)`, `target.from_(a, b)`, `target.from_.any()`, `s.to.itself(internal=True)` |
| Guards | `cond="is_valid"`, `cond=["a","b"]`, `unless="x"`, callables, **string expressions** parsed with `ast`: `cond="has_key and not is_locked_out"`, `cond="count > 0 and count <= 10"`, `In('state-id')` |
| Callback groups, documented order | `prepare_event` → validators → cond/unless → before → exit → on → enter → invoke → after |
| Naming conventions | `before_<event>`, `on_<event>`, `after_<event>`, `on_enter_<state>`, `on_exit_<state>`, `on_invoke_<state>`, plus generic `before_transition`, `on_transition`, `on_enter_state`, `on_exit_state` |
| Three binding styles | naming convention, inline (`on="do_work"`, `enter=`, `invoke=`), decorator (`@state.enter`) |
| **Signature-based dependency injection** | callbacks declare only what they need: `event`, `source`, `target`, `state`, `error`, `model`, `machine`, `transition`, `event_data`, `previous_configuration`, `new_configuration`, and any `send(**kwargs)` |
| Return values | `sm.send("go")` returns the callbacks' return value(s) |
| Instance API | `sm.configuration`, `sm.green.is_active`, `sm.allowed_events`, `sm.enabled_events(**kw)`, `sm.is_terminated` |
| Definition-time validation | missing callback names raise `InvalidDefinition` at instantiation; trap states, unreachable states and final reachability are checked by default |
| Statecharts in the class body | `class paid(State.Compound): ...`, `class fulfil(State.Parallel): ...`, `HistoryState(type="deep")`, `done_state_<id>` events, `donedata` |
| Runtime | `send(event, delay=500, send_id=)`, `cancel_event()`, `raise_()`, internal vs external queues, SCXML prefix matching (`error` matches `error.send.failed`), `*` wildcard, thread-safe sync `send()` |
| Async | auto-detected: any `async def` callback switches the engine; `await sm.send(...)`; per-caller results under `asyncio.gather` |
| Invoke / timeout | `State(invoke=fetch)`, child `StateChart` classes, `invoke=timeout(30, on="request_timeout")` |
| Listeners | `listeners=[...]`, class-level `listeners = [AuditListener]`, models are listeners too |
| Models / Django | `StateChart["OrderModel"]` generic, `MachineMixin` with `state_field_name`, `bind_events_as_methods`, Django autodiscovery of `statemachine(s).py` modules |
| Diagrams | `sm._graph().write_png()` (Graphviz), `f"{sm:mermaid}"`, `:md`, `:rst`, `:dot`, `:svg`, Jupyter `_repr_svg_`, a CLI, a **Sphinx directive** that renders the diagram from an importable class path, `{statechart:md}` docstring expansion |
| IO (3.2) | `statemachine.io.load("x.yaml")` for SCXML/JSON/YAML with a published JSON Schema and a restricted expression evaluator (their own schema, *not* XState JSON) |
| Conformance | W3C SCXML suite (212 files) in the tests; OMG PSSM (103 cases) landing in 3.3.0 |

### 3.2 The docs

- Furo on readthedocs; ~35 pages in a strict learning order: Installation → Tutorial → Concepts (states/transitions/events/actions/guards) → Runtime → Configuration → Advanced → IO → How-to ("Coming from pytransitions", "Coming from the State Pattern") → API autodoc → auto-generated example gallery (27 machines) → per-release notes and an upgrade guide.
- **Every `>>>` block in every page and the README is a doctest** (`--doctest-glob=*.md`). Diagrams are generated from code by the Sphinx directive, so they cannot drift.
- README: 400 lines, six live badges (pypi, pepy total, pepy monthly, codecov, readthedocs, commits-since-release), 12-line quickstart, then Guards → Compound → Parallel → History → Eventless → Error handling → Installing.

### 3.3 Weaknesses users report (our openings)

- **No persistence/snapshot API.** #597: compound/parallel configuration is an `OrderedSet` that does not map to a DB column. #618 asks for versioned snapshot/restore. HN (2026-01): insufficient for "versionable declarative workflows".
- **Throughput.** Our `benchmarks/competitors/results.json` (self-run, treat with caution): flat toggle 7,365 ev/s vs our sync 71,210 and transitions 124,773; hierarchical 2,901 vs 28,501; parallel 2,537 vs 25,349; construction 854/s vs 8,684/s. 3.1.0 claimed a 5–7x speedup over 3.0; it is still an order of magnitude behind.
- **String-named callbacks defeat IDE refactoring** (#417); pyright support only arrived in 3.0.
- **Lenient `StateChart` mode swallows callback exceptions** (DEBUG log only) and returns `None` for disallowed events — verified in §4.3.
- **Sync engine blocks the thread on `send(delay=)`** (their bug #706); `timeout()` is seconds while XState/ours is ms.
- **3.0 breakage**: Python 3.7/3.8 then 3.9 dropped; `current_state` deprecated; `add_observer()` removed; three security releases (CVE-2026-47103: `eval`/`exec` in the SCXML loader) in 3.2.x.
- **Single maintainer** (507 of ~570 commits), 43 open issues, no parent↔child messaging from Python (#576), no dynamic parallel regions (#616).

---

## 4. Where we actually fall short — verified

### 4.1 Storefront and onboarding

| Surface | xstate-statemachine 0.11.0 | python-statemachine 3.2.2 |
|---|---|---|
| PyPI summary | "A robust Python library for parsing and running XState JSON state machines." | "Python Finite State Machines made easy." |
| PyPI description | 163,869 chars / 3,234 lines; **24 relative links** (hero SVGs, machine PNGs, `CONTRIBUTING.md`, `LICENSE`, `pyproject.toml`) that 404 or do not render on PyPI | 11,272 chars / 400 lines; absolute `raw.githubusercontent.com` images |
| Development Status | 4 – Beta | 5 – Production/Stable |
| README | 3,234 lines, 18.7k words, 32 H2 / 90 headings; first code at line 98 after ~514 words, 8 badges, a pitch table and a collapsed 15-row TOC; first example is a **JSON dict**; "Prefer pure Python?" at line 2,257 (70% down) | 400 lines; quickstart is the Python class |
| Badges | 8, half self-asserted static shields ("tests: regression_tested", "coverage gate 90%") | 6 live badges |
| Taglines | four different ones across PyPI / README / docs / release title | one |
| GitHub | description `null`, homepage `null`, topics `[]`, Discussions off, 1 issue template, 2 open issues (both internal epics), 18 stars | description set, 17 topics, Discussions on, 1,324 stars |
| Release cadence | 23 releases in 15 months; 12 since Aug 10; **6 between Sep 23–25** | ~monthly |
| Docs site | 70 guide pages / 242k words; `pythonic-api.md` alone is 1,717 lines ("50 min read"); hand-written API reference ("87 min read"); no `sitemap.xml`/`robots.txt`; stale "v0.8.0"/`"0.7.0"` in API page chrome; `getting-started.md` shows 4 CLI commands (real: ~24) and lists `machine.py`, `snapshot.py`, `plugin.py`, `diagram_exporter.py` which do not exist | ~35 pages, linear, autodoc |
| Import time (`-X importtime`) | 1,253 ms cumulative; 4.5 MB / 272 `.py` files | 343 ms; 646 KB / 63 files |
| First-run on Windows | `xsm.exe` blocked by WDAC on this machine (documented only in a collapsed `<details>`); `python -m xstate_statemachine` works | n/a |

Strengths worth keeping: the README's honesty ("pick python-statemachine if you want a beautiful, pythonic declarative API"), and `tests/test_docs_executable.py` executing every Python block in README and guides — we match their doctest discipline and do not advertise it.

### 4.2 The Pythonic DSL — hands-on probe

Same traffic light in both (non-blank definition lines, incl. imports): theirs 26, ours 33. Same order lifecycle with compound + parallel + 100 ms timeout: theirs 26, ours 21 — but only by falling back to JSON-shaped `State("paid", states=[...], on_done="fulfil")` kwargs.

| python-statemachine capability | Ours (verified 2026-10-19) |
|---|---|
| Event inferred from attribute name | **No.** `State.to()` raises `InvalidConfigError` without `event=`; the attribute name is unused |
| `on_enter_<state>` / `on_exit_<state>` / `before_<event>` / `on_<event>` by convention | **No, and silent.** An undecorated `on_enter_yellow` never fires; a typo `on_enter_yelow` raises nothing. Only `@yellow.enter` works |
| Callback kwargs injected by name | **No.** Fixed `(self, interpreter, context, event, action_def)`; read `event.payload["amount"]` |
| Instance API: `sm = TrafficLight(); sm.send()` | **No.** `AttributeError: no attribute 'send'`. You hold three objects: class, `MachineNode`, interpreter |
| `sm.cycle()` event methods | **No.** `TrafficLight.cycle` is a `TransitionGroup` (mypy: `"TransitionGroup" not callable`) |
| `sm.green.is_active`, `sm.configuration` | **No.** `AttributeError: 'State' object has no attribute 'is_active'`; runtime state lives on the interpreter as string IDs |
| `send()` returns callback values | **No.** Returns `None`, or a `Receipt` with `wait=True`; action return values are dropped |
| Generic `before_transition` hook | **No.** Nearest is a `PluginBase.on_event_received` plugin; `on_transition` fires *after* |
| `cond="a and not b"` expressions, `unless=`, `In()` | **No.** `guard=` takes one registered name |
| Compound/parallel in the class body | **Broken.** Children declared as class attributes leak to the root (`root keys=['created','packing','shipped','paid']`, `paid.initial=None`); with `initial=True` on a child: `InvalidConfigError: Multiple initial states: created, packing`. **Transitions declared inside a nested `class paid(State):` body are silently dropped** (sending `SHIP` leaves `{'v.paid.packing'}`). **A nested class cannot be a `.to()` target**: `AttributeError: type object 'paid' has no attribute 'name'`. `class paid(State, on_done="closed")` → `TypeError: __init_subclass__() takes no keyword arguments` — nested form accepts only `initial`/`final`/`parallel`, so `after`, `on_done`, `history`, `tags`, `entry` force the `State(...)` kwarg form |
| History in the DSL | Only `State("resume", history="deep")` inside `states=[...]`, targeted by string |
| Definition-time validation of callback names | **No.** `create_machine()` succeeds; `ImplementationMissingError: Guard 'isAllowed' not implemented.` arrives at the first `send`. (`logic_names(machine)` exists but is not called) |
| Disallowed event | Silent `None`, status `running`. `strict=True` only catches *undeclared* events (`UnknownEventError ... Did you mean 'GO'?`), not declared-but-not-enabled ones, and **cannot be set from the class DSL** |
| Service sees the triggering event payload | **No.** Service receives `Event invoke.f.loading {'input': {}}`; `send("START", url=...)` payload is gone, so you add a second action to copy it into context. No `@loading.invoke` decorator |
| Start at a given state (state-string persistence) | **No** `SyncInterpreter(machine, state="flow.review")`. Either a full versioned JSON snapshot or a hand-built `PureSnapshot` where you supply the ancestor set yourself. (Theirs: `Flow(row, state_field="status")`, `Flow(start_value="review")`, `MachineMixin`) |
| `repr()` | Interpreter: `<...SyncInterpreter object at 0x...>`; `MachineNode`: `StateNode(id='L', type='compound')`. Theirs: `TL(model=Model(state=green), state_field='state', configuration=['green'])` |
| Flat `states` / `events` lists | No; walk `m.states` yourself. `m.known_events` exists |
| `.to_json()` | **Does not exist** (`hasattr` → `False`) yet `docs/_guide/pythonic-api.md` line 17 advertises it |
| Mermaid fidelity | `to_mermaid()` omits the `after` edge, final-state `--> [*]`, and parallel `--` separators |
| Docs drift | `pythonic-api.md` `storeError` example uses `e.data` → `DeprecationWarning: ErrorEvent.data is deprecated since 0.9.0 ... use ErrorEvent.error` |
| Typing | `context`/`event` are `Any` in decorated callbacks; under the repo's strict mypy, un-annotated callbacks error (`Call to untyped function "count"`). Neither library type-checks event strings; theirs at least autocompletes `sm.cycle` |

Supported and working in our DSL: `|` composition, `internal()`, `reenter=True`, nested/parallel/history via kwargs, `after`, `always`, `on_done`, tags/meta.

### 4.3 Where ours is better (verified)

- **Runtime diagnostics:** ERROR log with traceback for a raising action (`🔥 Action 'boom' raised while handling event 'GO'; skipping remaining actions`), `Receipt.error`, `UnknownEventError ... Known events: BACK, GO. Did you mean 'GO'?`. Their default `StateChart` mode swallows callback exceptions at DEBUG and returns `None` for disallowed events.
- **Build-time target validation:** `InvalidConfigError: Machine 'T' has unresolvable transition targets: T.green: on 'GO' -> target 'yelow' does not resolve`.
- **Persistence:** versioned snapshots with `machine_hash` drift detection, `SnapshotMigrator`, durable `after` deadlines, `OptimisticLock`/`PessimisticLock`, Django `StatechartField` with `select_for_update()` and a same-transaction `TransitionLog`, SQLAlchemy `version_id_col`. They have none of this and their users ask for it.
- **Pure transition API** (`get_next_snapshot`, `PureSnapshot`) with no interpreter.
- **Native asyncio engine** that fires its own timers; theirs needs `await sm.activate_initial_state()` and blocks the sync thread on delays.
- **Web/DB plumbing:** FastAPI, Starlette, Litestar, Flask routers; DRF viewset mixin; Django admin mixin; Redis/SQLite/SQLAlchemy stores; brokers.
- **Actor system** (`spawn`, `sendTo`, `sendParent`); they can only invoke child machines.
- **XState JSON / Stately round-trip** — theirs is their own SCXML-flavoured schema.
- **Mermaid and PlantUML without a binary**; their PNG path needs system Graphviz.
- **Throughput:** ~10x on every scenario in `benchmarks/competitors/`.

---

## 5. Performance and documentation — direct answers

**Performance: not the problem.** Our sync engine is ~10x faster on flat, guarded, hierarchical and parallel scenarios and ~10x faster to construct (`benchmarks/competitors/results.json`). Two caveats a newcomer *does* feel: import time is 3.7x theirs (1.25 s vs 0.34 s cumulative, from 272 modules in a 4.5 MB install) and `xsm.exe` can be blocked by Windows application control. Neither explains the download gap; the first is worth trimming (lazy-import `contrib/`, `persistence/`, `cli/`).

**Documentation: the problem is shape, not quantity.** We have 6x their word count, every code block is executed in CI, and we have eight tested recipes and seven comparison pages. What we lack is (a) a linear on-ramp — theirs is Installation → Tutorial → Concepts; ours offers five quick-start options (A–E) before "What just happened?"; (b) a Python-first first impression — the first example is JSON and the newcomer is never told what XState/Stately is in one sentence; (c) hygiene — version strings, CLI listings and the project structure in `getting-started.md` are stale, the API reference is hand-maintained, there is no sitemap; (d) size — the PyPI page is the whole README and is unreadable.

---

## 6. Recommendations, ranked by leverage ÷ effort

### Tier 0 — storefront (days, no runtime change)

1. **One tagline, everywhere.** Replace the PyPI summary "parsing and running XState JSON state machines" with something like "State machines and statecharts for Python — define them in plain Python or load XState JSON." Use it on PyPI, the GitHub description, README and docs home.
2. **Fill in the GitHub repo:** description, homepage, topics (`state-machine`, `statechart`, `fsm`, `finite-state-machine`, `xstate`, `scxml`, `hsm`, `python`, `asyncio`, `django`, `fastapi`), enable Discussions, add a feature-request template. Five minutes; the repo is currently invisible to GitHub topic search.
3. **Python-first README, 300–500 lines.** Lead with the class-based traffic light (after the DSL fixes below, so it is genuinely 12 lines), then "the same chart as XState JSON / in Stately", then a one-paragraph "what is XState and why would I care". Move the 13 use cases, EDA, persistence, integrations, API reference, FAQ and troubleshooting to the docs site. Point `pyproject.toml` `readme` at a short PyPI-specific file if the long README must stay for GitHub.
4. **Fix PyPI rendering:** absolute `https://raw.githubusercontent.com/basiltt/xstate-statemachine/main/...` URLs for all 24 relative references. Add `Programming Language :: Python :: 3 :: Only`, `Topic :: Software Development :: Libraries`; move Development Status to 5 when the DSL is fixed.
5. **Live badges:** real downloads/month (pepy), codecov, docs status. Drop the self-asserted shields.
6. **Batch releases.** Six releases in three days reads as instability to an evaluator.

### Tier 1 — make the Pythonic DSL a credible answer (one minor release)

7. **Infer `event` from the attribute name** (`cycle = green.to(yellow)` ⇒ event `CYCLE`/`cycle`; keep `event=` as an override). Small.
8. **Honour naming-convention hooks** (`on_enter_<state>`, `on_exit_<state>`, `before_<event>`, `on_<event>`, `after_<event>`, generic `before_transition`/`on_transition`) and **warn on an unmatched `on_enter_*`/`on_exit_*` method** — today a typo is silent. Small.
9. **Signature-based kwarg injection** for class-DSL callbacks: inspect the signature; if it is not the 4-arg form, inject `context`, `event`, `interpreter` and `send(**kwargs)` by name. Backward compatible. Medium.
10. **Instance façade:** `sm = TrafficLight()` returns an object with `.send()`, event methods (`sm.cycle()`), `.state`/`.configuration`, `.is_active("green")` or `sm.green.is_active`, `.can()`, `.allowed_events`, a readable `__repr__`, and `strict=`/`engine=` as class attributes. The class, `MachineNode` and interpreter stay available underneath. Large, but this is the single change that decides whether the "Pythonic API" claim holds.
11. **Fix nested classes:** transitions inside `class paid(State):` must be kept (or raise), nested classes must be valid `.to()` targets, children must not leak to the root, and the nested form must accept `after=`, `on_done=`, `history=`, `tags=`, `entry=`/`exit=`. Medium. Ship `State.Compound`/`State.Parallel`-style aliases if cheap.
12. **Definition-time validation:** call `logic_names()` inside `StateMachine.create_machine()` and raise `ImplementationMissingError` listing every unbound guard/action/service, like their `InvalidDefinition ... Did not found name 'is_allowed'`. Small.
13. **`strict` catches declared-but-not-enabled events** too (`TransitionNotAllowed`-style), and is settable from the class. Small.
14. **Services receive the triggering event's payload** (e.g. `event.input` defaults to the triggering event payload, or a `@state.invoke` decorator with injection). Small/Medium.
15. **`SyncInterpreter(machine, state="flow.review", context=...)`** / `from_state_ids()` for the "state string on a model row" case. Small/Medium.
16. **Diagram fidelity:** `to_mermaid()` emits `after` edges, `--> [*]` for finals, `--` between parallel regions; implement or un-document `.to_json()`; fix `e.data` → `e.error` in `pythonic-api.md`. Small.
17. **Expression guards** (`cond="a and not b"`) via a restricted `ast` evaluator — they already paid the CVE tuition here; copy the allow-list design. Medium. Optional.

### Tier 2 — docs shape (one sprint)

18. **Linear on-ramp:** Installation → Tutorial (Python class) → Concepts → "Also: XState JSON & Stately" → Reference. Collapse Quick Start A–E to one recommended path. Add "Coming from python-statemachine" and "Coming from transitions" how-tos (their migration guides are a major conversion tool).
19. **Autodoc the API reference** (mkdocstrings or Sphinx autodoc) instead of the hand-written 87-minute page; fix the stale version strings, CLI list and project structure in `getting-started.md`; add `sitemap.xml`/`robots.txt`.
20. **Advertise what we already do:** "every code block in these docs is executed in CI" deserves a badge and a sentence, as does the SCXML-correct transition selection.

### Tier 3 — distribution (ongoing; this is what moves downloads)

21. **Get depended on.** One ai-parrot-scale dependent is ~240k/month; one archivebox-scale dependent is ~90k. Targets: agent frameworks that need "the model proposes, the machine decides", Stately/XState shops with Python backends, Django/FastAPI SaaS teams that need durable workflow state. Ship thin integration packages that pull `xstate-statemachine` as a dependency.
22. **Own the "xstate python" query.** The official `statelyai/xstate-python` is stalled; get linked from Stately community docs, XState examples and the Stately Discord. This is the one query where our name is the exact match.
23. **awesome-python challenger slot.** Open since transitions was removed on 2026-10-02; apply once Tier 0–1 land and the download trajectory is visibly rising, because download counts are their primary evidence.
24. **Be the library an AI assistant recommends.** A growing share of first installs comes from LLM-assisted coding; canonical, short, example-heavy README/docs and a stable API surface are what gets recommended.
25. **Realistic expectation.** The XState-JSON-to-Python niche alone will not produce 100k/month organically. Reaching it depends on one or two dependents with CI volume plus winning a share of the generic "python state machine" query, which Tier 0–1 make possible and Tier 3 executes.

---

## 7. Sources

Competitor: https://pypi.org/pypi/python-statemachine/json · https://github.com/fgmacedo/python-statemachine (pyproject, README, docs/, releases) · https://python-statemachine.readthedocs.io/en/latest/ (actions, guards, async, statechart, processing_model, behaviour, validations, timeout, listeners, integrations, diagram, io, releases/3.0.0–3.2.2, releases/3.3.0 unreleased) · issues #400 #417 #515 #576 #597 #613 #616 #618 #692 #706 · HN 45804140, 46714643.
Downloads: https://pypistats.org/api/packages/{python-statemachine,transitions,xstate-statemachine}/{recent,overall,python_minor,system} · https://pepy.tech/project/python-statemachine · https://pepy.tech/project/xstate-statemachine · ClickPy ClickHouse SQL (`pypi.pypi_downloads_per_day*` tables, data through 2026-10-18) · https://clickpy.clickhouse.com/dashboard/{python-statemachine,transitions}.
Dependents: https://deps.dev/pypi/python-statemachine · https://libraries.io/pypi/python-statemachine · https://www.wheelodex.org/projects/python-statemachine/rdepends/ · https://github.com/fgmacedo/python-statemachine/network/dependents · PyPI `requires_dist` scan.
Discoverability: https://github.com/vinta/awesome-python (README line 634; commits 2026-08-23, 2026-10-02; CONTRIBUTING.md) · Stack Exchange and HN Algolia APIs · DuckDuckGo "python state machine" · https://github.com/statelyai/xstate-python.
Ours: `gh api repos/basiltt/xstate-statemachine` (2026-10-19) · `README.md` · `pyproject.toml` · `docs/_guide/pythonic-api.md` · `docs/_guide/getting-started.md` · `docs/_guide/quick-start.md` · `docs/_guide/comparisons/vs-python-statemachine.md` · `docs/_data/comparisons.json` · `src/xstate_statemachine/pythonic.py` · `benchmarks/competitors/` · probe scripts under `%TEMP%\psm_probe\` and `%TEMP%\xsm_audit\`.

Caveats: Google/Bing SERPs could not be scripted (DuckDuckGo only, one query); Reddit/YouTube/blog sentiment was not measured; python-statemachine third-party sentiment is thin (a handful of HN comments and GitHub issues); the throughput comparison is our own benchmark; download-bucket percentages in §2.4 are inference from the cited data, not measurement.
