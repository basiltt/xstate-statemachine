"""🧪 Mermaid export retains leaf membership without changing execution.

Explicit leaf declarations prevent Mermaid from placing implicit transition
targets outside their actual compound/parallel parents. These tests check
the emitted structure and public consumers; rendering is verified separately
in the documentation browser audit. Local-key alias collisions are an
existing limitation, not a feature repaired by this targeted change.
"""

from __future__ import annotations

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import copy
import io
import json
import re
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Tuple

# -------------------------------------------------------------------------
# 📦 Third-Party Imports
# -------------------------------------------------------------------------
import pytest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from src.xstate_statemachine import SyncInterpreter, create_machine
from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.analysis import analyse
from src.xstate_statemachine.cli.commands.diagram import render_diagram
from src.xstate_statemachine.cli.commands.docs import render_markdown
from src.xstate_statemachine.validation import walk


def _traffic_light() -> Dict[str, Any]:
    return {
        "id": "trafficLight",
        "initial": "red",
        "states": {
            "red": {"on": {"TIMER": "green"}},
            "green": {"on": {"TIMER": "yellow"}},
            "yellow": {"on": {"TIMER": "red"}},
        },
    }


def _compound() -> Dict[str, Any]:
    return {
        "id": "workflow",
        "initial": "working",
        "states": {
            "working": {
                "initial": "prepare",
                "states": {
                    "prepare": {"on": {"FINISH": "finished"}},
                    "finished": {"type": "final"},
                    "unused": {},
                },
                "onDone": "completed",
            },
            "completed": {"type": "final"},
        },
    }


def _parallel() -> Dict[str, Any]:
    return {
        "id": "player",
        "initial": "playing",
        "states": {
            "playing": {
                "type": "parallel",
                "states": {
                    "video": {
                        "initial": "loading",
                        "states": {
                            "loading": {"on": {"VIDEO_READY": "streaming"}},
                            "streaming": {"on": {"BUFFER": "loading"}},
                        },
                    },
                    "audio": {
                        "initial": "muted",
                        "states": {
                            "muted": {"on": {"UNMUTE": "audible"}},
                            "audible": {"on": {"MUTE": "muted"}},
                        },
                    },
                },
                "on": {"STOP": "stopped"},
            },
            "stopped": {},
        },
    }


def _declared_paths(source: str) -> List[Tuple[str, ...]]:
    """Read explicit declarations, including their enclosing state blocks."""
    stack: List[str] = []
    paths: List[Tuple[str, ...]] = []
    for line in source.splitlines():
        match = re.fullmatch(r'\s*state "([^"]+)" as ([^\s{}]+)( \{)?', line)
        if match:
            label, alias, composite = match.groups()
            assert label == alias
            paths.append(tuple(stack + [label]))
            if composite:
                stack.append(label)
        elif line.strip() == "}":
            stack.pop()
    assert not stack
    return paths


def _node_path(node: Any) -> Tuple[str, ...]:
    path: List[str] = []
    while node is not None:
        path.append(node.key)
        node = node.parent
    return tuple(reversed(path))


@pytest.mark.parametrize(
    "config", [_traffic_light(), _compound(), _parallel()]
)
def test_every_node_is_declared_inside_its_actual_parent(
    config: Dict[str, Any],
) -> None:
    machine = create_machine(copy.deepcopy(config))
    assert _declared_paths(machine.to_mermaid()) == [
        _node_path(node) for node in walk(machine)
    ]


def test_unreachable_atomic_and_final_leaves_are_not_dropped() -> None:
    machine = create_machine(
        {
            "id": "invoice",
            "initial": "draft",
            "states": {
                "draft": {},
                "archived": {"type": "final"},
                "unreachable": {},
            },
        }
    )
    assert machine.to_mermaid().splitlines() == [
        "stateDiagram-v2",
        "[*] --> invoice",
        'state "invoice" as invoice {',
        "    [*] --> draft",
        '    state "draft" as draft',
        '    state "archived" as archived',
        '    state "unreachable" as unreachable',
        "}",
    ]


def test_atomic_root_is_declared_without_inventing_an_initial_child() -> None:
    machine = create_machine({"id": "standalone", "states": {}})
    assert machine.to_mermaid() == (
        'stateDiagram-v2\nstate "standalone" as standalone'
    )


def test_outer_initial_edge_enters_root_then_its_initial_child() -> None:
    text = create_machine(_traffic_light()).to_mermaid()
    assert text.splitlines()[1] == "[*] --> trafficLight"
    assert text.count("[*] --> red") == 1
    assert "    [*] --> red" in text
    assert "\n[*] --> red" not in text


