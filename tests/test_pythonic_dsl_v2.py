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
    event_payload,
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

    def test_start_and_stop_transitions_keep_lifecycle_methods(self):
        with self.assertLogs("xstate_statemachine.pythonic", "WARNING") as cm:

            class Timer(StateMachine):
                idle = State(initial=True)
                running = State()
                start = idle.to(running)
                stop = running.to(idle)

        self.assertTrue(any("Timer.stop" in m for m in cm.output))
        self.assertTrue(any("sm.send('STOP')" in m for m in cm.output))

        t = Timer()
        self.assertIn("START", t.machine.known_events)  # the chart has it
        t.send("START")  # the event is sent explicitly
        self.assertEqual(t.state, "running")
        t.send("STOP")
        self.assertEqual(t.state, "idle")
        t.stop()  # the lifecycle method, not the event
        self.assertEqual(t.status, "stopped")
        self.assertIs(Timer.stop, StateMachine.stop)

    def test_nested_stop_transition_does_not_shadow_lifecycle(self):
        class Player(StateMachine):
            idle = State(initial=True)

            class playing(State):
                loud = State(initial=True)
                stop = loud.to("idle")

            play = idle.to(playing)

        self.assertIs(Player.stop, StateMachine.stop)

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
        sm.send("START")  # `start` is the lifecycle method, not sugar
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
# 8c. Services see the triggering event; @state.service decorator
# =========================================================================
class TestServiceInput(unittest.TestCase):
    def test_no_declared_input_means_no_input_like_xstate(self):
        """XState passes an invoked actor nothing unless `input` is declared
        (verified against xstate 5.33.3); the triggering payload is NOT
        forwarded implicitly, so a Stately export behaves the same here."""
        seen = {}

        class Fetch(StateMachine):
            idle = State(initial=True)
            loading = State(invoke={"src": "fetchUrl", "onDone": "done"})
            done = State()
            start = idle.to(loading)

            @service
            def fetch_url(self, interpreter, context, event):
                seen["input"] = event.payload["input"]
                return "ok"

        with Fetch() as sm:
            sm.send("START", url="http://x", retries=2)
            self.assertEqual(seen["input"], {})
            self.assertEqual(sm.state, "done")

    def test_service_receives_triggering_payload_as_input(self):
        seen = {}

        class Fetch(StateMachine):
            idle = State(initial=True)
            loading = State(
                invoke={
                    "src": "fetchUrl",
                    "input": event_payload,
                    "onDone": "done",
                },
            )
            done = State()
            start = idle.to(loading)

            @service
            def fetch_url(self, interpreter, context, event):
                seen["input"] = event.payload["input"]
                return "ok"

        with Fetch() as sm:
            sm.send("START", url="http://x", retries=2)
            self.assertEqual(seen["input"], {"url": "http://x", "retries": 2})
            self.assertEqual(sm.state, "done")

    def test_service_injection_reads_payload_fields_by_name(self):
        seen = {}

        class Fetch(StateMachine):
            idle = State(initial=True)
            loading = State(
                invoke={
                    "src": "fetchUrl",
                    "input": event_payload,
                    "onDone": "done",
                }
            )
            done = State()
            start = idle.to(loading)

            @service
            def fetch_url(self, url, retries=0):
                seen.update(url=url, retries=retries)
                return url.upper()

        with Fetch() as sm:
            sm.send("START", url="x")
            self.assertEqual(seen, {"url": "x", "retries": 0})

    def test_declared_input_wins_and_factory_sees_the_event(self):
        seen = {}

        class M(StateMachine):
            idle = State(initial=True)
            working = State(
                invoke={
                    "src": "work",
                    "input": lambda ctx, ev: {"n": ev.payload["n"] * 2},
                    "onDone": "done",
                }
            )
            done = State()
            go = idle.to(working)

            @service
            def work(self, interpreter, context, event):
                seen["input"] = event.payload["input"]

        with M() as sm:
            sm.go(n=21)
            self.assertEqual(seen["input"], {"n": 42})

    def test_no_payload_means_empty_input(self):
        seen = {}

        class M(StateMachine):
            idle = State(initial=True)
            working = State(invoke={"src": "work", "onDone": "done"})
            done = State()
            go = idle.to(working)

            @service
            def work(self, interpreter, context, event):
                seen["input"] = event.payload["input"]

        with M() as sm:
            sm.go()
            self.assertEqual(seen["input"], {})

    def test_state_service_decorator_wires_invoke(self):
        class Fetch(StateMachine):
            idle = State(initial=True)
            loading = State()
            done = State()
            failed = State()
            start = idle.to(loading)

            @loading.service(
                input=event_payload, on_done="done", on_error="failed"
            )
            def fetch_url(self, url):
                if url == "bad":
                    raise ValueError("bad url")
                return url.upper()

            def on_enter_done(self, event):
                self.result = event.data

        cfg = Fetch.create_machine().source_config
        inv = cfg["states"]["loading"]["invoke"]
        self.assertEqual(inv["src"], "fetchUrl")
        self.assertEqual(inv["onDone"], {"target": "done"})
        self.assertEqual(inv["onError"], {"target": "failed"})

        with Fetch() as sm:
            sm.send("START", url="x")
            self.assertEqual(sm.state, "done")
            self.assertEqual(sm.result, "X")
        with Fetch() as sm:
            sm.send("START", url="bad")
            self.assertEqual(sm.state, "failed")

    def test_state_service_decorator_async(self):
        class Fetch(StateMachine):
            idle = State(initial=True)
            loading = State()
            done = State()
            start = idle.to(loading)

            @loading.service(input=event_payload, on_done="done")
            async def fetch_url(self, url):
                await asyncio.sleep(0)
                return url.upper()

        async def main():
            async with Fetch() as sm:
                await sm.send("START", url="x")
                await sm.interpreter.await_settled(1.0)
                self.assertEqual(sm.state, "done")

        asyncio.run(main())

    def test_state_service_outside_statemachine_is_rejected(self):
        loading = State("loading")

        @loading.service(on_done="done")
        def fetch(self):
            pass

        with self.assertRaises(InvalidConfigError):
            build_machine(id="m", states=[loading], services=[fetch])


