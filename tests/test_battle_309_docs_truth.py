# tests/test_battle_309_docs_truth.py
# -----------------------------------------------------------------------------
# 📖 Battle #309 (adoption kit, adversary B): the newcomer docs say what is TRUE
# -----------------------------------------------------------------------------
# 🏛️ The Pages site is the reference of record, so every claim a newcomer
# reads on the journey page, the extras table and the Stately page is pinned
# to the code it describes: extras to pyproject, CLI flags to the pytest
# plugin, version labels to __version__, every page reachable from the site.
# -----------------------------------------------------------------------------
"""Pins the adoption-kit docs to the shipped library."""

import pathlib
import re
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "_guide"
SRC = ROOT / "src" / "xstate_statemachine"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _version() -> tuple:
    m = re.search(
        r'__version__ = "(\d+)\.(\d+)\.(\d+)"', _read(SRC / "__init__.py")
    )
    return tuple(int(x) for x in m.groups())


def _extras() -> set:
    text = _read(ROOT / "pyproject.toml")
    block = text.split("[project.optional-dependencies]", 1)[1]
    block = block.split("\n[", 1)[0]
    names = set(re.findall(r"^([a-z][a-z0-9-]*)\s*=", block, re.M))
    return names - {"dev", "lint", "test"}


class TestVersionLabels(unittest.TestCase):
    def test_no_feature_is_tagged_with_an_unreleased_version(self) -> None:
        """A `**[0.12.0]**` tag on a row that ships in 0.11.0 is a lie."""
        current = _version()
        bad = []
        pages = list(GUIDE.rglob("*.md")) + [ROOT / "docs/api/index.md"]
        for p in pages + [ROOT / "README.md"]:
            # 📝 the changelog RECORDS such labels being fixed (review #309
            #    H1); inline code is quoted text, never a feature tag
            text = re.sub(r"`[^`\n]*`", "", _read(p))
            if p.name == "changelog.md":
                continue
            for m in re.finditer(r"\*\*\[(\d+)\.(\d+)\.(\d+)\]\*\*", text):
                if tuple(int(x) for x in m.groups()) > current:
                    bad.append(f"{p.name}: {m.group(0)}")
        self.assertEqual(bad, [])

    def test_copy_paste_pins_name_a_released_version(self) -> None:
        current = _version()
        bad = []
        pin = re.compile(r"(?:@v|==|rev: v)(\d+)\.(\d+)\.(\d+)")
        for p in [
            GUIDE / "cli.md",
            ROOT / "README.md",
            GUIDE / "integrations.md",
        ]:
            for m in pin.finditer(_read(p)):
                if tuple(int(x) for x in m.groups()) > current:
                    bad.append(f"{p.name}: {m.group(0)}")
        self.assertEqual(bad, [])


class TestExtrasTable(unittest.TestCase):
    def test_every_pyproject_extra_has_a_row_and_no_phantoms(self) -> None:
        text = _read(GUIDE / "integrations-extras.md")
        rows = [
            ln.split("|")[1]
            for ln in text.splitlines()
            if ln.startswith("| `")
        ]
        listed = set(re.findall(r"`([a-z][a-z0-9-]*)`", " ".join(rows)))
        real = _extras()
        self.assertEqual(
            sorted(real - listed - {"format"}), [], "missing rows"
        )
        self.assertEqual(sorted(listed - real), [], "rows for no extra")

    def test_no_shipped_feature_is_described_as_arriving(self) -> None:
        text = _read(GUIDE / "integrations-extras.md")
        self.assertNotIn("arrives with", text)


class TestJourneyClaims(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _read(GUIDE / "integrations.md")

    def test_decision_tree_is_mermaid_with_litestar_and_observability(
        self,
    ) -> None:
        self.assertIn("```mermaid", self.text)
        for needle in (
            "[litestar]",
            "[observability]",
            "integration-inspector",
        ):
            self.assertIn(needle, self.text)

    def test_every_tree_link_resolves(self) -> None:
        pages = {p.stem for p in GUIDE.rglob("*.md")}
        tree = self.text.split("## Pick your path", 1)[1].split("\n## ", 1)[0]
        for slug in re.findall(r"\]\(\.\./([a-z0-9-]+)/", tree):
            self.assertIn(slug, pages)

    def test_coverage_flags_quoted_are_real_and_not_called_unshipped(
        self,
    ) -> None:
        plugin = _read(SRC / "contrib/testing/_coverage.py")
        for flag in set(re.findall(r"--xsm-[a-z-]+", self.text)):
            self.assertIn(f'"{flag}"', plugin, flag)
        self.assertNotIn("Not shipped yet", self.text)

    def test_inspector_entry_points_exist(self) -> None:
        src = "\n".join(_read(p) for p in SRC.rglob("*.py"))
        self.assertIn("def mount_inspector(", src)
        self.assertIn('"--live"', src)

    def test_limits_box_names_the_real_operational_limits(self) -> None:
        box = self.text.split("## What you get", 1)[1].split("\n## ", 1)[0]
        for needle in ("per process", "exactly one", "Windows"):
            self.assertIn(needle, box)
        self.assertNotIn("planned extras", box)

    def test_step_6_says_it_defers_to_the_fastapi_guide(self) -> None:
        step = self.text.split("### 6.", 1)[1].split("### 7.", 1)[0]
        self.assertIn("no code block", step)
        self.assertIn("integration-fastapi/#multi-worker-deployments", step)
        self.assertIn("Windows", step)

    def test_page_stays_short(self) -> None:
        self.assertLess(len(self.text.splitlines()), 400)


class TestStatelyPage(unittest.TestCase):
    def test_meta_conventions_read_by_the_library_are_called_shipped(
        self,
    ) -> None:
        text = _read(GUIDE / "stately-export.md")
        self.assertNotIn("planned", text.lower())
        src = "\n".join(_read(p) for p in SRC.rglob("*.py"))
        for key in ("meta.publish", "meta.tools"):
            self.assertIn(f"`{key}` (**shipped**)", text)
            self.assertIn(key, src)

    def test_schema_url_points_at_a_file_in_the_repo(self) -> None:
        text = _read(GUIDE / "stately-export.md")
        for rel in re.findall(
            r"xstate-statemachine/main/(schemas/[\w.-]+)", text
        ):
            self.assertTrue((ROOT / rel).is_file(), rel)


class TestNoOrphanPages(unittest.TestCase):
    def test_every_guide_page_is_reachable(self) -> None:
        """Every page is in the nav or linked from another guide page."""
        linked = set()
        for f in [
            ROOT / "docs/_layouts/default.html",
            ROOT / "docs/index.html",
        ]:
            linked |= set(re.findall(r"/guide/([a-z0-9-]+)/", _read(f)))
        for p in GUIDE.rglob("*.md"):
            body = _read(p)
            linked |= {
                s
                for s in re.findall(r"\]\(\.\./([a-z0-9-]+)/", body)
                if s != p.stem
            }
        orphans = sorted({p.stem for p in GUIDE.rglob("*.md")} - linked)
        self.assertEqual(orphans, [])


class TestComparisons(unittest.TestCase):
    def test_each_comparison_links_back_to_the_journey(self) -> None:
        bad = [
            p.name
            for p in (GUIDE / "comparisons").glob("vs-*.md")
            if "](../integrations/" not in _read(p)
        ]
        self.assertEqual(bad, [])


if __name__ == "__main__":  # pragma: no cover
    sys.exit(unittest.main())
