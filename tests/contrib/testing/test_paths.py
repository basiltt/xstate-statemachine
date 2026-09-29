"""The `xsm_path` fixture of the `[testing]` plugin (#269), exercised
through throw-away `pytester` sessions."""

from __future__ import annotations

import json
import textwrap

from .conftest import CORPUS, run

PAYMENT = (CORPUS / "AdvancePayment.json").as_posix()

TOGGLE = {
    "id": "toggle",
    "initial": "off",
    "states": {
        "off": {"on": {"TOGGLE": "on"}},
        "on": {"on": {"TOGGLE": "off", "RESET": "off"}},
    },
}


TRIANGLE = {
    "id": "tri",
    "initial": "off",
    "states": {
        "off": {"on": {"GO": "on", "SKIP": "mid"}},
        "on": {"on": {"GO": "mid"}},
        "mid": {"on": {"BACK": "on"}},
    },
}


def _mod(body: str) -> str:
    return "import pytest\n" + textwrap.dedent(body)


# =============================================================================
# xsm_path
# =============================================================================
class TestPathFixture:
    def test_one_case_per_configuration_with_readable_ids(
        self, xsm_pytester
    ) -> None:
        from xstate_statemachine import create_machine
        from xstate_statemachine.graph import shortest_paths

        cfg = json.loads((CORPUS / "AdvancePayment.json").read_text("utf-8"))
        from xstate_statemachine.testing_utils import stub_logic

        m = create_machine(cfg, logic=stub_logic(cfg))
        expected = len(shortest_paths(m))
        xsm_pytester.makepyfile(_mod(f"""
                @pytest.mark.xstate_machine({PAYMENT!r})
                def test_reach(xsm_path, xsm_interp, xsm_clock):
                    xsm_path.replay(xsm_interp, xsm_clock)
                    assert xsm_interp.current_state_ids == set(
                        xsm_path.final_states)
                """))
        result = run(xsm_pytester, "-vv")
        result.assert_outcomes(passed=expected)
        result.stdout.fnmatch_lines(["*test_reach?path?editing->challenge?*"])

    def test_guards_both_adds_the_forced_false_configurations(
        self, xsm_pytester
    ) -> None:
        xsm_pytester.makepyfile(_mod(f"""
                @pytest.mark.xstate_machine({PAYMENT!r})
                def test_reach(xsm_path, xsm_interp, xsm_clock):
                    xsm_path.replay(xsm_interp, xsm_clock)
                    assert xsm_interp.current_state_ids == set(
                        xsm_path.final_states)
                """))
        result = run(xsm_pytester, "-vv", "--xsm-path-guards=both")
        result.assert_outcomes(passed=4)
        result.stdout.fnmatch_lines(["*failure*PASSED*"])

    def test_full_paths_uses_simple_paths_and_caps(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_mod(f"""
                CFG = {TRIANGLE!r}
                @pytest.mark.xstate_machine(CFG)
                def test_p(xsm_path, xsm_interp, xsm_clock):
                    xsm_path.replay(xsm_interp, xsm_clock)
                    assert xsm_interp.current_state_ids == set(
                        xsm_path.final_states)
                """))
        # shortest: 3 configurations
        run(xsm_pytester).assert_outcomes(passed=3)
        # simple: off->on, off->on->mid, off->mid, off->mid->on
        run(xsm_pytester, "--xsm-full-paths").assert_outcomes(passed=4)
        run(
            xsm_pytester, "--xsm-full-paths", "--xsm-max-paths=2"
        ).assert_outcomes(passed=2)
        run(
            xsm_pytester, "--xsm-full-paths", "--xsm-max-depth=1"
        ).assert_outcomes(passed=2)

    def test_path_without_marker_fails_loudly(self, xsm_pytester) -> None:
        xsm_pytester.makepyfile(_mod("""
                def test_p(xsm_path):
                    pass
                """))
        result = run(xsm_pytester)
        result.assert_outcomes(errors=1)
        result.stdout.fnmatch_lines(["*xsm_path fixture needs*marker*"])