# =========================================================================
# 8d. Restoring at a given state
# =========================================================================
class TestFromState(unittest.TestCase):
    def _flow(self):
        class Flow(StateMachine):
            initial_context = {"n": 1}
            draft = State(initial=True)

            class review(State.Compound):
                reading = State(initial=True)
                voting = State()
                vote = reading.to(voting)

            published = State(final=True)
            submit = draft.to(review)
            approve = review.to(published)

            def __init__(self, *a, **kw):
                self.entered = []
                super().__init__(*a, **kw)

            def on_enter_state(self, state):
                self.entered.append(state)

        return Flow

    def test_facade_starts_in_the_given_state_without_entry_actions(self):
        Flow = self._flow()
        with Flow(state="review") as sm:
            self.assertEqual(sm.state, "review.reading")  # initial leaf
            self.assertEqual(sm.entered, [])  # no entry actions ran
            self.assertEqual(sm.context, {"n": 1})  # defaults kept
            sm.approve()
            self.assertEqual(sm.state, "published")
            self.assertEqual(sm.entered, ["published"])

    def test_facade_state_with_context_and_leaf_path(self):
        Flow = self._flow()
        with Flow(state="review.voting", context={"k": 2}) as sm:
            self.assertEqual(sm.state, "review.voting")
            # `context=` replaces initial_context, as create_machine does
            self.assertEqual(sm.context, {"k": 2})

    def test_unknown_state_is_loud(self):
        from xstate_statemachine import StateNotFoundError

        Flow = self._flow()
        with self.assertRaises(StateNotFoundError):
            Flow(state="nowhere")

    def test_interpreter_from_state_sync_and_async(self):
        Flow = self._flow()
        m = Flow.create_machine()
        i = SyncInterpreter.from_state(m, "review").start()
        self.assertEqual(i.current_state_ids, {"Flow.review.reading"})
        i.send("VOTE")
        self.assertEqual(i.current_state_ids, {"Flow.review.voting"})
        i.stop()

        from xstate_statemachine import Interpreter

        async def main():
            a = await Interpreter.from_state(m, "Flow.published").start()
            self.assertEqual(a.current_state_ids, {"Flow.published"})
            self.assertEqual(a.status, "done")
            await a.stop()

        asyncio.run(main())

    def test_parallel_regions_from_state(self):
        class P(StateMachine):
            class root(State.Parallel, initial=True):
                class x(State.Compound):
                    a = State(initial=True)
                    b = State()
                    nxt = a.to(b)

                class y(State.Compound):
                    c = State(initial=True)
                    d = State()

        with P(state=["root.x.b", "root.y.c"]) as sm:
            self.assertEqual(
                sm.configuration, frozenset({"root.x.b", "root.y.c"})
            )
        with P(state="root") as sm:
            self.assertEqual(
                sm.configuration, frozenset({"root.x.a", "root.y.c"})
            )

    def test_strict_still_applies_after_restore(self):
        from xstate_statemachine import InterpreterStoppedError

        Flow = self._flow()
        with Flow(state="review", strict=True) as sm:
            with self.assertRaises(TransitionNotAllowedError):
                sm.submit()  # not enabled in review
        with Flow(state="published", strict=True) as sm:
            self.assertEqual(sm.status, "done")
            with self.assertRaises(InterpreterStoppedError):
                sm.approve()  # the machine has finished


