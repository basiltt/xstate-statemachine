"""The deprecation helper and policy (#296)."""

from __future__ import annotations

import pathlib
import re
import unittest
import warnings

from xstate_statemachine import deprecations as dep
from xstate_statemachine.cli.args import resolve_template
from xstate_statemachine.events import ErrorEvent

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _call(n: int) -> int:
    count = 0
    for _ in range(n):
        # one call site, n calls
        count += dep.deprecated(
            "thing", since="0.1", removal="1.0", alternative="other"
        )
    return count


class TestHelper(unittest.TestCase):
    def setUp(self) -> None:
        dep.reset_deprecation_warnings()

    def test_once_per_call_site(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(_call(5), 1)
            # a second call site warns again
            dep.deprecated(
                "thing", since="0.1", removal="1.0", alternative="other"
            )
        self.assertEqual(len(w), 2)
        self.assertIs(w[0].category, DeprecationWarning)
        msg = str(w[0].message)
        for part in ("thing", "0.1", "1.0", "other"):
            self.assertIn(part, msg)

    def test_warning_points_at_the_caller_of_the_shim(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ErrorEvent("error.platform.x", ValueError("v"), "x").data
        self.assertEqual(w[0].filename, __file__)

    def test_error_event_data_warns_once_per_site(self) -> None:
        ev = ErrorEvent("error.platform.x", ValueError("v"), "x")
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            for _ in range(3):
                self.assertIs(ev.data, ev.error)
        self.assertEqual(len(w), 1)
        self.assertIn("ErrorEvent.error", str(w[0].message))

    def test_style_flag_uses_helper(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            self.assertEqual(resolve_template("class", None), "class-json")
        self.assertIn("--template class-json", str(w[0].message))

    def test_registry_lists_existing_deprecations(self) -> None:
        names = {d.what for d in dep.deprecations()}
        for expected in (
            "ErrorEvent.data",
            "--style",
            "leading-dot sibling target fallback",
            "strict_targets=False",
            "implicit actionErrorPolicy default 'continue'",
        ):
            self.assertIn(expected, names)

    def test_site_record_is_bounded(self) -> None:
        old = dep._SEEN_MAX
        dep._SEEN_MAX = 1
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                _call(1)
                dep.deprecated("x", since="0", removal="1", alternative="y")
            self.assertLessEqual(len(dep._SEEN), 1)
        finally:
            dep._SEEN_MAX = old


class TestPolicyDocs(unittest.TestCase):
    def test_policy_page_lists_every_registered_deprecation(self) -> None:
        page = (ROOT / "docs" / "_guide" / "deprecation-policy.md").read_text(
            encoding="utf-8"
        )
        for d in dep.deprecations():
            self.assertIn(d.what, page)
        self.assertIn("provisional", page)
        self.assertIn("next major", page)

    def test_changelog_headers_link_the_policy(self) -> None:
        for path in ("CHANGELOG.md", "docs/_guide/changelog.md"):
            head = (ROOT / path).read_text(encoding="utf-8")[:3000]
            self.assertTrue(re.search(r"deprecation-policy", head), msg=path)

    def test_readme_semver_statement_links_policy(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Semantic Versioning", readme)
        self.assertIn("deprecation-policy", readme)


if __name__ == "__main__":
    unittest.main()
