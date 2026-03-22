# tests/test_pythonic.py
"""Tests for the Pythonic API layer."""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import unittest

# -------------------------------------------------------------------------
# 📥 Project-Specific Imports
# -------------------------------------------------------------------------
from xstate_statemachine.pythonic import _snake_to_camel, State


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
