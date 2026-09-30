"""Seeded-bug demo for `model_test` (#271) -- THIS TEST IS MEANT TO FAIL.

`refund.json` lets a second `REFUND` drive `total` negative, but only after
`ADD, PAY, REFUND` -- a 4-event sequence. Hypothesis finds it, shrinks it,
and `model_test` writes the minimal sequence as an `xsm simulate --script`
file (`failing.json` here, or in `--xsm-failing-dir`):

    python -m pytest tests/contrib/testing/examples/test_refund_bug.py
    xsm simulate tests/contrib/testing/examples/refund.json \
        --script tests/contrib/testing/examples/failing.json

Excluded from the normal suite by this folder's `conftest.py`; it runs
only when named explicitly on the command line.
"""

import pathlib

import pytest

pytest.importorskip("hypothesis")

from xstate_statemachine.contrib.testing import model_test  # noqa: E402

TestRefund = model_test(
    pathlib.Path(__file__).with_name("refund.json"),
    invariants={
        "total never negative": lambda interp: interp.context["total"] >= 0
    },
)
