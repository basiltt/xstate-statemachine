"""📊 Preserve connected, labeled decisions in documentation diagrams.

These source contracts reject the alias/choice syntax that Mermaid silently
renders as two separate nodes. They supplement, not replace, visual browser
checks of the rendered labels, branch arrows, and light/dark themes.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import ast
import re
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# -------------------------------------------------------------------------
# 📥 Third-Party Imports
# -------------------------------------------------------------------------
import pytest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine import create_machine

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ALIASED_CHOICE = re.compile(
    r'(?m)^[ \t]*state[ \t]+"[^"\n]*"[ \t]+as[ \t]+' r"\S+[ \t]*<<choice>>"
)


def _diagrams(path: Path) -> List[str]:
    """Read fenced Mermaid blocks, not surrounding prose or code samples."""
    return re.findall(
        r"(?ms)^```mermaid[^\n]*\n(.*?)^```[ \t]*$",
        path.read_text(encoding="utf-8"),
    )


def test_no_aliased_choice_declarations_in_documentation() -> None:
    """An aliased choice silently detaches its diamond and loses its label."""
    scanned = 0
    for path in [ROOT / "README.md", *sorted(DOCS.rglob("*.md"))]:
        for diagram in _diagrams(path):
            scanned += 1
            assert not ALIASED_CHOICE.search(diagram), path
    assert scanned > 0, "No Mermaid source was checked"


@pytest.mark.parametrize(
    "source, invalid",
    [
        ('state "guard: canCheckout?" as g <<choice>>', True),
        ('  state "known event?" as known <<choice>>', True),
        ('\tstate "queue has room?" as room<<choice>>', True),
        ("state choice <<choice>>", False),
        ('state "a normal labeled state" as normal', False),
        ('known{"known event?"}', False),
    ],
)
def test_aliased_choice_contract(source: str, invalid: bool) -> None:
    """Reject the broken combined form without banning supported choices."""
    assert bool(ALIASED_CHOICE.search(source)) is invalid


@pytest.mark.parametrize(
    "page, decisions, edges",
    [
        (
            "guards",
            {"g": "guard: canCheckout?"},
            {
                ("start", "", "cart"),
                ("cart", "CHECKOUT", "g"),
                ("g", "✅ items > 0", "payment"),
                ("g", "❌ empty (stays put)", "cart"),
            },
        ),
        (
            "reliability",
            {"known": "known event?", "room": "queue has room?"},
            {
                ("ev", "", "known"),
                ("known", "no · strict=True", "unk"),
                ("known", "yes", "room"),
                ("room", "no · RAISE / BLOCK / DROP_NEWEST", "ovf"),
                ("room", "yes", "guard"),
                ("guard", "guard raised", "gep"),
                ("guard", "passed", "act"),
                ("act", "action raised", "aep"),
                ("act", "ok", "done"),
                ("done", "Receipt(changed=True)", "finish"),
            },
        ),
    ],
)
def test_decisions_keep_their_labels_and_branches(
    page: str,
    decisions: Dict[str, str],
    edges: Set[Tuple[str, str, str]],
) -> None:
    """Keep every condition and branch while using labeled decision nodes."""
    diagram = _diagrams(DOCS / "_guide" / f"{page}.md")[0]
    assert diagram.startswith("flowchart ")
    assert dict(re.findall(r'(\w+)\{"([^"\n]+)"\}', diagram)) == decisions
    actual_edges = re.findall(
        r'(?m)^[ \t]*(\w+)[ \t]+-->(?:\|"([^"\n]*)"\|)?' r"[ \t]+(\w+)[ \t]*$",
        diagram,
    )
    assert len(actual_edges) == len(edges)
    assert set(actual_edges) == edges
    for decision in decisions:
        assert any(target == decision for _, _, target in actual_edges)
        assert sum(source == decision for source, _, _ in actual_edges) == 2


def test_actor_labels_have_separate_return_paths() -> None:
    """Preserve every actor/message while using the reviewed layout."""
    diagram = _diagrams(DOCS / "_guide" / "actors.md")[0]
    assert diagram.startswith("flowchart LR\n")
    assert diagram.count('"spawn_worker"') == 3
    assert diagram.count('"send to parent"') == 3
    for actor in ("A", "B", "C"):
        assert f'P -- "spawn_worker" --> {actor}[' in diagram
        assert f'{actor} -. "send to parent" .-> P' in diagram


@pytest.mark.parametrize(
    "recipe, edges",
    [
        (
            "circuit-breaker-retry",
            {
                "[*] --> idle",
                "idle --> attempting: GET(url)",
                "attempting --> succeeded: done / retryReset",
                "attempting --> failed: error [notRetryable]",
                "attempting --> retrying: error / retryBump",
                "retrying --> attempting: after retryDelay [retryCanRetry]",
                "retrying --> failed: after retryDelay",
            },
        ),
        (
            "slot-filling",
            {
                "[*] --> collecting",
                "collecting --> collecting: USER_SAID / fillSlots (re-enter)",
                "collecting --> confirming: always [allSlotsFilled]",
                "collecting --> silent: after 30s",
                "silent --> collecting: always [canNudge] / nudge",
                "silent --> abandoned: always",
                "confirming --> booked: YES",
                "confirming --> collecting: NO / clearSlots",
            },
        ),
    ],
)
def test_recipe_layout_preserves_every_transition(
    recipe: str, edges: Set[str]
) -> None:
    """Spacing changes must not lose a timer, action, guard, or self-loop."""
    diagram = _diagrams(DOCS / "_guide" / "recipes" / f"{recipe}.md")[0]
    assert "stateDiagram-v2\n  direction LR\n" in diagram
    actual = [line.strip() for line in diagram.splitlines() if "-->" in line]
    assert len(actual) == len(edges)
    assert set(actual) == edges
    if recipe == "slot-filling":
        # 📝 Renderer-supported frontmatter, not deprecated init directives.
        assert diagram.startswith("---\nconfig:\n  state:\n")
        assert "nodeSpacing: 80" in diagram
        assert "rankSpacing: 120" in diagram


def test_deep_link_targets_the_contained_profile_node() -> None:
    """Mermaid aliases are not XState's dotted transition-target paths."""
    diagram = _diagrams(DOCS / "_guide" / "hierarchical.md")[1]
    assert diagram.startswith("flowchart TB\n")
    assert 'subgraph app["app"]' in diagram
    logged_in = diagram.split('subgraph loggedIn["loggedIn"]', 1)[1]
    assert 'dashboard -->|"GO_PROFILE"| profile' in logged_in.split("end")[0]
    assert 'profile -->|"BACK"| dashboard' in logged_in.split("end")[0]
    assert 'loggedIn -->|"LOGOUT"| loggedOut' in diagram
    assert 'loggedOut -->|"DEEP_LINK"| profile' in diagram
    assert "loggedIn.profile" not in diagram


