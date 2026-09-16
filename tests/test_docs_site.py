# tests/test_docs_site.py
# -----------------------------------------------------------------------------
# 🏛️ #53 + #56: the production-characteristics documentation is load-bearing
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: these facts (one loop per process, best-effort
# timers, the SyncInterpreter threading contract) cannot be inferred from
# the API and were learned the hard way by a production adopter. Docs can
# rot silently; a test that greps for the load-bearing statements cannot.
# The keyword sets mirror the filer's repro (LC-53) so this suite and that
# script agree on what "documented" means.
# -----------------------------------------------------------------------------
"""The guide states the runtime's production characteristics (#53, #56)."""

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "_guide"
PAGE = GUIDE / "production-characteristics.md"


def _read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").lower()


class TestProductionCharacteristicsPage(unittest.TestCase):
    def test_production_characteristics_page_exists(self) -> None:
        self.assertTrue(PAGE.is_file(), PAGE)

    def test_scaling_guide_page_exists_and_mentions_single_event_loop(
        self,
    ) -> None:
        body = _read(PAGE)
        self.assertRegex(body, r"one asyncio event loop on one os thread")
        self.assertIn("per-process budget", body)
        self.assertIn("scale by process", body)

    def test_page_carries_measured_scaling_table(self) -> None:
        body = _read(PAGE)
        for n in ("| 1 |", "| 100 |", "| 1,000 |"):
            self.assertIn(n, body, f"scaling row {n!r} missing")
        for detail in ("cpython", "tracemalloc", "macrostep"):
            self.assertIn(detail, body, f"method detail {detail!r} missing")

    def test_production_characteristics_covers_all_three_topics(self) -> None:
        body = _read(PAGE)
        topics = {
            "timer starvation": [r"starv", r"fires? late", r"under load"],
            # #50: timers no longer own a thread; only non-blocking
            # `spawn_<key>` children do. The page must say both.
            "sync threading": [
                r"do not own a thread",
                r"caller's thread",
                r"runner thread",
            ],
            "throughput budget": [
                r"ev/s",
                r"throughput",
                r"per-process budget",
            ],
        }
        for topic, patterns in topics.items():
            with self.subTest(topic=topic):
                self.assertTrue(
                    all(re.search(p, body) for p in patterns),
                    f"{topic}: not all of {patterns} found",
                )

    def test_blocking_action_warning_present(self) -> None:
        body = _read(PAGE)
        self.assertRegex(body, r"blocking work .* stalls every machine")

    def test_benchmark_script_ships(self) -> None:
        self.assertTrue(
            (ROOT / "benchmarks" / "production_characteristics.py").is_file()
        )
        self.assertIn("benchmarks/production_characteristics.py", _read(PAGE))


class TestCrossLinks(unittest.TestCase):
    def test_readme_links_to_performance_guide(self) -> None:
        readme = _read(ROOT / "README.md")
        self.assertIn("guide/production-characteristics/", readme)

    def test_interpreter_docstring_links_to_guide(self) -> None:
        src = _read(ROOT / "src" / "xstate_statemachine" / "interpreter.py")
        self.assertIn("guide/production-characteristics/", src)

    def test_linked_from_interpreters_delayed_transitions_and_faq(
        self,
    ) -> None:
        for page in ("interpreters.md", "delayed-transitions.md", "faq.md"):
            with self.subTest(page=page):
                self.assertIn(
                    "production-characteristics", _read(GUIDE / page)
                )

    def test_in_sidebar_nav(self) -> None:
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        self.assertIn("/guide/production-characteristics/", layout)


class TestCorrectedStatements(unittest.TestCase):
    def test_sync_interpreter_thread_safety_row_mentions_timer_threads(
        self,
    ) -> None:
        body = _read(GUIDE / "interpreters.md")
        row = next(
            (
                ln
                for ln in body.splitlines()
                if ln.startswith("| thread safety")
            ),
            "",
        )
        self.assertIn("background thread", row)
        self.assertNotRegex(row, r"\|\s*single-threaded\s*\|\s*$")

    def test_delayed_transitions_says_not_before_never_at(self) -> None:
        body = _read(GUIDE / "delayed-transitions.md")
        self.assertIn('"not before", never "at"', body)
        self.assertNotIn("they fire when you next interact", body)

    def test_faq_attributes_threads_to_the_right_interpreter(self) -> None:
        body = _read(GUIDE / "faq.md")
        self.assertNotIn("unless using `interpreter` with `after`", body)
        # #50: the sync engine spawns a thread only for non-blocking children.
        self.assertIn("only a non-blocking `spawn_<key>` child", body)
        self.assertNotIn("thread per `after` timer", body)
        self.assertIn("on an unloaded loop", body)


class TestGuideChangelogMirrorsRoot(unittest.TestCase):
    """The site's changelog page diverged from CHANGELOG.md for two waves
    before anyone noticed. Pin the [Unreleased] body byte-for-byte."""

    @staticmethod
    def _unreleased(text: str) -> str:
        start = text.index("## [Unreleased]")
        end = text.index("\n## [0.7.0]")
        body = text[start:end].split("\n", 1)[1]
        # The guide page appends a "For full details" trailer + rule.
        body = body.rsplit("For full details", 1)[0]
        return body.strip().rstrip("-").strip()

    def test_unreleased_sections_are_identical(self) -> None:
        root = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        guide = (GUIDE / "changelog.md").read_text(encoding="utf-8")
        self.assertEqual(self._unreleased(root), self._unreleased(guide))


class TestPublicSurfaceMatchesDocs(unittest.TestCase):
    def test_every_exception_class_is_exported(self) -> None:
        """A user must be able to `isinstance` against every error the
        library can hand them. `RestoredError` (what `interp.error` holds
        after restoring an errored snapshot) was documented as importable
        but missing from `__all__` -- found by executing the docs."""
        import inspect

        import src.xstate_statemachine as pkg
        from src.xstate_statemachine import exceptions

        public = {
            n
            for n, c in vars(exceptions).items()
            if inspect.isclass(c)
            and issubclass(c, exceptions.XStateMachineError)
        }
        self.assertEqual(sorted(public - set(pkg.__all__)), [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
