# /tests/test_xstate_v5_parity.py
# -----------------------------------------------------------------------------
# 🧪 Test Suite: XState v5 Feature Parity
# -----------------------------------------------------------------------------
# Covers every gap closed in v0.6.0 per docs/FEATURE_GAP_ANALYSIS.md.
#
# 🏛️ Architecture decision: each class maps to ONE feature area and asserts the
# *observable behaviour*, not the implementation. Where a gap previously failed
# SILENTLY (accepted config that did nothing), the test also pins that the
# feature now actually takes effect — a test that only checks "no exception"
# would still pass against the broken version.
#
# Both engines are exercised wherever they implement the feature independently.
# -----------------------------------------------------------------------------
"""
Parity tests for XState v5 features added in v0.6.0.
"""

# -----------------------------------------------------------------------------
# 📦 Standard Library Imports
# -----------------------------------------------------------------------------
import asyncio
import json
import logging
import time
import unittest
from typing import Any, Dict, List

# -----------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -----------------------------------------------------------------------------
from src.xstate_statemachine import (
    ActionEnqueuer,
    Event,
    ImplementationMissingError,
    InvalidConfigError,
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    assign,
    cancel,
    choose,
    create_machine,
    emit,
    enqueue_actions,
    escalate,
    forward_to,
    get_next_snapshot,
    initial_transition,
    log,
    pure,
    pure_transition,
    raise_,
    send_parent,
    send_to,
    spawn_child,
    stop_child,
    to_promise,
    wait_for,
    wait_for_sync,
)
from src.xstate_statemachine.actions import is_builtin, resolve_builtin
from src.xstate_statemachine.models import GuardDefinition

# -----------------------------------------------------------------------------
# 🪵 Logger Configuration
# -----------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# 🛠️ Test Helpers
# -----------------------------------------------------------------------------
def build(config: Dict[str, Any], **logic_kwargs: Any) -> Any:
    """Builds a machine from a raw config plus inline logic.

    Args:
        config (Dict[str, Any]): The XState-style machine configuration.
        **logic_kwargs (Any): Forwarded to `MachineLogic`.

    Returns:
        Any: A constructed `MachineNode`.
    """
    return create_machine(config, logic=MachineLogic(**logic_kwargs))


def start(config: Dict[str, Any], **logic_kwargs: Any) -> SyncInterpreter:
    """Builds and starts a `SyncInterpreter` in one step.

    Args:
        config (Dict[str, Any]): The machine configuration.
        **logic_kwargs (Any): Forwarded to `MachineLogic`.

    Returns:
        SyncInterpreter: The started interpreter.
    """
    return SyncInterpreter(build(config, **logic_kwargs)).start()


async def settle(interpreter: Interpreter, event: Any) -> None:
    """Sends an event and lets the async run loop drain it.

    Args:
        interpreter (Interpreter): The running interpreter.
        event (Any): The event to dispatch.
    """
    await interpreter.send(event)
    for _ in range(10):
        await asyncio.sleep(0)
    if not interpreter._event_queue.empty():  # noqa: SLF001
        await asyncio.wait_for(
            interpreter._event_queue.join(), timeout=2.0  # noqa: SLF001
        )


TRUE = staticmethod(lambda ctx, evt: True)
FALSE = staticmethod(lambda ctx, evt: False)


# -----------------------------------------------------------------------------
# 🛡️ Guards
# -----------------------------------------------------------------------------
class TestGuardForms(unittest.IsolatedAsyncioTestCase):
    """Pins every guard spelling XState accepts.

    🐛 Regressions covered:
      - `cond` was ignored, so v4-style guarded transitions ran UNGUARDED.
      - The object form was used as a dict key, raising
        `TypeError: unhashable type: 'dict'` inside the event loop.
    """

    @staticmethod
    def _yes(_ctx: Any, _evt: Any) -> bool:
        """A guard that always passes."""
        return True

    @staticmethod
    def _no(_ctx: Any, _evt: Any) -> bool:
        """A guard that always blocks."""
        return False

    def test_cond_alias_blocks_transition(self) -> None:
        """A failing `cond` guard must block, not fire unconditionally."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "cond": "g"}}},
                "b": {},
            },
        }
        interpreter = start(config, guards={"g": self._no})

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_cond_alias_allows_transition(self) -> None:
        """A passing `cond` guard must still allow the transition."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "cond": "g"}}},
                "b": {},
            },
        }
        interpreter = start(config, guards={"g": self._yes})

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_object_guard_with_params(self) -> None:
        """`{"type", "params"}` must resolve and receive its params."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "guard": {"type": "g", "params": {"min": 3}},
                        }
                    }
                },
                "b": {},
            },
        }
        interpreter = start(
            config, guards={"g": lambda ctx, evt, params: params["min"] > 2}
        )

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    async def test_object_guard_does_not_kill_async_loop(self) -> None:
        """The object form must not tear down the async interpreter.

        🐛 Regression: the raw dict was used as a lookup key, so the
        `TypeError` escaped into the run loop and every later `send()` was
        silently dropped while `status` still read `"running"`.
        """
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": {"target": "b", "guard": {"type": "g"}},
                        "OTHER": "c",
                    }
                },
                "b": {},
                "c": {},
            },
        }
        interpreter = await Interpreter(
            build(config, guards={"g": self._no})
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await settle(interpreter, "E")
        await settle(interpreter, "OTHER")

        # Assert — the machine survived and kept processing.
        self.assertEqual("running", interpreter.status)
        self.assertEqual({"m.c"}, interpreter.current_state_ids)

    def test_composite_and_requires_all(self) -> None:
        """`and` must block when any child fails."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "guard": {
                                "type": "and",
                                "children": ["yes", "no"],
                            },
                        }
                    }
                },
                "b": {},
            },
        }
        interpreter = start(config, guards={"yes": self._yes, "no": self._no})

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_composite_or_requires_any(self) -> None:
        """`or` must pass when any child passes."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "guard": {
                                "type": "or",
                                "children": ["no", "yes"],
                            },
                        }
                    }
                },
                "b": {},
            },
        }
        interpreter = start(config, guards={"yes": self._yes, "no": self._no})

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_composite_not_inverts(self) -> None:
        """`not` must invert its single child."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "guard": {"type": "not", "children": ["no"]},
                        }
                    }
                },
                "b": {},
            },
        }
        interpreter = start(config, guards={"no": self._no})

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_nested_composite_guards(self) -> None:
        """Composite guards must nest arbitrarily."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "guard": {
                                "type": "and",
                                "children": [
                                    "yes",
                                    {"type": "not", "children": ["no"]},
                                ],
                            },
                        }
                    }
                },
                "b": {},
            },
        }
        interpreter = start(config, guards={"yes": self._yes, "no": self._no})

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_state_in_guard(self) -> None:
        """`stateIn` must read the live configuration."""
        # Arrange
        config = {
            "id": "p",
            "type": "parallel",
            "states": {
                "A": {
                    "initial": "a1",
                    "states": {"a1": {"on": {"T": "a2"}}, "a2": {}},
                },
                "B": {
                    "initial": "b1",
                    "states": {
                        "b1": {
                            "on": {
                                "TRY": {
                                    "target": "b2",
                                    "guard": {
                                        "type": "stateIn",
                                        "params": {"state": "#p.A.a2"},
                                    },
                                }
                            }
                        },
                        "b2": {},
                    },
                },
            },
        }
        interpreter = start(config)

        # Act / Assert — blocked while A is in a1.
        interpreter.send("TRY")
        self.assertIn("p.B.b1", interpreter.current_state_ids)

        # Act / Assert — allowed once A reaches a2.
        interpreter.send("T")
        interpreter.send("TRY")
        self.assertIn("p.B.b2", interpreter.current_state_ids)

    def test_dynamic_params_are_resolved(self) -> None:
        """A callable `params` must be invoked, not passed through raw."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "context": {"limit": 4},
            "states": {
                "a": {
                    "on": {
                        "E": {
                            "target": "b",
                            "guard": {
                                "type": "g",
                                "params": lambda args: {
                                    "limit": args["context"]["limit"]
                                },
                            },
                        }
                    }
                },
                "b": {},
            },
        }
        interpreter = start(
            config, guards={"g": lambda c, e, p: p["limit"] == 4}
        )

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_two_argument_guards_still_work(self) -> None:
        """Existing `(context, event)` guards must be unaffected."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "guard": "g"}}},
                "b": {},
            },
        }
        interpreter = start(config, guards={"g": self._yes})

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_missing_guard_still_raises(self) -> None:
        """An unimplemented guard must remain a loud configuration error."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"E": {"target": "b", "guard": "ghost"}}},
                "b": {},
            },
        }
        interpreter = start(config, guards={})

        # Act / Assert
        with self.assertRaises(ImplementationMissingError):
            interpreter.send("E")


