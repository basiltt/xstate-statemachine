# tests/test_strict.py
# -----------------------------------------------------------------------------
# 🏛️ #51 (LC-34): strict mode -- an unknown event is an ERROR, not a no-op
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: XState ignores an event no active state handles,
# and that stays the default (it is the correct actor semantics). But there
# are two very different reasons an event goes unhandled: the machine
# DECLARES it somewhere and the current state simply does not care (fine),
# or NOTHING in the machine has ever heard of it (a typo, an outdated
# producer). The second is a bug no test can catch when it is a no-op.
# `strict` distinguishes them: the machine's full descriptor set is built
# once at create_machine(), and a send of an undeclared type raises
# `UnknownEventError` SYNCHRONOUSLY at the call site -- before queueing --
# because the async `send()` is fire-and-forget and a run-loop error could
# never be caught by the caller. Payload schemas are the same idea for the
# event's shape, dependency-free: any object with `validate`/`__call__`.
# -----------------------------------------------------------------------------
"""Strict mode: unknown events and payload schemas (#51)."""

import asyncio
import inspect
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    Interpreter,
    InvalidEventPayloadError,
    MachineLogic,
    SyncInterpreter,
    UnknownEventError,
    XStateMachineError,
    create_machine,
)


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


ORDER: Dict[str, Any] = {
    "id": "order",
    "initial": "pending",
    "states": {
        "pending": {"on": {"FILL": "filled", "CANCEL": "cancelled"}},
        "filled": {"type": "final"},
        "cancelled": {"type": "final"},
    },
}


def _run(coro):
    return asyncio.run(coro)


class TestSurface(_Quiet):
    def test_strict_accepted_on_config_and_both_constructors(self) -> None:
        m = create_machine(dict(ORDER, strict=True))
        self.assertTrue(m.strict)
        for cls in (Interpreter, SyncInterpreter):
            self.assertIn("strict", inspect.signature(cls.__init__).parameters)

    def test_exceptions_subclass_the_library_base(self) -> None:
        self.assertTrue(issubclass(UnknownEventError, XStateMachineError))
        self.assertTrue(
            issubclass(InvalidEventPayloadError, XStateMachineError)
        )

    def test_known_events_exposes_declared_descriptors(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "on": {"GO": "b", "mouse.*": "b"},
                    "after": {"100": "b"},
                    "invoke": {"src": "svc", "id": "job", "onDone": "b"},
                },
                "b": {"type": "final"},
            },
        }
        m = create_machine(
            cfg, logic=MachineLogic(services={"svc": lambda *a: 1})
        )
        known = m.known_events
        self.assertIn("GO", known)
        self.assertIn("mouse.*", known)
        self.assertTrue(any(k.startswith("after.") for k in known), known)
        self.assertIn("done.invoke.job", known)
        self.assertIn("error.platform.job", known)


