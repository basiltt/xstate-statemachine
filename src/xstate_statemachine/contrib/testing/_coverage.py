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

import argparse
import math
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
        type=_percent,
        default=None,
        metavar="N",
        help="fail the session if any machine's state coverage is < N%%",
    )
    group.addoption(
        "--xsm-fail-under-transition-coverage",
        type=_percent,
        default=None,
        metavar="N",
        help="fail the session if any machine's transition coverage is "
        "< N%%",
    )


def _percent(text: str) -> float:
    """A fail-under threshold: a finite number in ``[0, 100]``.

    🛡️ #270 battle: ``type=float`` accepted ``nan`` (every ``percent < nan``
    is False -- the gate silently PASSED at 0 % coverage), ``inf`` and
    ``-1`` / ``101`` (always fail / never fail). Refuse them at the
    command line like `coverage report --fail-under` does.
    """
    try:
        value = float(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"expected a percentage, got {text!r}"
        ) from exc
    if math.isnan(value) or math.isinf(value) or not 0 <= value <= 100:
        raise argparse.ArgumentTypeError(
            f"expected a percentage in [0, 100], got {text!r}"
        )
    return value


_ORPHANS = (
    "--xsm-coverage-report",
    "--xsm-fail-under-state-coverage",
    "--xsm-fail-under-transition-coverage",
)


def _refuse_orphan_options(config: Any) -> None:
    """🛡️ #270 battle B: a fail-under gate without ``--xsm-coverage`` was
    silently ignored -- CI believed it was gated."""
    for name in _ORPHANS:
        value = config.getoption(name, default=None)
        if value not in (None, []):
            raise pytest.UsageError(f"{name} requires --xsm-coverage")


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
        # 📝 #270 battle B: the same report twice is one report (it was
        #    written -- and announced -- twice).
        self.reports: List[Tuple[str, Optional[pathlib.Path]]] = []
        for spec in specs:
            parsed = _parse_report(spec)
            if parsed not in self.reports:
                self.reports.append(parsed)
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
        self.notes: List[str] = []

    # ------------------------------------------------------------ lifecycle
    @classmethod
    def configure(cls, config: Any) -> None:
        if not config.getoption("--xsm-coverage", default=False):
            _refuse_orphan_options(config)
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
        elif error is not None:
            # 📝 reviewer M3 (#268 battle): a worker that crashed never
            #    set `workeroutput`, so its coverage silently vanished and
            #    the gate judged partial data. Say so (the gate fails
            #    closed on the missing rows, but the operator must know
            #    WHY).
            import warnings

            warnings.warn(
                f"xsm coverage: worker {getattr(node, 'gateway', node)} "
                f"ended with an error ({error}); its coverage data was "
                f"lost and the gate judges the remaining workers only.",
                RuntimeWarning,
                stacklevel=2,
            )

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
        if self.config.getoption("collectonly", default=False):
            # 📝 #270 battle B: nothing ran, so there is nothing to
            #    report or gate (`--collect-only` must not fail).
            return
        reports = self.merged_reports()
        self.failures = below(
            reports, state=self.fail_state, transition=self.fail_transition
        )
        for kind, dest in self.reports:
            if dest is not None:
                self._write(kind, dest, reports)
        gated = self.fail_state is not None or self.fail_transition is not None
        if gated and not reports:
            # 🛡️ #270 battle B: a typo'd marker / `-k` that matched nothing
            #    built no machine; "0 machines below N%" must not PASS.
            self.failures.append(
                "no machines were observed, so the fail-under gate has "
                "nothing to judge (did any test build an interpreter?)"
            )
        if session.shouldstop or session.shouldfail:
            self.notes.append("(session interrupted -- coverage partial)")
        if self.failures and session.exitstatus == 0:
            session.exitstatus = pytest.ExitCode.TESTS_FAILED

    def _write(
        self, kind: str, dest: pathlib.Path, reports: List[CoverageReport]
    ) -> None:
        target = self._resolve(dest)
        render = reports_to_json if kind == "json" else reports_to_html
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(render(reports), encoding="utf-8")
        except OSError as exc:
            # 🔥 #270 battle B: a directory / unwritable path was an
            #    INTERNALERROR traceback at session end. One line, and
            #    the session fails (the CI artefact is missing).
            self.failures.append(
                f"cannot write {kind} report to {target}: "
                f"{exc.strerror or exc}"
            )
            return
        self.written.append(target)

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
        for note in self.notes:
            terminalreporter.write_line(f"xstate coverage {note}")
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
