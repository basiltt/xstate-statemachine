# src/xstate_statemachine/contrib/testing/_coverage.py
# -----------------------------------------------------------------------------
# 📊 `--xsm-coverage`: a session-wide state & transition coverage run (#270)
# -----------------------------------------------------------------------------
# 🏛️ One `CoverageCollector` for the whole session, registered with core's
#    `plugins.register_global` at `pytest_configure` and unregistered at
#    `pytest_unconfigure`. Every interpreter built in between -- by the
#    `xsm_*` fixtures, by a test's own `SyncInterpreter(...)`, by
#    `from_snapshot`, by a spawned child -- attaches it at construction, so
#    the numbers cover the suite, not just the fixture users.
#
# 📝 Without `--xsm-coverage` nothing here runs: no global plugin, no
#    report, no summary section.
# -----------------------------------------------------------------------------
"""Session coverage for the pytest plugin."""

from __future__ import annotations

import pathlib
from typing import Any, List, Optional, Tuple

import pytest

from ... import plugins
from ...coverage import (
    CoverageCollector,
    CoverageReport,
    below,
    reports_to_html,
    reports_to_json,
    reports_to_text,
)

__all__ = ["add_coverage_options", "CoverageSession"]

_KEY = "_xsm_coverage_session"
_DEFAULT_FILES = {"json": "xsm-coverage.json", "html": "xsm-coverage.html"}


def add_coverage_options(group: Any) -> None:
    group.addoption(
        "--xsm-coverage",
        action="store_true",
        default=False,
        help="record statechart state & transition coverage for every "
        "interpreter built during the session",
    )
    group.addoption(
        "--xsm-coverage-report",
        action="append",
        default=[],
        metavar="term|json[:PATH]|html[:PATH]",
        help="coverage report(s) to produce (repeatable; default: term)",
    )
    group.addoption(
        "--xsm-fail-under-state-coverage",
        type=float,
        default=None,
        metavar="N",
        help="fail the session if any machine's state coverage is < N%%",
    )
    group.addoption(
        "--xsm-fail-under-transition-coverage",
        type=float,
        default=None,
        metavar="N",
        help="fail the session if any machine's transition coverage is "
        "< N%%",
    )


def _parse_report(spec: str) -> Tuple[str, Optional[pathlib.Path]]:
    kind, _, dest = spec.partition(":")
    kind = kind.strip().lower()
    if kind not in ("term", "json", "html"):
        raise pytest.UsageError(
            f"--xsm-coverage-report={spec!r}: expected term, json[:PATH] "
            f"or html[:PATH]"
        )
    if kind == "term":
        if dest:
            raise pytest.UsageError("--xsm-coverage-report=term takes no path")
        return kind, None
    return kind, pathlib.Path(dest or _DEFAULT_FILES[kind])


class CoverageSession:
    """The per-session state behind ``--xsm-coverage``."""

    def __init__(self, config: Any) -> None:
        self.config = config
        self.collector = CoverageCollector()
        specs = config.getoption("--xsm-coverage-report") or ["term"]
        self.reports = [_parse_report(s) for s in specs]
        self.fail_state = config.getoption("--xsm-fail-under-state-coverage")
        self.fail_transition = config.getoption(
            "--xsm-fail-under-transition-coverage"
        )
        self.failures: List[str] = []
        self.written: List[pathlib.Path] = []

    # ------------------------------------------------------------ lifecycle
    @classmethod
    def configure(cls, config: Any) -> None:
        if not config.getoption("--xsm-coverage", default=False):
            return
        session = cls(config)
        setattr(config, _KEY, session)
        plugins.register_global(session.collector)

    @staticmethod
    def get(config: Any) -> Optional["CoverageSession"]:
        return getattr(config, _KEY, None)

    @classmethod
    def unconfigure(cls, config: Any) -> None:
        session = cls.get(config)
        if session is not None:
            plugins.unregister_global(session.collector)
            delattr(config, _KEY)

    # ------------------------------------------------------------ outputs
    def _resolve(self, path: pathlib.Path) -> pathlib.Path:
        if path.is_absolute():
            return path
        return pathlib.Path(str(self.config.invocation_params.dir)) / path

    def finish(self, session: Any) -> None:
        """``pytest_sessionfinish``: write files, apply the thresholds."""
        reports = self.collector.reports()
        for kind, dest in self.reports:
            if dest is None:
                continue
            target = self._resolve(dest)
            target.parent.mkdir(parents=True, exist_ok=True)
            render = reports_to_json if kind == "json" else reports_to_html
            target.write_text(render(reports), encoding="utf-8")
            self.written.append(target)
        self.failures = below(
            reports, state=self.fail_state, transition=self.fail_transition
        )
        if self.failures and session.exitstatus == 0:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED

    def summary(self, terminalreporter: Any) -> None:
        reports: List[CoverageReport] = self.collector.reports()
        if any(kind == "term" for kind, _ in self.reports):
            # 📝 The literal `---- xstate coverage ----` header (not a
            #    full-width `write_sep`) so CI log greps are stable.
            text = reports_to_text(reports)
            terminalreporter.write_line("")
            for line in text.splitlines():
                terminalreporter.write_line(line)
        for path in self.written:
            terminalreporter.write_line(f"xstate coverage written to {path}")
        for failure in self.failures:
            terminalreporter.write_line(
                f"FAIL xstate coverage: {failure}", red=True
            )
