"""Benchmark adapter for the ``python-statemachine`` library (v3.2.1).

Uses ``statemachine.StateMachine`` with ``State`` / ``State.Compound`` /
``State.Parallel`` nested-class declarations for hierarchical and parallel
machines, native ``Event(..., delay=...)`` for the delayed-transition
scenario, and the library's built-in async engine (auto-selected when a
callback is a coroutine function) for the async-dispatch scenario.

All machine construction happens in the ``setup_*`` functions; the returned
hot function only drives transitions/events, per the benchmark contract.
"""

import asyncio

import statemachine
from statemachine import State, StateMachine
from statemachine.event import Event

LIB_NAME = "python-statemachine"
LIB_VERSION = statemachine.__version__

CAPABILITY_NOTES: dict[str, str] = {}


# ---------------------------------------------------------------------------
# S1 flat_toggle
# ---------------------------------------------------------------------------


def setup_S1():
    class Flat(StateMachine):
        A = State(initial=True)
        B = State()
        toggle = A.to(B) | B.to(A)

    sm = Flat()

    def hot(n: int) -> None:
        for _ in range(n):
            sm.toggle()
        assert sm.current_state.id in ("A", "B")

    return hot


# ---------------------------------------------------------------------------
# S2 guarded_context
# ---------------------------------------------------------------------------


def setup_S2():
    class Guarded(StateMachine):
        allow_event_without_transition = True

        A = State(initial=True)
        B = State()
        toggle = A.to(B, cond="below_limit", after="increment") | B.to(
            A, cond="below_limit", after="increment"
        )

        def __init__(self, limit: int):
            self.counter = 0
            self.limit = limit
            super().__init__()

        def below_limit(self) -> bool:
            return self.counter < self.limit

        def increment(self) -> None:
            self.counter += 1

    def hot(n: int) -> None:
        sm = Guarded(limit=n + 1)  # never actually block the guard
        for _ in range(n):
            sm.toggle()
        assert sm.counter == n

    return hot


# ---------------------------------------------------------------------------
# S3 hierarchical
# ---------------------------------------------------------------------------


def _build_hierarchical():
    class Hier(StateMachine):
        class RootA(State.Compound, initial=True):
            A1 = State(initial=True)
            A2 = State()
            to_a2 = A1.to(A2)
            back_a1 = A2.to(A1)

        class RootB(State.Compound):
            B1 = State(initial=True)
            B2 = State()

        to_b2 = RootA.A2.to(RootB.B2)
        to_a1 = RootB.B2.to(RootA.A1)

    return Hier()


def setup_S3():
    sm = _build_hierarchical()

    def hot(n: int) -> None:
        for _ in range(n):
            sm.to_a2()
            sm.to_b2()
            sm.to_a1()
        assert "A1" in sm.current_state_value

    return hot


# ---------------------------------------------------------------------------
# S4 parallel
# ---------------------------------------------------------------------------


def setup_S4():
    class Par(StateMachine):
        class Root(State.Parallel, initial=True):
            class RegionX(State.Compound, initial=True):
                X1 = State(initial=True)
                X2 = State()
                toggle1 = X1.to(X2) | X2.to(X1)

            class RegionY(State.Compound, initial=True):
                Y1 = State(initial=True)
                Y2 = State()
                toggle2 = Y1.to(Y2) | Y2.to(Y1)

    sm = Par()

    def hot(n: int) -> None:
        for _ in range(n):
            sm.toggle1()
            sm.toggle2()
        csv = sm.current_state_value
        if n % 2 == 0:
            assert "X1" in csv and "Y1" in csv
        else:
            assert "X2" in csv and "Y2" in csv

    return hot


# ---------------------------------------------------------------------------
# S5 construction
# ---------------------------------------------------------------------------


def setup_S5():
    def hot(n: int) -> None:
        last = None
        for _ in range(n):
            sm = _build_hierarchical()
            last = sm.current_state_value
        assert "A1" in last

    return hot


# ---------------------------------------------------------------------------
# S6 many_instances
# ---------------------------------------------------------------------------


def setup_S6():
    class Flat(StateMachine):
        A = State(initial=True)
        B = State()
        toggle = A.to(B) | B.to(A)

    def hot(n: int) -> None:
        # Construct 1,000 independent machine instances and send 1 event to
        # each, inside the timed region, per the scenario definition.
        instances = [Flat() for _ in range(1000)]
        for sm in instances:
            sm.toggle()
        assert all(sm.current_state.id == "B" for sm in instances)

    return hot


# ---------------------------------------------------------------------------
# S7 delayed_transition
# ---------------------------------------------------------------------------


def setup_S7():
    class Delayed(StateMachine):
        A = State(initial=True)
        B = State(final=True)
        go = Event(A.to(B), delay=1)  # 1 ms native delay

    def hot(n: int) -> None:
        for _ in range(n):
            sm = Delayed()
            sm.send("go")
            assert sm.current_state.id == "B"

    return hot


# ---------------------------------------------------------------------------
# S8 async_dispatch
# ---------------------------------------------------------------------------


def setup_S8():
    class Async(StateMachine):
        A = State(initial=True)
        B = State()
        toggle = A.to(B) | B.to(A)

        async def on_toggle(self) -> None:
            pass

    sm = Async()

    async def _run(n: int) -> None:
        await sm.activate_initial_state()
        for _ in range(n):
            await sm.toggle()

    def hot(n: int) -> None:
        asyncio.run(_run(n))
        assert sm.current_state.id in ("A", "B")

    return hot
