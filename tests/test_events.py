# tests/test_events.py
# -----------------------------------------------------------------------------
# 🏛️ #79: reserved event namespaces are a documented, build-time-visible fact
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: the engine tells its own synthesised events
# (`done.invoke.*`, `error.platform.*`, `after.*`, `xstate.*`, the init
# sentinels) apart from user traffic by NAME PREFIX, and the wildcard
# matcher, `onUnhandled` and strict mode all consult that one list. That is
# deliberate and cheap -- but it means a user event that happens to live in
# one of those namespaces gets system-event semantics. 0.8.1 does not change
# the mechanism; it (a) centralises the list in `events.SYSTEM_EVENT_PREFIXES`,
# (b) warns at `create_machine()` for `on` keys in a reserved namespace, and
# (c) pins the current behaviour so it is a contract, not a surprise.
# -----------------------------------------------------------------------------
"""Reserved event namespaces (#79)."""

import asyncio
import logging
import unittest
import warnings
from typing import Any, Dict

from src.xstate_statemachine import (
    UnhandledEventError,
    UnknownEventError,
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.events import SYSTEM_EVENT_PREFIXES


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


WILDCARD: Dict[str, Any] = {
    "id": "wc",
    "initial": "a",
    "context": {"caught": []},
    "states": {"a": {"on": {"*": {"actions": ["note"]}}}},
}


def _note_logic() -> MachineLogic:
    def note(i, c, e, a):
        c["caught"].append(e.type)

    return MachineLogic(actions={"note": note})


class TestReservedPrefixList(_Quiet):
    def test_prefix_list_is_public_and_complete(self) -> None:
        self.assertEqual(
            SYSTEM_EVENT_PREFIXES,
            ("done.", "error.", "after.", "xstate.", "___xstate"),
        )


class TestPinnedRuntimeSemantics(_Quiet):
    """The behaviour the warning describes, pinned so it cannot drift
    silently in either direction."""

    def test_exact_key_in_reserved_namespace_still_matches(self) -> None:
        cfg = {
            "id": "ex",
            "initial": "a",
            "states": {"a": {"on": {"done.review": "b"}}, "b": {}},
        }
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            i = SyncInterpreter(create_machine(cfg))
        i.start()
        i.send("done.review")
        self.assertEqual(set(i.current_state_ids), {"ex.b"})
        i.stop()

    def test_user_event_in_reserved_namespace_matches_wildcard(self) -> None:
        """#79 acceptance: a USER-sent `error.myapp.validation` or
        `done.review` is user traffic and reaches `"*"`. Only events the
        engine minted are exempt -- provenance, not spelling."""

        async def main():
            i = await Interpreter(
                create_machine(WILDCARD, logic=_note_logic())
            ).start()
            for ev in (
                "PLAIN",
                "error.myapp.validation",
                "done.review",
                "my.ns",
            ):
                await i.send(ev)
            await asyncio.sleep(0.05)
            out = list(i.context["caught"])
            await i.stop()
            return out

        self.assertEqual(
            asyncio.run(main()),
            ["PLAIN", "error.myapp.validation", "done.review", "my.ns"],
        )

    def test_user_event_in_reserved_namespace_trips_onunhandled_error(
        self,
    ) -> None:
        """#79 acceptance: an unhandled user `done.review` is a policy
        violation like any other unhandled user event."""
        cfg = {
            "id": "u",
            "initial": "a",
            "onUnhandled": "error",
            "states": {"a": {"on": {"GO": "a"}}},
        }
        i = SyncInterpreter(create_machine(cfg))
        i.start()
        i.send("done.review")
        # `onUnhandled: "error"` fails the machine (status/error), the same
        # observable as for any other unhandled user event.
        self.assertEqual(i.status, "error")
        self.assertIsInstance(i.error, UnhandledEventError)

    def test_user_event_in_reserved_namespace_is_checked_by_strict(
        self,
    ) -> None:
        """#79: strict mode no longer treats a bare `done.` / `error.`
        prefix as a free pass for user events."""
        cfg = {
            "id": "s",
            "initial": "a",
            "states": {"a": {"on": {"GO": "a"}}},
        }
        i = SyncInterpreter(create_machine(cfg), strict=True)
        i.start()
        with self.assertRaises(UnknownEventError):
            i.send("done.typo")
        i.stop()

    def test_engine_synthesised_events_remain_exempt_from_onunhandled(
        self,
    ) -> None:
        """No regression to the 0.8.0 fix: a `done.invoke.*` the machine
        does not handle must not trip `onUnhandled: "error"`."""

        async def quick(i, c, e):
            return 1

        cfg = {
            "id": "ue",
            "initial": "a",
            "onUnhandled": "error",
            "states": {"a": {"invoke": {"id": "q", "src": "quick"}}},
        }

        async def main():
            i = await Interpreter(
                create_machine(
                    cfg, logic=MachineLogic(services={"quick": quick})
                )
            ).start()
            await asyncio.sleep(0.05)
            out = i.status
            if out == "running":
                await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), "running")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
