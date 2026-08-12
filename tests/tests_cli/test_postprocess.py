# tests/tests_cli/test_postprocess.py
"""Tests for post-emit polish: imports, provenance, formatting (S1/S2)."""

import ast
import importlib.util
import unittest

from src.xstate_statemachine.cli.postprocess import (
    apply_provenance,
    build_provenance_header,
    format_source,
    polish,
    prune_unused_imports,
)

# 📝 black is a DEVELOPMENT dependency, and `format_source` is best-effort by
#    design: without it, generated code is still valid and still faithful,
#    merely unformatted. Assertions about black's OUTPUT (double-quoted keys,
#    normalised spacing) therefore only hold where black is installed. CI's
#    test matrix installs the runtime plus pytest only, which is exactly the
#    runtime-only user this fallback exists to serve -- so these tests skip
#    there rather than fail. The behaviour that must hold EVERYWHERE (code is
#    parseable, imports are pruned, provenance is stamped) is asserted
#    unconditionally below.
_HAS_BLACK = importlib.util.find_spec("black") is not None


class TestPruneUnusedImports(unittest.TestCase):
    """Generated modules import a fixed helper set regardless of need."""

    def test_removes_unused_names_from_a_group(self) -> None:
        """Only the unused members of a from-import are dropped."""
        code = (
            "from typing import Any, Dict, Optional, Union\n"
            "\n"
            "x: Dict[str, Any] = {}\n"
        )
        result = prune_unused_imports(code)
        self.assertIn("Any", result)
        self.assertIn("Dict", result)
        self.assertNotIn("Optional", result)
        self.assertNotIn("Union", result)

    def test_drops_a_fully_unused_import_line(self) -> None:
        """An import with nothing used disappears entirely."""
        code = "import asyncio\nimport logging\n\nlogging.info('hi')\n"
        result = prune_unused_imports(code)
        self.assertNotIn("asyncio", result)
        self.assertIn("logging", result)

    def test_keeps_names_used_only_in_annotations(self) -> None:
        """A name used solely as a type annotation is still used."""
        code = (
            "from typing import Optional\n"
            "\n"
            "def f(x: Optional[int]) -> None:\n"
            "    pass\n"
        )
        self.assertIn("Optional", prune_unused_imports(code))

    def test_keeps_names_used_in_string_annotations(self) -> None:
        """Quoted annotations reference real names."""
        code = (
            "from typing import Optional\n"
            "\n"
            "def f(x: 'Optional[int]') -> None:\n"
            "    pass\n"
        )
        self.assertIn("Optional", prune_unused_imports(code))

    def test_never_touches_star_imports(self) -> None:
        """What a star import binds is not statically knowable."""
        code = "from os.path import *\n\nx = 1\n"
        self.assertIn("import *", prune_unused_imports(code))

    def test_respects_aliases(self) -> None:
        """An alias binds the asname, not the original name."""
        code = "import numpy as np\nimport json as j\n\nnp.array([1])\n"
        result = prune_unused_imports(code)
        self.assertIn("numpy as np", result)
        self.assertNotIn("json", result)

    def test_dotted_import_binds_root_name(self) -> None:
        """`import a.b` binds `a`, so using `a.b.c()` counts as used."""
        code = "import os.path\n\nos.path.join('a', 'b')\n"
        self.assertIn("os.path", prune_unused_imports(code))

    def test_invalid_source_is_returned_unchanged(self) -> None:
        """Pruning must never turn broken code into different broken code."""
        code = "def f(:\n"
        self.assertEqual(prune_unused_imports(code), code)

    def test_output_stays_parseable(self) -> None:
        """Pruning must not corrupt the module."""
        code = (
            "import logging\n"
            "from typing import Any, Dict, Optional\n"
            "\n"
            "logger = logging.getLogger(__name__)\n"
            "\n"
            "def f() -> Dict[str, Any]:\n"
            "    return {}\n"
        )
        ast.parse(prune_unused_imports(code))


class TestProvenance(unittest.TestCase):
    """A reader must be able to answer 'where from' and 'how to regenerate'."""

    HEADER = build_provenance_header(
        source_files=["orders.json"],
        template="pythonic-builder",
        version="0.7.0",
        command="xsm generate-template orders.json",
    )

    def test_header_records_source_template_version_and_command(self) -> None:
        """All four provenance facts are present."""
        for expected in (
            "orders.json",
            "pythonic-builder",
            "0.7.0",
            "xsm generate-template orders.json",
            "DO NOT EDIT",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.HEADER)

    def test_header_is_a_valid_docstring(self) -> None:
        """The header must parse as a module docstring."""
        tree = ast.parse(self.HEADER + "\nx = 1\n")
        self.assertIsInstance(ast.get_docstring(tree), str)

    def test_replaces_an_existing_docstring(self) -> None:
        """Regeneration must not stack docstrings."""
        code = '"""Old docstring."""\n\nimport os\n'
        result = apply_provenance(code, self.HEADER)
        self.assertNotIn("Old docstring", result)
        self.assertIn("orders.json", result)
        self.assertIn("import os", result)
        ast.parse(result)

    def test_prepends_when_no_docstring_exists(self) -> None:
        """A module without a docstring simply gains one."""
        code = "import os\n"
        result = apply_provenance(code, self.HEADER)
        self.assertIn("import os", result)
        self.assertEqual(
            ast.get_docstring(ast.parse(result)).splitlines()[0],
            "Generated state machine logic — DO NOT EDIT BY HAND.",
        )


