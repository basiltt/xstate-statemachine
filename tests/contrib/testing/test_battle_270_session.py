# tests/contrib/testing/test_battle_270_session.py
"""#270 battle (adversary B): the `--xsm-coverage` pytest session.

Options, report specs, exit codes, xdist, and X0 (escaping / no context
leak) -- each a `pytester` session on a tiny inline chart.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import textwrap
from typing import Any

import pytest

from .conftest import run

HAS_XDIST = importlib.util.find_spec("xdist") is not None
pytestmark = pytest.mark.timeout(300)

CHART = {
    "id": "toggle",
    "initial": "off",
    "context": {"secret": "S3CR3T-TOKEN-270"},
    "states": {"off": {"on": {"T": "on"}}, "on": {"on": {"T": "off"}}},
}

BODY = """
import pytest
from xstate_statemachine import create_machine, SyncInterpreter

CHART = {chart!r}

def test_toggle():
    i = SyncInterpreter(create_machine(CHART)).start()
    i.send("T")
    i.stop()
"""


def _suite(pytester: Any, chart: Any = None, extra: str = "") -> None:
    src = BODY.format(chart=chart or CHART) + textwrap.dedent(extra)
    pytester.makepyfile(test_suite=src)


def _clean(r: Any) -> None:
    text = r.stdout.str() + r.stderr.str()
    assert "Traceback" not in text and "INTERNALERROR" not in text, text


# -----------------------------------------------------------------------------
# 1. options
# -----------------------------------------------------------------------------
class TestOptions:
    def test_all_three_reports_and_duplicates_once(
        self, xsm_pytester: Any
    ) -> None:
        _suite(xsm_pytester)
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=term",
            "--xsm-coverage-report=term",
            "--xsm-coverage-report=json:a.json",
            "--xsm-coverage-report=json:a.json",
            "--xsm-coverage-report=html:a.html",
        )
        assert r.ret == 0
        out = r.stdout.str()
        assert out.count("xstate coverage written to") == 2
        assert out.count("toggle") >= 1
        assert (xsm_pytester.path / "a.json").is_file()
        assert (xsm_pytester.path / "a.html").is_file()

    def test_default_filenames(self, xsm_pytester: Any) -> None:
        _suite(xsm_pytester)
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=json",
            "--xsm-coverage-report=html",
        )
        assert r.ret == 0
        assert (xsm_pytester.path / "xsm-coverage.json").is_file()
        assert (xsm_pytester.path / "xsm-coverage.html").is_file()

    @pytest.mark.parametrize("dest", ["adir", "afile/sub.json"])
    def test_unwritable_path_is_one_line_and_fails(
        self, xsm_pytester: Any, dest: str
    ) -> None:
        _suite(xsm_pytester)
        (xsm_pytester.path / "adir").mkdir()
        (xsm_pytester.path / "afile").write_text("x")
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            f"--xsm-coverage-report=json:{dest}",
        )
        _clean(r)
        assert r.ret == pytest.ExitCode.TESTS_FAILED
        assert "cannot write json report" in r.stdout.str()

    def test_report_written_when_session_fails(
        self, xsm_pytester: Any
    ) -> None:
        _suite(xsm_pytester, extra="\ndef test_bad():\n    assert 0\n")
        r = run(xsm_pytester, "--xsm-coverage", "--xsm-coverage-report=json")
        assert r.ret == pytest.ExitCode.TESTS_FAILED
        assert (xsm_pytester.path / "xsm-coverage.json").is_file()

    @pytest.mark.parametrize(
        "opt",
        [
            "--xsm-fail-under-state-coverage=90",
            "--xsm-fail-under-transition-coverage=90",
            "--xsm-coverage-report=json",
        ],
    )
    def test_orphan_option_without_coverage_is_usage_error(
        self, xsm_pytester: Any, opt: str
    ) -> None:
        _suite(xsm_pytester)
        r = run(xsm_pytester, opt)
        assert r.ret == pytest.ExitCode.USAGE_ERROR
        assert "requires --xsm-coverage" in r.stderr.str()

    def test_nothing_observed_fails_a_set_gate(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile("def test_x():\n    pass\n")
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-state-coverage=100",
        )
        assert r.ret == pytest.ExitCode.TESTS_FAILED
        assert "no machines were observed" in r.stdout.str()

    def test_nothing_observed_without_gate_passes(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile("def test_x():\n    pass\n")
        r = run(xsm_pytester, "--xsm-coverage")
        assert r.ret == 0
        assert "no machines observed" in r.stdout.str()

    def test_plugin_disabled_is_argparse_error(
        self, xsm_pytester: Any
    ) -> None:
        _suite(xsm_pytester)
        r = xsm_pytester.runpytest_subprocess(
            "-p", "no:xstate_statemachine", "--xsm-coverage"
        )
        assert r.ret == pytest.ExitCode.USAGE_ERROR
        assert "Traceback" not in r.stderr.str()


# -----------------------------------------------------------------------------
# 2. exit codes
# -----------------------------------------------------------------------------
class TestExitCodes:
    def test_fail_line_printed_even_when_tests_failed(
        self, xsm_pytester: Any
    ) -> None:
        _suite(xsm_pytester, extra="\ndef test_bad():\n    assert 0\n")
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-fail-under-transition-coverage=100",
        )
        assert r.ret == pytest.ExitCode.TESTS_FAILED
        assert "FAIL xstate coverage" in r.stdout.str()

    def test_x_stop_marks_coverage_partial(self, xsm_pytester: Any) -> None:
        _suite(
            xsm_pytester,
            extra="\ndef test_a_bad():\n    assert 0\n"
            "def test_z():\n    pass\n",
        )
        r = run(xsm_pytester, "--xsm-coverage", "-x", "-p", "no:randomly")
        assert "coverage partial" in r.stdout.str()

    def test_full_run_not_marked_partial(self, xsm_pytester: Any) -> None:
        _suite(xsm_pytester)
        r = run(xsm_pytester, "--xsm-coverage")
        assert "coverage partial" not in r.stdout.str()

    def test_collect_only_writes_and_gates_nothing(
        self, xsm_pytester: Any
    ) -> None:
        _suite(xsm_pytester)
        r = run(
            xsm_pytester,
            "--collect-only",
            "--xsm-coverage",
            "--xsm-coverage-report=json",
            "--xsm-fail-under-state-coverage=100",
        )
        assert r.ret == 0
        assert not (xsm_pytester.path / "xsm-coverage.json").exists()

    def test_k_nothing_matches_fails_loudly(self, xsm_pytester: Any) -> None:
        _suite(xsm_pytester)
        r = run(
            xsm_pytester,
            "-k",
            "nothing_matches",
            "--xsm-coverage",
            "--xsm-fail-under-state-coverage=100",
        )
        assert r.ret != 0
        assert "no machines were observed" in r.stdout.str()


# -----------------------------------------------------------------------------
# 3. xdist
# -----------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_XDIST, reason="pytest-xdist not installed")
class TestXdist:
    def _sub(self, pytester: Any, *args: str) -> Any:
        from .conftest import PLUGIN_ARGS

        return pytester.runpytest_subprocess(*PLUGIN_ARGS, *args)

    def test_loadfile_json_written_once(self, xsm_pytester: Any) -> None:
        _suite(xsm_pytester)
        xsm_pytester.makepyfile(
            test_other=BODY.format(chart=CHART).replace(
                "test_toggle", "test_toggle2"
            )
        )
        r = self._sub(
            xsm_pytester,
            "-n",
            "2",
            "--dist",
            "loadfile",
            "--xsm-coverage",
            "--xsm-coverage-report=json:cov.json",
        )
        assert r.ret == 0, r.stdout.str()
        assert r.stdout.str().count("xstate coverage written to") == 1
        files = sorted(p.name for p in xsm_pytester.path.glob("*.json"))
        assert files == ["cov.json"]
        doc = json.loads((xsm_pytester.path / "cov.json").read_text("utf-8"))
        assert doc["machines"][0]["states"]["percent"] == 100

    def test_n0_works(self, xsm_pytester: Any) -> None:
        _suite(xsm_pytester)
        r = self._sub(xsm_pytester, "-n", "0", "--xsm-coverage")
        assert r.ret == 0

    def test_crashed_worker_warns_and_gate_judges(
        self, xsm_pytester: Any
    ) -> None:
        _suite(
            xsm_pytester,
            extra="\ndef test_crash():\n    import os\n    os._exit(3)\n",
        )
        r = self._sub(
            xsm_pytester,
            "-n",
            "2",
            "--xsm-coverage",
            "--xsm-fail-under-state-coverage=100",
        )
        assert r.ret != 0
        out = r.stdout.str()
        assert "INTERNALERROR" not in out
        assert "crashed" in out  # xdist's own report of the dead worker
        assert "FAIL xstate coverage" in out or "coverage data was lost" in (
            out + r.stderr.str()
        )

    def test_no_xdist_plugin_is_fine(self, xsm_pytester: Any) -> None:
        _suite(xsm_pytester)
        r = run(xsm_pytester, "-p", "no:xdist", "--xsm-coverage")
        assert r.ret == 0
        _clean(r)


# -----------------------------------------------------------------------------
# 7. security / X0
# -----------------------------------------------------------------------------
class TestX0:
    def test_html_escapes_and_no_context_leak(self, xsm_pytester: Any) -> None:
        evil = "<img src=x onerror=alert(1)>"
        chart = {
            "id": "evil",
            "initial": "off",
            "context": {"secret": "S3CR3T-TOKEN-270"},
            "states": {
                "off": {"on": {"T": "on", "<b>EV</b>": evil}},
                "on": {},
                evil: {},
            },
        }
        _suite(xsm_pytester, chart=chart)
        r = run(
            xsm_pytester,
            "--xsm-coverage",
            "--xsm-coverage-report=json:c.json",
            "--xsm-coverage-report=html:c.html",
        )
        assert r.ret == 0, r.stdout.str()
        html = (xsm_pytester.path / "c.html").read_text("utf-8")
        assert "<img" not in html and "<b>EV" not in html
        assert "&lt;img" in html and "&lt;b&gt;EV" in html
        js = (xsm_pytester.path / "c.json").read_text("utf-8")
        for text in (html, js, r.stdout.str()):
            assert "S3CR3T-TOKEN-270" not in text
