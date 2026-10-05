"""#269 battle (adversary B): the `xsm_path` fixture as a real user drives
it -- option combinations, ids, determinism, failure reporting, real
logic left intact after `replay`, and exploration shared across tests."""

from __future__ import annotations

import textwrap

from .conftest import run

TRI = {
    "id": "m",
    "initial": "a",
    "context": {},
    "states": {
        "a": {"on": {"GO": [{"target": "b", "guard": "ok"}, {"target": "c"}]}},
        "b": {"on": {"GO": "c"}},
        "c": {},
    },
}
BAD = {"id": "bad", "initial": "nope", "states": {"a": {}}}


def _mod(body: str) -> str:
    return "import pytest\n" + textwrap.dedent(body)


REACH = """
    @pytest.mark.xstate_machine({cfg!r})
    def test_p(xsm_path, xsm_interp, xsm_clock):
        xsm_path.replay(xsm_interp, xsm_clock)
        assert xsm_interp.current_state_ids == set(xsm_path.final_states)
    """


def _ids(result) -> list:
    return [
        line.split("::", 1)[1].split(" ", 1)[0]
        for line in result.outlines
        if "::test_" in line and ("PASSED" in line or "FAILED" in line)
    ]


class TestOptions:
    def test_ids_and_count_per_option(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_mod(REACH.format(cfg=TRI)))
        r = run(xsm_pytester, "-vv")
        r.assert_outcomes(passed=3)
        assert _ids(r) == [
            "test_p[path[a]]",
            "test_p[path[a->b]]",
            "test_p[path[a->b->c]]",
        ]
        # `both`: c is now one step away (guard `ok` forced False)
        r = run(xsm_pytester, "-vv", "--xsm-path-guards", "both")
        r.assert_outcomes(passed=3)
        assert _ids(r)[-1] == "test_p[path[a->c]]"
        r = run(xsm_pytester, "-vv", "--xsm-max-depth", "0")
        r.assert_outcomes(passed=1)
        r = run(
            xsm_pytester,
            "--xsm-full-paths",
            "--xsm-max-paths",
            "5",
            "--xsm-path-guards",
            "both",
        )
        r.assert_outcomes(passed=3)  # a->b, a->b->c, a->c

    def test_order_is_deterministic(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_mod(REACH.format(cfg=TRI)))
        args = ("-vv", "--xsm-path-guards", "both")
        assert _ids(run(xsm_pytester, *args)) == _ids(run(xsm_pytester, *args))

    def test_negative_bound_is_a_usage_error(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_mod(REACH.format(cfg=TRI)))
        r = run(xsm_pytester, "--xsm-max-depth", "-1")
        assert r.ret != 0
        r.stderr.fnmatch_lines(["*must be >= 0*"])

    def test_node_id_selection_with_arrows(self, xsm_pytester) -> None:
        path = xsm_pytester.makepyfile(_mod(REACH.format(cfg=TRI)))
        r = run(xsm_pytester, f"{path.name}::test_p[path[a->b]]")
        r.assert_outcomes(passed=1)


class TestFailures:
    def test_machine_that_cannot_start_is_one_error_per_test(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_mod(f"""
                @pytest.mark.xstate_machine({BAD!r})
                def test_bad(xsm_path):
                    pass

                def test_other():
                    pass
                """))
        r = run(xsm_pytester)
        # 📝 Used to be "Interrupted: 1 error during collection" -- the
        #    whole session died, `test_other` never ran.
        r.assert_outcomes(passed=1, errors=1)
        r.stdout.fnmatch_lines(
            ["*cannot generate xsm_path cases*does not start*nope*"]
        )
        assert "Traceback" not in r.stdout.str()


class TestRealLogic:
    def test_replay_restores_the_users_guard(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(
            logicmod="""
                from xstate_statemachine import MachineLogic
                def ok(c, e):
                    return True
                def make():
                    return MachineLogic(guards={"ok": ok})
                """,
            test_real=_mod(f"""
                import logicmod
                @pytest.mark.xstate_machine({TRI!r}, logic="logicmod:make")
                def test_p(xsm_path, xsm_interp, xsm_clock):
                    xsm_path.replay(xsm_interp, xsm_clock)
                    # a `guard:ok=False` step must not leak the stub
                    assert xsm_interp.machine.logic.guards["ok"] is logicmod.ok
                    assert xsm_interp.current_state_ids == set(
                        xsm_path.final_states)
                """),
        )
        xsm_pytester.syspathinsert()
        run(xsm_pytester, "--xsm-path-guards", "both").assert_outcomes(
            passed=3
        )


class TestSharedExploration:
    def test_two_functions_one_machine_explore_once(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makeconftest("""
            import xstate_statemachine.contrib.testing._paths as P
            CALLS = []
            _orig = P._explore
            def _spy(machine, config):
                CALLS.append(machine.id)
                return _orig(machine, config)
            P._explore = _spy
            def pytest_sessionfinish(session):
                print(f"\\nEXPLORED={len(CALLS)}")
                P._explore = _orig
            """)
        xsm_pytester.makepyfile(_mod(f"""
                CFG = {TRI!r}
                @pytest.mark.xstate_machine(CFG)
                def test_one(xsm_path):
                    pass
                @pytest.mark.xstate_machine(CFG)
                def test_two(xsm_path):
                    pass
                @pytest.mark.xstate_machine(dict(CFG, id="other"))
                def test_three(xsm_path):
                    pass
                """))
        r = run(xsm_pytester, "-s")
        r.assert_outcomes(passed=9)
        r.stdout.fnmatch_lines(["*EXPLORED=2*"])