# -----------------------------------------------------------------------------
# 🎯 Event Descriptors
# -----------------------------------------------------------------------------
class TestEventDescriptors(unittest.IsolatedAsyncioTestCase):
    """Pins wildcard, partial and forbidden event descriptors.

    🐛 Regression: event lookup was an exact dict-key test, so `"*"` and
    `"mouse.*"` keys never matched, and `on: {E: None}` vanished entirely,
    letting an ancestor handler fire.
    """

    def test_wildcard_matches_any_event(self) -> None:
        """A bare `*` must catch an otherwise unhandled event."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"*": "b"}}, "b": {}},
            }
        )

        # Act
        interpreter.send("ANYTHING_AT_ALL")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_partial_descriptor_matches_namespace(self) -> None:
        """`mouse.*` must match `mouse.click`."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"mouse.*": "b"}}, "b": {}},
            }
        )

        # Act
        interpreter.send("mouse.click")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_exact_beats_partial_beats_wildcard(self) -> None:
        """The most specific descriptor must win."""
        # Arrange
        config = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {
                        "*": "wild",
                        "mouse.*": "partial",
                        "mouse.click": "exact",
                    }
                },
                "wild": {},
                "partial": {},
                "exact": {},
            },
        }

        # Act / Assert — exact wins.
        interpreter = start(config)
        interpreter.send("mouse.click")
        self.assertEqual({"m.exact"}, interpreter.current_state_ids)

        # Act / Assert — partial beats wildcard.
        interpreter = start(config)
        interpreter.send("mouse.move")
        self.assertEqual({"m.partial"}, interpreter.current_state_ids)

        # Act / Assert — wildcard is the last resort.
        interpreter = start(config)
        interpreter.send("keyboard.press")
        self.assertEqual({"m.wild"}, interpreter.current_state_ids)

    def test_longer_partial_wins(self) -> None:
        """`a.b.*` must outrank `a.*` for `a.b.c`."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "s",
                "states": {
                    "s": {"on": {"a.*": "short", "a.b.*": "long"}},
                    "short": {},
                    "long": {},
                },
            }
        )

        # Act
        interpreter.send("a.b.c")

        # Assert
        self.assertEqual({"m.long"}, interpreter.current_state_ids)

    def test_forbidden_transition_blocks_ancestor(self) -> None:
        """`on: {E: None}` must consume the event at that level."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "p",
                "states": {
                    "p": {
                        "initial": "c",
                        "on": {"E": "out"},
                        "states": {"c": {"on": {"E": None}}},
                    },
                    "out": {},
                },
            }
        )

        # Act
        interpreter.send("E")

        # Assert — the ancestor's handler must NOT have fired.
        self.assertEqual({"m.p.c"}, interpreter.current_state_ids)

    def test_ancestor_still_fires_without_forbidden(self) -> None:
        """Control: the ancestor handles the event when not forbidden."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "p",
                "states": {
                    "p": {
                        "initial": "c",
                        "on": {"E": "out"},
                        "states": {"c": {}},
                    },
                    "out": {},
                },
            }
        )

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.out"}, interpreter.current_state_ids)

    async def test_descriptors_work_in_async_engine(self) -> None:
        """The async engine must match the sync engine."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"on": {"ns.*": "b"}}, "b": {}},
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await settle(interpreter, "ns.thing")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🏷️ Metadata Keys
# -----------------------------------------------------------------------------
class TestMetadataKeys(unittest.TestCase):
    """Pins `tags`, `meta` and `description`, previously dropped at parse."""

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "states": {
            "a": {
                "tags": ["loading", "busy"],
                "meta": {"note": "hello"},
                "description": "The A state",
                "on": {"E": "b"},
            },
            "b": {"tags": "done"},
        },
    }

    def test_tags_are_parsed_and_queryable(self) -> None:
        """Tags must reach the node and the `has_tag` API."""
        # Arrange
        interpreter = start(self.CONFIG)

        # Assert
        self.assertTrue(interpreter.has_tag("loading"))
        self.assertTrue(interpreter.has_tag("busy"))
        self.assertFalse(interpreter.has_tag("done"))
        self.assertEqual({"loading", "busy"}, interpreter.tags)

    def test_tags_update_on_transition(self) -> None:
        """The tag set must follow the active configuration."""
        # Arrange
        interpreter = start(self.CONFIG)

        # Act
        interpreter.send("E")

        # Assert
        self.assertTrue(interpreter.has_tag("done"))
        self.assertFalse(interpreter.has_tag("loading"))

    def test_string_tag_is_normalised_to_a_set(self) -> None:
        """A bare string tag must behave like a one-element list."""
        # Arrange
        machine = build(self.CONFIG)

        # Assert
        self.assertEqual({"done"}, machine.states["b"].tags)

    def test_meta_is_collected_from_active_states(self) -> None:
        """`get_meta()` must key meta by state id."""
        # Arrange
        interpreter = start(self.CONFIG)

        # Assert
        self.assertEqual({"m.a": {"note": "hello"}}, interpreter.get_meta())

    def test_description_is_retained(self) -> None:
        """`description` must survive parsing."""
        # Arrange
        machine = build(self.CONFIG)

        # Assert
        self.assertEqual("The A state", machine.states["a"].description)


