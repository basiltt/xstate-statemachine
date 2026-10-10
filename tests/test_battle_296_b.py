"""Battle #296 adversary B: the 1.0 promise as a reader sees it.

Every claim the third-party-plugin docs, SECURITY.md, README, the API index,
the deprecation policy and the compatibility page make about #296 is checked
against the code (or against real `xsm plugins` output with the fixture
distribution installed).
"""

import contextlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from xstate_statemachine import plugin_discovery as pd

from .test_plugin_discovery import install_fixture

ROOT = pathlib.Path(__file__).resolve().parents[1]
PLUGINS_MD = ROOT / "docs" / "_guide" / "plugins.md"
API = ROOT / "docs" / "api" / "index.md"


def _read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def _section(text: str, start: str, end: str) -> str:
    a = text.index(start)
    return text[a : text.index(end, a)]


def _third_party_docs() -> str:
    return _section(
        _read(PLUGINS_MD),
        "## 🔎 Third-party plugins: discovery",
        "## 📜 Complete Example",
    )


def _fences(text: str, lang: str):
    return re.findall(r"```" + lang + r"\n(.*?)```", text, re.S)


def _run_cli(fixture_dir: pathlib.Path, *args: str, disabled=False):
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(fixture_dir)])
    env["PYTHONUTF8"] = "1"
    env.pop(pd.DISABLE_ENV, None)
    if disabled:
        env[pd.DISABLE_ENV] = "1"
    return subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


class _Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._dir = tempfile.TemporaryDirectory()
        cls.tmp = pathlib.Path(cls._dir.name)
        install_fixture(cls.tmp)
        sys.path.insert(0, str(cls.tmp))

    @classmethod
    def tearDownClass(cls) -> None:
        sys.path.remove(str(cls.tmp))
        for mod in [m for m in sys.modules if m.startswith("xsm_thirdparty")]:
            del sys.modules[mod]
        cls._dir.cleanup()

    def setUp(self) -> None:
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(pd.DISABLE_ENV, None)


class TestThirdPartyPluginDocsExecute(_Fixture):
    """Every python block in the discovery/writing sections runs."""

    def test_every_python_block_runs_with_the_fixture_installed(self):
        blocks = _fences(_third_party_docs(), "python")
        self.assertGreaterEqual(len(blocks), 4)
        for src in blocks:
            with self.subTest(src=src[:60]):
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile(src, str(PLUGINS_MD), "exec"), {})

    def test_documented_calls_with_the_fixture_names(self):
        # the docs' `acme-audit` spelled as the fixture's real names
        from xstate_statemachine import SyncInterpreter, create_machine
        from xstate_statemachine.contrib.observability import instrument_all
        from xstate_statemachine.plugins import attach_discovered, discover

        names = {p.name for p in discover()}
        self.assertIn("thirdparty_audit", names)
        self.assertEqual(
            [s.name for s in pd.last_skipped], ["thirdparty_broken"]
        )
        m = create_machine({"id": "m", "initial": "a", "states": {"a": {}}})
        i = SyncInterpreter(m)
        by_dist = attach_discovered(i, allow=["xsm-thirdparty-plugin"])
        self.assertEqual([type(p).__name__ for p in by_dist], ["AuditPlugin"])
        i2 = SyncInterpreter(m)
        got = instrument_all(i2, discovered=True, allow=["thirdparty_audit"])
        self.assertEqual([type(p).__name__ for p in got], ["AuditPlugin"])
        with self.assertRaises(RuntimeError):
            discover(strict=True)

    def test_toml_block_matches_the_fixture_shape(self):
        toml = "\n".join(_fences(_third_party_docs(), "toml"))
        for group in pd.GROUPS:
            self.assertIn(f'[project.entry-points."{group}"]', toml)
        fixture = _read(
            ROOT / "tests/fixtures/xsm_thirdparty_plugin/" "pyproject.toml"
        )
        self.assertIn(
            '[project.entry-points."xstate_statemachine.plugins"]', fixture
        )


