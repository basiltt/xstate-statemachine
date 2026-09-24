"""Tests for the zero-dependency `cli.ui` rendering toolkit.

Every widget has a plain rendering (no ANSI, one line per event) and a
styled one; both are pinned. Width maths is tested against fixed cells
because a tearing table is the classic failure of hand-rolled layout.
"""

from __future__ import annotations

import io
import os
import sys
import unittest
from unittest import mock

from src.xstate_statemachine.cli.ui import (
    PLAIN,
    Capabilities,
    Column,
    Console,
    Node,
    Table,
    detect,
)
from src.xstate_statemachine.cli.ui import animate, banner, box, keys, prompt
from src.xstate_statemachine.cli.ui.progress import (
    ProgressBar,
    Spinner,
    StepList,
)
from src.xstate_statemachine.cli.ui.style import THEME, paint, sgr
from src.xstate_statemachine.cli.ui.text import (
    pad,
    strip_ansi,
    truncate,
    visible_width,
    wrap,
)
from src.xstate_statemachine.cli.ui.tree import render as render_tree

RICH = Capabilities(
    tty=True,
    color=True,
    truecolor=True,
    unicode=True,
    animate=False,
    width=80,
    height=24,
)
ANIM = Capabilities(
    tty=True,
    color=True,
    truecolor=True,
    unicode=True,
    animate=True,
    width=80,
    height=24,
)
C16 = Capabilities(
    tty=True,
    color=True,
    truecolor=False,
    unicode=True,
    animate=False,
    width=80,
    height=24,
)


def _zero_dep_guard() -> None:
    """Every `cli.ui` module must import with third-party imports blocked."""
    import importlib

    blocked = {
        "rich",
        "colorama",
        "click",
        "typer",
        "prompt_toolkit",
        "blessed",
    }

    class _Block(importlib.abc.MetaPathFinder):  # type: ignore[name-defined]
        def find_spec(self, name, path, target=None):
            if name.split(".")[0] in blocked:
                raise ImportError(f"third-party import attempted: {name}")
            return None

    finder = _Block()
    sys.meta_path.insert(0, finder)
    try:
        for m in (
            "term",
            "style",
            "text",
            "box",
            "table",
            "tree",
            "progress",
            "keys",
            "prompt",
            "banner",
            "animate",
            "console",
        ):
            importlib.reload(
                importlib.import_module(f"src.xstate_statemachine.cli.ui.{m}")
            )
    finally:
        sys.meta_path.remove(finder)


class TestText(unittest.TestCase):
    def test_visible_width_ignores_ansi_and_counts_wide(self) -> None:
        self.assertEqual(visible_width("\x1b[1mabc\x1b[0m"), 3)
        self.assertEqual(visible_width("日本"), 4)
        self.assertEqual(visible_width("✓ ok"), 4)

    def test_pad_and_truncate_respect_visible_width(self) -> None:
        styled = paint("hello", "ok", RICH)
        self.assertEqual(visible_width(pad(styled, 8)), 8)
        self.assertEqual(visible_width(pad("x", 3, "right")), 3)
        cut = truncate(styled + " world", 7)
        self.assertLessEqual(visible_width(cut), 7)
        self.assertTrue(cut.endswith("\x1b[0m"))  # colour never bleeds
        self.assertEqual(truncate("short", 10), "short")

    def test_wrap_keeps_paragraphs(self) -> None:
        self.assertEqual(wrap("a b c\n\nd", 3), ["a b", "c", "", "d"])

    def test_strip_ansi(self) -> None:
        self.assertEqual(strip_ansi("\x1b[38;2;1;2;3mx\x1b[0m"), "x")


class TestStyle(unittest.TestCase):
    def test_paint_is_identity_without_colour(self) -> None:
        self.assertEqual(paint("x", "accent", PLAIN), "x")

    def test_truecolor_and_16_colour_tiers(self) -> None:
        self.assertIn("38;2;", sgr(THEME["accent"], RICH))
        s16 = sgr(THEME["accent"], C16)
        self.assertTrue("38;5;" in s16 or ";93" in s16 or "[1;93" in s16)

    def test_unknown_role_is_an_error(self) -> None:
        with self.assertRaises(KeyError):
            paint("x", "nope", RICH)

    def test_every_theme_role_renders(self) -> None:
        for role in THEME:
            paint("x", role, RICH)


