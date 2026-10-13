"""📊 Preserve connected, labeled decisions in documentation diagrams.

These source contracts reject the alias/choice syntax that Mermaid silently
renders as two separate nodes. They supplement, not replace, visual browser
checks of the rendered labels, branch arrows, and light/dark themes.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

# -------------------------------------------------------------------------
# 📥 Third-Party Imports
# -------------------------------------------------------------------------
import pytest

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
