"""Battle #268 (adversary B): fake broker + `--xsm-coverage` gate.

Defects pinned here:

* under pytest-xdist (`-n 2`) the controller saw "(no machines observed)"
  and the `--xsm-fail-under-*` gate PASSED a suite far below threshold --
  workers' collectors were never shipped back. Fixed in `_coverage.py`
  (worker -> `workeroutput` -> controller merge).
* `FakeBrokerAdapter.deliver()` accepted a non-`Envelope` and the failure
  surfaced later inside the consumer; it is now a `TypeError` at the call,
  like `publish()`.
* `SyncFakeBrokerAdapter` / `BrokerPublishError` were documented but not
  exported from `contrib.testing`.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import textwrap
import threading
from typing import Any

import pytest

from xstate_statemachine.contrib import testing as xt
from xstate_statemachine.contrib.testing._coverage import merge_reports
from xstate_statemachine.coverage import CoverageReport
from xstate_statemachine.eda import Envelope

from .conftest import PLUGIN_ARGS, run

HAS_XDIST = importlib.util.find_spec("xdist") is not None

CFG = {
    "id": "cov",
    "initial": "a",
    "states": {
        "a": {"on": {"GO": "b"}},
        "b": {"on": {"GO": "c"}},
        "c": {},
    },
}

MODULE = "import pytest\n" + textwrap.dedent(f"""
    CFG = {CFG!r}

    @pytest.mark.xstate_machine(CFG)
    def test_one(xsm_interp):
        assert xsm_interp.matches("a")

    @pytest.mark.xstate_machine(CFG)
    def test_two(xsm_interp):
        xsm_interp.send("GO")
        assert xsm_interp.matches("b")
    """)


def _env(subject: str = "s", n: int = 0) -> Envelope:
    return Envelope.new(type="xsm.m.E", subject=subject, data={"n": n})


# =============================================================================
# Coverage gate
# =============================================================================
def _report(unvisited: Any, unhit: Any) -> CoverageReport:
    return CoverageReport(
        machine_id="m",
        key="m@1",
        states_visited=3 - len(unvisited),
        states_total=3,
        unvisited=tuple(unvisited),
        transitions_hit=2 - len(unhit),
        transitions_total=2,
        unhit=tuple(unhit),
    )


class TestMergeReports:
    def test_union_of_coverage(self) -> None:
        e1, e2 = ("m.a", "on 'GO'", "m.b"), ("m.b", "on 'GO'", "m.c")
        a = _report(["m.b", "m.c"], [e1, e2])
        b = _report(["m.c"], [e2])
        (merged,) = merge_reports([a, b])
        assert merged.unvisited == ("m.c",)
        assert merged.states_visited == 2
        assert merged.unhit == (e2,)
        assert merged.transitions_hit == 1

    def test_distinct_keys_kept_sorted(self) -> None:
        a = _report([], [])
        b = CoverageReport("z", "a@0", 0, 0, (), 0, 0, ())
        assert [r.key for r in merge_reports([a, b])] == ["a@0", "m@1"]

    def test_empty(self) -> None:
        assert merge_reports([]) == []


class TestCoverageSerial:
    def test_gate_fails_and_names_unvisited(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(test_cov=MODULE)
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-state-coverage=90",
        )
        r.assert_outcomes(passed=2)
        assert r.ret == 1
        r.stdout.fnmatch_lines(
            [
                "cov*states 2/3 (66.7%)*",
                "  unvisited: c",
                "FAIL xstate coverage: cov: state coverage 66.7% < 90%",
            ]
        )

    def test_zero_transition_chart(self, xsm_pytester) -> None:
        cfg = {"id": "solo", "initial": "x", "states": {"x": {}}}
        xsm_pytester.makepyfile(
            test_solo="import pytest\n"
            f"@pytest.mark.xstate_machine({cfg!r})\n"
            "def test_s(xsm_interp):\n    pass\n"
        )
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-transition-coverage=100",
            "--xsm-fail-under-state-coverage=100",
        )
        r.assert_outcomes(passed=1)
        assert r.ret == 0


@pytest.mark.skipif(not HAS_XDIST, reason="pytest-xdist not installed")
@pytest.mark.timeout(300)
class TestCoverageXdist:
    def _run(self, pytester: Any, *args: str) -> Any:
        return pytester.runpytest_subprocess(
            *PLUGIN_ARGS, "-q", "-n", "2", "-p", "no:django", *args
        )

    def test_gate_fails_under_xdist(self, xsm_pytester) -> None:
        # 🐛 before the fix: "(no machines observed)" and exit 0.
        xsm_pytester.makepyfile(test_cov=MODULE)
        r = self._run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-state-coverage=90",
        )
        r.assert_outcomes(passed=2)
        assert r.ret == 1
        out = r.stdout.str()
        assert "no machines observed" not in out
        assert "FAIL xstate coverage: cov: state coverage 66.7%" in out
        assert out.count("---- xstate coverage ----") == 1

    def test_xdist_json_matches_serial(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(test_cov=MODULE)
        run(
            xsm_pytester, "--xsm-coverage", "--xsm-coverage-report=json:s.json"
        )
        self._run(
            xsm_pytester, "--xsm-coverage", "--xsm-coverage-report=json:p.json"
        )
        serial = json.loads((xsm_pytester.path / "s.json").read_text())
        para = json.loads((xsm_pytester.path / "p.json").read_text())
        assert para == serial


# =============================================================================
# Fake broker
# =============================================================================
class TestExports:
    def test_sync_fake_and_error_exported(self) -> None:
        for name in ("SyncFakeBrokerAdapter", "BrokerPublishError"):
            assert name in xt.__all__
            assert getattr(xt, name) is not None


class TestBrokerAdversarial:
    def test_deliver_malformed_is_typed_error(self) -> None:
        sync = xt.SyncFakeBrokerAdapter()
        with pytest.raises(TypeError, match="deliver.. needs an Envelope"):
            sync.deliver("t", {"type": "x"})  # type: ignore[arg-type]
        fake = xt.FakeBrokerAdapter()
        with pytest.raises(TypeError, match="dict"):
            asyncio.run(fake.deliver("t", {"type": "x"}))  # type: ignore
        assert sync.pending("t") == 0 and fake.pending("t") == 0

    def test_ack_nack_redelivery_counts(self) -> None:
        b = xt.SyncFakeBrokerAdapter()
        b.deliver("t", _env(n=1))
        b.deliver("t", _env(n=2))
        d = next(b.subscribe("t", timeout=0))
        b.nack(d, requeue=True)
        b.nack(d, requeue=True)  # double settle: a no-op
        got = [x for x in b.subscribe("t", timeout=0)]
        assert [x.envelope.data["n"] for x in got] == [1, 2]
        for x in got:
            b.ack(x)
        assert (len(b.acked), len(b.nacked), b.in_flight) == (2, 1, 0)

    def test_fail_next_times(self) -> None:
        b = xt.SyncFakeBrokerAdapter()
        b.fail_next_publish(times=2)
        for _ in range(2):
            with pytest.raises(xt.BrokerPublishError):
                b.publish("o", _env())
        b.publish("o", _env())
        assert len(b.published_on("o")) == 1

    def test_ten_thousand_per_subject_order(self) -> None:
        b = xt.SyncFakeBrokerAdapter()
        for n in range(10_000):
            b.publish("t", _env(f"s{n % 7}", n))
        seen: dict = {}
        for d in b.subscribe("t", timeout=0):
            seen.setdefault(d.envelope.subject, []).append(d.envelope.data)
            b.ack(d)
        assert sum(len(v) for v in seen.values()) == 10_000
        for v in seen.values():
            ns = [x["n"] for x in v]
            assert ns == sorted(ns)
        assert b.in_flight == 0

    def test_threaded_producers_async_consumer(self) -> None:
        b = xt.FakeBrokerAdapter()
        per, threads = 500, 4

        def produce(k: int) -> None:
            for n in range(per):
                asyncio.run(b.publish("t", _env(f"p{k}", n)))

        async def consume() -> list:
            got: list = []
            async for d in b.subscribe("t", timeout=30):
                got.append(d)
                await b.ack(d)
                if len(got) == per * threads:
                    break
            return got

        ts = [
            threading.Thread(target=produce, args=(k,)) for k in range(threads)
        ]
        for t in ts:
            t.start()
        got = asyncio.run(consume())
        for t in ts:
            t.join()
        assert len(got) == per * threads
        for k in range(threads):
            ns = [
                d.envelope.data["n"]
                for d in got
                if d.envelope.subject == f"p{k}"
            ]
            assert ns == list(range(per))
