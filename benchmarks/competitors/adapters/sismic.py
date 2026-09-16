"""Benchmark adapter for `sismic` (v1.6.11).

sismic is a Python statechart library built around a YAML/dict statechart
definition (`sismic.model.Statechart`) and a discrete-event `Interpreter`
(`sismic.interpreter.Interpreter`) that follows a semantics close to SCXML.

Machines here are built with `sismic.io.import_from_yaml`, which is the
idiomatic way to define a statechart in sismic. Guards/actions are Python
expressions/statements evaluated by the default `PythonEvaluator` against a
context (initialized via the `preamble` field, exposed at `interpreter.context`).

Delayed transitions use the `after(seconds)` guard function together with a
`SimulatedClock`, which is manually advanced -- this is sismic's idiomatic,
deterministic way to test timeouts without real sleeping.

sismic has no async engine and no notion of independent lightweight
"instances" beyond building N `Interpreter` objects, so S6 just builds N
interpreters (S1-shaped) and sends one event to each.
"""

from __future__ import annotations

import sismic
from sismic.interpreter import Interpreter
from sismic.io import import_from_yaml

LIB_NAME = "sismic"
LIB_VERSION = sismic.__version__

CAPABILITY_NOTES = {
    "S4": "supported natively via 'parallel states' in the statechart YAML",
    "S8": "sismic has no native asyncio interpreter loop; unsupported",
}


# ---------------------------------------------------------------------------
# YAML statechart definitions
# ---------------------------------------------------------------------------

_S1_YAML = """
statechart:
  name: flat_toggle
  root state:
    name: root
    initial: A
    states:
      - name: A
        transitions:
          - target: B
            event: toggle
      - name: B
        transitions:
          - target: A
            event: toggle
"""

_S2_YAML = """
statechart:
  name: guarded_context
  preamble: counter = 0
  root state:
    name: root
    initial: A
    states:
      - name: A
        transitions:
          - target: B
            event: toggle
            guard: counter < N
            action: counter += 1
      - name: B
        transitions:
          - target: A
            event: toggle
            guard: counter < N
            action: counter += 1
"""

_S3_YAML = """
statechart:
  name: hierarchical
  root state:
    name: root
    initial: a
    states:
      - name: a
        initial: a1
        states:
          - name: a1
            transitions:
              - target: b2
                event: cross
          - name: a2
      - name: b
        initial: b1
        states:
          - name: b1
          - name: b2
            transitions:
              - target: a1
                event: back
"""

_S4_YAML = """
statechart:
  name: parallel
  root state:
    name: root
    parallel states:
      - name: r1
        initial: r1a
        states:
          - name: r1a
            transitions:
              - target: r1b
                event: t1
          - name: r1b
            transitions:
              - target: r1a
                event: t1
      - name: r2
        initial: r2a
        states:
          - name: r2a
            transitions:
              - target: r2b
                event: t2
          - name: r2b
            transitions:
              - target: r2a
                event: t2
"""

_S7_YAML = """
statechart:
  name: delayed_transition
  root state:
    name: root
    initial: idle
    states:
      - name: idle
        transitions:
          - target: done
            guard: after(0.001)
      - name: done
        transitions:
          - target: idle
            action: send('reset')
"""


def _s1_statechart():
    return import_from_yaml(_S1_YAML)


def _s2_statechart(n: int):
    # N is baked into the guard expression, so patch it per-call at import time.
    text = _S2_YAML.replace("counter < N", "counter < {}".format(n))
    return import_from_yaml(text)


def _s3_statechart():
    return import_from_yaml(_S3_YAML)


def _s4_statechart():
    return import_from_yaml(_S4_YAML)


def _s7_statechart():
    return import_from_yaml(_S7_YAML)


# ---------------------------------------------------------------------------
# S1: flat_toggle
# ---------------------------------------------------------------------------


