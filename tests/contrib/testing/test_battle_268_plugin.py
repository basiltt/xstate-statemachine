# tests/contrib/testing/test_battle_268_plugin.py
"""#268 battle (adversary A): marker parsing, fixture lifecycle, logic
loading, `xsm_send_all` grammar and plugin hygiene -- each case a
throw-away `pytester` session."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys
import textwrap
from typing import Any

import pytest

from .conftest import CORPUS, SRC, run

pytestmark = pytest.mark.timeout(300)

CFG = (
    'CFG = {"id": "t", "initial": "a", "states": {"a": {"on": '
    '{"GO": "b", "PAY": {"target": "b", "guard": "ok"}}, '
    '"after": {"1000": "c"}}, "b": {}, "c": {}}}\n'
)


def _mod(body: str) -> str:
    return "import pytest\n" + CFG + textwrap.dedent(body)


def _out(result: Any) -> str:
    return str(result.stdout.str()) + str(result.stderr.str())


# -----------------------------------------------------------------------------
# 1. marker parsing
# -----------------------------------------------------------------------------
class TestMarkerParsing:
    @pytest.mark.parametrize(
        "marker",
        [
            "(CFG, CFG)",
            '(CFG, logics="x:y")',
            '(CFG, strict="false")',
            "()",
            "(42)",
        ],
    )
    def test_malformed_marker_is_a_clean_error(
        self, xsm_pytester: Any, marker: str
    ) -> None:
        xsm_pytester.makepyfile(_mod(f"""
            @pytest.mark.xstate_machine{marker}
            def test_it(xsm_interp):
                pass
            """))
        result = run(xsm_pytester)
        out = _out(result)
        assert "test_it" in out
        assert "Traceback" not in out
        assert result.ret != 0

    def test_function_marker_overrides_module_pytestmark(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            OTHER = {"id": "o", "initial": "x", "states": {"x": {}}}
            pytestmark = pytest.mark.xstate_machine(OTHER)

            def test_module(xsm_interp):
                assert xsm_interp.current_state_ids == {"o.x"}

            @pytest.mark.xstate_machine(CFG)
            def test_override(xsm_interp):
                assert "t.a" in xsm_interp.current_state_ids
            """))
        run(xsm_pytester).assert_outcomes(passed=2)

    def test_stacked_twice_closest_wins(self, xsm_pytester: Any) -> None:
        # 📝 Documented: the decorator nearest the function wins
        #    (`get_closest_marker`), like every other pytest marker.
        xsm_pytester.makepyfile(_mod("""
            OTHER = {"id": "o", "initial": "x", "states": {"x": {}}}
            @pytest.mark.xstate_machine(OTHER)
            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_interp):
                assert "t.a" in xsm_interp.current_state_ids
            """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_path_source_and_shared_machine_node(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makefile(
            ".json",
            m='{"id": "j", "initial": "a", "states": {"a": {}}}',
        )
        xsm_pytester.makepyfile(_mod("""
            import pathlib
            from xstate_statemachine import create_machine
            from xstate_statemachine.testing_utils import stub_logic
            NODE = create_machine(CFG, logic=stub_logic(CFG))
            P = pathlib.Path(__file__).parent / "m.json"

            @pytest.mark.xstate_machine(P)
            def test_path(xsm_interp):
                assert xsm_interp.current_state_ids == {"j.a"}

            @pytest.mark.xstate_machine(NODE)
            def test_node1(xsm_interp):
                xsm_interp.send("GO")
                assert "t.b" in xsm_interp.current_state_ids

            @pytest.mark.xstate_machine(NODE)
            def test_node2(xsm_interp):
                assert "t.a" in xsm_interp.current_state_ids
            """))
        run(xsm_pytester).assert_outcomes(passed=3)

    def test_parametrized_builds_once_per_param(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            seen = []

            @pytest.mark.parametrize("n", [1, 2, 3])
            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_machine, xsm_ran, n):
                seen.append(xsm_machine)  # hold it: id() reuse after GC
                assert xsm_ran == []

            def test_distinct():
                assert len({id(m) for m in seen}) == 3
            """))
        run(xsm_pytester).assert_outcomes(passed=4)

    def test_guards_false_without_machine_marker(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            @pytest.mark.xstate_guards_false("ok")
            def test_it(xsm_interp):
                pass
            """))
        result = run(xsm_pytester)
        assert "needs an" in _out(result)
        assert result.ret != 0


# -----------------------------------------------------------------------------
# 2. fixture lifecycle
# -----------------------------------------------------------------------------
class TestLifecycle:
    def test_threads_flat_and_timer_dead_after_teardown(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            import threading
            kept = []
            counts = []

            @pytest.mark.parametrize("n", range(200))
            @pytest.mark.xstate_machine(CFG)
            def test_many(xsm_interp, n):
                kept.append(xsm_interp)
                counts.append(threading.active_count())

            def test_after():
                assert max(counts) - min(counts) <= 2
                assert all(i.status == "stopped" for i in kept)
                assert all("t.a" in i.current_state_ids for i in kept[:5])
            """))
        run(xsm_pytester).assert_outcomes(passed=201)

    def test_self_stop_and_fresh_clock_store_ran(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            @pytest.mark.xstate_machine(CFG)
            def test_stop_myself(xsm_interp, xsm_clock, xsm_store, xsm_ran):
                xsm_clock.increment(10**9)
                xsm_store.save("k", "v")
                xsm_interp.stop()

            @pytest.mark.xstate_machine(CFG)
            def test_fresh(xsm_interp, xsm_clock, xsm_store, xsm_ran):
                assert xsm_clock.now() == 0
                assert xsm_store.load("k") is None
                assert xsm_ran == []
                assert "t.a" in xsm_interp.current_state_ids
            """))
        run(xsm_pytester).assert_outcomes(passed=2)

    def test_module_scoped_user_fixture_is_scope_error(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            @pytest.fixture(scope="module")
            def shared(xsm_interp):
                return xsm_interp

            @pytest.mark.xstate_machine(CFG)
            def test_it(shared):
                pass
            """))
        result = run(xsm_pytester)
        assert "ScopeMismatch" in _out(result)

    def test_ainterp_without_asyncio_skips(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(_mod("""
            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_ainterp):
                pass
            """))
        result = run(xsm_pytester, "-p", "no:asyncio", "-rs")
        result.assert_outcomes(skipped=1)
        assert "pytest-asyncio" in _out(result)

    def test_ainterp_asend_all_snapshot_together(
        self, xsm_pytester: Any
    ) -> None:
        pytest.importorskip("pytest_asyncio")
        xsm_pytester.makepyfile(_mod("""
            @pytest.mark.asyncio
            @pytest.mark.xstate_machine(CFG)
            async def test_it(xsm_ainterp, xsm_asend_all, xsm_snapshot):
                await xsm_asend_all(xsm_ainterp, "+1000")
                assert "t.c" in xsm_ainterp.current_state_ids
                xsm_snapshot(xsm_ainterp, "snaps/c.json")
            """))
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        run(xsm_pytester).assert_outcomes(passed=1)


# -----------------------------------------------------------------------------
# 3. logic loading
# -----------------------------------------------------------------------------
class TestLogicLoading:
    def test_logic_errors_are_one_usage_error(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(
            badlogic="import nope_missing_pkg\n",
            needargs=(
                "def make(x):\n    return x\n"
                "def as_dict():\n    return {'actions': {}}\n"
            ),
        )
        xsm_pytester.makepyfile(test_l=_mod("""
            @pytest.mark.xstate_machine(CFG, logic="badlogic:make")
            def test_raises_on_import(xsm_interp):
                pass

            @pytest.mark.xstate_machine(CFG, logic="needargs:make")
            def test_needs_args(xsm_interp):
                pass

            @pytest.mark.xstate_machine(CFG, logic="needargs:as_dict")
            def test_dict(xsm_interp):
                pass
            """))
        xsm_pytester.syspathinsert()
        result = run(xsm_pytester)
        out = _out(result)
        assert "Traceback" not in out
        assert "nope_missing_pkg" in out
        assert "missing 1 required positional argument" in out
        assert "got dict" in out

    def test_logic_instance_and_callable_accepted(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(_mod("""
            from xstate_statemachine import MachineLogic
            L = MachineLogic(guards={"ok": lambda c, e: False})

            @pytest.mark.xstate_machine(CFG, logic=L)
            def test_instance(xsm_interp):
                xsm_interp.send("PAY")
                assert "t.a" in xsm_interp.current_state_ids

            @pytest.mark.xstate_machine(CFG, logic=lambda: L)
            def test_callable(xsm_interp):
                xsm_interp.send("PAY")
                assert "t.a" in xsm_interp.current_state_ids
            """))
        run(xsm_pytester).assert_outcomes(passed=2)

    def test_strict_config_names_unknown_key(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(_mod("""
            BAD = {"id": "t", "initial": "a", "bogusKey": 1,
                   "states": {"a": {}}}

            @pytest.mark.xstate_machine(BAD, strict_config=True)
            def test_it(xsm_interp):
                pass
            """))
        result = run(xsm_pytester)
        assert "bogusKey" in _out(result)
        assert result.ret != 0


# -----------------------------------------------------------------------------
# 5. xsm_send_all grammar
# -----------------------------------------------------------------------------
class TestSendAll:
    def test_payload_forms_and_tokens(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(_mod("""
            from xstate_statemachine import Event
            seen = []

            def logic():
                from xstate_statemachine import MachineLogic
                return MachineLogic(guards={
                    "ok": lambda c, e: seen.append(dict(e.payload)) or True})

            @pytest.mark.xstate_machine(CFG, logic=logic)
            def test_tuple(xsm_interp, xsm_send_all):
                xsm_send_all(xsm_interp, ("PAY", {"amount": 1}))
                assert seen[-1] == {"amount": 1}

            @pytest.mark.xstate_machine(CFG, logic=logic)
            def test_dict(xsm_interp, xsm_send_all):
                xsm_send_all(xsm_interp, {"type": "PAY", "amount": 2})
                assert seen[-1] == {"amount": 2}

            @pytest.mark.xstate_machine(CFG, logic=logic)
            def test_event(xsm_interp, xsm_send_all):
                xsm_send_all(xsm_interp, Event("PAY", {"amount": 3}))
                assert seen[-1] == {"amount": 3}

            @pytest.mark.xstate_machine(CFG)
            def test_plus_forms(xsm_interp, xsm_send_all, xsm_clock):
                xsm_send_all(xsm_interp, "+0", "+1.5", "+ 500")
                assert xsm_clock.now() * 1000 == pytest.approx(501.5)

            @pytest.mark.parametrize("tok", ["++5", "", "A,B"])
            @pytest.mark.xstate_machine(CFG)
            def test_bad(xsm_interp, xsm_send_all, tok):
                with pytest.raises(ValueError):
                    xsm_send_all(xsm_interp, tok)

            @pytest.mark.xstate_machine(CFG)
            def test_stopped(xsm_interp, xsm_send_all):
                # 📝 The engine logs and drops; no hang, no exception.
                xsm_interp.stop()
                xsm_send_all(xsm_interp, "GO")
                assert xsm_interp.status == "stopped"
            """))
        run(xsm_pytester).assert_outcomes(passed=8)


# -----------------------------------------------------------------------------
# 6. plugin hygiene
# -----------------------------------------------------------------------------
class TestHygiene:
    def test_import_does_not_pull_hypothesis_or_pydantic(self) -> None:
        code = (
            "import sys; sys.path.insert(0, %r);"
            "import xstate_statemachine.contrib.testing.pytest_plugin;"
            "bad = [m for m in ('hypothesis', 'pydantic', 'pytest_asyncio')"
            " if m in sys.modules]; print(bad)" % str(SRC)
        )
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert out.strip() == "[]"

    def test_markers_listed_and_strict_markers(
        self, xsm_pytester: Any
    ) -> None:
        result = run(xsm_pytester, "--markers")
        out = _out(result)
        assert "xstate_machine(source" in out
        assert "xstate_guards_false(*names)" in out
        xsm_pytester.makepyfile(_mod("""
            @pytest.mark.xstate_guards_false("ok")
            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_interp):
                xsm_interp.send("PAY")
                assert "t.a" in xsm_interp.current_state_ids
            """))
        run(
            xsm_pytester,
            "--strict-markers",
            "-W",
            "error",
            "-p",
            "no:cacheprovider",
            "--import-mode=importlib",
        ).assert_outcomes(passed=1)

    def test_version_runs_no_tests(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile("def test_x():\n    raise SystemExit(9)\n")
        result = run(xsm_pytester, "--xsm-version")
        assert result.ret == 0
        assert "xstate-statemachine" in _out(result)

    def test_doctest_modules_with_marker(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(_mod('''
            def helper():
                """
                >>> 1 + 1
                2
                """

            @pytest.mark.xstate_machine(CFG)
            def test_it(xsm_interp):
                assert "t.a" in xsm_interp.current_state_ids
            '''))
        run(xsm_pytester, "--doctest-modules").assert_outcomes(passed=2)


# -----------------------------------------------------------------------------
# 7. the generated template over corpus charts
# -----------------------------------------------------------------------------
CORPUS_CHARTS = [
    "HelloWorld.json",
    "SimplePayment.json",
    "Parallelism.json",
    "Hierarchy.json",
    "Kiosk.json",
    "Parking.json",
    "Installation_v1.json",
    "Joyride.json",
    "ConsoleLifecycle.json",
    "TMC2209.json",
]
UNICODE_CHART = {
    "id": "café",
    "initial": "attente",
    "states": {
        "attente": {"on": {"PAYÉ": "réglé", "ÜBER-GEHEN": "fertig"}},
        "réglé": {"type": "final"},
        "fertig": {},
    },
}


def _gt(chart: pathlib.Path, out: pathlib.Path, *extra: str) -> None:
    env = dict(
        os.environ,
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
        PYTHONPATH=str(SRC),
    )
    proc = subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "gt", str(chart)]
        + ["-t", "pytest", *extra, "-o", str(out)],
        env=env,
        capture_output=True,
        text=True,
        errors="replace",
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


class TestGeneratedTemplate:
    @pytest.mark.parametrize("fixtures", [True, False])
    def test_corpus_modules_pass_from_generated_dir(
        self, xsm_pytester: Any, fixtures: bool
    ) -> None:
        charts = [CORPUS / name for name in CORPUS_CHARTS]
        gen = xsm_pytester.path / "generated"
        uni = xsm_pytester.path / "unicode.json"
        uni.write_text(json.dumps(UNICODE_CHART), encoding="utf-8")
        for chart in charts + [uni]:
            # 📝 `-o generated/<chart>/` with the chart one level up: the
            #    layout the template's CONFIG_PATH fallback supports.
            out = gen / chart.stem
            out.mkdir(parents=True)
            _gt(chart, out, *(["--fixtures"] if fixtures else []))
            shutil.copy(chart, gen / chart.name)
        tests = list(gen.rglob("test_*.py"))
        assert len(tests) == len(charts) + 1
        for t in tests:
            # 📝 Non-ASCII state / event names must still make valid,
            #    importable test identifiers.
            compile(t.read_text(encoding="utf-8"), str(t), "exec")
        r = run(xsm_pytester, "generated", "--import-mode=importlib")
        assert r.ret == 0, r.stdout.str()[-3000:]

    def test_chart_engine_rejects_is_one_line_not_traceback(
        self, tmp_path: pathlib.Path
    ) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text(
            json.dumps({"id": "bad", "states": {"a": {}, "b": {}}}),
            encoding="utf-8",
        )
        env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(SRC))
        proc = subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", "gt", str(bad)]
            + ["-t", "pytest", "--fixtures", "-o", str(tmp_path)],
            env=env,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=120,
        )
        assert proc.returncode == 1
        assert "Traceback" not in proc.stderr
        assert "cannot generate the pytest companion" in proc.stderr
