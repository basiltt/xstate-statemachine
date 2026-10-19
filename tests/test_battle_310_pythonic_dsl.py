# tests/test_battle_310_pythonic_dsl.py
"""
⚔️ Battle tests for the second-generation Pythonic DSL (#310).

These go beyond the feature tests in ``test_pythonic_dsl_v2.py`` and try
to break the new surface the way production code will: concurrent sends,
hooks that raise, deep nesting driven by a simulated clock, snapshot
round-trips of façade-built machines, inheritance chains, every shape of
callback signature, a 200-state machine, and lifecycle misuse.

Every test states the invariant it defends in its docstring.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import json
import logging
import threading
import time
import unittest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine import (
    ImplementationMissingError,
    Interpreter,
    InvalidConfigError,
    PluginBase,
    SimulatedClock,
    State,
    StateMachine,
    SyncInterpreter,
    TransitionNotAllowedError,
    create_machine,
)
from xstate_statemachine._pythonic_class import RESULT_SINK_MAXLEN
from xstate_statemachine.pythonic import action, build_machine, guard
from xstate_statemachine.testing_utils import stub_logic


# =========================================================================
# ⚡ Concurrency
# =========================================================================
class TestConcurrency(unittest.TestCase):
    def test_hundreds_of_concurrent_async_sends_keep_results_apart(self):
        """Invariant: each `await sm.send()` returns ITS actions' results,
        never a neighbour's, under heavy `gather` pressure."""

        class Counter(StateMachine):
            engine = "async"
            initial_context = {"n": 0}
            idle = State(initial=True)
            inc = idle.internal(actions=["bump"])

            @action
            def bump(self, context, amount):
                context["n"] += amount
                return amount

        async def main():
            async with Counter() as sm:
                results = await asyncio.gather(
                    *(sm.inc(amount=i) for i in range(1, 201))
                )
                self.assertEqual(results, list(range(1, 201)))
                self.assertEqual(sm.context["n"], sum(range(1, 201)))

        asyncio.run(main())

    def test_sync_facade_accepts_cross_thread_events_via_send_threadsafe(
        self,
    ):
        """Invariant: a sync façade is driven from other threads only via
        `sm.interpreter.send_threadsafe()`, and convention hooks run when
        the owning thread drains the mailbox."""
        seen = []

        class Light(StateMachine):
            initial_context = {"ticks": 0}
            green = State(initial=True)
            red = State()
            go = green.to(red) | red.to(green)

            def on_go(self, context):
                context["ticks"] += 1
                seen.append(threading.current_thread().name)

        with Light() as sm:
            producers = [
                threading.Thread(
                    target=sm.interpreter.send_threadsafe, args=("GO",)
                )
                for _ in range(20)
            ]
            for t in producers:
                t.start()
            for t in producers:
                t.join()
            sm.interpreter.tick()  # owner drains the mailbox
            self.assertEqual(sm.context["ticks"], 20)
            # 🧵 every hook ran on the OWNING thread, never a producer's
            self.assertEqual(set(seen), {threading.current_thread().name})


# =========================================================================
# 💥 Hooks that raise
# =========================================================================
class TestRaisingHooks(unittest.TestCase):
    def test_raising_entry_hook_is_contained_and_reported(self):
        """Invariant: a convention hook that raises is an ACTION error --
        logged, the transition still completes, the receipt carries it,
        the machine keeps running (AGENTS.md error semantics)."""

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_enter_b(self):
                raise RuntimeError("kaboom")

        with M() as sm:
            with self.assertLogs("xstate_statemachine", "ERROR"):
                receipt = sm.interpreter.send("GO", wait=True)
            self.assertIsInstance(receipt.error, RuntimeError)
            self.assertEqual(sm.state, "b")
            self.assertEqual(sm.status, "running")

    def test_raising_before_hook_does_not_block_the_transition(self):
        """Invariant: `before_<event>` runs from a plugin hook; a raise
        there is contained by the plugin machinery and the event is still
        processed."""

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def before_go(self):
                raise ValueError("pre-flight failed")

        with M() as sm:
            with self.assertLogs("xstate_statemachine", "ERROR"):
                sm.go()
            self.assertEqual(sm.state, "b")

    def test_guard_raising_is_false_and_strict_refuses(self):
        """Invariant: a raising guard counts as False; under `strict` that
        surfaces as TransitionNotAllowedError without dispatch."""

        class M(StateMachine):
            strict = True
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="broken")

            @guard
            def broken(self):
                raise KeyError("missing")

        with M() as sm:
            with self.assertLogs("xstate_statemachine", "ERROR"):
                with self.assertRaises(TransitionNotAllowedError):
                    sm.go()
            self.assertEqual(sm.state, "a")


