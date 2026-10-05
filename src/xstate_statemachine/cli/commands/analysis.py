# src/xstate_statemachine/cli/commands/analysis.py
# -----------------------------------------------------------------------------
# 🔬 Shared machine analysis for `validate`, `inspect`, `docs` and `simulate`
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the CLI does NOT re-implement validation. It
#    builds the machine with the library's own `create_machine` -- with
#    `strict_config=True` so a misspelled key is a finding, not a warning
#    lost in a log -- and then walks the REAL `MachineNode` for facts
#    (states, events, timers, logic, unreachable states). Anything the
#    library would refuse, the CLI refuses in the same words.
# -----------------------------------------------------------------------------
"""Build a machine from a JSON file and derive facts about it."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ...exceptions import XStateMachineError
from ...factory import create_machine
from ...machine_logic import MachineLogic
from ...models import MachineNode, StateNode
from ...validation import transitions_of, walk
from ..extractor import extract_logic_names

logger = logging.getLogger(__name__)


@dataclass
class Finding:
    """One validation finding."""

    severity: str  # error | warning | info
    message: str
    path: str = ""


@dataclass
class Facts:
    """Everything the CLI knows about one machine file."""

    path: Path
    config: Dict[str, Any] = field(default_factory=dict)
    machine: Optional[MachineNode] = None
    findings: List[Finding] = field(default_factory=list)
    actions: Set[str] = field(default_factory=set)
    guards: Set[str] = field(default_factory=set)
    services: Set[str] = field(default_factory=set)
    delays: Set[str] = field(default_factory=set)
    events: Set[str] = field(default_factory=set)
    unreachable: List[str] = field(default_factory=list)
    engine_unreachable: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(f.severity == "error" for f in self.findings)

    @property
    def machine_id(self) -> str:
        return (
            self.config.get("id", self.path.stem)
            if self.config
            else self.path.stem
        )

    def state_count(self, *, all_levels: bool = False) -> int:
        if self.machine is None:
            return (
                len(self.config.get("states", {}))
                if isinstance(self.config, dict)
                else 0
            )
        if all_levels:
            return sum(1 for _ in walk(self.machine)) - 1
        return len(self.machine.states)

    def to_json(self) -> Dict[str, Any]:
        return {
            "file": str(self.path),
            "ok": self.ok,
            "machine": self.machine_id,
            "states": self.state_count(all_levels=True),
            "top_level_states": self.state_count(),
            "events": sorted(self.events),
            "actions": sorted(self.actions),
            "guards": sorted(self.guards),
            "services": sorted(self.services),
            "delays": sorted(self.delays),
            "unreachable_states": self.unreachable,
            "findings": [f.__dict__ for f in self.findings],
        }


class _CaptureWarnings(logging.Handler):
    """Collects the library's WARNING records during a build so the CLI can
    turn them into findings instead of interleaving them with the UI."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.records: List[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _stub_logic(
    actions: Set[str], guards: Set[str], services: Set[str]
) -> MachineLogic:
    """Placeholder logic so `create_machine` does not fail on missing impls."""
    return MachineLogic(
        actions={a: (lambda i, c, e, ad: None) for a in actions},
        guards={g: (lambda c, e: True) for g in guards},
        services={s: (lambda i, c, e: None) for s in services},
    )


def _unreachable(machine: MachineNode) -> List[str]:
    """State ids no transition, initial or history target can reach."""
    reachable: Set[str] = set()

    def enter(node: StateNode) -> None:
        if node.id in reachable:
            return
        reachable.add(node.id)
        if node.type == "parallel":
            for child in node.states.values():
                enter(child)
        elif node.initial and node.initial in node.states:
            enter(node.states[node.initial])
        elif node.type == "compound" and node.states and not node.initial:
            enter(next(iter(node.states.values())))

    def enter_target(node: StateNode) -> None:
        # 🔥 #269 battle: a target deep in the tree (`#m.a.b.leaf`, a
        #    history node) enters every ancestor on the way down -- and
        #    every sibling region of a parallel ancestor. Only the target
        #    itself used to be marked, so `xsm inspect` / `validate` called
        #    `m.a` "unreachable" while the engine sat in `m.a.b.leaf`.
        enter(node)
        if node.type == "history":
            parent = node.parent
            if parent is not None:
                enter(parent)
        child = node
        anc = node.parent
        while anc is not None:
            if anc.type == "parallel":
                for region in anc.states.values():
                    if region is not child:
                        enter(region)
            reachable.add(anc.id)
            child, anc = anc, anc.parent

    enter(machine)
    changed = True
    while changed:
        changed = False
        for node in list(walk(machine)):
            if node.id not in reachable:
                continue
            # `transitions_of` covers on / always / after / onDone and every
            # invoke's onDone / onError; `resolved_target` is memoised by the
            # build-time validator (None = targetless / internal).
            for _label, t in transitions_of(node):
                target = t.resolved_target
                if target is not None and target.id not in reachable:
                    enter_target(target)
                    changed = True
    return sorted(
        n.id
        for n in walk(machine)
        if n is not machine and n.id not in reachable
    )


