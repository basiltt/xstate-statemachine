"""Put the example directory on ``sys.path`` so ``import app`` works,
and skip the whole suite cleanly without the ``[flask]`` extra."""

import sys
from pathlib import Path

import pytest

pytest.importorskip("flask")

EXAMPLE_DIR = str(Path(__file__).resolve().parents[1])
if EXAMPLE_DIR not in sys.path:
    sys.path.insert(0, EXAMPLE_DIR)
