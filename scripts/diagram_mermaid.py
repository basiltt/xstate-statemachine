"""Stately-style Mermaid for the statecharts embedded in the docs.

``to_stately_mermaid(config)`` turns one XState JSON machine into a Mermaid
``stateDiagram-v2`` whose labels are small HTML fragments styled by
``docs/assets/css/style.css`` (the ``xsm-*`` classes) so the rendered
chart reads like the Stately editor: bold state titles, ``entry /`` and
``exit /`` rows with action chips, an ``invoke`` row, event pills on the
transitions with ``if guard`` / ``else`` and action chips, numbered
alternatives for one event, ``done:`` / ``error:`` pills for invoked
services, ``after`` pills for delays, a final-state mark, dashed regions
for parallel states.

📝 Why not ``MachineNode.to_mermaid()``?  That exporter is the library's
public, plain-text Mermaid (documented in the diagrams guide and pinned by
tests). The docs embeds need richer, Stately-like output, which is a
presentation concern of the site, so it lives here with the docs tooling.

🏛️ Design notes (each one is a Mermaid 11 constraint found by rendering):

* A composite state cannot carry description rows ("Group nodes can only
  have label"), so a compound state's entry/exit/invoke/internal rows
  become chips in its title line instead.
* Two self-loops on one state collapse into one edge and the surviving
  label is placed over its neighbours; an edge between a composite state
  and one of its own descendants aborts the render. So every transition
  that stays inside its source (targetless, self-target, a target up or
  down its own branch) is drawn as a row inside the state box, never as
  an edge.
* Markdown strings are not supported in state diagrams; HTML labels are,
  and their size is measured with the page CSS applied, as long as the
  classes are not scoped under the diagram's root (the measurement happens
  before Mermaid adds the ``statediagram`` class).
* Label text is escaped with Mermaid's own ``#NN;`` entities: an HTML
  ``&lt;``-style entity ends the statement at its ``;`` and ``&#35;`` is
  re-encoded by Mermaid's entity pass.
* Parallel regions are nested composite states with a dashed class rather
  than ``--`` dividers, which draw a second box around every region.
* Stately lays a small linear machine out left to right and everything
  else top to bottom; ``default_direction`` follows that.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import json
import logging
import pathlib
import re
import sys
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine import MachineLogic  # noqa: E402
from xstate_statemachine.exceptions import StateNotFoundError  # noqa: E402
from xstate_statemachine.models import (  # noqa: E402
    ActionDefinition,
    GuardDefinition,
    InvokeDefinition,
    MachineNode,
    StateNode,
    TransitionDefinition,
)
from xstate_statemachine.resolver import resolve_target_state  # noqa: E402

STATELY_PROJECT = "4dbe1227-e533-4104-9772-dd7c7b3a86df"
LAYOUT_FILE = ROOT / "scripts" / "stately" / "diagram_layout.json"
DATA_FILE = ROOT / "docs" / "assets" / "data" / "diagrams.json"
DIRECTIONS = ("TB", "LR")
#: A flat machine with at most this many states and no more transitions
#: than states reads as a strip, which is how Stately lays it out.
SMALL_CHAIN_STATES = 3

_CLASS_DEFS = {
    "xsmParallel": "stroke-dasharray:0",
    "xsmRegion": "stroke-dasharray:5 4",
    "xsmHistory": "stroke-dasharray:3 3",
}

Row = Tuple[str, str]  # (html for a description row, plain text for a chip)


def machine_from_config(config: Dict[str, Any]) -> MachineNode:
    """Parse *config* without requiring any action/guard/service code.

    📝 ``create_machine`` insists on implementations; the diagram only
    needs the parsed tree, which ``MachineNode`` builds from the JSON.
    """
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        return MachineNode(config, MachineLogic())
    finally:
        logging.disable(previous)


# -------------------------------------------------------------------------
# 🧩 Label fragments
# -------------------------------------------------------------------------
def _esc(text: Any) -> str:
    """Escape *text* for a Mermaid HTML label with Mermaid's ``#NN;``
    entities (see the module notes); line breaks become spaces."""
    out = re.sub(r"[\r\n\t]+", " ", str(text))
    return re.sub(r"[&<>\"'#%;{}]", lambda m: f"#{ord(m.group())};", out)


def _kw(text: str) -> str:
    """An italic keyword: ``after``, ``done:``, ``error:``, ``always``."""
    return f"<span class='xsm-kw'>{_esc(text)}</span>"


def _sec(text: str) -> str:
    """A section label inside a state: ``entry /``, ``exit /``, ``invoke``,
    ``on`` (Stately's "Entry actions" / "Invoke" headings)."""
    return f"<span class='xsm-sec'>{_esc(text)}</span>"


def _if(text: str) -> str:
    """Stately's small-caps ``IF`` / ``ELSE`` guard marker."""
    return f"<span class='xsm-if'>{_esc(text)}</span>"


def _ev(text: str) -> str:
    return f"<span class='xsm-ev'>{_esc(text)}</span>"


def _chip(text: str, extra: str = "") -> str:
    cls = "xsm-chip" + (f" {extra}" if extra else "")
    return f"<span class='{cls}'>{_esc(text)}</span>"


def _chips(actions: Sequence[ActionDefinition]) -> str:
    return " ".join(_chip(_action_text(a)) for a in actions)


def _names(actions: Sequence[ActionDefinition]) -> str:
    return ", ".join(_action_text(a) for a in actions)


def _pill(head: str, actions: Sequence[ActionDefinition]) -> str:
    inner = head + (f"<br/>{_chips(actions)}" if actions else "")
    return f"<span class='xsm-pill'>{inner}</span>"


def _badge(index: int, count: int) -> str:
    """``1`` / ``2`` … in front of the alternatives of one event."""
    return f"<span class='xsm-num'>{index + 1}</span> " if count > 1 else ""


def _action_text(action: ActionDefinition) -> str:
    """``raise FOO`` / ``sendTo FOO`` for the event-carrying built-ins, the
    action type otherwise (``assign``, ``log``, a user action name)."""
    params = action.params if isinstance(action.params, dict) else {}
    event = params.get("event")
    if isinstance(event, dict):
        event = event.get("type")
    if (
        action.type in ("raise", "sendTo", "sendParent", "escalate")
        and isinstance(event, str)
        and event
    ):
        return f"{action.type} {event}"
    return action.type


def _guard_text(guard: Any) -> Optional[str]:
    """The guard as Stately shows it: its name, ``and(a, b)`` for a
    composite, ``in <state>`` for the built-in ``stateIn`` guard.

    📝 ``TransitionDefinition.guard`` is the guard's display string; a
    ``GuardDefinition`` is accepted too for callers that hold one.
    """
    if guard is None or guard == "":
        return None
    if isinstance(guard, str):
        return guard
    if not isinstance(guard, GuardDefinition):
        return str(guard)
    if guard.is_composite:
        inner = ", ".join(_guard_text(c) or "?" for c in guard.children)
        return f"{guard.type}({inner})"
    if guard.is_state_in:
        params = guard.params if isinstance(guard.params, dict) else {}
        state = params.get("state") or params.get("stateValue")
        return f"in {state}" if state else "in"
    return guard.type


def _guard_of(transition: TransitionDefinition) -> Any:
    """The parsed guard when the transition kept one, else its name."""
    return getattr(transition, "guard_def", None) or transition.guard


def _condition(
    transition: TransitionDefinition, index: int, count: int
) -> Tuple[str, str]:
    """``(html, plain)`` for the guard part of a label: ``if guard``, or
    ``else`` for an unguarded alternative that follows guarded ones."""
    guard = _guard_text(_guard_of(transition))
    if guard:
        return f" {_if('if')} {_esc(guard)}", f" if {guard}"
    if count > 1 and index > 0:
        return f" {_if('else')}", " else"
    return "", ""


def format_delay(delay: Any) -> str:
    """``15000 ms`` for a numeric delay (as Stately prints it); a named
    delay is kept as is (``BACKOFF``)."""
    if isinstance(delay, bool) or not isinstance(delay, (int, float)):
        return str(delay)
    if float(delay).is_integer():
        return f"{int(delay)} ms"
    return f"{delay:g} ms"


def _invoke_text(invoke: InvokeDefinition) -> str:
    src = invoke.src or invoke.id
    if invoke.id_is_explicit and invoke.id != src:
        return f"{src} #{invoke.id}"
    return str(src)


def _state_title(node: StateNode, chips: Iterable[str] = ()) -> str:
    mark = "<span class='xsm-final'></span>" if node.type == "final" else ""
    label = node.key if node.parent is not None else (node.id or node.key)
    if node.type == "history":
        # Stately: an "H" badge in front of the history state's own name.
        badge = "H*" if node.history == "deep" else "H"
        mark = f"<span class='xsm-num xsm-hist'>{badge}</span> "
    title = f"<span class='xsm-title'>{mark}{_esc(label)}</span>"
    extra = " ".join(chips)
    return f"{title} {extra}" if extra else title


# -------------------------------------------------------------------------
# 🧮 Transition classification
# -------------------------------------------------------------------------
def _targets(
    transition: TransitionDefinition, source: StateNode
) -> List[StateNode]:
    """Every resolved target of *transition* (none for a targetless one)."""
    if not transition.target_str:
        return []
    if transition.resolved_targets:
        return list(transition.resolved_targets)
    out: List[StateNode] = []
    for target in transition.target_strs or (transition.target_str,):
        try:
            out.append(resolve_target_state(target, source))
        except StateNotFoundError as exc:
            # 📝 A validated machine never gets here; an unresolvable target
            #    must fail the build, not vanish from the chart.
            raise ValueError(
                f"{source.id}: cannot resolve target {target!r}"
            ) from exc
    return out


def _is_within(node: StateNode, ancestor: StateNode) -> bool:
    cursor: Optional[StateNode] = node
    while cursor is not None:
        if cursor is ancestor:
            return True
        cursor = cursor.parent
    return False


def _split_targets(
    transition: TransitionDefinition, source: StateNode
) -> Tuple[List[StateNode], List[StateNode]]:
    """``(inside, outside)``: targets on *source*'s own branch (itself, an
    ancestor or a descendant) are drawn as rows, the rest as edges."""
    inside: List[StateNode] = []
    outside: List[StateNode] = []
    for target in _targets(transition, source):
        if _is_within(target, source) or _is_within(source, target):
            inside.append(target)
        else:
            outside.append(target)
    return inside, outside


# -------------------------------------------------------------------------
# 🧾 Rows (atomic / final states) and title chips (composite states)
# -------------------------------------------------------------------------
def _inside_row(
    head: str,
    plain: str,
    transition: TransitionDefinition,
    node: StateNode,
    index: int = 0,
    count: int = 1,
) -> Optional[Row]:
    """A row for a transition that stays on *node*'s branch, or ``None``
    when every target lies elsewhere (it is an edge then)."""
    inside, outside = _split_targets(transition, node)
    if transition.target_str and not inside:
        return None
    cond_html, cond_plain = _condition(transition, index, count)
    head = _badge(index, count) + head + cond_html
    plain += cond_plain
    for target in inside:
        arrow = "↻ self" if target is node else f"→ {target.key}"
        head += f" {_kw(arrow)}"
        plain += f" {arrow}"
    if transition.actions:
        head += f" {_kw('/')} {_chips(transition.actions)}"
        plain += f" / {_names(transition.actions)}"
    return head, plain


def _row_items(node: StateNode) -> List[Row]:
    """What happens *inside* the state: entry/exit actions, invoked
    services, and the transitions that do not leave its branch."""
    items: List[Row] = []
    if node.entry:
        items.append(
            (
                f"{_sec('entry /')} {_chips(node.entry)}",
                f"entry / {_names(node.entry)}",
            )
        )
    if node.exit:
        items.append(
            (
                f"{_sec('exit /')} {_chips(node.exit)}",
                f"exit / {_names(node.exit)}",
            )
        )
    for invoke in node.invoke:
        text = _invoke_text(invoke)
        items.append(
            (
                f"{_sec('invoke')} {_chip(text, 'xsm-chip-invoke')}",
                f"invoke {text}",
            )
        )
    for event, transitions in node.on.items():
        count = len(transitions)
        for index, t in enumerate(transitions):
            if event == "":
                head, plain = _kw("always"), "always"
            else:
                head, plain = f"{_sec('on')} {_ev(event)}", f"on {event}"
            row = _inside_row(head, plain, t, node, index, count)
            if row:
                items.append(row)
    for delay, transitions in node.after.items():
        text = format_delay(delay)
        count = len(transitions)
        for index, t in enumerate(transitions):
            row = _inside_row(
                f"{_kw('after')} {_esc(text)}",
                f"after {text}",
                t,
                node,
                index,
                count,
            )
            if row:
                items.append(row)
    for invoke in node.invoke:
        text = _invoke_text(invoke)
        for kind, transitions in (
            ("done", invoke.on_done),
            ("error", invoke.on_error),
        ):
            dot = f"<span class='xsm-dot xsm-dot-{kind}'></span>"
            count = len(transitions)
            for index, t in enumerate(transitions):
                row = _inside_row(
                    f"{dot}{_kw(kind + ':')} {_esc(text)}",
                    f"{kind}: {text}",
                    t,
                    node,
                    index,
                    count,
                )
                if row:
                    items.append(row)
    count = len(node.on_done_transitions)
    for index, t in enumerate(node.on_done_transitions):
        row = _inside_row(_kw("onDone"), "onDone", t, node, index, count)
        if row:
            items.append(row)
    return items


# -------------------------------------------------------------------------
# 🔗 Edges
# -------------------------------------------------------------------------
def _edges(node: StateNode) -> List[Tuple[StateNode, StateNode, str]]:
    """``(source, target, label_html)`` for every transition that leaves
    *node*'s branch (the others are rows, see above)."""
    out: List[Tuple[StateNode, StateNode, str]] = []

    def add(
        t: TransitionDefinition, head: str, index: int = 0, count: int = 1
    ) -> None:
        _, outside = _split_targets(t, node)
        if not outside:
            return
        cond_html, _ = _condition(t, index, count)
        label = _pill(_badge(index, count) + head + cond_html, t.actions)
        for target in outside:
            out.append((node, target, label))

    for event, transitions in node.on.items():
        for index, t in enumerate(transitions):
            head = _kw("always") if event == "" else _ev(event)
            add(t, head, index, len(transitions))
    for index, t in enumerate(node.on_done_transitions):
        add(t, _kw("onDone"), index, len(node.on_done_transitions))
    for delay, transitions in node.after.items():
        head = f"{_kw('after')} {_esc(format_delay(delay))}"
        for index, t in enumerate(transitions):
            add(t, head, index, len(transitions))
    for invoke in node.invoke:
        text = _esc(_invoke_text(invoke))
        for kind, transitions in (
            ("done", invoke.on_done),
            ("error", invoke.on_error),
        ):
            dot = f"<span class='xsm-dot xsm-dot-{kind}'></span>"
            for index, t in enumerate(transitions):
                add(
                    t,
                    f"{dot}{_kw(kind + ':')} {text}",
                    index,
                    len(transitions),
                )
    return out


# -------------------------------------------------------------------------
# 🏗️ Diagram assembly
# -------------------------------------------------------------------------
class _Aliases:
    """Collision-free Mermaid identifiers for every state node."""

    def __init__(self) -> None:
        self._by_id: Dict[str, str] = {}
        self._used: set = set()

    def of(self, node: StateNode) -> str:
        alias = self._by_id.get(node.id)
        if alias is None:
            base = re.sub(r"\W+", "_", node.id).strip("_") or "state"
            if base[0].isdigit():
                base = "s_" + base
            alias, n = base, 1
            while alias in self._used:
                n += 1
                alias = f"{base}_{n}"
            self._used.add(alias)
            self._by_id[node.id] = alias
        return alias


def _walk(node: StateNode) -> Iterable[StateNode]:
    yield node
    for child in node.states.values():
        yield from _walk(child)


def _initial_child(node: StateNode) -> Optional[StateNode]:
    initial = node.initial
    if isinstance(initial, (list, tuple)):
        initial = initial[0] if initial else None
    if isinstance(initial, str):
        return node.states.get(initial)
    return None


def default_direction(config: Dict[str, Any]) -> str:
    """``LR`` for a small flat chain, ``TB`` otherwise (Stately's habit)."""
    states = config.get("states") or {}
    if not isinstance(states, dict) or len(states) > SMALL_CHAIN_STATES:
        return "TB"
    edges = 0
    for state in states.values():
        if not isinstance(state, dict):
            return "TB"
        if state.get("states") or state.get("type") == "parallel":
            return "TB"
        for key in ("on", "after"):
            value = state.get(key) or {}
            for alternatives in (
                value.values() if isinstance(value, dict) else []
            ):
                edges += (
                    len(alternatives) if isinstance(alternatives, list) else 1
                )
        invoke = state.get("invoke")
        if invoke:
            edges += len(invoke) if isinstance(invoke, list) else 1
    return "LR" if edges <= len(states) else "TB"


def compound_ids(config: Dict[str, Any]) -> List[str]:
    """Ids of the compound/parallel states below the root, in document
    order: the keys ``composite_directions`` accepts."""
    machine = machine_from_config(config)
    return [n.id for n in _walk(machine) if n.states and n is not machine]


def to_stately_mermaid(
    config: Dict[str, Any],
    *,
    direction: Optional[str] = None,
    composite_directions: Optional[Dict[str, str]] = None,
) -> str:
    """Render *config* as Stately-style Mermaid source.

    Args:
        config: One XState JSON machine (a whole machine, not a fragment).
        direction: ``TB`` or ``LR`` for the top level; ``None`` picks
            :func:`default_direction`.
        composite_directions: Optional ``{state_id: "LR"|"TB"}`` overrides
            for individual compound states.

    Returns:
        Mermaid ``stateDiagram-v2`` text.
    """
    machine = machine_from_config(config)
    aliases = _Aliases()
    overrides = composite_directions or {}
    classes: List[Tuple[str, str]] = []
    top = direction if direction in DIRECTIONS else default_direction(config)
    lines: List[str] = ["stateDiagram-v2", f"direction {top}"]

    def emit(node: StateNode, depth: int) -> None:
        pad = "  " * depth
        alias = aliases.of(node)
        items = _row_items(node)
        if node.states:
            chips = [_chip(plain) for _, plain in items]
            lines.append(
                f'{pad}state "{_state_title(node, chips)}" as {alias} {{'
            )
            # 📝 Mermaid applies a direction to the block it is written in,
            #    so the machine box repeats the top-level one.
            sub = overrides.get(node.id) or (top if depth == 0 else None)
            if sub in DIRECTIONS:
                lines.append(f"{pad}  direction {sub}")
            first = _initial_child(node)
            if node.type != "parallel" and first is not None:
                lines.append(f"{pad}  [*] --> {aliases.of(first)}")
            for child in node.states.values():
                emit(child, depth + 1)
            lines.append(f"{pad}}}")
            if node.type == "parallel":
                classes.append((alias, "xsmParallel"))
            elif node.parent is not None and node.parent.type == "parallel":
                classes.append((alias, "xsmRegion"))
        else:
            lines.append(f'{pad}state "{_state_title(node)}" as {alias}')
            for row, _ in items:
                lines.append(f"{pad}{alias} : {row}")
            if node.type == "history":
                classes.append((alias, "xsmHistory"))
            elif node.parent is not None and node.parent.type == "parallel":
                classes.append((alias, "xsmRegion"))

    emit(machine, 0)
    for node in _walk(machine):
        for source, target, label in _edges(node):
            lines.append(
                f"{aliases.of(source)} --> {aliases.of(target)} : {label}"
            )
    for alias, cls in classes:
        lines.append(f"class {alias} {cls}")
    for cls in sorted({c for _, c in classes}):
        lines.append(f"classDef {cls} {_CLASS_DEFS[cls]}")
    return "\n".join(lines) + "\n"


# -------------------------------------------------------------------------
# 📦 The served asset
# -------------------------------------------------------------------------
def load_layout() -> Dict[str, Dict[str, Any]]:
    """Per-chart layout overrides chosen by ``scripts/check_diagrams.py``."""
    if LAYOUT_FILE.exists():
        return json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))
    return {}


def render_entry(
    key: str, config: Dict[str, Any], layout: Dict[str, Dict[str, Any]]
) -> str:
    """Mermaid text for one inventory *key* honouring its layout override."""
    chart = layout.get(key, {})
    direction = chart.get("direction")
    if direction not in DIRECTIONS:
        direction = None
    return to_stately_mermaid(
        config,
        direction=direction,
        composite_directions=chart.get("composites"),
    )


def build_asset(
    inventory: Dict[str, Dict[str, Any]],
    stately_ids: Dict[str, str],
    keys: Iterable[str],
    titles: Dict[str, str],
) -> Dict[str, Any]:
    """The ``diagrams.json`` payload: project id plus, per embedded key, the
    Stately machine id, the chart title and the Mermaid text."""
    layout = load_layout()
    machines: Dict[str, Dict[str, Any]] = {}
    for key in sorted(keys):
        config = inventory[key]["config"]
        machines[key] = {
            "id": stately_ids.get(key),
            "title": titles.get(key) or config.get("id") or key,
            "mermaid": render_entry(key, config, layout),
        }
    return {"project": STATELY_PROJECT, "machines": machines}
