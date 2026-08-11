# tests/tests_cli/test_postprocess.py
"""Tests for post-emit polish: imports, provenance, formatting (S1/S2)."""

import ast
import unittest

from src.xstate_statemachine.cli.postprocess import (
    apply_provenance,
    build_provenance_header,
    format_source,
    polish,
    prune_unused_imports,
)


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
        self.assertIn('"a": 1', formatted)
        ast.parse(formatted)

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
        self.assertIn('"a": 1', result)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
