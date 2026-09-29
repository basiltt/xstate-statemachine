---
title: "pytest integration"
description: "A pytest plugin that turns a JSON chart into fixtures: a started interpreter on a simulated clock, stub logic that records what ran, and snapshot assertions — for both engines."
---

# pytest

Testing a statechart is always the same setup: build the machine with stub logic, start a `SyncInterpreter` on a `SimulatedClock`, send events, advance the clock, assert on the configuration. Our own `xsm gt -t pytest` template emits exactly that boilerplate. The `[testing]` extra makes it declarative instead: put one marker on the test, name the fixtures you need, and the plugin builds the machine, starts it, and stops it at teardown — for the sync **and** the async engine. It also gives you a snapshot assertion that records to a file, fails with a unified diff, and never writes unless you ask it to.

## Install

```bash
pip install "xstate-statemachine[testing]"
```

Requires `pytest>=8`. The extra also installs `hypothesis>=6.100` for the model-based tester that lands with [#271](https://github.com/basiltt/xstate-statemachine/issues/271); this page needs only pytest. The plugin is registered through a `pytest11` entry point, so pytest finds it on its own — no `conftest.py`, no `pytest_plugins` line. `xsm_ainterp` additionally needs [`pytest-asyncio`](https://pypi.org/project/pytest-asyncio/). Tested versions are in the [compatibility table](#compatibility).

## Quick start

A test file needs the marker and the fixture names — nothing else. The block below writes such a file and runs it through pytest, so it is executed in CI exactly as a user would run it:

<!-- doc-requires: pytest -->
```python
import json, pathlib, sys, tempfile
import pytest
from xstate_statemachine import __version__ as _  # the package must be installed

TEST = '''
import pytest

CHECKOUT = {
    "id": "checkout", "initial": "cart", "context": {"items": 0},
    "states": {
        "cart":      {"on": {"PAY": {"target": "paying", "guard": "hasItems", "actions": "charge"}}},
        "paying":    {"after": {"3000": "confirmed"}},
        "confirmed": {"type": "final"},
    },
}

@pytest.mark.xstate_machine(CHECKOUT)                    # a dict, a JSON path, or a MachineNode
def test_pay_then_confirm(xsm_interp, xsm_clock, xsm_ran, xsm_send_all):
    xsm_send_all(xsm_interp, "PAY", "+3000")             # the `xsm simulate --events` grammar
    assert xsm_interp.matches("checkout.confirmed")
    assert xsm_ran == ["charge"]                         # stub actions record their names

@pytest.mark.xstate_machine(CHECKOUT)
@pytest.mark.xstate_guards_false("hasItems")             # stub guard forced False...
def test_guard_blocks_payment(xsm_interp, xsm_guards):
    assert xsm_interp.send("PAY", wait=True).denied
    xsm_guards["hasItems"] = True                        # ...and flipped live
    xsm_interp.send("PAY")
    assert xsm_interp.matches("checkout.paying")

@pytest.mark.xstate_machine(CHECKOUT)
def test_snapshot(xsm_interp, xsm_snapshot):
    xsm_interp.send("PAY")
    xsm_snapshot(xsm_interp, "snapshots/paying.json")    # --xsm-update-snapshots records it
'''

with tempfile.TemporaryDirectory() as tmp:
    pathlib.Path(tmp, "test_checkout.py").write_text(TEST, encoding="utf-8")
    plugin = "xstate_statemachine.contrib.testing.pytest_plugin"
    common = ["-q", "-p", "no:cacheprovider", f"--rootdir={tmp}", tmp]
    # first run records the snapshot; the second must pass against it unchanged
    assert pytest.main([*common, "--xsm-update-snapshots"]) == 0, "recording run"
    assert pytest.main(common) == 0, "verification run"
    print(pathlib.Path(tmp, "snapshots", "paying.json").read_text(encoding="utf-8"))
```

The recorded snapshot holds only what describes behaviour — `state_ids`, `value`, `context`, `status` — with sorted keys and a trailing newline, so it is byte-identical across runs and machines:

```json
{
  "context": {
    "items": 0
  },
  "state_ids": [
    "checkout.paying"
  ],
  "status": "running",
  "value": "paying"
}
```

## Reference

### Markers

| Marker | What it does |
|:--|:--|
| `@pytest.mark.xstate_machine(source, *, logic=None, strict_config=None, strict=None)` | Declares the machine the `xsm_*` fixtures serve. `source` is a **JSON path** (relative to the test file, then to pytest's rootdir), a **config dict**, or an already-built **`MachineNode`**. `logic` is a dotted `"package.module:callable"` whose call returns a `MachineLogic`; without it the machine runs on [`stub_logic`](../testing-and-pure-api/) — actions record their name, guards return `True`, services return `None` synchronously. `strict_config` and `strict` are passed to `create_machine` and must be `True`, `False` or `None`. A `MachineNode` source is used as-is: `logic=`, `strict_config=` and `strict=` are refused for it (the node is never mutated). A malformed marker, an unreadable file, an unloadable or raising `logic=` factory, or a config `create_machine` refuses is a `pytest.UsageError` naming the test. |
| `@pytest.mark.xstate_guards_false("g1", "g2")` | With stub logic, the named guards return `False`; unlisted guards stay `True`. The table is held **by reference** — mutate `xsm_guards` between sends to flip a guard. Combining it with `logic=` (or a `MachineNode` source) is a `pytest.UsageError`: real logic owns its guards and the plugin will not pretend otherwise. |

Both markers are registered, so `--strict-markers` projects need nothing extra.

### Fixtures

All fixtures are prefixed `xsm_` so they cannot shadow your own `machine`, `clock` or `store`. Requesting one on a test without the marker fails at setup with a message naming the marker.

| Fixture | Gives you |
|:--|:--|
| `xsm_machine` | The `MachineNode` built from the marker. |
| `xsm_clock` | A fresh `SimulatedClock`. `xsm_clock.increment(ms)` fires the `after` timers that became due. Under the async engine `increment` returns an awaitable — `await` it. |
| `xsm_interp` | A **started** `SyncInterpreter(xsm_machine, clock=xsm_clock)`; stopped at teardown. |
| `xsm_ainterp` | The async twin: a started `Interpreter` on `xsm_clock`, stopped at teardown. Needs `pytest-asyncio` and an `@pytest.mark.asyncio` test (or `asyncio_mode = auto`); **skipped with a message naming the package** when pytest-asyncio is not installed or is disabled (`-p no:asyncio`). |
| `xsm_ran` | The list every stub action appends its name to, in execution order. Empty and never written to when the marker passes `logic=` or a `MachineNode` — real actions do not report here. |
| `xsm_guards` | The live stub-guard table (`name -> bool`) behind `xstate_guards_false`. Empty and inert with `logic=` or a `MachineNode` source (a built node has its own logic). |
| `xsm_store` | A fresh `persistence.MemoryStore()`, for `persisted(xsm_store, key, xsm_machine)` round-trips. |
| `xsm_send_all` | `xsm_send_all(interp, "A", "+500", "B")` — sends `A`, advances `xsm_clock` by 500 ms, sends `B`. Same grammar as `xsm simulate --events`; a bare number is a clock advance too. Sync interpreters only. |
| `xsm_asend_all` | `await xsm_asend_all(ainterp, "A", "+500", "B")` — the async form; each send is awaited with `wait=True` and each advance is awaited. |
| `xsm_snapshot` | `xsm_snapshot(interp, "snapshots/paid.json")` — asserts the interpreter's normalised snapshot equals the file. With `--xsm-update-snapshots` it (re)writes the file instead. A missing or different file raises `SnapshotMismatchError` (an `AssertionError`) whose message is a unified diff of recorded → actual. Relative paths resolve next to the test file. |

### Options

| Option | Effect |
|:--|:--|
| `--xsm-version` | Print `xstate-statemachine <version>` and exit 0. |
| `--xsm-update-snapshots` | Every `xsm_snapshot` call writes its file instead of comparing. |
| `-p no:xstate_statemachine` | Disable the plugin for a session (pytest's own opt-out). |

### Helpers (importable from `xstate_statemachine.contrib.testing`)

| Name | What it does |
|:--|:--|
| `normalize_snapshot(blob)` | The deterministic subset of a `get_snapshot()` blob: `state_ids`, `value`, `context`, `status`. |
| `render_snapshot(normalized)` | The exact file form — `json.dumps(sort_keys=True, indent=2)` plus a newline. |
| `parse_marker(item)` | What the plugin reads from a collected test's markers (`MachineSpec` or `None`); useful when writing your own fixtures on top. |
| `SnapshotMismatchError` | Raised by `xsm_snapshot`; carries `.path` and `.diff`. |
| `PLUGIN_NAME` | `"xstate_statemachine"` — the name to pass to `-p no:`. |

### Generated tests on the fixtures

`xsm gt -t pytest --fixtures machine.json` emits the recorded-trajectory test module on the plugin's marker and fixtures instead of building the interpreter by hand: the same `STEPS`, the same assertions, no stub builder or fixture boilerplate in the file. Without `--fixtures` the output is unchanged.

## Path generation

Request the `xsm_path` fixture under an `xstate_machine` marker and pytest parametrises the test over [`graph.shortest_paths(machine)`](../testing-and-pure-api/) — **one case per reachable configuration**, found by running the real engine on stub logic and a simulated clock (parallel regions, history and `after` timers included):

```python
import pytest

@pytest.mark.xstate_machine("machines/AdvancePayment.json")
def test_every_state_is_reachable(xsm_path, xsm_interp, xsm_clock):
    xsm_path.replay(xsm_interp, xsm_clock)          # events + clock advances
    assert xsm_interp.current_state_ids == set(xsm_path.final_states)
```

```text
test_reach[path[editing]] PASSED
test_reach[path[editing->challenge]] PASSED
test_reach[path[editing->challenge->success]] PASSED
```

Ids name the leaf configurations the path walks through (parallel leaves joined with `+`). `xsm_path` is a `graph.Path`: `steps`, `final_states`, `event_string()` (the `xsm simulate --events` grammar) and `replay(interp, clock)`, which forces each step's recorded guard/service assumptions for that step only.

| Option | Effect |
|:--|:--|
| `--xsm-full-paths` | Parametrise over `simple_paths` (every acyclic path) instead of one shortest path per configuration. |
| `--xsm-max-paths=N` | Cap for `--xsm-full-paths` (default 1000). |
| `--xsm-max-depth=N` | Longest path explored (default 50). |
| `--xsm-path-guards=true\|false\|both` | What stub guards return during generation; `both` also reaches the configurations only a `False` guard (or a failing service) leads to. |

📝 Named `after` delays (declared in `MachineLogic.delays`) have no static duration: their steps advance the clock by a large sentinel and carry a `delay:<name>=unknown` assumption. With real `logic=` the *generation* still uses stubs; `replay` then runs your real guards, so a path whose guard assumption your logic does not satisfy will (correctly) not reach its configuration.

## State & transition coverage

Line coverage cannot tell you whether any test ever reached `timeout` or took `paying --PAY_FAILED--> failed`. The chart knows every state and transition; `--xsm-coverage` records which ones ran:

```text
$ pytest --xsm-coverage --xsm-fail-under-transition-coverage=90
...
---- xstate coverage ----
checkout          states 12/15 (80%)  transitions 18/22 (81.8%)
  unvisited: timeout, errorRecovery, refund.partial
  unhit:     paying --PAY_FAILED--> failed, after 30000 ...
FAIL xstate coverage: checkout: transition coverage 81.8% < 90%
```

The session registers one `CoverageCollector` with core's [`plugins.register_global`](../plugins/) at start-up and unregisters it at the end, so **every** interpreter built during the run is counted — the `xsm_*` fixtures, a test's own `SyncInterpreter(...)` / `Interpreter(...)`, `from_snapshot` restores (their configuration counts at `start()`), spawned children, on any thread. Machines are grouped by `machine.id` + `structure_hash`, so two builds of one chart merge and an edited chart is a new row. A parallel configuration marks every active leaf and its ancestors; a history restore marks the states actually re-entered. Denominators: every state except the root and history pseudo-states, and [`transition_coverage_targets(machine)`](../testing-and-pure-api/) for transitions (`on`, `always`, `after`, `onDone`, invoke `onDone`/`onError`).

| Option | Effect |
|:--|:--|
| `--xsm-coverage` | Enable. Without it nothing is registered and no section is printed. |
| `--xsm-coverage-report=term\|json[:PATH]\|html[:PATH]` | Repeatable; default `term`. `json` defaults to `xsm-coverage.json`, `html` to `xsm-coverage.html` (one self-contained file: inline CSS, no scripts, no external links). |
| `--xsm-fail-under-state-coverage=N` | Session exits 1 if any machine's state coverage is below N %. |
| `--xsm-fail-under-transition-coverage=N` | Same for transitions. |

The same collector works outside pytest:

```python
from xstate_statemachine import SyncInterpreter, create_machine
from xstate_statemachine.coverage import CoverageCollector

m = create_machine({"id": "t", "initial": "a", "states": {
    "a": {"on": {"GO": "b"}}, "b": {"on": {"BACK": "a"}}}})
cov = CoverageCollector()
SyncInterpreter(m).use(cov).start().send("GO")
report = cov.report(m)
assert (report.states_visited, report.transitions_hit) == (2, 1)
print(report.to_text())      # also .to_json(), .to_html()
```

**JSON schema (`version: 1`, stable).** A reader must reject any other `version`.

```text
{"version": 1,
 "machines": [{"machine": "checkout", "key": "checkout@<structure_hash>",
               "states":      {"visited": 12, "total": 15, "percent": 80.0,
                               "unvisited": ["checkout.timeout", ...]},
               "transitions": {"hit": 18, "total": 22, "percent": 81.82,
                               "unhit": [{"from": "checkout.paying",
                                          "label": "on 'PAY_FAILED'",
                                          "to": "checkout.failed"}, ...]}}]}
```

`xsm coverage xsm-coverage.json [--fail-under N] [--plain] [--json]` renders it in CI logs and exits 1 when any machine is under `N` % (state or transition). A CI job:

```yaml
- run: pytest --xsm-coverage --xsm-coverage-report=term --xsm-coverage-report=json:xsm-coverage.json
- run: xsm coverage xsm-coverage.json --fail-under 90 --plain
- uses: actions/upload-artifact@v4
  with: {name: xstate-coverage, path: xsm-coverage.json}
```

## Guarantees

> **What this does:** builds the machine once per test from the marker, starts the interpreter on a simulated clock so no test waits on wall time, stops it at teardown, and fails loudly — with the test id — on any marker or logic mistake. Snapshot files are deterministic (sorted keys, fixed indent, behavioural fields only) and are written **only** under `--xsm-update-snapshots`. Without the marker the plugin does nothing: it registers fixtures and two options and requires no configuration. Both engines share the same semantics.
>
> **What this does not do:** run your services, actions or guards unless you pass `logic=` — stubs complete synchronously and record, they do not do work; provide an event loop (`xsm_ainterp` needs `pytest-asyncio`); assert on timing (use `xsm_clock`); persist anything outside the snapshot files you name.
>
> See the programme-wide [Guarantees](../guarantees/) and [Security](../security/) pages ([#303](https://github.com/basiltt/xstate-statemachine/issues/303)).

## Threat model

> **Who can call this:** whoever runs your test suite. The plugin is active in every pytest session of a project that installed the library; it reads nothing and writes nothing until a test carries the marker.
>
> **What it exposes:** `logic=` imports and **calls** a dotted callable from your test — trusted code, the same trust as a `conftest.py` or `LogicLoader`; do not point it at untrusted modules. `--xsm-update-snapshots` writes files at the paths your tests name, resolved under the test tree. A snapshot file contains the machine's `context` **in clear text** — do not put secrets in a context you snapshot, or redact before asserting.
>
> **You must configure:** nothing for the sync engine. For the async engine, install `pytest-asyncio` and mark tests `@pytest.mark.asyncio`. Keep snapshot files under version control and review their diffs like code — a changed snapshot is a changed behaviour.

## Compatibility

| pytest | Python | Tested in CI |
|:--|:--|:--|
| 8.x – 9.x | 3.9 – 3.14 | ✅ `[testing]` cell (Linux); the repository's own suite runs with the plugin loaded on every matrix cell |

## Troubleshooting

| Symptom | Cause | Fix |
|:--|:--|:--|
| `MissingExtraError: … pip install "xstate-statemachine[testing]"` | importing `xstate_statemachine.contrib.testing` without pytest installed | run the command (pytest itself is the dependency) |
| `fixture 'xsm_interp' not found` | plugin not loaded — disabled with `-p no:xstate_statemachine`, or the package is not installed in the interpreter running pytest | drop the opt-out; `pip install "xstate-statemachine[testing]"` in that environment |
| `the xsm_interp fixture needs an @pytest.mark.xstate_machine(...) marker` | a fixture was requested on an unmarked test | add the marker |
| `UsageError: … machine file 'machines/x.json' not found (tried …)` | the path is relative to the test file, then rootdir | fix the path or pass an absolute one |
| `UsageError: … xstate_guards_false only applies to stub logic` | `logic=` and `xstate_guards_false` on the same test | make the real guard return `False`, or drop `logic=` |
| `SKIPPED … xsm_ainterp needs pytest-asyncio` | async fixture without a runner | `pip install pytest-asyncio`, mark the test `@pytest.mark.asyncio` |
| `SnapshotMismatchError: no snapshot file at …` | first run of a new snapshot | run once with `--xsm-update-snapshots`, commit the file |
| `RuntimeWarning: SimulatedClock.increment() … never awaited` | `xsm_clock.increment()` called without `await` under the async engine | `await xsm_clock.increment(ms)` or use `xsm_asend_all` |
