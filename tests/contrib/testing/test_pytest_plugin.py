# tests/contrib/testing/test_pytest_plugin.py
"""#268: the `[testing]` pytest plugin, exercised through `pytester`.

🏛️ Every case runs a small inline test file under a fresh pytest so the
plugin is tested the way a user meets it: via the `pytest11` entry point,
markers and `xsm_*` fixtures -- not by calling fixture functions directly.
"""

from __future__ import annotations

import json
import pathlib
import sys
import textwrap

import pytest

from tests.contrib.conftest import requires_extra

pytest_plugins = ["pytester"]
pytestmark = requires_extra("testing")

ROOT = pathlib.Path(__file__).resolve().parents[3]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
ADVANCE = CORPUS / "AdvancePayment.json"

TOGGLE = {
    "id": "t",
    "initial": "off",
    "context": {"n": 0},
    "states": {
        "off": {
            "on": {"FLIP": {"target": "on", "guard": "ok", "actions": "bump"}},
            "after": {"1000": {"target": "timeout"}},
        },
        "on": {"on": {"FLIP": "off"}},
        "timeout": {"type": "final"},
    },
}


def _write(pytester: pytest.Pytester, body: str, **files: str) -> None:
    pytester.makepyfile(
        test_inline=textwrap.dedent(body).replace("ROOT", repr(str(ROOT)))
    )
    for name, content in files.items():
        (pytester.path / name).write_text(content, encoding="utf-8")


def _run(pytester: pytest.Pytester, *args: str) -> pytest.RunResult:
    pytester.syspathinsert(str(ROOT / "src"))
    return pytester.runpytest_inprocess("-p", "no:cacheprovider", "-q", *args)


class TestNoOpWithoutMarker:
    def test_plain_suite_is_untouched(self, pytester: pytest.Pytester):
        _write(pytester, "def test_x():\n    assert 1\n")
        res = _run(pytester)
        res.assert_outcomes(passed=1)
        assert "xstate" not in res.stdout.str().lower()

    def test_fixture_without_marker_fails_loudly(self, pytester):
        _write(pytester, "def test_x(xsm_interp):\n    pass\n")
        res = _run(pytester)
        res.assert_outcomes(errors=1)  # fixture setup, so an ERROR
        res.stdout.fnmatch_lines(["*requires*xstate_machine*"])

    def test_version_flag(self, pytester: pytest.Pytester):
        _write(pytester, "def test_x():\n    pass\n")
        res = _run(pytester, "--xsm-version")
        assert res.ret == 0
        res.stdout.fnmatch_lines(["xstate-statemachine *"])

    def test_opt_out_disables_fixtures(self, pytester: pytest.Pytester):
        _write(
            pytester,
            """
            import pytest
            @pytest.mark.xstate_machine({"id": "m", "initial": "a",
                                         "states": {"a": {}}})
            def test_x(xsm_interp):
                pass
            """,
        )
        res = _run(pytester, "-p", "no:xstate_statemachine")
        assert res.ret != 0
        res.stdout.fnmatch_lines(["*fixture 'xsm_interp' not found*"])


