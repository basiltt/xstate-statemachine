# tests/contrib/testing/test_fake_broker.py
"""#272: the `[testing]` import path re-exports the core fake broker and
the replay helpers."""

from __future__ import annotations

import asyncio
import unittest

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("testing")

from src.xstate_statemachine import create_machine  # noqa: E402
from src.xstate_statemachine.contrib.testing import (  # noqa: E402
    FakeBrokerAdapter,
    assert_replay_consistent,
    replay,
)
from src.xstate_statemachine.eda import Envelope  # noqa: E402
from src.xstate_statemachine.eda import fake as core_fake  # noqa: E402
from src.xstate_statemachine.persistence import (  # noqa: E402
    MemoryLog,
    TransitionLogPlugin,
    TransitionRecord,
    persisted,
    MemoryStore,
)

CFG = {
    "id": "t",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {"on": {"BACK": "a"}}},
}


class TestReexports(unittest.TestCase):
    def test_same_object_as_core(self) -> None:
        self.assertIs(FakeBrokerAdapter, core_fake.FakeBrokerAdapter)
        from src.xstate_statemachine.persistence import log

        self.assertIs(replay, log.replay)

    def test_fake_works_from_the_testing_path(self) -> None:
        b = FakeBrokerAdapter()
        asyncio.run(b.publish("t", Envelope.new(type="x")))
        self.assertEqual(len(b.published), 1)


class TestReplayConsistent(unittest.TestCase):
    def _log(self) -> MemoryLog:
        log = MemoryLog()
        with persisted(
            MemoryStore(),
            "k",
            create_machine(CFG),
            plugins=[TransitionLogPlugin(log)],
        ) as i:
            i.send("GO")
            i.send("BACK")
        return log

    def test_consistent_from_store_and_records(self) -> None:
        log = self._log()
        i = assert_replay_consistent(create_machine(CFG), log, key="k")
        self.assertIn("t.a", i.current_state_ids)
        i.stop()
        i = assert_replay_consistent(create_machine(CFG), log.read("k"))
        i.stop()
        with self.assertRaises(ValueError):
            assert_replay_consistent(create_machine(CFG), log)

    def test_divergence_is_an_assertion(self) -> None:
        log = self._log()
        changed = dict(CFG, states={"a": {"on": {"GO": "a"}}, "b": {}})
        with self.assertRaises(AssertionError):
            assert_replay_consistent(create_machine(changed), log, key="k")