def setup_S1():
    statechart = _s1_statechart()
    interpreter = Interpreter(statechart)
    interpreter.execute()  # stabilize into initial state 'A'

    def hot(n: int) -> None:
        for i in range(n):
            interpreter.queue("toggle").execute()
        expected = "A" if n % 2 == 0 else "B"
        assert expected in interpreter.configuration
        assert (
            "B" if expected == "A" else "A"
        ) not in interpreter.configuration

    return hot


# ---------------------------------------------------------------------------
# S2: guarded_context
# ---------------------------------------------------------------------------


def setup_S2():
    def hot(n: int) -> None:
        statechart = _s2_statechart(n)
        interpreter = Interpreter(statechart)
        interpreter.execute()
        for i in range(n):
            interpreter.queue("toggle").execute()
        # guard blocks once counter reaches n, so exactly n increments happen
        assert interpreter.context["counter"] == n

    return hot


# ---------------------------------------------------------------------------
# S3: hierarchical
# ---------------------------------------------------------------------------


def setup_S3():
    statechart = _s3_statechart()
    interpreter = Interpreter(statechart)
    interpreter.execute()  # stabilize into a1

    def hot(n: int) -> None:
        for i in range(n):
            interpreter.queue("cross").execute()
            interpreter.queue("back").execute()
        assert "a1" in interpreter.configuration
        assert "root" in interpreter.configuration

    return hot


# ---------------------------------------------------------------------------
# S4: parallel
# ---------------------------------------------------------------------------


def setup_S4():
    statechart = _s4_statechart()
    interpreter = Interpreter(statechart)
    interpreter.execute()  # stabilize into r1a / r2a

    def hot(n: int) -> None:
        for i in range(n):
            interpreter.queue("t1").execute()
            interpreter.queue("t2").execute()
        expected_r1 = "r1a" if n % 2 == 0 else "r1b"
        expected_r2 = "r2a" if n % 2 == 0 else "r2b"
        assert expected_r1 in interpreter.configuration
        assert expected_r2 in interpreter.configuration

    return hot


# ---------------------------------------------------------------------------
# S5: construction
# ---------------------------------------------------------------------------


def setup_S5():
    def hot(n: int) -> None:
        last_interpreter = None
        for i in range(n):
            statechart = import_from_yaml(_S3_YAML)
            last_interpreter = Interpreter(statechart)
            last_interpreter.execute()
        assert "a1" in last_interpreter.configuration

    return hot


# ---------------------------------------------------------------------------
# S6: many_instances
# ---------------------------------------------------------------------------


def setup_S6():
    statechart = _s1_statechart()

    def hot(n: int) -> None:
        interpreters = []
        for i in range(n):
            interp = Interpreter(statechart)
            interp.execute()
            interp.queue("toggle").execute()
            interpreters.append(interp)
        assert all("B" in it.configuration for it in interpreters)
        assert len(interpreters) == n

    return hot


# ---------------------------------------------------------------------------
# S7: delayed_transition
# ---------------------------------------------------------------------------


def setup_S7():
    statechart = _s7_statechart()
    interpreter = Interpreter(statechart)
    interpreter.execute()  # stabilize into idle

    def hot(n: int) -> None:
        for i in range(n):
            interpreter.clock.time += 0.002
            # execute() runs to a stable configuration: idle -> done (after guard
            # fires) -> idle again (via the internal 'reset' event), all in one call.
            interpreter.execute()
            assert "idle" in interpreter.configuration

    return hot


# ---------------------------------------------------------------------------
# S8: async_dispatch -- unsupported
# ---------------------------------------------------------------------------


def setup_S8():
    return None


if __name__ == "__main__":
    for name in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"):
        setup_fn = globals()["setup_{}".format(name)]
        hot_fn = setup_fn()
        if hot_fn is None:
            print(
                "{}: unsupported ({})".format(
                    name, CAPABILITY_NOTES.get(name, "n/a")
                )
            )
            continue
        hot_fn(50)
        print("{}: OK".format(name))
