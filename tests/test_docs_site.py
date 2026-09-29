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
    before anyone noticed. Pin the LATEST section body -- whatever heading
    it carries ([Unreleased] before a release, [x.y.z] after) -- so the
    two never drift again, across releases."""

    _HEAD = re.compile(r"^## \[([^\]]+)\].*$", re.M)

    def _latest(self, text: str) -> "tuple[str, str]":
        heads = list(self._HEAD.finditer(text))
        # Skip an empty [Unreleased] placeholder right after a release.
        for k, h in enumerate(heads):
            body = text[h.end() : heads[k + 1].start()]
            if body.strip() and body.strip() != "Nothing yet.":
                body = body.rsplit("For full details", 1)[0]
                return h.group(1), body.strip().rstrip("-").strip()
        raise AssertionError("no changelog section with content")

    def test_latest_sections_are_identical(self) -> None:
        root = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        guide = (GUIDE / "changelog.md").read_text(encoding="utf-8")
        rv, rb = self._latest(root)
        gv, gb = self._latest(guide)
        self.assertEqual(rv, gv, "guide changelog is on a different version")
        # The guide page may add ONE intro line under the heading.
        gb_lines = [ln for ln in gb.splitlines() if ln.strip()]
        rb_lines = [ln for ln in rb.splitlines() if ln.strip()]
        if (
            gb_lines
            and gb_lines[0].startswith("**")
            and gb_lines[0] not in rb_lines
        ):
            gb_lines = gb_lines[1:]
        self.assertEqual(rb_lines, gb_lines)


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


class TestIntegrationsSection(unittest.TestCase):
    """The Integrations guide (#258) and the page template every extra copies.

    🏛️ Later integration pages are asserted here as they land: each must
    carry the Guarantees and Threat-model boxes (X0.17, #303) -- add the
    page name to `INTEGRATION_PAGES` when its issue ships.
    """

    INTEGRATION_PAGES: tuple = (
        "integration-redis",  # #306
        "integration-pydantic",  # #266
        "integration-starlette",  # #275
        "integration-fastapi",  # #276
        "integration-litestar",  # #278
        "integration-sqlalchemy",  # #284
        "integration-flask",  # #285
        "integration-agents",  # #287, #290
        "integration-testing",  # #268
    )

    def test_overview_page_exists_and_is_in_nav(self) -> None:
        page = GUIDE / "integrations.md"
        self.assertTrue(page.is_file(), page)
        text = _read(page)
        self.assertIn("zero runtime dependencies", text)
        self.assertIn("missingextraerror", text)  # _read lower-cases
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        self.assertIn("/guide/integrations/", layout)
        self.assertIn("stately-export,integrations,", layout)  # pages_order

    def test_overview_lists_every_registry_extra(self) -> None:
        from src.xstate_statemachine.contrib._registry import EXTRAS

        # 📝 #309: the extras table moved off the journey page.
        text = _read(GUIDE / "integrations-extras.md")
        missing = [f"`{name}`" for name in EXTRAS if f"`{name}`" not in text]
        self.assertEqual(missing, [], f"extras not documented: {missing}")

    def test_integration_pages_have_the_mandatory_boxes(self) -> None:
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        for page in self.INTEGRATION_PAGES:
            text = _read(GUIDE / f"{page}.md")
            for section in (
                "## install",
                "## quick start",
                "## reference",
                "## guarantees",
                "## threat model",
                "## compatibility",
                "## troubleshooting",
            ):
                self.assertIn(section, text, f"{page}: {section}")
            self.assertIn("**what this does not do:**", text, page)
            self.assertIn("**you must configure:**", text, page)
            self.assertIn(f"/guide/{page}/", layout, f"{page} not in sidebar")
            self.assertIn(f"{page},", layout, f"{page} not in pages_order")

    def test_template_has_the_mandatory_boxes(self) -> None:
        tpl = _read(ROOT / "docs" / "_templates" / "integration-page.md")
        for section in (  # _read lower-cases
            "## install",
            "## quick start",
            "## reference",
            "## guarantees",
            "## threat model",
            "## compatibility",
            "## troubleshooting",
        ):
            self.assertIn(section, tpl)

    def test_every_shipped_integration_page_has_both_boxes(self) -> None:
        for name in self.INTEGRATION_PAGES:
            text = _read(GUIDE / f"{name}.md")
            self.assertIn("## guarantees", text, name)
            self.assertIn("## threat model", text, name)


class TestAdoptionKitPages(unittest.TestCase):
    """#309: the journey page, the extras page and the Stately page."""

    PAGES = ("integrations-extras", "stately-export")

    def test_new_pages_are_in_nav_order_and_search(self) -> None:
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        index = _read(ROOT / "docs" / "assets" / "js" / "search-index.json")
        for page in self.PAGES:
            self.assertTrue((GUIDE / f"{page}.md").is_file(), page)
            self.assertIn(f"/guide/{page}/", layout, f"{page} not in sidebar")
            self.assertIn(f"{page},", layout, f"{page} not in pages_order")
            self.assertIn(f"/guide/{page}/", index, f"{page} not searchable")

    def test_journey_has_the_four_sections_and_a_mermaid_tree(self) -> None:
        text = _read(GUIDE / "integrations.md")
        for section in (
            "## pick your path",
            "## 15-minute tutorial",
            "## what you get / what you don't",
            "## where next",
        ):
            self.assertIn(section, text)
        self.assertIn("```mermaid", text)
        self.assertIn("../guarantees/", text)
        self.assertIn("../security/", text)
        # 📝 Unshipped steps are prose with their issue, never fake code.
        self.assertIn("#270", text)
        self.assertIn("#274", text)

    def test_stately_page_marks_planned_meta_conventions(self) -> None:
        text = _read(GUIDE / "stately-export.md")
        self.assertIn("meta.publish", text)
        self.assertIn("meta.tools", text)
        self.assertIn("planned", text)
        self.assertIn(
            '"filematch": ["*.machine.json"]', text
        )  # _read lower-cases


class TestRecipesSection(unittest.TestCase):
    """#308: the recipes index and every recipe page exist, are in the
    sidebar, `pages_order` and the search index, and are linked from the
    README Cookbook and the Integrations journey page."""

    RECIPES = GUIDE / "recipes"
    PAGES = (
        "recipes",
        "stripe-webhooks",
        "apscheduler-timers",
        "task-queue-workers",
        "form-wizard",
        "slot-filling",
        "feature-flag-rollout",
        "websocket-reconnect",
        "circuit-breaker-retry",
    )

    def test_every_page_exists_and_is_in_nav_and_search(self) -> None:
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        index = _read(ROOT / "docs" / "assets" / "js" / "search-index.json")
        self.assertIn('<h3 class="sidebar-heading">recipes</h3>', layout)
        for page in self.PAGES:
            path = self.RECIPES / f"{page}.md"
            self.assertTrue(path.is_file(), path)
            self.assertIn(f"permalink: /guide/{page}/", _read(path))
            self.assertIn(f"/guide/{page}/", layout, f"{page} not in sidebar")
            self.assertIn(f"{page},", layout, f"{page} not in pages_order")
            self.assertIn(f"/guide/{page}/", index, f"{page} not searchable")

    def test_index_is_linked_from_readme_cookbook_and_integrations(
        self,
    ) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        cookbook = readme.split("## 📚 Cookbook", 1)[1].split("\n## ", 1)[0]
        self.assertIn("xstate-statemachine/guide/recipes/", cookbook)
        journey = _read(GUIDE / "integrations.md")
        where_next = journey.split("## where next", 1)[1]
        self.assertIn("](../recipes/)", where_next)
        self.assertIn("](../vs-step-functions/)", where_next)


class TestSecurityBaseline(unittest.TestCase):
    """X0.1 + X0.3 (#303): the trust model and the crash-consistency spec
    are published, cross-linked, in the nav, and every X0 item is mapped
    to evidence."""

    def test_root_security_md_states_the_trust_model(self) -> None:
        text = _read(ROOT / "SECURITY.md")
        for needle in (
            "## reporting a vulnerability",
            "## trust model",
            "installed packages are fully trusted",
            "events and snapshots are not",
            "never pickle",
            "principal=",
            "#303",
        ):
            self.assertIn(needle, text, needle)

    def test_security_page_maps_every_x0_item(self) -> None:
        text = _read(GUIDE / "security.md")
        for n in range(1, 18):
            self.assertIn(f"| x0.{n} |", text, f"X0.{n} row missing")
        self.assertIn("job **`audit`**", text)
        self.assertIn("../guarantees/", text)

    def test_guarantees_page_specifies_order_and_crash_windows(self) -> None:
        text = _read(GUIDE / "guarantees.md")
        self.assertIn("## the order of operations", text)
        self.assertIn("## crash windows, one by one", text)
        self.assertIn("## the `processed_ids` ring", text)
        self.assertIn("at least once", text)
        self.assertIn("exactly once", text)
        # 📝 every crash-window row names a test; the tests must exist.
        named = re.findall(r"`(test_[a-z_]+\.py)::", text)
        self.assertTrue(named)
        all_tests = {p.name for p in (ROOT / "tests").rglob("test_*.py")}
        self.assertEqual(sorted(set(named) - all_tests), [])

    def test_both_pages_are_in_nav_and_linked(self) -> None:
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        for page in ("security", "guarantees"):
            self.assertIn(f"/guide/{page}/", layout, f"{page} not in sidebar")
            self.assertIn(f"{page},", layout, f"{page} not in pages_order")
        # the integration template points readers at the spec, not the issue
        tpl = _read(ROOT / "docs" / "_templates" / "integration-page.md")
        self.assertIn("(../guarantees/)", tpl)


class TestPythonLibraryComparisonPages(unittest.TestCase):
    """#286: the three comparison pages exist, are in nav and search, and
    are reachable from the README, the landing page and the journey."""

    PAGES = ("vs-django-fsm", "vs-transitions", "vs-python-statemachine")

    def test_pages_exist_and_are_linked_everywhere(self) -> None:
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        index = _read(ROOT / "docs" / "assets" / "js" / "search-index.json")
        readme = _read(ROOT / "README.md")
        landing = _read(ROOT / "docs" / "index.html")
        journey = _read(GUIDE / "integrations.md")
        for page in self.PAGES:
            self.assertTrue(
                (GUIDE / "comparisons" / f"{page}.md").is_file(), page
            )
            self.assertIn(f"/guide/{page}/", layout, f"{page} not in sidebar")
            self.assertIn(f"{page},", layout, f"{page} not in pages_order")
            self.assertIn(f"/guide/{page}/", index, f"{page} not searchable")
            self.assertIn(f"/guide/{page}/", readme, f"{page} not in README")
            self.assertIn(f"/guide/{page}/", landing, f"{page} not landing")
            self.assertIn(f"../{page}/", journey, f"{page} not in journey")


class TestHardeningPages(unittest.TestCase):
    """#296: the generated compatibility table and the deprecation policy
    are published, in nav and search, and linked from where readers look."""

    PAGES = ("compatibility", "deprecation-policy")

    def test_pages_exist_in_nav_and_search(self) -> None:
        layout = _read(ROOT / "docs" / "_layouts" / "default.html")
        index = _read(ROOT / "docs" / "assets" / "js" / "search-index.json")
        for page in self.PAGES:
            self.assertTrue((GUIDE / f"{page}.md").is_file(), page)
            self.assertIn(f"/guide/{page}/", layout, f"{page} not in sidebar")
            self.assertIn(f"{page},", layout, f"{page} not in pages_order")
            self.assertIn(f"/guide/{page}/", index, f"{page} not searchable")

    def test_compatibility_table_is_generated_and_current(self) -> None:
        import sys

        sys.path.insert(0, str(ROOT / "scripts"))
        import gen_compatibility as gen

        page = (GUIDE / "compatibility.md").read_text(encoding="utf-8")
        self.assertIn("GENERATED by scripts/gen_compatibility.py", page)
        self.assertEqual(page, gen.render(gen.load()))
        for name, e in gen.load().items():
            self.assertIn(f"`[{name}]`", page)
            self.assertIn(e["oldest"].split("==")[1], page)

    def test_readme_links_both(self) -> None:
        readme = _read(ROOT / "README.md")
        for page in self.PAGES:
            self.assertIn(f"/guide/{page}/", readme)

    def test_extras_page_links_compatibility(self) -> None:
        self.assertIn(
            "../compatibility/", _read(GUIDE / "integrations-extras.md")
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