# -----------------------------------------------------------------------------
# ⚡ Eventless (always) Transitions
# -----------------------------------------------------------------------------
class TestAlwaysTransitions(unittest.TestCase):
    """Pins the v5 top-level `always` key, previously ignored."""

    def test_top_level_always_fires(self) -> None:
        """`always` must behave like the legacy empty-string event."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"always": "b"}, "b": {}},
            }
        )

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_always_respects_guards(self) -> None:
        """A guarded `always` must only fire when its guard passes."""

        def flip(_i: Any, ctx: Any, _e: Any, _a: Any) -> None:
            """Marks the context ready."""
            ctx["ready"] = True

        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {"ready": False},
                "states": {
                    "a": {
                        "always": {"target": "b", "guard": "isReady"},
                        "on": {"FLIP": {"actions": ["flip"]}},
                    },
                    "b": {},
                },
            },
            guards={"isReady": lambda c, e: c.get("ready", False)},
            actions={"flip": flip},
        )
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

        # Act
        interpreter.send("FLIP")

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_legacy_empty_string_still_works(self) -> None:
        """The v4 spelling must remain supported."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"": "b"}}, "b": {}},
            }
        )

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_max_iterations_breaks_infinite_loop(self) -> None:
        """Mutually-targeting `always` transitions must terminate."""
        # Arrange / Act — would hang without the microstep bound.
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "maxIterations": 25,
                "states": {"a": {"always": "b"}, "b": {"always": "a"}},
            }
        )

        # Assert — it settled rather than spinning forever.
        self.assertTrue(interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🎬 Built-in Action Creators
# -----------------------------------------------------------------------------
class TestBuiltinActions(unittest.IsolatedAsyncioTestCase):
    """Pins the declarative action vocabulary added in v0.6.0.

    🐛 Regression: none of these existed. On `SyncInterpreter` they raised
    `ImplementationMissingError`; on the async engine the machine was
    silently destroyed.
    """

    def test_assign_with_literal_values(self) -> None:
        """`assign` must write literals into the context."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {"n": 0},
                "states": {
                    "a": {
                        "entry": [
                            {
                                "type": "assign",
                                "params": {"assignment": {"n": 5}},
                            }
                        ]
                    }
                },
            }
        )

        # Assert
        self.assertEqual(5, interpreter.context["n"])

    def test_assign_with_callable_values(self) -> None:
        """`assign` values may be callables of `{context, event}`."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {"n": 1},
                "states": {
                    "a": {
                        "entry": [
                            {
                                "type": "assign",
                                "params": {
                                    "assignment": {
                                        "n": lambda args: args["context"]["n"]
                                        + 9
                                    }
                                },
                            }
                        ]
                    }
                },
            }
        )

        # Assert
        self.assertEqual(10, interpreter.context["n"])

    def test_raise_sends_event_to_self(self) -> None:
        """`raise` must deliver an internal event."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "entry": [
                            {"type": "raise", "params": {"event": "GO"}}
                        ],
                        "on": {"GO": "b"},
                    },
                    "b": {},
                },
            }
        )

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_log_action_does_not_crash(self) -> None:
        """`log` must be a harmless no-op side effect."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "entry": [
                            {
                                "type": "log",
                                "params": {"expr": "hi", "label": "L"},
                            }
                        ]
                    }
                },
            }
        )

        # Assert
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_choose_picks_first_passing_branch(self) -> None:
        """`choose` must take the first branch whose guard passes."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {"v": 0},
                "states": {
                    "a": {
                        "entry": [
                            {
                                "type": "choose",
                                "params": {
                                    "conditions": [
                                        {
                                            "guard": "no",
                                            "actions": [
                                                {
                                                    "type": "assign",
                                                    "params": {
                                                        "assignment": {"v": 1}
                                                    },
                                                }
                                            ],
                                        },
                                        {
                                            "actions": [
                                                {
                                                    "type": "assign",
                                                    "params": {
                                                        "assignment": {"v": 2}
                                                    },
                                                }
                                            ]
                                        },
                                    ]
                                },
                            }
                        ]
                    }
                },
            },
            guards={"no": lambda c, e: False},
        )

        # Assert — the fallback branch ran, not the guarded one.
        self.assertEqual(2, interpreter.context["v"])

    def test_pure_returns_actions_to_run(self) -> None:
        """`pure` must execute the actions it returns."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {},
                "states": {
                    "a": {
                        "entry": [
                            {
                                "type": "pure",
                                "params": {
                                    "get": lambda args: [
                                        {
                                            "type": "assign",
                                            "params": {
                                                "assignment": {"p": True}
                                            },
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                },
            }
        )

        # Assert
        self.assertTrue(interpreter.context["p"])

    def test_enqueue_actions_with_check(self) -> None:
        """`enqueueActions` must expose `enqueue` and `check`."""

        def callback(args: Dict[str, Any]) -> None:
            """Enqueues one unconditional and one guarded assignment."""
            args["enqueue"].assign({"always": 1})
            if args["check"]("yes"):
                args["enqueue"].assign({"guarded": True})

        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {},
                "states": {
                    "a": {
                        "entry": [
                            {
                                "type": "enqueueActions",
                                "params": {"callback": callback},
                            }
                        ]
                    }
                },
            },
            guards={"yes": lambda c, e: True},
        )

        # Assert
        self.assertEqual(1, interpreter.context["always"])
        self.assertTrue(interpreter.context["guarded"])

    def test_emit_reaches_listener(self) -> None:
        """`emit` must publish to listeners registered via `on`."""
        # Arrange
        received: List[str] = []
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "E": {
                                "actions": [
                                    {
                                        "type": "emit",
                                        "params": {
                                            "event": {"type": "OUT", "v": 1}
                                        },
                                    }
                                ]
                            }
                        }
                    }
                },
            }
        )
        interpreter.on("OUT", lambda ev: received.append(ev.type))

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual(["OUT"], received)

    def test_emit_wildcard_listener(self) -> None:
        """`on("*")` must receive every emitted event."""
        # Arrange
        received: List[str] = []
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "E": {
                                "actions": [
                                    {
                                        "type": "emit",
                                        "params": {"event": "ANY"},
                                    }
                                ]
                            }
                        }
                    }
                },
            }
        )
        interpreter.on("*", lambda ev: received.append(ev.type))

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual(["ANY"], received)

    def test_emit_listener_failure_is_contained(self) -> None:
        """A raising listener must not disturb the machine."""

        def bad(_ev: Any) -> None:
            """A deliberately faulty listener."""
            raise ValueError("listener boom")

        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "E": {
                                "target": "b",
                                "actions": [
                                    {
                                        "type": "emit",
                                        "params": {"event": "OUT"},
                                    }
                                ],
                            }
                        }
                    },
                    "b": {},
                },
            }
        )
        interpreter.on("OUT", bad)

        # Act
        interpreter.send("E")

        # Assert — the transition still completed.
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_user_action_wins_over_builtin_name(self) -> None:
        """A user-defined `log` must take precedence over the built-in."""
        # Arrange
        calls: List[str] = []

        def user_log(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            """Records that the user implementation ran."""
            calls.append("user")

        # Act
        start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"entry": ["log"]}},
            },
            actions={"log": user_log},
        )

        # Assert
        self.assertEqual(["user"], calls)

    def test_spawn_child_alias_is_not_hijacked(self) -> None:
        """`spawn_child` must still mean "spawn the service named child".

        🏛️ The library's convention is `spawn_<serviceKey>`. Registering
        `spawn_child` as an alias for the `spawnChild` built-in would
        silently break every machine that spawns a service called `child`.
        """
        # Assert
        self.assertFalse(is_builtin("spawn_child"))
        self.assertTrue(is_builtin("spawnChild"))
        self.assertEqual("xstate.spawnChild", resolve_builtin("spawnChild"))

    async def test_builtin_actions_work_in_async_engine(self) -> None:
        """The async engine must support the same built-ins."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "context": {"n": 0},
                    "states": {
                        "a": {
                            "on": {
                                "E": {
                                    "target": "b",
                                    "actions": [
                                        {
                                            "type": "assign",
                                            "params": {"assignment": {"n": 3}},
                                        }
                                    ],
                                }
                            }
                        },
                        "b": {},
                    },
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await settle(interpreter, "E")

        # Assert
        self.assertEqual(3, interpreter.context["n"])
        self.assertEqual({"m.b"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🌐 Actor System & Messaging
# -----------------------------------------------------------------------------
class TestActorSystem(unittest.IsolatedAsyncioTestCase):
    """Pins `systemId`, `sendTo`, `sendParent`, `stopChild`, `spawnChild`."""

    CHILD: Dict[str, Any] = {
        "id": "kid",
        "initial": "idle",
        "states": {
            "idle": {
                "on": {
                    "PING": {
                        "actions": [
                            {
                                "type": "sendParent",
                                "params": {"event": "PONG"},
                            }
                        ]
                    }
                }
            }
        },
    }

    PARENT: Dict[str, Any] = {
        "id": "p",
        "initial": "a",
        "context": {},
        "states": {
            "a": {
                "entry": [
                    {
                        "type": "spawnChild",
                        "params": {
                            "src": "kid",
                            "id": "worker",
                            "systemId": "w",
                        },
                    }
                ],
                "on": {
                    "GO": {
                        "actions": [
                            {
                                "type": "sendTo",
                                "params": {"to": "w", "event": "PING"},
                            }
                        ]
                    },
                    "PONG": "done",
                    "STOPIT": {
                        "actions": [
                            {
                                "type": "stopChild",
                                "params": {"id": "worker"},
                            }
                        ]
                    },
                },
            },
            "done": {},
        },
    }

    def _parent(self) -> SyncInterpreter:
        """Builds and starts the parent machine with a child factory.

        Returns:
            SyncInterpreter: The started parent.
        """
        return start(
            self.PARENT,
            services={
                "kid": lambda i, c, e: build(self.CHILD),
            },
        )

    def test_spawn_child_registers_system_id(self) -> None:
        """`systemId` must be discoverable through `interpreter.system`."""
        # Arrange / Act
        interpreter = self._parent()
        self.addCleanup(interpreter.stop)

        # Assert
        self.assertIn("w", interpreter.system)
        self.assertIsNotNone(interpreter.system.get("w"))
        self.assertIn("w", interpreter.system.get_all())

    def test_explicit_actor_id_is_used(self) -> None:
        """An explicit `id` must name the actor deterministically."""
        # Arrange / Act
        interpreter = self._parent()
        self.addCleanup(interpreter.stop)

        # Assert
        self.assertIn("p:worker", interpreter._actors)

    def test_send_to_and_send_parent_round_trip(self) -> None:
        """A parent must reach a child by systemId and receive a reply."""
        # Arrange
        interpreter = self._parent()
        self.addCleanup(interpreter.stop)

        # Act
        interpreter.send("GO")

        # Assert
        self.assertEqual({"p.done"}, interpreter.current_state_ids)

    def test_stop_child_removes_the_actor(self) -> None:
        """`stopChild` must deregister the child."""
        # Arrange
        interpreter = self._parent()
        self.addCleanup(interpreter.stop)
        self.assertEqual(1, len(interpreter._actors))

        # Act
        interpreter.send("STOPIT")

        # Assert
        self.assertEqual(0, len(interpreter._actors))

    async def test_actor_system_in_async_engine(self) -> None:
        """The async engine must support the same actor messaging."""
        # Arrange
        interpreter = await Interpreter(
            create_machine(
                self.PARENT,
                logic=MachineLogic(
                    services={"kid": lambda i, c, e: build(self.CHILD)}
                ),
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await asyncio.sleep(0.02)

        # Act
        await settle(interpreter, "GO")
        await asyncio.sleep(0.05)

        # Assert
        self.assertIn("w", interpreter.system)
        self.assertEqual({"p.done"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 💾 Deep Persistence
# -----------------------------------------------------------------------------
class TestDeepPersistence(unittest.TestCase):
    """Pins that a snapshot captures the whole actor hierarchy.

    🐛 Regression: snapshots held only `{status, context, state_ids}`. A
    parent with live children restored with ZERO children — silent,
    unrecoverable data loss for anyone persisting a workflow.
    """

    CHILD: Dict[str, Any] = {
        "id": "kid",
        "initial": "idle",
        "states": {"idle": {"on": {"N": "busy"}}, "busy": {}},
    }

    PARENT: Dict[str, Any] = {
        "id": "p",
        "initial": "a",
        "context": {"n": 1},
        "states": {
            "a": {
                "entry": [
                    {
                        "type": "spawnChild",
                        "params": {"src": "kid", "id": "w"},
                    }
                ],
                "on": {"E": "b"},
            },
            "b": {},
        },
    }

    def _logic(self) -> MachineLogic:
        """Builds logic exposing the child machine as a service.

        Returns:
            MachineLogic: Logic with a `kid` service.
        """
        return MachineLogic(
            services={"kid": lambda i, c, e: build(self.CHILD)}
        )

    def test_snapshot_includes_child_actors(self) -> None:
        """Child actors must appear in the persisted snapshot."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(self.PARENT, logic=self._logic())
        ).start()
        self.addCleanup(interpreter.stop)

        # Act
        data = json.loads(interpreter.get_snapshot())

        # Assert
        self.assertIn("actors", data)
        self.assertIn("p:w", data["actors"])

    def test_child_state_survives_round_trip(self) -> None:
        """A restored child must retain its own active state."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(self.PARENT, logic=self._logic())
        ).start()
        self.addCleanup(interpreter.stop)
        interpreter._actors["p:w"].send("N")
        snapshot = interpreter.get_snapshot()

        # Act
        restored = SyncInterpreter.from_snapshot(
            snapshot, create_machine(self.PARENT, logic=self._logic())
        )

        # Assert
        self.assertIn("p:w", restored._actors)
        self.assertEqual(
            {"kid.busy"}, restored._actors["p:w"].current_state_ids
        )

    def test_snapshot_records_full_configuration(self) -> None:
        """Ancestors must be persisted, not re-derived from leaves."""
        # Arrange
        interpreter = SyncInterpreter(
            create_machine(self.PARENT, logic=self._logic())
        ).start()
        self.addCleanup(interpreter.stop)

        # Act
        data = json.loads(interpreter.get_snapshot())

        # Assert
        self.assertIn("configuration", data)
        self.assertIn("p.a", data["configuration"])

    def test_history_survives_round_trip(self) -> None:
        """A restored machine must still honour a history transition."""
        # Arrange
        config = {
            "id": "m",
            "initial": "p",
            "states": {
                "p": {
                    "initial": "c1",
                    "states": {
                        "c1": {"on": {"N": "c2"}},
                        "c2": {"on": {"O": "#m.away"}},
                        "h": {"type": "history"},
                    },
                },
                "away": {"on": {"B": "#m.p.h"}},
            },
        }
        interpreter = start(config)
        interpreter.send("N")
        interpreter.send("O")
        snapshot = interpreter.get_snapshot()

        # Act
        restored = SyncInterpreter.from_snapshot(snapshot, build(config))
        restored.status = "running"
        restored.send("B")

        # Assert
        self.assertEqual({"m.p.c2"}, restored.current_state_ids)


# -----------------------------------------------------------------------------
# 🏁 Output, Done Status & Error Snapshots
# -----------------------------------------------------------------------------
class TestCompletionAndErrors(unittest.IsolatedAsyncioTestCase):
    """Pins `output`, `status == "done"` and error snapshots."""

    def test_top_level_final_sets_done_and_output(self) -> None:
        """Reaching a top-level final state must be observable."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"E": "f"}},
                    "f": {"type": "final", "output": {"result": 42}},
                },
            }
        )

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual("done", interpreter.status)
        self.assertEqual({"result": 42}, interpreter.output)

    def test_on_done_carries_output_as_event_data(self) -> None:
        """A compound `onDone` must receive the final state's output."""
        # Arrange
        seen: Dict[str, Any] = {}

        def capture(_i: Any, _c: Any, event: Any, _a: Any) -> None:
            """Records the done event's data."""
            seen["data"] = getattr(event, "data", None)

        interpreter = start(
            {
                "id": "m",
                "initial": "p",
                "states": {
                    "p": {
                        "initial": "w",
                        "onDone": {"target": "end", "actions": ["cap"]},
                        "states": {
                            "w": {"on": {"E": "f"}},
                            "f": {"type": "final", "output": {"n": 7}},
                        },
                    },
                    "end": {},
                },
            },
            actions={"cap": capture},
        )

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"n": 7}, seen["data"])
        self.assertEqual({"m.end"}, interpreter.current_state_ids)

    def test_callable_output_is_resolved(self) -> None:
        """`output` may be a callable of `{context, event}`."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {"n": 3},
                "states": {
                    "a": {"on": {"E": "f"}},
                    "f": {
                        "type": "final",
                        "output": lambda args: args["context"]["n"] * 2,
                    },
                },
            }
        )

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual(6, interpreter.output)

    async def test_unhandled_service_error_sets_error_status(self) -> None:
        """A failing service with no `onError` must be observable."""

        async def boom(_i: Any, _c: Any, _e: Any) -> None:
            """A deliberately failing service."""
            raise ValueError("kaboom")

        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "l",
                    "states": {"l": {"invoke": {"src": "b"}}},
                },
                services={"b": boom},
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await asyncio.sleep(0.1)

        # Assert
        self.assertEqual("error", interpreter.status)
        self.assertIsInstance(interpreter.error, ValueError)

    async def test_handled_service_error_keeps_running(self) -> None:
        """A declared `onError` must keep the machine healthy."""

        async def boom(_i: Any, _c: Any, _e: Any) -> None:
            """A deliberately failing service."""
            raise ValueError("kaboom")

        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "l",
                    "states": {
                        "l": {"invoke": {"src": "b", "onError": "e"}},
                        "e": {},
                    },
                },
                services={"b": boom},
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await asyncio.sleep(0.1)

        # Assert
        self.assertEqual("running", interpreter.status)
        self.assertEqual({"m.e"}, interpreter.current_state_ids)

    async def test_to_promise_returns_output(self) -> None:
        """`to_promise` must resolve with the machine's output."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {"on": {"E": "f"}},
                        "f": {"type": "final", "output": {"r": 7}},
                    },
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await interpreter.send("E")
        result = await to_promise(interpreter, timeout=2)

        # Assert
        self.assertEqual({"r": 7}, result)

    async def test_wait_for_predicate(self) -> None:
        """`wait_for` must return once the predicate holds."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {"a": {"on": {"E": "b"}}, "b": {}},
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await interpreter.send("E")
        await wait_for(interpreter, lambda i: i.matches("m.b"), timeout=2)

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🔭 Observation API
# -----------------------------------------------------------------------------
class TestObservationApi(unittest.TestCase):
    """Pins `matches`, `can`, `subscribe` and `input`."""

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "initial": "c",
                "states": {"c": {"on": {"E": "d"}}, "d": {}},
            }
        },
    }

    def test_matches_accepts_several_spellings(self) -> None:
        """Full id, partial path and `#`-prefixed forms must all work."""
        # Arrange
        interpreter = start(self.CONFIG)

        # Assert
        self.assertTrue(interpreter.matches("m.p.c"))
        self.assertTrue(interpreter.matches("p.c"))
        self.assertTrue(interpreter.matches("#m.p.c"))
        self.assertFalse(interpreter.matches("m.p.d"))

    def test_matches_an_active_ancestor(self) -> None:
        """An ancestor of an active leaf must also match."""
        # Arrange
        interpreter = start(self.CONFIG)

        # Assert
        self.assertTrue(interpreter.matches("m.p"))

    def test_can_predicts_transitions(self) -> None:
        """`can` must evaluate guards without side effects."""
        # Arrange
        interpreter = start(self.CONFIG)

        # Act / Assert
        self.assertTrue(interpreter.can("E"))
        self.assertFalse(interpreter.can("NOPE"))
        # The prediction must not have moved the machine.
        self.assertEqual({"m.p.c"}, interpreter.current_state_ids)

    def test_can_respects_guards(self) -> None:
        """A blocked transition must report `False`."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"E": {"target": "b", "guard": "no"}}},
                    "b": {},
                },
            },
            guards={"no": lambda c, e: False},
        )

        # Assert
        self.assertFalse(interpreter.can("E"))

    def test_subscribe_and_unsubscribe(self) -> None:
        """Subscribers must fire on change and stop after unsubscribing."""
        # Arrange
        seen: List[Any] = []
        interpreter = start(self.CONFIG)
        unsubscribe = interpreter.subscribe(
            lambda i: seen.append(sorted(i.current_state_ids))
        )

        # Act
        interpreter.send("E")
        count_after_first = len(seen)
        unsubscribe()
        interpreter.send("E")

        # Assert
        self.assertEqual(1, count_after_first)
        self.assertEqual(count_after_first, len(seen))

    def test_subscriber_exception_is_contained(self) -> None:
        """A raising subscriber must not break the machine."""

        def bad(_i: Any) -> None:
            """A deliberately faulty subscriber."""
            raise ValueError("subscriber boom")

        # Arrange
        interpreter = start(self.CONFIG)
        interpreter.subscribe(bad)

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.p.d"}, interpreter.current_state_ids)

    def test_input_seeds_context(self) -> None:
        """`input` must be readable and merged into a plain context."""
        # Arrange
        interpreter = SyncInterpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "context": {"n": 1},
                    "states": {"a": {}},
                }
            ),
            input={"k": 9},
        ).start()

        # Assert
        self.assertEqual({"k": 9}, interpreter.input)
        self.assertEqual({"k": 9}, interpreter.context["input"])

    def test_context_factory_receives_input(self) -> None:
        """A callable `context` must be invoked with `{input}`."""
        # Arrange
        interpreter = SyncInterpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "context": lambda args: {
                        "greeting": "hi " + args["input"]["name"]
                    },
                    "states": {"a": {}},
                }
            ),
            input={"name": "Ada"},
        ).start()

        # Assert
        self.assertEqual("hi Ada", interpreter.context["greeting"])


