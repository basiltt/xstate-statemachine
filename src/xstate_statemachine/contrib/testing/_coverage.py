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
from typing import Any, Dict, List, Optional, Tuple

import pytest

from ... import plugins
from ...coverage import (
    CoverageCollector,
    CoverageReport,
    below,
    reports_from_json,
    reports_to_html,
    reports_to_json,
    reports_to_text,
)

__all__ = ["add_coverage_options", "CoverageSession", "merge_reports"]

_KEY = "_xsm_coverage_session"
_PLUGIN = "xsm-coverage-session"
#: ``workeroutput`` key a pytest-xdist worker ships its reports under.
_WORKER_KEY = "xsm_coverage"
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
        # 📝 pytest-xdist: reports shipped back by each worker; folded
        #    into the controller's own at `finish` (battle #268).
        self.worker_reports: List[CoverageReport] = []
        self.is_worker = hasattr(config, "workerinput")

    # ------------------------------------------------------------ lifecycle
    @classmethod
    def configure(cls, config: Any) -> None:
        if not config.getoption("--xsm-coverage", default=False):
            return
        session = cls(config)
        setattr(config, _KEY, session)
        plugins.register_global(session.collector)
        config.pluginmanager.register(session, _PLUGIN)

    @staticmethod
    def get(config: Any) -> Optional["CoverageSession"]:
        return getattr(config, _KEY, None)

    @classmethod
    def unconfigure(cls, config: Any) -> None:
        session = cls.get(config)
        if session is not None:
            plugins.unregister_global(session.collector)
            if config.pluginmanager.get_plugin(_PLUGIN) is session:
                config.pluginmanager.unregister(session, _PLUGIN)
            delattr(config, _KEY)

    # ------------------------------------------------------------ xdist
    @pytest.hookimpl(optionalhook=True)
    def pytest_testnodedown(self, node: Any, error: Any) -> None:
        """Controller side of pytest-xdist: collect a worker's reports."""
        text = getattr(node, "workeroutput", {}).get(_WORKER_KEY)
        if text:
            self.worker_reports.extend(reports_from_json(text))

    def merged_reports(self) -> List[CoverageReport]:
        """This process's reports merged with every worker's, by key."""
        return merge_reports(
            list(self.collector.reports()) + self.worker_reports
        )

    # ------------------------------------------------------------ outputs
    def _resolve(self, path: pathlib.Path) -> pathlib.Path:
        if path.is_absolute():
            return path
        return pathlib.Path(str(self.config.invocation_params.dir)) / path

    def finish(self, session: Any) -> None:
        """``pytest_sessionfinish``: write files, apply the thresholds.

        📝 On a pytest-xdist worker this only ships the raw reports to the
        controller (``workeroutput``); files, summary and the gate are
        the controller's, over the merged suite.
        """
        if self.is_worker:
            self.config.workeroutput[_WORKER_KEY] = reports_to_json(
                self.collector.reports()
            )
            return
        reports = self.merged_reports()
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
        if self.is_worker:
            return
        reports: List[CoverageReport] = self.merged_reports()
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


def merge_reports(reports: List[CoverageReport]) -> List[CoverageReport]:
    """Union several processes' reports of the same machines (by ``key``).

    A state/transition is covered if ANY process covered it, so the merged
    ``unvisited`` / ``unhit`` are the intersections. Sorted by key.
    """
    by_key: Dict[str, CoverageReport] = {}
    for r in reports:
        prev = by_key.get(r.key)
        if prev is None:
            by_key[r.key] = r
            continue
        unvisited = tuple(sorted(set(prev.unvisited) & set(r.unvisited)))
        unhit = tuple(sorted(set(prev.unhit) & set(r.unhit)))
        by_key[r.key] = CoverageReport(
            machine_id=r.machine_id,
            key=r.key,
            states_visited=r.states_total - len(unvisited),
            states_total=r.states_total,
            unvisited=unvisited,
            transitions_hit=r.transitions_total - len(unhit),
            transitions_total=r.transitions_total,
            unhit=unhit,
        )
    return [by_key[k] for k in sorted(by_key)]
