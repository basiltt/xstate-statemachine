# tests/contrib/testing/test_battle_268_team_adoption.py
"""#268 battle: a team adopts the `[testing]` plugin for a real chart.

The orders team (fastapi_orders) wants declarative tests: point at the
shipped `machine.json`, get fixtures, keep snapshot files in git, run
under `pytest -n 4`. Every leg below runs a throw-away `pytester` session
(the only honest way to test a plugin) and pins what a production team
would hit:

* **real logic via the dotted factory** -- `logic="logic:build_logic"`
  with the example's `sys.path`; a `CHECKOUT` → `PAY` flow reaches `paid`
  with the real gateway stub; the fixture tears the interpreter down even
  when the test fails;
* **snapshot files round-trip** -- `--xsm-update-snapshots` writes, a
  second run passes, an edited snapshot fails with a unified diff that
  names the changed key and never a traceback; the file is byte-identical
  across two update runs (deterministic), and a `Decimal` / `datetime`
  context survives;
* **`xsm_send_all` grammar** -- `"+900000"` fires the 15-minute timeout to
  `expired`; `"+nan"` / `"+-5"` / `"+abc"` are usage errors, not hangs;
* **`xstate_guards_false`** on stub logic forces the named guards; on a
  real-logic chart it is refused with a clear message;
* **`xsm_path` × real chart** -- one case per configuration, every case
  replays onto its final states;
* **parallel** -- `-n 4` (pytest-xdist) gives the same outcomes and the
  same snapshot files as a serial run; no file write races;
* **opt-out** -- `-p no:xstate_statemachine` leaves a marker-less module
  untouched and a marker-using module failing with "fixture not found";
* **the generated template** -- `xsm gt -t pytest --fixtures` on the
  orders chart emits a module that passes under the plugin.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import shutil
import subprocess
import sys
import textwrap
from typing import Any

import pytest

from .conftest import PLUGIN_ARGS, run

ROOT = pathlib.Path(__file__).resolve().parents[3]
ORDERS = ROOT / "examples" / "integrations" / "fastapi_orders"
CHART = ORDERS / "machine.json"

pytestmark = pytest.mark.timeout(300)

HAS_XDIST = importlib.util.find_spec("xdist") is not None
HAS_FASTAPI = importlib.util.find_spec("fastapi") is not None
HAS_PYDANTIC = importlib.util.find_spec("pydantic") is not None

PRELUDE = f"""
import json, sys, pytest
sys.path.insert(0, {str(ORDERS)!r})
CHART = {str(CHART)!r}
"""


def _module(body: str) -> str:
    return PRELUDE + textwrap.dedent(body)


def _needs_example() -> None:
    if not (HAS_FASTAPI and HAS_PYDANTIC):
        pytest.skip("the orders example needs [fastapi,pydantic]")


# -----------------------------------------------------------------------------
# 1. real logic through the dotted factory
# -----------------------------------------------------------------------------
class TestRealLogic:
    def test_checkout_pay_reaches_paid_with_real_logic(
        self, xsm_pytester: Any
    ) -> None:
        _needs_example()
        xsm_pytester.makepyfile(_module("""
            @pytest.mark.xstate_machine(CHART, logic="logic:build_logic")
            def test_flow(xsm_interp, xsm_send_all):
                xsm_interp.send("ADD_ITEM", sku="tea", qty=1)
                xsm_send_all(xsm_interp, "CHECKOUT")
                assert "order.awaitingPayment" in xsm_interp.current_state_ids
                xsm_interp.send("PAY", card_token="tok_ok")
                assert xsm_interp.matches("order.paid")
            """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_fixture_teardown_stops_interp_even_on_failure(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_module("""
            import threading
            CFG = {"id": "t", "initial": "a", "states": {"a": {"after": {"100": "b"}}, "b": {}}}
            seen = {}
            # 📝 relative, not absolute: an in-process pytester inherits the
            #    OUTER session's threads (35 under the coverage job).
            baseline = threading.active_count()

            @pytest.mark.xstate_machine(CFG)
            def test_fails(xsm_interp):
                seen["i"] = xsm_interp
                assert False, "deliberate"

            def test_after():
                assert seen["i"].status == "stopped"
                assert threading.active_count() <= baseline + 1
            """))
        run(xsm_pytester).assert_outcomes(passed=1, failed=1)

    def test_bad_dotted_logic_is_one_usage_error(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_module("""
            CFG = {"id": "t", "initial": "a", "states": {"a": {}}}

            @pytest.mark.xstate_machine(CFG, logic="nope.module:make")
            def test_it(xsm_interp):
                pass

            @pytest.mark.xstate_machine(CFG, logic="json:dumps")
            def test_not_a_logic(xsm_interp):
                pass
            """))
        result = run(xsm_pytester)
        out = result.stdout.str() + result.stderr.str()
        assert "Traceback" not in out
        assert "nope.module" in out and "dumps" in out


# -----------------------------------------------------------------------------
# 2. snapshot files: write, pass, diff, deterministic, rich types
# -----------------------------------------------------------------------------
SNAP_MODULE = """
from decimal import Decimal
from datetime import datetime, timezone
CFG = {
    "id": "acct", "initial": "open",
    "context": {"total": "0", "n": 0},
    "states": {"open": {"on": {"ADD": {"actions": "add"}, "CLOSE": "closed"}},
               "closed": {"type": "final"}},
}
from xstate_statemachine import MachineLogic
def make():
    def add(i, c, e, a):
        c["total"] = Decimal(c["total"]) + Decimal("1.25")
        c["n"] += 1
        c["when"] = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return MachineLogic(actions={"add": add})

