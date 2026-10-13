"""🔎 Keep Stately fullscreen viewing inside the documentation site.

These are source contracts, using only the Python standard library. They
protect the shared controls, iframe lifecycle, and viewport containment
without adding a JavaScript runtime or browser to the library's CI. They
do not prove browser focus behavior, cross-origin keyboard delivery, or
rendered layout: those require separate real-browser verification.
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
SCRIPT = DOCS / "assets" / "js" / "stately.js"
STYLE = DOCS / "assets" / "css" / "style.css"


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
                return source[opening + 1 : token.start()]
    raise AssertionError("Unclosed source block")


def _function(source: str, name: str) -> str:
    """Scope a contract to its owner instead of a matching unrelated hook."""
    match = re.search(
        rf"\bfunction\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", source
    )
    if match is None:
        raise AssertionError(f"Missing JavaScript function: {name}")
    return _block(source, match.end() - 1)


def _matching_block(source: str, declaration: str) -> str:
    """Read a specific conditional or callback rather than the whole file."""
    match = re.search(declaration, source)
    if match is None:
        raise AssertionError(f"Missing source block: {declaration}")
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


class TestStatelyEmbedCompatibility(unittest.TestCase):
    """A fullscreen control must retain existing inline embed behavior."""

    def setUp(self) -> None:
        self.script = SCRIPT.read_text(encoding="utf-8")

    def test_embed_and_external_editor_routes_stay_distinct(self) -> None:
        embed = _function(self.script, "embedUrl")
        editor = _function(self.script, "editorUrl")
        self.assertIn("https://stately.ai/registry/editor/embed/", embed)
        self.assertIn("https://stately.ai/registry/editor/", editor)
        self.assertNotIn("/embed/", editor)
        for body in (embed, editor):
            self.assertIn("mode=design", body)
            self.assertIn("machineId=", body)
        self.assertIn("colorMode=", embed)

    def test_shared_loader_uses_the_docs_base_and_machine_map(self) -> None:
        self.assertRegex(
            self.script,
            r"querySelectorAll\(\s*['\"]\.stately\[data-machine\]['\"]",
        )
        self.assertRegex(
            self.script, r"getAttribute\(\s*['\"]data-base['\"]\s*\)"
        )
        self.assertRegex(
            self.script,
            r"fetch\(\s*base\s*\+\s*['\"]/assets/data/stately\.json['\"]",
        )
        self.assertIn("map.machines[key]", self.script)
        self.assertIn("map.project", self.script)

    def test_inline_iframes_remain_lazy_and_observer_driven(self) -> None:
        mount = _function(self.script, "mount")
        self.assertRegex(
            mount,
            r"\.loading\s*=\s*state\.fullscreen\s*\?\s*"
            r"['\"]eager['\"]\s*:\s*['\"]lazy['\"]",
        )
        self.assertIn("IntersectionObserver", self.script)
        self.assertIn(".isIntersecting", self.script)
        self.assertIn(".unobserve(", self.script)
        self.assertRegex(mount, r"\.src\s*=\s*embedUrl\(")
        self.assertNotIn("editorUrl(", mount)

    def test_theme_still_follows_the_document_root(self) -> None:
        theme = _function(self.script, "theme")
        self.assertIn("document.documentElement", self.script)
        self.assertRegex(theme, r"getAttribute\(\s*['\"]data-theme['\"]")
        self.assertIn("MutationObserver", self.script)
        self.assertRegex(
            self.script,
            r"attributeFilter:\s*\[\s*['\"]data-theme['\"]\s*\]",
        )


class TestStatelyFullscreenControls(unittest.TestCase):
    """Each embed opens the same named, native in-page dialog."""

    def setUp(self) -> None:
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.create = _function(self.script, "createFullscreen")
        self.open = _function(self.script, "openFullscreen")

    def test_every_embed_gets_an_accessible_fullscreen_button(self) -> None:
        controls = _matching_block(self.script, r"if\s*\(viewer\)\s*\{")
        self.assertRegex(controls, r"frames\.forEach\(")
        self.assertRegex(
            controls, r"element\(['\"]button['\"],\s*['\"]stately-expand"
        )
        self.assertRegex(controls, r"button\.type\s*=\s*['\"]button['\"]")
        for name, value in (
            ("aria-haspopup", "dialog"),
            ("aria-controls", "statelyFullscreen"),
        ):
            self.assertRegex(
                controls,
                rf"setAttribute\(['\"]{name}['\"],\s*['\"]{value}['\"]",
            )
        self.assertRegex(controls, r"setAttribute\(['\"]aria-label['\"]")
        self.assertIn("state.title", controls)
        self.assertIn("openFullscreen(state, button)", controls)
        self.assertIn("state.actions.insertBefore(button", controls)

    def test_viewer_is_a_single_native_dialog_with_a_named_title(self) -> None:
        self.assertRegex(
            self.create,
            r"element\(['\"]dialog['\"],\s*['\"]stately-fullscreen['\"]",
        )
        self.assertEqual(self.script.count("viewer = createFullscreen()"), 1)
        hosts = _matching_block(
            self.script, r"hosts\.forEach\(function\s*\(host\)\s*\{"
        )
        self.assertNotIn("createFullscreen(", hosts)
        self.assertIn("dialog.id = 'statelyFullscreen'", self.create)
        self.assertIn("title.id = 'statelyFullscreenTitle'", self.create)
        self.assertRegex(
            self.create,
            r"setAttribute\(['\"]aria-labelledby['\"],\s*"
            r"['\"]statelyFullscreenTitle['\"]",
        )
        self.assertIn("viewer.title.textContent = state.title", self.open)
        self.assertIn("viewer.dialog.showModal()", self.open)
        self.assertNotIn("requestFullscreen", self.script)
        self.assertNotIn("window.open(", self.script)

    def test_unsupported_dialog_does_not_get_an_unusable_button(self) -> None:
        self.assertRegex(
            self.create, r"typeof dialog\.showModal\s*!==\s*['\"]function"
        )
        self.assertRegex(
            self.create, r"typeof dialog\.close\s*!==\s*['\"]function"
        )
        self.assertIn("return null", self.create)
        self.assertLess(
            self.create.index("return null"),
            self.create.index("document.body.appendChild(dialog)"),
        )

    def test_external_editor_links_remain_safe_and_chart_specific(
        self,
    ) -> None:
        link = _function(self.script, "editorLink")
        self.assertIn("stately-open stately-editor-link", link)
        self.assertIn("Open in Stately", link)
        self.assertRegex(link, r"\.target\s*=\s*['\"]_blank['\"]")
        self.assertRegex(link, r"\.rel\s*=\s*['\"][^'\"]*\bnoopener\b")
        self.assertIn("link.href = editorUrl(project, id)", link)
        self.assertIn("actions.appendChild(editorLink(id))", self.script)
        self.assertIn("var link = editorLink()", self.create)
        self.assertIn(
            "viewer.link.href = editorUrl(project, state.id)", self.open
        )

    def test_close_is_named_autofocused_and_wired_to_shared_cleanup(
        self,
    ) -> None:
        self.assertRegex(
            self.create,
            r"element\(['\"]button['\"],\s*['\"]stately-fullscreen-close",
        )
        self.assertRegex(self.create, r"close\.type\s*=\s*['\"]button['\"]")
        self.assertIn("close.autofocus = true", self.create)
        self.assertRegex(
            self.create,
            r"close\.setAttribute\(['\"]aria-label['\"],\s*['\"]Close",
        )
        self.assertRegex(
            self.create,
            r"close\.addEventListener\(['\"]click['\"],\s*closeFullscreen",
        )
        self.assertIn("viewer.close.focus({ preventScroll: true })", self.open)

    def test_titles_are_text_and_embed_heights_are_validated(self) -> None:
        element = _function(self.script, "element")
        self.assertIn("node.textContent = text", element)
        self.assertNotIn(".innerHTML", self.script)
        self.assertIn("Number.isFinite(height)", self.script)
        self.assertIn("height <= 0", self.script)

    def test_keyboard_return_control_follows_the_iframe(self) -> None:
        self.assertIn("'stately-fullscreen-return'", self.create)
        self.assertIn("'Back to viewer controls'", self.create)
        self.assertIn("returnControl.type = 'button'", self.create)
        self.assertLess(
            self.create.index("dialog.appendChild(box)"),
            self.create.index("dialog.appendChild(returnControl)"),
        )
        callback = _matching_block(
            self.create,
            r"returnControl\.addEventListener\('click', function \(\) \{",
        )
        self.assertIn("close.focus({ preventScroll: true })", callback)
        self.assertNotIn(
            "returnControl.setAttribute('aria-hidden'", self.create
        )
        self.assertNotIn("returnControl.tabIndex = -1", self.create)


class TestStatelyFullscreenLifecycle(unittest.TestCase):
    """Source guards for deferred loading, reopen races, and teardown."""

    def setUp(self) -> None:
        self.script = SCRIPT.read_text(encoding="utf-8")
        self.open = _function(self.script, "openFullscreen")
        self.close = _function(self.script, "finishClose")
        self.schedule = _function(self.script, "scheduleFullscreenMount")

    def test_fullscreen_has_a_separate_iframe_after_visible_layout(
        self,
    ) -> None:
        self.assertIn("box: viewer.box, id: state.id", self.open)
        self.assertIn("iframe: null, mode: null, fullscreen: true", self.open)
        self.assertLess(
            self.open.index("viewer.dialog.showModal()"),
            self.open.index("scheduleFullscreenMount()"),
        )
        create = _function(self.script, "createFullscreen")
        self.assertNotIn("mount(", create)
        self.assertNotIn("createElement('iframe')", create)
        self.assertIn("requestAnimationFrame(", self.schedule)
        self.assertIn("state !== active", self.schedule)
        self.assertIn("!viewer.dialog.open", self.schedule)
        self.assertIn("getBoundingClientRect()", self.schedule)
        self.assertIn("rect.width <= 0 || rect.height <= 0", self.schedule)
        self.assertIn("mount(state)", self.schedule)
        self.assertNotIn("appendChild(state.iframe)", self.script)

    def test_obsolete_load_callbacks_cannot_update_a_new_frame(self) -> None:
        mount = _function(self.script, "mount")
        for event in ("load", "error"):
            with self.subTest(event=event):
                callback = _matching_block(
                    mount, rf"f\.on{event}\s*=\s*function\s*\(\)\s*\{{"
                )
                self.assertRegex(
                    callback, r"if\s*\(state\.iframe\s*!==\s*f\)\s*return"
                )
        self.assertLess(
            mount.index("state.iframe = f"), mount.index("f.src = embedUrl")
        )
        self.assertIn("disposeFrame(state)", mount)

    def test_native_cancel_and_close_share_the_same_cleanup(self) -> None:
        create = _function(self.script, "createFullscreen")
        cancel = _matching_block(
            create,
            r"addEventListener\(['\"]cancel['\"],\s*"
            r"function\s*\(event\)\s*\{",
        )
        self.assertIn("event.preventDefault()", cancel)
        self.assertIn("closeFullscreen()", cancel)
        close_event = _matching_block(
            create,
            r"addEventListener\(['\"]close['\"],\s*function\s*\(\)\s*\{",
        )
        self.assertRegex(
            close_event, r"if\s*\(!dialog\.open\)\s*finishClose\(\)"
        )
        close = _function(self.script, "closeFullscreen")
        self.assertIn("viewer.dialog.close()", close)
        self.assertIn("finishClose()", close)

    def test_close_disposes_pending_and_loaded_fullscreen_work(self) -> None:
        self.assertIn("cancelAnimationFrame(frameRequest)", self.close)
        self.assertIn("frameRequest = 0", self.close)
        self.assertIn("active = null", self.close)
        self.assertIn("disposeFrame(previous)", self.close)
        self.assertIn("viewer.box.textContent = ''", self.close)
        self.assertIn("viewer.status.textContent = ''", self.close)
        dispose = _function(self.script, "disposeFrame")
        for callback in ("onload", "onerror"):
            self.assertIn("state.iframe." + callback + " = null", dispose)
        self.assertIn("state.iframe.remove()", dispose)
        self.assertIn("state.iframe = null", dispose)
        self.assertIn("state.mode = null", dispose)

    def test_close_restores_focus_scroll_and_only_its_own_scroll_lock(
        self,
    ) -> None:
        self.assertIn("opener: opener", self.open)
        self.assertIn(
            "scrollX: window.scrollX, scrollY: window.scrollY", self.open
        )
        self.assertIn(
            "!document.body.classList.contains('diagram-open')", self.open
        )
        unlock = _matching_block(
            self.close, r"if\s*\(previous\.ownsScrollLock\)\s*\{"
        )
        self.assertIn("document.body.classList.remove('diagram-open')", unlock)
        focus = _matching_block(
            self.close, r"if\s*\(previous\.opener\.isConnected\)\s*\{"
        )
        self.assertIn("previous.opener.focus({ preventScroll: true })", focus)
        self.assertIn("window.scrollTo(", self.close)
        self.assertIn(
            "left: previous.scrollX, top: previous.scrollY", self.close
        )
        self.assertIn("behavior: 'instant'", self.close)

    def test_theme_updates_only_an_open_fullscreen_viewer(self) -> None:
        observer = _matching_block(
            self.script, r"new MutationObserver\(function\s*\(\)\s*\{"
        )
        self.assertRegex(
            observer,
            r"if\s*\(active\s*&&\s*viewer\.dialog\.open\)\s*"
            r"scheduleFullscreenMount\(\)",
        )
        self.assertIn("cancelAnimationFrame(frameRequest)", self.schedule)


class TestStatelyFullscreenContainment(unittest.TestCase):
    """The close control stays outside the shrinking chart viewport."""

    def setUp(self) -> None:
        self.css = STYLE.read_text(encoding="utf-8")

    def test_native_dialog_is_hidden_until_opened(self) -> None:
        closed = _declarations(self.css, ".stately-fullscreen")
        opened = _declarations(self.css, ".stately-fullscreen[open]")
        self.assertEqual(closed.get("display"), "none")
        self.assertEqual(opened.get("display"), "flex")
        self.assertEqual(closed.get("flex-direction"), "column")

    def test_dialog_fills_the_dynamic_viewport(self) -> None:
        dialog = _declarations(self.css, ".stately-fullscreen")
        self.assertEqual(dialog.get("position"), "fixed")
        self.assertEqual(dialog.get("inset"), "0")
        self.assertEqual(dialog.get("margin"), "0")
        self.assertIn(dialog.get("width"), ("100%", "100vw", "100dvw"))
        self.assertEqual(dialog.get("height"), "100dvh")
        self.assertIn(
            dialog.get("max-width"), ("none", "100%", "100vw", "100dvw")
        )
        self.assertIn(
            dialog.get("max-height"), ("none", "100%", "100vh", "100dvh")
        )
        self.assertEqual(dialog.get("overflow"), "hidden")

    def test_chart_frame_shrinks_without_pushing_away_toolbar(self) -> None:
        frame = _declarations(self.css, ".stately-fullscreen-frame")
        for dimension in ("min-width", "min-height"):
            self.assertEqual(frame.get(dimension), "0")
        self.assertIn(frame.get("flex"), ("1", "1 1 auto", "1 1 0"))
        self.assertEqual(frame.get("overflow"), "hidden")
        toolbar = _declarations(self.css, ".stately-fullscreen-toolbar")
        self.assertTrue(
            toolbar.get("flex") == "none" or toolbar.get("flex-shrink") == "0",
            "the toolbar must keep its space above the iframe",
        )

    def test_close_control_has_a_nonshrinking_touch_target(self) -> None:
        close = _declarations(self.css, ".stately-fullscreen-close")
        self.assertTrue(
            close.get("flex") == "none" or close.get("flex-shrink") == "0"
        )
        for dimension in ("width", "height"):
            with self.subTest(dimension=dimension):
                value = close.get("min-" + dimension, close.get(dimension))
                self.assertIsNotNone(value)
                self.assertRegex(value, r"^\d+(?:\.\d+)?px$")
                self.assertGreaterEqual(float(value[:-2]), 44)

    def test_titles_shrink_and_keyboard_focus_stays_visible(self) -> None:
        title = _declarations(self.css, ".stately-fullscreen-title")
        self.assertEqual(title.get("min-width"), "0")
        for selector in (
            ".stately-expand:focus-visible",
            ".stately-fullscreen-close:focus-visible",
        ):
            with self.subTest(selector=selector):
                focus = _declarations(self.css, ":focus-visible")
                focus.update(_declarations(self.css, selector))
                self.assertTrue(focus.get("outline"))
                self.assertNotIn(focus["outline"], ("none", "0"))

    def test_viewer_uses_theme_tokens_and_existing_scroll_lock(self) -> None:
        dialog = _declarations(self.css, ".stately-fullscreen")
        for property_name in ("color", "background"):
            self.assertIn("var(--", dialog.get(property_name, ""))
        self.assertEqual(
            _declarations(self.css, "body.diagram-open").get("overflow"),
            "hidden",
        )

    def test_viewer_controls_respect_device_safe_areas(self) -> None:
        declarations = {}
        for selector in (
            ".stately-fullscreen",
            ".stately-fullscreen-toolbar",
            ".stately-fullscreen-frame",
        ):
            for name, value in _declarations(self.css, selector).items():
                declarations[selector + name] = value
        values = " ".join(declarations.values())
        for edge in ("top", "right", "bottom", "left"):
            with self.subTest(edge=edge):
                self.assertIn("env(safe-area-inset-" + edge, values)

    def test_keyboard_return_is_visible_when_focused(self) -> None:
        button = _declarations(self.css, ".stately-fullscreen-return")
        clipped = _declarations(
            self.css, ".stately-fullscreen-return:not(:focus)"
        )
        self.assertEqual(button.get("position"), "absolute")
        self.assertEqual(button.get("min-height"), "44px")
        self.assertEqual(button.get("min-width"), "44px")
        self.assertNotIn(button.get("display"), (None, "none"))
        self.assertEqual(clipped.get("clip-path"), "inset(50%)")
        for rules in (button, clipped):
            self.assertNotEqual(rules.get("display"), "none")
            self.assertNotEqual(rules.get("visibility"), "hidden")