# -----------------------------------------------------------------------------
# 🧪 Pure Transition API
# -----------------------------------------------------------------------------
class TestPureTransitionApi(unittest.TestCase):
    """Pins the actor-free reducers mirroring XState v5.19.0."""

    CONFIG: Dict[str, Any] = {
        "id": "m",
        "initial": "a",
        "context": {"n": 0},
        "states": {
            "a": {
                "on": {
                    "E": {
                        "target": "b",
                        "actions": [
                            {
                                "type": "assign",
                                "params": {"assignment": {"n": 1}},
                            }
                        ],
                    }
                }
            },
            "b": {},
        },
    }

    def test_initial_transition_returns_snapshot(self) -> None:
        """`initial_transition` must report the starting state."""
        # Arrange / Act
        snapshot, _actions = initial_transition(build(self.CONFIG))

        # Assert
        self.assertEqual({"m.a"}, snapshot.state_ids)
        self.assertEqual("active", snapshot.status)

    def test_transition_computes_next_state(self) -> None:
        """`pure_transition` must apply the event and its assignments."""
        # Arrange
        machine = build(self.CONFIG)
        snapshot, _ = initial_transition(machine)

        # Act
        result, actions = pure_transition(machine, snapshot, "E")

        # Assert
        self.assertEqual({"m.b"}, result.state_ids)
        self.assertEqual(1, result.context["n"])
        self.assertIn("assign", [a.type for a in actions])

    def test_transition_does_not_mutate_input_snapshot(self) -> None:
        """The pure API must leave its input untouched."""
        # Arrange
        machine = build(self.CONFIG)
        snapshot, _ = initial_transition(machine)

        # Act
        pure_transition(machine, snapshot, "E")

        # Assert
        self.assertEqual({"m.a"}, snapshot.state_ids)
        self.assertEqual(0, snapshot.context["n"])

    def test_get_next_snapshot_wrapper(self) -> None:
        """`get_next_snapshot` must discard the action list."""
        # Arrange
        machine = build(self.CONFIG)
        snapshot, _ = initial_transition(machine)

        # Act
        result = get_next_snapshot(machine, snapshot, "E")

        # Assert
        self.assertEqual({"m.b"}, result.state_ids)

    def test_snapshot_matches_helper(self) -> None:
        """`PureSnapshot.matches` must mirror the interpreter helper."""
        # Arrange
        machine = build(self.CONFIG)
        snapshot, _ = initial_transition(machine)

        # Assert
        self.assertTrue(snapshot.matches("m.a"))
        self.assertFalse(snapshot.matches("m.b"))

    def test_pure_api_does_not_run_side_effects(self) -> None:
        """Declared actions must be reported, not executed."""
        # Arrange
        calls: List[str] = []

        def spy(_i: Any, _c: Any, _e: Any, _a: Any) -> None:
            """Records that a real execution happened."""
            calls.append("ran")

        machine = build(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"E": {"target": "b", "actions": ["spy"]}}},
                    "b": {},
                },
            },
            actions={"spy": spy},
        )
        snapshot, _ = initial_transition(machine)

        # Act
        _result, actions = pure_transition(machine, snapshot, "E")

        # Assert — reported but never executed.
        self.assertEqual(["spy"], [a.type for a in actions])
        self.assertEqual([], calls)


