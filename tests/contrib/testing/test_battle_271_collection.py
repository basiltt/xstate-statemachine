"""Battle test #271 (B): pytest collection of ``model_test`` classes.

Each scenario is a throw-away ``pytester`` session, because collection is
only honest when pytest itself does it:

* a module-level ``TestX = model_test(...)`` runs exactly ONCE (pytest's
  own ``Test*`` class rule must not collect it a second time);
* two model tests in one module, ``-k`` selection, a model test nested in
  a test class (collected too);
* ``--hypothesis-seed`` reproduces the same minimal artefact;
  ``--hypothesis-show-statistics`` works; ``-p no:hypothesis`` still runs;
* hypothesis absent → ``MissingExtraError`` naming ``[testing]`` at
  collection, reported as one collection error, not an internal error;
* ``--xsm-failing-dir``: relative paths resolve against the invocation
  dir, missing directories are created, paths outside rootdir work.
"""

from __future__ import annotations

import json
import pathlib
import textwrap

import pytest

pytest.importorskip("hypothesis")

from .conftest import run  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
REFUND = HERE / "examples" / "refund.json"

HEADER = """
import pathlib
from hypothesis import settings
from xstate_statemachine.contrib.testing import model_test

HERE = pathlib.Path(__file__).parent
S = settings(max_examples=100, database=None, derandomize=True)
NEG = {"neg": lambda i: i.context["total"] >= 0}
"""


def _setup(pytester: pytest.Pytester, body: str, name: str = "test_m"):
    (pytester.path / "refund.json").write_text(
        REFUND.read_text("utf-8"), "utf-8"
    )
    pytester.makepyfile(
        **{name: textwrap.dedent(HEADER) + textwrap.dedent(body)}
    )


# =============================================================================
# collected once, by name
# =============================================================================
def test_module_level_model_test_runs_exactly_once(xsm_pytester) -> None:
    _setup(
        xsm_pytester,
        """
        TestGood = model_test(HERE / "refund.json", settings=S)
        """,
    )
    result = run(xsm_pytester)
    result.assert_outcomes(passed=1)  # not 2: no second plain-class run
    assert "PytestCollectionWarning" not in result.stdout.str()


def test_two_model_tests_and_k_selection(xsm_pytester, tmp_path) -> None:
    _setup(
        xsm_pytester,
        """
        TestGood = model_test(HERE / "refund.json", settings=S)
        TestBad = model_test(
            HERE / "refund.json", invariants=NEG, settings=S
        )
        """,
    )
    out = tmp_path / "o"
    run(xsm_pytester, f"--xsm-failing-dir={out}").assert_outcomes(
        passed=1, failed=1
    )
    run(
        xsm_pytester, "-k", "Good", f"--xsm-failing-dir={out}"
    ).assert_outcomes(passed=1, deselected=1)


def test_model_test_nested_in_a_class_is_collected(xsm_pytester) -> None:
    _setup(
        xsm_pytester,
        """
        class TestOuter:
            TestInner = model_test(HERE / "refund.json", settings=S)

            def test_plain(self):
                assert True
        """,
    )
    run(xsm_pytester).assert_outcomes(passed=2)


# =============================================================================
# hypothesis options
# =============================================================================
def test_seed_reproduces_the_same_artefact(xsm_pytester, tmp_path) -> None:
    _setup(
        xsm_pytester,
        """
        TestBad = model_test(
            HERE / "refund.json",
            invariants=NEG,
            settings=settings(max_examples=200, database=None),
        )
        """,
    )
    blobs = []
    for n in range(2):
        out = tmp_path / str(n)
        run(
            xsm_pytester, "--hypothesis-seed=1234", f"--xsm-failing-dir={out}"
        ).assert_outcomes(failed=1)
        blobs.append(json.loads((out / "failing.json").read_text("utf-8")))
    assert blobs[0] == blobs[1]
    assert [c["send"] for c in blobs[0]] == ["ADD", "PAY", "REFUND"] + [
        "REFUND"
    ]


