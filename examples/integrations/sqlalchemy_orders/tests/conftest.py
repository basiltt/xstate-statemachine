"""Put the example directory on ``sys.path`` so ``import sync_app`` works,
and skip the whole suite cleanly without the ``[sqlalchemy]`` extra."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("sqlalchemy")

EXAMPLE_DIR = str(Path(__file__).resolve().parents[1])
if EXAMPLE_DIR not in sys.path:
    sys.path.insert(0, EXAMPLE_DIR)
