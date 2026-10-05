# src/xstate_statemachine/coverage.py
# -----------------------------------------------------------------------------
# 📊 State & transition coverage (#270)
# -----------------------------------------------------------------------------
# 🏛️ Line coverage says nothing about whether a test suite ever reached
#    `timeout` or `errorRecovery`. The chart knows every state and every
#    transition; a plugin hook knows which ones ran. `CoverageCollector` is
#    that plugin: attach it to interpreters (or register it globally with
#    `plugins.register_global`) and ask it for a `CoverageReport`.
#
# 📝 Denominators are static: every non-history state under the root, and
#    `graph.transition_coverage_targets(machine)` for transitions. A hit is
#    matched on the `TransitionDefinition` object the engine executed, so
#    the numerator and the denominator can never disagree on labels.
#
# 🧵 One collector may observe interpreters on many threads (the sync
#    engine's daemon threads, a pytest session with xdist-free threads):
#    every mutation happens under one lock.
#
# 🪶 Stdlib only; core imports nothing from here.
# -----------------------------------------------------------------------------
"""State and transition coverage for statecharts.

Example:
    >>> from xstate_statemachine import create_machine, SyncInterpreter
    >>> from xstate_statemachine.coverage import CoverageCollector
    >>> m = create_machine({"id": "t", "initial": "a", "states": {
    ...     "a": {"on": {"GO": "b"}}, "b": {"on": {"BACK": "a"}}}})
    >>> cov = CoverageCollector()
    >>> i = SyncInterpreter(m).use(cov).start(); i.send("GO")
    >>> r = cov.report(m)
    >>> (r.states_visited, r.states_total, r.transitions_hit)
    (2, 2, 1)
"""

from __future__ import annotations

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import html
import json
import threading
import weakref
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from .graph import transition_coverage_targets
from .models import MachineNode
from .plugins import PluginBase
from .validation import transitions_of, walk

__all__ = [
    "COVERAGE_SCHEMA_VERSION",
    "CoverageCollector",
    "CoverageReport",
    "below",
    "format_edge",
    "machine_key",
    "reports_from_json",
    "reports_to_html",
    "reports_to_json",
    "reports_to_text",
]

#: The ``version`` of the JSON document `reports_to_json` writes. Bumped
#: only on an incompatible layout change; readers reject other versions.
COVERAGE_SCHEMA_VERSION = 1

Triple = Tuple[str, str, str]
Machine = MachineNode[Any]


def machine_key(machine: Machine) -> str:
    """``"<machine id>@<structure_hash>"`` -- two builds of the same chart
    share a key; an edited chart gets a new one."""
    return f"{machine.id}@{machine.structure_hash}"


def _pct(hit: int, total: int) -> float:
    return 100.0 if total == 0 else round(100.0 * hit / total, 2)


def _short(state_id: str, machine_id: str) -> str:
    prefix = machine_id + "."
    return state_id[len(prefix) :] if state_id.startswith(prefix) else state_id


def _edge_label(label: str) -> str:
    """``"on 'GO'"`` → ``"GO"``; other labels (``after 2000``) unchanged."""
    if label.startswith("on '") and label.endswith("'"):
        return label[4:-1]
    return label


