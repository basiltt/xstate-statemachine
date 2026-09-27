"""Shared fixtures for `tests/contrib/`.

Each subfolder here is run by one CI cell that installs exactly one extra.
`requires_extra("fastapi")` skips a test (with the pip command in the reason)
when the extra's modules are not importable, so the same test files are
collectable in every cell and in a bare checkout.
"""

from __future__ import annotations

import importlib.util

import pytest

from src.xstate_statemachine.contrib._registry import EXTRAS


def requires_extra(extra: str):
    """``@requires_extra("fastapi")`` -- skip unless the extra is installed."""
    missing = [
        m for m in EXTRAS[extra].modules if importlib.util.find_spec(m) is None
    ]
    return pytest.mark.skipif(
        bool(missing),
        reason=(
            f"extra [{extra}] not installed (missing {', '.join(missing)}); "
            f'pip install "xstate-statemachine[{extra}]"'
        ),
    )