@pytest.mark.xstate_machine(CFG, logic="test_snap:make")
def test_snapshot(xsm_interp, xsm_snapshot):
    xsm_interp.send("ADD")
    xsm_interp.send("ADD")
    xsm_snapshot(xsm_interp, "snapshots/after_two.json")
"""


class TestSnapshots:
    def test_write_pass_diff_cycle_is_deterministic(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(test_snap=_module(SNAP_MODULE))
        # 1. no file yet: a plain run fails and SAYS how to create it
        r = run(xsm_pytester)
        r.assert_outcomes(failed=1)
        assert "--xsm-update-snapshots" in r.stdout.str()
        # 2. write
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        snap = xsm_pytester.path / "snapshots" / "after_two.json"
        first = snap.read_bytes()
        data = json.loads(first)
        assert data["context"]["n"] == 2
        assert data["context"]["total"] == "2.50"  # Decimal exact, as str
        assert "2026-01-01" in json.dumps(data["context"]["when"])
        # 3. a second update is byte-identical (deterministic ordering)
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        assert snap.read_bytes() == first
        # 4. plain run passes
        run(xsm_pytester).assert_outcomes(passed=1)
        # 5. an edited snapshot fails with a unified diff, no traceback
        data["context"]["n"] = 3
        snap.write_text(json.dumps(data, indent=2, sort_keys=True))
        r = run(xsm_pytester)
        r.assert_outcomes(failed=1)
        out = r.stdout.str()
        assert "SnapshotMismatchError" in out
        assert '"n": 3' in out and '"n": 2' in out
        assert "---" in out and "+++" in out

    def test_snapshot_path_outside_the_test_tree_is_refused(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_module("""
            CFG = {"id": "t", "initial": "a", "states": {"a": {}}}

            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_interp, xsm_snapshot):
                xsm_snapshot(xsm_interp, "../../../../etc/evil.json")
            """))
        r = run(xsm_pytester, "--xsm-update-snapshots")
        out = r.stdout.str() + r.stderr.str()
        assert r.ret != 0
        assert not (xsm_pytester.path.parent.parent / "etc").exists()
        assert "outside the project" in out


# -----------------------------------------------------------------------------
# 3. the send_all grammar
# -----------------------------------------------------------------------------
class TestSendAll:
    def test_timeout_fires_through_the_grammar(
        self, xsm_pytester: Any
    ) -> None:
        _needs_example()
        xsm_pytester.makepyfile(_module("""
            @pytest.mark.xstate_machine(CHART)
            def test_expiry(xsm_interp, xsm_send_all):
                xsm_interp.send("ADD_ITEM", sku="tea", qty=1)
                xsm_send_all(xsm_interp, "CHECKOUT", "+900000")
                assert xsm_interp.matches("order.expired")
            """))
        run(xsm_pytester).assert_outcomes(passed=1)

    @pytest.mark.parametrize("bad", ["+nan", "+-5", "+abc", "+inf", "+1e309"])
    def test_bad_clock_tokens_are_errors_not_hangs(
        self, xsm_pytester: Any, bad: str
    ) -> None:
        xsm_pytester.makepyfile(_module(f"""
            CFG = {{"id": "t", "initial": "a", "states": {{"a": {{}}}}}}

            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_interp, xsm_send_all):
                xsm_send_all(xsm_interp, {bad!r})
            """))
        # 📝 pytest-timeout is not in every venv (3.9 lacks it): pass the
        #    flag only when the plugin exists; the inner test is sub-second.
        extra = (
            ("--timeout=30",)
            if importlib.util.find_spec("pytest_timeout")
            else ()
        )
        r = run(xsm_pytester, *extra)
        r.assert_outcomes(failed=1)
        assert (
            "Traceback"
            not in r.stdout.str().split("short test summary")[0][-400:]
        )


# -----------------------------------------------------------------------------
# 4. guards_false marker
# -----------------------------------------------------------------------------
class TestGuardsFalse:
    def test_forces_named_guards_under_stub_logic(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_module("""
            CFG = {"id": "g", "initial": "a",
                   "states": {"a": {"on": {"GO": [{"target": "b", "guard": "ok"}, {"target": "c"}]}},
                              "b": {}, "c": {}}}

            @pytest.mark.xstate_machine(CFG)
            def test_default(xsm_interp):
                xsm_interp.send("GO"); assert xsm_interp.matches("g.b")

            @pytest.mark.xstate_machine(CFG)
            @pytest.mark.xstate_guards_false("ok")
            def test_forced(xsm_interp, xsm_guards):
                xsm_interp.send("GO"); assert xsm_interp.matches("g.c")
                assert xsm_guards == {"ok": False}

            @pytest.mark.xstate_machine(CFG)
            @pytest.mark.xstate_guards_false("nope")
            def test_unknown_guard(xsm_interp):
                pass
            """))
        r = run(xsm_pytester)
        assert r.parseoutcomes().get("passed") == 2
        assert r.parseoutcomes().get("errors", 0) == 1
        assert "nope" in r.stdout.str() + r.stderr.str()


# -----------------------------------------------------------------------------
# 5. xsm_path on the real chart
# -----------------------------------------------------------------------------
class TestPathsOnRealChart:
    def test_one_case_per_configuration_all_replay(
        self, xsm_pytester: Any
    ) -> None:
        _needs_example()
        xsm_pytester.makepyfile(_module("""
            @pytest.mark.xstate_machine(CHART)
            def test_reach(xsm_path, xsm_interp, xsm_clock):
                xsm_path.replay(xsm_interp, xsm_clock)
                assert xsm_interp.current_state_ids == set(xsm_path.final_states)
            """))
        ids = run(xsm_pytester, "--collect-only")
        assert any(
            "path[cart" in line for line in ids.stdout.lines
        ), ids.stdout.str()
        r = run(xsm_pytester)
        assert r.parseoutcomes().get("passed", 0) == 9  # one per config


# -----------------------------------------------------------------------------
# 6. parallel (xdist) parity
# -----------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_XDIST, reason="pytest-xdist not installed")
class TestParallel:
    def test_xdist_same_outcomes_and_snapshots(
        self, xsm_pytester: Any
    ) -> None:
        body = _module(SNAP_MODULE) + textwrap.dedent("""
            for k in range(8):
                @pytest.mark.xstate_machine(CFG, logic="test_snap:make")
                def _t(xsm_interp, xsm_snapshot, k=k):
                    for _ in range(k):
                        xsm_interp.send("ADD")
                    xsm_snapshot(xsm_interp, f"snapshots/n{k}.json")
                globals()[f"test_n{k}"] = _t
            """)
        xsm_pytester.makepyfile(test_snap=body)
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=9)
        serial = {
            p.name: p.read_bytes()
            for p in (xsm_pytester.path / "snapshots").glob("*.json")
        }
        shutil.rmtree(xsm_pytester.path / "snapshots")
        r = xsm_pytester.runpytest_subprocess(
            *PLUGIN_ARGS,
            "-q",
            "-n",
            "4",
            "--xsm-update-snapshots",
            "-p",
            "no:django",
        )
        r.assert_outcomes(passed=9)
        parallel = {
            p.name: p.read_bytes()
            for p in (xsm_pytester.path / "snapshots").glob("*.json")
        }
        assert parallel == serial
        r2 = xsm_pytester.runpytest_subprocess(
            *PLUGIN_ARGS, "-q", "-n", "4", "-p", "no:django"
        )
        r2.assert_outcomes(passed=9)


# -----------------------------------------------------------------------------
# 7. opt-out
# -----------------------------------------------------------------------------
class TestOptOut:
    def test_disabled_plugin_touches_nothing(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(
            test_plain="def test_ok():\n    assert 1\n",
            test_marked=_module("""
            CFG = {"id": "t", "initial": "a", "states": {"a": {}}}

            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_interp):
                pass
            """),
        )
        r = xsm_pytester.runpytest_inprocess(
            "-p",
            "no:xstate_statemachine",
            "-p",
            "no:django",
            "-q",
            "-W",
            "ignore::pytest.PytestUnknownMarkWarning",
        )
        out = r.stdout.str()
        assert "test_plain.py" not in out or "passed" in out
        assert "fixture 'xsm_interp' not found" in out


# -----------------------------------------------------------------------------
# 8. the generated template runs under the plugin
# -----------------------------------------------------------------------------
class TestGeneratedTemplate:
    def test_xsm_gt_pytest_fixtures_module_passes(
        self, xsm_pytester: Any, tmp_path: pathlib.Path
    ) -> None:
        _needs_example()
        out_dir = tmp_path / "gen"
        out_dir.mkdir()
        env = {"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        import os

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "xstate_statemachine",
                "gt",
                str(CHART),
                "-t",
                "pytest",
                "--fixtures",
                "-o",
                str(out_dir),
            ],
            cwd=str(ROOT),
            env={**os.environ, **env},
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        tests = list(out_dir.rglob("test_*.py"))
        assert tests, list(out_dir.rglob("*"))
        # the common layout: generated module in gen/, chart one level up
        gen = xsm_pytester.path / "gen"
        gen.mkdir()
        for t in tests:
            shutil.copy(t, gen / t.name)
        shutil.copy(CHART, xsm_pytester.path / CHART.name)
        r = run(xsm_pytester, "gen")
        assert r.ret == 0, r.stdout.str()[-2000:]
        assert r.parseoutcomes().get("passed", 0) >= 1
