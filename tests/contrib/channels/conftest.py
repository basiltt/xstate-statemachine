# tests/contrib/channels/conftest.py
"""[channels] fixtures: the shared Django test project."""

from __future__ import annotations

import asyncio
import sys
import warnings

from ..conftest import requires_extra
from ..django import bootstrap

pytestmark = requires_extra("channels")

if bootstrap.available():
    bootstrap.ensure()
    if sys.platform == "win32":  # pragma: no cover - platform specific
        # 📝 `channels.testing` imports daphne, whose __init__ switches the
        #    PROCESS-wide policy to WindowsSelectorEventLoopPolicy on
        #    Windows. Import it now and put the policy back, so the rest
        #    of the suite keeps the default Proactor loop.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            policy = asyncio.get_event_loop_policy()
            import channels.testing  # noqa: F401

            asyncio.set_event_loop_policy(policy)
else:  # pragma: no cover - bare checkout
    collect_ignore_glob = ["test_*.py"]
