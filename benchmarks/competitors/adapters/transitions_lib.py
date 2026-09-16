"""Benchmark adapter for the ``transitions`` library (v0.9.3).

Uses ``transitions.Machine`` for flat machines, ``transitions.extensions.
HierarchicalMachine`` for nested/parallel machines, and ``transitions.
extensions.asyncio.AsyncMachine`` for the async scenario.

All machine construction happens in the ``setup_*`` functions; the returned
hot function only drives transitions/events, per the benchmark contract.
"""

import asyncio
import time

import transitions
from transitions import Machine
from transitions.extensions import HierarchicalMachine
from transitions.extensions.asyncio import AsyncMachine
from transitions.extensions.states import Timeout, add_state_features

LIB_NAME = "transitions"
LIB_VERSION = transitions.__version__

CAPABILITY_NOTES: dict[str, str] = {}


@add_state_features(Timeout)
class _TimeoutMachine(Machine):
    """Machine composed with the native ``Timeout`` state mixin, used for S7."""


# ---------------------------------------------------------------------------
# Shared machine configs
# ---------------------------------------------------------------------------


def _flat_toggle_config():
    states = ["A", "B"]
    trans = [
        {"trigger": "toggle", "source": "A", "dest": "B"},
        {"trigger": "toggle", "source": "B", "dest": "A"},
    ]
    return states, trans


def _hierarchical_config():
    """3-level nested config: root > a/b > a1/a2, b1/b2."""
    states = [
        {
            "name": "a",
            "initial": "a1",
            "children": [{"name": "a1"}, {"name": "a2"}],
        },
        {
            "name": "b",
            "initial": "b1",
            "children": [{"name": "b1"}, {"name": "b2"}],
        },
    ]
    trans = [
        {"trigger": "to_b2", "source": "a_a1", "dest": "b_b2"},
        {"trigger": "to_a1", "source": "b_b2", "dest": "a_a1"},
        # keep a full round-trip cycle usable regardless of starting side
        {"trigger": "to_a2", "source": "a_a1", "dest": "a_a2"},
        {"trigger": "back_a1", "source": "a_a2", "dest": "a_a1"},
    ]
    return states, trans


def _parallel_config():
    states = [
        {
            "name": "root",
            "parallel": [
                {
                    "name": "r1",
                    "initial": "x",
                    "children": [{"name": "x"}, {"name": "y"}],
                },
                {
                    "name": "r2",
                    "initial": "p",
                    "children": [{"name": "p"}, {"name": "q"}],
                },
            ],
        }
    ]
    trans = [
        {"trigger": "toggle1", "source": "root_r1_x", "dest": "root_r1_y"},
        {"trigger": "toggle1", "source": "root_r1_y", "dest": "root_r1_x"},
        {"trigger": "toggle2", "source": "root_r2_p", "dest": "root_r2_q"},
        {"trigger": "toggle2", "source": "root_r2_q", "dest": "root_r2_p"},
    ]
    return states, trans


class _Model:
    """Plain model object; transitions attaches ``state`` + trigger methods."""


# ---------------------------------------------------------------------------
# S1 flat_toggle
# ---------------------------------------------------------------------------


def setup_S1():
    states, trans = _flat_toggle_config()
    model = _Model()
    Machine(
        model=model,
        states=states,
        transitions=trans,
        initial="A",
        auto_transitions=False,
        ignore_invalid_triggers=False,
    )

    def hot(n: int) -> None:
        for _ in range(n):
            model.toggle()
        expected = "A" if n % 2 == 0 else "B"
        assert model.state == expected

    return hot


# ---------------------------------------------------------------------------
# S2 guarded_context
# ---------------------------------------------------------------------------


def setup_S2():
    states, _ = _flat_toggle_config()
    trans = [
        {
            "trigger": "toggle",
            "source": "A",
            "dest": "B",
            "conditions": "below_limit",
            "after": "increment",
        },
        {
            "trigger": "toggle",
            "source": "B",
            "dest": "A",
            "conditions": "below_limit",
            "after": "increment",
        },
    ]

    class Counter(_Model):
        """Model owns the counter, guard and action -- the idiomatic shape."""

        def __init__(self, limit: int) -> None:
            self.counter = 0
            self.limit = limit

        def below_limit(self) -> bool:
            return self.counter < self.limit

        def increment(self) -> None:
            self.counter += 1

    def hot(n: int) -> None:
        # Fresh model per call so the counter starts at 0 -- the same
        # shape as every other adapter's S2 (which also build per call).
        # The guard is exercised on every event and never blocks.
        model = Counter(limit=n + 1)
        Machine(
            model=model,
            states=states,
            transitions=trans,
            initial="A",
            auto_transitions=False,
            ignore_invalid_triggers=False,
        )
        toggle = model.toggle
        for _ in range(n):
            toggle()
        assert model.counter == n

    return hot


