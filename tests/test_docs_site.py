# tests/test_docs_site.py
# -----------------------------------------------------------------------------
# 🏛️ The documentation site is a shipped artifact
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the GitHub Pages landing page is executed, not
# eyeballed. It is the first code a visitor reads, and nothing in the build
# validated it.
#
# It shipped the exact defect this release exists to fix: the "Functional"
# sample called `green.to(yellow, event="TIMER")` as a bare statement.
# `State.to()` RETURNS a Transition; it does not register one, so the value was
# discarded and the machine could never move — while a comment on the next line
# promised `green → yellow`.
#
# Crucially, that sample RAN WITHOUT ERROR. A smoke test that only checks the
# exit code would have passed it, which is why this file asserts the machine
# actually TRANSITIONS.
# -----------------------------------------------------------------------------
"""The docs landing page and navigation must stay true."""

import html
import os
import re
import subprocess
import sys
import unittest
from typing import Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DOCS = os.path.join(_ROOT, "docs")
_INDEX = os.path.join(_DOCS, "index.html")
_LAYOUT = os.path.join(_DOCS, "_layouts", "default.html")


def _read(path: str) -> str:
    """Read a UTF-8 file."""
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _code_samples() -> Dict[str, str]:
    """Extract the syntax-highlighted samples from the landing page."""
    page = _read(_INDEX)
    samples: Dict[str, str] = {}
    for match in re.finditer(
        r'data-tab="(\w+)">\s*<pre><code>(.*?)</code></pre>', page, re.S
    ):
        plain = html.unescape(re.sub(r"<[^>]+>", "", match.group(2)))
        samples[match.group(1)] = plain
    return samples


class TestLandingPageSamples(unittest.TestCase):
    """Every "define a machine" sample must run AND move."""

    PREAMBLE = (
        "import logging\n"
        "logging.disable(logging.CRITICAL)\n"
        "import sys\n"
        f"sys.path.insert(0, {_ROOT!r})\n"
        "import src.xstate_statemachine as _x\n"
        "sys.modules['xstate_statemachine'] = _x\n"
    )

    def setUp(self) -> None:
        self.samples = _code_samples()
        self.assertGreaterEqual(
            len(self.samples), 4, "landing page samples not found"
        )

    def test_every_sample_executes(self) -> None:
        """A sample that raises is a broken first impression."""
        for name, code in self.samples.items():
            with self.subTest(sample=name):
                result = subprocess.run(
                    [sys.executable, "-c", self.PREAMBLE + code],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    (result.stderr or "").strip()[-300:],
                )

    def test_every_sample_actually_transitions(self) -> None:
        """Running without error is NOT enough.

        The broken functional sample ran fine and simply never moved. Each
        sample sends TIMER twice, so a working traffic light must end in
        `red`; a machine with discarded transitions stays in `green`.
        """
        for name, code in self.samples.items():
            with self.subTest(sample=name):
                # 📝 Keep the interpreter alive so its state can be read.
                body = code.replace("interp.stop()", "")
                probe = "\nprint('FINAL', sorted(interp.current_state_ids))\n"
                result = subprocess.run(
                    [sys.executable, "-c", self.PREAMBLE + body + probe],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    encoding="utf-8",
                    errors="replace",
                )
                self.assertEqual(result.returncode, 0, result.stderr[-300:])
                lines = (result.stdout or "").strip().splitlines()
                self.assertTrue(lines, "sample produced no output")
                self.assertIn(
                    "trafficLight.red",
                    lines[-1],
                    f"{name}: two TIMER events did not reach 'red' — "
                    f"transitions are not registered ({lines[-1]})",
                )


class TestSiteNavigation(unittest.TestCase):
    """Every sidebar link must resolve to a real page."""

    def test_no_broken_guide_links(self) -> None:
        """A 404 in the nav is the most visible kind of rot."""
        layout = _read(_LAYOUT)
        linked = set(re.findall(r"'/guide/([a-z0-9-]+)/'", layout))
        guide_dir = os.path.join(_DOCS, "_guide")
        present = {
            os.path.splitext(name)[0]
            for name in os.listdir(guide_dir)
            if name.endswith(".md")
        }
        self.assertEqual(sorted(linked - present), [])

    def test_every_guide_page_is_reachable(self) -> None:
        """An unlinked page may as well not exist."""
        layout = _read(_LAYOUT)
        linked = set(re.findall(r"'/guide/([a-z0-9-]+)/'", layout))
        guide_dir = os.path.join(_DOCS, "_guide")
        present = {
            os.path.splitext(name)[0]
            for name in os.listdir(guide_dir)
            if name.endswith(".md")
        }
        self.assertEqual(sorted(present - linked), [])


def _package_version() -> str:
    """Read ``project.version`` from pyproject.toml.

    📝 ``tomllib`` is stdlib only from Python 3.11, but this package
    supports 3.9+ and the CI matrix runs 3.9 and 3.10 — where importing it
    raises ModuleNotFoundError and failed this test on three jobs. Rather
    than add a `tomli` test dependency for one field, fall back to a
    narrow regex anchored to the ``[project]`` table.
    """
    path = os.path.join(_ROOT, "pyproject.toml")
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover — Python < 3.11
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        table = re.search(r"^\[project\]$(.*?)(?=^\[)", text, re.S | re.M)
        match = re.search(
            r'^version\s*=\s*"([^"]+)"',
            table.group(1) if table else text,
            re.M,
        )
        if match is None:  # pragma: no cover — malformed pyproject
            raise AssertionError("could not read project.version")
        return match.group(1)

    with open(path, "rb") as handle:
        version: str = tomllib.load(handle)["project"]["version"]
    return version


class TestSiteIsCurrent(unittest.TestCase):
    """The landing page must not advertise a stale release."""

    def test_hero_badge_matches_package_version(self) -> None:
        """It sat at v0.5.0 for two releases before anyone noticed."""
        version = _package_version()

        page = _read(_INDEX)
        badge = re.search(r'class="hero-badge">v([0-9.]+)', page)
        self.assertIsNotNone(badge, "hero badge not found")
        self.assertEqual(badge.group(1), version)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