class TestBoxTableTree(unittest.TestCase):
    def test_panel_lines_are_uniform_width(self) -> None:
        for caps in (PLAIN, RICH):
            lines = box.panel(
                caps, ["a", "a much longer line " * 10], title="T", width=40
            )
            self.assertTrue(all(visible_width(l) == 40 for l in lines), lines)

    def test_panel_ascii_fallback(self) -> None:
        lines = box.panel(PLAIN, ["x"], title="T", width=20)
        self.assertTrue(lines[0].startswith("+ T "))
        self.assertNotIn("╭", "".join(lines))

    def test_table_fits_terminal_and_aligns(self) -> None:
        caps = Capabilities(False, False, False, False, False, 40, 24)
        t = Table([Column("a"), Column("b", align="right"), Column("c")])
        t.add("x" * 30, "1", "y" * 30)
        lines = t.render(caps)
        self.assertTrue(all(visible_width(l) <= 40 for l in lines))
        self.assertIn("|", lines[1])  # header row uses the vertical glyph
        # right alignment: the "1" sits at the right edge of its cell
        self.assertRegex(lines[3], r"\|\s+1 \|")

    def test_table_styled_cells_do_not_tear(self) -> None:
        t = Table([Column("k", role="kind.compound"), Column("v")])
        t.add("compound", "1").add("x", "22")
        lines = t.render(RICH)
        widths = {visible_width(l) for l in lines}
        self.assertEqual(len(widths), 1, lines)

    def test_tree_connectors(self) -> None:
        root = Node("r", [Node("a", [Node("a1")]), Node("b")])
        plain = render_tree(PLAIN, root)
        self.assertEqual(plain, ["r", "|-- a", "|   `-- a1", "`-- b"])
        rich = [strip_ansi(l) for l in render_tree(RICH, root)]
        self.assertEqual(rich, ["r", "├── a", "│   └── a1", "└── b"])

    def test_cards_grid(self) -> None:
        caps = Capabilities(False, False, False, False, False, 100, 24)
        lines = box.cards(
            caps, [("A", "1"), ("B", "2"), ("C", "3")], columns=3
        )
        self.assertTrue(all("+" in l for l in lines[:1]))
        self.assertEqual(len({visible_width(l) for l in lines}), 1)


class TestProgress(unittest.TestCase):
    def test_spinner_plain_prints_start_and_result(self) -> None:
        buf = io.StringIO()
        with Spinner(PLAIN, "Working", stream=buf) as sp:
            sp.update("Worked")
        self.assertEqual(buf.getvalue(), "Working...\nOK Worked\n")

    def test_spinner_fail_on_exception(self) -> None:
        buf = io.StringIO()
        with self.assertRaises(RuntimeError):
            with Spinner(PLAIN, "Working", stream=buf):
                raise RuntimeError("x")
        self.assertIn("X Working", buf.getvalue())

    def test_spinner_animated_thread_stops(self) -> None:
        buf = io.StringIO()
        with Spinner(ANIM, "Working", stream=buf, interval=0.01):
            pass
        out = buf.getvalue()
        self.assertIn("\x1b[?25l", out)  # hides cursor
        self.assertIn("\x1b[?25h", out)  # restores it
        self.assertIn("Working", strip_ansi(out))

    def test_progress_bar_plain_and_unicode(self) -> None:
        buf = io.StringIO()
        bar = ProgressBar(PLAIN, 2, label="files", stream=buf)
        bar.advance()
        bar.advance()
        self.assertEqual(buf.getvalue(), "[1/2] files\n[2/2] files\n")
        rendered = strip_ansi(ProgressBar(RICH, 4, width=8)._render())
        self.assertIn("0%", rendered)

    def test_steplist_plain_one_line_per_finish(self) -> None:
        buf = io.StringIO()
        st = StepList(PLAIN, ["Parse", "Write"], stream=buf)
        st.begin()
        st.start(0)
        st.finish(0, "3 files")
        st.start(1)
        st.finish(1, state="failed")
        self.assertEqual(buf.getvalue(), "OK Parse -- 3 files\nX Write\n")

    def test_steplist_animated_redraws_in_place(self) -> None:
        buf = io.StringIO()
        st = StepList(ANIM, ["A", "B"], stream=buf)
        st.begin()
        st.finish(0)
        self.assertIn("\x1b[2A", buf.getvalue())  # cursor moved up 2 rows


class TestPrompts(unittest.TestCase):
    def test_select_with_scripted_keys(self) -> None:
        buf = io.StringIO()
        idx = prompt.select(
            RICH,
            "Pick",
            [("a", "first"), ("b", "second"), ("c", "third")],
            source=keys.scripted("down down enter"),
            stream=buf,
        )
        self.assertEqual(idx, 2)
        self.assertIn("Pick", strip_ansi(buf.getvalue()))

    def test_select_digit_jump_and_escape(self) -> None:
        self.assertEqual(
            prompt.select(
                RICH,
                "P",
                [("a", ""), ("b", "")],
                source=keys.scripted("2 enter"),
                stream=io.StringIO(),
            ),
            1,
        )
        self.assertIsNone(
            prompt.select(
                RICH,
                "P",
                [("a", "")],
                source=keys.scripted("esc"),
                stream=io.StringIO(),
            )
        )

    def test_multiselect_toggle_all_none(self) -> None:
        src = keys.scripted("space down space enter")
        self.assertEqual(
            prompt.multiselect(
                RICH,
                "M",
                [("a", ""), ("b", ""), ("c", "")],
                source=src,
                stream=io.StringIO(),
            ),
            [0, 1],
        )
        self.assertEqual(
            prompt.multiselect(
                RICH,
                "M",
                [("a", ""), ("b", "")],
                source=keys.scripted("a enter"),
                stream=io.StringIO(),
            ),
            [0, 1],
        )

    def test_confirm_and_text(self) -> None:
        self.assertTrue(
            prompt.confirm(
                RICH, "Q?", source=keys.scripted("enter"), stream=io.StringIO()
            )
        )
        self.assertFalse(
            prompt.confirm(
                RICH, "Q?", source=keys.scripted("n"), stream=io.StringIO()
            )
        )
        self.assertEqual(
            prompt.text(
                RICH,
                "Name",
                default="ab",
                source=keys.scripted("backspace c enter"),
                stream=io.StringIO(),
            ),
            "ac",
        )

    def test_scripted_source_exhaustion_is_loud(self) -> None:
        src = keys.scripted("a")
        src()
        with self.assertRaises(EOFError):
            src()


