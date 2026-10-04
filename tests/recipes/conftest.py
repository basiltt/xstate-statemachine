# tests/recipes/conftest.py
"""Shared helpers for the recipe tests (#308).

Each recipe lives in ``examples/recipes/<name>/`` as plain modules a user
copies; the tests import them by putting that folder on ``sys.path`` --
the same way a user runs them -- and every module name is unique across
recipes so the imports cannot shadow each other.
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path
from typing import Any, Callable, Dict

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


class Driver:
    """One test script on EITHER engine: ``send()``, ``wait(ms)``,
    ``value``. The async engine runs on a private loop and every call is
    made inside it (the interpreter is bound to its loop's thread)."""

    def __init__(self, engine: str, machine: Any) -> None:
        from xstate_statemachine import (
            Interpreter,
            SimulatedClock,
            SyncInterpreter,
        )

        self.clock = SimulatedClock()
        self.engine = engine
        if engine == "sync":
            self.i = SyncInterpreter(machine, clock=self.clock).start()
        else:
            self.loop = asyncio.new_event_loop()
            self.i = self.loop.run_until_complete(
                Interpreter(machine, clock=self.clock).start()
            )

    def run(self, call: Callable[[], Any]) -> Any:
        if self.engine == "sync":
            return call()

        async def _inside() -> Any:
            res = call()
            return await res if inspect.isawaitable(res) else res

        return self.loop.run_until_complete(_inside())

    def send(self, event: str, **kw: Any) -> Any:
        return self.run(lambda: self.i.send(event, wait=True, **kw))

    def wait(self, ms: float) -> None:
        self.run(lambda: self.clock.increment(ms))

    @property
    def value(self) -> Any:
        return self.i.value

    def close(self) -> None:
        """Idempotent: a test may close the driver itself (to time
        `stop()`); the fixture's teardown then finds it already closed."""
        if getattr(self, "_closed", False):
            return
        self._closed = True
        self.run(self.i.stop)
        if self.engine == "async":
            self.loop.close()
