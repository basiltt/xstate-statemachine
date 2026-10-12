"""📱 Keep the shared documentation shell usable on narrow screens.

These source contracts run without Jekyll, Ruby, Node, or a browser. They
protect the shared controls and containment rules; they are not substitutes
for checking rendered pages and keyboard interaction in a real browser.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LAYOUT = DOCS / "_layouts" / "default.html"
STYLE = DOCS / "assets" / "css" / "style.css"
SCRIPT = DOCS / "assets" / "js" / "main.js"


@dataclass
class _Element:
    """An HTML element and its ancestors before Liquid renders the page."""

    tag: str
    attrs: Dict[str, Optional[str]]
    ancestors: Tuple["_Element", ...]


class _LayoutParser(HTMLParser):
    """Read real attributes without depending on their order or spacing."""

    VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    def __init__(self, source: str) -> None:
        super().__init__()
        self.elements: List[_Element] = []
        self.content_containers: List[Tuple[_Element, ...]] = []
        self._stack: List[_Element] = []
        self.feed(source)
        self.close()

    def handle_starttag(
        self, tag: str, attrs: List[Tuple[str, Optional[str]]]
    ) -> None:
        element = _Element(tag, dict(attrs), tuple(self._stack))
        self.elements.append(element)
        if tag not in self.VOID_TAGS:
            self._stack.append(element)

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index].tag == tag:
                del self._stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if re.search(r"\{\{\s*content\s*\}\}", data):
            self.content_containers.append(tuple(self._stack))


def _layout_branches(source: str) -> Dict[str, str]:
    """Select the outer home/guide branch without requiring a Liquid runtime.

    Both branches deliberately use the same main-content ID. They never
    render together, so checking the raw template would report a duplicate
    that is not present in either generated page.
    """
    condition = re.search(
        r"\{%\s*if\s+page\.layout\s*==\s*['\"]home['\"]\s*%\}", source
    )
    if condition is None:
        raise AssertionError("home/guide layout condition missing")
    depth = 1
    divider = None
    for tag in re.finditer(r"\{%\s*(\w+)\b.*?%\}", source[condition.end() :]):
        keyword = tag.group(1)
        if keyword in ("if", "unless", "for", "case"):
            depth += 1
        elif keyword in ("endif", "endunless", "endfor", "endcase"):
            depth -= 1
            if depth == 0:
                if divider is None:
                    raise AssertionError("guide layout branch missing")
                body = source[condition.end() :]
                prefix = source[: condition.start()]
                suffix = body[tag.end() :]
                return {
                    "home": prefix + body[: divider.start()] + suffix,
                    "guide": prefix
                    + body[divider.end() : tag.start()]
                    + suffix,
                }
        elif keyword == "else" and depth == 1:
            divider = tag
    raise AssertionError("home/guide layout condition is not closed")


def _declarations(css: str, selector: str) -> Dict[str, str]:
    """Read explicit declarations for one selector, including media rules.

    This deliberately does not model the cascade or measure browser layout.
    Later declarations for the exact same selector replace earlier ones,
    making accidental removal or overriding of a guard visible to tests.
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    result = {}
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
        selectors = [part.strip() for part in match.group(1).split(",")]
        if selector not in selectors:
            continue
        for declaration in match.group(2).split(";"):
            key, separator, value = declaration.partition(":")
            if separator:
                result[key.strip()] = value.strip()
    return result


def _block_body(source: str, opening: int) -> str:
    """Read a balanced brace block, ignoring quoted strings and comments."""
    tokens = re.compile(
        r"//[^\n]*|/\*.*?\*/|'(?:\\.|[^'\\])*'|" r'"(?:\\.|[^"\\])*"|[{}]',
        re.S,
    )
    depth = 1
    for token in tokens.finditer(source, opening + 1):
        if token.group() == "{":
            depth += 1
        elif token.group() == "}":
            depth -= 1
            if depth == 0:
                return source[opening + 1 : token.start()]
    raise AssertionError("unclosed source block")