class TestBannerAnimate(unittest.TestCase):
    def test_banner_sizes(self) -> None:
        wide = banner.render(RICH, "1.0")
        narrow = banner.render(
            Capabilities(True, True, True, True, False, 45, 24), "1.0"
        )
        ascii_ = banner.render(PLAIN, "1.0")
        self.assertGreater(len(wide), len(narrow))
        self.assertTrue(all(ord(ch) < 128 for l in ascii_ for ch in l))
        self.assertIn("v1.0", strip_ansi(wide[-1]))

    def test_animations_are_instant_when_plain(self) -> None:
        buf = io.StringIO()
        animate.wipe_in(PLAIN, ["a", "b"], stream=buf)
        animate.typewriter(PLAIN, "hi", stream=buf)
        animate.pulse(PLAIN, "x", stream=buf)
        self.assertEqual(buf.getvalue(), "a\nb\nhi\nx\n")

    def test_animations_run_when_animated(self) -> None:
        buf = io.StringIO()
        animate.wipe_in(ANIM, ["a"], total_ms=1, stream=buf)
        animate.typewriter(ANIM, "hi", total_ms=1, stream=buf)
        animate.pulse(ANIM, "x", total_ms=1, stream=buf)
        self.assertIn("hi", strip_ansi(buf.getvalue()))


class TestDetectAndConsole(unittest.TestCase):
    def test_non_tty_is_plain(self) -> None:
        caps = detect(io.StringIO())
        self.assertFalse(caps.color)
        self.assertFalse(caps.animate)
        self.assertTrue(caps.plain)

    def test_no_color_env_wins_over_force(self) -> None:
        with mock.patch.dict(
            os.environ, {"NO_COLOR": "1", "FORCE_COLOR": "1"}
        ):
            self.assertFalse(detect(io.StringIO()).color)

    def test_force_color_on_non_tty(self) -> None:
        env = {"FORCE_COLOR": "1", "COLORTERM": "truecolor"}
        for k in ("NO_COLOR", "XSM_NO_COLOR", "XSM_PLAIN", "TERM"):
            os.environ.pop(k, None)
        with (
            mock.patch.dict(os.environ, env),
            mock.patch(
                "src.xstate_statemachine.cli.ui.term._enable_windows_vt",
                return_value=True,
            ),
        ):
            caps = detect(io.StringIO())
        self.assertTrue(caps.color)
        self.assertFalse(caps.animate)  # never animate off-tty

    def test_flags(self) -> None:
        self.assertTrue(detect(io.StringIO(), plain=True).plain)
        with (
            mock.patch.dict(os.environ, {"FORCE_COLOR": "1"}),
            mock.patch(
                "src.xstate_statemachine.cli.ui.term._enable_windows_vt",
                return_value=True,
            ),
        ):
            self.assertFalse(detect(io.StringIO(), no_color=True).color)

    def test_console_plain_output_is_ansi_free(self) -> None:
        buf = io.StringIO()
        c = Console(PLAIN, buf)
        c.ok("done")
        c.rule("t")
        c.kv([("Version", "1"), ("Py", "3")])
        c.panel(["x"], title="P")
        out = buf.getvalue()
        self.assertNotIn("\x1b", out)
        self.assertIn("OK done", out)
        self.assertIn("Version  1", out)

    def test_console_degrades_unencodable_glyphs(self) -> None:
        class Latin1(io.StringIO):
            encoding = "latin-1"

        buf = Latin1()
        c = Console(PLAIN, buf)
        c.print("✓ ok · a → b …")  # every glyph has an ASCII stand-in
        self.assertIn("OK ok - a -> b ...", buf.getvalue())
        c.print("漢")  # none for this one: replaced, never raised
        self.assertIn("?", buf.getvalue().splitlines()[-1])

    def test_console_interactive_requires_tty_stdin(self) -> None:
        self.assertFalse(Console(PLAIN, io.StringIO()).interactive)

    def test_zero_dependency_guard(self) -> None:
        _zero_dep_guard()


if __name__ == "__main__":
    unittest.main()
