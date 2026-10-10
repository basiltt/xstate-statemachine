"""Entry-point plugin discovery (#296).

🏛️ The fixture package in ``tests/fixtures/xsm_thirdparty_plugin`` is made
visible through a temporary ``.dist-info`` generated from ITS OWN
``pyproject.toml`` (no pip, no network, identical on Windows and Linux):
``importlib.metadata`` finds distributions by scanning ``sys.path``, which is
exactly what an installed package looks like to it.
"""

from __future__ import annotations

import configparser
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Dict, List
from unittest import mock

from xstate_statemachine import SyncInterpreter, create_machine
from xstate_statemachine import plugin_discovery as pd
from xstate_statemachine.plugins import (
    PLUGINS_GROUP,
    STORES_GROUP,
    DiscoveredPlugin,
    attach_discovered,
    discover,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "xsm_thirdparty_plugin"
SRC = ROOT / "src"


def _entry_points_from_pyproject() -> Dict[str, Dict[str, str]]:
    """Parse the fixture's ``[project.entry-points."group"]`` tables."""
    groups: Dict[str, Dict[str, str]] = {}
    current = None
    text = (FIXTURE / "pyproject.toml").read_text(encoding="utf-8")
    for line in text.splitlines():
        head = re.match(r'\[project\.entry-points\."([^"]+)"\]', line)
        if head:
            current = groups.setdefault(head.group(1), {})
            continue
        if line.startswith("["):
            current = None
            continue
        kv = re.match(r'(\w+)\s*=\s*"([^"]+)"', line)
        if current is not None and kv:
            current[kv.group(1)] = kv.group(2)
    return groups


def install_fixture(target: pathlib.Path) -> None:
    """Lay the fixture out in *target* as an installed distribution."""
    shutil.copytree(
        FIXTURE / "xsm_thirdparty_plugin", target / "xsm_thirdparty_plugin"
    )
    info = target / "xsm_thirdparty_plugin-1.2.3.dist-info"
    info.mkdir()
    (info / "METADATA").write_text(
        "Metadata-Version: 2.1\nName: xsm-thirdparty-plugin\n"
        "Version: 1.2.3\n",
        encoding="utf-8",
    )
    cp = configparser.ConfigParser(delimiters=("=",))
    cp.optionxform = str  # type: ignore[assignment,method-assign]
    for group, entries in _entry_points_from_pyproject().items():
        cp[group] = entries
    with open(info / "entry_points.txt", "w", encoding="utf-8") as fh:
        cp.write(fh)


class _FixtureOnPath(unittest.TestCase):
    tmp: pathlib.Path

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


class TestDiscover(_FixtureOnPath):
    def test_finds_fixture_with_distribution_version_and_hooks(self) -> None:
        with self.assertLogs("xstate_statemachine", "WARNING"):
            found = discover()
        by_name = {p.name: p for p in found}
        self.assertIn("thirdparty_audit", by_name)
        p = by_name["thirdparty_audit"]
        self.assertIsInstance(p, DiscoveredPlugin)
        self.assertEqual(p.distribution, "xsm-thirdparty-plugin")
        self.assertEqual(p.version, "1.2.3")
        self.assertEqual(p.hooks, ("on_interpreter_start", "on_transition"))
        self.assertEqual(p.group, PLUGINS_GROUP)

    def test_broken_loader_is_logged_and_skipped(self) -> None:
        with self.assertLogs("xstate_statemachine", "WARNING") as logs:
            names = [p.name for p in discover()]
        self.assertNotIn("thirdparty_broken", names)
        self.assertIn("thirdparty_broken", "\n".join(logs.output))

    def test_strict_reraises_the_loader_error(self) -> None:
        with self.assertRaises(RuntimeError):
            discover(strict=True)

    def test_allow_filters_before_import(self) -> None:
        found = discover(allow=["thirdparty_audit"])
        self.assertEqual([p.name for p in found], ["thirdparty_audit"])
        by_dist = discover(allow=["some-other-dist"])
        self.assertEqual(by_dist, [])

    def test_stores_group_is_discovered_not_instantiated(self) -> None:
        found = discover(group=STORES_GROUP)
        self.assertEqual([p.name for p in found], ["thirdparty_memory"])
        self.assertIsInstance(found[0].obj, type)
        self.assertEqual(found[0].hooks, ())

    def test_env_switch_disables_discovery(self) -> None:
        os.environ[pd.DISABLE_ENV] = "1"
        self.assertEqual(discover(), [])
        self.assertEqual(discover(strict=True), [])

    def test_attach_discovered_uses_the_plugin(self) -> None:
        m = create_machine(
            {
                "id": "m",
                "initial": "a",
                "states": {"a": {"on": {"GO": "b"}}, "b": {}},
            }
        )
        it = SyncInterpreter(m)
        attached = attach_discovered(it, allow=["thirdparty_audit"])
        self.assertEqual(len(attached), 1)
        it.start()
        it.send("GO")
        it.stop()
        self.assertEqual(attached[0].started, ["m"])
        self.assertIn(["m", "m.b"], attached[0].transitions)


class TestShim(unittest.TestCase):
    def test_py39_dict_shape_is_selected_by_key(self) -> None:
        sentinel = object()

        class FakeDict(dict):
            pass

        fake = FakeDict({PLUGINS_GROUP: [sentinel]})
        with mock.patch("importlib.metadata.entry_points", return_value=fake):
            self.assertEqual(pd._entry_points(PLUGINS_GROUP), [sentinel])
            self.assertEqual(pd._entry_points("nope"), [])

    def test_hooks_of_non_plugin_is_empty(self) -> None:
        self.assertEqual(pd.hooks_of(object), ())
        self.assertEqual(pd.hooks_of(len), ())

    def test_attach_skips_a_failing_constructor(self) -> None:
        @pd.plugin_factory
        def boom() -> None:
            raise ValueError("x")

        found = [DiscoveredPlugin("b", "d", "1", boom, ())]
        it = mock.Mock()
        with mock.patch.object(pd, "discover", return_value=found):
            with self.assertLogs("xstate_statemachine", "WARNING"):
                self.assertEqual(attach_discovered(it), [])
            with self.assertRaises(ValueError):
                attach_discovered(it, strict=True)
        it.use.assert_not_called()


class TestNothingOnImport(unittest.TestCase):
    def test_import_does_not_load_entry_points(self) -> None:
        code = (
            "import sys, importlib.metadata as md\n"
            "calls=[]\n"
            "orig=md.entry_points\n"
            "md.entry_points=lambda *a, **k: calls.append(1) or orig(*a, **k)\n"
            "import xstate_statemachine, xstate_statemachine.plugins\n"
            "print(len(calls))\n"
        )
        env = dict(os.environ, PYTHONPATH=str(SRC))
        out = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        self.assertEqual(out.stdout.strip(), "0")


class TestCli(_FixtureOnPath):
    def _run(self, *args: str, **env: str) -> subprocess.CompletedProcess:
        full_env = dict(os.environ)
        full_env.pop(pd.DISABLE_ENV, None)
        full_env.update(env)
        full_env["PYTHONPATH"] = os.pathsep.join([str(self.tmp), str(SRC)])
        return subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", "plugins", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=full_env,
            check=True,
        )

    def test_json_lists_fixture(self) -> None:
        data = json.loads(self._run("--json").stdout)
        rows: List[dict] = data["plugins"]
        audit = next(r for r in rows if r["name"] == "thirdparty_audit")
        self.assertEqual(audit["distribution"], "xsm-thirdparty-plugin")
        self.assertEqual(audit["version"], "1.2.3")
        self.assertEqual(audit["group"], PLUGINS_GROUP)
        self.assertEqual(
            audit["hooks"], ["on_interpreter_start", "on_transition"]
        )
        self.assertIn("thirdparty_memory", [r["name"] for r in rows])
        self.assertNotIn("thirdparty_broken", [r["name"] for r in rows])

    def test_plain_output(self) -> None:
        out = self._run("--plain").stdout
        self.assertIn("thirdparty_audit  xsm-thirdparty-plugin 1.2.3", out)
        self.assertIn("hooks: on_interpreter_start, on_transition", out)

    def test_disabled(self) -> None:
        out = self._run("--plain", XSM_DISABLE_PLUGIN_DISCOVERY="1").stdout
        self.assertIn("disabled", out)


if __name__ == "__main__":
    unittest.main()
