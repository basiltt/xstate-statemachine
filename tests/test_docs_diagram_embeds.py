"""The machine diagrams embedded in the docs site.

Every ``<div class="stately" data-machine="KEY">`` in docs/ must resolve to
an entry of the served asset (``docs/assets/data/diagrams.json``: the Stately
machine id, the title and Stately-style Mermaid for the chart), the asset
must be exactly what the generator produces from the inventory, and the
layout must load the renderer that draws the markers and links each one to
the same machine in the Stately editor.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSET = DOCS / "assets" / "data" / "diagrams.json"
RENDERER = DOCS / "assets" / "js" / "diagrams.js"
DIV = re.compile(r'<div class="stately" data-machine="([^"]+)"')
UUID = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$")
PROJECT = "4dbe1227-e533-4104-9772-dd7c7b3a86df"

# One Mermaid statement per line, as the generator writes them.
STATEMENT = re.compile(
    r"^(?:"
    r"stateDiagram-v2|"
    r"\s*direction (?:TB|LR)|"
    r'\s*state "[^"\n]+" as [A-Za-z_]\w*(?: \{)?|'
    r"\s*[A-Za-z_]\w* : .+|"
    r"\s*\[\*\] --> [A-Za-z_]\w*|"
    r"[A-Za-z_]\w* --> [A-Za-z_]\w* : <span class='xsm-pill'>.+</span>|"
    r"class [A-Za-z_]\w* xsm\w+|"
    r"classDef xsm\w+ .+|"
    r"\s*\}"
    r")$"
)


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


def _inventory():
    return json.loads(
        (ROOT / "scripts" / "stately" / "machine_inventory.json").read_text(
            "utf-8"
        )
    )


class TestDiagramAsset(unittest.TestCase):
    def setUp(self) -> None:
        self.asset = json.loads(ASSET.read_text(encoding="utf-8"))
        self.machines = self.asset["machines"]

    def test_asset_points_at_the_stately_project(self) -> None:
        self.assertEqual(self.asset["project"], PROJECT)
        self.assertGreater(len(self.machines), 200)
        for key, entry in self.machines.items():
            with self.subTest(key=key):
                self.assertRegex(entry["id"], UUID)
                self.assertIsInstance(entry["title"], str)
                self.assertTrue(entry["title"])
                self.assertTrue(entry["mermaid"].startswith("stateDiagram-v2"))

    def test_every_embed_resolves(self) -> None:
        seen = 0
        for md in _pages():
            for key in DIV.findall(md.read_text(encoding="utf-8")):
                seen += 1
                self.assertIn(key, self.machines, f"{md}: {key}")
        self.assertGreater(seen, 100, "embeds went missing")

    def test_mermaid_sources_are_well_formed(self) -> None:
        """Every line is a statement the generator emits, every alias is
        declared once, every transition joins two declared aliases."""
        for key, entry in self.machines.items():
            source = entry["mermaid"]
            with self.subTest(key=key):
                self.assertEqual(source.count("{"), source.count("}"))
                declared = re.findall(
                    r'state "[^"\n]+" as ([A-Za-z_]\w*)', source
                )
                self.assertEqual(
                    len(declared), len(set(declared)), "alias clash"
                )
                for line in source.rstrip("\n").split("\n"):
                    self.assertRegex(line, STATEMENT)
                for src, tgt in re.findall(
                    r"^([A-Za-z_]\w*) --> ([A-Za-z_]\w*) :", source, re.M
                ):
                    self.assertIn(src, declared)
                    self.assertIn(tgt, declared)
                self.assertNotIn("%%", source)

    def test_no_published_chart_is_a_fragment_or_a_lone_box(self) -> None:
        """A fragment (no root id/initial) has transitions pointing outside
        it; a one-state chart with no transitions is a single box. Neither
        helps a reader, so neither may be embedded."""
        inv = _inventory()
        for key in self.machines:
            cfg = inv[key]["config"]
            self.assertIsInstance(cfg.get("id"), str, key)
            self.assertTrue(
                "initial" in cfg or cfg.get("type") == "parallel", key
            )
            states = cfg.get("states") or {}
            self.assertTrue(len(states) >= 2 or _has_edge(cfg), key)

    def test_gallery_covers_every_shipped_example_machine(self) -> None:
        gallery = (DOCS / "_guide" / "example-gallery.md").read_text("utf-8")
        for key, e in _inventory().items():
            if key not in self.machines:
                continue
            if any(w.startswith("examples/") for w in e["where"]):
                self.assertIn(f'data-machine="{key}"', gallery, e["where"])

    def test_asset_is_exactly_what_the_generator_produces(self) -> None:
        """A generator or layout change must come with the regenerated
        asset (``python scripts/place_stately_embeds.py``)."""
        from scripts import diagram_mermaid as dm
        from scripts import place_stately_embeds as generator

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "diagrams.json"
            with patch.object(dm, "DATA_FILE", target):
                generator.write_map()
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                ASSET.read_text(encoding="utf-8"),
            )


class TestRenderer(unittest.TestCase):
    """The layout loads the module that draws markers and links to Stately."""

    def test_layout_loads_the_renderer_module(self) -> None:
        layout = (DOCS / "_layouts" / "default.html").read_text("utf-8")
        self.assertRegex(
            layout,
            r'<script type="module" src="\{\{ \'/assets/js/diagrams\.js\''
            r" \| relative_url \}\}\"></script>",
        )
        self.assertNotIn("stately.js", layout)
        self.assertNotIn("mermaid.esm", layout, "one renderer, one import")

    def test_renderer_draws_the_asset_and_links_every_chart_to_stately(
        self,
    ) -> None:
        js = RENDERER.read_text("utf-8")
        self.assertIn("'../data/diagrams.json'", js)
        self.assertIn(".stately[data-machine]", js)
        self.assertIn("https://stately.ai/registry/editor/", js)
        self.assertIn("mode=design&machineId=", js)
        self.assertIn("Open in Stately", js)
        self.assertNotIn("<iframe", js)
        self.assertNotIn("registry/editor/embed", js)


class TestGenerator(unittest.TestCase):
    """``scripts/diagram_mermaid.py`` draws what Stately draws."""

    @classmethod
    def setUpClass(cls) -> None:
        from scripts import diagram_mermaid as dm

        cls.dm = dm
        cls.source = dm.to_stately_mermaid(
            {
                "id": "order",
                "initial": "cart",
                "on": {"RESET": {"target": ".cart", "actions": "clear"}},
                "states": {
                    "cart": {
                        "entry": "init",
                        "exit": [
                            "flush",
                            {
                                "type": "raise",
                                "params": {"event": {"type": "PING"}},
                            },
                        ],
                        "on": {
                            "ADD": {"actions": "addItem"},
                            "CHECKOUT": {
                                "target": "charging",
                                "guard": "hasItems",
                            },
                            "RELOAD": {"target": "cart", "reenter": True},
                        },
                        "after": {"90000": "expired"},
                    },
                    "charging": {
                        "initial": "trying",
                        "entry": "bumpAttempt",
                        "invoke": {
                            "src": "chargeCard",
                            "onDone": {
                                "target": "shipped",
                                "actions": "storeReceipt",
                            },
                            "onError": "failed",
                        },
                        "states": {
                            "trying": {"on": {"RETRY": "#order.charging"}},
                            "hist": {"type": "history"},
                        },
                    },
                    "failed": {
                        "on": {
                            "RETRY": {
                                "target": "charging",
                                "guard": "canRetry",
                            }
                        }
                    },
                    "expired": {},
                    "shipped": {"type": "final"},
                },
            }
        )

    def test_states_carry_stately_style_rows(self) -> None:
        src = self.source
        self.assertIn("<span class='xsm-title'>cart</span>", src)
        self.assertRegex(
            src,
            r"order_cart : <span class='xsm-kw'>entry /</span> "
            r"<span class='xsm-chip'>init</span>",
        )
        self.assertIn("<span class='xsm-chip'>raise PING</span>", src)
        self.assertIn("<span class='xsm-final'></span>shipped", src)
        self.assertIn("state \"<span class='xsm-title'>H</span>\" as", src)
        self.assertIn("class order_charging_hist xsmHistory", src)

    def test_internal_and_self_transitions_are_rows_not_edges(self) -> None:
        src = self.source
        self.assertNotIn("order_cart --> order_cart", src)
        self.assertRegex(
            src,
            r"order_cart : <span class='xsm-kw'>on</span> "
            r"<span class='xsm-ev'>ADD</span> <span class='xsm-kw'>/</span> "
            r"<span class='xsm-chip'>addItem</span>",
        )
        self.assertIn(
            "<span class='xsm-ev'>RELOAD</span> <span class='xsm-kw'>↻ self</span>",
            src,
        )
        # a transition from the machine root to one of its states is a title chip
        self.assertNotRegex(
            src, r"^order --> ", "no edge may start at the root box"
        )
        self.assertIn(
            "<span class='xsm-chip'>on RESET → cart / clear</span>", src
        )
        # and so is a child's transition up to its own parent
        self.assertNotRegex(src, r"^order_charging_trying --> order_charging ")
        self.assertIn(
            "<span class='xsm-ev'>RETRY</span> <span class='xsm-kw'>→ charging</span>",
            src,
        )

    def test_edges_are_pills_with_guards_delays_and_service_results(
        self,
    ) -> None:
        src = self.source
        self.assertIn(
            "order_cart --> order_charging : <span class='xsm-pill'>"
            "<span class='xsm-ev'>CHECKOUT</span> <span class='xsm-kw'>if</span> hasItems</span>",
            src,
        )
        self.assertIn(
            "order_cart --> order_expired : <span class='xsm-pill'>"
            "<span class='xsm-kw'>after</span> 90 s</span>",
            src,
        )
        self.assertIn(
            "order_charging --> order_shipped : <span class='xsm-pill'>"
            "<span class='xsm-dot xsm-dot-done'></span><span class='xsm-kw'>done:</span> chargeCard"
            "<br/><span class='xsm-chip'>storeReceipt</span></span>",
            src,
        )
        self.assertIn(
            "<span class='xsm-kw'>error:</span> chargeCard</span>", src
        )

    def test_compound_states_put_their_rows_in_the_title(self) -> None:
        self.assertRegex(
            self.source,
            r'state "<span class=\'xsm-title\'>charging</span> '
            r"<span class='xsm-chip'>entry / bumpAttempt</span> "
            r"<span class='xsm-chip'>invoke chargeCard</span>\" as order_charging \{",
        )

    def test_parallel_regions_are_dashed_classed_clusters(self) -> None:
        src = self.dm.to_stately_mermaid(
            {
                "id": "player",
                "type": "parallel",
                "states": {
                    "video": {
                        "initial": "on",
                        "states": {"on": {}, "off": {}},
                    },
                    "audio": {
                        "initial": "on",
                        "states": {"on": {}, "off": {}},
                    },
                },
            }
        )
        self.assertIn("class player xsmParallel", src)
        self.assertIn("class player_video xsmRegion", src)
        self.assertIn("class player_audio xsmRegion", src)
        self.assertNotIn(
            "\n--\n", src, "regions are classed clusters, not dividers"
        )
        self.assertIn(
            "state \"<span class='xsm-title'>on</span>\" as player_video_on",
            src,
        )
        self.assertIn(
            "state \"<span class='xsm-title'>on</span>\" as player_audio_on",
            src,
        )

    def test_labels_are_html_escaped(self) -> None:
        src = self.dm.to_stately_mermaid(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"GO <b>": "b"}},
                    "b": {"entry": "x%y#z"},
                },
            }
        )
        # 📝 Mermaid's own `#NN;` entities: an HTML `&lt;`-style entity
        #    would end the statement at its `;`, and `&#35;` is re-mangled.
        self.assertIn("GO #60;b#62;", src)
        self.assertIn("x#37;y#35;z", src)
        self.assertNotIn("&", src)

    def test_format_delay(self) -> None:
        fd = self.dm.format_delay
        self.assertEqual(fd(500), "500 ms")
        self.assertEqual(fd(1000), "1 s")
        self.assertEqual(fd(1500), "1.5 s")
        self.assertEqual(fd(90000), "90 s")
        self.assertEqual(fd(60000), "1 min")
        self.assertEqual(fd(7200000), "2 h")
        self.assertEqual(fd("BACKOFF"), "BACKOFF")

    def test_layout_override_changes_only_the_direction(self) -> None:
        inv = _inventory()
        key = next(iter(json.loads(ASSET.read_text("utf-8"))["machines"]))
        default = self.dm.render_entry(key, inv[key]["config"], {})
        turned = self.dm.render_entry(
            key, inv[key]["config"], {key: {"direction": "LR"}}
        )
        self.assertEqual(default.split("\n")[1], "direction TB")
        self.assertEqual(turned.split("\n")[1], "direction LR")
        self.assertEqual(default.split("\n")[2:], turned.split("\n")[2:])


class TestGalleryGenerator(unittest.TestCase):
    """Regeneration must retain the layout's sole H1 and a clean EOF."""

    def test_gallery_regenerates_without_title_or_newline_drift(self) -> None:
        from scripts import place_stately_embeds as generator

        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory)
            (docs / "_guide").mkdir()
            target = docs / "_guide" / "example-gallery.md"
            with patch.object(generator, "DOCS", docs):
                generator.write_gallery()
                first = target.read_bytes()
                generator.write_gallery()
                self.assertEqual(target.read_bytes(), first)
        self.assertTrue(first.endswith(b"\n"))
        self.assertFalse(first.endswith(b"\n\n"))
        self.assertNotIn(b"\r", first)
        text = first.decode("utf-8")
        self.assertIn("title: Example gallery\n", text)
        self.assertNotRegex(text, r"(?m)^#\s+", "layout supplies the H1")
        self.assertEqual(
            text,
            (DOCS / "_guide" / "example-gallery.md").read_text("utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