class TestSources:
    def test_dict_source_stub_logic_and_ran(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        _write(
            pytester,
            """
            import json, pytest
            CFG = json.load(open("chart.json"))
            @pytest.mark.xstate_machine(CFG)
            def test_x(xsm_interp, xsm_ran):
                xsm_interp.send("FLIP")
                assert xsm_interp.matches("t.on")
                assert xsm_ran == ["bump"]
            """,
        )
        _run(pytester).assert_outcomes(passed=1)

    def test_json_path_relative_to_test_file_and_rootdir(self, pytester):
        (pytester.path / "charts").mkdir()
        (pytester.path / "charts" / "t.json").write_text(json.dumps(TOGGLE))
        _write(
            pytester,
            """
            import pytest
            @pytest.mark.xstate_machine("charts/t.json")
            def test_x(xsm_interp):
                assert xsm_interp.matches("t.off")
            @pytest.mark.xstate_machine(ROOT + "/tests/tests_cli/"
                                        "stately_machines/AdvancePayment.json")
            def test_abs(xsm_interp):
                assert xsm_interp.matches("Advance payment flow.editing")
            """,
        )
        _run(pytester).assert_outcomes(passed=2)

    def test_missing_path_is_usage_error(self, pytester):
        _write(
            pytester,
            """
            import pytest
            @pytest.mark.xstate_machine("nope.json")
            def test_x(xsm_interp):
                pass
            """,
        )
        res = _run(pytester)
        assert res.ret != 0
        res.stdout.fnmatch_lines(["*chart 'nope.json' not found*"])

    def test_machine_node_source(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        _write(
            pytester,
            """
            import json, pytest
            from xstate_statemachine import create_machine
            from xstate_statemachine.testing_utils import stub_logic
            CFG = json.load(open("chart.json"))
            M = create_machine(CFG, logic=stub_logic(CFG))
            @pytest.mark.xstate_machine(M)
            def test_x(xsm_machine, xsm_interp):
                assert xsm_machine is M
                xsm_interp.send("FLIP")
                assert xsm_interp.matches("t.on")
            """,
        )
        _run(pytester).assert_outcomes(passed=1)

    def test_dotted_logic_callable(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        (pytester.path / "mylogic.py").write_text(textwrap.dedent("""
                from xstate_statemachine import MachineLogic
                CALLS = []
                def make():
                    return MachineLogic(
                        actions={"bump": lambda i, c, e, a: CALLS.append(1)},
                        guards={"ok": lambda c, e: False},
                    )
                """))
        _write(
            pytester,
            """
            import json, pytest
            CFG = json.load(open("chart.json"))
            @pytest.mark.xstate_machine(CFG, logic="mylogic:make")
            def test_x(xsm_interp, xsm_ran):
                r = xsm_interp.send("FLIP")
                assert xsm_interp.matches("t.off")   # real guard said no
                assert xsm_ran == []                  # not stub logic
            """,
        )
        _run(pytester).assert_outcomes(passed=1)

    def test_unknown_marker_kwarg_fails(self, pytester):
        _write(
            pytester,
            """
            import pytest
            @pytest.mark.xstate_machine({"id": "m", "initial": "a",
                                         "states": {"a": {}}}, bogus=1)
            def test_x(xsm_interp):
                pass
            """,
        )
        res = _run(pytester)
        assert res.ret != 0
        res.stdout.fnmatch_lines(["*unknown xstate_machine option*bogus*"])


class TestGuardsClockStore:
    def test_guards_false_marker_and_live_flip(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        _write(
            pytester,
            """
            import json, pytest
            CFG = json.load(open("chart.json"))
            @pytest.mark.xstate_machine(CFG)
            @pytest.mark.xstate_guards_false("ok")
            def test_x(xsm_interp, xsm_guards):
                r = xsm_interp.send("FLIP", wait=True)
                assert r.denied and xsm_interp.matches("t.off")
                xsm_guards["ok"] = True
                xsm_interp.send("FLIP")
                assert xsm_interp.matches("t.on")
            """,
        )
        _run(pytester).assert_outcomes(passed=1)

    def test_guards_false_with_real_logic_is_usage_error(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        (pytester.path / "mylogic.py").write_text(
            "from xstate_statemachine import MachineLogic\n"
            "def make():\n    return MachineLogic(actions={'bump': "
            "lambda i,c,e,a: None}, guards={'ok': lambda c,e: True})\n"
        )
        _write(
            pytester,
            """
            import json, pytest
            CFG = json.load(open("chart.json"))
            @pytest.mark.xstate_machine(CFG, logic="mylogic:make")
            @pytest.mark.xstate_guards_false("ok")
            def test_x(xsm_interp):
                pass
            """,
        )
        res = _run(pytester)
        assert res.ret != 0
        res.stdout.fnmatch_lines(["*only applies to stub logic*"])

    def test_clock_send_all_and_store(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        _write(
            pytester,
            """
            import json, pytest
            CFG = json.load(open("chart.json"))
            @pytest.mark.xstate_machine(CFG)
            def test_x(xsm_interp, xsm_clock, xsm_send_all, xsm_store):
                xsm_send_all(xsm_interp, "+999")
                assert xsm_interp.matches("t.off")
                xsm_send_all(xsm_interp, "+1")
                assert xsm_interp.matches("t.timeout")
                xsm_store.save("k", xsm_interp.get_snapshot())
                assert xsm_store.load("k") is not None
            """,
        )
        _run(pytester).assert_outcomes(passed=1)


class TestSnapshots:
    def test_update_then_pass_then_diff(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        body = """
            import json, pytest
            CFG = json.load(open("chart.json"))
            @pytest.mark.xstate_machine(CFG)
            def test_x(xsm_interp, xsm_snapshot):
                xsm_interp.send("FLIP")
                xsm_snapshot(xsm_interp, "snaps/after_flip.json")
            """
        _write(pytester, body)
        res = _run(pytester)  # no file yet -> fail with instruction
        res.assert_outcomes(failed=1)
        res.stdout.fnmatch_lines(["*--xsm-update-snapshots*"])
        _run(pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        snap = pytester.path / "snaps" / "after_flip.json"
        first = snap.read_text(encoding="utf-8")
        data = json.loads(first)
        assert data["state_ids"] == ["t.on"]
        for volatile in ("taken_at", "machine_hash", "version"):
            assert volatile not in data
        _run(pytester).assert_outcomes(passed=1)  # deterministic
        assert snap.read_text(encoding="utf-8") == first
        # 🔀 change behaviour -> unified diff
        _write(pytester, body.replace('send("FLIP")', 'send("NOPE")'))
        res = _run(pytester)
        res.assert_outcomes(failed=1)
        res.stdout.fnmatch_lines(["*snapshot mismatch*", "*-*t.on*"])


class TestAsync:
    def test_ainterp_skips_without_pytest_asyncio(self, pytester):
        _write(
            pytester,
            """
            import sys, pytest
            sys.modules["pytest_asyncio"] = None  # simulate absence
            @pytest.mark.xstate_machine({"id": "m", "initial": "a",
                                         "states": {"a": {}}})
            def test_x(xsm_ainterp):
                pass
            """,
        )
        res = _run(pytester, "-p", "no:asyncio", "-rs")
        res.assert_outcomes(skipped=1)
        res.stdout.fnmatch_lines(["*pytest-asyncio*"])

    @pytest.mark.skipif(
        "pytest_asyncio" not in sys.modules
        and not __import__("importlib").util.find_spec("pytest_asyncio"),
        reason="pytest-asyncio not installed",
    )
    def test_ainterp_runs_under_pytest_asyncio(self, pytester):
        (pytester.path / "chart.json").write_text(json.dumps(TOGGLE))
        _write(
            pytester,
            """
            import json, pytest
            CFG = json.load(open("chart.json"))
            @pytest.mark.xstate_machine(CFG)
            @pytest.mark.asyncio
            async def test_x(xsm_ainterp, xsm_ran):
                i = await xsm_ainterp()
                await i.send("FLIP", wait=True)
                assert i.matches("t.on") and xsm_ran == ["bump"]
                await i.stop()
            """,
        )
        _run(pytester).assert_outcomes(passed=1)
