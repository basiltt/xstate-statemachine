"""Runs ``order.feature`` (#272 BDD recipe); skipped without pytest-bdd."""

import pytest

pytest.importorskip("pytest_bdd")

from pytest_bdd import scenarios  # noqa: E402

scenarios("order.feature")
