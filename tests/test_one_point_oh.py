"""The 1.0 checklist (#296) as executable checks.

Imported into ``tests/test_public_api_surface.py`` so the contrib-exports
contract runs wherever the public-API surface does.
"""

from __future__ import annotations

import importlib
import io
import pathlib
import pkgutil
import re
import tokenize
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _contrib_section() -> str:
    text = (ROOT / "docs" / "api" / "index.md").read_text(encoding="utf-8")
    start = text.index("## `xstate_statemachine.contrib`")
    end = text.index("\n## ", start + 5)
    return text[start:end]


class TestOnePointOhChecklist(unittest.TestCase):
    """Contract checks the 1.0 release depends on."""

    def test_every_contrib_export_is_in_the_api_reference(self) -> None:
        """Every `contrib.*.__all__` name is in the API reference's table."""
        import xstate_statemachine.contrib as contrib
        from xstate_statemachine.exceptions import MissingExtraError

        documented = set(
            re.findall(r"`([A-Za-z_][\w.]*)`", _contrib_section())
        )
        for info in pkgutil.iter_modules(contrib.__path__):
            if info.name.startswith("_"):
                continue
            try:
                mod = importlib.import_module(
                    f"xstate_statemachine.contrib.{info.name}"
                )
            except MissingExtraError:
                continue  # extra not installed here; its CI cell covers it
            with self.subTest(subpackage=info.name):
                missing = sorted(
                    n
                    for n in getattr(mod, "__all__", ())
                    if n not in documented
                )
                self.assertEqual(missing, [], info.name)

    def test_every_contrib_subpackage_has_a_table_row(self) -> None:
        import xstate_statemachine.contrib as contrib

        section = _contrib_section()
        for info in pkgutil.iter_modules(contrib.__path__):
            if not info.name.startswith("_"):
                self.assertIn(f"contrib.{info.name}", section, info.name)

    def test_no_todo_or_fixme_comments_in_src(self) -> None:
        """No open TODO/FIXME/XXX comments ship in the library.

        📝 Comment tokens only: the code generators legitimately WRITE
        `# TODO: implement` into the scaffolds they emit for users, as
        string literals. Those are output, not unfinished library work.
        """
        marker = re.compile(r"\b(TODO|FIXME|XXX)\b")
        found = []
        for path in sorted((ROOT / "src").rglob("*.py")):
            source = path.read_bytes()
            for tok in tokenize.tokenize(io.BytesIO(source).readline):
                if tok.type == tokenize.COMMENT and marker.search(tok.string):
                    found.append(f"{path.name}:{tok.start[0]}")
        self.assertEqual(found, [])

    def test_readme_states_semver_and_python_range(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Semantic Versioning", readme)
        self.assertIn("Supported Python: 3.9 – 3.14", readme)
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('requires-python = ">=3.9"', pyproject)

    def test_security_md_has_plugin_trust_model(self) -> None:
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        self.assertIn("### Third-party plugins", text)
        self.assertIn("in-process with full privileges", text)
        self.assertIn("XSM_DISABLE_PLUGIN_DISCOVERY", text)

    def test_windows_setup_note_is_accurate(self) -> None:
        """`python -m xstate_statemachine setup` is documented and real."""
        cli_md = (ROOT / "docs" / "_guide" / "cli.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("python -m xstate_statemachine setup", cli_md)
        from xstate_statemachine.cli.args import get_parser

        ns = get_parser().parse_args(["setup"])
        self.assertEqual(ns.subcommand, "setup")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
