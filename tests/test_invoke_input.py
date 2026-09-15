# tests/test_invoke_input.py
# -----------------------------------------------------------------------------
# 🏛️ #42 (LC-29): `invoke.input` may be a callable and MUST reach the child
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: `InvokeDefinition.input` was stored verbatim
# (so a callable stayed a function object) and, for a child MACHINE, never
# forwarded at all -- the child was constructed with no input. XState v5's
# contract is `input: ({context, event}) => value`, resolved per spawn and
# handed to the child's `context` factory as `{input}`. Both engines now
# resolve it through one `InvokeDefinition.resolve_input()` and pass the
# result as the child's `input`.
#
# Seeding rule when the child has NO context factory: `input` is exposed
# at `context["input"]` -- the 0.7.x convention, unchanged. It is NOT
# spread into declared keys: that would make `Interpreter(m, input=...)` a
# context-injection vector (review F11). A child that wants its keys filled
# from the parent declares a `context` factory: `lambda a: {...a["input"]}`.
# -----------------------------------------------------------------------------
"""`invoke.input`: static, callable, deep-copied, forwarded to machines."""

import asyncio
import logging
import unittest
from typing import Any, Dict

from src.xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
)
from src.xstate_statemachine.models import InvokeDefinition


class _Quiet(unittest.TestCase):
    def setUp(self) -> None:
        logging.disable(logging.CRITICAL)
        self.addCleanup(logging.disable, logging.NOTSET)


# The filer's child, now with the XState-idiomatic factory that reads input.
CHILD: Dict[str, Any] = {
    "id": "leg",
    "initial": "work",
    "context": lambda args: {
        "snapshot": (args["input"] or {}).get("snapshot")
    },
    "states": {"work": {"on": {"GO": "done"}}, "done": {"type": "final"}},
}
# A child with a PLAIN context dict: input lands only at context["input"].
CHILD_PLAIN: Dict[str, Any] = {
    "id": "leg",
    "initial": "work",
    "context": {"snapshot": None},
    "states": {"work": {}},
}
CHILD_WITH_FACTORY: Dict[str, Any] = {
    "id": "leg",
    "initial": "work",
    "context": lambda args: {"venue": args["input"]["venue"], "seen": True},
    "states": {"work": {}},
}


def _parent(invoke_input: Any, child: Dict[str, Any] = CHILD) -> Any:
    cfg = {
        "id": "book",
        "context": {"profile": {"venue": "X", "size": 7}},
        "initial": "running",
        "states": {
            "running": {
                "invoke": {"id": "leg1", "src": "leg", "input": invoke_input}
            }
        },
    }
    return create_machine(
        cfg, logic=MachineLogic(services={"leg": create_machine(child)})
    )


async def _child_of(machine: Any) -> Any:
    i = await Interpreter(machine).start()
    for _ in range(200):
        if "book:leg1" in i._actors:
            break
        await asyncio.sleep(0.002)
    child = i._actors["book:leg1"]
    await i.stop()
    return child, i


def _inv(invoke_input: Any) -> InvokeDefinition:
    """Build a real InvokeDefinition through create_machine."""
    cfg = {
        "id": "h",
        "initial": "s",
        "states": {"s": {"invoke": {"src": "svc", "input": invoke_input}}},
    }
    if invoke_input is None:
        del cfg["states"]["s"]["invoke"]["input"]
    m = create_machine(cfg, logic=MachineLogic(services={"svc": lambda *a: 1}))
    return m.states["s"].invoke[0]


class TestResolveInput(_Quiet):
    def test_static_input_is_deep_copied(self) -> None:
        static = {"snapshot": {"venue": "X"}}
        out = _inv(static).resolve_input({}, None)
        self.assertEqual(out, static)
        self.assertIsNot(out["snapshot"], static["snapshot"])

    def test_callable_two_arity_gets_context_and_event(self) -> None:
        inv = _inv(lambda ctx, evt: {"v": ctx["x"], "e": evt})
        self.assertEqual(inv.resolve_input({"x": 1}, "E"), {"v": 1, "e": "E"})

    def test_callable_single_mapping_arity(self) -> None:
        inv = _inv(lambda args: args["context"]["x"])
        self.assertEqual(inv.resolve_input({"x": 9}, None), 9)

    def test_no_input_resolves_to_none(self) -> None:
        self.assertIsNone(_inv(None).resolve_input({}, None))