def test_compound_initials_and_on_done_edges_are_preserved() -> None:
    text = create_machine(_compound()).to_mermaid()
    assert [line for line in text.splitlines() if "[*] -->" in line] == [
        "[*] --> workflow",
        "    [*] --> working",
        "        [*] --> prepare",
    ]
    assert [line for line in text.splitlines() if " : " in line] == [
        "working --> completed : onDone",
        "prepare --> finished : FINISH",
    ]


def test_parallel_regions_and_existing_edge_labels_are_preserved() -> None:
    text = create_machine(_parallel()).to_mermaid()
    paths = _declared_paths(text)
    for path in (
        ("player", "playing", "video", "loading"),
        ("player", "playing", "video", "streaming"),
        ("player", "playing", "audio", "muted"),
        ("player", "playing", "audio", "audible"),
        ("player", "stopped"),
    ):
        assert path in paths
    assert [line for line in text.splitlines() if " : " in line] == [
        "playing --> stopped : STOP",
        "loading --> streaming : VIDEO_READY",
        "streaming --> loading : BUFFER",
        "muted --> audible : UNMUTE",
        "audible --> muted : MUTE",
    ]


def test_parallel_root_does_not_invent_a_single_initial_region() -> None:
    config = _parallel()["states"]["playing"]
    config.pop("on")
    config["id"] = "parallelRoot"
    machine = create_machine(config)
    assert machine.initial is None
    assert [
        line for line in machine.to_mermaid().splitlines() if "[*] -->" in line
    ] == [
        "        [*] --> loading",
        "        [*] --> muted",
    ]


def test_repeated_local_keys_retain_the_documented_alias_limitation() -> None:
    # 📝 This characterizes compatibility, not correct duplicate-key
    # rendering. Qualified IDs would require changes to existing consumers
    # such as Django's active-state class annotations as well.
    machine = create_machine(
        {
            "id": "duplicates",
            "initial": "left",
            "states": {
                side: {
                    "initial": "idle",
                    "states": {
                        "idle": {"on": {side.upper(): "done"}},
                        "done": {"type": "final"},
                    },
                }
                for side in ("left", "right")
            },
        }
    )
    text = machine.to_mermaid()
    assert text.count('state "idle" as idle') == 2
    assert text.count('state "done" as done') == 2
    assert "idle --> done : LEFT" in text
    assert "idle --> done : RIGHT" in text
    assert machine.states["left"].states["idle"].id == "duplicates.left.idle"
    assert machine.states["right"].states["idle"].id == "duplicates.right.idle"


def test_export_leaves_configuration_tree_and_plantuml_unchanged() -> None:
    config = _parallel()
    original_config = copy.deepcopy(config)
    machine = create_machine(config)
    nodes = [
        (node.id, node.type, node.initial, tuple(node.states))
        for node in walk(machine)
    ]
    plantuml = machine.to_plantuml()
    first = machine.to_mermaid()
    assert machine.to_mermaid() == first
    assert machine.source_config == original_config
    assert config == original_config
    assert [
        (node.id, node.type, node.initial, tuple(node.states))
        for node in walk(machine)
    ] == nodes
    assert machine.to_plantuml() == plantuml


def test_export_does_not_change_interpreter_execution() -> None:
    machine = create_machine(_traffic_light())
    machine.to_mermaid()
    interpreter = SyncInterpreter(machine).start()
    try:
        assert interpreter.active_state_ids == {"trafficLight.red"}
        interpreter.send("TIMER")
        assert interpreter.active_state_ids == {"trafficLight.green"}
    finally:
        interpreter.stop()


@pytest.mark.parametrize(
    "config", [_traffic_light(), _compound(), _parallel()]
)
def test_public_cli_matches_the_export_exactly(
    config: Dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "machine.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    expected = create_machine(copy.deepcopy(config)).to_mermaid()
    output = io.StringIO()
    monkeypatch.setattr(sys, "argv", ["xsm", "diagram", str(path), "--plain"])
    reset_console()
    try:
        with redirect_stdout(output):
            main()
    finally:
        reset_console()
    assert output.getvalue() == expected + "\n"


def test_diagram_api_and_generated_markdown_use_the_same_export(
    tmp_path: Path,
) -> None:
    config = _parallel()
    path = tmp_path / "player.json"
    path.write_text(json.dumps(config), encoding="utf-8")
    machine = create_machine(config)
    expected = machine.to_mermaid()
    assert render_diagram(machine, "mermaid") == expected
    markdown = render_markdown(analyse(path))
    diagram = re.search(r"```mermaid\n(.*?)\n```", markdown, re.DOTALL)
    assert diagram is not None
    assert diagram.group(1) == expected