def _documented_configs(body: str) -> Dict[str, Dict[str, Any]]:
    """Read literal configurations without executing documentation code."""
    configs = {}
    for block in re.findall(r"(?ms)^```python\n(.*?)^```[ \t]*$", body):
        for statement in ast.parse(block).body:
            if not isinstance(statement, ast.Assign):
                continue
            if not any(
                isinstance(target, ast.Name) and target.id == "config"
                for target in statement.targets
            ):
                continue
            value = ast.literal_eval(statement.value)
            configs[value["id"]] = value
    for name, initial, edges in (
        (
            "doorLock",
            "locked",
            [("locked", "UNLOCK", "unlocked"), ("unlocked", "LOCK", "locked")],
        ),
        ("switch", "idle", [("idle", "START", "running")]),
    ):
        states: Dict[str, Any] = {}
        for source, event, target in edges:
            states.setdefault(source, {}).setdefault("on", {})[event] = target
            states.setdefault(target, {})
        configs[name] = {"id": name, "initial": initial, "states": states}
    return configs


def test_documented_mermaid_outputs_match_the_exporter() -> None:
    """Check all API samples and the nested GitHub README fence verbatim."""
    body = (DOCS / "_guide" / "diagrams.md").read_text(encoding="utf-8")
    configs = _documented_configs(body)
    samples = re.findall(
        r"(?ms)^```(?:mermaid)?[ \t]*\n(stateDiagram-v2.*?)^```[ \t]*$",
        body,
    )
    assert len(samples) == 5
    names = []
    for sample in samples:
        root = re.search(r'(?m)^state "(\w+)" as \w+ \{', sample)
        assert root is not None
        name = root.group(1)
        names.append(name)
        assert sample.strip() == create_machine(configs[name]).to_mermaid()
    assert sorted(names) == [
        "doorLock",
        "player",
        "switch",
        "trafficLight",
        "trafficLight",
    ]
    assert "overall entry arrow points to that wrapper" in body
    assert "Mermaid alias limitation" in body
    assert "Repeated local keys in different parents are ambiguous" in body
