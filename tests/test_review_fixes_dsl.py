# tests/test_review_fixes_dsl.py
"""
🐍 Regression tests for the 0.12.0 code review of the Pythonic DSL.

Each test names the review finding (``PD-xx``) it pins. They cover the
class façade, the metaclass, hook binding, nested-class inheritance,
build-time validation, the functional compiler and ``MachineBuilder``.
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import asyncio
import functools
import logging

# -------------------------------------------------------------------------
# 📦 Third-Party Imports
# -------------------------------------------------------------------------
import pytest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine import (
    InvalidConfigError,
    NotSupportedError,
)
from xstate_statemachine.pythonic import (
    MachineBuilder,
    State,
    StateMachine,
    _attr_to_event,
    _compile_config,
    action,
    build_machine,
    guard,
    service,
    transition,
)

# =========================================================================
# PD-01 / PD-02: plain async methods bound by name
# =========================================================================


def test_pd01_plain_async_guard_bound_by_name_is_refused():
    class M(StateMachine):
        a = State(initial=True)
        b = State()
        go = a.to(b, guard="ok")

        async def ok(self):
            return False

    with pytest.raises(NotSupportedError, match="ok"):
        M()


def test_pd02_auto_engine_counts_plain_async_actions_bound_by_name():
    class M(StateMachine):
        a = State(initial=True)
        b = State()
        go = a.to(b, actions=["do_it"])

        async def do_it(self, context):
            context["done"] = True

    async def main():
        m = M()
        assert m.engine == "async"
        async with m:
            await m.go()
            assert m.state == "b"
            assert m.context["done"] is True

    asyncio.run(main())


def test_pd02_unreferenced_async_helper_keeps_sync_engine():
    class M(StateMachine):
        a = State(initial=True)
        b = State()
        go = a.to(b)

        async def helper(self):  # never referenced by the chart
            return None

    with M() as m:
        assert m.engine == "sync"


# =========================================================================
# PD-03 / PD-04: callbacks and states that would shadow the façade
# =========================================================================


def test_pd03_decorated_callback_named_like_facade_method_is_refused():
    with pytest.raises(InvalidConfigError, match="'send' is reserved"):

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["send"])

            @action
            def send(self, context):
                pass


def test_pd03_decorated_callback_named_like_lifecycle_is_refused():
    with pytest.raises(InvalidConfigError, match="'stop'"):

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b, actions=["halt"])

            @action("halt")
            def stop(self):
                pass


def test_pd04_states_named_start_and_stop_keep_lifecycle(caplog):
    with caplog.at_level(logging.WARNING):

        class M(StateMachine):
            start = State(initial=True)
            stop = State(final=True)
            finish = start.to(stop)

    assert "lifecycle" in caplog.text
    m = M()
    assert m.state == "start"
    assert m.matches("start")
    m.stop()  # the lifecycle method, not a BoundState
    assert m.status == "stopped"
    with M() as m2:
        m2.finish()
        assert m2.state == "stop"


# =========================================================================
# PD-05: inferred event names
# =========================================================================


@pytest.mark.parametrize(
    "attr, event",
    [
        ("cycle", "CYCLE"),
        ("slow_down", "SLOW_DOWN"),
        ("slowDown", "SLOW_DOWN"),
        ("go2", "GO2"),
        ("START_NOW", "START_NOW"),
        ("START", "START"),
        ("HTTPError", "HTTP_ERROR"),
        ("XMLHttp", "XML_HTTP"),
        ("parseXML", "PARSE_XML"),
    ],
)
def test_pd05_attr_to_event(attr, event):
    assert _attr_to_event(attr) == event


def test_pd05_screaming_attribute_keeps_its_event():
    class M(StateMachine):
        a = State(initial=True)
        b = State()
        GO_NOW = a.to(b)

    with M() as m:
        m.GO_NOW()
        assert m.state == "b"
        assert "GO_NOW" in m.machine.known_events


# =========================================================================
# PD-07 / PD-20: functional compiler
# =========================================================================


def test_pd07_internal_transition_with_target_is_refused():
    a = State("a", initial=True)
    b = State("b")
    with pytest.raises(InvalidConfigError, match="internal"):
        transition(a, "GO", b, internal=True)
    # ✅ The internal form with no target is fine.
    t = transition(a, "GO", None, internal=True)
    assert t.target is None


def test_pd07_builder_internal_transition_with_target_is_refused():
    with pytest.raises(InvalidConfigError, match="internal"):
        MachineBuilder("m").state("a", initial=True).transition(
            "a", "GO", "a", internal=True
        )


def test_pd20_ambiguous_foreign_state_name_is_refused():
    x1 = State("x", initial=True)
    x2 = State("x", initial=True)
    p = State("p", initial=True, states=[x1])
    q = State("q", states=[x2])
    foreign = State("x")
    with pytest.raises(InvalidConfigError, match="ambiguous"):
        _compile_config(
            machine_id="m",
            states=[p, q],
            transitions=[transition(foreign, "GO", q)],
        )


# =========================================================================
# PD-08 / PD-09: naming-convention hooks
# =========================================================================


def test_pd08_before_and_after_hooks_see_dict_declared_events(caplog):
    with caplog.at_level(logging.WARNING):

        class M(StateMachine):
            a = State(initial=True, on={"GO": "b"})
            b = State()

            def __init__(self, *args, **kwargs):
                self.calls = []
                super().__init__(*args, **kwargs)

            def before_go(self):
                self.calls.append("before")

            def after_go(self):
                self.calls.append("after")

    assert "never run" not in caplog.text
    with M() as m:
        m.send("GO")
        assert m.state == "b"
        assert m.calls == ["before", "after"]


def test_pd08_unknown_event_warning_is_grammatical(caplog):
    with caplog.at_level(logging.WARNING):

        class M(StateMachine):
            a = State(initial=True)
            b = State()
            go = a.to(b)

            def before_nope(self):
                pass

    assert "is not an event of this machine" in caplog.text


def test_pd09_after_hook_runs_once_per_macrostep():
    class M(StateMachine):
        a = State(initial=True)
        b = State(always="c")
        c = State()
        go = a.to(b)

        def __init__(self, *args, **kwargs):
            self.calls = []
            super().__init__(*args, **kwargs)

        def after_go(self):
            self.calls.append("go")

        def after_transition(self):
            self.calls.append("*")

    with M() as m:
        m.go()
        assert m.state == "c"
        assert sorted(m.calls) == ["*", "go"]


# =========================================================================
# PD-12: nested state class inheritance
# =========================================================================


def test_pd12_nested_state_class_inheriting_children_is_refused():
    class base_p(State.Compound):
        x = State(initial=True)
        y = State()

    with pytest.raises(InvalidConfigError, match="base_p"):

        class M(StateMachine):
            class p2(base_p, initial=True):
                pass


def test_pd12_nested_state_class_with_empty_base_is_fine():
    class Marker(State.Compound):
        pass

    class M(StateMachine):
        class p(Marker, initial=True):
            x = State(initial=True)

    with M() as m:
        assert m.state == "p.x"


# =========================================================================
# PD-13 / PD-14 / PD-30: callable registration
# =========================================================================


def test_pd13_partial_with_explicit_name_is_accepted():
    def f(context, event, k=0):
        return k == 1

    g = functools.partial(f, k=1)
    g._xsm_name = "myGuard"  # type: ignore[attr-defined]
    m = build_machine(
        id="m",
        states=[State("a", initial=True)],
        guards=[g],
    )
    assert "myGuard" in m.logic.guards


def test_pd13_nameless_callable_is_a_config_error():
    def f(context, event, k=0):
        return True

    with pytest.raises(InvalidConfigError, match="name"):
        build_machine(
            id="m",
            states=[State("a", initial=True)],
            guards=[functools.partial(f, k=1)],
        )


def test_pd14_guard_passed_as_action_is_refused():
    @guard
    def g(context, event):
        return True

    with pytest.raises(InvalidConfigError, match="@guard"):
        build_machine(id="m", states=[State("a", initial=True)], actions=[g])


def test_pd14_duplicate_registered_name_is_refused():
    @action("x")
    def one(context):
        pass

    @action("x")
    def two(context):
        pass

    with pytest.raises(InvalidConfigError, match="'x'"):
        build_machine(
            id="m", states=[State("a", initial=True)], actions=[one, two]
        )


def test_pd14_duplicate_name_on_class_is_refused():
    class M(StateMachine):
        a = State(initial=True)
        b = State()
        go = a.to(b, actions=["x"])

        @action("x")
        def one(self):
            pass

        @action("x")
        def two(self):
            pass

    with pytest.raises(InvalidConfigError, match="'x'"):
        M()


@pytest.mark.parametrize("bad", ["", 123])
def test_pd30_decorator_rejects_bad_names(bad):
    for deco in (action, guard, service):
        with pytest.raises(InvalidConfigError):
            deco(bad)


def test_pd30_second_decorator_with_other_kind_is_refused():
    with pytest.raises(InvalidConfigError, match="already"):

        @action
        @guard
        def both(context, event):
            return True


# =========================================================================
# PD-15 / PD-16: MachineBuilder
# =========================================================================


def test_pd15_builder_does_not_mutate_caller_on_dict():
    on = {"X": "b"}
    MachineBuilder("m").state("a", initial=True, on=on, always="b")
    assert on == {"X": "b"}


def test_pd15_builder_refuses_history_with_final_or_bad_value():
    with pytest.raises(InvalidConfigError, match="history"):
        MachineBuilder("m").state("h", final=True, history="deep")
    with pytest.raises(InvalidConfigError, match="history"):
        MachineBuilder("m").state("h", history="sideways")


def test_pd16_builder_refuses_initial_with_parallel_children():
    b = MachineBuilder("m").state("p", initial=True)
    with pytest.raises(InvalidConfigError, match="parallel"):
        b.child_states(
            "p", initial="x", parallel=True, states={"x": {}, "y": {}}
        )


def test_pd16_builder_root_refuses_structural_keys():
    with pytest.raises(InvalidConfigError, match="states"):
        MachineBuilder("m").root(states={})


# =========================================================================
# PD-18 / PD-19 / PD-24: metaclass and façade details
# =========================================================================


def test_pd18_subclass_named_statemachine_is_compiled():
    # 📝 A subclass literally called `StateMachine` is a normal machine.
    ns = {
        "a": State(initial=True),
        "b": State(),
        "__module__": __name__,
        "__qualname__": "StateMachine",
    }
    cls = type(StateMachine)("StateMachine", (StateMachine,), ns)
    with cls() as m:
        assert m.state == "a"


def test_pd19_private_state_attribute_warns(caplog):
    with caplog.at_level(logging.WARNING):

        class M(StateMachine):
            a = State(initial=True)
            _hidden = State()

    assert "_hidden" in caplog.text


def test_pd24_relative_state_restore_does_not_warn(caplog):
    class M(StateMachine):
        a = State(initial=True)
        b = State()
        go = a.to(b)

    with caplog.at_level(logging.WARNING):
        m = M(state="b")
    assert m.state == "b"
    assert "Lookup will fail" not in caplog.text
    m.stop()