class TestUnknownEvents(_Quiet):
    def test_unknown_event_raises_under_strict(self) -> None:
        async def main():
            i = await Interpreter(create_machine(ORDER), strict=True).start()
            try:
                await i.send("FILLL")
            except UnknownEventError as exc:
                out = str(exc)
            else:
                out = None
            await i.stop()
            return out

        msg = _run(main())
        self.assertIsNotNone(msg)
        self.assertIn("'FILLL'", msg)
        self.assertIn("order", msg)
        self.assertIn("CANCEL", msg)
        self.assertIn("FILL", msg)

    def test_unknown_event_error_suggests_close_match(self) -> None:
        async def main():
            i = await Interpreter(create_machine(ORDER), strict=True).start()
            try:
                await i.send("FILLL")
            except UnknownEventError as exc:
                return str(exc)
            finally:
                await i.stop()

        self.assertIn("Did you mean 'FILL'?", _run(main()))

    def test_declared_but_unhandled_event_is_still_ignored(self) -> None:
        """CANCEL is declared in `pending` but not in `filled`: a no-op."""

        async def main():
            i = await Interpreter(create_machine(ORDER), strict=True).start()
            await i.send("FILL")
            await asyncio.sleep(0.02)
            await i.send("CANCEL")  # known, unhandled here -> ignored
            await asyncio.sleep(0.02)
            out = (set(i.current_state_ids), i.status)
            await i.stop()
            return out

        self.assertEqual(_run(main()), ({"order.filled"}, "done"))

    def test_wildcard_descriptor_does_not_disable_unknown_check(self) -> None:
        # #190: `strict` is a DECLARATION rule; a `"*"` DISPATCH handler
        # must not silently switch it off for the whole machine.
        from src.xstate_statemachine import UnknownEventError

        cfg = {"id": "m", "initial": "a", "states": {"a": {"on": {"*": {}}}}}

        async def main():
            i = await Interpreter(create_machine(cfg), strict=True).start()
            try:
                with self.assertRaises(UnknownEventError):
                    await i.send("ANYTHING_AT_ALL")
            finally:
                await i.stop()
            return "ok"

        self.assertEqual(_run(main()), "ok")

    def test_wildcard_still_dispatches_when_not_strict(self) -> None:
        hits = []
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"*": {"actions": ["hit"]}}}},
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    cfg,
                    logic=MachineLogic(
                        actions={"hit": lambda i, c, e, a: hits.append(e.type)}
                    ),
                )
            ).start()
            await i.send("ANYTHING_AT_ALL", wait=True)
            await i.stop()

        _run(main())
        self.assertEqual(hits, ["ANYTHING_AT_ALL"])

    def test_partial_descriptor_counts_as_known(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {"mouse.*": {}}}},
        }

        async def main():
            i = await Interpreter(create_machine(cfg), strict=True).start()
            await i.send("mouse.click")
            try:
                await i.send("keyboard.press")
            except UnknownEventError:
                out = "raised"
            else:
                out = "silent"
            await i.stop()
            return out

        self.assertEqual(_run(main()), "raised")

    def test_strict_raises_synchronously_before_queueing(self) -> None:
        async def main():
            i = await Interpreter(create_machine(ORDER), strict=True).start()
            with self.assertRaises(UnknownEventError):
                i.send("FILLL")  # NOT awaited: must still raise here
            depth = i.queue_depth
            await i.stop()
            return depth

        self.assertEqual(_run(main()), 0)

    def test_internal_raise_of_unknown_event_is_strict(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "actionErrorPolicy": "fail",
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "actions": [
                                {"type": "raise", "params": {"event": "NOPE"}}
                            ]
                        }
                    }
                }
            },
        }

        async def main():
            i = await Interpreter(create_machine(cfg), strict=True).start()
            await i.send("GO")
            await asyncio.sleep(0.05)
            out = (i.status, type(i.error).__name__ if i.error else None)
            await i.stop()
            return out

        status, err = _run(main())
        self.assertEqual(status, "stopped")  # #145: "fail" stops the machine
        self.assertEqual(err, "TransitionFailedError")

    def test_after_and_invoke_generated_events_are_known(self) -> None:
        cfg = {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {
                    "after": {"10": "b"},
                    "invoke": {"src": "svc", "onDone": "c"},
                },
                "b": {"type": "final"},
                "c": {"type": "final"},
            },
        }

        async def svc(i, c, e):
            await asyncio.sleep(0.05)
            return 1

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(services={"svc": svc})),
                strict=True,
            ).start()
            for _ in range(200):
                if i.status == "done":
                    break
                await asyncio.sleep(0.005)
            out = (i.status, i.error)
            await i.stop()
            return out

        status, err = _run(main())
        self.assertEqual(status, "done")
        self.assertIsNone(err)

    def test_non_strict_default_is_unchanged(self) -> None:
        async def main():
            i = await Interpreter(create_machine(ORDER)).start()
            await i.send("FILLL")  # silent no-op
            await asyncio.sleep(0.02)
            out = (set(i.current_state_ids), i.status)
            await i.stop()
            return out

        self.assertEqual(_run(main()), ({"order.pending"}, "running"))