class TestFormatting(unittest.TestCase):
    """Formatting is best-effort and must never break generation."""

    def test_formats_to_black_style(self) -> None:
        """Poorly formatted input comes back normalised."""
        formatted = format_source("x   =    {'a':1,   'b':2}\n")
        ast.parse(formatted)
        if not _HAS_BLACK:  # pragma: no cover — runtime-only environment
            self.skipTest("black not installed; formatting is best-effort")
        self.assertIn('"a": 1', formatted)

    def test_unformattable_input_is_returned_unchanged(self) -> None:
        """black declining must not lose the caller's code."""
        broken = "def f(:\n"
        self.assertEqual(format_source(broken), broken)


class TestPolishPipeline(unittest.TestCase):
    """The full pipeline: prune, stamp, format."""

    def test_pipeline_produces_clean_parseable_output(self) -> None:
        """Unused imports go, provenance arrives, formatting applies."""
        code = (
            "import asyncio\n"
            "from typing import Any, Dict, Optional\n"
            "\n"
            "def f() -> Dict[str, Any]:\n"
            "    return {'a':1}\n"
        )
        header = build_provenance_header(
            source_files=["m.json"],
            template="pythonic-functional",
            version="0.7.0",
            command="xsm generate-template m.json",
        )
        result = polish(code, header=header)

        ast.parse(result)
        self.assertNotIn("asyncio", result)
        self.assertNotIn("Optional", result)
        self.assertIn("m.json", result)
        if not _HAS_BLACK:  # pragma: no cover — runtime-only environment
            self.skipTest("black not installed; formatting is best-effort")
        self.assertIn('"a": 1', result)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()


class TestCombinedFileIsPolished(unittest.TestCase):
    """Single-file output must be formatted as one artifact.

    🏛️ Polishing has to happen AFTER the merge. Concatenating two
    already-formatted files leaves seams black never sees -- duplicate
    module docstrings and import blocks reflowed by de-duplication -- so
    `--file-count 1` output failed `black --check` for every template.
    """

    CONFIG = {
        "id": "n",
        "initial": "a",
        "states": {"a": {"entry": "logIt", "on": {"GO": "b"}}, "b": {}},
    }

    def test_every_template_produces_black_clean_single_file(self) -> None:
        """All five templates, sync and async, in combined-file mode."""
        import itertools
        import json
        import logging
        import os
        import subprocess
        import sys
        import tempfile

        from src.xstate_statemachine.cli.__main__ import main

        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)

        templates = (
            "pythonic-functional",
            "pythonic-builder",
            "pythonic-class",
            "class-json",
            "function-json",
        )

        for template, async_mode in itertools.product(
            templates, ("yes", "no")
        ):
            with self.subTest(template=template, async_mode=async_mode):
                with tempfile.TemporaryDirectory() as out:
                    source = os.path.join(out, "n.json")
                    with open(source, "w", encoding="utf-8") as handle:
                        json.dump(self.CONFIG, handle)

                    saved, sys.argv = sys.argv, [
                        "xsm",
                        "generate-template",
                        source,
                        "--template",
                        template,
                        "-o",
                        out,
                        "--force",
                        "-am",
                        async_mode,
                        "-fc",
                        "1",
                    ]
                    try:
                        main()
                    finally:
                        sys.argv = saved

                    produced = [
                        os.path.join(out, name)
                        for name in os.listdir(out)
                        if name.endswith(".py")
                    ]
                    self.assertTrue(produced, "no file was generated")

                    # 📝 The black-clean check needs black; the merge-seam
                    #    check below does not, and runs everywhere.
                    for path in produced if _HAS_BLACK else ():
                        result = subprocess.run(
                            [
                                sys.executable,
                                "-m",
                                "black",
                                "--check",
                                "-l",
                                "79",
                                path,
                            ],
                            capture_output=True,
                        )
                        self.assertEqual(
                            result.returncode, 0, f"{path} is not black-clean"
                        )

                    with open(produced[0], encoding="utf-8") as handle:
                        content = handle.read()
                    # 📝 Exactly one provenance docstring, not two merged.
                    self.assertEqual(content.count("DO NOT EDIT BY HAND"), 1)


class TestFormattingAvailability(unittest.TestCase):
    """The formatter probe is a hint and must never break generation."""

    def test_reports_true_when_black_is_installed(self) -> None:
        """The probe must agree with whether black is actually importable.

        📝 Asserted against the real environment rather than hardcoded to
        True: this hint exists to tell RUNTIME-ONLY users to install the
        ``format`` extra, so "correctly reports False" is as much a part of
        the contract as "correctly reports True" -- and a test that only
        ever ran with black installed could never catch an inverted probe.
        """
        from src.xstate_statemachine.cli.postprocess import (
            formatting_available,
        )

        self.assertEqual(formatting_available(), _HAS_BLACK)

    def test_survives_a_finder_that_raises(self) -> None:
        """`find_spec` can RAISE rather than return None.

        A broken parent package or a hostile meta-path finder makes
        `find_spec("black")` raise. That would crash the CLI for exactly
        the runtime-only users this hint exists to help.
        """
        import sys

        from src.xstate_statemachine.cli.postprocess import (
            formatting_available,
        )

        class _Blocker:
            """Meta-path finder that refuses to look up black."""

            def find_spec(self, name, path=None, target=None):
                if name == "black":
                    raise ImportError("blocked")
                return None

        sys.meta_path.insert(0, _Blocker())
        try:
            self.assertFalse(formatting_available())
        finally:
            sys.meta_path.pop(0)
