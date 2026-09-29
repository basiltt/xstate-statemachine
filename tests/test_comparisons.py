# tests/test_comparisons.py
"""#291 E5: comparison pages, their data file, and the launch-kit drafts.

Stdlib only -- the comparison data is JSON (Jekyll reads `_data/*.json`)
precisely so this test needs no YAML parser.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "_data" / "comparisons.json"
PAGES = ROOT / "docs" / "_guide" / "comparisons"
LAUNCH = ROOT / "docs" / "research" / "launch"
DRAFT = "DRAFT — do not post without maintainer approval"

EXPECTED_ROWS = [
    "Hierarchy",
    "Parallel",
    "Guards as policy",
    "`after` timeouts",
    "Human-in-the-loop as durable state",
    "Persistence / replay",
    "Visual editor",
    "Typed context / events",
    "Observability",
    "Multi-agent",
    "Incremental adoption",
]
PAGE_OF = {
    "langgraph": "vs-langgraph",
    "burr": "vs-burr",
    "statelyai_agent": "vs-statelyai-agent",
}


class TestComparisonData(unittest.TestCase):
    def setUp(self) -> None:
        self.data = json.loads(DATA.read_text("utf-8"))

    def test_every_required_row_is_present_and_complete(self) -> None:
        features = [r["feature"] for r in self.data["rows"]]
        for want in EXPECTED_ROWS:
            self.assertTrue(
                any(f.startswith(want) for f in features), f"row {want!r}"
            )
        keys = {"feature", "ours", *self.data["competitors"]}
        for row in self.data["rows"]:
            self.assertEqual(set(row), keys, row["feature"])
            self.assertTrue(all(str(v).strip() for v in row.values()))

    def test_every_page_renders_every_row_from_the_data(self) -> None:
        for key, comp in self.data["competitors"].items():
            page = PAGES / f"{PAGE_OF[key]}.md"
            text = page.read_text("utf-8")
            # 📝 the table is a Liquid loop over the data file ...
            self.assertIn("site.data.comparisons.rows", text, page)
            self.assertIn(f"row.{key}", text, page)
            self.assertIn(comp["name"], text, page)
            # ... and every row is named in the page's row manifest
            for row in self.data["rows"]:
                self.assertIn(row["feature"], text, f"{page.name}: row")
            for section in (
                "## feature table",
                "## when to choose",
                "## when to choose xstate-statemachine",
                "## ours, in 20 lines",
            ):
                self.assertIn(section, text.lower(), page.name)
            self.assertIn("<!-- doc-requires: pydantic -->", text)
            self.assertIn("FakeModel", text)
            self.assertIn(f"permalink: /guide/{PAGE_OF[key]}/", text)

    def test_pages_are_in_nav_order_and_search(self) -> None:
        layout = (ROOT / "docs" / "_layouts" / "default.html").read_text(
            "utf-8"
        )
        index = (
            ROOT / "docs" / "assets" / "js" / "search-index.json"
        ).read_text("utf-8")
        for slug in PAGE_OF.values():
            self.assertIn(f"/guide/{slug}/", layout, f"{slug} not in sidebar")
            self.assertIn(f"{slug},", layout, f"{slug} not in pages_order")
            self.assertIn(f"/guide/{slug}/", index, f"{slug} not searchable")


class TestPythonLibraryComparisons(unittest.TestCase):
    """#286: vs django-fsm / transitions / python-statemachine.

    Each competitor is its own top-level entry in the data file (its own
    rows, each with a `source` note), so the three pages render from one
    file and cannot drift.
    """

    PAGES = {
        "django_fsm": "vs-django-fsm",
        "transitions": "vs-transitions",
        "python_statemachine": "vs-python-statemachine",
    }
    ROWS = [
        "Hierarchy (nested states)",
        "Parallel regions",
        "Timers (`after`)",
        "Invoked services",
        "Actors / child machines",
        "Async",
        "Locking / concurrent writers",
        "Versioning / migration",
        "Admin / UI",
        "REST / DRF",
        "Audit trail",
        "Visual editor",
        "Typed context",
        "Persistence",
        "XState JSON portability",
    ]

    def setUp(self) -> None:
        self.data = json.loads(DATA.read_text("utf-8"))

    def test_every_row_is_present_complete_and_sourced(self) -> None:
        for key in self.PAGES:
            entry = self.data[key]
            for field in ("name", "url", "checked"):
                self.assertTrue(str(entry[field]).strip(), f"{key}.{field}")
            rows = entry["rows"]
            self.assertEqual([r["feature"] for r in rows], self.ROWS, key)
            for row in rows:
                self.assertEqual(
                    set(row), {"feature", "ours", "theirs", "source"}
                )
                for field, value in row.items():
                    self.assertTrue(
                        str(value).strip(), f"{key}/{row['feature']}/{field}"
                    )
                # 📝 a source names the competitor's version checked
                self.assertIn(entry["name"], row["source"], row["feature"])

    def test_ours_column_is_identical_across_the_three_pages(self) -> None:
        ours = [[r["ours"] for r in self.data[k]["rows"]] for k in self.PAGES]
        self.assertEqual(ours[0], ours[1])
        self.assertEqual(ours[0], ours[2])

    def test_pages_render_from_the_data_and_have_the_sections(self) -> None:
        for key, slug in self.PAGES.items():
            page = PAGES / f"{slug}.md"
            text = page.read_text("utf-8")
            self.assertIn(f"site.data.comparisons.{key}", text, slug)
            self.assertIn("row.source", text, slug)
            self.assertIn(f"permalink: /guide/{slug}/", text)
            for row in self.ROWS:
                self.assertIn(row, text, f"{slug}: row manifest")
            low = text.lower()
            for section in (
                "## feature table",
                "## the same order lifecycle",
                "## when to choose",
                "## when to choose xstate-statemachine",
            ):
                self.assertIn(section, low, f"{slug}: {section}")
            # ✅ ours executes (python fence), theirs never does (text)
            self.assertIn("```python", text, slug)
            self.assertIn("stub_logic", text, slug)
            self.assertIn("### Theirs", text, slug)
            theirs = text.split("### Theirs", 1)[1].split("### Ours", 1)[0]
            self.assertIn("```text", theirs, slug)
            self.assertNotIn("```python", theirs, slug)

    def test_django_page_has_the_planned_migration_recipe(self) -> None:
        text = (PAGES / "vs-django-fsm.md").read_text("utf-8")
        self.assertIn("## Migration recipe", text)
        self.assertIn("xsm_migrate_fsm", text)
        self.assertIn("issues/310", text)
        self.assertIn("not shipped yet", text)

    def test_pages_are_in_nav_order_and_search(self) -> None:
        layout = (ROOT / "docs" / "_layouts" / "default.html").read_text(
            "utf-8"
        )
        index = (
            ROOT / "docs" / "assets" / "js" / "search-index.json"
        ).read_text("utf-8")
        for slug in self.PAGES.values():
            self.assertIn(f"/guide/{slug}/", layout, f"{slug} not in sidebar")
            self.assertIn(f"{slug},", layout, f"{slug} not in pages_order")
            self.assertIn(f"/guide/{slug}/", index, f"{slug} not searchable")


class TestLaunchKit(unittest.TestCase):
    FILES = (
        "show_hn.md",
        "reddit_python.md",
        "reddit_langchain.md",
        "blog_outline.md",
        "tweet_thread.md",
        "awesome_lists.md",
        "djangopackages.md",
        "stately_community.md",
    )

    def test_every_draft_exists(self) -> None:
        for name in self.FILES:
            self.assertTrue((LAUNCH / name).is_file(), name)

    def test_every_file_starts_with_the_draft_header(self) -> None:
        files = sorted(LAUNCH.glob("*"))
        self.assertTrue(files)
        for path in files:
            head = path.read_text("utf-8").lstrip("﻿").splitlines()[0]
            self.assertIn(DRAFT, head, path.name)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
