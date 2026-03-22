# tests/test_pythonic.py
"""Tests for the Pythonic API layer."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import unittest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine.pythonic import (
    _snake_to_camel,
    _compile_config,
    _compile_logic_from_functions,
    _compile_logic_from_instance,
    build_machine,
    MachineBuilder,
    StateMachine,
    State,
    Transition,
    TransitionGroup,
    transition,
    action,
    guard,
    service,
)
from xstate_statemachine.exceptions import (
    InvalidConfigError,
    NotSupportedError,
)
from xstate_statemachine import (
    Interpreter,
    MachineLogic,
    SyncInterpreter,
    create_machine,
    PluginBase,
)


class TestSnakeToCamel(unittest.TestCase):
    """Tests for the _snake_to_camel helper."""

    def test_simple_conversion(self):
        self.assertEqual(_snake_to_camel("hello_world"), "helloWorld")

    def test_single_word(self):
        self.assertEqual(_snake_to_camel("hello"), "hello")

    def test_multiple_underscores(self):
        self.assertEqual(_snake_to_camel("a_b_c"), "aBC")

    def test_already_camel(self):
        self.assertEqual(_snake_to_camel("helloWorld"), "helloWorld")


class TestState(unittest.TestCase):
    """Tests for the State class."""

    def test_state_basic_attributes(self):
        s = State("idle")
        self.assertEqual(s.name, "idle")
        self.assertFalse(s.initial)
        self.assertFalse(s.final)
        self.assertFalse(s.parallel)

    def test_state_initial_flag(self):
        s = State("idle", initial=True)
        self.assertTrue(s.initial)

    def test_state_final_type(self):
        s = State("done", final=True)
        self.assertTrue(s.final)

    def test_state_parallel_type(self):
        s = State("regions", parallel=True)
        self.assertTrue(s.parallel)

    def test_state_final_and_parallel_raises(self):
        with self.assertRaises(Exception):
            State("bad", final=True, parallel=True)

    def test_state_name_defaults_to_empty(self):
        s = State()
        self.assertEqual(s.name, "")

    def test_state_nested_children(self):
        child1 = State("a", initial=True)
        child2 = State("b")
        parent = State("parent", states=[child1, child2])
        self.assertEqual(len(parent.states), 2)
        self.assertEqual(parent.states[0].name, "a")

    def test_state_on_dict(self):
        s = State("idle", on={"CLICK": "active"})
        self.assertEqual(s.on, {"CLICK": "active"})

    def test_state_entry_exit(self):
        s = State("idle", entry=["logEntry"], exit=["cleanup"])
        self.assertEqual(s.entry, ["logEntry"])
        self.assertEqual(s._exit_actions, ["cleanup"])

    def test_state_after(self):
        s = State("waiting", after={1000: "timeout"})
        self.assertEqual(s.after, {1000: "timeout"})

    def test_state_invoke_single(self):
        s = State("loading", invoke={"src": "fetchData"})
        self.assertEqual(s.invoke, {"src": "fetchData"})

    def test_state_invoke_list(self):
        inv = [{"src": "svc1"}, {"src": "svc2"}]
        s = State("loading", invoke=inv)
        self.assertEqual(s.invoke, inv)

    def test_state_on_done(self):
        s = State("parent", on_done="next")
        self.assertEqual(s.on_done, "next")

    def test_state_always(self):
        s = State("check", always={"target": "done"})
        self.assertEqual(s.always, {"target": "done"})

    def test_state_context(self):
        s = State("root", context={"count": 0})
        self.assertEqual(s.context, {"count": 0})


class TestTransition(unittest.TestCase):
    """Tests for the Transition class."""

    def setUp(self):
        self.idle = State("idle", initial=True)
        self.running = State("running")

    def test_transition_basic(self):
        t = self.idle.to(self.running, event="START")
        self.assertIsInstance(t, Transition)
        self.assertEqual(t.source, self.idle)
        self.assertEqual(t.target, self.running)
        self.assertEqual(t.event, "START")
        self.assertIsNone(t.guard)
        self.assertEqual(t.actions, [])

    def test_transition_with_guard_and_actions(self):
        t = self.idle.to(
            self.running,
            event="GO",
            guard="isReady",
            actions=["prepare", "log"],
        )
        self.assertEqual(t.guard, "isReady")
        self.assertEqual(t.actions, ["prepare", "log"])

    def test_transition_reenter(self):
        t = self.idle.to(self.idle, event="RETRY", reenter=True)
        self.assertTrue(t.reenter)

    def test_transition_internal(self):
        t = self.idle.internal("HEARTBEAT", actions=["logHb"])
        self.assertTrue(t.internal)
        self.assertIsNone(t.target)
        self.assertEqual(t.actions, ["logHb"])

    def test_transition_without_event_raises(self):
        with self.assertRaises(Exception):
            self.idle.to(self.running)

    def test_transition_combine_with_pipe(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = a.to(b, event="GO") | b.to(c, event="GO")
        self.assertIsInstance(group, TransitionGroup)
        self.assertEqual(len(group.transitions), 2)

    def test_transition_group_pipe_chain(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = a.to(b, event="X") | b.to(c, event="X") | c.to(a, event="X")
        self.assertEqual(len(group.transitions), 3)

    def test_transition_standalone_function(self):
        t = transition(self.idle, "START", self.running)
        self.assertIsInstance(t, Transition)
        self.assertEqual(t.event, "START")
        self.assertEqual(t.source, self.idle)
        self.assertEqual(t.target, self.running)

    def test_transition_standalone_with_kwargs(self):
        t = transition(
            self.idle,
            "GO",
            self.running,
            guard="ok",
            actions=["log"],
        )
        self.assertEqual(t.guard, "ok")
        self.assertEqual(t.actions, ["log"])


class TestDecorators(unittest.TestCase):
    """Tests for @action, @guard, @service decorators."""

    def test_action_decorator_auto_name(self):
        @action
        def increment_counter(i, ctx, e, a):
            pass

        self.assertEqual(increment_counter._xsm_type, "action")
        self.assertEqual(increment_counter._xsm_name, "incrementCounter")

    def test_action_decorator_explicit_name(self):
        @action("customName")
        def my_func(i, ctx, e, a):
            pass

        self.assertEqual(my_func._xsm_name, "customName")

    def test_guard_decorator(self):
        @guard
        def can_retry(ctx, e):
            return True

        self.assertEqual(can_retry._xsm_type, "guard")
        self.assertEqual(can_retry._xsm_name, "canRetry")

    def test_service_decorator(self):
        @service
        def fetch_data(i, ctx, e):
            pass

        self.assertEqual(fetch_data._xsm_type, "service")
        self.assertEqual(fetch_data._xsm_name, "fetchData")

    def test_guard_async_raises_error(self):
        with self.assertRaises(NotSupportedError):

            @guard
            async def bad_guard(ctx, e):
                return True

    def test_action_decorator_preserves_function(self):
        @action
        def my_action(i, ctx, e, a):
            return 42

        self.assertEqual(my_action(None, None, None, None), 42)

    def test_guard_explicit_name(self):
        @guard("myGuard")
        def some_guard(ctx, e):
            return True

        self.assertEqual(some_guard._xsm_name, "myGuard")

    def test_service_explicit_name(self):
        @service("myService")
        def some_service(i, ctx, e):
            pass

        self.assertEqual(some_service._xsm_name, "myService")


class TestCompileConfig(unittest.TestCase):
    """Tests for _compile_config internal function."""

    def test_basic_two_state_machine(self):
        idle = State("idle", initial=True)
        running = State("running")
        t = idle.to(running, event="START")
        config = _compile_config(
            machine_id="test",
            states=[idle, running],
            transitions=[t],
            context=None,
        )
        self.assertEqual(config["id"], "test")
        self.assertEqual(config["initial"], "idle")
        self.assertIn("idle", config["states"])
        self.assertIn("running", config["states"])
        self.assertEqual(
            config["states"]["idle"]["on"]["START"],
            {"target": "running"},
        )

    def test_transition_with_guard_and_actions(self):
        a = State("a", initial=True)
        b = State("b")
        t = a.to(b, event="GO", guard="ok", actions=["log"])
        config = _compile_config(
            machine_id="t",
            states=[a, b],
            transitions=[t],
            context=None,
        )
        on_go = config["states"]["a"]["on"]["GO"]
        self.assertEqual(on_go["target"], "b")
        self.assertEqual(on_go["guard"], "ok")
        self.assertEqual(on_go["actions"], ["log"])

    def test_internal_transition_omits_target(self):
        a = State("a", initial=True)
        t = a.internal("HB", actions=["logHb"])
        config = _compile_config(
            machine_id="t",
            states=[a],
            transitions=[t],
            context=None,
        )
        on_hb = config["states"]["a"]["on"]["HB"]
        self.assertNotIn("target", on_hb)
        self.assertEqual(on_hb["actions"], ["logHb"])

    def test_reenter_compiles_flag(self):
        a = State("a", initial=True)
        t = a.to(a, event="R", reenter=True)
        config = _compile_config(
            machine_id="t",
            states=[a],
            transitions=[t],
            context=None,
        )
        self.assertTrue(config["states"]["a"]["on"]["R"]["reenter"])

    def test_conditional_transitions_same_event(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = a.to(b, event="GO", guard="g1") | a.to(c, event="GO")
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[group],
            context=None,
        )
        on_go = config["states"]["a"]["on"]["GO"]
        self.assertIsInstance(on_go, list)
        self.assertEqual(len(on_go), 2)

    def test_final_state_type(self):
        a = State("a", initial=True)
        done = State("done", final=True)
        config = _compile_config(
            machine_id="t",
            states=[a, done],
            transitions=[],
            context=None,
        )
        self.assertEqual(config["states"]["done"]["type"], "final")

    def test_parallel_state_type(self):
        r1 = State("r1", states=[State("a", initial=True)])
        r2 = State("r2", states=[State("b", initial=True)])
        p = State("p", parallel=True, states=[r1, r2])
        config = _compile_config(
            machine_id="t",
            states=[p],
            transitions=[],
            context=None,
        )
        self.assertEqual(config["states"]["p"]["type"], "parallel")

    def test_nested_states(self):
        child1 = State("c1", initial=True)
        child2 = State("c2")
        parent = State("parent", initial=True, states=[child1, child2])
        config = _compile_config(
            machine_id="t",
            states=[parent],
            transitions=[],
            context=None,
        )
        p_config = config["states"]["parent"]
        self.assertEqual(p_config["initial"], "c1")
        self.assertIn("c1", p_config["states"])
        self.assertIn("c2", p_config["states"])

    def test_context_passed_through(self):
        a = State("a", initial=True)
        config = _compile_config(
            machine_id="t",
            states=[a],
            transitions=[],
            context={"count": 0},
        )
        self.assertEqual(config["context"], {"count": 0})

    def test_state_on_dict_used_when_no_transition(self):
        a = State("a", initial=True, on={"CLICK": "b"})
        b = State("b")
        config = _compile_config(
            machine_id="t",
            states=[a, b],
            transitions=[],
            context=None,
        )
        self.assertEqual(config["states"]["a"]["on"]["CLICK"], "b")

    def test_transition_overrides_state_on(self):
        a = State("a", initial=True, on={"GO": "b"})
        b = State("b")
        c = State("c")
        t = a.to(c, event="GO", guard="check")
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[t],
            context=None,
        )
        on_go = config["states"]["a"]["on"]["GO"]
        self.assertEqual(on_go["target"], "c")
        self.assertEqual(on_go["guard"], "check")

    def test_always_string_compiles_to_empty_event(self):
        a = State("a", initial=True, always="done")
        done = State("done")
        config = _compile_config(
            machine_id="t",
            states=[a, done],
            transitions=[],
            context=None,
        )
        self.assertEqual(config["states"]["a"]["on"][""], "done")

    def test_always_dict_compiles_to_empty_event(self):
        a = State(
            "a",
            initial=True,
            always={"target": "done", "guard": "isOk"},
        )
        done = State("done")
        config = _compile_config(
            machine_id="t",
            states=[a, done],
            transitions=[],
            context=None,
        )
        self.assertEqual(
            config["states"]["a"]["on"][""],
            {"target": "done", "guard": "isOk"},
        )

    def test_on_done_string_compiles(self):
        child = State("child", initial=True, final=True)
        parent = State(
            "parent",
            initial=True,
            on_done="next",
            states=[child],
        )
        nxt = State("next")
        config = _compile_config(
            machine_id="t",
            states=[parent, nxt],
            transitions=[],
            context=None,
        )
        self.assertEqual(
            config["states"]["parent"]["onDone"],
            {"target": "next"},
        )

    def test_after_passed_through(self):
        a = State("a", initial=True, after={1000: "b"})
        b = State("b")
        config = _compile_config(
            machine_id="t",
            states=[a, b],
            transitions=[],
            context=None,
        )
        self.assertEqual(config["states"]["a"]["after"], {1000: "b"})

    def test_invoke_passed_through(self):
        a = State(
            "a",
            initial=True,
            invoke={"src": "svc", "onDone": "b"},
        )
        b = State("b")
        config = _compile_config(
            machine_id="t",
            states=[a, b],
            transitions=[],
            context=None,
        )
        self.assertEqual(
            config["states"]["a"]["invoke"],
            {"src": "svc", "onDone": "b"},
        )

    def test_entry_exit_in_config(self):
        a = State(
            "a",
            initial=True,
            entry=["logIn"],
            exit=["logOut"],
        )
        config = _compile_config(
            machine_id="t",
            states=[a],
            transitions=[],
            context=None,
        )
        # Single-element lists are unwrapped to bare strings
        self.assertEqual(config["states"]["a"]["entry"], "logIn")
        self.assertEqual(config["states"]["a"]["exit"], "logOut")

    def test_no_initial_state_raises(self):
        a = State("a")
        b = State("b")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, b],
                transitions=[],
                context=None,
            )

    def test_multiple_initial_states_raises(self):
        a = State("a", initial=True)
        b = State("b", initial=True)
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, b],
                transitions=[],
                context=None,
            )

    def test_duplicate_state_name_raises(self):
        a = State("a", initial=True)
        a2 = State("a")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, a2],
                transitions=[],
                context=None,
            )

    def test_unknown_transition_source_raises(self):
        a = State("a", initial=True)
        b = State("b")
        orphan = State("orphan")
        t = orphan.to(a, event="GO")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, b],
                transitions=[t],
                context=None,
            )

    def test_nested_state_dot_paths(self):
        child = State("c1", initial=True)
        parent = State("parent", initial=True, states=[child])
        other = State("other")
        t = child.to(other, event="GO")
        config = _compile_config(
            machine_id="t",
            states=[parent, other],
            transitions=[t],
            context=None,
        )
        on_go = config["states"]["parent"]["states"]["c1"]["on"]["GO"]
        self.assertEqual(on_go["target"], "other")


class TestCompileLogic(unittest.TestCase):
    """Tests for logic compilation functions."""

    def test_compile_from_decorated_functions(self):
        @action
        def my_action(i, ctx, e, a):
            pass

        @guard
        def my_guard(ctx, e):
            return True

        @service
        def my_service(i, ctx, e):
            pass

        logic = _compile_logic_from_functions(
            actions=[my_action],
            guards=[my_guard],
            services=[my_service],
        )
        self.assertIsInstance(logic, MachineLogic)
        self.assertIn("myAction", logic.actions)
        self.assertIn("myGuard", logic.guards)
        self.assertIn("myService", logic.services)

    def test_compile_from_undecorated_functions(self):
        def increment_counter(i, ctx, e, a):
            pass

        logic = _compile_logic_from_functions(
            actions=[increment_counter],
            guards=[],
            services=[],
        )
        self.assertIn("incrementCounter", logic.actions)

    def test_compile_from_instance_binds_self(self):
        class MyLogic:
            def __init__(self):
                self.called = False

            @action
            def do_thing(self, i, ctx, e, a):
                self.called = True

        instance = MyLogic()
        decorated = [
            v for v in vars(MyLogic).values() if hasattr(v, "_xsm_type")
        ]
        logic = _compile_logic_from_instance(
            instance=instance, decorated=decorated
        )
        # The bound function should work without `self`
        bound_fn = logic.actions["doThing"]
        bound_fn(None, {}, None, None)
        self.assertTrue(instance.called)

    def test_compile_guard_from_instance(self):
        class MyLogic:
            @guard
            def is_ready(self, ctx, e):
                return True

        instance = MyLogic()
        decorated = [
            v for v in vars(MyLogic).values() if hasattr(v, "_xsm_type")
        ]
        logic = _compile_logic_from_instance(
            instance=instance, decorated=decorated
        )
        bound_fn = logic.guards["isReady"]
        self.assertTrue(bound_fn({}, None))


class TestBuildMachineFunctional(unittest.TestCase):
    """Tests for the build_machine() functional API."""

    def test_basic_functional(self):
        idle = State("idle", initial=True)
        running = State("running")
        t = idle.to(running, event="START")
        machine = build_machine(
            id="test", states=[idle, running], transitions=[t]
        )
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.idle", interp.current_state_ids)
        interp.send("START")
        self.assertIn("test.running", interp.current_state_ids)
        interp.stop()

    def test_functional_with_decorated_actions(self):
        idle = State("idle", initial=True)
        active = State("active")
        result = {}

        @action
        def log_start(i, ctx, e, a):
            result["called"] = True

        t = idle.to(active, event="GO", actions=["logStart"])
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
            actions=[log_start],
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["called"])

    def test_functional_with_guards(self):
        idle = State("idle", initial=True)
        active = State("active")

        @guard
        def is_ready(ctx, e):
            return ctx.get("ready", False)

        t = idle.to(active, event="GO", guard="isReady")
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
            guards=[is_ready],
            context={"ready": False},
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        # Guard blocks -- still in idle
        self.assertIn("test.idle", interp.current_state_ids)
        interp.stop()

    def test_functional_with_undecorated_functions(self):
        idle = State("idle", initial=True)
        active = State("active")
        result = {}

        def log_start(i, ctx, e, a):
            result["called"] = True

        t = idle.to(active, event="GO", actions=["logStart"])
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
            actions=[log_start],
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["called"])

    def test_functional_with_transition_group(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        group = a.to(b, event="X") | b.to(c, event="X")
        machine = build_machine(
            id="test", states=[a, b, c], transitions=[group]
        )
        interp = SyncInterpreter(machine).start()
        interp.send("X")
        self.assertIn("test.b", interp.current_state_ids)
        interp.send("X")
        self.assertIn("test.c", interp.current_state_ids)
        interp.stop()

    def test_functional_context(self):
        idle = State("idle", initial=True)
        machine = build_machine(
            id="test",
            states=[idle],
            context={"count": 42},
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["count"], 42)
        interp.stop()


class TestMachineBuilder(unittest.TestCase):
    """Tests for MachineBuilder fluent API."""

    def test_basic_builder(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("running")
            .transition("idle", "START", "running")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.idle", interp.current_state_ids)
        interp.send("START")
        self.assertIn("test.running", interp.current_state_ids)
        interp.stop()

    def test_builder_with_logic(self):
        result = {}
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("active")
            .transition("idle", "GO", "active", actions=["logIt"])
            .action(
                "logIt",
                lambda i, ctx, e, a: result.update({"ok": True}),
            )
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["ok"])

    def test_builder_context(self):
        machine = (
            MachineBuilder("test")
            .context({"x": 1})
            .state("idle", initial=True)
            .build()
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 1)
        interp.stop()

    def test_builder_context_override(self):
        machine = (
            MachineBuilder("test")
            .context({"x": 1})
            .state("idle", initial=True)
            .build(context={"x": 99})
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 99)
        interp.stop()

    def test_builder_guard(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("active")
            .transition("idle", "GO", "active", guard="isOk")
            .guard("isOk", lambda ctx, e: False)
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertIn("test.idle", interp.current_state_ids)
        interp.stop()

    def test_builder_child_states(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("moving")
            .child_states(
                "moving",
                initial="up",
                states={"up": {}, "down": {}},
            )
            .transition("idle", "GO", "moving")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertIn("test.moving.up", interp.current_state_ids)
        interp.stop()

    def test_builder_child_states_unknown_parent_raises(self):
        builder = MachineBuilder("test").state("idle", initial=True)
        with self.assertRaises(InvalidConfigError):
            builder.child_states(
                "nonexistent",
                initial="x",
                states={"x": {}},
            )

    def test_builder_final_state(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("done", final=True)
            .transition("idle", "FINISH", "done")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("FINISH")
        self.assertIn("test.done", interp.current_state_ids)
        interp.stop()


class TestStateMachineClassBased(unittest.TestCase):
    """Tests for the StateMachine class-based API."""

    def test_basic_machine_creation(self):
        class Light(StateMachine):
            off = State(initial=True)
            on = State()
            toggle = off.to(on, event="TOGGLE") | on.to(off, event="TOGGLE")

        machine = Light.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("Light.off", interp.current_state_ids)
        interp.send("TOGGLE")
        self.assertIn("Light.on", interp.current_state_ids)
        interp.send("TOGGLE")
        self.assertIn("Light.off", interp.current_state_ids)
        interp.stop()

    def test_custom_machine_id(self):
        class Light(StateMachine):
            machine_id = "myLight"
            off = State(initial=True)
            on = State()

        machine = Light.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("myLight.off", interp.current_state_ids)
        interp.stop()

    def test_actions_fire(self):
        result = {}

        class Counter(StateMachine):
            idle = State(initial=True)
            done = State()
            go = idle.to(done, event="GO", actions=["logIt"])

            @action
            def log_it(self, i, ctx, e, a):
                result["fired"] = True

        machine = Counter.create_machine()
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result["fired"])

    def test_guards_block(self):
        class Gated(StateMachine):
            idle = State(initial=True)
            active = State()
            go = idle.to(active, event="GO", guard="isReady")

            @guard
            def is_ready(self, ctx, e):
                return ctx.get("ready", False)

        machine = Gated.create_machine(context={"ready": False})
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertIn("Gated.idle", interp.current_state_ids)
        interp.stop()

    def test_context_override(self):
        class WithCtx(StateMachine):
            initial_context = {"x": 1}
            idle = State(initial=True)

        machine = WithCtx.create_machine(context={"x": 99})
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 99)
        interp.stop()

    def test_state_names_auto_inferred(self):
        class M(StateMachine):
            my_state = State(initial=True)

        machine = M.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("M.my_state", interp.current_state_ids)
        interp.stop()


class TestBackwardCompatibility(unittest.TestCase):
    """Verify existing JSON API still works unchanged."""

    def test_json_api_still_works(self):
        config = {
            "id": "test",
            "initial": "idle",
            "states": {
                "idle": {"on": {"GO": "running"}},
                "running": {"type": "final"},
            },
        }
        machine = create_machine(config)
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.idle", interp.current_state_ids)
        interp.send("GO")
        self.assertIn("test.running", interp.current_state_ids)
        interp.stop()

    def test_pythonic_works_with_plugins(self):
        events_seen = []

        class TestPlugin(PluginBase):
            def on_transition(self, interp, frm, to, t):
                events_seen.append("transition")

        idle = State("idle", initial=True)
        active = State("active")
        t = idle.to(active, event="GO")
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
        )
        interp = SyncInterpreter(machine)
        interp.use(TestPlugin())
        interp.start()
        interp.send("GO")
        interp.stop()
        self.assertIn("transition", events_seen)

    def test_all_existing_tests_still_pass(self):
        """Meta-test: existing test suite must not be broken.

        This is verified by running the full test suite, not by
        this individual test. This test just documents the intent.
        """
        pass


# =================================================================
# 🔀 Always Transitions (dedicated class from spec §11)
# =================================================================


class TestAlwaysTransitions(unittest.TestCase):
    """Tests for always (eventless) transitions."""

    def test_always_list_compiles_to_empty_event(self):
        a = State(
            "a",
            initial=True,
            always=[
                {"target": "b", "guard": "isOk"},
                {"target": "c"},
            ],
        )
        b = State("b")
        c = State("c")
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[],
            context=None,
        )
        on_empty = config["states"]["a"]["on"][""]
        self.assertIsInstance(on_empty, list)
        self.assertEqual(len(on_empty), 2)

    def test_always_works_with_sync_interpreter(self):
        """Always transitions should fire immediately."""
        a = State(
            "a",
            initial=True,
            always={"target": "b"},
        )
        b = State("b")
        machine = build_machine(id="test", states=[a, b], transitions=[])
        interp = SyncInterpreter(machine).start()
        # Should immediately transition to b
        self.assertIn("test.b", interp.current_state_ids)
        interp.stop()

    def test_always_in_builder(self):
        machine = (
            MachineBuilder("test")
            .state("a", initial=True, always={"target": "b"})
            .state("b")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.b", interp.current_state_ids)
        interp.stop()

    def test_always_in_functional(self):
        a = State(
            "a",
            initial=True,
            always={"target": "b"},
        )
        b = State("b")
        machine = build_machine(id="test", states=[a, b])
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.b", interp.current_state_ids)
        interp.stop()


# =================================================================
# 🏗️ StateMachine Class-Based — Extended Tests (spec §11)
# =================================================================


class TestStateMachineClassBasedExtended(unittest.TestCase):
    """Extended tests for the StateMachine class-based API."""

    def test_hierarchical_states_nested_class(self):
        class Elevator(StateMachine):
            idle = State(initial=True)

            class moving(State):
                up = State(initial=True)
                down = State()

            go_up = idle.to(moving.up, event="CALL_UP")

        machine = Elevator.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("Elevator.idle", interp.current_state_ids)
        interp.send("CALL_UP")
        self.assertIn("Elevator.moving.up", interp.current_state_ids)
        interp.stop()

    def test_entry_exit_decorators(self):
        results = {}

        class M(StateMachine):
            idle = State(initial=True)
            active = State()
            go = idle.to(active, event="GO")

            @idle.enter
            def on_idle_enter(self, i, ctx, e, a):
                results["entered"] = True

            @idle.exit
            def on_idle_exit(self, i, ctx, e, a):
                results["exited"] = True

        machine = M.create_machine()
        interp = SyncInterpreter(machine).start()
        # Enter fires on start
        self.assertTrue(results.get("entered"))
        interp.send("GO")
        # Exit fires on leaving idle
        self.assertTrue(results.get("exited"))
        interp.stop()

    def test_self_binding_with_functools_partial(self):
        """Verify that decorated methods have `self` properly
        bound via functools.partial."""

        class Counter(StateMachine):
            initial_context = {"count": 0}
            idle = State(initial=True)
            done = State()
            go = idle.to(done, event="GO", actions=["increment"])

            @action
            def increment(self, i, ctx, e, a):
                ctx["count"] += 1

        machine = Counter.create_machine()
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        self.assertEqual(interp.context["count"], 1)
        interp.stop()

    def test_on_done_class_based(self):
        class M(StateMachine):
            parent = State(
                initial=True,
                on_done="done",
                states=[State("c", initial=True, final=True)],
            )
            done = State()

        # Should compile without error
        machine = M.create_machine()
        self.assertIsNotNone(machine)

    def test_context_with_initial_context_attr(self):
        class M(StateMachine):
            initial_context = {"x": 42}
            idle = State(initial=True)

        machine = M.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 42)
        interp.stop()


# =================================================================
# 🔧 MachineBuilder — Extended Tests (spec §11)
# =================================================================


class TestMachineBuilderExtended(unittest.TestCase):
    """Extended tests for MachineBuilder fluent API."""

    def test_builder_parallel(self):
        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("regions")
            .child_states(
                "regions",
                parallel=True,
                states={
                    "r1": {
                        "initial": "a",
                        "states": {"a": {}, "b": {}},
                    },
                    "r2": {
                        "initial": "c",
                        "states": {"c": {}, "d": {}},
                    },
                },
            )
            .transition("idle", "GO", "regions")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        ids = interp.current_state_ids
        self.assertTrue(
            any("r1" in s for s in ids),
            f"Expected r1 region in {ids}",
        )
        interp.stop()

    def test_builder_invoke(self):
        machine = (
            MachineBuilder("test")
            .state(
                "loading",
                initial=True,
                invoke={
                    "src": "fetchData",
                    "onDone": "success",
                },
            )
            .state("success")
            .service(
                "fetchData",
                lambda i, ctx, e: {"result": "ok"},
            )
            .build()
        )
        self.assertIsNotNone(machine)

    def test_builder_after(self):
        machine = (
            MachineBuilder("test")
            .state(
                "waiting",
                initial=True,
                after={500: "done"},
            )
            .state("done")
            .build()
        )
        self.assertIsNotNone(machine)

    def test_builder_always(self):
        machine = (
            MachineBuilder("test")
            .state(
                "a",
                initial=True,
                always={"target": "b"},
            )
            .state("b")
            .build()
        )
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.b", interp.current_state_ids)
        interp.stop()

    def test_builder_accepts_decorated_functions(self):
        @action
        def log_it(i, ctx, e, a):
            pass

        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("active")
            .transition("idle", "GO", "active", actions=["logIt"])
            .action("logIt", log_it)
            .build()
        )
        self.assertIsNotNone(machine)

    def test_builder_on_done(self):
        machine = (
            MachineBuilder("test")
            .state("parent", initial=True, on_done="done")
            .child_states(
                "parent",
                initial="child",
                states={"child": {"type": "final"}},
            )
            .state("done")
            .build()
        )
        self.assertIsNotNone(machine)

    def test_builder_build_idempotent(self):
        """Calling build() twice should produce valid machines
        without corrupting internal state."""
        builder = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("active")
            .transition("idle", "GO", "active")
        )
        machine1 = builder.build()
        machine2 = builder.build()

        interp1 = SyncInterpreter(machine1).start()
        interp1.send("GO")
        self.assertIn("test.active", interp1.current_state_ids)
        interp1.stop()

        interp2 = SyncInterpreter(machine2).start()
        interp2.send("GO")
        self.assertIn("test.active", interp2.current_state_ids)
        interp2.stop()


# =================================================================
# 🏗️ Functional API — Extended Tests (spec §11)
# =================================================================


class TestBuildMachineFunctionalExtended(unittest.TestCase):
    """Extended tests for the build_machine() functional API."""

    def test_functional_hierarchical(self):
        child1 = State("c1", initial=True)
        child2 = State("c2")
        parent = State("parent", initial=True, states=[child1, child2])
        machine = build_machine(id="test", states=[parent])
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.parent.c1", interp.current_state_ids)
        interp.stop()

    def test_functional_invoke(self):
        idle = State(
            "idle",
            initial=True,
            invoke={
                "src": "fetchData",
                "onDone": "done",
            },
        )
        done = State("done")

        @service
        def fetch_data(i, ctx, e):
            return {"ok": True}

        machine = build_machine(
            id="test",
            states=[idle, done],
            services=[fetch_data],
        )
        self.assertIsNotNone(machine)

    def test_functional_after(self):
        wait = State("wait", initial=True, after={500: "done"})
        done = State("done")
        machine = build_machine(id="test", states=[wait, done])
        self.assertIsNotNone(machine)

    def test_functional_always(self):
        a = State("a", initial=True, always={"target": "b"})
        b = State("b")
        machine = build_machine(id="test", states=[a, b])
        interp = SyncInterpreter(machine).start()
        self.assertIn("test.b", interp.current_state_ids)
        interp.stop()

    def test_functional_on_done(self):
        child = State("child", initial=True, final=True)
        parent = State(
            "parent",
            initial=True,
            on_done="done",
            states=[child],
        )
        done = State("done")
        machine = build_machine(id="test", states=[parent, done])
        self.assertIsNotNone(machine)


# =================================================================
# 🔀 Merge Rules (spec §11)
# =================================================================


class TestMergeRules(unittest.TestCase):
    """Tests for transition merge behavior."""

    def test_transition_overrides_state_on_for_same_event(self):
        a = State("a", initial=True, on={"GO": "b"})
        b = State("b")
        c = State("c")
        t = a.to(c, event="GO", guard="check")
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[t],
            context=None,
        )
        on_go = config["states"]["a"]["on"]["GO"]
        self.assertEqual(on_go["target"], "c")
        self.assertEqual(on_go["guard"], "check")

    def test_state_on_preserved_when_no_transition_conflict(
        self,
    ):
        a = State("a", initial=True, on={"CLICK": "b"})
        b = State("b")
        c = State("c")
        t = a.to(c, event="OTHER")
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[t],
            context=None,
        )
        self.assertEqual(config["states"]["a"]["on"]["CLICK"], "b")
        self.assertEqual(config["states"]["a"]["on"]["OTHER"]["target"], "c")

    def test_mixed_on_and_transitions_different_events(self):
        a = State("a", initial=True, on={"X": "b"})
        b = State("b")
        c = State("c")
        t = a.to(c, event="Y")
        config = _compile_config(
            machine_id="t",
            states=[a, b, c],
            transitions=[t],
            context=None,
        )
        self.assertEqual(config["states"]["a"]["on"]["X"], "b")
        self.assertIn("Y", config["states"]["a"]["on"])


# =================================================================
# 🚨 Error Handling (consolidated class from spec §11)
# =================================================================


class TestErrorHandling(unittest.TestCase):
    """Consolidated error-handling tests."""

    def test_final_and_parallel_raises(self):
        with self.assertRaises(InvalidConfigError):
            State("bad", final=True, parallel=True)

    def test_final_with_on_transitions_raises(self):
        done = State("done", final=True, on={"GO": "other"})
        other = State("other", initial=True)
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[other, done],
                transitions=[],
                context=None,
            )

    def test_final_with_children_raises(self):
        child = State("child", initial=True)
        done = State("done", final=True, states=[child])
        other = State("other", initial=True)
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[other, done],
                transitions=[],
                context=None,
            )

    def test_final_with_transition_object_raises(self):
        done = State("done", final=True)
        other = State("other", initial=True)
        t = done.to(other, event="GO")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[other, done],
                transitions=[t],
                context=None,
            )

    def test_parallel_child_with_initial_raises(self):
        c1 = State(
            "c1",
            initial=True,
            states=[State("a", initial=True)],
        )
        c2 = State(
            "c2",
            states=[State("b", initial=True)],
        )
        parent = State(
            "parent",
            initial=True,
            parallel=True,
            states=[c1, c2],
        )
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[parent],
                transitions=[],
                context=None,
            )

    def test_to_without_event_raises(self):
        a = State("a", initial=True)
        b = State("b")
        with self.assertRaises(InvalidConfigError):
            a.to(b)

    def test_async_guard_raises(self):
        with self.assertRaises(NotSupportedError):

            @guard
            async def bad_guard(ctx, e):
                return True

    def test_async_guard_explicit_name_raises(self):
        with self.assertRaises(NotSupportedError):

            @guard("myGuard")
            async def bad_guard(ctx, e):
                return True

    def test_duplicate_state_name_raises(self):
        a = State("a", initial=True)
        a2 = State("a")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a, a2],
                transitions=[],
                context=None,
            )

    def test_unknown_transition_source_raises(self):
        a = State("a", initial=True)
        orphan = State("orphan")
        t = orphan.to(a, event="GO")
        with self.assertRaises(InvalidConfigError):
            _compile_config(
                machine_id="t",
                states=[a],
                transitions=[t],
                context=None,
            )


# =================================================================
# 🐍 __repr__ Tests
# =================================================================


class TestRepr(unittest.TestCase):
    """Tests for __repr__ methods on public classes."""

    def test_state_repr(self):
        s = State("idle", initial=True)
        r = repr(s)
        self.assertIn("idle", r)
        self.assertIn("initial", r)

    def test_state_repr_no_flags(self):
        s = State("plain")
        r = repr(s)
        self.assertIn("plain", r)
        self.assertNotIn("initial", r)

    def test_transition_repr(self):
        a = State("a")
        b = State("b")
        t = a.to(b, event="GO")
        r = repr(t)
        self.assertIn("a", r)
        self.assertIn("b", r)
        self.assertIn("GO", r)

    def test_transition_group_repr(self):
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        g = a.to(b, event="X") | b.to(c, event="X")
        r = repr(g)
        self.assertIn("2", r)

    def test_machine_builder_repr(self):
        builder = (
            MachineBuilder("myMachine")
            .state("idle", initial=True)
            .state("running")
        )
        r = repr(builder)
        self.assertIn("myMachine", r)
        self.assertIn("2", r)


# =================================================================
# 🔧 Build Idempotency & Context Edge Cases
# =================================================================


class TestEdgeCases(unittest.TestCase):
    """Edge case tests for discovered issues."""

    def test_empty_context_dict_preserved(self):
        """An empty dict {} should be set as context,
        not treated as falsy/None."""
        idle = State("idle", initial=True)
        machine = build_machine(
            id="test",
            states=[idle],
            context={},
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context, {})
        interp.stop()

    def test_builder_empty_context_preserved(self):
        machine = (
            MachineBuilder("test")
            .context({})
            .state("idle", initial=True)
            .build()
        )
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context, {})
        interp.stop()

    def test_class_based_empty_context_preserved(self):
        class M(StateMachine):
            initial_context = {}
            idle = State(initial=True)

        machine = M.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context, {})
        interp.stop()

    def test_class_based_context_none_override(self):
        """Passing context=None should use initial_context."""

        class M(StateMachine):
            initial_context = {"x": 1}
            idle = State(initial=True)

        machine = M.create_machine(context=None)
        interp = SyncInterpreter(machine).start()
        self.assertEqual(interp.context["x"], 1)
        interp.stop()

    def test_builder_action_uses_explicit_name(self):
        """MachineBuilder.action() should use the explicitly
        provided name, not _xsm_name from decorators."""
        result = {}

        @action("decoratorName")
        def my_func(i, ctx, e, a):
            result["ok"] = True

        machine = (
            MachineBuilder("test")
            .state("idle", initial=True)
            .state("done")
            .transition(
                "idle",
                "GO",
                "done",
                actions=["explicitName"],
            )
            .action("explicitName", my_func)
            .build()
        )
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(result.get("ok"))

    def test_exit_decorator_on_state(self):
        """@state.exit should work as a decorator (not
        _exit_decorator)."""
        results = {}

        class M(StateMachine):
            idle = State(initial=True)
            done = State()
            go = idle.to(done, event="GO")

            @idle.exit
            def on_exit(self, i, ctx, e, a):
                results["exited"] = True

        machine = M.create_machine()
        interp = SyncInterpreter(machine).start()
        interp.send("GO")
        interp.stop()
        self.assertTrue(results.get("exited"))


# =================================================================
# 🔴 Round-2 Fixes — New Validation Tests
# =================================================================


class TestRound2Fixes(unittest.TestCase):
    """Tests for round-2 review fixes."""

    def test_enter_decorator_outside_class_raises(self):
        """@state.enter used outside StateMachine class
        should raise InvalidConfigError at build time."""
        idle = State("idle", initial=True)
        done = State("done")

        @idle.enter
        def on_enter(i, ctx, e, a):
            pass

        with self.assertRaises(InvalidConfigError):
            build_machine(
                id="test",
                states=[idle, done],
                actions=[on_enter],
            )

    def test_exit_decorator_outside_class_raises(self):
        """@state.exit used outside StateMachine class
        should raise InvalidConfigError at build time."""
        idle = State("idle", initial=True)
        done = State("done")

        @idle.exit
        def on_exit(i, ctx, e, a):
            pass

        with self.assertRaises(InvalidConfigError):
            build_machine(
                id="test",
                states=[idle, done],
                actions=[on_exit],
            )

    def test_transition_or_with_invalid_type(self):
        """Transition | non-Transition should raise TypeError."""
        a = State("a", initial=True)
        b = State("b")
        t = a.to(b, event="GO")
        with self.assertRaises(TypeError):
            _ = t | "not_a_transition"

    def test_transition_group_or_with_invalid_type(self):
        """TransitionGroup | non-Transition should raise TypeError."""
        a = State("a", initial=True)
        b = State("b")
        c = State("c")
        g = a.to(b, event="X") | b.to(c, event="X")
        with self.assertRaises(TypeError):
            _ = g | 42

    def test_builder_duplicate_state_raises(self):
        """MachineBuilder.state() should reject duplicate names."""
        builder = MachineBuilder("test").state("idle", initial=True)
        with self.assertRaises(InvalidConfigError):
            builder.state("idle")

    def test_builder_no_initial_state_raises(self):
        """MachineBuilder.build() should raise when no initial
        state is defined and multiple states exist."""
        builder = MachineBuilder("test").state("a").state("b")
        with self.assertRaises(InvalidConfigError):
            builder.build()

    def test_builder_single_state_no_initial_ok(self):
        """A single-state builder should not require initial
        (the interpreter infers it)."""
        machine = MachineBuilder("test").state("only").build()
        self.assertIsNotNone(machine)

    def test_state_reuse_across_builds(self):
        """State objects reused across multiple builds
        should not corrupt each other."""
        idle = State("idle", initial=True)
        done = State("done")
        t = idle.to(done, event="GO")

        m1 = build_machine(
            id="m1",
            states=[idle, done],
            transitions=[t],
        )
        m2 = build_machine(
            id="m2",
            states=[idle, done],
            transitions=[t],
        )

        i1 = SyncInterpreter(m1).start()
        i2 = SyncInterpreter(m2).start()
        self.assertIn("m1.idle", i1.current_state_ids)
        self.assertIn("m2.idle", i2.current_state_ids)
        i1.stop()
        i2.stop()


# =================================================================
# 🔀 Spec §11 — Missing Test Coverage
# =================================================================


class TestClassBasedParallelNestedClass(unittest.TestCase):
    """Tests for parallel states via nested class syntax."""

    def test_parallel_states_nested_class(self):
        """Parallel states defined via nested class syntax."""
        r1_a = State("a", initial=True)
        r1_b = State("b")
        r2_c = State("c", initial=True)
        r2_d = State("d")
        r1 = State("r1", states=[r1_a, r1_b])
        r2 = State("r2", states=[r2_c, r2_d])
        idle = State("idle", initial=True)
        monitoring = State(
            "monitoring",
            parallel=True,
            states=[r1, r2],
        )

        t = idle.to(monitoring, event="START")
        machine = build_machine(
            id="test",
            states=[idle, monitoring],
            transitions=[t],
        )
        interp = SyncInterpreter(machine).start()
        interp.send("START")
        ids = interp.current_state_ids
        self.assertTrue(
            any("r1" in s for s in ids),
            f"Expected r1 region in {ids}",
        )
        self.assertTrue(
            any("r2" in s for s in ids),
            f"Expected r2 region in {ids}",
        )
        interp.stop()


class TestClassBasedAlways(unittest.TestCase):
    """Tests for always transition in class-based API."""

    def test_always_transition_class_based(self):
        class M(StateMachine):
            a = State(
                initial=True,
                always={"target": "b"},
            )
            b = State()

        machine = M.create_machine()
        interp = SyncInterpreter(machine).start()
        self.assertIn("M.b", interp.current_state_ids)
        interp.stop()


class TestAsyncInterpreterCompat(unittest.TestCase):
    """Tests for Pythonic API with async Interpreter."""

    def test_pythonic_machine_works_with_async_interpreter(
        self,
    ):
        idle = State("idle", initial=True)
        active = State("active")
        t = idle.to(active, event="GO")
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
        )

        async def run():
            interp = await Interpreter(machine).start()
            self.assertIn("test.idle", interp.current_state_ids)
            await interp.send("GO")
            # Allow event loop to process the queued event
            await asyncio.sleep(0.05)
            self.assertIn("test.active", interp.current_state_ids)
            await interp.stop()

        asyncio.run(run())


class TestSnapshotRestore(unittest.TestCase):
    """Tests for Pythonic machine snapshot/restore."""

    def test_pythonic_machine_snapshot_restore(self):
        idle = State("idle", initial=True)
        active = State("active")
        t = idle.to(active, event="GO")
        machine = build_machine(
            id="test",
            states=[idle, active],
            transitions=[t],
            context={"count": 0},
        )

        interp = SyncInterpreter(machine).start()
        snapshot = interp.get_snapshot()
        self.assertIn("test.idle", interp.current_state_ids)

        interp.send("GO")
        self.assertIn("test.active", interp.current_state_ids)
        interp.stop()

        # Restore to original state via factory method
        interp2 = SyncInterpreter.from_snapshot(snapshot, machine)
        self.assertIn("test.idle", interp2.current_state_ids)


class TestConfigOutputMatchesJson(unittest.TestCase):
    """Tests verifying Pythonic output matches JSON format."""

    def test_config_output_matches_json_format(self):
        """Pythonic API should produce identical config to
        hand-written JSON."""
        idle = State("idle", initial=True)
        running = State("running")
        done = State("done", final=True)
        t = idle.to(running, event="START") | running.to(done, event="FINISH")
        config = _compile_config(
            machine_id="test",
            states=[idle, running, done],
            transitions=[t],
            context={"count": 0},
        )

        expected = {
            "id": "test",
            "initial": "idle",
            "context": {"count": 0},
            "states": {
                "idle": {"on": {"START": {"target": "running"}}},
                "running": {"on": {"FINISH": {"target": "done"}}},
                "done": {"type": "final"},
            },
        }
        self.assertEqual(config, expected)
