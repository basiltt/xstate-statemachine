# tests/tests_cli/test_naming.py
"""Tests for collision-free identifier allocation (M4)."""

import keyword
import unittest

from src.xstate_statemachine.cli.naming import (
    IdentifierAllocator,
    literal,
    to_identifier,
)


class TestToIdentifier(unittest.TestCase):
    """Shape-level conversion of arbitrary names."""

    def test_camel_to_snake_never_returns_a_keyword(self) -> None:
        """A chart may name a guard `and` / `not` / `class` -- the engine
        accepts a bare-string keyword as a user predicate. `safe_identifier`
        suffixes `_` but `camel_to_snake` used to strip it again, so the
        typed template emitted `def and(...)` (SyntaxError, DebtState_v4)."""
        from src.xstate_statemachine.cli.strategies._shared import (
            safe_identifier,
        )
        from src.xstate_statemachine.cli.utils import camel_to_snake

        for word in ("and", "not", "or", "class", "None"):
            with self.subTest(word=word):
                for candidate in (
                    camel_to_snake(word),
                    camel_to_snake(safe_identifier(word)),
                ):
                    self.assertFalse(keyword.iskeyword(candidate), candidate)
                    self.assertTrue(candidate.isidentifier(), candidate)
        self.assertEqual(camel_to_snake("isReady"), "is_ready")  # unchanged

    def test_bare_string_operator_name_is_a_guard(self) -> None:
        """`parse_guard("and").leaf_names()` must yield `and`: only the dict
        form declares composition (models.GuardDefinition). Dropping it made
        `stub_logic(raw_cfg)` disagree with `stub_logic(machine)` and the
        engine raised ImplementationMissingError."""
        from src.xstate_statemachine.cli.ir import parse_guard

        self.assertEqual(parse_guard("and").leaf_names(), ("and",))
        self.assertEqual(
            parse_guard(
                {"type": "and", "params": {"guards": ["a", "b"]}}
            ).leaf_names(),
            ("a", "b"),
        )
        self.assertEqual(parse_guard("!x").leaf_names(), ("x",))

    def test_keywords_are_suffixed(self) -> None:
        """Defect #7: `None = none` was a hard SyntaxError."""
        for word in ("class", "None", "return", "lambda", "import"):
            with self.subTest(word=word):
                result = to_identifier(word)
                self.assertFalse(keyword.iskeyword(result))
                self.assertTrue(result.isidentifier())

    def test_soft_keywords_are_suffixed(self) -> None:
        """`match`/`case`/`type` are legal but hostile as bindings."""
        self.assertEqual(to_identifier("match"), "match_")
        self.assertEqual(to_identifier("type"), "type_")

    def test_leading_digit_is_prefixed(self) -> None:
        """Identifiers may not begin with a digit."""
        self.assertEqual(to_identifier("2fast"), "s_2fast")

    def test_punctuation_becomes_underscores(self) -> None:
        """Hyphens and dots are not valid in identifiers."""
        self.assertEqual(to_identifier("my-state"), "my_state")
        self.assertEqual(to_identifier("a.b.c"), "a_b_c")

    def test_accents_are_transliterated_not_destroyed(self) -> None:
        """`café` should stay readable rather than becoming `caf_`."""
        self.assertEqual(to_identifier("café"), "cafe")

    def test_non_ascii_scripts_fall_back(self) -> None:
        """CJK/emoji have no ASCII skeleton; the fallback must be valid."""
        for name in ("状態", "🎉", "   "):
            with self.subTest(name=name):
                result = to_identifier(name)
                self.assertTrue(result.isidentifier())

    def test_every_result_is_a_valid_identifier(self) -> None:
        """Total function: no input may produce invalid Python."""
        hostile = ["", "-", "___", "1", "class", "a b", "?!", "état", "🎉x"]
        for name in hostile:
            with self.subTest(name=name):
                result = to_identifier(name)
                self.assertTrue(
                    result.isidentifier(), f"{name!r} -> {result!r}"
                )
                self.assertFalse(keyword.iskeyword(result))


class TestIdentifierAllocator(unittest.TestCase):
    """Uniqueness guarantees -- the heart of defect #3."""

    def test_colliding_names_get_distinct_bindings(self) -> None:
        """Defect #3: two states silently collapsed into one variable.

        `"my-state"` and `"my_state"` both sanitised to `my_state`, so the
        second assignment destroyed the first -- and in the reproducer the
        casualty was the machine's initial state.
        """
        alloc = IdentifierAllocator()
        first = alloc.allocate("my-state")
        second = alloc.allocate("my_state")
        third = alloc.allocate("my state")
        self.assertEqual(len({first, second, third}), 3)

    def test_allocation_is_stable(self) -> None:
        """Asking twice for the same source name yields the same binding."""
        alloc = IdentifierAllocator()
        self.assertEqual(
            alloc.allocate("my-state"), alloc.allocate("my-state")
        )

    def test_reserved_names_are_never_handed_out(self) -> None:
        """Module-level imports must not be shadowed by state bindings."""
        alloc = IdentifierAllocator(reserved=frozenset({"State", "logger"}))
        self.assertNotEqual(alloc.allocate("State"), "State")
        self.assertNotEqual(alloc.allocate("logger"), "logger")

    def test_many_unicode_states_stay_unique(self) -> None:
        """Names that all reduce to the same skeleton must still differ."""
        alloc = IdentifierAllocator()
        bindings = [alloc.allocate(n) for n in ("状態", "状况", "🎉", "🚀")]
        self.assertEqual(len(set(bindings)), 4)

    def test_get_and_contains(self) -> None:
        """Lookup helpers reflect allocation state."""
        alloc = IdentifierAllocator()
        self.assertIsNone(alloc.get("x"))
        self.assertNotIn("x", alloc)
        alloc.allocate("x")
        self.assertEqual(alloc.get("x"), "x")
        self.assertIn("x", alloc)


class TestLiteral(unittest.TestCase):
    """Embedding values in generated source."""

    def test_quotes_and_backslashes_survive_round_trip(self) -> None:
        """Hand-rolled escaping broke on mixed quotes and backslashes."""
        for value in ['say "hi"', "it's", "back\\slash", "line\nbreak", "🎉"]:
            with self.subTest(value=value):
                self.assertEqual(eval(literal(value)), value)  # noqa: S307

    def test_non_string_values(self) -> None:
        """Numbers, booleans and containers round-trip too."""
        for value in (1, 1.5, True, None, [1, 2], {"a": 1}):
            with self.subTest(value=value):
                self.assertEqual(eval(literal(value)), value)  # noqa: S307


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
