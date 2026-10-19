# tests/test_pythonic_dsl_v2.py
"""
🐍 Tests for the second-generation Pythonic DSL.

Covers event inference, nested-class statecharts, naming-convention
hooks, signature-based argument injection, the instance façade
(``sm = Machine()``), strict mode and definition-time logic validation.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import json
import logging
import unittest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine import (
    ImplementationMissingError,
    InvalidConfigError,
    SyncInterpreter,
    UnknownEventError,
)
from xstate_statemachine.exceptions import TransitionNotAllowedError
from xstate_statemachine.pythonic import (
    State,
    StateMachine,
    action,
    build_machine,
    guard,
    service,
)


# =========================================================================
# 1. Event inference
# =========================================================================
class TestEventInference(unittest.TestCase):
    def test_event_is_inferred_from_attribute_name(self):
        class Light(StateMachine):
            green = State(initial=True)
            yellow = State()
            red = State()
            cycle = green.to(yellow) | yellow.to(red) | red.to(green)

        m = Light.create_machine()
        self.assertIn("CYCLE", m.known_events)
        i = SyncInterpreter(m).start()
        i.send("CYCLE")
        self.assertEqual(i.current_state_ids, {"Light.yellow"})
        i.stop()

    def test_snake_case_attribute_becomes_screaming_snake_event(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            slow_down = a.to(b)

        self.assertIn("SLOW_DOWN", M.create_machine().known_events)

    def test_explicit_event_still_wins(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, event="GO_NOW")

        self.assertIn("GO_NOW", M.create_machine().known_events)
        self.assertNotIn("GO", M.create_machine().known_events)

    def test_functional_api_without_event_fails_at_build_time(self):
        a = State("a", initial=True)
        b = State("b")
        t = a.to(b)  # no error yet: the name may still be inferred
        with self.assertRaises(InvalidConfigError) as cm:
            build_machine(id="m", states=[a, b], transitions=[t])
        self.assertIn("event", str(cm.exception))


# =========================================================================
# 2. Nested classes
# =========================================================================
class TestNestedClasses(unittest.TestCase):
    def test_transitions_inside_nested_body_are_kept(self):
        class Order(StateMachine):
            created = State(initial=True)

            class paid(State):
                packing = State(initial=True)
                shipped = State(final=True)
                ship = packing.to(shipped)

            pay = created.to(paid)

        i = SyncInterpreter(Order.create_machine()).start()
        i.send("PAY")
        self.assertEqual(i.current_state_ids, {"Order.paid.packing"})
        i.send("SHIP")
        self.assertEqual(i.current_state_ids, {"Order.paid.shipped"})
        i.stop()

    def test_nested_class_is_a_valid_target_and_source(self):
        class M(StateMachine):
            a = State(initial=True)

            class b(State):
                x = State(initial=True)

            go = a.to(b)
            back = b.to(a)

        i = SyncInterpreter(M.create_machine()).start()
        i.send("GO")
        self.assertEqual(i.current_state_ids, {"M.b.x"})
        i.send("BACK")
        self.assertEqual(i.current_state_ids, {"M.a"})
        i.stop()

    def test_children_listed_in_states_do_not_leak_to_root(self):
        class M(StateMachine):
            packing = State(initial=True)
            shipped = State(final=True)
            created = State(initial=True)
            paid = State(states=[packing, shipped], on_done="closed")
            closed = State(final=True)
            pay = created.to(paid)
            ship = packing.to(shipped)

        m = M.create_machine()
        self.assertEqual(set(m.states), {"created", "paid", "closed"})
        i = SyncInterpreter(m).start()
        i.send("PAY")
        self.assertEqual(i.current_state_ids, {"M.paid.packing"})
        i.send("SHIP")
        self.assertEqual(i.current_state_ids, {"M.closed"})
        i.stop()

    def test_nested_class_accepts_state_keywords(self):
        class M(StateMachine):
            a = State(initial=True)

            class b(State, after={10: "c"}, tags=["busy"], meta={"k": 1}):
                x = State(initial=True)

            c = State(final=True)
            go = a.to(b)

        m = M.create_machine()
        b = m.get_state_by_id("M.b")
        self.assertIn("busy", b.tags)
        self.assertEqual(b.meta, {"k": 1})
        self.assertIn("after.10.M.b", m.known_events)

    def test_nested_class_on_done_and_entry(self):
        seen = []

        class M(StateMachine):
            a = State(initial=True)

            class b(State, on_done="c", entry=["note"]):
                x = State(initial=True)
                y = State(final=True)
                fin = x.to(y)

            c = State(final=True)
            go = a.to(b)

            @action
            def note(self, i, ctx, e, a):
                seen.append("note")

        i = SyncInterpreter(M.create_machine()).start()
        i.send("GO")
        self.assertEqual(seen, ["note"])
        i.send("FIN")
        self.assertEqual(i.current_state_ids, {"M.c"})
        i.stop()

    def test_compound_and_parallel_aliases(self):
        class M(StateMachine):
            a = State(initial=True)

            class fulfil(State.Parallel):
                class payment(State.Compound):
                    pending = State(initial=True)
                    settled = State(final=True)
                    settle = pending.to(settled)

                class notify(State.Compound):
                    idle = State(initial=True)
                    sent = State(final=True)
                    send_mail = idle.to(sent)

            go = a.to(fulfil)

        i = SyncInterpreter(M.create_machine()).start()
        i.send("GO")
        self.assertEqual(
            i.current_state_ids,
            {"M.fulfil.payment.pending", "M.fulfil.notify.idle"},
        )
        i.send("SETTLE")
        i.send("SEND_MAIL")
        self.assertEqual(
            i.current_state_ids,
            {"M.fulfil.payment.settled", "M.fulfil.notify.sent"},
        )
        i.stop()

    def test_history_in_nested_class(self):
        class M(StateMachine):
            class online(State, initial=True):
                a = State(initial=True)
                b = State()
                resume = State(history="shallow")
                nxt = a.to(b)

            offline = State()
            drop = online.to(offline)
            back = offline.to(online.resume)

        i = SyncInterpreter(M.create_machine()).start()
        i.send("NXT")
        i.send("DROP")
        i.send("BACK")
        self.assertEqual(i.current_state_ids, {"M.online.b"})
        i.stop()


# =========================================================================
# 3. Naming-convention hooks
# =========================================================================
class TestNamingConventionHooks(unittest.TestCase):
    def test_on_enter_and_on_exit_state_hooks(self):
        log = []

        class Light(StateMachine):
            green = State(initial=True)
            yellow = State()
            cycle = green.to(yellow)

            def on_enter_green(self):
                log.append("enter green")

            def on_exit_green(self):
                log.append("exit green")

            def on_enter_yellow(self):
                log.append("enter yellow")

        sm = Light()
        sm.cycle()
        self.assertEqual(log, ["enter green", "exit green", "enter yellow"])
        sm.stop()

    def test_on_event_hook_runs_between_exit_and_entry(self):
        log = []

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_exit_a(self):
                log.append("exit")

            def on_go(self):
                log.append("on_go")

            def on_enter_b(self):
                log.append("enter")

        sm = M()
        sm.go()
        self.assertEqual(log, ["exit", "on_go", "enter"])
        sm.stop()

    def test_generic_hooks(self):
        log = []

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_enter_state(self, state):
                log.append(f"enter:{state}")

            def on_exit_state(self, state):
                log.append(f"exit:{state}")

            def on_transition(self, event, source, target):
                log.append(f"{event.type}:{source}->{target}")

        sm = M()
        sm.go()
        self.assertEqual(log, ["enter:a", "exit:a", "GO:a->b", "enter:b"])
        sm.stop()

    def test_before_and_after_hooks(self):
        log = []

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def before_go(self, amount):
                log.append(f"before:{amount}")

            def after_go(self):
                log.append("after")

            def before_transition(self, event):
                log.append(f"before_any:{event.type}")

            def after_transition(self, event):
                log.append(f"after_any:{event.type}")

        sm = M()
        sm.go(amount=2)
        self.assertEqual(
            log, ["before_any:GO", "before:2", "after_any:GO", "after"]
        )
        sm.stop()

    def test_before_hook_does_not_run_for_blocked_event(self):
        log = []

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def before_go(self):
                log.append("before")

        sm = M()
        sm.send("NOPE")
        sm.go()
        sm.go()  # not allowed in b
        self.assertEqual(log, ["before"])
        sm.stop()

    def test_unmatched_on_enter_name_warns(self):
        with self.assertLogs("xstate_statemachine.pythonic", "WARNING") as cm:

            class M(StateMachine):
                green = State(initial=True)

                def on_enter_gren(self):  # typo
                    pass

        self.assertTrue(any("on_enter_gren" in m for m in cm.output))

    def test_decorated_method_is_not_treated_as_convention(self):
        log = []

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["on_enter_whatever"])

            @action
            def on_enter_whatever(self):
                log.append("explicit")

        sm = M()
        sm.go()
        self.assertEqual(log, ["explicit"])
        sm.stop()


# =========================================================================
# 4. Signature-based argument injection
# =========================================================================
class TestArgumentInjection(unittest.TestCase):
    def test_payload_kwargs_are_injected_by_name(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["record"])

            @action
            def record(self, amount, note="n/a"):
                seen["amount"] = amount
                seen["note"] = note

        sm = M()
        sm.go(amount=3)
        self.assertEqual(seen, {"amount": 3, "note": "n/a"})
        sm.stop()

    def test_context_event_and_interpreter_are_injectable(self):
        seen = {}

        class M(StateMachine):
            initial_context = {"n": 1}
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["record"])

            @action
            def record(self, context, event, interpreter):
                seen["n"] = context["n"]
                seen["type"] = event.type
                seen["interp"] = interpreter is not None

        sm = M()
        sm.go()
        self.assertEqual(seen, {"n": 1, "type": "GO", "interp": True})
        sm.stop()

    def test_legacy_four_argument_action_is_untouched(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["record"])

            @action
            def record(self, i, ctx, e, a):
                seen["args"] = (i is not None, ctx, e.type, a is not None)

        sm = M()
        sm.go()
        self.assertEqual(seen["args"], (True, {}, "GO", True))
        sm.stop()

    def test_guard_injection(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="allowed")

            @guard
            def allowed(self, amount=0):
                return amount > 5

        sm = M()
        sm.go(amount=1)
        self.assertEqual(sm.state, "a")
        sm.go(amount=9)
        self.assertEqual(sm.state, "b")
        sm.stop()

    def test_missing_required_argument_is_a_clear_error(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["record"])

            @action
            def record(self, amount):
                pass

        sm = M()
        receipt = sm.interpreter.send("GO", wait=True)
        self.assertIsInstance(receipt.error, TypeError)
        self.assertIn("amount", str(receipt.error))
        sm.stop()

    def test_var_keyword_receives_remaining_payload(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["record"])

            @action
            def record(self, amount, **rest):
                seen.update(amount=amount, rest=rest)

        sm = M()
        sm.go(amount=1, x=2, y=3)
        self.assertEqual(seen, {"amount": 1, "rest": {"x": 2, "y": 3}})
        sm.stop()

    def test_send_returns_callback_values(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)
            back = b.to(a)

            def on_go(self, amount):
                return f"counted {amount}"

            def on_back(self):
                return "one"

            def on_enter_a(self):
                return "two"

        sm = M()
        self.assertEqual(sm.go(amount=3), "counted 3")
        self.assertEqual(sm.back(), ["one", "two"])
        sm.stop()


# =========================================================================
# 5. The instance façade
# =========================================================================
class TestInstanceFacade(unittest.TestCase):
    def _light(self):
        class Light(StateMachine):
            green = State(initial=True)
            yellow = State()
            red = State()
            cycle = green.to(yellow) | yellow.to(red) | red.to(green)

            def __init__(self, *args, **kwargs):
                self.count = 0
                super().__init__(*args, **kwargs)

            def on_cycle(self):
                self.count += 1

        return Light

    def test_instance_runs_immediately(self):
        sm = self._light()()
        self.assertEqual(sm.state, "green")
        sm.send("CYCLE")
        self.assertEqual(sm.state, "yellow")
        sm.cycle()
        self.assertEqual(sm.state, "red")
        self.assertEqual(sm.count, 2)
        sm.stop()

    def test_bound_state_is_active(self):
        sm = self._light()()
        self.assertTrue(sm.green.is_active)
        self.assertFalse(sm.red.is_active)
        sm.cycle()
        self.assertTrue(sm.yellow.is_active)
        self.assertEqual(sm.yellow.name, "yellow")
        sm.stop()

    def test_class_level_state_access_is_unchanged(self):
        Light = self._light()
        self.assertIsInstance(Light.green, State)
        self.assertEqual(Light.green.name, "green")

    def test_configuration_and_matches(self):
        sm = self._light()()
        self.assertEqual(sm.configuration, frozenset({"green"}))
        self.assertTrue(sm.matches("green"))
        self.assertTrue(sm.can("CYCLE"))
        self.assertIn("CYCLE", sm.allowed_events)
        sm.stop()

    def test_context_and_override(self):
        class M(StateMachine):
            initial_context = {"n": 0}
            a = State(initial=True)

        sm = M()
        self.assertEqual(sm.context, {"n": 0})
        sm2 = M(context={"n": 5})
        self.assertEqual(sm2.context, {"n": 5})
        sm.stop()
        sm2.stop()

    def test_repr(self):
        sm = self._light()()
        self.assertEqual(repr(sm), "Light(state='green', context={})")
        sm.stop()

    def test_machine_and_interpreter_are_exposed(self):
        sm = self._light()()
        self.assertEqual(sm.machine.id, "Light")
        self.assertIsInstance(sm.interpreter, SyncInterpreter)
        sm.stop()

    def test_create_machine_still_works_and_does_not_start(self):
        Light = self._light()
        m = Light.create_machine()
        self.assertEqual(m.id, "Light")
        i = SyncInterpreter(m).start()
        i.send("CYCLE")
        self.assertEqual(i.current_state_ids, {"Light.yellow"})
        i.stop()

    def test_event_methods_reject_positional_arguments(self):
        sm = self._light()()
        with self.assertRaises(TypeError):
            sm.cycle(1)
        sm.stop()

    def test_state_raises_for_parallel_configuration(self):
        class M(StateMachine):
            class root(State.Parallel, initial=True):
                class x(State.Compound):
                    a = State(initial=True)

                class y(State.Compound):
                    b = State(initial=True)

        sm = M()
        with self.assertRaises(ValueError):
            sm.state
        self.assertEqual(sm.configuration, frozenset({"root.x.a", "root.y.b"}))
        sm.stop()

    def test_stop_and_status(self):
        sm = self._light()()
        self.assertEqual(sm.status, "running")
        sm.stop()
        self.assertEqual(sm.status, "stopped")

    def test_context_manager(self):
        with self._light()() as sm:
            sm.cycle()
            self.assertEqual(sm.state, "yellow")
        self.assertEqual(sm.status, "stopped")

    def test_transition_named_like_a_facade_method_is_rejected(self):
        with self.assertRaises(InvalidConfigError) as cm:

            class M(StateMachine):
                a = State(initial=True)
                b = State()
                send = a.to(b)

        self.assertIn("reserved", str(cm.exception))
        self.assertIn("send", str(cm.exception))

    def test_start_and_stop_may_be_event_names(self):
        class Timer(StateMachine):
            idle = State(initial=True)
            running = State()
            start = idle.to(running)
            stop = running.to(idle)

        with Timer() as t:
            t.start()  # sends START
            self.assertEqual(t.state, "running")
            t.stop()  # sends STOP
            self.assertEqual(t.state, "idle")
        self.assertEqual(t.status, "stopped")

    def test_string_entry_and_actions_are_single_actions(self):
        seen = []

        class M(StateMachine):
            a = State(initial=True, entry="boot")
            b = State()
            go = a.to(b, actions="note")

            @action
            def boot(self):
                seen.append("boot")

            @action
            def note(self):
                seen.append("note")

        sm = M()
        sm.go()
        self.assertEqual(seen, ["boot", "note"])
        sm.stop()

    def test_nested_transition_is_an_event_method_on_the_machine(self):
        class Order(StateMachine):
            created = State(initial=True)

            class paid(State):
                packing = State(initial=True)
                shipped = State(final=True)
                ship = packing.to(shipped)

            pay = created.to(paid)

        sm = Order()
        sm.pay()
        sm.ship()
        self.assertEqual(sm.state, "paid.shipped")
        sm.stop()


# =========================================================================
# 6. Async façade
# =========================================================================
class TestAsyncFacade(unittest.TestCase):
    def test_async_callback_selects_async_engine(self):
        class Fetch(StateMachine):
            idle = State(initial=True)
            done = State()
            fetch = idle.to(done)

            async def on_fetch(self, url):
                await asyncio.sleep(0)
                return url.upper()

        async def main():
            sm = Fetch()
            self.assertEqual(sm.engine, "async")
            await sm.start()
            result = await sm.fetch(url="x")
            self.assertEqual(result, "X")
            self.assertEqual(sm.state, "done")
            await sm.stop()

        asyncio.run(main())

    def test_explicit_async_engine_with_sync_callbacks(self):
        class M(StateMachine):
            engine = "async"
            a = State(initial=True)
            b = State()
            go = a.to(b)

        async def main():
            sm = M()
            await sm.start()
            await sm.go()
            self.assertEqual(sm.state, "b")
            await sm.stop()

        asyncio.run(main())

    def test_async_context_manager(self):
        class M(StateMachine):
            engine = "async"
            a = State(initial=True)
            b = State()
            go = a.to(b)

        async def main():
            async with M() as sm:
                await sm.go()
                self.assertEqual(sm.state, "b")
            self.assertEqual(sm.status, "stopped")

        asyncio.run(main())


# =========================================================================
# 7. Strict mode
# =========================================================================
class TestStrictMode(unittest.TestCase):
    def test_strict_rejects_undeclared_event(self):
        class M(StateMachine):
            strict = True
            a = State(initial=True)
            b = State()
            go = a.to(b)

        sm = M()
        with self.assertRaises(UnknownEventError):
            sm.send("GOO")
        sm.stop()

    def test_strict_rejects_declared_but_disabled_event(self):
        class M(StateMachine):
            strict = True
            a = State(initial=True)
            b = State()
            go = a.to(b)

        sm = M()
        sm.go()
        with self.assertRaises(TransitionNotAllowedError) as cm:
            sm.go()
        self.assertIn("GO", str(cm.exception))
        self.assertIn("b", str(cm.exception))
        self.assertEqual(sm.state, "b")
        sm.stop()

    def test_strict_rejects_guard_denied_event(self):
        class M(StateMachine):
            strict = True
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="never")

            @guard
            def never(self):
                return False

        sm = M()
        with self.assertRaises(TransitionNotAllowedError):
            sm.go()
        sm.stop()

    def test_lenient_default_ignores(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

        sm = M()
        sm.go()
        self.assertIsNone(sm.go())
        sm.stop()


# =========================================================================
# 8. Definition-time validation
# =========================================================================
class TestDefinitionTimeValidation(unittest.TestCase):
    def test_missing_logic_is_reported_at_create_machine(self):
        class M(StateMachine):
            a = State(initial=True, entry=["boot"])
            b = State(invoke={"src": "fetch"})
            go = a.to(b, guard="isReady", actions=["log", "save"])

        self.assertIsNotNone(M.create_machine())  # static artifact: fine
        with self.assertRaises(ImplementationMissingError) as cm:
            M.create_machine(validate=True)
        msg = str(cm.exception)
        for name in ("boot", "fetch", "isReady", "save"):
            self.assertIn(name, msg)
        self.assertNotIn("'log'", msg)  # built-in

    def test_missing_logic_is_reported_at_instantiation(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="isReady")

        with self.assertRaises(ImplementationMissingError):
            M()

    def test_validation_can_be_disabled(self):
        class M(StateMachine):
            validate_logic = False
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="isReady")

        sm = M()
        self.assertEqual(sm.state, "a")
        sm.stop()


# =========================================================================
# 8b. Review regressions
# =========================================================================
class TestReviewRegressions(unittest.TestCase):
    def test_parameterised_guard_with_three_arguments_still_works(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, guard={"type": "isBig", "params": {"n": 3}})

            @guard
            def is_big(self, context, event, params):
                return params["n"] > 2

        sm = M()
        sm.go()
        self.assertEqual(sm.state, "b")
        sm.stop()

    def test_guard_params_injectable_by_name(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, guard={"type": "isBig", "params": {"n": 3}})

            @guard
            def is_big(self, params):
                return params["n"] > 2

        sm = M()
        sm.go()
        self.assertEqual(sm.state, "b")
        sm.stop()

    def test_legacy_arity_guard_naming_a_payload_field_is_injected(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="can_pay")

            @guard
            def can_pay(self, context, amount):
                seen["amount"] = amount
                return amount > 1

        sm = M()
        sm.go(amount=5)
        self.assertEqual(seen["amount"], 5)
        self.assertEqual(sm.state, "b")
        sm.stop()

    def test_engine_name_at_wrong_position_means_injection(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["act"])

            @action
            def act(self, context, event, amount, note):
                seen.update(amount=amount, note=note, t=event.type)

        sm = M()
        sm.go(amount=1, note="x")
        self.assertEqual(seen, {"amount": 1, "note": "x", "t": "GO"})
        sm.stop()

    def test_keyword_only_and_defaults_mean_injection(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="g", actions=["act"])

            @guard
            def g(self, context, *, event):
                return event.type == "GO"

            @action
            def act(self, context, event, a=1, b=2):
                seen.update(a=a, b=b)

        sm = M()
        sm.go(b=7)
        self.assertEqual(seen, {"a": 1, "b": 7})
        sm.stop()

    def test_spawn_service_action_passes_validation(self):
        class Child(StateMachine):
            x = State(initial=True)

        class Parent(StateMachine):
            a = State(initial=True, entry=["spawn_child"])

            @service
            def child(self, interpreter, context, event):
                return Child.create_machine()

        m = Parent.create_machine(validate=True)
        self.assertIsNotNone(m)

    def test_same_named_states_under_different_parents_are_distinct(self):
        class G(StateMachine):
            class a(State, initial=True):
                idle = State(initial=True)
                work = State()
                start = idle.to(work)

            class b(State):
                idle = State(initial=True)
                work = State()
                start = idle.to(work)

            jump = a.to(b)

        cfg = G.create_machine().source_config
        self.assertEqual(
            cfg["states"]["a"]["states"]["idle"]["on"]["START"],
            {"target": "#G.a.work"},
        )
        self.assertEqual(
            cfg["states"]["b"]["states"]["idle"]["on"]["START"],
            {"target": "#G.b.work"},
        )
        sm = G()
        sm.jump()
        sm.start()
        self.assertEqual(sm.state, "b.work")
        sm.stop()

    def test_async_before_hook_is_rejected_at_class_creation(self):
        with self.assertRaises(InvalidConfigError):

            class M(StateMachine):
                a = State(initial=True)
                b = State()
                go = a.to(b)

                async def before_go(self):
                    pass

    def test_concurrent_async_sends_keep_their_results_apart(self):
        class M(StateMachine):
            engine = "async"
            a = State(initial=True)
            go = a.internal(actions=["r1"])
            nxt = a.internal(actions=["r2"])

            @action
            def r1(self):
                return "X"

            @action
            def r2(self):
                return "Y"

        async def main():
            async with M() as sm:
                results = await asyncio.gather(sm.go(), sm.nxt())
                self.assertEqual(results, ["X", "Y"])

        asyncio.run(main())

    def test_payload_cannot_shadow_context_or_chart_params(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_enter_state(self, state, context):
                seen.setdefault("states", []).append(state)
                seen["ctx_type"] = type(context).__name__

        sm = M()
        sm.go(state="CA", context="nope")
        self.assertEqual(seen["states"], ["a", "b"])
        self.assertEqual(seen["ctx_type"], "dict")
        sm.stop()

    def test_payload_key_named_event_is_allowed(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["act"])

            @action
            def act(self, event, **rest):
                seen["t"] = event.type
                seen["field"] = event.payload["event"]
                seen["rest"] = rest

        sm = M()
        sm.go(event="payload-value")
        self.assertEqual(
            seen, {"t": "GO", "field": "payload-value", "rest": {}}
        )
        sm.stop()

    def test_shared_state_objects_are_not_mutated_by_conventions(self):
        a = State("a", initial=True)
        b = State("b")

        class M1(StateMachine):
            s_a = a
            s_b = b
            go = a.to(b)

            def on_enter_b(self):
                pass

        class M2(StateMachine):
            s_a = a
            s_b = b
            go = a.to(b)

        self.assertEqual(a.entry, [])
        self.assertEqual(b.entry, [])
        m2 = M2()  # would raise ImplementationMissingError if mutated
        m2.go()
        self.assertEqual(m2.state, "b")
        m2.stop()

    def test_subclass_inherits_chart_and_hooks(self):
        log = []

        class Base(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_enter_b(self):
                log.append("base")

        class Child(Base):
            c = State()
            more = Base.b.to(c)

        sm = Child()
        sm.go()
        sm.more()
        self.assertEqual(sm.state, "c")
        self.assertEqual(log, ["base"])
        sm.stop()

    def test_generic_hooks_run_before_specific_regardless_of_order(self):
        log = []

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def on_enter_b(self):
                log.append("specific")

            def on_enter_state(self, state):
                log.append(f"generic:{state}")

        sm = M()
        sm.go()
        self.assertEqual(log, ["generic:a", "generic:b", "specific"])
        sm.stop()

    def test_nested_class_state_is_active(self):
        class M(StateMachine):
            a = State(initial=True)

            class b(State):
                x = State(initial=True)

            go = a.to(b)

        sm = M()
        self.assertFalse(sm.b.is_active)
        sm.go()
        self.assertTrue(sm.b.is_active)
        self.assertEqual(sm.b.path, "b")
        sm.stop()

    def test_strict_is_readable_on_the_instance(self):
        class M(StateMachine):
            a = State(initial=True)

        sm = M(strict=True)
        self.assertTrue(sm.strict)
        self.assertFalse(M.strict)
        sm.stop()


# =========================================================================
# 9. MachineNode.to_json
# =========================================================================
class TestToJson(unittest.TestCase):
    def test_to_json_round_trips(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

        m = M.create_machine()
        data = json.loads(m.to_json())
        self.assertEqual(data["id"], "M")
        self.assertEqual(data["states"]["a"]["on"]["GO"]["target"], "b")
        self.assertIn("\n", m.to_json(indent=2))


if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.WARNING)
    unittest.main()
