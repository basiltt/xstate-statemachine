# src/xstate_statemachine/cli/commands/simulate.py
# -----------------------------------------------------------------------------
# 🎮 `xsm simulate` -- run a machine live in the terminal
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: ONE engine drives both modes. `Session` wraps a
#    `SyncInterpreter` on a `SimulatedClock` with stub logic (actions
#    record, guards are user-overridable, services no-op) and keeps a
#    snapshot stack for undo. The scripted mode (`--events`, `--clock`,
#    `--script`, `--json`) is a deterministic driver over that session for
#    CI; the interactive mode is a key-driven driver over the SAME session,
#    so anything you can do live you can replay from a script -- and the
#    interactive loop is testable with an injected key source.
# -----------------------------------------------------------------------------
"""The `simulate` subcommand."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from ...clock import SimulatedClock
from ...events import Receipt
from ...factory import create_machine
from ...machine_logic import MachineLogic
from ...models import MachineNode
from ...sync_interpreter import SyncInterpreter
from ...validation import walk
from ..extractor import extract_logic_names
from ..ui import Column, Table
from ..ui import keys as K
from . import get_console
from .inspect import state_tree


# =============================================================================
# Session
# =============================================================================
@dataclass
class StepRecord:
    """One thing that happened: an event, a clock advance or an undo."""

    kind: str  # event | clock | undo | reset
    label: str
    before: List[str]
    after: List[str]
    changed: bool
    actions: List[str] = field(default_factory=list)
    error: Optional[str] = None
    denied: bool = False
    deferred: bool = False
    clock_ms: float = 0.0


class Session:
    """A machine, a virtual clock and a history, driven by events."""

    def __init__(
        self,
        config: Dict[str, Any],
        *,
        guards: Optional[Dict[str, bool]] = None,
    ):
        self.config = config
        self.actions_ran: List[str] = []
        self.guard_values: Dict[str, bool] = dict(guards or {})
        a, g, s = extract_logic_names(config)
        self.action_names, self.guard_names, self.service_names = (
            sorted(a),
            sorted(g),
            sorted(s),
        )
        self.machine: MachineNode = create_machine(
            json.loads(json.dumps(config)), logic=self._logic(a, g, s)
        )
        self.clock = SimulatedClock()
        self.interp = SyncInterpreter(self.machine, clock=self.clock).start()
        self.history: List[StepRecord] = []
        self._undo: List[str] = []  # snapshots BEFORE each step

    # ---------------------------------------------------------------- logic
    def _logic(
        self, actions: Set[str], guards: Set[str], services: Set[str]
    ) -> MachineLogic:
        session = self

        def mk_action(name: str):
            def _a(i: Any, c: Any, e: Any, ad: Any) -> None:
                session.actions_ran.append(name)

            return _a

        def mk_guard(name: str):
            def _g(c: Any, e: Any) -> bool:
                return session.guard_values.get(name, True)

            return _g

        return MachineLogic(
            actions={x: mk_action(x) for x in actions},
            guards={x: mk_guard(x) for x in guards},
            services={x: (lambda i, c, e: None) for x in services},
        )

    # ---------------------------------------------------------------- facts
    @property
    def active(self) -> Set[str]:
        return set(self.interp.current_state_ids)

    @property
    def enabled_events(self) -> List[str]:
        """Events `can()` says would do something right now."""
        return [
            e for e in sorted(self.machine.known_events) if self.interp.can(e)
        ]

    @property
    def armed_timers(self) -> List[Tuple[str, Any]]:
        out = []
        for n in walk(self.machine):
            if n.id in self.active or any(
                s.startswith(n.id + ".") for s in self.active
            ):
                for d in n.after:
                    out.append((n.id, d))
        return out

    # ---------------------------------------------------------------- steps
    def _record(
        self,
        kind: str,
        label: str,
        before: Set[str],
        receipt: Optional[Receipt],
    ) -> StepRecord:
        after = self.active
        rec = StepRecord(
            kind=kind,
            label=label,
            before=sorted(before),
            after=sorted(after),
            changed=before != after,
            actions=list(self.actions_ran),
            error=(
                type(receipt.error).__name__
                if receipt and receipt.error
                else None
            ),
            denied=bool(receipt and receipt.denied),
            deferred=bool(receipt and receipt.deferred),
            clock_ms=self.clock.now() * 1000.0,
        )
        self.history.append(rec)
        return rec

    def send(self, event: str, **payload: Any) -> StepRecord:
        self._undo.append(self.interp.get_snapshot())
        before = self.active
        self.actions_ran.clear()
        receipt = self.interp.send(event, wait=True, **payload)
        return self._record("event", event, before, receipt)

    def advance(self, ms: float) -> StepRecord:
        self._undo.append(self.interp.get_snapshot())
        before = self.active
        self.actions_ran.clear()
        self.clock.increment(ms)
        return self._record("clock", f"+{ms:g} ms", before, None)

    def undo(self) -> Optional[StepRecord]:
        if not self._undo:
            return None
        blob = self._undo.pop()
        before = self.active
        self.interp.stop()
        # ⏱️ A static restore leaves `after` timers dormant (#128); the
        #    simulator's undo means "be in that state again", so re-arm
        #    them from zero -- the timer restarts, as it would on entry.
        self.interp = SyncInterpreter.from_snapshot(
            blob, self.machine, clock=self.clock, restart_timers=True
        )
        self.interp.start()
        return self._record("undo", "undo", before, None)

    def reset(self) -> StepRecord:
        before = self.active
        self.interp.stop()
        self.clock = SimulatedClock()
        self.interp = SyncInterpreter(self.machine, clock=self.clock).start()
        self._undo.clear()
        return self._record("reset", "reset", before, None)

    def set_guard(self, name: str, value: bool) -> None:
        self.guard_values[name] = value

    def stop(self) -> None:
        if self.interp.status == "running":
            self.interp.stop()

    # ---------------------------------------------------------------- export
    def to_json(self) -> Dict[str, Any]:
        return {
            "machine": self.machine.id,
            "status": self.interp.status,
            "active": sorted(self.active),
            "value": self.interp.value,
            "context": self.interp.context,
            "clock_ms": self.clock.now() * 1000.0,
            "enabled_events": self.enabled_events,
            "chain_trips": self.interp.chain_trips,
            "history": [r.__dict__ for r in self.history],
        }


# =============================================================================
# Scripted driver
# =============================================================================
def run_script(session: Session, commands: List[Dict[str, Any]]) -> None:
    """Apply a list of ``{"send": "GO"}`` / ``{"clock": 500}`` /
    ``{"guard": "g", "value": false}`` / ``{"undo": true}`` commands."""
    for cmd in commands:
        if "send" in cmd:
            session.send(cmd["send"], **(cmd.get("payload") or {}))
        elif "clock" in cmd:
            session.advance(float(cmd["clock"]))
        elif "guard" in cmd:
            session.set_guard(cmd["guard"], bool(cmd.get("value", True)))
        elif cmd.get("undo"):
            session.undo()
        elif cmd.get("reset"):
            session.reset()
        else:
            raise ValueError(f"unknown script command {cmd!r}")


def parse_events_arg(
    events: Optional[str], clock: Optional[str]
) -> List[Dict[str, Any]]:
    """`--events A,B,+500,C` → commands; `+N` is a clock advance."""
    out: List[Dict[str, Any]] = []
    for tok in (events or "").split(","):
        tok = tok.strip()
        if not tok:
            continue
        if tok.startswith("+"):
            out.append({"clock": float(tok[1:])})
        else:
            out.append({"send": tok})
    if clock:
        out.append({"clock": float(clock)})
    return out


# =============================================================================
# Rendering
# =============================================================================
def _status_panel(session: Session) -> List[str]:
    c = get_console()
    i = session.interp
    status_role = {
        "running": "ok",
        "done": "brand",
        "error": "err",
        "stopped": "muted",
    }.get(i.status, "text")
    lines = [
        f"{c.style('status', 'key')}  {c.style(i.status, status_role)}    "
        f"{c.style('clock', 'key')}  {session.clock.now() * 1000:g} ms    "
        f"{c.style('steps', 'key')}  {len(session.history)}"
    ]
    if i.context:
        ctx = json.dumps(i.context, default=str)
        lines.append(f"{c.style('context', 'key')} {c.style(ctx, 'code')}")
    if session.armed_timers:
        lines.append(
            f"{c.style('timers', 'key')}  "
            + ", ".join(
                f"{sid.rsplit('.', 1)[-1]}:{d}"
                for sid, d in session.armed_timers
            )
        )
    if i.chain_trips:
        lines.append(
            c.style(
                f"chain trips {i.chain_trips}  {type(i.last_chain_error).__name__}",
                "warn",
            )
        )
    if i.last_error and not i.chain_trips:
        lines.append(
            c.style(f"last_error {type(i.last_error).__name__}", "warn")
        )
    return lines


def render_state(session: Session, *, title: str = "simulate") -> None:
    c = get_console()
    c.panel(_status_panel(session), title=title, subtitle=session.machine.id)
    c.tree(
        state_tree(
            session.machine, active=session.active, unicode=c.caps.unicode
        )
    )


def render_step(rec: StepRecord) -> None:
    c = get_console()
    icon = {"event": "→", "clock": "⏱", "undo": "↶", "reset": "⟲"}.get(
        rec.kind, "•"
    )
    if not c.caps.unicode:
        icon = {"event": "->", "clock": "T+", "undo": "<-", "reset": "<<"}.get(
            rec.kind, "*"
        )
    label = c.style(rec.label, "event" if rec.kind == "event" else "accent")
    if rec.error:
        outcome = c.style(f"error {rec.error}", "err")
    elif rec.denied:
        outcome = c.style("denied by guard", "warn")
    elif rec.deferred:
        outcome = c.style("deferred", "warn")
    elif rec.changed:
        outcome = c.style(
            " ".join(s.rsplit(".", 1)[-1] for s in rec.after), "ok"
        )
    else:
        outcome = c.style("no change", "muted")
    acts = (
        c.style("  actions: " + ", ".join(rec.actions), "action")
        if rec.actions
        else ""
    )
    c.print(f"  {icon} {label}  {outcome}{acts}")


def render_history_table(session: Session) -> None:
    c = get_console()
    t = Table(
        [
            Column("#", align="right", min_width=2),
            Column("Step", role="event", min_width=8),
            Column("Result", min_width=10),
            Column("Actions", role="action"),
            Column("Clock", align="right", min_width=6),
        ],
        zebra=True,
    )
    for n, r in enumerate(session.history, 1):
        result = r.error or (
            "denied"
            if r.denied
            else (
                "deferred"
                if r.deferred
                else (
                    " ".join(s.rsplit(".", 1)[-1] for s in r.after)
                    if r.changed
                    else "-"
                )
            )
        )
        t.add(n, r.label, result, ", ".join(r.actions), f"{r.clock_ms:g}")
    c.table(t)


# =============================================================================
# Interactive driver
# =============================================================================
def interactive(
    session: Session, *, source: Optional[K.KeySource] = None
) -> None:
    c = get_console()
    src = source or K.default_source()
    c.blank()
    render_state(session)
    c.blank()
    c.print(
        c.style(
            "  ↑↓ pick event · enter send · t +timer · c +clock · g guards · u undo · r reset · h history · s snapshot · q quit",
            "dim",
        )
    )
    c.blank()
    cursor = 0
    while True:
        events = session.enabled_events
        options = [(e, "") for e in events] or [("(no enabled events)", "")]
        if events:
            idx = c.select(
                "Send",
                options,
                default=min(cursor, len(events) - 1),
                source=src,
                hint="enter send · esc for commands",
            )
            if idx is not None:
                cursor = idx
                rec = session.send(events[idx])
                render_step(rec)
                if rec.changed:
                    c.pulse(
                        "  "
                        + "  ".join(s.rsplit(".", 1)[-1] for s in rec.after)
                    )
                c.blank()
                render_state(session)
                c.blank()
                continue
        # command mode
        key = src()
        if key in ("q", K.ESC):
            c.print(c.style("bye", "muted"))
            return
        if key == "t":
            timers = session.armed_timers
            if not timers:
                c.warn("no timer armed in the active configuration")
                continue
            delay = max(d for _, d in timers if isinstance(d, (int, float)))
            render_step(session.advance(float(delay) + 1))
        elif key == "c":
            raw = c.text("Advance clock by ms:", default="1000", source=src)
            if raw:
                try:
                    render_step(session.advance(float(raw)))
                except ValueError:
                    c.error("not a number")
        elif key == "g":
            if not session.guard_names:
                c.warn("this machine has no guards")
                continue
            chosen = c.multiselect(
                "Guards returning True",
                [(g, "") for g in session.guard_names],
                selected=[
                    i
                    for i, g in enumerate(session.guard_names)
                    if session.guard_values.get(g, True)
                ],
                source=src,
            )
            if chosen is not None:
                for i, g in enumerate(session.guard_names):
                    session.set_guard(g, i in chosen)
        elif key == "u":
            undone = session.undo()
            if undone is None:
                c.warn("nothing to undo")
            else:
                render_step(undone)
        elif key == "r":
            render_step(session.reset())
        elif key == "h":
            render_history_table(session)
        elif key == "s":
            c.print(c.style(session.interp.get_snapshot(), "code"))
        else:
            continue
        c.blank()
        render_state(session)
        c.blank()


# =============================================================================
# Entry
# =============================================================================
def run_simulate(
    path: str,
    *,
    events: Optional[str] = None,
    clock: Optional[str] = None,
    script: Optional[str] = None,
    as_json: bool = False,
    guards_false: Optional[str] = None,
) -> None:
    c = get_console()
    logging.disable(logging.CRITICAL)
    try:
        config = json.loads(Path(path).read_text(encoding="utf-8"))
        guards = {
            g.strip(): False
            for g in (guards_false or "").split(",")
            if g.strip()
        }
        session = Session(config, guards=guards)
    except Exception as exc:  # noqa: BLE001 -- reported, exit 1
        c.error(f"{path}: {type(exc).__name__}: {exc}")
        raise SystemExit(1)

    commands = parse_events_arg(events, clock)
    if script:
        commands += json.loads(Path(script).read_text(encoding="utf-8"))
    scripted = bool(commands) or as_json or not c.interactive

    try:
        if scripted:
            run_script(session, commands)
            if as_json:
                c.print(json.dumps(session.to_json(), indent=2, default=str))
            else:
                c.blank()
                for rec in session.history:
                    render_step(rec)
                c.blank()
                render_state(session)
                if not commands:
                    c.blank()
                    c.info(
                        "no events given; use --events A,B,+500 or run in a terminal for interactive mode"
                    )
            return
        interactive(session)
    finally:
        session.stop()
        logging.disable(logging.NOTSET)
