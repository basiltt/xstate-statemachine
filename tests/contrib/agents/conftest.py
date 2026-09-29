"""Shared helpers for `tests/contrib/agents/` (#287, #290)."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from ..conftest import requires_extra

pytestmark = requires_extra("agents")


def weather_tools(**kw: Any) -> Any:
    from src.xstate_statemachine.contrib.agents import tool, tool_registry

    ran: Dict[str, int] = {"get_weather": 0, "send_email": 0, "secret": 0}

    def get_weather(city: str) -> Dict[str, Any]:
        """Current weather for a city."""
        ran["get_weather"] += 1
        return {"city": city, "sky": "sunny", "api_key": "sk-LEAK"}

    def send_email(to: str, body: str) -> str:
        """Send an e-mail (a side effect)."""
        ran["send_email"] += 1
        return f"sent to {to}"

    def secret() -> str:
        """Never allowed in TOOL_LOOP states narrowed to get_weather."""
        ran["secret"] += 1
        return "boom"

    reg = tool_registry(
        tool(get_weather, timeout_s=2),
        tool(send_email, timeout_s=2, side_effect=True),
        tool(secret, timeout_s=2),
        **kw,
    )
    return reg, ran


@pytest.fixture
def tools_and_ran():
    return weather_tools()