# -----------------------------------------------------------------------------
# ⏱️ Named Delays
# -----------------------------------------------------------------------------
class TestNamedDelays(unittest.TestCase):
    """Pins symbolic `after` delays resolved from `MachineLogic.delays`.

    🐛 Regression: every `after` key was coerced with `int()`, so a named
    delay raised a bare `ValueError` at parse time.
    """

    def test_named_delay_resolves_and_fires(self) -> None:
        """A symbolic delay must resolve through `delays`."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"after": {"SHORT": "b"}}, "b": {}},
            },
            delays={"SHORT": 20},
        )
        self.addCleanup(interpreter.stop)
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

        # Act — poll rather than sleeping a fixed interval.
        deadline = time.monotonic() + 5.0
        while (
            interpreter.current_state_ids != {"m.b"}
            and time.monotonic() < deadline
        ):
            time.sleep(0.005)

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_numeric_delay_still_works(self) -> None:
        """Integer delays must be unaffected."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"after": {20: "b"}}, "b": {}},
            }
        )
        self.addCleanup(interpreter.stop)

        # Act
        deadline = time.monotonic() + 5.0
        while (
            interpreter.current_state_ids != {"m.b"}
            and time.monotonic() < deadline
        ):
            time.sleep(0.005)

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🐍 Python-facing Action Creator Helpers
# -----------------------------------------------------------------------------
class TestActionCreatorHelpers(unittest.TestCase):
    """Pins the helper functions that build action dictionaries.

    These exist so a Python-authored machine gets the same ergonomics as
    XState's JS helpers rather than hand-writing params dicts.
    """

    def test_helpers_produce_dispatchable_actions(self) -> None:
        """Every helper must emit a dict the interpreter can dispatch."""
        # Arrange
        cases = [
            (raise_("GO"), "xstate.raise"),
            (send_to("a", "GO"), "xstate.sendTo"),
            (send_parent("GO"), "xstate.sendParent"),
            (forward_to("a"), "xstate.forwardTo"),
            (escalate("boom"), "xstate.escalate"),
            (log("hi"), "xstate.log"),
            (cancel("x"), "xstate.cancel"),
            (stop_child("kid"), "xstate.stopChild"),
            (spawn_child("kid"), "xstate.spawnChild"),
            (emit("OUT"), "xstate.emit"),
            (assign({"n": 1}), "xstate.assign"),
            (pure(lambda args: None), "xstate.pure"),
            (choose([{"actions": []}]), "xstate.choose"),
            (enqueue_actions(lambda args: None), "xstate.enqueueActions"),
        ]

        # Assert
        for action, expected_type in cases:
            self.assertEqual(expected_type, action["type"])
            self.assertIn("params", action)

    def test_helper_built_action_executes(self) -> None:
        """A helper-built action must work end to end."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "context": {},
                "states": {
                    "a": {
                        "entry": [assign({"via": "helper"})],
                        "on": {"GO": "b"},
                    },
                    "b": {},
                },
            }
        )

        # Assert
        self.assertEqual("helper", interpreter.context["via"])

    def test_enqueuer_convenience_methods(self) -> None:
        """`ActionEnqueuer` must expose the documented shortcuts."""
        # Arrange
        enqueuer = ActionEnqueuer(None, None)

        # Act
        enqueuer.assign({"a": 1})
        enqueuer.raise_("R")
        enqueuer.send_to("t", "S")
        enqueuer.send_parent("P")
        enqueuer.emit("E")
        enqueuer.log("L")
        enqueuer.cancel("c")
        enqueuer.stop_child("k")
        enqueuer.spawn_child("s")
        enqueuer({"type": "custom"})

        # Assert
        self.assertEqual(10, len(enqueuer.items))

    def test_alias_spellings_resolve_identically(self) -> None:
        """camelCase and snake_case must map to the same built-in."""
        # Assert
        self.assertEqual(resolve_builtin("sendTo"), resolve_builtin("send_to"))
        self.assertEqual(
            resolve_builtin("enqueueActions"),
            resolve_builtin("enqueue_actions"),
        )
        self.assertIsNone(resolve_builtin("myOwnAction"))


# -----------------------------------------------------------------------------
# 🧭 Initial-State Resolution
# -----------------------------------------------------------------------------
class TestInitialStateResolution(unittest.TestCase):
    """Pins how a missing `initial` is handled.

    🐛 Regression: a compound state without `initial` started with an EMPTY
    active configuration and silently dropped every event.
    """

    def test_single_child_is_inferred(self) -> None:
        """One child needs no explicit `initial`."""
        # Arrange / Act
        machine = build({"id": "m", "states": {"only": {}}})

        # Assert
        self.assertEqual("only", machine.initial)

    def test_ambiguous_parent_raises_on_start(self) -> None:
        """Several children with no `initial` must fail loudly at start."""
        # Arrange
        machine = build({"id": "m", "states": {"a": {}, "b": {}}})

        # Act / Assert
        with self.assertRaises(InvalidConfigError):
            SyncInterpreter(machine).start()

    def test_history_child_is_not_inferred_as_initial(self) -> None:
        """A history pseudo-state must never be chosen as `initial`."""
        # Arrange / Act
        machine = build(
            {
                "id": "m",
                "states": {
                    "p": {
                        "states": {
                            "real": {},
                            "h": {"type": "history"},
                        }
                    }
                },
            }
        )

        # Assert
        self.assertEqual("real", machine.states["p"].initial)


# -----------------------------------------------------------------------------
# 🕰️ History States
# -----------------------------------------------------------------------------
class TestHistoryStates(unittest.IsolatedAsyncioTestCase):
    """Pins shallow and deep history, previously parsed as plain atomic."""

    SHALLOW: Dict[str, Any] = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "initial": "c1",
                "states": {
                    "c1": {"on": {"N": "c2"}},
                    "c2": {"on": {"OUT": "#m.away"}},
                    "h": {"type": "history"},
                },
            },
            "away": {"on": {"BACK": "#m.p.h"}},
        },
    }

    DEEP: Dict[str, Any] = {
        "id": "m",
        "initial": "p",
        "states": {
            "p": {
                "initial": "x",
                "states": {
                    "x": {
                        "initial": "x1",
                        "states": {
                            "x1": {"on": {"D": "x2"}},
                            "x2": {"on": {"OUT": "#m.away"}},
                        },
                    },
                    "h": {"type": "history", "history": "deep"},
                },
            },
            "away": {"on": {"BACK": "#m.p.h"}},
        },
    }

    def test_history_node_is_parsed_as_history(self) -> None:
        """`type: "history"` must not be misparsed as atomic."""
        # Arrange / Act
        node = build(self.DEEP).states["p"].states["h"]

        # Assert
        self.assertEqual("history", node.type)
        self.assertEqual("deep", node.history)

    def test_shallow_history_restores_immediate_child(self) -> None:
        """Shallow history must return to the remembered child."""
        # Arrange
        interpreter = start(self.SHALLOW)
        interpreter.send("N")
        interpreter.send("OUT")

        # Act
        interpreter.send("BACK")

        # Assert
        self.assertEqual({"m.p.c2"}, interpreter.current_state_ids)

    def test_deep_history_restores_nested_leaf(self) -> None:
        """Deep history must restore the full nested configuration."""
        # Arrange
        interpreter = start(self.DEEP)
        interpreter.send("D")
        interpreter.send("OUT")

        # Act
        interpreter.send("BACK")

        # Assert
        self.assertEqual({"m.p.x.x2"}, interpreter.current_state_ids)

    def test_unvisited_history_falls_back_to_initial(self) -> None:
        """An unvisited history state must use the parent's `initial`."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {"on": {"GO": "#m.p.h"}},
                    "p": {
                        "initial": "c1",
                        "states": {"c1": {}, "h": {"type": "history"}},
                    },
                },
            }
        )

        # Act
        interpreter.send("GO")

        # Assert
        self.assertEqual({"m.p.c1"}, interpreter.current_state_ids)

    async def test_history_in_async_engine(self) -> None:
        """The async engine must restore history identically."""
        # Arrange
        interpreter = await Interpreter(build(self.SHALLOW)).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        for event in ("N", "OUT", "BACK"):
            await settle(interpreter, event)

        # Assert
        self.assertEqual({"m.p.c2"}, interpreter.current_state_ids)


