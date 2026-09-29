"""Put the example directory on ``sys.path`` so ``import bot`` works."""

import sys
from pathlib import Path

EXAMPLE_DIR = str(Path(__file__).resolve().parents[1])
if EXAMPLE_DIR not in sys.path:
    sys.path.insert(0, EXAMPLE_DIR)
