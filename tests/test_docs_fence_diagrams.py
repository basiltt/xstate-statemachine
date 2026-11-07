"""Keep the fence checker honest: it finds every hand-authored diagram, and
its browser rules still enforce colour, clipping and phone sizing.

The 57 ```mermaid fences are colour-matched by Mermaid's own theme (see
diagrams.js `themeVariables`), unlike the generated statecharts which the
stylesheet recolours; ``scripts/check_fence_diagrams.py`` renders them all
in both themes at page and phone widths and fails on unreadable output.
These tests pin its source contracts without a browser.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _module():
    spec = importlib.util.spec_from_file_location(
        "check_fence_diagrams", ROOT / "scripts" / "check_fence_diagrams.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestFenceDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fc = _module()

    def test_every_fence_is_found_with_its_kind_and_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = pathlib.Path(tmp) / "docs"
            docs.mkdir()
            (docs / "a.md").write_text(
                "intro\n\n```mermaid\nsequenceDiagram\n  A->>B: hi\n```\n",
                encoding="utf-8",
            )
            (docs / "b.md").write_text(
                "```mermaid\n---\nconfig:\n  state:\n"
                "    nodeSpacing: 8\n---\nstateDiagram-v2\n  A --> B\n```\n",
                encoding="utf-8",
            )
            found = self.fc.fences(docs)
        self.assertEqual(
            [f["kind"] for f in found],
            ["sequenceDiagram", "stateDiagram-v2"],
        )
        self.assertEqual(found[0]["line"], 3)
        self.assertTrue(found[0]["file"].endswith("a.md"))

    def test_non_mermaid_fences_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = pathlib.Path(tmp) / "docs"
            docs.mkdir()
            (docs / "a.md").write_text(
                "```python\nprint(1)\n```\n", encoding="utf-8"
            )
            self.assertEqual(self.fc.fences(docs), [])


class TestBrowserRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fc = _module()

    def test_contrast_is_measured_on_the_painted_run(self) -> None:
        js = self.fc.MEASURE_JS
        for contract in (
            "tspan",  # sequence labels live there; the parent text is the box
            "backdrop",
            "low contrast",
            "parseColor",
        ):
            with self.subTest(contract=contract):
                self.assertIn(contract, js)

    def test_phones_must_keep_the_natural_size(self) -> None:
        js = self.fc.MEASURE_JS
        self.assertIn("innerWidth <= 720", js)
        self.assertIn("chart shrunk to", js)
        self.assertIn("does not scroll", js)

    def test_harness_hosts_fences_and_a_narrow_viewport(self) -> None:
        harness = (ROOT / "scripts" / "diagram_harness.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("__fenceSources", harness)
        self.assertIn("query.get('width')", harness)


if __name__ == "__main__":
    unittest.main()