# -----------------------------------------------------------------------------
# 🧱 Robustness & Edge Cases
# -----------------------------------------------------------------------------
class TestRobustness(unittest.TestCase):
    """Pins that malformed or unusual configuration fails predictably."""

    def test_invalid_guard_shape_raises(self) -> None:
        """A guard object without a `type` must be rejected at build."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError):
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {"on": {"E": {"target": "b", "guard": {}}}},
                        "b": {},
                    },
                }
            )

    def test_composite_guard_without_children_raises(self) -> None:
        """`and` with no operands is meaningless and must be rejected."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError):
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "E": {
                                    "target": "b",
                                    "guard": {"type": "and"},
                                }
                            }
                        },
                        "b": {},
                    },
                }
            )

    def test_not_guard_requires_exactly_one_child(self) -> None:
        """`not` with two operands is ambiguous and must be rejected."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError):
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "E": {
                                    "target": "b",
                                    "guard": {
                                        "type": "not",
                                        "children": ["x", "y"],
                                    },
                                }
                            }
                        },
                        "b": {},
                    },
                }
            )

    def test_state_in_without_params_is_false(self) -> None:
        """A malformed `stateIn` must block rather than crash."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "E": {
                                "target": "b",
                                "guard": {"type": "stateIn"},
                            }
                        }
                    },
                    "b": {},
                },
            }
        )

        # Act
        interpreter.send("E")

        # Assert
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_unknown_named_delay_is_skipped_not_fatal(self) -> None:
        """An unresolvable delay must warn, not crash the machine."""
        # Arrange / Act
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"after": {"MISSING": "b"}}, "b": {}},
            }
        )
        self.addCleanup(interpreter.stop)

        # Assert — still usable, just without that timer.
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    def test_send_to_unknown_target_is_not_fatal(self) -> None:
        """An unresolvable `sendTo` target must warn and continue."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {
                    "a": {
                        "on": {
                            "E": {
                                "target": "b",
                                "actions": [
                                    {
                                        "type": "sendTo",
                                        "params": {
                                            "to": "ghost",
                                            "event": "X",
                                        },
                                    }
                                ],
                            }
                        }
                    },
                    "b": {},
                },
            }
        )

        # Act
        interpreter.send("E")

        # Assert — the transition still completed.
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    def test_coerce_event_accepts_dict_form(self) -> None:
        """A mapping with a `type` key must be accepted by `can`."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"E": "b"}}, "b": {}},
            }
        )

        # Assert
        self.assertTrue(interpreter.can({"type": "E", "payload": 1}))

    def test_coerce_event_rejects_bad_input(self) -> None:
        """A value that is not an event must raise a clear TypeError."""
        # Arrange
        interpreter = start({"id": "m", "initial": "a", "states": {"a": {}}})

        # Act / Assert
        with self.assertRaises(TypeError):
            interpreter._coerce_event(123)