# =========================================================================
# 🌳 Deep nesting, history and timers
# =========================================================================
class TestDeepNesting(unittest.TestCase):
    def test_five_levels_with_history_and_simulated_timer(self):
        """Invariant: transitions declared at every nesting level compile,
        history restores the deepest leaf, and `after` timers on nested
        states fire under a SimulatedClock driven through the façade."""

        class Deep(StateMachine):
            off = State(initial=True)

            class on(State.Compound):
                class l2(State.Compound, initial=True):
                    class l3(State.Compound, initial=True):
                        class l4(State.Compound, initial=True):
                            a = State(initial=True)
                            b = State(after={500: "c"})
                            c = State()
                            step = a.to(b)

                resume = State(history="deep")

            power = off.to(on) | on.to(off)
            back = off.to(on.resume)

        clock = SimulatedClock()
        with Deep(clock=clock) as sm:
            sm.power()
            self.assertEqual(sm.state, "on.l2.l3.l4.a")
            sm.step()
            self.assertEqual(sm.state, "on.l2.l3.l4.b")
            clock.increment(499)
            self.assertEqual(sm.state, "on.l2.l3.l4.b")
            clock.increment(1)
            self.assertEqual(sm.state, "on.l2.l3.l4.c")
            sm.power()  # off
            self.assertEqual(sm.state, "off")
            sm.back()  # deep history -> c
            self.assertEqual(sm.state, "on.l2.l3.l4.c")
            self.assertTrue(sm.on.is_active)
            self.assertFalse(sm.off.is_active)

    def test_same_leaf_names_at_every_level_stay_distinct(self):
        """Invariant: transitions are keyed by the source's PATH; four
        states all called `idle` with a `start` transition each route to
        their own sibling."""

        class G(StateMachine):
            class a(State.Compound, initial=True):
                idle = State(initial=True)
                work = State()
                kick = idle.to(work)

            class b(State.Compound):
                idle = State(initial=True)
                work = State()
                kick = idle.to(work)

                class deeper(State.Compound):
                    idle = State(initial=True)
                    work = State()
                    kick = idle.to(work)

            jump = a.to(b)
            dive = b.to(b.deeper)

        with G() as sm:
            sm.jump()
            sm.send("KICK")
            self.assertEqual(sm.state, "b.work")
            sm.dive()
            self.assertEqual(sm.state, "b.deeper.idle")
            sm.send("KICK")
            self.assertEqual(sm.state, "b.deeper.work")


