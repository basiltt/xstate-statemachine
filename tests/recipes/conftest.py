# tests/recipes/conftest.py
"""Shared helpers for the recipe tests (#308).

Each recipe lives in ``examples/recipes/<name>/`` as plain modules a user
copies; the tests import them by putting that folder on ``sys.path`` --
the same way a user runs them -- and every module name is unique across
recipes so the imports cannot shadow each other.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Dict

import pytest

ROOT = Path(__file__).resolve().parents[2]
RECIPES = ROOT / "examples" / "recipes"
PAGES = ROOT / "docs" / "_guide" / "recipes"

# 📦 The examples import the INSTALLED name; make this checkout's `src`
#    win over any other editable install.
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


def load_recipe(name: str, module: str) -> Any:
    """Import ``examples/recipes/<name>/<module>.py``."""
    folder = str(RECIPES / name)
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return importlib.import_module(module)


def chart(name: str) -> Dict[str, Any]:
    return json.loads((RECIPES / name / "machine.json").read_text("utf-8"))


def requires(*modules: str) -> Any:
    """Skip (with the pip command) unless every module imports."""
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    return pytest.mark.skipif(
        bool(missing),
        reason=f"soft dependency missing: pip install {' '.join(missing)}",
    )