# -----------------------------------------------------------------------------
# 🚀 Async Engine: Built-in Actions & Delayed Sends
# -----------------------------------------------------------------------------
class TestAsyncBuiltinActions(unittest.IsolatedAsyncioTestCase):
    """Exercises the async engine's own built-in action implementations.

    🏛️ The two engines implement delivery independently (asyncio tasks vs
    daemon threads), so the sync coverage above does not exercise this code.
    """

    async def test_raise_in_async_engine(self) -> None:
        """`raise` must deliver an internal event on the async engine."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "E": {
                                    "target": "b",
                                    "actions": [
                                        {
                                            "type": "raise",
                                            "params": {"event": "GO"},
                                        }
                                    ],
                                }
                            }
                        },
                        "b": {"on": {"GO": "c"}},
                        "c": {},
                    },
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await settle(interpreter, "E")
        await asyncio.sleep(0.05)

        # Assert
        self.assertEqual({"m.c"}, interpreter.current_state_ids)

    async def test_delayed_send_fires(self) -> None:
        """A delayed `raise` must arrive after its delay."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "S": {
                                    "actions": [
                                        {
                                            "type": "raise",
                                            "params": {
                                                "event": "LATE",
                                                "delay": 30,
                                                "id": "x",
                                            },
                                        }
                                    ]
                                },
                                "LATE": "b",
                            }
                        },
                        "b": {},
                    },
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await interpreter.send("S")
        await wait_for(interpreter, lambda i: i.matches("m.b"), timeout=3)

        # Assert
        self.assertEqual({"m.b"}, interpreter.current_state_ids)

    async def test_cancel_aborts_delayed_send(self) -> None:
        """`cancel` must stop a pending delayed send."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "S": {
                                    "actions": [
                                        {
                                            "type": "raise",
                                            "params": {
                                                "event": "LATE",
                                                "delay": 40,
                                                "id": "x",
                                            },
                                        }
                                    ]
                                },
                                "C": {
                                    "actions": [
                                        {
                                            "type": "cancel",
                                            "params": {"sendId": "x"},
                                        }
                                    ]
                                },
                                "LATE": "b",
                            }
                        },
                        "b": {},
                    },
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act
        await interpreter.send("S")
        await interpreter.send("C")
        await asyncio.sleep(0.15)

        # Assert — the delayed event never arrived.
        self.assertEqual({"m.a"}, interpreter.current_state_ids)

    async def test_escalate_reaches_parent(self) -> None:
        """`escalate` must send an error event to the parent actor."""
        # Arrange
        child = {
            "id": "kid",
            "initial": "idle",
            "states": {
                "idle": {
                    "on": {
                        "FAIL": {
                            "actions": [
                                {
                                    "type": "escalate",
                                    "params": {"error": "bad"},
                                }
                            ]
                        }
                    }
                }
            },
        }
        parent = {
            "id": "p",
            "initial": "a",
            "context": {},
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        }
                    ],
                    "on": {
                        "GO": {
                            "actions": [
                                {
                                    "type": "sendTo",
                                    "params": {"to": "k", "event": "FAIL"},
                                }
                            ]
                        },
                        "*": "caught",
                    },
                },
                "caught": {},
            },
        }
        interpreter = await Interpreter(
            create_machine(
                parent,
                logic=MachineLogic(
                    services={"kid": lambda i, c, e: build(child)}
                ),
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await asyncio.sleep(0.03)

        # Act
        await interpreter.send("GO")
        await asyncio.sleep(0.1)

        # Assert — the escalation was observed by the parent.
        self.assertEqual({"p.caught"}, interpreter.current_state_ids)

    async def test_forward_to_relays_event(self) -> None:
        """`forwardTo` must relay the triggering event to a child."""
        # Arrange
        child = {
            "id": "kid",
            "initial": "idle",
            "states": {"idle": {"on": {"WORK": "busy"}}, "busy": {}},
        }
        parent = {
            "id": "p",
            "initial": "a",
            "context": {},
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        }
                    ],
                    "on": {
                        "WORK": {
                            "actions": [
                                {
                                    "type": "forwardTo",
                                    "params": {"to": "k"},
                                }
                            ]
                        }
                    },
                }
            },
        }
        interpreter = await Interpreter(
            create_machine(
                parent,
                logic=MachineLogic(
                    services={"kid": lambda i, c, e: build(child)}
                ),
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await asyncio.sleep(0.03)

        # Act
        await interpreter.send("WORK")
        await asyncio.sleep(0.08)

        # Assert
        self.assertEqual(
            {"kid.busy"}, interpreter._actors["p:k"].current_state_ids
        )

    async def test_stop_child_in_async_engine(self) -> None:
        """`stopChild` must deregister and stop the child."""
        # Arrange
        child = {"id": "kid", "initial": "idle", "states": {"idle": {}}}
        parent = {
            "id": "p",
            "initial": "a",
            "context": {},
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        }
                    ],
                    "on": {
                        "STOP": {
                            "actions": [
                                {
                                    "type": "stopChild",
                                    "params": {"id": "k"},
                                }
                            ]
                        }
                    },
                }
            },
        }
        interpreter = await Interpreter(
            create_machine(
                parent,
                logic=MachineLogic(
                    services={"kid": lambda i, c, e: build(child)}
                ),
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await asyncio.sleep(0.03)
        self.assertEqual(1, len(interpreter._actors))

        # Act
        await interpreter.send("STOP")
        await asyncio.sleep(0.08)

        # Assert
        self.assertEqual(0, len(interpreter._actors))

    async def test_emit_in_async_engine(self) -> None:
        """`emit` must reach listeners on the async engine."""
        # Arrange
        received: List[str] = []
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {
                            "on": {
                                "E": {
                                    "actions": [
                                        {
                                            "type": "emit",
                                            "params": {"event": "OUT"},
                                        }
                                    ]
                                }
                            }
                        }
                    },
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        interpreter.on("OUT", lambda ev: received.append(ev.type))

        # Act
        await settle(interpreter, "E")

        # Assert
        self.assertEqual(["OUT"], received)

    async def test_deep_persistence_in_async_engine(self) -> None:
        """Async snapshots must also capture child actors."""
        # Arrange
        child = {"id": "kid", "initial": "idle", "states": {"idle": {}}}
        parent = {
            "id": "p",
            "initial": "a",
            "context": {},
            "states": {
                "a": {
                    "entry": [
                        {
                            "type": "spawnChild",
                            "params": {"src": "kid", "id": "k"},
                        }
                    ]
                }
            },
        }
        interpreter = await Interpreter(
            create_machine(
                parent,
                logic=MachineLogic(
                    services={"kid": lambda i, c, e: build(child)}
                ),
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await asyncio.sleep(0.03)

        # Act
        data = json.loads(interpreter.get_snapshot())

        # Assert
        self.assertIn("p:k", data["actors"])


# -----------------------------------------------------------------------------
# 🧩 Helper Edge Cases
# -----------------------------------------------------------------------------
class TestHelperEdgeCases(unittest.IsolatedAsyncioTestCase):
    """Covers timeout, terminal-status and blocking-wait helper paths."""

    async def test_wait_for_times_out(self) -> None:
        """`wait_for` must raise when the predicate never holds."""
        # Arrange
        interpreter = await Interpreter(
            build({"id": "m", "initial": "a", "states": {"a": {}}})
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act / Assert
        with self.assertRaises(TimeoutError):
            await wait_for(
                interpreter, lambda i: i.matches("m.nope"), timeout=0.05
            )

    async def test_wait_for_detects_terminal_status(self) -> None:
        """Reaching a terminal status must abort the wait promptly."""
        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "a",
                    "states": {
                        "a": {"on": {"E": "f"}},
                        "f": {"type": "final"},
                    },
                }
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)
        await interpreter.send("E")
        await asyncio.sleep(0.05)

        # Act / Assert — the machine is done and can never match.
        with self.assertRaises(TimeoutError):
            await wait_for(
                interpreter, lambda i: i.matches("m.never"), timeout=2
            )

    async def test_to_promise_reraises_machine_error(self) -> None:
        """`to_promise` must propagate a machine's recorded error."""

        async def boom(_i: Any, _c: Any, _e: Any) -> None:
            """A deliberately failing service."""
            raise ValueError("kaboom")

        # Arrange
        interpreter = await Interpreter(
            build(
                {
                    "id": "m",
                    "initial": "l",
                    "states": {"l": {"invoke": {"src": "b"}}},
                },
                services={"b": boom},
            )
        ).start()
        self.addAsyncCleanup(interpreter.stop)

        # Act / Assert
        with self.assertRaises(ValueError):
            await to_promise(interpreter, timeout=2)

    def test_wait_for_sync_returns_when_satisfied(self) -> None:
        """The blocking helper must return once the predicate holds."""
        # Arrange
        interpreter = start(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"E": "b"}}, "b": {}},
            }
        )
        interpreter.send("E")

        # Act
        result = wait_for_sync(
            interpreter, lambda i: i.matches("m.b"), timeout=1
        )

        # Assert
        self.assertIs(interpreter, result)

    def test_wait_for_sync_times_out(self) -> None:
        """The blocking helper must raise when unsatisfied."""
        # Arrange
        interpreter = start({"id": "m", "initial": "a", "states": {"a": {}}})

        # Act / Assert
        with self.assertRaises(TimeoutError):
            wait_for_sync(
                interpreter, lambda i: i.matches("m.nope"), timeout=0.05
            )

    def test_pure_snapshot_repr(self) -> None:
        """`PureSnapshot` must render readably for debugging."""
        # Arrange
        snapshot, _ = initial_transition(
            build({"id": "m", "initial": "a", "states": {"a": {}}})
        )

        # Assert
        self.assertIn("PureSnapshot", repr(snapshot))
        self.assertIn("m.a", repr(snapshot))

    def test_actor_system_repr_and_contains(self) -> None:
        """`ActorSystem` must support `in` and render readably."""
        # Arrange
        interpreter = start({"id": "m", "initial": "a", "states": {"a": {}}})

        # Assert
        self.assertIn("ActorSystem", repr(interpreter.system))
        self.assertNotIn("ghost", interpreter.system)