class TestPayloadSchemas(_Quiet):
    class Fill:
        """A dependency-free validator: any object with validate()/__call__."""

        @staticmethod
        def validate(payload: Dict[str, Any]) -> None:
            if not isinstance(payload.get("qty"), (int, float)):
                raise ValueError("qty: Input should be a valid number")

    def test_payload_schema_validates(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(ORDER, event_schemas={"FILL": self.Fill})
            ).start()
            await i.send("FILL", qty=1.0)
            await asyncio.sleep(0.02)
            out = set(i.current_state_ids)
            await i.stop()
            return out

        self.assertEqual(_run(main()), {"order.filled"})

    def test_payload_schema_rejects(self) -> None:
        async def main():
            i = await Interpreter(
                create_machine(ORDER, event_schemas={"FILL": self.Fill})
            ).start()
            try:
                await i.send("FILL", qty="not-a-number")
            except InvalidEventPayloadError as exc:
                out = str(exc)
            else:
                out = None
            depth = i.queue_depth
            await i.stop()
            return out, depth

        msg, depth = _run(main())
        self.assertIn("'FILL'", msg)
        self.assertIn("valid number", msg)
        self.assertEqual(depth, 0)

    def test_callable_schema_is_accepted(self) -> None:
        def check(payload):
            if "qty" not in payload:
                raise KeyError("qty")

        i = SyncInterpreter(
            create_machine(ORDER, event_schemas={"FILL": check})
        ).start()
        with self.assertRaises(InvalidEventPayloadError):
            i.send("FILL")
        i.send("FILL", qty=1)
        self.assertEqual(i.current_state_ids, {"order.filled"})


class TestStrictSync(_Quiet):
    def test_unknown_event_raises_sync(self) -> None:
        i = SyncInterpreter(create_machine(ORDER), strict=True).start()
        with self.assertRaises(UnknownEventError) as cm:
            i.send("FILLL")
        self.assertIn("Did you mean 'FILL'?", str(cm.exception))
        self.assertEqual(i.current_state_ids, {"order.pending"})
        i.stop()

    def test_declared_unhandled_ignored_sync(self) -> None:
        i = SyncInterpreter(create_machine(ORDER), strict=True).start()
        i.send("FILL")
        i.send("CANCEL")
        self.assertEqual(i.current_state_ids, {"order.filled"})

    def test_config_key_strict_applies_without_ctor_flag(self) -> None:
        i = SyncInterpreter(create_machine(dict(ORDER, strict=True))).start()
        with self.assertRaises(UnknownEventError):
            i.send("FILLL")
        i.stop()


class TestStrictPropagatesToChildren(_Quiet):
    """#51 (0.8.0 audit): a parent that opted into `strict=True` at the
    constructor must hand that down to every child it creates -- spawned
    AND invoked -- on both engines. The sync engine was fixed first; this
    pins the async engine's two child constructors to the same contract.
    """

    CHILD: Dict[str, Any] = {
        "id": "child",
        "initial": "wait",
        "states": {"wait": {"on": {"KNOWN": "wait"}}},
    }

    def _parent(self, how: str) -> Any:
        state = (
            {"entry": ["spawn_kid"]}
            if how == "spawn"
            else {"invoke": {"src": "kid", "id": "k"}}
        )
        return create_machine(
            {"id": "p", "initial": "a", "states": {"a": state}},
            logic=MachineLogic(services={"kid": create_machine(self.CHILD)}),
        )

    def _async_child(self, how: str) -> Any:
        async def main():
            i = await Interpreter(self._parent(how), strict=True).start()
            for _ in range(200):
                if i._actors:
                    break
                await asyncio.sleep(0.002)
            (child,) = i._actors.values()
            out = (child.strict, child.machine.strict)
            await i.stop()
            return out

        return _run(main())

    def test_async_spawned_child_inherits_ctor_strict(self) -> None:
        self.assertEqual(self._async_child("spawn"), (True, False))

    def test_async_invoked_child_inherits_ctor_strict(self) -> None:
        self.assertEqual(self._async_child("invoke"), (True, False))

    def test_sync_invoked_child_inherits_ctor_strict(self) -> None:
        i = SyncInterpreter(self._parent("invoke"), strict=True).start()
        (child,) = i._actors.values()
        self.assertTrue(child.strict)
        with self.assertRaises(UnknownEventError):
            child.send("UNDECLARED")
        i.stop()