# ---------------------------------------------------------------------------
# S3 hierarchical
# ---------------------------------------------------------------------------


def setup_S3():
    states, trans = _hierarchical_config()
    model = _Model()
    HierarchicalMachine(
        model=model,
        states=states,
        transitions=trans,
        initial="a_a1",
        auto_transitions=False,
        ignore_invalid_triggers=False,
    )

    def hot(n: int) -> None:
        for _ in range(n):
            model.to_b2()
            model.to_a1()
        assert model.state == "a_a1"

    return hot


# ---------------------------------------------------------------------------
# S4 parallel
# ---------------------------------------------------------------------------


def setup_S4():
    states, trans = _parallel_config()
    model = _Model()
    HierarchicalMachine(
        model=model,
        states=states,
        transitions=trans,
        initial="root",
        auto_transitions=False,
        ignore_invalid_triggers=False,
    )

    def hot(n: int) -> None:
        for _ in range(n):
            model.toggle1()
            model.toggle2()
        expected = (
            ["root_r1_x", "root_r2_p"]
            if n % 2 == 0
            else [
                "root_r1_y",
                "root_r2_q",
            ]
        )
        assert model.state == expected

    return hot


# ---------------------------------------------------------------------------
# S5 construction
# ---------------------------------------------------------------------------


def setup_S5():
    states, trans = _hierarchical_config()

    def hot(n: int) -> None:
        last_state = None
        for _ in range(n):
            model = _Model()
            HierarchicalMachine(
                model=model,
                states=states,
                transitions=trans,
                initial="a_a1",
                auto_transitions=False,
                ignore_invalid_triggers=False,
            )
            last_state = model.state
        assert last_state == "a_a1"

    return hot


# ---------------------------------------------------------------------------
# S6 many_instances
# ---------------------------------------------------------------------------


def setup_S6():
    states, trans = _flat_toggle_config()

    def hot(n: int) -> None:
        # Construct 1,000 independent machine instances and send 1 event to
        # each, inside the timed region, per the scenario definition.
        models = []
        for _ in range(1000):
            model = _Model()
            Machine(
                model=model,
                states=states,
                transitions=trans,
                initial="A",
                auto_transitions=False,
                ignore_invalid_triggers=False,
            )
            models.append(model)
        for model in models:
            model.toggle()
        assert all(model.state == "B" for model in models)

    return hot


# ---------------------------------------------------------------------------
# S7 delayed_transition
# ---------------------------------------------------------------------------


def setup_S7():
    # transitions has a native ``Timeout`` state mixin (transitions.extensions.
    # states.Timeout) composed onto a custom Machine via ``add_state_features``;
    # it starts a threading.Timer on state entry and fires ``on_timeout`` when
    # it expires. Used here with a ~1ms timeout to mirror the other libraries'
    # delayed-transition scenario.
    def hot(n: int) -> None:
        for _ in range(n):
            model = _Model()
            done = {"fired": False}

            def _on_timeout(**kwargs):
                model.go()
                done["fired"] = True

            # "start" is a plain (non-timeout) initial state; entering "A" via
            # a real transition triggers State.enter(), which is what starts
            # the Timeout mixin's threading.Timer. Constructing directly with
            # initial="A" would not call enter() and the timer would never
            # start.
            states = [
                "start",
                {"name": "A", "timeout": 0.001, "on_timeout": _on_timeout},
                "B",
            ]
            trans = [
                {"trigger": "arm", "source": "start", "dest": "A"},
                {"trigger": "go", "source": "A", "dest": "B"},
            ]
            machine = _TimeoutMachine(
                model=model,
                states=states,
                transitions=trans,
                initial="start",
                auto_transitions=False,
                ignore_invalid_triggers=False,
            )
            model.arm()
            while not done["fired"]:
                time.sleep(0.0002)
            assert model.state == "B"
            del machine

    return hot


# ---------------------------------------------------------------------------
# S8 async_dispatch
# ---------------------------------------------------------------------------


def setup_S8():
    states, trans = _flat_toggle_config()
    model = _Model()
    AsyncMachine(
        model=model,
        states=states,
        transitions=trans,
        initial="A",
        auto_transitions=False,
        ignore_invalid_triggers=False,
    )

    async def _run(n: int) -> None:
        for _ in range(n):
            await model.toggle()

    def hot(n: int) -> None:
        asyncio.run(_run(n))
        expected = "A" if n % 2 == 0 else "B"
        assert model.state == expected

    return hot