class TestDocumentationControls(unittest.TestCase):
    """The same accessible navigation shell serves every site page."""

    def setUp(self) -> None:
        self.branches = _layout_branches(LAYOUT.read_text(encoding="utf-8"))
        self.elements = _LayoutParser(self.branches["guide"]).elements
        self.by_id = {
            element.attrs["id"]: element
            for element in self.elements
            if element.attrs.get("id")
        }

    def test_layout_has_one_unrestricted_mobile_viewport(self) -> None:
        viewports = [
            element
            for element in self.elements
            if element.tag == "meta"
            and element.attrs.get("name") == "viewport"
        ]
        self.assertEqual(len(viewports), 1)
        content = viewports[0].attrs.get("content") or ""
        self.assertIn("width=device-width", content)
        self.assertRegex(content, r"initial-scale=1(?:\.0)?(?:,|$)")
        self.assertNotIn("user-scalable=no", content)
        self.assertNotIn("maximum-scale=1", content)

    def test_gallery_does_not_repeat_the_layout_page_title(self) -> None:
        gallery = (DOCS / "_guide" / "example-gallery.md").read_text("utf-8")
        self.assertRegex(gallery, r"(?m)^title: Example gallery$")
        self.assertNotRegex(gallery, r"(?m)^#\s+", "layout supplies the H1")

    def test_compatibility_does_not_repeat_the_layout_page_title(self) -> None:
        page = (DOCS / "_guide" / "compatibility.md").read_text("utf-8")
        self.assertRegex(page, r'(?m)^title: "Compatibility"$')
        self.assertNotRegex(page, r"(?m)^#\s+", "layout supplies the H1")

    def test_control_targets_have_unique_ids(self) -> None:
        for layout, source in self.branches.items():
            with self.subTest(layout=layout):
                ids = [
                    element.attrs["id"]
                    for element in _LayoutParser(source).elements
                    if element.attrs.get("id")
                ]
                self.assertEqual(
                    len(ids), len(set(ids)), "duplicate layout ID"
                )

    def test_skip_links_target_main_content_in_both_layouts(self) -> None:
        for layout, source in self.branches.items():
            with self.subTest(layout=layout):
                parser = _LayoutParser(source)
                links = [
                    element
                    for element in parser.elements
                    if "skip-link"
                    in (element.attrs.get("class") or "").split()
                ]
                self.assertEqual(len(links), 1)
                self.assertEqual(links[0].attrs.get("href"), "#main-content")
                targets = [
                    element
                    for element in parser.elements
                    if element.attrs.get("id") == "main-content"
                ]
                self.assertEqual(len(targets), 1)
                self.assertEqual(targets[0].tag, "main")
                self.assertEqual(len(parser.content_containers), 1)
                self.assertIn(targets[0], parser.content_containers[0])
                if layout == "home":
                    self.assertEqual(targets[0].attrs.get("tabindex"), "-1")

    def test_mobile_toggles_name_existing_regions(self) -> None:
        controls = {
            "navToggle": "navLinks",
            "sidebarToggle": "sidebar",
            "mobileTocToggle": "mobileTocDrawer",
        }
        for toggle_id, panel_id in controls.items():
            with self.subTest(toggle=toggle_id):
                toggle = self.by_id[toggle_id]
                self.assertEqual(toggle.tag, "button")
                self.assertEqual(toggle.attrs.get("type"), "button")
                self.assertTrue(toggle.attrs.get("aria-label"))
                self.assertEqual(toggle.attrs.get("aria-expanded"), "false")
                self.assertEqual(toggle.attrs.get("aria-controls"), panel_id)
                self.assertIn(panel_id, self.by_id)

    def test_drawers_have_named_close_buttons(self) -> None:
        for close_id, panel_id in (
            ("sidebarClose", "sidebar"),
            ("mobileTocClose", "mobileTocDrawer"),
        ):
            with self.subTest(button=close_id):
                button = self.by_id[close_id]
                self.assertEqual(button.tag, "button")
                self.assertEqual(button.attrs.get("type"), "button")
                self.assertTrue(button.attrs.get("aria-label"))
                self.assertIn(
                    panel_id,
                    [parent.attrs.get("id") for parent in button.ancestors],
                )

    def test_documentation_controls_share_an_in_flow_toolbar(self) -> None:
        for control_id in ("sidebarToggle", "mobileTocToggle"):
            with self.subTest(control=control_id):
                self.assertTrue(
                    any(
                        "docs-toolbar"
                        in (parent.attrs.get("class") or "").split()
                        for parent in self.by_id[control_id].ancestors
                    )
                )
        self.assertNotIn('class="docs-toolbar"', self.branches["home"])

    def test_search_and_theme_are_outside_collapsible_navigation(self) -> None:
        for control_id in ("searchBtn", "themeToggle"):
            with self.subTest(control=control_id):
                control = self.by_id[control_id]
                ancestor_ids = {
                    parent.attrs.get("id") for parent in control.ancestors
                }
                ancestor_classes = {
                    cls
                    for parent in control.ancestors
                    for cls in (parent.attrs.get("class") or "").split()
                }
                self.assertIn("topNav", ancestor_ids)
                self.assertNotIn("navLinks", ancestor_ids)
                self.assertIn("nav-actions", ancestor_classes)
                self.assertEqual(control.tag, "button")
                self.assertEqual(control.attrs.get("type"), "button")
                self.assertTrue(control.attrs.get("aria-label"))


