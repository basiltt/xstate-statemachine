"""The `[testing]` pytest plugin: fixtures, markers, options, snapshots (#268).

Every case below writes a small test module into a throw-away `pytester`
session and asserts on that session's outcome -- the plugin is exercised
exactly as a user's pytest run would exercise it. Both engines are covered
(`xsm_interp` and `xsm_ainterp`); timing is virtual (`SimulatedClock`).
"""

from __future__ import annotations

import importlib.util
import json
import sys
import textwrap

import pytest

from src.xstate_statemachine.contrib.testing.pytest_plugin import (
    SNAPSHOT_KEYS,
    SnapshotMismatchError,
    normalize_snapshot,
    render_snapshot,
)

from .conftest import CORPUS, NO_DJANGO, PLUGIN, PLUGIN_ARGS, run

# 📝 No `requires_extra("testing")` gate: the plugin needs only pytest (always
#    present here) and ships through an unconditional entry point, so every
#    matrix cell must run this suite -- hypothesis is not a precondition.
# 🧷 The async-run test has its own `pytest-asyncio` skip below.

HAS_ASYNCIO_PLUGIN = importlib.util.find_spec("pytest_asyncio") is not None

#: A chart with one of everything the fixtures touch: an action, a guard,
#: an `after` timer and a context key.
TOGGLE = {
    "id": "toggle",
    "initial": "off",
    "context": {"n": 0},
    "states": {
        "off": {
            "on": {
                "TOGGLE": {"target": "on", "actions": "bump", "guard": "ok"}
            },
            "after": {"500": "on"},
        },
        "on": {"on": {"TOGGLE": "off"}},
    },
}

PRELUDE = f"import json, pytest\nCFG = {TOGGLE!r}\n"


def _module(body: str) -> str:
    return PRELUDE + textwrap.dedent(body)