def analyse(
    path: Path,
    *,
    strict_config: bool = True,
    engine_reachability: bool = False,
) -> Facts:
    """Load, build and inspect one machine file. Never raises for a bad
    file -- problems become `findings`."""
    facts = Facts(path=path)
    if not path.exists():
        facts.findings.append(Finding("error", "file not found"))
        return facts
    try:
        facts.config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        facts.findings.append(
            Finding("error", f"invalid JSON: {exc}", f"line {exc.lineno}")
        )
        return facts
    if not isinstance(facts.config, dict):
        facts.findings.append(Finding("error", "root must be a JSON object"))
        return facts

    # 📝 Cheap structural checks first so the messages the tests pin stay.
    cfg = facts.config
    if "id" not in cfg:
        facts.findings.append(Finding("error", "missing 'id' field"))
    if "initial" not in cfg and cfg.get("type") != "parallel":
        facts.findings.append(Finding("error", "missing 'initial' field"))
    if "states" not in cfg:
        facts.findings.append(Finding("error", "missing 'states' field"))
    elif not isinstance(cfg.get("states"), dict):
        facts.findings.append(Finding("error", "'states' must be an object"))
    elif cfg.get("initial") and cfg["initial"] not in cfg["states"]:
        facts.findings.append(
            Finding(
                "error",
                f"initial state '{cfg['initial']}' not found in states",
            )
        )
    if not facts.ok:
        return facts

    try:
        facts.actions, facts.guards, facts.services = extract_logic_names(cfg)
    except Exception as exc:  # noqa: BLE001 -- reported, not raised
        facts.findings.append(
            Finding("warning", f"could not extract logic names: {exc}")
        )

    cap = _CaptureWarnings()
    # 🧭 Resolve the package logger from the package itself (not a literal
    #    name) so an import as `src.xstate_statemachine` -- the test-suite
    #    path -- is captured just like the installed `xstate_statemachine`.
    lib_logger = logging.getLogger(__name__.rsplit(".cli", 1)[0])
    lib_logger.addHandler(cap)
    # 🧭 The library's unknown-key report is a WARNING log record. A host
    #    (or a test) may have `logging.disable()`d everything, which would
    #    silently drop the one finding this command exists to surface;
    #    lift the gate for the duration of the build and put it back.
    disabled_before = logging.root.manager.disable
    logging.disable(logging.NOTSET)
    try:
        facts.machine = create_machine(
            json.loads(json.dumps(cfg)),
            logic=_stub_logic(facts.actions, facts.guards, facts.services),
            strict_config=strict_config,
        )
    except XStateMachineError as exc:
        facts.findings.append(Finding("error", str(exc)))
        return facts
    finally:
        lib_logger.removeHandler(cap)
        logging.disable(disabled_before)
    for rec in cap.records:
        facts.findings.append(
            Finding("warning", rec.getMessage().lstrip("⚠️ ").strip())
        )

    m = facts.machine
    facts.events = set(m.known_events)
    for node in walk(m):
        for key in node.after:
            if isinstance(key, str):
                facts.delays.add(key)
    facts.unreachable = _unreachable(m)
    for sid in facts.unreachable:
        facts.findings.append(Finding("warning", "state is unreachable", sid))
    # 🗺️ #269: the static pass above is the cheap, complete-over-approximation
    #    every `validate` run pays for. The engine-backed walk is exact but
    #    depth-bounded and can be slow on wide parallel charts, so it runs
    #    only when asked (`xsm inspect`, not `validate` over 200 files) and
    #    only ADDS findings: a state the static pass calls reachable that
    #    the real engine cannot enter within the bound -- typically a
    #    target whose compound parent has no `initial`, or a leaf behind a
    #    service that must fail. It never removes a static warning, so the
    #    corpus regression stays byte-identical.
    if engine_reachability:
        facts.engine_unreachable = _engine_unreachable(m, facts.unreachable)
        for sid in facts.engine_unreachable:
            facts.findings.append(
                Finding(
                    "warning",
                    "state is never entered by the engine "
                    "(reachable statically only)",
                    sid,
                )
            )
    return facts


def _engine_unreachable(
    machine: MachineNode, static_unreachable: List[str], *, max_depth: int = 8
) -> List[str]:
    """Settled states the engine never reaches that the static pass missed.

    Only ATOMIC / final states are compared: compound, parallel and history
    nodes are entered transiently and `reachable_states` reports them via
    their leaves; a state that merely hosts an `invoke` + `always` is
    passed through, never settled in, and is excluded too.
    """
    from ...graph import reachable_states

    try:
        reached = reachable_states(machine, guards="both", max_depth=max_depth)
    except Exception:  # noqa: BLE001 -- analysis must never crash the CLI
        logger.debug("engine reachability skipped", exc_info=True)
        return []
    skip = set(static_unreachable)
    out: List[str] = []
    for node in walk(machine):
        if node is machine or node.id in skip or node.id in reached:
            continue
        if node.type not in ("atomic", "final"):
            continue
        if node.invoke or "" in node.on:  # pass-through states
            continue
        out.append(node.id)
    return sorted(out)


def kind_of(node: StateNode) -> str:
    return node.type


def event_table(machine: MachineNode) -> List[Tuple[str, str, str, str, str]]:
    """(event, from state, target, guard, actions) for every transition."""
    rows = []
    for node in walk(machine):
        for label, t in transitions_of(node):
            targets = (
                t.resolved_target.id if t.resolved_target else "(internal)"
            )
            guard = getattr(t.guard_def, "type", "") if t.guard_def else ""
            acts = ", ".join(a.type for a in t.actions)
            rows.append((_short_label(label), node.id, targets, guard, acts))
    return rows


def _short_label(label: str) -> str:
    """`on 'GO'` -> `GO`; `after 500` / `onDone` / `invoke 'x' onDone` kept."""
    if label.startswith("on '") and label.endswith("'"):
        return label[4:-1]
    return label or "always"


def short_id(state_id: str, machine_id: str) -> str:
    """Drop the machine-id prefix from a state id for compact tables."""
    prefix = machine_id + "."
    return state_id[len(prefix) :] if state_id.startswith(prefix) else state_id
