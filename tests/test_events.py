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


class TestBuildTimeWarning(_Quiet):
    def _build(self, on: Dict[str, Any]):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            create_machine(
                {"id": "m", "initial": "a", "states": {"a": {"on": on}}}
            )
        return [str(w.message) for w in caught if w.category is UserWarning]

    def test_user_event_in_reserved_namespace_warns_at_build_time(
        self,
    ) -> None:
        msgs = self._build({"done.review": "a", "error.validation": "a"})
        self.assertEqual(len(msgs), 1)
        self.assertIn("'done.review'", msgs[0])
        self.assertIn("'error.validation'", msgs[0])
        self.assertIn("reserved namespace", msgs[0])

    def test_engine_shaped_keys_do_not_warn(self) -> None:
        msgs = self._build(
            {
                "done.invoke.fetch": "a",
                "done.state.m.a": "a",
                "error.platform.fetch": "a",
                "after.500": "a",
                "xstate.error.actor.kid": "a",
            }
        )
        self.assertEqual(msgs, [])

    def test_ordinary_dotted_names_do_not_warn(self) -> None:
        self.assertEqual(self._build({"review.done": "a", "my.ns.x": "a"}), [])


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

    def test_wildcard_does_not_match_reserved_namespace_user_event(
        self,
    ) -> None:
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

        self.assertEqual(asyncio.run(main()), ["PLAIN", "my.ns"])

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
