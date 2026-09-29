"""#287 E1: human-in-the-loop as a DURABLE waiting state.

The agent parks in `awaiting_human`, is persisted to `SQLiteStore`, the
process "restarts" (a fresh interpreter from the store), and
`HUMAN_APPROVED` resumes it to `done`. The `after` escalation of
`awaiting_human` is a persisted deadline that `DueTimerScanner` fires with
an injected `now`. Both engines.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest

from src.xstate_statemachine import SimulatedClock, create_machine

from ..conftest import requires_extra
from .conftest import weather_tools

pytestmark = requires_extra("agents")
pytest.importorskip("pydantic")

from src.xstate_statemachine.contrib.agents import (  # noqa: E402
    TOOL_LOOP,
    FakeModel,
    agent_logic,
    run_agent,
    run_agent_sync,
)
from src.xstate_statemachine.persistence import (  # noqa: E402
    DueTimerScanner,
    SQLiteStore,
)

T0 = 1_800_000_000.0
EMAIL = {"tool": "send_email", "args": {"to": "ops@x", "body": "hi"}}


def _machine(model: Any, reg: Any, **kw: Any) -> Any:
    return create_machine(
        TOOL_LOOP, logic=agent_logic(model, reg, human_timeout_s=3600, **kw)
    )


class TestDurableHumanSync:
    def test_persist_restart_approve_complete(self, tmp_path) -> None:
        reg, ran = weather_tools()
        store = SQLiteStore(tmp_path / "agents.db")
        model = FakeModel([EMAIL, {"text": "Mail sent."}], is_async=False)
        m = _machine(model, reg)

        first = run_agent_sync(
            m,
            prompt="mail ops",
            store=store,
            key="agent:1",
            clock=SimulatedClock(wall_start=T0),
        )
        assert first.waiting and ran["send_email"] == 0
        rec = store.load("agent:1")
        assert rec is not None and rec.deadlines  # humanTimeout persisted
        snap = json.loads(rec.snapshot)
        assert snap["state_ids"] == ["toolLoop.awaiting_human"]

        # 🔁 "restart": a new process builds a new machine object, same chart
        m2 = _machine(model, reg)
        second = run_agent_sync(m2, store=store, key="agent:1", approve=True)
        assert second.final_state == "toolLoop.done"
        assert second.output == "Mail sent."
        assert ran["send_email"] == 1
        assert not store.load("agent:1").deadlines

    def test_escalation_fires_via_due_timer_scanner(self, tmp_path) -> None:
        reg, ran = weather_tools()
        store = SQLiteStore(tmp_path / "agents.db")
        model = FakeModel([EMAIL], is_async=False)
        m = _machine(model, reg)
        run_agent_sync(
            m,
            prompt="mail ops",
            store=store,
            key="agent:2",
            clock=SimulatedClock(wall_start=T0),
        )
        scanner = DueTimerScanner(store, lambda k: m)
        assert scanner.run_once(now=T0 + 3599) == 0  # not due yet
        assert scanner.run_once(now=T0 + 3601) == 1
        snap = json.loads(store.load("agent:2").snapshot)
        assert snap["state_ids"] == ["toolLoop.error"]
        assert snap["context"]["error"]["kind"] == "human_timeout"
        assert ran["send_email"] == 0

    def test_approval_after_escalation_is_ignored(self, tmp_path) -> None:
        reg, ran = weather_tools()
        store = SQLiteStore(tmp_path / "agents.db")
        m = _machine(FakeModel([EMAIL], is_async=False), reg)
        run_agent_sync(
            m,
            prompt="p",
            store=store,
            key="k",
            clock=SimulatedClock(wall_start=T0),
        )
        DueTimerScanner(store, lambda k: m).run_once(now=T0 + 7200)
        late = run_agent_sync(m, store=store, key="k", approve=True)
        assert late.final_state == "toolLoop.error"
        assert ran["send_email"] == 0


class TestDurableHumanAsync:
    def test_persist_restart_approve_complete(self, tmp_path) -> None:
        reg, ran = weather_tools()
        store = SQLiteStore(tmp_path / "agents.db")

        async def go() -> Any:
            model = FakeModel([EMAIL, {"text": "Mail sent."}])
            first = await run_agent(
                _machine(model, reg),
                prompt="mail ops",
                store=store,
                key="a:1",
                timeout_s=5,
            )
            assert first.waiting and ran["send_email"] == 0
            second = await run_agent(
                _machine(model, reg),
                store=store,
                key="a:1",
                approve=True,
                timeout_s=5,
            )
            return second

        res = asyncio.run(go())
        assert res.final_state == "toolLoop.done" and ran["send_email"] == 1

    def test_store_and_key_go_together(self) -> None:
        from src.xstate_statemachine.contrib.agents import AgentConfigError

        with pytest.raises(AgentConfigError):
            asyncio.run(run_agent(model=FakeModel([]), key="k"))