# =============================================================================
# Sources: dict, JSON path (next to the test file, then rootdir), MachineNode
# =============================================================================
class TestSources:
    def test_dict_source_builds_the_machine(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                def test_it(xsm_machine, xsm_interp):
                    assert xsm_machine.id == "toggle"
                    assert xsm_interp.matches("toggle.off")
                    assert xsm_interp.status == "running"
                """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_json_path_relative_to_the_test_file(self, xsm_pytester) -> None:
        (xsm_pytester.path / "machines").mkdir()
        (xsm_pytester.path / "machines" / "toggle.json").write_text(
            json.dumps(TOGGLE), encoding="utf-8"
        )
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine("machines/toggle.json")
                def test_it(xsm_interp):
                    xsm_interp.send("TOGGLE")
                    assert xsm_interp.matches("toggle.on")
                """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_json_path_falls_back_to_rootdir(self, xsm_pytester) -> None:
        (xsm_pytester.path / "charts").mkdir()
        (xsm_pytester.path / "charts" / "t.json").write_text(
            json.dumps(TOGGLE), encoding="utf-8"
        )
        sub = xsm_pytester.mkpydir("nested")
        (sub / "test_nested.py").write_text(
            _module("""
                @pytest.mark.xstate_machine("charts/t.json")
                def test_it(xsm_machine):
                    assert xsm_machine.id == "toggle"
                """),
            encoding="utf-8",
        )
        run(xsm_pytester, "nested").assert_outcomes(passed=1)

    def test_corpus_machine_from_an_absolute_path(self, xsm_pytester) -> None:
        path = (CORPUS / "AdvancePayment.json").as_posix()
        xsm_pytester.makepyfile(_module(f"""
                @pytest.mark.xstate_machine({path!r})
                def test_flow(xsm_interp, xsm_send_all):
                    xsm_send_all(xsm_interp, "SUBMIT", "+2001")
                    assert xsm_interp.matches("Advance payment flow.success")
                """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_machine_node_source_is_used_as_is(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                from xstate_statemachine import MachineLogic, create_machine

                seen = []
                MACHINE = create_machine(
                    CFG,
                    logic=MachineLogic(
                        actions={"bump": lambda i, c, e, a: seen.append(1)},
                        guards={"ok": lambda c, e: True},
                    ),
                )

                @pytest.mark.xstate_machine(MACHINE)
                def test_it(xsm_machine, xsm_interp, xsm_ran):
                    assert xsm_machine is MACHINE
                    xsm_interp.send("TOGGLE")
                    assert seen == [1]      # the REAL action ran...
                    assert xsm_ran == []    # ...so nothing is recorded here
                """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_strict_on_a_machine_node_is_refused_not_mutated(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_module("""
                from xstate_statemachine import create_machine
                from xstate_statemachine.testing_utils import stub_logic

                MACHINE = create_machine(CFG, logic=stub_logic(CFG))
                BEFORE = MACHINE.strict

                @pytest.mark.xstate_machine(MACHINE, strict=not BEFORE)
                def test_refused(xsm_machine):
                    pass

                def test_node_untouched():
                    assert MACHINE.strict == BEFORE
                """))
        result = run(xsm_pytester)
        result.assert_outcomes(passed=1, errors=1)
        result.stdout.fnmatch_lines(["*UsageError*MachineNode*strict=*"])

    def test_missing_json_file_is_a_usage_error(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine("nope/missing.json")
                def test_it(xsm_machine):
                    pass
                """))
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*UsageError*missing.json*not found*"])

    def test_invalid_config_is_a_usage_error(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine({"id": "broken"})
                def test_it(xsm_machine):
                    pass
                """))
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*UsageError*create_machine failed*"])


# =============================================================================
# Logic: stub default, dotted callable, guards marker
# =============================================================================
class TestLogic:
    def test_stub_logic_records_actions_in_xsm_ran(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                def test_it(xsm_interp, xsm_ran):
                    assert xsm_ran == []
                    xsm_interp.send("TOGGLE")
                    assert xsm_ran == ["bump"]
                    assert xsm_interp.context == {"n": 0}  # stubs do not mutate
                """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_logic_from_a_dotted_callable(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(
            mylogic="""
            from xstate_statemachine import MachineLogic

            def make_logic():
                def bump(i, ctx, e, a):
                    ctx["n"] += 1
                return MachineLogic(
                    actions={"bump": bump}, guards={"ok": lambda c, e: True}
                )
            """,
            test_logic=_module("""
                @pytest.mark.xstate_machine(CFG, logic="mylogic:make_logic")
                def test_it(xsm_interp, xsm_ran):
                    xsm_interp.send("TOGGLE")
                    assert xsm_interp.context["n"] == 1   # real action ran
                    assert xsm_ran == []                   # nothing recorded
                """),
        )
        run(xsm_pytester).assert_outcomes(passed=1)

    @pytest.mark.parametrize(
        "dotted, fragment",
        [
            ("no_such_module:make", "cannot import"),
            ("mylogic:missing", "has no 'missing'"),
            ("mylogic:NOT_CALLABLE", "is not callable"),
            ("mylogic:wrong_type", "must return a MachineLogic"),
            ("mylogic:boom", "logic='mylogic:boom': the factory raised*Kaput"),
            ("mylogic", "dotted 'package.module:callable'"),
        ],
    )
    def test_bad_logic_reference_is_a_usage_error(
        self, xsm_pytester, dotted: str, fragment: str
    ) -> None:
        xsm_pytester.makepyfile(
            mylogic="""
            NOT_CALLABLE = 1
            def wrong_type():
                return {"actions": {}}
            def boom():
                raise RuntimeError("Kaput")
            """,
            test_bad=_module(f"""
                @pytest.mark.xstate_machine(CFG, logic={dotted!r})
                def test_it(xsm_machine):
                    pass
                """),
        )
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines([f"*UsageError*{fragment}*"])

    def test_guards_false_marker_forces_named_guards(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                @pytest.mark.xstate_guards_false("ok")
                def test_it(xsm_interp, xsm_guards, xsm_ran):
                    receipt = xsm_interp.send("TOGGLE", wait=True)
                    assert receipt.denied and xsm_interp.matches("toggle.off")
                    assert xsm_ran == []
                    xsm_guards["ok"] = True          # flip it live
                    xsm_interp.send("TOGGLE")
                    assert xsm_interp.matches("toggle.on")
                    assert xsm_ran == ["bump"]
                """))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_guards_false_with_real_logic_is_refused(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(
            mylogic="""
            from xstate_statemachine import MachineLogic
            def make_logic():
                return MachineLogic(
                    actions={"bump": lambda i, c, e, a: None},
                    guards={"ok": lambda c, e: True},
                )
            """,
            test_refused=_module("""
                @pytest.mark.xstate_machine(CFG, logic="mylogic:make_logic")
                @pytest.mark.xstate_guards_false("ok")
                def test_it(xsm_interp):
                    pass
                """),
        )
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(
            ["*UsageError*xstate_guards_false only applies to stub logic*"]
        )

    def test_guards_false_without_machine_marker_is_refused(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_guards_false("ok")
                def test_it(xsm_interp):
                    pass
                """))
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*UsageError*needs an*xstate_machine*"])

    def test_strict_kwargs_pass_through(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG, strict=True)
                def test_strict(xsm_interp):
                    from xstate_statemachine import UnknownEventError
                    with pytest.raises(UnknownEventError):
                        xsm_interp.send("NOT_DECLARED")

                @pytest.mark.xstate_machine(
                    dict(CFG, actionErrorPolicyy="rollback"), strict_config=True
                )
                def test_strict_config(xsm_machine):
                    pass
                """))
        result = run(xsm_pytester)
        result.assert_outcomes(passed=1, errors=1)
        result.stdout.fnmatch_lines(["*UsageError*create_machine failed*"])

    @pytest.mark.parametrize(
        "marker, fragment",
        [
            ("xstate_machine()", "exactly one positional"),
            ("xstate_machine(CFG, bogus=1)", "unknown keyword"),
            ("xstate_machine(42)", "must be a JSON path"),
            ("xstate_machine(CFG, logic=':x')", "dotted"),
            ("xstate_machine(CFG, strict='false')", "strict= must be True"),
            (
                "xstate_machine(CFG, strict_config=1)",
                "strict_config= must be True",
            ),
        ],
    )
    def test_malformed_machine_marker(
        self, xsm_pytester, marker: str, fragment: str
    ) -> None:
        xsm_pytester.makepyfile(_module(f"""
                @pytest.mark.{marker}
                def test_it(xsm_machine):
                    pass
                """))
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines([f"*UsageError*{fragment}*"])


# =============================================================================
# Clock, send_all, store
# =============================================================================
class TestClockAndHelpers:
    def test_send_all_grammar_advances_the_clock(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                def test_it(xsm_interp, xsm_clock, xsm_send_all):
                    xsm_send_all(xsm_interp, "+499")
                    assert xsm_interp.matches("toggle.off")
                    xsm_send_all(xsm_interp, "+1", "TOGGLE")
                    # +1 ms fired the after(500) -> on; TOGGLE -> off again
                    assert xsm_interp.matches("toggle.off")
                    assert xsm_clock.now() * 1000 == pytest.approx(500)

                @pytest.mark.xstate_machine(CFG)
                def test_numbers_are_clock_advances(xsm_interp, xsm_send_all):
                    xsm_send_all(xsm_interp, 500)
                    assert xsm_interp.matches("toggle.on")

                @pytest.mark.xstate_machine(CFG)
                def test_bad_step_type(xsm_interp, xsm_send_all):
                    with pytest.raises(TypeError, match="event names or"):
                        xsm_send_all(xsm_interp, None)

                @pytest.mark.xstate_machine(CFG)
                def test_big_whole_numbers_are_not_exponent_formatted(
                    xsm_interp, xsm_clock, xsm_send_all
                ):
                    xsm_send_all(xsm_interp, 1_000_000, 2.5, 1e6)
                    assert xsm_clock.now() * 1000 == pytest.approx(2_000_002.5)
                """))
        run(xsm_pytester).assert_outcomes(passed=4)

    def test_store_is_a_fresh_memory_store(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                from xstate_statemachine.persistence import MemoryStore, persisted

                @pytest.mark.xstate_machine(CFG)
                def test_a(xsm_store, xsm_machine):
                    assert isinstance(xsm_store, MemoryStore)
                    with persisted(xsm_store, "k", xsm_machine) as m:
                        m.send("TOGGLE")
                    assert xsm_store.load("k").version == 1

                @pytest.mark.xstate_machine(CFG)
                def test_b(xsm_store):
                    assert xsm_store.load("k") is None   # not shared with test_a
                """))
        run(xsm_pytester).assert_outcomes(passed=2)

    def test_interp_is_stopped_at_teardown(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                KEEP = {}

                @pytest.mark.xstate_machine(CFG)
                def test_a(xsm_interp):
                    KEEP["i"] = xsm_interp
                    assert xsm_interp.status == "running"

                def test_b():
                    assert KEEP["i"].status == "stopped"
                """))
        run(xsm_pytester).assert_outcomes(passed=2)


