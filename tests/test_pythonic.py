# tests/test_pythonic.py
"""Tests for the Pythonic API layer."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import unittest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine.pythonic import (
    _snake_to_camel,
    _compile_config,
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
        self.assertEqual(s.exit, ["cleanup"])

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