class TestDocumentationContainment(unittest.TestCase):
    """Wide statecharts and examples must not widen the entire document."""

    def setUp(self) -> None:
        self.css = STYLE.read_text(encoding="utf-8")

    def test_layout_and_grid_children_can_shrink(self) -> None:
        for selector in (
            ".page-wrapper > *",
            ".hero-grid > *",
            ".bento > *",
            ".main-content",
            ".content",
        ):
            with self.subTest(selector=selector):
                declarations = _declarations(self.css, selector)
                self.assertEqual(declarations.get("min-width"), "0")

    def test_syntax_highlighting_wrappers_fit_their_container(self) -> None:
        for selector in (
            ".code-frame",
            ".content .highlight",
            ".highlighter-rouge",
            ".code-tab-panel",
        ):
            with self.subTest(selector=selector):
                declarations = _declarations(self.css, selector)
                self.assertEqual(declarations.get("min-width"), "0")
                self.assertEqual(declarations.get("max-width"), "100%")

    def test_code_preserves_indentation_and_scrolls_locally(self) -> None:
        for selector in (
            ".content pre",
            ".highlight pre",
            "pre.highlight",
            ".code-tab-panel pre",
        ):
            with self.subTest(selector=selector):
                declarations = _declarations(self.css, selector)
                self.assertEqual(declarations.get("min-width"), "0")
                self.assertEqual(declarations.get("max-width"), "100%")
                self.assertEqual(declarations.get("overflow-x"), "auto")
                self.assertEqual(declarations.get("white-space"), "pre")
                self.assertEqual(declarations.get("overflow-wrap"), "normal")
        self.assertEqual(
            _declarations(self.css, ".code-frame > pre").get("overflow-x"),
            "auto",
        )

    def test_tables_scroll_inside_the_article_or_landing_section(self) -> None:
        for selector in (".table-scroll", ".comparison-table"):
            with self.subTest(selector=selector):
                declarations = _declarations(self.css, selector)
                self.assertEqual(declarations.get("min-width"), "0")
                self.assertEqual(declarations.get("max-width"), "100%")
                self.assertEqual(declarations.get("overflow-x"), "auto")
                self.assertEqual(
                    declarations.get("overscroll-behavior-x"), "contain"
                )

    def test_mobile_toolbar_reserves_space_and_anchor_offset(self) -> None:
        toolbar = _declarations(self.css, ".docs-toolbar")
        self.assertEqual(toolbar.get("position"), "sticky")
        self.assertEqual(toolbar.get("height"), "var(--docs-toolbar-height)")
        for selector in (
            ".sidebar-toggle",
            ".mobile-toc-toggle",
            ".docs-toolbar-inner > .back-to-top",
        ):
            self.assertEqual(
                _declarations(self.css, selector).get("position"), "static"
            )
        for selector in (".main-content", ".content h2"):
            self.assertIn(
                "var(--docs-toolbar-height)",
                _declarations(self.css, selector).get("scroll-margin-top", ""),
            )

    def test_zoomed_diagrams_stay_inside_a_scrollable_viewer(self) -> None:
        canvas = _declarations(self.css, ".statechart-lightbox-canvas")
        for property_name in ("min-width", "min-height"):
            self.assertEqual(canvas.get(property_name), "0")
        self.assertEqual(canvas.get("overflow"), "auto")
        self.assertEqual(canvas.get("display"), "flex")
        svg = _declarations(self.css, ".statechart-lightbox-canvas svg")
        self.assertEqual(svg.get("flex"), "none")
        self.assertEqual(svg.get("margin"), "auto")
        self.assertNotIn("transform", svg)


