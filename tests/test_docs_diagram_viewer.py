"""🔎 Keep the in-browser statechart renderer and its viewer honest.

Source contracts over ``docs/assets/js/diagrams.js`` and the stylesheet,
using only the Python standard library: no JavaScript runtime or browser
in the library's CI. They protect what a reader relies on -- every chart
gets a Full screen viewer and an Open in Stately link, charts are drawn
lazily, label sizes are measured with the fonts and classes they are shown
with, colliding labels are settled -- and the contract between the renderer
and ``scripts/check_diagrams.py``, which renders every chart headlessly.
The rendered geometry itself is that script's job, not a unit test's.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
from pathlib import Path
import re
from typing import Dict
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SCRIPT = DOCS / "assets" / "js" / "diagrams.js"
STYLE = DOCS / "assets" / "css" / "style.css"
CHECKER = ROOT / "scripts" / "check_diagrams.py"
HARNESS = ROOT / "scripts" / "diagram_harness.html"
MERMAID = (
    "https://cdn.jsdelivr.net/npm/mermaid@12.3.0/dist/mermaid.esm.min.mjs"
)


def _block(source: str, opening: int) -> str:
    """Read balanced braces, ignoring JavaScript strings and comments."""
    tokens = re.compile(
        r"//[^\n]*|/\*.*?\*/|'(?:\\.|[^'\\])*'|"
        r'"(?:\\.|[^"\\])*"|`(?:\\.|[^`\\])*`|[{}]',
        re.S,
    )
    depth = 1
    for token in tokens.finditer(source, opening + 1):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : token.start()]  # noqa: E203
    raise AssertionError("Unclosed source block")


def _function(source: str, name: str) -> str:
    """Scope a contract to its owner instead of a matching unrelated hook."""
    match = re.search(
        rf"\b(?:async\s+)?function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{",
        source,
    )
    if match is None:
        raise AssertionError(f"Missing JavaScript function: {name}")
    return _block(source, match.end() - 1)


def _declarations(css: str, selector: str) -> Dict[str, str]:
    """Read non-print declarations, not the browser's computed cascade."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    for match in reversed(list(re.finditer(r"@media\s+print\s*\{", css))):
        opening = match.end() - 1
        end = opening + len(_block(css, opening)) + 2
        css = css[: match.start()] + css[end:]
    result = {}
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [part.strip() for part in match.group(1).split(",")]
        if selector not in selectors:
            continue
        for declaration in match.group(2).split(";"):
            name, separator, value = declaration.partition(":")
            if separator:
                result[name.strip()] = value.strip()
    return result


class TestRendererContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.script = SCRIPT.read_text(encoding="utf-8")

    def test_mermaid_is_pinned_and_configured_once(self) -> None:
        self.assertIn(f"const MERMAID_URL = '{MERMAID}'", self.script)
        loader = _function(self.script, "loadMermaid")
        self.assertIn("await import(MERMAID_URL)", loader)
        self.assertIn("return null", loader)  # offline: links still built
        self.assertEqual(self.script.count("mermaid.initialize("), 1)
        config = _function(self.script, "configureMermaid")
        self.assertIn("securityLevel: 'loose'", config)  # HTML labels
        self.assertIn("htmlLabels: true", config)
        self.assertIn("useMaxWidth: true", config)
        self.assertIn("layout: 'elk'", config)  # orthogonal routing

    def test_every_chart_gets_a_viewer_button_and_an_editor_link(
        self,
    ) -> None:
        figure = _function(self.script, "buildFigure")
        self.assertIn("'statechart-expand'", figure)
        self.assertRegex(figure, r"button\.type\s*=\s*'button'")
        self.assertRegex(figure, r"setAttribute\('aria-label',")
        self.assertIn("'Full screen'", figure)
        self.assertIn("'statechart-canvas'", figure)
        self.assertIn("'figcaption'", figure)
        link = _function(self.script, "editorLink")
        self.assertIn("'statechart-open'", link)
        self.assertRegex(link, r"\.target\s*=\s*'_blank'")
        self.assertRegex(link, r"\.rel\s*=\s*'noopener noreferrer'")
        self.assertIn("'Open in Stately ↗'", link)
        url = _function(self.script, "editorUrl")
        self.assertIn("encodeURIComponent(project)", url)
        self.assertIn("encodeURIComponent(id)", url)
        embeds = _function(self.script, "collectEmbeds")
        self.assertIn("editorLink(project, entry.id)", embeds)
        self.assertIn("buildFigure('embed', title, link", embeds)

    def test_embeds_render_lazily_and_fences_eagerly(self) -> None:
        observe = _function(self.script, "observe")
        self.assertIn("IntersectionObserver", observe)
        self.assertIn(".isIntersecting", observe)
        self.assertIn(".unobserve(", observe)
        self.assertIn("rootMargin", observe)
        self.assertIn("pending.forEach(render)", observe)  # no observer
        start = _function(self.script, "start")
        self.assertIn("fences.forEach(render)", start)
        self.assertIn("observe(embeds)", start)
        self.assertLess(
            start.index("fontsReady()"),
            start.index("configureMermaid()"),
        )

    def test_fonts_are_loaded_before_labels_are_measured(self) -> None:
        fonts = _function(self.script, "fontsReady")
        for face in ("Space Grotesk", "JetBrains Mono", "italic 400"):
            self.assertIn(face, fonts)
        self.assertIn("document.fonts.load(", fonts)
        self.assertIn("setTimeout(resolve", fonts)  # offline: do not hang

    def test_colliding_labels_are_settled_after_each_render(self) -> None:
        render = _function(self.script, "render")
        self.assertLess(
            render.index("surface.innerHTML = svg"),
            render.index("settleLabels(surface.querySelector('svg'))"),
        )
        # A geometry quirk in the cosmetic passes must not remove the chart.
        self.assertRegex(render, r"try \{\s*settleLabels\(")
        self.assertIn("fitMachineBox(surface.querySelector('svg'))", render)
        fit = _function(self.script, "fitMachineBox")
        self.assertIn("setAttribute('viewBox'", fit)  # the canvas follows
        self.assertIn("g.cluster-label", fit)  # the title stays centred
        settle = _function(self.script, "settleLabels")
        self.assertIn("getTotalLength()", settle)
        self.assertIn("shiftGroup(group", settle)
        self.assertIn("g.cluster-label", settle)  # composite titles count
        self.assertIn("within(box)", settle)  # and the machine box bounds

    def test_render_failure_keeps_the_page_readable(self) -> None:
        render = _function(self.script, "render")
        self.assertIn("catch (error)", render)
        self.assertIn("'statechart-error'", render)
        self.assertIn("pre.textContent = diagram.source", render)
        self.assertIn("button.disabled = true", render)
        embeds = _function(self.script, "collectEmbeds")
        self.assertIn("'Diagram data unavailable.'", embeds)

    def test_viewer_lifecycle_is_accessible(self) -> None:
        close = _function(self.script, "closeViewer")
        self.assertRegex(close, r"\.toggleAttribute\(\s*'inert',")
        self.assertRegex(close, r"\.focus\(")
        self.assertIn("document.body.classList.remove('diagram-open')", close)
        opened = _function(self.script, "openViewer")
        self.assertIn("diagram.title", opened)
        self.assertIn("closeButton.focus(", opened)
        for contract in (
            "'Escape'",
            "'Tab'",
            ".stopPropagation()",
            "ResizeObserver",
        ):
            self.assertIn(contract, self.script)
        self.assertNotIn(".style.transform", self.script)

    def test_tooling_hook_matches_the_headless_checker(self) -> None:
        self.assertIn("window.xsmDiagrams = {", self.script)
        for member in ("ready", "figures", "renderAll:", "renderInto:"):
            self.assertIn(member, self.script)
        checker = CHECKER.read_text(encoding="utf-8")
        self.assertIn("window.xsmDiagrams.renderAll()", checker)
        self.assertIn("window.xsmDiagrams.renderInto(k, s)", checker)
        self.assertIn("diagram_harness.html", checker)
        harness = HARNESS.read_text(encoding="utf-8")
        self.assertIn('src="/docs/assets/js/diagrams.js"', harness)
        self.assertIn('href="/docs/assets/css/style.css"', harness)
        self.assertIn("div.className = 'stately'", harness)