# =========================================================================
# 💾 Snapshots and restore
# =========================================================================
class TestSnapshotRoundTrip(unittest.TestCase):
    def _order(self):
        class Order(StateMachine):
            initial_context = {"paid": False}
            created = State(initial=True)

            class paid(State.Compound):
                packing = State(initial=True)
                shipped = State(final=True)
                ship = packing.to(shipped)

            closed = State(final=True)
            pay = created.to(paid)
            close = paid.to(closed)

            def on_pay(self, context):
                context["paid"] = True

            def on_enter_shipped(self, context):
                context["shipped_at"] = "now"

        return Order

    def test_facade_snapshot_restores_on_a_bare_interpreter(self):
        """Invariant: a façade-built machine's snapshot restores onto
        `SyncInterpreter.from_snapshot(..., Cls.create_machine())`, and the
        convention-bound entry actions keep running after the restore."""
        Order = self._order()
        with Order() as sm:
            sm.pay()
            blob = sm.interpreter.get_snapshot()
        restored = SyncInterpreter.from_snapshot(
            blob, Order.create_machine()
        ).start()
        self.assertEqual(restored.current_state_ids, {"Order.paid.packing"})
        self.assertTrue(restored.context["paid"])
        restored.send("SHIP")
        self.assertEqual(restored.context["shipped_at"], "now")
        restored.stop()

    def test_from_state_then_snapshot_then_restore_is_stable(self):
        """Invariant: `Cls(state=...)` → snapshot → restore → same leaves."""
        Order = self._order()
        with Order(state="paid.packing") as sm:
            blob = sm.interpreter.get_snapshot()
        data = json.loads(blob)
        self.assertEqual(data["state_ids"], ["Order.paid.packing"])
        with Order(state="paid.packing") as again:
            again.ship()
            self.assertEqual(again.state, "paid.shipped")

    def test_to_json_round_trips_through_create_machine(self):
        """Invariant: `to_json()` is the chart the machine was built from;
        reloading it with stub logic gives an equivalent machine."""
        Order = self._order()
        chart = json.loads(Order.create_machine().to_json())
        m = create_machine(chart, logic=stub_logic(chart))
        i = SyncInterpreter(m).start()
        i.send("PAY")
        i.send("SHIP")
        self.assertEqual(i.current_state_ids, {"Order.paid.shipped"})
        i.stop()