# =============================================================================
# Async engine
# =============================================================================
class TestAsyncEngine:
    @pytest.mark.skipif(
        not HAS_ASYNCIO_PLUGIN, reason="pytest-asyncio not installed"
    )
    def test_ainterp_under_pytest_asyncio(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.asyncio
                @pytest.mark.xstate_machine(CFG)
                async def test_it(xsm_ainterp, xsm_asend_all, xsm_ran, xsm_clock):
                    assert xsm_ainterp.matches("toggle.off")
                    await xsm_asend_all(xsm_ainterp, "TOGGLE")
                    assert xsm_ainterp.matches("toggle.on")
                    assert xsm_ran == ["bump"]
                    await xsm_asend_all(xsm_ainterp, "TOGGLE", "+500")
                    assert xsm_ainterp.matches("toggle.on")  # timer fired
                    assert xsm_clock.now() * 1000 == pytest.approx(500)

                @pytest.mark.asyncio
                @pytest.mark.xstate_machine(CFG)
                @pytest.mark.xstate_guards_false("ok")
                async def test_guards_apply_to_async_too(xsm_ainterp):
                    r = await xsm_ainterp.send("TOGGLE", wait=True)
                    assert r.denied
                """))
        run(xsm_pytester).assert_outcomes(passed=2)

    def test_ainterp_skips_with_a_message_without_pytest_asyncio(
        self, xsm_pytester
    ) -> None:
        # 📝 Decided from the plugin manager at request time: with the
        #    runner disabled (`-p no:asyncio`) the fixture SKIPS even though
        #    the package is installed -- it must not fail.
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                def test_it(xsm_ainterp):
                    raise AssertionError("must not run")
                """))
        result = xsm_pytester.runpytest_inprocess(
            *PLUGIN_ARGS, *NO_DJANGO, "-p", "no:asyncio", "-q", "-rs"
        )
        result.assert_outcomes(skipped=1)
        result.stdout.fnmatch_lines(
            ["*SKIP*xsm_ainterp needs pytest-asyncio*pip install*"]
        )

    @pytest.mark.skipif(
        not HAS_ASYNCIO_PLUGIN, reason="pytest-asyncio not installed"
    )
    def test_async_fixture_module_is_not_imported_under_no_asyncio(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_module("""
                def test_it(request):
                    pm = request.config.pluginmanager
                    assert not pm.hasplugin("xstate_statemachine_async_fixtures")
                """))
        xsm_pytester.runpytest_subprocess(
            *PLUGIN_ARGS, "-p", "no:asyncio", "-q"
        ).assert_outcomes(passed=1)