# -----------------------------------------------------------------------------
# 🧾 Report
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class CoverageReport:
    """Coverage of one machine.

    Attributes:
        machine_id: The machine's id.
        key: `machine_key` of the machine.
        states_visited: Distinct states entered at least once.
        states_total: Every state except the root and history
            pseudo-states.
        unvisited: Sorted ids of the states never entered.
        transitions_hit: Distinct chart transitions taken at least once.
        transitions_total: ``len(graph.transition_coverage_targets(m))``.
        unhit: Sorted ``(from_id, label, to_id)`` never taken.
    """

    machine_id: str
    key: str
    states_visited: int
    states_total: int
    unvisited: Tuple[str, ...]
    transitions_hit: int
    transitions_total: int
    unhit: Tuple[Triple, ...] = field(default_factory=tuple)

    @property
    def state_percent(self) -> float:
        return _pct(self.states_visited, self.states_total)

    @property
    def transition_percent(self) -> float:
        return _pct(self.transitions_hit, self.transitions_total)

    def to_dict(self) -> Dict[str, Any]:
        """The per-machine object of the version-1 JSON schema."""
        return {
            "machine": self.machine_id,
            "key": self.key,
            "states": {
                "visited": self.states_visited,
                "total": self.states_total,
                "percent": self.state_percent,
                "unvisited": list(self.unvisited),
            },
            "transitions": {
                "hit": self.transitions_hit,
                "total": self.transitions_total,
                "percent": self.transition_percent,
                "unhit": [
                    {"from": f, "label": lbl, "to": t}
                    for f, lbl, t in self.unhit
                ],
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoverageReport":
        """Inverse of `to_dict` (raises ``KeyError`` / ``TypeError`` on a
        malformed object)."""
        s, t = data["states"], data["transitions"]
        return cls(
            machine_id=str(data["machine"]),
            key=str(data["key"]),
            states_visited=int(s["visited"]),
            states_total=int(s["total"]),
            unvisited=tuple(str(x) for x in s["unvisited"]),
            transitions_hit=int(t["hit"]),
            transitions_total=int(t["total"]),
            unhit=tuple(
                (str(u["from"]), str(u["label"]), str(u["to"]))
                for u in t["unhit"]
            ),
        )

    def to_json(self) -> str:
        return reports_to_json([self])

    def to_text(self) -> str:
        return reports_to_text([self])

    def to_html(self) -> str:
        return reports_to_html([self])


# -----------------------------------------------------------------------------
# 🔌 Collector
# -----------------------------------------------------------------------------
def _index_of(machine: Machine) -> Dict[int, Triple]:
    """``id(TransitionDefinition)`` → coverage triple for one build."""
    index: Dict[int, Triple] = {}
    for node in walk(machine):
        for label, t in transitions_of(node):
            target = t.resolved_target
            index[id(t)] = (node.id, label, (target or node).id)
    return index


class _MachineData:
    """Observations for one structure key (shared by every build)."""

    __slots__ = ("machine", "states", "hits")

    def __init__(self, machine: Machine) -> None:
        #: 📝 The first build seen; used for `machines()` / `report()`.
        self.machine = machine
        self.states: Set[str] = set()
        self.hits: Set[Triple] = set()


class _Build:
    """One machine OBJECT: its own transition index + the shared data.

    📝 Held only weakly (battle #270): a rebuilt chart per test must not
    keep every earlier build, and its index, alive for the session. The
    index is per build, so a recycled ``id()`` can never be looked up in
    an index that outlived its machine.
    """

    __slots__ = ("ref", "index", "data")

    def __init__(
        self, ref: "weakref.ref[Machine]", data: _MachineData
    ) -> None:
        machine = ref()
        assert machine is not None
        self.ref = ref
        self.index = _index_of(machine)
        self.data = data


class CoverageCollector(PluginBase[Any]):
    """A plugin that records visited states and taken transitions.

    Attach it per interpreter (``interp.use(collector)``) or process-wide
    with `plugins.register_global`. Configurations of parallel states mark
    every active leaf *and* its ancestors; a history restore marks the
    states actually re-entered. Restored interpreters (``from_snapshot``)
    count their configuration when they ``start()``.

    Thread-safe.
    """

    def __init__(self) -> None:
        # 📝 Re-entrant: a weakref callback (`_forget`) can fire on this
        #    thread from a GC triggered while the lock is already held.
        self._lock = threading.RLock()
        self._data: Dict[str, _MachineData] = {}
        #: 📝 Per machine OBJECT (a rebuilt chart has new transition
        #:    objects), weakly held; entries vanish with their machine.
        self._by_obj: Dict[int, _Build] = {}

    # -------------------------------------------------------------- recording
    def _forget(self, ref: "weakref.ref[Machine]") -> None:
        # 📝 Weakref callback: may run on any thread, at any GC point.
        with self._lock:
            for k, b in list(self._by_obj.items()):
                if b.ref is ref:
                    del self._by_obj[k]

    def _build_for(self, machine: Machine) -> _Build:
        hit = self._by_obj.get(id(machine))
        if hit is not None and hit.ref() is machine:
            return hit
        key = machine_key(machine)
        data = self._data.get(key)
        if data is None:
            data = self._data[key] = _MachineData(machine)
        build = _Build(weakref.ref(machine, self._forget_cb()), data)
        self._by_obj[id(machine)] = build
        return build

    def _forget_cb(self) -> Any:
        # 📝 A weak reference to self: the callback must not keep the
        #    collector alive through every machine it has seen.
        me = weakref.ref(self)

        def cb(ref: "weakref.ref[Machine]") -> None:
            col = me()
            if col is not None:
                col._forget(ref)

        return cb

    def _data_for(self, machine: Machine) -> _MachineData:
        return self._build_for(machine).data

    def _record_config(self, interpreter: Any, nodes: Iterable[Any]) -> None:
        machine = getattr(interpreter, "machine", None)
        if not isinstance(machine, MachineNode):
            return
        with self._lock:
            data = self._data_for(machine)
            for node in nodes:
                while node is not None and node is not machine:
                    data.states.add(node.id)
                    node = node.parent

    def on_interpreter_start(self, interpreter: Any) -> None:
        # 📝 Fresh interpreters have an empty configuration here (the init
        #    `on_transition` records it); restored ones already sit in
        #    their configuration and this is the only place it is seen.
        self._record_config(
            interpreter, list(getattr(interpreter, "_active_state_nodes", ()))
        )

    def on_transition(
        self,
        interpreter: Any,
        from_states: Any,
        to_states: Any,
        transition: Any,
    ) -> None:
        self._record_config(interpreter, list(to_states))
        machine = getattr(interpreter, "machine", None)
        if not isinstance(machine, MachineNode):
            return
        with self._lock:
            build = self._build_for(machine)
            triple = build.index.get(id(transition))
            if triple is not None:
                build.data.hits.add(triple)

    # -------------------------------------------------------------- merging
    def merge(self, other: "CoverageCollector") -> None:
        """Fold *other*'s observations into this collector."""
        with other._lock:
            items = [
                (k, d.machine, set(d.states), set(d.hits))
                for k, d in other._data.items()
            ]
        with self._lock:
            for _key, machine, states, hits in items:
                data = self._data_for(machine)
                data.states |= states
                data.hits |= hits

    # -------------------------------------------------------------- reports
    def report(self, machine: Machine) -> CoverageReport:
        """Coverage of *machine* (all zeros if never observed)."""
        key = machine_key(machine)
        with self._lock:
            data = self._data.get(key)
            states = set(data.states) if data else set()
            hits = set(data.hits) if data else set()
        all_states = sorted(
            n.id
            for n in walk(machine)
            if n is not machine and n.type != "history"
        )
        targets = transition_coverage_targets(machine)
        visited = [s for s in all_states if s in states]
        hit = targets & hits
        return CoverageReport(
            machine_id=machine.id,
            key=key,
            states_visited=len(visited),
            states_total=len(all_states),
            unvisited=tuple(s for s in all_states if s not in states),
            transitions_hit=len(hit),
            transitions_total=len(targets),
            unhit=tuple(sorted(targets - hits)),
        )

    def machines(self) -> List[Machine]:
        """Every machine observed so far (one per structure key)."""
        with self._lock:
            return [d.machine for _, d in sorted(self._data.items())]

    def reports(self) -> List[CoverageReport]:
        """A report per observed machine, sorted by key."""
        return [self.report(m) for m in self.machines()]


# -----------------------------------------------------------------------------
# 🖨️ Renderers (shared by the pytest plugin and `xsm coverage`)
# -----------------------------------------------------------------------------
def reports_to_json(reports: Iterable[CoverageReport]) -> str:
    """The stable version-1 document::

    {"version": 1, "machines": [{"machine", "key",
      "states": {"visited", "total", "percent", "unvisited"},
      "transitions": {"hit", "total", "percent",
                      "unhit": [{"from", "label", "to"}]}}]}
    """
    doc = {
        "version": COVERAGE_SCHEMA_VERSION,
        "machines": [r.to_dict() for r in reports],
    }
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


def reports_from_json(text: str) -> List[CoverageReport]:
    """Parse a `reports_to_json` document.

    Raises:
        ValueError: Not JSON, wrong ``version``, or a malformed entry.
    """
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"not a coverage report: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("version") != (
        COVERAGE_SCHEMA_VERSION
    ):
        raise ValueError(
            f"unsupported coverage report version "
            f"{doc.get('version') if isinstance(doc, dict) else None!r}; "
            f"expected {COVERAGE_SCHEMA_VERSION}"
        )
    try:
        return [CoverageReport.from_dict(m) for m in doc["machines"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"malformed coverage report: {exc!r}") from exc


def _fmt_pct(p: float) -> str:
    return f"{p:.0f}%" if float(p).is_integer() else f"{p:.1f}%"


def format_edge(triple: Triple, machine_id: str) -> str:
    f, lbl, t = triple
    return (
        f"{_short(f, machine_id)} --{_edge_label(lbl)}--> "
        f"{_short(t, machine_id)}"
    )


#: The terminal summary lists at most this many names per line; the
#: JSON / HTML reports always carry the complete lists.
TEXT_LIST_LIMIT = 20


def _capped(items: List[str]) -> str:
    if len(items) <= TEXT_LIST_LIMIT:
        return ", ".join(items)
    rest = len(items) - TEXT_LIST_LIMIT
    return ", ".join(items[:TEXT_LIST_LIMIT]) + f", ... and {rest} more"


def reports_to_text(
    reports: Iterable[CoverageReport], *, header: bool = True
) -> str:
    """The terminal summary::

    ---- xstate coverage ----
    checkout          states 12/15 (80%)  transitions 18/22 (82%)
      unvisited: timeout, errorRecovery
      unhit:     paying --PAY_FAILED--> failed, ...
    """
    reports = list(reports)
    lines: List[str] = ["---- xstate coverage ----"] if header else []
    width = max([len(r.machine_id) for r in reports] + [16]) + 2
    for r in reports:
        lines.append(
            f"{r.machine_id:<{width}}"
            f"states {r.states_visited}/{r.states_total} "
            f"({_fmt_pct(r.state_percent)})  "
            f"transitions {r.transitions_hit}/{r.transitions_total} "
            f"({_fmt_pct(r.transition_percent)})"
        )
        if r.unvisited:
            names = _capped([_short(s, r.machine_id) for s in r.unvisited])
            lines.append(f"  unvisited: {names}")
        if r.unhit:
            edges = _capped([format_edge(u, r.machine_id) for u in r.unhit])
            lines.append(f"  unhit:     {edges}")
    if not reports:
        lines.append("(no machines observed)")
    return "\n".join(lines) + "\n"


_HTML_STYLE = (
    "body{font:14px/1.4 system-ui,sans-serif;margin:2em;color:#222}"
    "table{border-collapse:collapse;margin:1em 0}"
    "td,th{border:1px solid #ccc;padding:4px 8px;text-align:left}"
    ".bar{display:inline-block;height:10px;background:#3a7}"
    ".miss{color:#b33}code{font-size:13px}"
)


def reports_to_html(
    reports: Iterable[CoverageReport], *, title: str = "xstate coverage"
) -> str:
    """One self-contained HTML file: inline CSS, no scripts, no links."""
    esc = html.escape
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        f"<title>{esc(title)}</title>",
        f"<style>{_HTML_STYLE}</style></head><body>",
        f"<h1>{esc(title)}</h1>",
        "<table><tr><th>machine</th><th>states</th>"
        "<th>transitions</th></tr>",
    ]
    reports = list(reports)
    for r in reports:
        parts.append(
            f"<tr><td><a href='#{esc(r.key)}'>{esc(r.machine_id)}</a></td>"
            f"<td>{r.states_visited}/{r.states_total} "
            f"({_fmt_pct(r.state_percent)}) <span class='bar' "
            f"style='width:{r.state_percent:.0f}px'></span></td>"
            f"<td>{r.transitions_hit}/{r.transitions_total} "
            f"({_fmt_pct(r.transition_percent)}) <span class='bar' "
            f"style='width:{r.transition_percent:.0f}px'></span></td></tr>"
        )
    parts.append("</table>")
    for r in reports:
        parts.append(f"<h2 id='{esc(r.key)}'>{esc(r.machine_id)}</h2>")
        parts.append("<h3>Unvisited states</h3><ul>")
        parts.extend(
            f"<li class='miss'><code>{esc(s)}</code></li>" for s in r.unvisited
        )
        parts.append("</ul><h3>Unhit transitions</h3><ul>")
        parts.extend(
            f"<li class='miss'><code>{esc(format_edge(u, r.machine_id))}"
            f"</code></li>"
            for u in r.unhit
        )
        parts.append("</ul>")
    parts.append("</body></html>")
    return "\n".join(parts) + "\n"


def below(
    reports: Iterable[CoverageReport],
    *,
    state: Optional[float] = None,
    transition: Optional[float] = None,
) -> List[str]:
    """Human-readable failures of the ``fail-under`` thresholds.

    Raises:
        ValueError: A threshold is NaN or outside ``0..100`` (a NaN
            compares false with everything and would disable the gate).
    """
    for name, v in (("state", state), ("transition", transition)):
        if v is not None and not 0.0 <= v <= 100.0:
            raise ValueError(f"{name} threshold must be 0..100, got {v!r}")
    out: List[str] = []
    for r in reports:
        if state is not None and r.state_percent < state:
            out.append(
                f"{r.machine_id}: state coverage "
                f"{_fmt_pct(r.state_percent)} < {state:g}%"
            )
        if transition is not None and r.transition_percent < transition:
            out.append(
                f"{r.machine_id}: transition coverage "
                f"{_fmt_pct(r.transition_percent)} < {transition:g}%"
            )
    return out