# -----------------------------------------------------------------------------
# #51 follow-up -- a strict machine cannot raise, from a literal, an event
# it never handles. Caught at create_machine(), so `actionErrorPolicy` is
# irrelevant.
# -----------------------------------------------------------------------------
class TestStrictStaticRaise(_Quiet):
    @staticmethod
    def _cfg(raised: Any, strict: bool = True) -> Dict[str, Any]:
        return {
            "id": "sr",
            "initial": "a",
            "strict": strict,
            "states": {
                "a": {
                    "on": {
                        "GO": {
                            "target": "b",
                            "actions": [
                                {"type": "raise", "params": {"event": raised}}
                            ],
                        },
                        "PING": "a",
                    }
                },
                "b": {
                    "entry": [{"type": "raise", "params": {"event": "PING"}}]
                },
            },
        }

    def test_typo_in_static_raise_is_a_build_time_error(self) -> None:
        from src.xstate_statemachine import InvalidConfigError

        with self.assertRaises(InvalidConfigError) as cm:
            create_machine(self._cfg("PINK"))
        msg = str(cm.exception)
        self.assertIn("'PINK'", msg)
        self.assertIn("Did you mean 'PING'", msg)

    def test_dict_form_event_is_checked_too(self) -> None:
        from src.xstate_statemachine import InvalidConfigError

        with self.assertRaises(InvalidConfigError):
            create_machine(self._cfg({"type": "PINK", "x": 1}))

    def test_declared_raise_builds(self) -> None:
        create_machine(self._cfg("PING"))
        create_machine(self._cfg({"type": "PING"}))

    def test_not_strict_is_unchanged(self) -> None:
        create_machine(self._cfg("PINK", strict=False))

    def test_wildcard_makes_every_raise_known(self) -> None:
        cfg = self._cfg("ANYTHING")
        cfg["states"]["b"]["on"] = {"*": "a"}
        create_machine(cfg)


# -----------------------------------------------------------------------------
# #78 -- `send_threadsafe()` carries the same guardrail as `send()`
# -----------------------------------------------------------------------------
class TestSendThreadsafeStrict(_Quiet):
    """The recommended cross-thread entry point must not be the one entry
    point without validation."""

    class Qty:
        @staticmethod
        def validate(payload: Dict[str, Any]) -> None:
            qty = (payload or {}).get("qty")
            if not isinstance(qty, int) or qty <= 0:
                raise ValueError("qty must be a positive int")

    def _run_from_thread(self, machine, strict: bool, *args, **kw):
        """Start an interpreter, call `send_threadsafe` from a worker, and
        return (exception-or-None, final state ids)."""
        import threading

        async def main():
            i = await Interpreter(
                create_machine(**machine), strict=strict
            ).start()
            box: Dict[str, Any] = {}

            def worker():
                try:
                    i.send_threadsafe(*args, **kw).result(1)
                except Exception as exc:  # noqa: BLE001
                    box["exc"] = exc

            t = threading.Thread(target=worker)
            t.start()
            for _ in range(30):
                await asyncio.sleep(0.01)
            t.join(1)
            out = (box.get("exc"), set(i.current_state_ids))
            await i.stop()
            return out

        return _run(main())

    def test_send_threadsafe_rejects_unknown_event(self) -> None:
        exc, _ = self._run_from_thread({"config": ORDER}, True, "FIL")
        self.assertIsInstance(exc, UnknownEventError)
        self.assertIn("FILL", str(exc))  # difflib suggestion

    def test_send_threadsafe_validates_payload_schema(self) -> None:
        exc, _ = self._run_from_thread(
            {"config": ORDER, "event_schemas": {"FILL": self.Qty}},
            False,
            "FILL",
            qty=-1,
        )
        self.assertIsInstance(exc, InvalidEventPayloadError)

    def test_send_threadsafe_invalid_payload_does_not_transition(self) -> None:
        _, state = self._run_from_thread(
            {"config": ORDER, "event_schemas": {"FILL": self.Qty}},
            False,
            "FILL",
            qty=-1,
        )
        self.assertNotIn("order.filled", state)

    def test_send_threadsafe_valid_event_still_delivered(self) -> None:
        exc, state = self._run_from_thread(
            {"config": ORDER, "event_schemas": {"FILL": self.Qty}},
            True,
            "FILL",
            qty=3,
        )
        self.assertIsNone(exc)
        self.assertEqual(state, {"order.filled"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