class TestXsmPluginsDocsMatchRealOutput(_Fixture):
    def test_plain_output_shape_is_the_documented_shape(self):
        doc = _section(_third_party_docs(), "$ xsm plugins --plain\n", "```")
        doc_lines = doc.splitlines()[1:]
        real = _run_cli(self.tmp, "--plain", "plugins")
        self.assertEqual(real.returncode, 0, real.stderr)
        real_lines = real.stdout.splitlines()
        # 📝 versions of the library's own brokers float; compare the rest
        norm = re.compile(r"xstate-statemachine \S+")
        self.assertEqual(
            [norm.sub("xstate-statemachine V", x) for x in doc_lines],
            [norm.sub("xstate-statemachine V", x) for x in real_lines],
        )
        self.assertTrue(real_lines[-1].split("SKIPPED:")[0].strip())

    def test_json_keys_and_skipped_entry_are_documented(self):
        real = _run_cli(self.tmp, "plugins", "--json")
        data = json.loads(real.stdout)
        doc = json.loads(_fences(_third_party_docs(), "json")[0])
        self.assertEqual(list(doc), list(data))
        self.assertEqual(doc["skipped"], data["skipped"])
        self.assertEqual(set(doc["plugins"][0]), set(data["plugins"][0]))
        self.assertIn(doc["plugins"][0], data["plugins"])

    def test_strict_exit_code_and_stderr_line_are_documented(self):
        real = _run_cli(self.tmp, "plugins", "--strict")
        self.assertEqual(real.returncode, 1)
        line = [x for x in real.stderr.splitlines() if x.startswith("error:")]
        self.assertEqual(len(line), 1)
        self.assertNotIn("Traceback", real.stderr)
        self.assertIn(line[0], _third_party_docs())
        ok = _run_cli(self.tmp, "plugins")
        self.assertEqual(ok.returncode, 0)  # SKIPPED rows still exit 0
        self.assertIn("exits 0", _third_party_docs().replace("exit **`1`", ""))

    def test_disabled_message_is_documented(self):
        real = _run_cli(self.tmp, "--plain", "plugins", disabled=True)
        self.assertIn(real.stdout.strip(), _third_party_docs())

    def test_help_mentions_json_and_strict(self):
        real = _run_cli(self.tmp, "plugins", "--help")
        for flag in ("--json", "--strict"):
            self.assertIn(flag, real.stdout)


class TestApiIndexRows(unittest.TestCase):
    def test_every_plugin_discovery_name_has_a_row(self):
        text = _read(API)
        for name in [*pd.__all__, "hooks_of"]:
            with self.subTest(name=name):
                self.assertRegex(text, r"\| `[^|]*\b" + name + r"\b")

    def test_every_deprecations_name_has_a_row(self):
        from xstate_statemachine import deprecations as dep

        text = _read(API)
        for name in dep.__all__:
            self.assertRegex(text, r"\| `" + name + r"\b")

    def test_cli_line_names_strict_not_a_nonexistent_flag(self):
        text = _read(API)
        self.assertIn("xsm plugins [--json] [--strict]", text)