class TestStylesheetContracts(unittest.TestCase):
    def setUp(self) -> None:
        self.css = STYLE.read_text(encoding="utf-8")

    def test_label_classes_are_unscoped_so_measurement_matches_display(
        self,
    ) -> None:
        # 📝 Mermaid measures a label before the SVG is inside .statechart;
        #    a size-affecting rule scoped there would clip the shown text.
        for cls in (
            "xsm-title",
            "xsm-pill",
            "xsm-ev",
            "xsm-kw",
            "xsm-sec",
            "xsm-if",
            "xsm-num",
            "xsm-chip",
        ):
            with self.subTest(cls=cls):
                self.assertRegex(self.css, rf"(?m)^\.{cls}\s*\{{")
        pill = _declarations(self.css, ".xsm-pill")
        self.assertIn("padding", pill)
        self.assertIn("border", pill)
        chip = _declarations(self.css, ".xsm-chip")
        self.assertEqual(chip.get("font-family"), "var(--font-mono)")
        self.assertIn("padding", chip)

    def test_both_themes_define_the_diagram_palette(self) -> None:
        light = _declarations(self.css, ".statechart")
        # The Full screen viewer lives outside the figure and needs them too.
        viewer = _declarations(self.css, ".statechart-lightbox")
        dark = _declarations(self.css, 'html[data-theme="dark"] .statechart')
        for variable in ("--sc-fg", "--sc-node", "--sc-edge", "--sc-pill"):
            with self.subTest(variable=variable):
                self.assertIn(variable, light)
                self.assertIn(variable, dark)
                self.assertIn(variable, viewer)
                self.assertNotEqual(light[variable], dark[variable])

    def test_editor_link_is_a_touch_target_and_print_hides_controls(
        self,
    ) -> None:
        link = _declarations(self.css, ".statechart-open")
        self.assertEqual(link.get("min-height"), "44px")
        self.assertIn(
            "display: none", self.css[self.css.rindex("@media print") :]
        )  # noqa: E203
        self.assertNotIn(".stately-", self.css)
        pending = _declarations(
            self.css, ".statechart.is-pending .statechart-canvas"
        )
        self.assertIn("min-height", pending)


class TestOverlapAnalysis(unittest.TestCase):
    """``scripts/check_diagrams.analyse`` on synthetic geometry: the rules
    the headless check enforces, without a browser."""

    @classmethod
    def setUpClass(cls) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "check_diagrams", ROOT / "scripts" / "check_diagrams.py"
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        cls.analyse = staticmethod(module.analyse)

    @staticmethod
    def _geometry(**overrides):
        base = {
            "clusters": [
                {
                    "id": "root",
                    "box": [0, 0, 400, 300],
                    "title": [0, 0, 400, 24],
                    "text": "m",
                }
            ],
            "leaves": [
                {"id": "a", "box": [40, 60, 80, 40], "text": "a"},
                {"id": "b", "box": [40, 200, 80, 40], "text": "b"},
            ],
            "markers": [],
            "labels": [
                {"edge": "edge0", "box": [60, 130, 60, 30], "text": "GO"}
            ],
            "edges": [
                {
                    "id": "edge0",
                    "len": 100,
                    "points": [[80, 100], [80, 130], [80, 160], [80, 200]],
                }
            ],
            "clipped": [],
        }
        base.update(overrides)
        return base

    def test_clean_geometry_has_no_findings(self) -> None:
        self.assertEqual(self.analyse(self._geometry()), ([], []))

    def test_label_outside_the_machine_box_is_an_error(self) -> None:
        errors, _ = self.analyse(
            self._geometry(
                labels=[
                    {"edge": "edge0", "box": [370, 130, 60, 30], "text": "GO"}
                ]
            )
        )
        self.assertEqual(errors, ["label 'GO' hangs outside the machine box"])

    def test_overlaps_and_clipping_are_errors(self) -> None:
        errors, warnings = self.analyse(
            self._geometry(
                labels=[
                    {"edge": "edge0", "box": [60, 130, 60, 30], "text": "GO"},
                    {
                        "edge": "edge1",
                        "box": [80, 140, 60, 30],
                        "text": "BACK",
                    },
                    {"edge": "edge2", "box": [50, 70, 60, 30], "text": "ON_A"},
                ],
                clipped=[{"text": "GO", "fo": [60, 30], "content": [70, 30]}],
            )
        )
        self.assertIn(
            "clipped label 'GO': box [60, 30] < content [70, 30]", errors
        )
        self.assertIn("label 'GO' overlaps label 'BACK'", errors)
        self.assertIn("state 'a' overlaps label 'ON_A'", errors)
        self.assertEqual(warnings, [])

    def test_a_line_through_a_foreign_state_is_an_error_and_over_a_label_a_warning(
        self,
    ) -> None:
        errors, warnings = self.analyse(
            self._geometry(
                leaves=[
                    {"id": "a", "box": [40, 60, 80, 40], "text": "a"},
                    {"id": "b", "box": [40, 240, 80, 40], "text": "b"},
                    {"id": "c", "box": [50, 170, 60, 20], "text": "c"},
                ],
                labels=[
                    {"edge": "edge9", "box": [60, 120, 40, 20], "text": "X"}
                ],
                edges=[
                    {
                        "id": "edge0",
                        "len": 140,
                        "points": [[80, 100 + 5 * i] for i in range(29)],
                    }
                ],
            )
        )
        self.assertEqual(errors, ["transition edge0 runs through state 'c'"])
        self.assertEqual(warnings, ["transition edge0 crosses label 'X'"])

    def test_render_failure_is_reported_as_one_error(self) -> None:
        self.assertEqual(
            self.analyse({"error": "boom"}), (["render failed: boom"], [])
        )


if __name__ == "__main__":
    unittest.main()
