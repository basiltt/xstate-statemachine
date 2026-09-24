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
                    enter(target)
                    changed = True
    return sorted(
        n.id
        for n in walk(machine)
        if n is not machine and n.id not in reachable
    )


def analyse(path: Path, *, strict_config: bool = True) -> Facts:
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
    lib_logger = logging.getLogger("xstate_statemachine")
    lib_logger.addHandler(cap)
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
    return facts


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
            rows.append((label or "always", node.id, targets, guard, acts))
    return rows