def test_show_statistics_and_no_hypothesis_plugin(xsm_pytester) -> None:
    _setup(
        xsm_pytester,
        """
        TestGood = model_test(HERE / "refund.json", settings=S)
        """,
    )
    result = run(xsm_pytester, "--hypothesis-show-statistics")
    result.assert_outcomes(passed=1)
    result.stdout.fnmatch_lines(["*Hypothesis Statistics*"])
    run(xsm_pytester, "-p", "no:hypothesispytest").assert_outcomes(passed=1)


def test_hypothesis_missing_is_one_collection_error(xsm_pytester) -> None:
    xsm_pytester.makeconftest("""
        import sys
        for k in [m for m in sys.modules if m.split(".")[0] == "hypothesis"]:
            sys.modules.pop(k)
        sys.modules["hypothesis"] = None
        # 📝 hypothesis <= 6.10x's pytest plugin (the compat floor) wraps
        #    `FixtureFunctionMarker.__call__` and tests `"hypothesis" in
        #    sys.modules` -- TRUE for our None sentinel -- then imports
        #    `hypothesis.internal` and dies. Restore the original so the
        #    simulated absence is the only thing under test.
        try:
            import _hypothesis_pytestplugin as _hp
            from _pytest import fixtures as _fx
            if getattr(_hp, "_orig_call", None) is not None:
                _fx.FixtureFunctionMarker.__call__ = _hp._orig_call
        except Exception:
            pass
        """)
    _setup(
        xsm_pytester,
        """
        TestGood = model_test(HERE / "refund.json")
        """.replace("from hypothesis import settings\n", ""),
    )
    (xsm_pytester.path / "test_m.py").write_text(
        textwrap.dedent("""
        import pathlib
        from xstate_statemachine.contrib.testing import model_test

        TestGood = model_test(pathlib.Path(__file__).parent / "refund.json")
        """),
        "utf-8",
    )
    xsm_pytester.makepyfile(test_other="def test_ok():\n    assert True\n")
    result = run(xsm_pytester, "-p", "no:hypothesispytest")
    # 📝 pytest's own rule: a collection error interrupts the session.
    result.assert_outcomes(errors=1)
    result.stdout.fnmatch_lines(["*MissingExtraError*[[]testing[]]*"])


# =============================================================================
# --xsm-failing-dir
# =============================================================================
def test_failing_dir_relative_and_created(xsm_pytester) -> None:
    _setup(
        xsm_pytester,
        """
        TestBad = model_test(
            HERE / "refund.json", invariants=NEG, settings=S
        )
        """,
    )
    run(xsm_pytester, "--xsm-failing-dir=a/b/c").assert_outcomes(failed=1)
    assert (xsm_pytester.path / "a" / "b" / "c" / "failing.json").is_file()
    assert not (xsm_pytester.path / "failing.json").exists()


def test_failing_dir_outside_rootdir(xsm_pytester, tmp_path) -> None:
    _setup(
        xsm_pytester,
        """
        TestBad = model_test(
            HERE / "refund.json", invariants=NEG, settings=S
        )
        """,
    )
    out = tmp_path.parent / (tmp_path.name + "_outside")
    run(xsm_pytester, f"--xsm-failing-dir={out}").assert_outcomes(failed=1)
    assert (out / "failing.json").is_file()


def test_default_artefact_is_next_to_the_module(xsm_pytester) -> None:
    _setup(
        xsm_pytester,
        """
        TestBad = model_test(
            HERE / "refund.json", invariants=NEG, settings=S
        )
        """,
    )
    run(xsm_pytester).assert_outcomes(failed=1)
    assert (xsm_pytester.path / "failing.json").is_file()


# =============================================================================
# the shipped demo stays out of directory runs and the repo tree
# =============================================================================
def test_shipped_demo_is_not_collected_by_a_directory_run(
    xsm_pytester,
) -> None:
    ex = xsm_pytester.mkdir("examples")
    for f in ("conftest.py", "refund.json", "test_refund_bug.py"):
        (ex / f).write_text((HERE / "examples" / f).read_text("utf-8"))
    result = run(xsm_pytester, "--collect-only")
    assert "TestRefund" not in result.stdout.str()
