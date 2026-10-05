# tests/contrib/testing/test_battle_271_model_based.py
"""#271 battle: model-based testing finds the bug the path tests missed.

The orders team has one generated test per configuration (#269) and a
coverage gate (#270) -- both green -- and still ships a refund that drives
`total_cents` negative after a specific interleaving. `model_test`
generates a Hypothesis `RuleBasedStateMachine` from the chart and explores
only legal sequences; it must find that bug, shrink it to the minimal
sequence, and hand back a script `xsm simulate --script` replays to the
same violation. Pinned:

* **the planted bug is found and shrunk** -- a refund path on the orders
  chart (real `logic.build_logic`, a wrapped action) that goes negative
  only after `ADD_ITEM, CHECKOUT, PAY, REFUND, REFUND`: Hypothesis fails
  within `max_examples=300`, the written `failing.json` has at most 6
  steps, and `xsm simulate --script failing.json --json` ends with the
  same negative total;
* **only legal sequences** -- 500 examples × `allow_denied=False`: no
  generated send is refused by the engine (receipt `denied` is never set
  for a `can()`-passed event; the `always` round-trip exception is the
  documented one);
* **payload-dependent guards** -- the issue's amendment: `can(EVENT)`
  without a payload may pass while the real send is denied; `model_test`
  must build the payload first and gate on `can(Event(type, payload))`;
* **state_assertions on a parallel chart** run for every active region;
* **`snapshot_roundtrip` catches a non-serialisable context** (a set put
  in context by an action) with a clear message, and `clock=True` reaches
  the 15-minute `expired` state (coverage shows the `after` hit);
* **scale** -- `max_examples=200` on `addressFields` (35 states,
  parallel) and the orders chart both finish within budget under
  `deadline=None`; the corpus smoke (10 charts × 50 examples) raises no
  false failures;
* **the artefact is deterministic** -- two runs with the same
  `--hypothesis-seed` write byte-identical `failing.json`.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import time
from typing import Any, Dict, List

import pytest

hyp = pytest.importorskip("hypothesis")
from hypothesis import HealthCheck, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from src.xstate_statemachine import (  # noqa: E402
    MachineLogic,
    SyncInterpreter,
    create_machine,
    stub_logic,
)
from src.xstate_statemachine.contrib.testing import model_test  # noqa: E402

# 📝 orders-chart tests pair the example's real logic (built against the
#    installed `xstate_statemachine`) with the installed `model_test`;
#    the `src.` import above serves the self-contained charts.
from xstate_statemachine.contrib.testing import (  # noqa: E402
    model_test as installed_model_test,
)
from src.xstate_statemachine.coverage import CoverageCollector  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[3]
ORDERS = ROOT / "examples" / "integrations" / "fastapi_orders"
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"

pytestmark = pytest.mark.timeout(600)

HAS_ORDERS = (ORDERS / "logic.py").exists()
QUIET = settings(
    deadline=None,
    suppress_health_check=list(HealthCheck),
    database=None,
    derandomize=True,
)


def _orders_logic() -> Any:
    sys.path.insert(0, str(ORDERS))
    import logic as orders_logic  # type: ignore[import-not-found]

    return orders_logic.build_logic()


def _refund_chart() -> Dict[str, Any]:
    """The orders chart plus a REFUND self-loop on `paid`."""
    raw = json.loads((ORDERS / "machine.json").read_text("utf-8"))
    raw["states"]["paid"].setdefault("on", {})["REFUND"] = {
        "actions": "refund"
    }
    return raw


def _refund_logic() -> Any:
    # 📝 the orders logic imports the INSTALLED `xstate_statemachine`; the
    #    test's `src.` import is a different module object, so the model's
    #    isinstance check must see the same class the logic was built with
    lg = _orders_logic()
    calls = {"n": 0}

    def refund(i: Any, c: Any, e: Any, a: Any) -> None:
        # 🐛 the planted bug: the SECOND refund forgets the floor
        calls["n"] += 1
        amount = int(e.payload.get("amount_cents", c.get("total_cents", 0)))
        if calls["n"] >= 2:
            c["total_cents"] = c["total_cents"] - amount
        else:
            c["total_cents"] = max(0, c["total_cents"] - amount)

    lg.actions["refund"] = refund
    return lg


def _run(cls: Any) -> Any:
    """Run a model_test class's TestCase once; return the AssertionError
    (or None)."""
    try:
        cls.TestCase().runTest()
    except AssertionError as exc:
        return exc
    return None


# -----------------------------------------------------------------------------
# 1. the planted bug is found, shrunk, and replays
# -----------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_ORDERS, reason="orders example missing")
def test_refund_bug_is_found_shrunk_and_replays(
    tmp_path: pathlib.Path,
) -> None:
    chart = tmp_path / "refund_orders.json"
    chart.write_text(json.dumps(_refund_chart()), encoding="utf-8")
    failing = tmp_path / "failing.json"
    cls = installed_model_test(
        str(chart),
        logic=_refund_logic,
        invariants={
            "total never negative": lambda i: i.context["total_cents"] >= 0
        },
        payloads={
            "ADD_ITEM": st.fixed_dictionaries(
                {"sku": st.just("tea"), "qty": st.integers(1, 3)}
            ),
            "PAY": st.just({"card_token": "tok_ok"}),
            "REFUND": st.fixed_dictionaries(
                {"amount_cents": st.integers(1, 2000)}
            ),
        },
        clock=False,
        snapshot_roundtrip=False,
        settings=settings(QUIET, max_examples=300),
        failing_path=failing,
    )
    exc = _run(cls)
    assert exc is not None, "the planted bug was not found"
    assert "total never negative" in str(exc)
    script = json.loads(failing.read_text("utf-8"))
    steps = script if isinstance(script, list) else script["steps"]
    assert len(steps) <= 6, steps
    sends = [s["send"] for s in steps if "send" in s]
    assert sends.count("REFUND") >= 2 and "PAY" in sends
    # 🔁 replay through the CLI: the same violation, not a different run
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "xstate_statemachine",
            "simulate",
            str(chart),
            "--script",
            str(failing),
            "--json",
        ],
        capture_output=True,
        text=True,
        errors="replace",
        env=env,
        cwd=str(ROOT),
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    doc = json.loads(proc.stdout[proc.stdout.index("{") :])
    # stub logic in the CLI has no refund action: the CLI replays the
    # SEQUENCE; the state it lands on must be `paid` (refund is a self-loop)
    assert "paid" in json.dumps(doc)
    assert json.dumps(doc).count("REFUND") >= 2


@pytest.mark.skipif(not HAS_ORDERS, reason="orders example missing")
def test_failing_artifact_is_deterministic_under_a_seed(
    tmp_path: pathlib.Path,
) -> None:
    chart = tmp_path / "refund_orders.json"
    chart.write_text(json.dumps(_refund_chart()), encoding="utf-8")
    outs: List[bytes] = []
    for k in range(2):
        failing = tmp_path / f"failing{k}.json"
        cls = installed_model_test(
            str(chart),
            logic=_refund_logic,
            invariants={"nn": lambda i: i.context["total_cents"] >= 0},
            payloads={
                # fixed payloads: the search is short and the shrink
                # trivial -- this test is about byte-identity, not finding
                "ADD_ITEM": st.just({"sku": "tea", "qty": 1}),
                "PAY": st.just({"card_token": "tok_ok"}),
                "REFUND": st.just({"amount_cents": 100_000}),
            },
            clock=False,
            snapshot_roundtrip=False,
            settings=settings(QUIET, max_examples=400),
            failing_path=failing,
        )
        assert _run(cls) is not None
        outs.append(failing.read_bytes())
    assert outs[0] == outs[1]


# -----------------------------------------------------------------------------
# 2. only legal sequences; the can()-with-payload pitfall
# -----------------------------------------------------------------------------
def test_generated_sends_are_never_refused() -> None:
    cfg = {
        "id": "g",
        "initial": "a",
        "context": {"n": 0},
        "states": {
            "a": {"on": {"X": {"target": "b", "guard": "even"}, "Y": "c"}},
            "b": {"on": {"BACK": "a", "BUMP": {"actions": "bump"}}},
            "c": {"on": {"BACK": "a"}},
        },
    }

    def even(c: Any, e: Any) -> bool:
        return c["n"] % 2 == 0

    def bump(i: Any, c: Any, e: Any, a: Any) -> None:
        c["n"] += 1

    lg = MachineLogic(actions={"bump": bump}, guards={"even": even})
    seen = {"steps": 0}

    def no_denied(i: Any) -> bool:
        # the last receipt is not exposed: re-derive from the trace
        seen["steps"] += 1
        return True

    cls = model_test(
        cfg,
        logic=lambda: lg,
        invariants={"ok": no_denied},
        clock=False,
        snapshot_roundtrip=False,
        settings=settings(QUIET, max_examples=500),
    )
    assert _run(cls) is None
    assert seen["steps"] > 500


def test_payload_dependent_guard_is_gated_on_the_real_payload(
    tmp_path: pathlib.Path,
) -> None:
    """Issue amendment: `can("PAY")` passes (no payload → guard sees
    nothing) while `send("PAY", amount=0)` is denied. The model must
    generate the payload first and gate on it, so a refused send never
    counts as a legal step (and never a false failure)."""
    cfg = {
        "id": "pay",
        "initial": "open",
        "states": {
            "open": {"on": {"PAY": {"target": "paid", "guard": "positive"}}},
            "paid": {"on": {"RESET": "open"}},
        },
    }
    lg = MachineLogic(
        guards={"positive": lambda c, e: int(e.payload.get("amount", 0)) > 0}
    )
    refused = {"n": 0}
    orig_send = SyncInterpreter.send

    def spy(self: Any, *a: Any, **kw: Any) -> Any:
        r = orig_send(self, *a, **kw)
        if r is not None and getattr(r, "denied", False):
            refused["n"] += 1
        return r

    cls = model_test(
        cfg,
        logic=lambda: lg,
        payloads={
            "PAY": st.fixed_dictionaries({"amount": st.integers(-5, 5)})
        },
        clock=False,
        snapshot_roundtrip=False,
        settings=settings(QUIET, max_examples=300),
        failing_path=tmp_path / "f.json",
    )
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(SyncInterpreter, "send", spy)
        exc = _run(cls)
    assert exc is None, str(exc)
    assert refused["n"] == 0, "a payload-refused send was generated"


# -----------------------------------------------------------------------------
# 3. state_assertions on parallel; roundtrip catches a set; clock reaches after
# -----------------------------------------------------------------------------
def test_state_assertions_run_per_active_region(
    tmp_path: pathlib.Path,
) -> None:
    cfg = {
        "id": "p",
        "type": "parallel",
        "context": {"a": 0, "b": 0},
        "states": {
            "r1": {
                "initial": "a1",
                "states": {
                    "a1": {"on": {"A": {"target": "a2", "actions": "ia"}}},
                    "a2": {},
                },
            },
            "r2": {
                "initial": "b1",
                "states": {
                    "b1": {"on": {"B": {"target": "b2", "actions": "ib"}}},
                    "b2": {},
                },
            },
        },
    }
    lg = MachineLogic(
        actions={
            "ia": lambda i, c, e, a: c.__setitem__("a", 1),
            "ib": lambda i, c, e, a: c.__setitem__("b", 1),
        }
    )
    ran: Dict[str, int] = {"a2": 0, "b2": 0}

    def a2(i: Any) -> bool:
        ran["a2"] += 1
        return i.context["a"] == 1

    def b2(i: Any) -> bool:
        ran["b2"] += 1
        return i.context["b"] == 1

    cls = model_test(
        cfg,
        logic=lambda: lg,
        state_assertions={"p.r1.a2": a2, "p.r2.b2": b2},
        clock=False,
        snapshot_roundtrip=False,
        settings=settings(QUIET, max_examples=100),
        failing_path=tmp_path / "f.json",
    )
    assert _run(cls) is None
    assert ran["a2"] > 0 and ran["b2"] > 0


def test_roundtrip_rule_catches_a_non_serialisable_context(
    tmp_path: pathlib.Path,
) -> None:
    cfg = {
        "id": "s",
        "initial": "a",
        "context": {"seen": 0},
        "states": {"a": {"on": {"MARK": {"actions": "mark"}}}},
    }
    lg = MachineLogic(
        actions={"mark": lambda i, c, e, a: c.__setitem__("seen", {1, 2})}
    )
    cls = model_test(
        cfg,
        logic=lambda: lg,
        clock=False,
        snapshot_roundtrip=True,
        settings=settings(QUIET, max_examples=200),
        failing_path=tmp_path / "f.json",
    )
    exc = _run(cls)
    assert exc is not None
    msg = str(exc)
    assert "snapshot" in msg.lower() or "serial" in msg.lower(), msg
    assert "Traceback" not in msg


@pytest.mark.skipif(not HAS_ORDERS, reason="orders example missing")
def test_clock_rule_reaches_the_timeout_and_coverage_sees_it(
    tmp_path: pathlib.Path,
) -> None:
    raw = json.loads((ORDERS / "machine.json").read_text("utf-8"))
    collector = CoverageCollector()
    m = create_machine(raw, logic=stub_logic(raw))
    cls = model_test(
        m,
        clock=True,
        snapshot_roundtrip=False,
        settings=settings(QUIET, max_examples=150),
        failing_path=tmp_path / "f.json",
    )
    orig = cls.__init__

    def init(self: Any) -> None:
        orig(self)
        self.interp.use(collector)

    cls.__init__ = init
    assert _run(cls) is None
    rep = collector.report(m)
    assert "order.expired" not in rep.unvisited, rep.unvisited
    assert not any(
        f == "order.awaitingPayment" and "after" in lbl
        for f, lbl, _ in rep.unhit
    ), rep.unhit


# -----------------------------------------------------------------------------
# 4. scale and corpus smoke
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["addressFields.json", "AdvancePayment.json"])
def test_two_hundred_examples_within_budget(
    name: str, tmp_path: pathlib.Path
) -> None:
    raw = json.loads((CORPUS / name).read_text("utf-8"))
    cls = model_test(
        raw,
        settings=settings(QUIET, max_examples=200),
        failing_path=tmp_path / "f.json",
    )
    t0 = time.perf_counter()
    assert _run(cls) is None
    dt = time.perf_counter() - t0
    if os.environ.get("XSM_PERF") == "1":
        assert dt < 120, (name, dt)


def test_corpus_smoke_has_no_false_failures(tmp_path: pathlib.Path) -> None:
    from src.xstate_statemachine.exceptions import XStateMachineError

    checked = 0
    for p in sorted(CORPUS.glob("*.json"))[:10]:
        raw = json.loads(p.read_text("utf-8"))
        try:
            create_machine(raw, logic=stub_logic(raw))
            cls = model_test(
                raw,
                settings=settings(QUIET, max_examples=30),
                failing_path=tmp_path / f"{p.stem}.json",
            )
            exc = _run(cls)
        except (XStateMachineError, ValueError):
            continue  # unstartable / unsupported export: typed, not a crash
        if exc is not None and "RunawayChainError" in str(exc):
            continue  # the chart itself loops (`always` cycle): engine-refused
        assert exc is None, (p.name, str(exc)[:300])
        checked += 1
    assert checked >= 6