class TestResponsivePanelContract(unittest.TestCase):
    """Keep mobile CSS and the shared accessibility controller in sync."""

    def setUp(self) -> None:
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.css = STYLE.read_text(encoding="utf-8")

    def test_each_panel_uses_its_own_css_breakpoint(self) -> None:
        media_blocks = {}
        for match in re.finditer(
            r"@media\s*(\(max-width:\s*\d+px\))\s*\{", self.css
        ):
            query = re.sub(r"\s+", "", match.group(1))
            media_blocks.setdefault(query, "")
            media_blocks[query] += _block_body(self.css, match.end() - 1)
        panel_selectors = {
            "navLinks": ".nav-links",
            "sidebar": ".sidebar",
            "mobileTocDrawer": ".mobile-toc-toggle",
        }
        seen = set()
        for match in re.finditer(
            r"\bcreateResponsivePanel\(\s*\{", self.script
        ):
            options = _block_body(self.script, match.end() - 1)
            panel = re.search(r"\bpanel:\s*([^,\n]+)", options)
            media = re.search(r"\bmedia:\s*['\"]([^'\"]+)['\"]", options)
            self.assertIsNotNone(panel, "panel missing from controller")
            self.assertIsNotNone(media, "responsive breakpoint missing")
            expression = panel.group(1).strip()
            target = re.search(r"qs\(['\"]#([^'\"]+)", expression)
            if target is None:
                bindings = list(
                    re.finditer(
                        rf"\b{re.escape(expression)}\s*=\s*"
                        r"qs\(['\"]#([^'\"]+)",
                        self.script[: match.start()],
                    )
                )
                self.assertTrue(bindings, "panel has no known DOM target")
                target = bindings[-1]
            panel_id = target.group(1)
            query = re.sub(r"\s+", "", media.group(1))
            with self.subTest(panel=panel_id, query=query):
                self.assertIn(panel_id, panel_selectors)
                self.assertIn(query, media_blocks)
                self.assertTrue(
                    _declarations(
                        media_blocks[query], panel_selectors[panel_id]
                    ),
                    "panel CSS and JavaScript must switch together",
                )
                seen.add(panel_id)
        self.assertEqual(seen, set(panel_selectors))

    def test_shared_controller_has_accessibility_and_resize_hooks(
        self,
    ) -> None:
        declaration = re.search(
            r"\bfunction\s+createResponsivePanel\([^)]*\)\s*\{",
            self.script,
        )
        self.assertIsNotNone(declaration)
        controller = _block_body(self.script, declaration.end() - 1)
        # 📝 Scope these checks to the panel controller: the search dialog
        # also handles Escape, but cannot repair a broken sidebar handler.
        for attribute in ("aria-expanded", "aria-hidden", "inert"):
            with self.subTest(attribute=attribute):
                self.assertRegex(
                    controller,
                    rf"\.(?:set|toggle)Attribute\(\s*['\"]{attribute}['\"]",
                )
        for key in ("Escape", "Tab"):
            with self.subTest(key=key):
                self.assertRegex(controller, rf"\.key\s*===\s*['\"]{key}['\"]")
        self.assertIn(".focus()", controller)
        self.assertIn(".matchMedia(", controller)
        self.assertRegex(
            controller, r"\.addEventListener\(\s*['\"]change['\"]"
        )

    def test_diagram_viewer_has_sized_zoom_and_accessible_lifecycle(
        self,
    ) -> None:
        layout = LAYOUT.read_text(encoding="utf-8")
        module = re.search(
            r'<script type="module">(.*?)</script>', layout, re.S
        )
        self.assertIsNotNone(module)
        script = module.group(1)
        for dimension in ("width", "height"):
            self.assertRegex(script, rf"\.style\.{dimension}\s*=")
        self.assertNotIn(".style.transform", script)
        for contract in (
            "'Escape'",
            "'Tab'",
            ".stopPropagation()",
            "ResizeObserver",
            "MutationObserver",
            "data-theme",
        ):
            self.assertIn(contract, script)
        close = re.search(r"function\s+closeViewer\([^)]*\)\s*\{", script)
        self.assertIsNotNone(close)
        close_body = _block_body(script, close.end() - 1)
        self.assertRegex(close_body, r"\.toggleAttribute\(\s*['\"]inert['\"],")
        self.assertRegex(close_body, r"\.focus\(")