# =========================================================================
# 8e. Injection and DSL corners
# =========================================================================
class TestInjectionCorners(unittest.TestCase):
    def test_every_engine_name_resolves(self):
        seen = {}

        class M(StateMachine):
            a = State(initial=True)
            b = State(
                invoke={
                    "src": "svc",
                    "input": event_payload,
                    "onDone": "c",
                    "onError": "d",
                }
            )
            c = State()
            d = State()
            go = a.to(b, actions=[{"type": "act", "params": {"limit": 3}}])

            @action
            def act(self, event_type, action, params, interp):
                seen["event_type"] = event_type
                seen["action_type"] = action.type
                seen["params"] = params
                seen["interp"] = interp is not None

            @service
            def svc(self, input, data, error):
                seen["input"] = input
                seen["data_error"] = (data, error)
                raise RuntimeError("boom")

            def on_enter_d(self, error, data):
                seen["enter_d"] = (type(error).__name__, data)

        with M() as sm:
            with self.assertLogs("xstate_statemachine", "ERROR"):
                sm.go(x=1)
            self.assertEqual(sm.state, "d")
        self.assertEqual(seen["event_type"], "GO")
        self.assertEqual(seen["action_type"], "act")
        self.assertEqual(seen["params"], {"limit": 3})
        self.assertTrue(seen["interp"])
        self.assertEqual(seen["input"], {"x": 1})
        # `data` on a plain Event is its payload (compat alias); `error` None
        self.assertEqual(seen["data_error"], ({"input": {"x": 1}}, None))
        self.assertEqual(seen["enter_d"], ("RuntimeError", None))

    def test_is_legacy_signature_helper(self):
        from xstate_statemachine._pythonic_runtime import (
            is_legacy_signature,
        )

        self.assertTrue(is_legacy_signature(lambda i, c, e, a: None, "action"))
        self.assertTrue(is_legacy_signature(lambda c, e: None, "guard"))
        self.assertTrue(is_legacy_signature(lambda *a: None, "service"))
        self.assertFalse(is_legacy_signature(lambda amount: None, "action"))
        self.assertFalse(
            is_legacy_signature(lambda context, event, x, y: None, "action")
        )

    def test_async_legacy_action_with_result_sink(self):
        class M(StateMachine):
            engine = "async"
            a = State(initial=True)
            go = a.internal(actions=["act"])

            @action
            async def act(self, i, ctx, e, a):
                return "legacy-async"

        async def main():
            async with M() as sm:
                self.assertEqual(await sm.go(), "legacy-async")

        asyncio.run(main())

    def test_event_sender_errors_and_reprs(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            c = State()
            mixed = a.to(b, event="X") | b.to(c, event="Y")
            back = c.to(a)

        with M() as sm:
            with self.assertRaises(TypeError):
                sm.mixed()  # two different events: ambiguous
            self.assertIn("event sender", repr(sm.mixed))
            self.assertEqual(repr(sm.a), "BoundState('a', active)")
            self.assertEqual(sm.a.id, "M.a")
            self.assertIs(sm.a.definition, M.a)
            with self.assertRaises(AttributeError):
                sm.a.__deepcopy__  # dunder probes are not delegated
        self.assertIn("Transition(", repr(M.back))
        self.assertIn("transitions", repr(M.mixed))
        self.assertEqual(M.mixed.event_types, {"X", "Y"})
        self.assertEqual(M.back.event_types, set())  # inferred, not stored

    def test_group_composition_orders(self):
        a, b, c, d = (State(n) for n in "abcd")
        a.initial = True
        t1, t2, t3 = a.to(b, event="E"), b.to(c, event="E"), c.to(d, event="E")
        g1 = t1 | t2
        self.assertEqual(len((g1 | t3).transitions), 3)
        self.assertEqual(len((t3 | g1).transitions), 3)
        self.assertEqual(len((g1 | (t3 | t3)).transitions), 4)

    def test_nested_class_internal_and_class_level_access(self):
        class M(StateMachine):
            class a(State, initial=True, final=False):
                x = State(initial=True)

            b = State()
            poke = a.internal(actions=["note"])
            go = a.to(b)

            @action
            def note(self):
                self.poked = True

        self.assertIs(M.a, M.a)  # class access gives the class back
        with M() as sm:
            sm.poke()
            self.assertTrue(sm.poked)
            self.assertEqual(sm.state, "a.x")

    def test_bad_nested_keyword_and_history_on_done_dict(self):
        with self.assertRaises(InvalidConfigError):

            class Bad(State, bogus=1):
                pass

        class M(StateMachine):
            class p(State, initial=True, on_done={"target": "q"}):
                x = State(initial=True, final=True)

            q = State(final=True)

        with M() as sm:
            self.assertEqual(sm.status, "done")

    def test_state_service_appends_to_existing_invokes(self):
        class M(StateMachine):
            idle = State(initial=True)
            busy = State(invoke={"src": "first"})
            go = idle.to(busy)

            @service
            def first(self):
                return 1

            @busy.service(id="second-id", input={"k": 1})
            def second(self, input):
                return input["k"]

        inv = M.create_machine().source_config["states"]["busy"]["invoke"]
        self.assertEqual([i["src"] for i in inv], ["first", "second"])
        self.assertEqual(inv[1]["id"], "second-id")

        class N(StateMachine):
            idle = State(initial=True)
            busy = State()
            go = idle.to(busy)

            @busy.service
            def one(self):
                return 1

            @busy.service
            def two(self):
                return 2

        inv2 = N.create_machine().source_config["states"]["busy"]["invoke"]
        self.assertEqual([i["src"] for i in inv2], ["one", "two"])

    def test_machine_root_with_facade(self):
        class M(StateMachine):
            machine_root = State("", on={"RESET": "a"}, always=None)
            a = State(initial=True)
            b = State()
            go = a.to(b)

        with M() as sm:
            sm.go()
            sm.send("RESET")
            self.assertEqual(sm.state, "a")

    def test_unresolvable_nested_reference_is_loud(self):
        class Other(State):
            x = State(initial=True)

        with self.assertRaises(InvalidConfigError):

            class M(StateMachine):
                a = State(initial=True)
                go = a.to(Other)


# =========================================================================
# 8f. Plain methods satisfy string references by name
# =========================================================================
class TestPlainMethodBinding(unittest.TestCase):
    def test_plain_methods_are_bound_as_guard_action_and_service(self):
        seen = []

        class Shop(StateMachine):
            initial_context = {"stock": 1}
            browsing = State(initial=True)
            paying = State(invoke={"src": "charge_card", "onDone": "done"})
            done = State()
            checkout = browsing.to(
                paying, guard="has_stock", actions=["reserve"]
            )

            def has_stock(self, context):  # snake_case reference
                return context["stock"] > 0

            def reserve(self, context, qty=1):
                context["stock"] -= qty
                seen.append("reserve")

            def charge_card(self, interpreter, context, event):
                seen.append("charge")
                return "receipt"

        with Shop() as sm:
            sm.checkout()
            self.assertEqual(sm.state, "done")
        self.assertEqual(seen, ["reserve", "charge"])

    def test_camel_case_reference_binds_snake_case_method(self):
        class M(StateMachine):
            a = State(initial=True, entry="say_hi")
            b = State()
            go = a.to(b, guard="isReady")

            def say_hi(self):
                self.greeted = True

            def is_ready(self):
                return True

        with M() as sm:
            self.assertTrue(sm.greeted)
            sm.go()
            self.assertEqual(sm.state, "b")

    def test_decorated_name_wins_over_plain_method(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["note"])

            @action("note")
            def decorated(self):
                self.which = "decorated"

            def note(self):
                self.which = "plain"

        with M() as sm:
            sm.go()
            self.assertEqual(sm.which, "decorated")

    def test_unreferenced_helper_methods_are_left_alone(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def helper(self):
                return "not a callback"

        with M() as sm:
            self.assertEqual(sm.helper(), "not a callback")
            self.assertNotIn("helper", sm.machine.logic.actions)
            sm.go()

    def test_missing_name_still_reported(self):
        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, guard="is_readyy")  # typo: no such method

            def is_ready(self):
                return True

        with self.assertRaises(ImplementationMissingError) as cm:
            M()
        self.assertIn("is_readyy", str(cm.exception))


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