class TestPromiseConsistency(unittest.TestCase):
    def test_policy_page(self):
        text = _read(ROOT / "docs/_guide/deprecation-policy.md")
        self.assertIn("once per call site", text)
        self.assertIn("-W error::DeprecationWarning", text)
        self.assertIn("still provisional *in* 1.0", text)
        head = "\n".join(_read(ROOT / "CHANGELOG.md").splitlines()[:12])
        self.assertIn("guide/deprecation-policy/", head)

    def test_security_trust_model_and_versions(self):
        text = _read(ROOT / "SECURITY.md")
        for phrase in (
            "in-process with full privileges",
            "never discovers implicitly",
            "allow=",
            "XSM_DISABLE_PLUGIN_DISCOVERY",
            "private vulnerability reporting",
            "Semantic Versioning",
        ):
            self.assertIn(phrase, text)
        # 📝 the supported-versions table names the current minor
        pyproject = _read(ROOT / "pyproject.toml")
        ver = re.search(r'^version = "(\d+)\.(\d+)', pyproject, re.M)
        self.assertIn(f"{ver.group(1)}.{ver.group(2)}.x", text)

    def test_readme_semver_python_and_all(self):
        text = _read(ROOT / "README.md")
        self.assertIn("Semantic Versioning", text)
        self.assertIn("**provisional**", text)
        self.assertIn("Supported Python: 3.9 – 3.14", text)
        self.assertIn("xstate-statemachine[all]", text)
        py = re.search(
            r'requires-python = ">=(3\.\d+)"', _read(ROOT / "pyproject.toml")
        )
        self.assertEqual(py.group(1), "3.9")

    def test_compat_page_names_its_source_commit_rule(self):
        text = _read(ROOT / "docs/_guide/compatibility.md")
        self.assertIn("GENERATED by scripts/gen_compatibility.py", text)
        self.assertIn("asserted", text)
        stamp = re.search(
            r"Matrix verified: (\d{4}-\d\d-\d\d), commit (\w+)", text
        )
        self.assertIsNotNone(stamp)
        ok = subprocess.run(
            ["git", "cat-file", "-e", stamp.group(2) + "^{commit}"],
            cwd=ROOT,
            capture_output=True,
        )
        if ok.returncode not in (0, 128):  # pragma: no cover
            self.skipTest("git unavailable")
        self.assertEqual(ok.returncode, 0, "stamp names an unknown commit")

    def test_table_pins_are_the_pins_ci_installs(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        try:
            import gen_compatibility as gc
        finally:
            sys.path.remove(str(ROOT / "scripts"))
        extras = gc.load()
        page = _read(ROOT / "docs/_guide/compatibility.md")
        wf = _read(ROOT / ".github/workflows/compat.yml")
        self.assertIn("gen_compatibility.py --pip-args", wf)
        for name, e in extras.items():
            with self.subTest(extra=name):
                old = gc.pip_args(extras, name, "oldest")
                new = gc.pip_args(extras, name, "newest")
                self.assertIn(e["oldest"], old)
                self.assertIn(e["newest"], new)
                self.assertIn(f"**{e['oldest'].split('==')[1]}**", page)
                self.assertIn(f"latest `{e['newest']}`", page)
                for pin in e.get("extra_pins", []):
                    self.assertIn(pin, old)
                    self.assertIn(f"`{pin}`", page)

    def test_agents_ranges_match_the_code_and_ci(self):
        from xstate_statemachine.contrib.agents.langgraph import (
            LANGGRAPH_TESTED,
        )
        from xstate_statemachine.contrib.agents.pydantic_ai import (
            PYDANTIC_AI_TESTED,
        )

        doc = _read(ROOT / "docs/_guide/integration-agents.md")
        (a, b), (c, _) = LANGGRAPH_TESTED
        self.assertIn(f"`>={a}.{b},<{c}.0` (`LANGGRAPH_TESTED`)", doc)
        (a, b), (c, _) = PYDANTIC_AI_TESTED
        self.assertIn(f"`>={a}.{b},<{c}`", doc)
        ci = _read(ROOT / ".github/workflows/ci.yml")
        lg = LANGGRAPH_TESTED
        self.assertIn(f'"langgraph>={lg[0][0]}.{lg[0][1]},<{lg[1][0]}"', ci)

    def test_deprecated_and_removed_entries_name_a_replacement(self):
        text = _read(ROOT / "CHANGELOG.md")
        start = text.index("## [Unreleased]")
        end = text.index("## [0.7.0]")
        sections = re.findall(
            r"### (Deprecated|Removed)\n(.*?)(?=\n### |\n## )",
            text[start:end],
            re.S,
        )
        self.assertTrue(sections)
        cue = re.compile(
            r"superseded|naming|use |instead|replac|→|->|flips to|"
            r"removed in|alternative",
            re.I,
        )
        for kind, body in sections:
            for entry in re.split(r"\n- ", body):
                if entry.strip():
                    with self.subTest(kind=kind, entry=entry[:60]):
                        self.assertRegex(entry, cue)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