# -----------------------------------------------------------------------------
# 🧾 Model Representations
# -----------------------------------------------------------------------------
class TestModelRepr(unittest.TestCase):
    """Covers the `__repr__` helpers used when debugging configurations."""

    def test_guard_definition_repr(self) -> None:
        """Simple and composite guards must render distinctly."""
        # Arrange
        simple = GuardDefinition("isReady")
        composite = GuardDefinition({"type": "and", "children": ["a", "b"]})

        # Assert
        self.assertIn("isReady", repr(simple))
        self.assertIn("and", repr(composite))

    def test_guard_definition_is_idempotent(self) -> None:
        """Re-wrapping an existing definition must be a no-op."""
        # Arrange
        original = GuardDefinition({"type": "g", "params": {"n": 1}})

        # Act
        rewrapped = GuardDefinition(original)

        # Assert
        self.assertEqual(original.type, rewrapped.type)
        self.assertEqual(original.params, rewrapped.params)

    def test_guard_definition_rejects_bad_type(self) -> None:
        """A non-string, non-dict guard must be rejected."""
        # Act / Assert
        with self.assertRaises(InvalidConfigError):
            GuardDefinition(123)

    def test_not_guard_via_params_shorthand(self) -> None:
        """`{"type": "not", "params": {"guard": ...}}` must be accepted."""
        # Arrange
        definition = GuardDefinition(
            {"type": "not", "params": {"guard": "inner"}}
        )

        # Assert
        self.assertTrue(definition.is_composite)
        self.assertEqual(1, len(definition.children))

    def test_composite_guard_via_params_guards(self) -> None:
        """`params.guards` must be accepted as the operand list."""
        # Arrange
        definition = GuardDefinition(
            {"type": "or", "params": {"guards": ["a", "b"]}}
        )

        # Assert
        self.assertEqual(2, len(definition.children))

    def test_is_builtin_property(self) -> None:
        """`is_builtin` must cover composite and stateIn guards."""
        # Assert
        self.assertTrue(
            GuardDefinition({"type": "and", "children": ["a"]}).is_builtin
        )
        self.assertTrue(
            GuardDefinition({"type": "stateIn", "params": {}}).is_builtin
        )
        self.assertFalse(GuardDefinition("plain").is_builtin)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
