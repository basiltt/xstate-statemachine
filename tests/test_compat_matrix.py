"""The framework-compatibility matrix and its generated page (#296)."""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import unittest

from xstate_statemachine.contrib._registry import EXTRAS

ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX = ROOT / "tests" / "contrib" / "compat_matrix.json"
PAGE = ROOT / "docs" / "_guide" / "compatibility.md"
GEN = ROOT / "scripts" / "gen_compatibility.py"
PYPROJECT = ROOT / "pyproject.toml"

sys.path.insert(0, str(ROOT / "scripts"))
import gen_compatibility as gen  # noqa: E402


def _shipped_extras() -> set:
    """Extras whose pyproject entry is non-empty and that have a subpackage
    on disk (umbrella extras excluded)."""
    text = PYPROJECT.read_text(encoding="utf-8")
    shipped = set()
    for name, extra in EXTRAS.items():
        if not extra.subpackage:
            continue
        m = re.search(rf"^{name}\s*=\s*\[([^\]]*)\]", text, re.M)
        if m and m.group(1).strip():
            shipped.add(name)
    return shipped


def _floor(name: str, package: str) -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    start = re.search(rf"^{name}\s*=\s*\[", text, re.M)
    assert start, name
    # the entry runs until the next `key =` line at column 0
    rest = text[start.end() :]
    end = re.search(r"^\w+\s*=", rest, re.M)
    block = rest[: end.start()] if end else rest
    m = re.search(rf'"{re.escape(package)}(?:\[[^\]]*\])?>=([\d.]+)"', block)
    assert m, (name, package)
    return m.group(1)


class TestCompatMatrix(unittest.TestCase):
    def setUp(self) -> None:
        self.extras = json.loads(MATRIX.read_text(encoding="utf-8"))["extras"]

    def test_covers_exactly_the_shipped_extras(self) -> None:
        self.assertEqual(set(self.extras), _shipped_extras())

    def test_declared_is_the_pyproject_floor_and_oldest_is_not_below(
        self,
    ) -> None:
        def key(v: str) -> tuple:
            parts = [int(x) for x in v.split(".")]
            return tuple(parts + [0] * (3 - len(parts)))

        for name, e in self.extras.items():
            floor = _floor(name, e["package"])
            self.assertEqual(e["declared"], floor, msg=name)
            self.assertIn(f">={floor}", e["newest"], msg=name)
            m = re.search(r"==([\d.]+)$", e["oldest"])
            self.assertTrue(m, e["oldest"])
            pinned = m.group(1)
            self.assertGreaterEqual(key(pinned), key(floor), msg=name)
            if key(pinned) > key(floor):
                # A raised practical floor must say why.
                self.assertTrue(e.get("note"), msg=name)

    def test_two_cells_per_extra(self) -> None:
        cells = gen.matrix(self.extras)
        self.assertEqual(len(cells), 2 * len(self.extras))
        for name in self.extras:
            kinds = {c["kind"] for c in cells if c["extra"] == name}
            self.assertEqual(kinds, {"oldest", "newest"})

    def test_oldest_cells_run_on_the_oldest_supported_python(self) -> None:
        for name, e in self.extras.items():
            self.assertEqual(e["python"]["oldest"], "3.9", msg=name)

    def test_pip_args_for_a_cell(self) -> None:
        args = gen.pip_args(self.extras, "fastapi", "oldest")
        self.assertEqual(args[:2], [".[fastapi]", "fastapi==0.106.0"])
        self.assertIn("httpx==0.27.2", args)
        newest = gen.pip_args(self.extras, "fastapi", "newest")
        self.assertNotIn("httpx==0.27.2", newest)

    def test_every_extra_has_a_test_folder(self) -> None:
        for name in self.extras:
            self.assertTrue(
                (ROOT / "tests" / "contrib" / name).is_dir(), msg=name
            )


class TestGeneratedPage(unittest.TestCase):
    def test_page_is_byte_identical_to_a_fresh_render(self) -> None:
        self.assertEqual(
            PAGE.read_bytes(), gen.render(gen.load()).encode("utf-8")
        )

    def test_check_mode_passes(self) -> None:
        out = subprocess.run(
            [sys.executable, str(GEN), "--check"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_matrix_mode_emits_github_include(self) -> None:
        out = subprocess.run(
            [sys.executable, str(GEN), "--matrix"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(out.stdout)
        self.assertIn("include", data)

    def test_workflow_reads_the_generator(self) -> None:
        wf = (ROOT / ".github" / "workflows" / "compat.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("gen_compatibility.py --matrix", wf)
        self.assertIn("gen_compatibility.py --check", wf)
        self.assertIn("--pip-args", wf)
        self.assertIn("workflow_dispatch", wf)
        self.assertIn("schedule", wf)
        self.assertIn("tests/contrib/compat_matrix.json", wf)
        self.assertIn('"pyproject.toml"', wf)

    def test_every_extra_is_on_the_page(self) -> None:
        text = PAGE.read_text(encoding="utf-8")
        for name in gen.load():
            self.assertIn(f"`[{name}]`", text)


if __name__ == "__main__":
    unittest.main()
