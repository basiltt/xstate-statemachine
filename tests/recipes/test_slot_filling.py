# tests/recipes/test_slot_filling.py
"""Slot-filling recipe on BOTH engines, with a simulated clock."""

from __future__ import annotations

from typing import Any, List

import pytest

from .conftest import Driver, load_recipe

sf = load_recipe("slot_filling", "slot_filling")


@pytest.fixture(params=["sync", "async"])
def bot(request: Any) -> Any:
    said: List[str] = []
    d = Driver(request.param, sf.build_machine(said.append))
    d.said = said  # type: ignore[attr-defined]
    yield d
    d.close()


def test_slots_in_any_order_then_confirm(bot: Driver) -> None:
    bot.send("USER_SAID", name="Ann")
    assert bot.value == "collecting" and bot.said[-1] == sf.PROMPTS["date"]
    bot.send("USER_SAID", date="Fri", party_size=4)  # two slots, one turn
    assert bot.value == "confirming"
    assert bot.said[-1] == "Book 4 on Fri for Ann?"
    bot.send("YES")
    assert bot.value == "booked"


def test_no_clears_and_restarts(bot: Driver) -> None:
    bot.send("USER_SAID", name="Ann", date="Fri", party_size=2)
    bot.send("NO")
    assert bot.value == "collecting"
    assert bot.i.context["slots"] == dict.fromkeys(
        ("date", "party_size", "name")
    )


def test_silence_nudges_twice_then_abandons(bot: Driver) -> None:
    bot.send("USER_SAID", date="Fri")
    bot.wait(30_000)
    assert bot.value == "collecting" and bot.said[-1].startswith("Still")
    assert bot.i.context["nudges"] == 1  # exactly one nudge per silence
    bot.wait(30_000)
    assert bot.i.context["nudges"] == 2
    bot.wait(30_000)
    assert bot.value == "abandoned"


def test_an_answer_resets_the_silence_timer(bot: Driver) -> None:
    bot.wait(29_000)
    bot.send("USER_SAID", date="Fri")  # re-entry restarts `after`
    bot.wait(29_000)
    assert not any(s.startswith("Still") for s in bot.said)
    bot.wait(1_000)
    assert bot.said[-1].startswith("Still")


def test_empty_values_do_not_fill(bot: Driver) -> None:
    bot.send("USER_SAID", date="", party_size=None, bogus=1)
    assert sf.missing(bot.i.context) == ["date", "party_size", "name"]
