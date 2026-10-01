"""Put the example directory on ``sys.path`` so ``import app`` works."""

import importlib.util
import sys
from pathlib import Path

import pytest

EXAMPLE_DIR = str(Path(__file__).resolve().parents[1])
if EXAMPLE_DIR not in sys.path:
    sys.path.insert(0, EXAMPLE_DIR)


@pytest.fixture
def fulfilment(tmp_path):
    """A fresh app on the fake broker, Celery eager when installed."""
    import app

    has_celery = importlib.util.find_spec("celery") is not None
    a = app.build_app("fake", tmp_path, celery=has_celery)
    yield a
    a.close()