class TestInputReachesChildMachine(_Quiet):
    def test_static_input_seeds_child_machine_context(self) -> None:
        child, _ = asyncio.run(
            _child_of(_parent({"snapshot": {"venue": "X", "size": 7}}))
        )
        self.assertEqual(child.context["snapshot"], {"venue": "X", "size": 7})
        self.assertEqual(child.input, {"snapshot": {"venue": "X", "size": 7}})
        self.assertNotIn("input", child.context)  # the factory shaped it

    def test_callable_input_resolved_against_parent_context_and_event(
        self,
    ) -> None:
        child, _ = asyncio.run(
            _child_of(_parent(lambda ctx, evt: {"snapshot": ctx["profile"]}))
        )
        self.assertEqual(child.context["snapshot"], {"venue": "X", "size": 7})

    def test_callable_input_single_mapping_arity(self) -> None:
        child, _ = asyncio.run(
            _child_of(
                _parent(lambda args: {"snapshot": args["context"]["profile"]})
            )
        )
        self.assertEqual(child.context["snapshot"]["venue"], "X")

    def test_input_is_deep_copied_not_aliased(self) -> None:
        async def main():
            m = _parent(lambda ctx, evt: {"snapshot": ctx["profile"]})
            i = await Interpreter(m).start()
            for _ in range(200):
                if "book:leg1" in i._actors:
                    break
                await asyncio.sleep(0.002)
            child = i._actors["book:leg1"]
            i.context["profile"]["venue"] = "MUTATED"
            out = child.context["snapshot"]["venue"]
            await i.stop()
            return out

        self.assertEqual(asyncio.run(main()), "X")

    def test_child_context_factory_receives_input_key(self) -> None:
        child, _ = asyncio.run(
            _child_of(_parent({"venue": "Z"}, child=CHILD_WITH_FACTORY))
        )
        self.assertEqual(child.context, {"venue": "Z", "seen": True})

    def test_plain_context_child_gets_input_only_under_input_key(
        self,
    ) -> None:
        """No factory -> 0.7.x rule: declared keys are NOT overwritten."""
        child, _ = asyncio.run(
            _child_of(_parent({"snapshot": 1, "extra": 2}, child=CHILD_PLAIN))
        )
        self.assertIsNone(child.context["snapshot"])  # untouched
        self.assertNotIn("extra", child.context)
        self.assertEqual(child.context["input"], {"snapshot": 1, "extra": 2})

    def test_input_resolver_exception_becomes_on_error(self) -> None:
        def bad(ctx, evt):
            raise KeyError("profile missing")

        cfg = {
            "id": "book",
            "initial": "running",
            "context": {"err": None},
            "states": {
                "running": {
                    "invoke": {
                        "id": "leg1",
                        "src": "leg",
                        "input": bad,
                        "onError": {"target": "failed", "actions": ["rec"]},
                    }
                },
                "failed": {},
            },
        }

        def rec(i, c, e, a):
            c["err"] = repr(e.data)

        async def main():
            m = create_machine(
                cfg,
                logic=MachineLogic(
                    actions={"rec": rec},
                    services={"leg": create_machine(CHILD)},
                ),
            )
            i = await Interpreter(m).start()
            await asyncio.sleep(0.05)
            out = (set(i.current_state_ids), i.context["err"], i.status)
            await i.stop()
            return out

        state, err, status = asyncio.run(main())
        self.assertEqual(state, {"book.failed"})
        self.assertIn("profile missing", err)
        self.assertEqual(status, "running")

    def test_callable_service_input_matches_machine_service_input(
        self,
    ) -> None:
        """A callable `src` receives the SAME resolved input as a machine."""
        got: Dict[str, Any] = {}

        async def svc(interp, ctx, event):
            got["payload"] = event.payload
            return "ok"

        cfg = {
            "id": "book",
            "initial": "running",
            "context": {"profile": {"venue": "X"}},
            "states": {
                "running": {
                    "invoke": {
                        "src": "svc",
                        "input": lambda ctx, evt: {"snapshot": ctx["profile"]},
                    }
                }
            },
        }

        async def main():
            i = await Interpreter(
                create_machine(cfg, logic=MachineLogic(services={"svc": svc}))
            ).start()
            await asyncio.sleep(0.03)
            await i.stop()

        asyncio.run(main())
        self.assertEqual(
            got["payload"], {"input": {"snapshot": {"venue": "X"}}}
        )


class TestInputSync(_Quiet):
    def _run(self, invoke_input: Any) -> Any:
        i = SyncInterpreter(_parent(invoke_input)).start()
        child = i._actors["book:leg1"]
        i.stop()
        return child

    def test_static_input_seeds_child_sync(self) -> None:
        child = self._run({"snapshot": {"venue": "X", "size": 7}})
        self.assertEqual(child.context["snapshot"], {"venue": "X", "size": 7})

    def test_callable_input_sync(self) -> None:
        child = self._run(lambda ctx, evt: {"snapshot": ctx["profile"]})
        self.assertEqual(child.context["snapshot"]["size"], 7)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