# =============================================================================
# Snapshots
# =============================================================================
class TestSnapshots:
    def test_update_writes_then_plain_run_passes(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                def test_it(xsm_interp, xsm_snapshot):
                    xsm_interp.send("TOGGLE")
                    xsm_snapshot(xsm_interp, "snapshots/on.json")
                """))
        # 1. Nothing recorded yet -> fails and says how to record.
        first = run(xsm_pytester)
        first.assert_outcomes(failed=1)
        first.stdout.fnmatch_lines(
            ["*no snapshot file*--xsm-update-snapshots*"]
        )
        # 2. --xsm-update-snapshots writes the file.
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        written = xsm_pytester.path / "snapshots" / "on.json"
        text = written.read_text(encoding="utf-8")
        data = json.loads(text)
        assert set(data) == set(SNAPSHOT_KEYS)
        assert data["state_ids"] == ["toggle.on"]
        assert data["context"] == {"n": 0}
        assert "taken_at" not in text and "machine_hash" not in text
        # 3. Deterministic: the file is byte-identical after a second write.
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        assert written.read_text(encoding="utf-8") == text
        assert text.endswith("\n") and text == render_snapshot(data)
        # 4. A plain run now passes.
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_mismatch_fails_with_a_unified_diff(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                def test_it(xsm_interp, xsm_snapshot):
                    xsm_snapshot(xsm_interp, "snap.json")
                """))
        recorded = render_snapshot(
            {
                "context": {"n": 0},
                "state_ids": ["toggle.on"],
                "status": "running",
                "value": "on",
            }
        )
        (xsm_pytester.path / "snap.json").write_text(
            recorded, encoding="utf-8"
        )
        result = run(xsm_pytester)
        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(
            [
                "*SnapshotMismatchError*snapshot mismatch*snap.json*",
                "*--- snap.json (recorded)*",
                "*+++ snap.json (actual)*",
                '*-    "toggle.on"*',
                '*+    "toggle.off"*',
            ]
        )
        # the file was NOT rewritten by a plain run
        assert (xsm_pytester.path / "snap.json").read_text("utf-8") == recorded

    def test_corrupt_snapshot_file_is_reported(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                def test_it(xsm_interp, xsm_snapshot):
                    xsm_snapshot(xsm_interp, "snap.json")
                """))
        (xsm_pytester.path / "snap.json").write_text("{not json", "utf-8")
        result = run(xsm_pytester)
        result.assert_outcomes(failed=1)
        result.stdout.fnmatch_lines(["*snapshot file is not valid JSON*"])

    def test_normalize_keeps_only_behavioural_keys(self) -> None:
        blob = json.dumps(
            {
                "version": 4,
                "machine_hash": "abc",
                "taken_at": 1.0,
                "deadlines": [{"due_at_wall": 9.9}],
                "state_ids": ["m.a"],
                "value": "a",
                "context": {"k": 1},
                "status": "running",
                "pending_events": [],
            }
        )
        assert normalize_snapshot(blob) == {
            "state_ids": ["m.a"],
            "value": "a",
            "context": {"k": 1},
            "status": "running",
        }
        assert issubclass(SnapshotMismatchError, AssertionError)


# =============================================================================
# Plugin plumbing: options, no-op without the marker, opt-out, markers
# =============================================================================
class TestPlumbing:
    def test_xsm_version_prints_and_exits_zero(self, xsm_pytester) -> None:
        from src.xstate_statemachine import __version__

        result = run(xsm_pytester, "--xsm-version")
        assert result.ret == 0
        result.stdout.fnmatch_lines([f"xstate-statemachine {__version__}"])

    def test_no_marker_means_nothing_happens(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile("""
            def test_plain():
                assert 1 + 1 == 2

            def test_fixture_names_are_prefixed(request):
                names = request.session._fixturemanager._arg2fixturedefs
                assert "xsm_interp" in names and "interp" not in names
                assert "machine" not in names and "clock" not in names
            """)
        run(xsm_pytester).assert_outcomes(passed=2)

    def test_fixture_without_marker_fails_with_a_hint(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile("""
            def test_it(xsm_interp):
                pass
            """)
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(
            ["*the xsm_interp fixture needs an @pytest.mark.xstate_machine*"]
        )

    def test_opt_out_removes_the_plugin(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(f"""
            def test_it(request):
                pm = request.config.pluginmanager
                assert not pm.has_plugin("xstate_statemachine")
                assert pm.get_plugin({PLUGIN!r}) is None
                assert not any(
                    getattr(p, "__name__", "") == {PLUGIN!r}
                    for p in pm.get_plugins()
                )
                assert "xsm_interp" not in (
                    request.session._fixturemanager._arg2fixturedefs
                )
            """)
        result = xsm_pytester.runpytest_inprocess(
            *NO_DJANGO, "-p", "no:xstate_statemachine", "-q"
        )
        result.assert_outcomes(passed=1)

    def test_markers_are_registered_for_strict_markers(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_module("""
                @pytest.mark.xstate_machine(CFG)
                @pytest.mark.xstate_guards_false("ok")
                def test_it(xsm_machine):
                    pass
                """))
        run(xsm_pytester, "--strict-markers").assert_outcomes(passed=1)
        result = run(xsm_pytester, "--markers")
        result.stdout.fnmatch_lines(
            ["*xstate_machine(source, *", "*xstate_guards_false(*names)*"]
        )

    def test_plugin_imports_only_pytest_and_core(self) -> None:
        """The entry point loads in core-only installs: no hypothesis, no
        contrib.pydantic, nothing else third-party, at import time."""
        import ast
        import pathlib

        src = pathlib.Path(
            sys.modules[
                "src.xstate_statemachine.contrib.testing.pytest_plugin"
            ].__file__
        ).read_text(encoding="utf-8")
        roots = set()
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Import):
                roots.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                roots.add((node.module or "").split(".")[0])
        stdlib = {"difflib", "importlib", "json", "pathlib", "typing", "sys"}
        # 📝 pytest-asyncio lives in `_async_fixtures`, registered from
        #    `pytest_configure` only when the asyncio plugin is active.
        assert roots - stdlib - {"__future__"} == {"pytest"}