# =========================================================================
# 🧬 Inheritance
# =========================================================================
class TestInheritance(unittest.TestCase):
    def test_three_level_chain_overrides_and_extends(self):
        """Invariant: a subclass inherits the base chart and hooks, may
        override a hook by name, and may add states and transitions that
        target inherited ones."""
        log = []

        class Base(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_enter_b(self):
                log.append("base")

        class Mid(Base):
            def on_enter_b(self):
                log.append("mid")

        class Leaf(Mid):
            c = State()
            more = Base.b.to(c)

        with Leaf() as sm:
            sm.go()
            sm.more()
            self.assertEqual(sm.state, "c")
            self.assertEqual(log, ["mid"])
            self.assertEqual(
                set(Leaf.create_machine().states), {"a", "b", "c"}
            )

    def test_base_class_machine_is_untouched_by_subclass(self):
        """Invariant: defining a subclass does not change the base's
        chart (no shared-object mutation)."""

        class Base(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

        before = Base.create_machine().to_json()

        class Child(Base):
            c = State()
            extra = Base.b.to(c)

            def on_enter_b(self):
                pass

        self.assertEqual(Base.create_machine().to_json(), before)
        self.assertNotIn("extra", before.lower())


# =========================================================================
# 💉 Every callback shape
# =========================================================================
class TestCallbackShapes(unittest.TestCase):
    def test_all_signature_shapes_coexist(self):
        """Invariant: legacy positional, injected, keyword-only, defaults,
        `*args`, `**kwargs` and chart-param callbacks all run correctly in
        one machine."""
        seen = {}

        class M(StateMachine):
            initial_context = {"n": 0}
            a = State(initial=True)
            b = State()
            go = a.to(
                b,
                guard="ok",
                actions=[
                    "legacy",
                    "injected",
                    "kw_only",
                    "defaults",
                    "star_args",
                    "star_kwargs",
                    {"type": "with_params", "params": {"limit": 7}},
                ],
            )

            @guard
            def ok(self, context, event, params):
                seen["guard_params"] = params
                return True

            @action
            def legacy(self, i, ctx, e, a):
                seen["legacy"] = (type(ctx).__name__, e.type, a.type)

            @action
            def injected(self, context, amount):
                seen["injected"] = (context["n"], amount)

            @action
            def kw_only(self, *, event, amount):
                seen["kw_only"] = (event.type, amount)

            @action
            def defaults(self, amount, note="n/a"):
                seen["defaults"] = (amount, note)

            @action
            def star_args(self, *args):
                seen["star_args"] = len(args)

            @action
            def star_kwargs(self, **kwargs):
                seen["star_kwargs"] = kwargs

            @action
            def with_params(self, limit, amount):
                seen["with_params"] = (limit, amount)

        with M() as sm:
            sm.go(amount=3, limit=99)  # payload `limit` must NOT win
        self.assertIsNone(seen["guard_params"])
        self.assertEqual(seen["legacy"], ("dict", "GO", "legacy"))
        self.assertEqual(seen["injected"], (0, 3))
        self.assertEqual(seen["kw_only"], ("GO", 3))
        self.assertEqual(seen["defaults"], (3, "n/a"))
        self.assertEqual(seen["star_args"], 4)
        self.assertEqual(seen["star_kwargs"], {"amount": 3, "limit": 99})
        self.assertEqual(seen["with_params"], (7, 3))

    def test_functional_api_gets_injection_too(self):
        """Invariant: `build_machine` callbacks may use injection."""
        seen = {}
        a = State("a", initial=True)
        b = State("b")

        def record(amount, context):
            seen["amount"], seen["ctx"] = amount, context

        m = build_machine(
            id="f",
            states=[a, b],
            transitions=[a.to(b, event="GO", actions=["record"])],
            actions=[record],
            context={"x": 1},
        )
        i = SyncInterpreter(m).start()
        i.send("GO", amount=5)
        self.assertEqual(seen, {"amount": 5, "ctx": {"x": 1}})
        i.stop()

    def test_missing_injected_argument_is_a_loud_action_error(self):
        """Invariant: a typo'd parameter name fails at the call with a
        message naming the callback and the parameter, not a silent skip."""

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["act"])

            @action
            def act(self, amout):  # typo
                pass

        with M() as sm:
            with self.assertLogs("xstate_statemachine", "ERROR") as cm:
                receipt = sm.interpreter.send("GO", amount=1, wait=True)
            self.assertIsInstance(receipt.error, TypeError)
            self.assertIn("amout", str(receipt.error))
            self.assertIn("act", str(receipt.error))
            self.assertTrue(any("amout" in line for line in cm.output))


# =========================================================================
# 📏 Scale and bounds
# =========================================================================
class TestScale(unittest.TestCase):
    def test_two_hundred_state_machine_builds_and_runs(self):
        """Invariant: a large class body compiles once (cached) and
        instantiation stays cheap; a chain of 200 transitions runs."""
        n = 200
        ns = {}
        states = [State(f"s{i}", initial=(i == 0)) for i in range(n)]
        for i, s in enumerate(states):
            ns[f"s{i}"] = s
        for i in range(n - 1):
            ns[f"step{i}"] = states[i].to(states[i + 1], event="NEXT")
        Big = type("Big", (StateMachine,), ns)

        t0 = time.perf_counter()
        first = Big()
        t_first = time.perf_counter() - t0
        t0 = time.perf_counter()
        second = Big()
        t_second = time.perf_counter() - t0
        self.assertIsNotNone(Big._xsm_config_cache)
        # 📊 the second build reuses the compiled config; it must not be
        #    slower than the first by more than noise.
        self.assertLess(t_second, max(t_first * 1.5, 0.05))
        for _ in range(n - 1):
            first.send("NEXT")
        self.assertEqual(first.state, f"s{n - 1}")
        first.stop()
        second.stop()

    def test_result_sink_is_bounded(self):
        """Invariant: sends made directly on `sm.interpreter` feed the
        result sink but can never grow it past RESULT_SINK_MAXLEN."""

        class M(StateMachine):
            a = State(initial=True)
            tick = a.internal(actions=["val"])

            @action
            def val(self):
                return 1

        with M() as sm:
            for _ in range(RESULT_SINK_MAXLEN * 3):
                sm.interpreter.send("TICK")
            self.assertLessEqual(len(sm._xsm_results), RESULT_SINK_MAXLEN)
            # the next façade send still folds only ITS result
            self.assertEqual(sm.tick(), 1)


# =========================================================================
# 🚦 Lifecycle misuse
# =========================================================================
class TestLifecycleMisuse(unittest.TestCase):
    def test_wrong_context_manager_for_engine_is_a_type_error(self):
        class S(StateMachine):
            a = State(initial=True)

        class A(StateMachine):
            engine = "async"
            a = State(initial=True)

        sm = S()
        with self.assertRaises(TypeError):
            asyncio.run(sm.__aenter__())
        sm.stop()

        async def main():
            am = A()
            with self.assertRaises(TypeError):
                am.__enter__()
            await am.stop()

        asyncio.run(main())

    def test_send_after_stop_is_dropped_not_crashed(self):
        """Invariant: a send to a stopped façade is a logged drop (lenient)
        or a strict refusal, never an exception from engine internals."""

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

        sm = M()
        sm.stop()
        sm.stop()  # idempotent
        with self.assertLogs("xstate_statemachine", "WARNING"):
            self.assertIsNone(sm.go())
        from xstate_statemachine import InterpreterStoppedError

        strict = M(strict=True)
        strict.stop()
        with self.assertRaises(InterpreterStoppedError):
            strict.go()

    def test_bad_engine_value_is_rejected(self):
        class M(StateMachine):
            a = State(initial=True)

        with self.assertRaises(InvalidConfigError):
            M(engine="threads")

    def test_create_machine_path_runs_compiled_hooks_only(self):
        """Invariant: on a bare interpreter the compiled conventions
        (entry/exit/on_<event>) run; before_/after_ do not, and
        create_machine() said so."""
        log = []

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_enter_b(self):
                log.append("enter")

            def on_go(self):
                log.append("on")

            def before_go(self):
                log.append("before")

            def after_go(self):
                log.append("after")

        with self.assertLogs("xstate_statemachine.pythonic", "WARNING") as cm:
            m = M.create_machine()
        self.assertTrue(any("before_go" in line for line in cm.output))
        i = SyncInterpreter(m).start()
        i.send("GO")
        i.stop()
        self.assertEqual(log, ["on", "enter"])


# =========================================================================
# 🔌 Plugins and the façade
# =========================================================================
class TestPluginsWithFacade(unittest.TestCase):
    def test_user_plugin_sees_facade_events_and_transitions(self):
        """Invariant: plugins passed to the façade observe the same
        lifecycle as on a bare interpreter."""
        events = []

        class Spy(PluginBase):
            def on_event_received(self, interpreter, event):
                events.append(("event", event.type))

            def on_transition(self, interp, from_states, to_states, t):
                events.append(("transition", sorted(s.id for s in to_states)))

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

        with M(plugins=[Spy()]) as sm:
            sm.go()
        self.assertIn(("event", "GO"), events)
        self.assertTrue(
            any(kind == "transition" and "M.b" in ids for kind, ids in events)
        )

    def test_validation_lists_every_missing_name_once(self):
        """Invariant: one error names all missing guards, actions and
        services, each once, so a user fixes them in one pass."""

        class M(StateMachine):
            a = State(initial=True, entry=["boot"], invoke={"src": "svc"})
            b = State(entry="boot")
            go = a.to(b, guard="g1", actions=["act", "act"])

        with self.assertRaises(ImplementationMissingError) as cm:
            M()
        msg = str(cm.exception)
        for name in (
            "action 'act'",
            "action 'boot'",
            "guard 'g1'",
            "service 'svc'",
        ):
            self.assertEqual(msg.count(name), 1, name)


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
