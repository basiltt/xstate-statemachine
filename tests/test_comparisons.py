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
