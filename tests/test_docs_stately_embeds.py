"""The Stately embeds on the docs site (#412 follow-up).

Every ``<div class="stately" data-machine="KEY">`` in docs/ must resolve to a
machine id in the served map, the map must point at the public project, and
the layout must load the script that turns the divs into theme-following
iframes.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MAP = DOCS / "assets" / "data" / "stately.json"
DIV = re.compile(r'<div class="stately" data-machine="([^"]+)"')
UUID = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")


def _has_edge(node) -> bool:
    """Any ``on``/``after``/``always``/``invoke`` at this node or below."""
    if any(k in node for k in ("on", "after", "always", "invoke")):
        return True
    return any(
        _has_edge(s)
        for s in (node.get("states") or {}).values()
        if isinstance(s, dict)
    )


def _pages():
    for md in DOCS.rglob("*.md"):
        if "superpowers" in md.parts or "research" in md.parts:
            continue
        yield md


class TestStatelyEmbeds(unittest.TestCase):
    def setUp(self) -> None:
        self.map = json.loads(MAP.read_text(encoding="utf-8"))

    def test_map_points_at_the_public_project(self) -> None:
        self.assertEqual(
            self.map["project"], "4dbe1227-e533-4104-9772-dd7c7b3a86df"
        )
        for key, mid in self.map["machines"].items():
            self.assertRegex(mid, UUID, key)

    def test_every_embed_resolves(self) -> None:
        seen = 0
        for md in _pages():
            for key in DIV.findall(md.read_text(encoding="utf-8")):
                seen += 1
                self.assertIn(key, self.map["machines"], f"{md}: {key}")
        self.assertGreater(seen, 100, "embeds went missing")

    def test_layout_loads_the_script_and_follows_the_theme(self) -> None:
        layout = (DOCS / "_layouts" / "default.html").read_text("utf-8")
        self.assertIn("assets/js/stately.js", layout)
        js = (DOCS / "assets" / "js" / "stately.js").read_text("utf-8")
        self.assertIn("colorMode=", js)
        self.assertIn("MutationObserver", js)
        self.assertIn("data-theme", js)

    def test_no_published_chart_is_a_fragment_or_a_lone_box(self) -> None:
        """A fragment (no root id/initial) draws as unconnected boxes in
        Stately; a one-state chart with no transitions draws as one box.
        Neither helps a reader, so neither may be embedded."""
        inv = json.loads(
            (
                ROOT / "scripts" / "stately" / "machine_inventory.json"
            ).read_text("utf-8")
        )
        readme = json.loads(
            (
                DOCS / "assets" / "images" / "machines" / "machines.json"
            ).read_text("utf-8")
        )
        for key in self.map["machines"]:
            if key in inv:
                cfg = inv[key]["config"]
            else:
                cfg = readme[key]  # the README chart sources
                cfg = cfg.get("config", cfg)
            self.assertIsInstance(cfg.get("id"), str, key)
            self.assertTrue(
                "initial" in cfg or cfg.get("type") == "parallel", key
            )
            states = cfg.get("states") or {}
            self.assertTrue(len(states) >= 2 or _has_edge(cfg), key)

    def test_gallery_covers_every_shipped_example_machine(self) -> None:
        gallery = (DOCS / "_guide" / "example-gallery.md").read_text("utf-8")
        inv = json.loads(
            (
                ROOT / "scripts" / "stately" / "machine_inventory.json"
            ).read_text("utf-8")
        )
        for key, e in inv.items():
            if key not in self.map["machines"]:
                continue
            if any(w.startswith("examples/") for w in e["where"]):
                self.assertIn(f'data-machine="{key}"', gallery, e["where"])


if __name__ == "__main__":
    unittest.main()
