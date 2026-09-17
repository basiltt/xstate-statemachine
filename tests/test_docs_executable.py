# tests/test_docs_executable.py
# -----------------------------------------------------------------------------
# 📖 Documentation stays true -- every code block runs, every link resolves
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the docs are meant to be the library's reference
# of record, and two 0.8.0 audits found the same failure mode both times --
# samples that had quietly stopped running (a kwarg renamed, a name never
# exported) and cross-links that 404ed on the published site. Neither can
# be caught by a test that reads the docs; it has to EXECUTE them. So this
# module does: every ```python block in README.md and docs/_guide/*.md that
# imports the package is run as a program, and every relative link and
# anchor is resolved against the real page set.
#
# Fragments are a legitimate documentation device ("...then later:" with
# `interp` already in scope), so a block may opt out by preceding its fence
# with `<!-- doc-fragment -->`. The marker is deliberate and visible in the
# source: an author must SAY a block is partial, rather than the test
# guessing from the error. Blocks that demonstrate an exception being raised
# use the same marker.
# -----------------------------------------------------------------------------
"""Executes every documentation code sample; resolves every documentation link."""

import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from typing import Iterator, List, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "_guide"
DOC_FILES = [ROOT / "README.md", *sorted(GUIDE.glob("*.md"))]
FRAGMENT_MARK = "<!-- doc-fragment -->"
FENCE = re.compile(r"```python\n(.*?)```", re.S)
IMPORTS_PACKAGE = re.compile(r"^\s*from xstate_statemachine", re.M)
PER_BLOCK_TIMEOUT_S = 60


def _blocks(md: pathlib.Path) -> Iterator[Tuple[int, str, bool]]:
    """Yield ``(line_no, source, is_fragment)`` for each python fence."""
    text = md.read_text(encoding="utf-8")
    for m in FENCE.finditer(text):
        line = text[: m.start()].count("\n") + 1
        before = text[: m.start()].rstrip()
        yield line, m.group(1), before.endswith(FRAGMENT_MARK)


def _runnable_blocks() -> List[Tuple[str, int, str]]:
    out = []
    for md in DOC_FILES:
        for line, src, is_fragment in _blocks(md):
            if is_fragment or not IMPORTS_PACKAGE.search(src):
                continue
            out.append((md.relative_to(ROOT).as_posix(), line, src))
    return out


class TestDocCodeBlocksExecute(unittest.TestCase):
    """Every unmarked block that imports the package must exit 0."""

    def test_every_documented_sample_runs(self) -> None:
        blocks = _runnable_blocks()
        # 🛡️ Guard against the test silently testing nothing (a regex or
        #    path change that yields zero blocks would otherwise pass).
        self.assertGreater(len(blocks), 150, "doc block discovery broke")
        env = {
            **os.environ,
            "PYTHONPATH": str(ROOT),
            "PYTHONIOENCODING": "utf-8",
        }
        failures = []
        with tempfile.TemporaryDirectory() as tmp:
            for rel, line, src in blocks:
                # 📦 Docs import the installed name; tests run from the
                #    source checkout.
                program = src.replace(
                    "from xstate_statemachine", "from src.xstate_statemachine"
                )
                path = pathlib.Path(tmp, "block.py")
                path.write_text(program, encoding="utf-8")
                proc = subprocess.run(
                    [sys.executable, "-X", "utf8", str(path)],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=tmp,
                    env=env,
                    timeout=PER_BLOCK_TIMEOUT_S,
                )
                if proc.returncode != 0:
                    tail = (proc.stderr.strip().splitlines() or ["?"])[-1]
                    failures.append(f"{rel}:{line}  {tail[:160]}")
        self.assertEqual(
            failures,
            [],
            "Documentation samples that no longer run (mark intentional "
            f"fragments with {FRAGMENT_MARK}):\n  " + "\n  ".join(failures),
        )


def _slug(heading: str, github: bool = False) -> str:
    h = re.sub(r"[`*_]", "", heading).strip().lower()
    if github:
        # GitHub: drop variation selectors, strip punctuation, keep every
        # hyphen (so "Actions & Side Effects" -> "actions--side-effects").
        h = h.replace("️", "")
        h = re.sub(r"[^\w\- ]", "", h)
        return h.replace(" ", "-")
    # Jekyll/kramdown and main.js keep only ASCII alphanumerics and collapse
    # runs of hyphens, so "## 🔢 Execution Order" -> "execution-order".
    h = re.sub(r"[^a-z0-9\- ]", "", h).strip()
    return re.sub(r"-+", "-", h.replace(" ", "-"))


class TestDocLinksResolve(unittest.TestCase):
    def setUp(self) -> None:
        self.pages = {p.stem for p in GUIDE.glob("*.md")}
        self.headings = {
            p.stem: {
                _slug(m.group(1))
                for m in re.finditer(
                    r"^#{1,6}\s+(.*)$", p.read_text(encoding="utf-8"), re.M
                )
            }
            for p in GUIDE.glob("*.md")
        }

    def test_guide_cross_links_and_anchors(self) -> None:
        link = re.compile(r"\]\((\.\./([a-z0-9-]+)/(#[^)]*)?|#([^)]+))\)")
        bad = []
        for p in GUIDE.glob("*.md"):
            for m in link.finditer(p.read_text(encoding="utf-8")):
                page, anchor, local = m.group(2), m.group(3), m.group(4)
                if page and page not in self.pages:
                    bad.append(f"{p.name}: no page for {m.group(1)}")
                elif page and anchor and anchor[1:] not in self.headings[page]:
                    bad.append(f"{p.name}: no anchor for {m.group(1)}")
                elif local and local not in self.headings[p.stem]:
                    bad.append(f"{p.name}: no local anchor #{local}")
        self.assertEqual(bad, [])

    def test_guide_pages_do_not_use_raw_md_links(self) -> None:
        """`](page.md)` renders on GitHub but 404s on the Jekyll site, whose
        permalinks are `/guide/<name>/`. Use `](../<name>/)`."""
        raw = re.compile(r"\]\([a-z0-9-]+\.md(#[^)]*)?\)")
        offenders = [
            p.name
            for p in GUIDE.glob("*.md")
            if raw.search(p.read_text(encoding="utf-8"))
        ]
        self.assertEqual(offenders, [])

    def test_readme_anchors_and_site_links(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        heads = {
            _slug(m.group(1), github=True)
            for m in re.finditer(r"^#{1,6}\s+(.*)$", text, re.M)
        }
        anchors = set(re.findall(r"\]\(#([^)]+)\)", text))
        bad = sorted(a for a in anchors if a.replace("️", "") not in heads)
        self.assertEqual(bad, [], "README anchors with no heading")
        site = set(
            re.findall(r"xstate-statemachine/guide/([a-z0-9-]+)/", text)
        )
        self.assertEqual(
            sorted(site - self.pages), [], "README -> missing site page"
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
