"""Tests for `xsm update`. Network and pip are never touched: `fetch_latest`,
`detect_install` and `_run` are patched at the module seam."""

from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from typing import List
from unittest import mock

import src.xstate_statemachine.cli.commands as cmds
from src.xstate_statemachine import __version__
from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands import update as U
from src.xstate_statemachine.cli.ui import Capabilities, Console


def _run(argv: List[str]) -> tuple:
    reset_console()
    saved, sys.argv = sys.argv, ["xsm", *argv]
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code or 0
    finally:
        sys.argv = saved
        reset_console()
    return code, buf.getvalue()


def _pip(python: str = "py") -> U.InstallInfo:
    return U.InstallInfo(
        "pip",
        "pip",
        "/site-packages",
        python,
        [python, "-m", "pip", "install", "--upgrade", U.DIST],
    )


class TestVersionArithmetic(unittest.TestCase):
    def test_ordering(self) -> None:
        order = [
            "0.9.0",
            "0.9.1",
            "0.10.0a1",
            "0.10.0b2",
            "0.10.0rc1",
            "0.10.0",
            "1.0.0",
        ]
        for a, b in zip(order, order[1:]):
            self.assertTrue(U.is_newer(b, a), (a, b))
            self.assertFalse(U.is_newer(a, b), (a, b))
        self.assertFalse(U.is_newer("0.10.0", "0.10.0"))
        self.assertTrue(U.is_newer("0.10.0", "0.10.0.dev3"))
        self.assertTrue(U.is_newer("v0.10.1", "0.10.0"))


class TestDetectInstall(unittest.TestCase):
    def _dist(
        self,
        installer: str,
        direct: str = "",
        location: str = "/venv/lib/site-packages",
    ):
        d = mock.MagicMock()
        d.read_text.side_effect = lambda n: {
            "INSTALLER": installer,
            "direct_url.json": direct,
        }.get(n)
        d.locate_file.return_value = location
        return d

    def test_pip(self) -> None:
        with mock.patch.object(
            U.metadata, "distribution", return_value=self._dist("pip")
        ):
            info = U.detect_install("py")
        self.assertEqual(info.kind, "pip")
        self.assertEqual(info.command[:4], ["py", "-m", "pip", "install"])

    def test_editable_is_refused(self) -> None:
        direct = json.dumps(
            {"dir_info": {"editable": True}, "url": "file:///C:/src/x"}
        )
        with mock.patch.object(
            U.metadata, "distribution", return_value=self._dist("pip", direct)
        ):
            info = U.detect_install("py")
        self.assertEqual(info.kind, "editable")
        self.assertFalse(info.upgradable)
        self.assertEqual(info.location, "C:/src/x")
        self.assertIn("git", info.reason)

    def test_pipx_and_uv_tool(self) -> None:
        with mock.patch.object(
            U.metadata,
            "distribution",
            return_value=self._dist(
                "pip", location="/home/u/.local/pipx/venvs/xsm/lib"
            ),
        ):
            self.assertEqual(
                U.detect_install().command, ["pipx", "upgrade", U.DIST]
            )
        with mock.patch.object(
            U.metadata,
            "distribution",
            return_value=self._dist(
                "uv", location="/home/u/.local/share/uv/tools/xsm/lib"
            ),
        ):
            self.assertEqual(
                U.detect_install().command, ["uv", "tool", "upgrade", U.DIST]
            )
        with mock.patch.object(
            U.metadata, "distribution", return_value=self._dist("uv")
        ):
            self.assertEqual(
                U.detect_install().kind, "pip"
            )  # uv pip in a venv

    def test_conda_and_unknown_installers_are_refused(self) -> None:
        with (
            mock.patch.object(
                U.metadata, "distribution", return_value=self._dist("pip")
            ),
            mock.patch.object(U.os, "listdir", return_value=["conda-meta"]),
            mock.patch.object(U.os.path, "isdir", return_value=True),
        ):
            info = U.detect_install()
        self.assertEqual(info.kind, "conda")
        self.assertIn("conda update", info.reason)
        with mock.patch.object(
            U.metadata, "distribution", return_value=self._dist("poetry")
        ):
            info = U.detect_install("py")
        self.assertEqual(info.kind, "unknown")
        self.assertIn("poetry", info.reason)

    def test_not_installed(self) -> None:
        with mock.patch.object(
            U.metadata,
            "distribution",
            side_effect=U.metadata.PackageNotFoundError,
        ):
            self.assertFalse(U.detect_install().upgradable)


class TestUpdateCommand(unittest.TestCase):
    def setUp(self) -> None:
        reset_console()
        self.addCleanup(reset_console)

    def test_up_to_date(self) -> None:
        with (
            mock.patch.object(U, "fetch_latest", return_value=__version__),
            mock.patch.object(U, "detect_install", return_value=_pip()),
        ):
            code, out = _run(["update", "--plain"])
        self.assertEqual(code, 0)
        self.assertIn("is the latest release", out)
        with (
            mock.patch.object(U, "fetch_latest", return_value=__version__),
            mock.patch.object(U, "detect_install", return_value=_pip()),
        ):
            code, out = _run(["update", "--check", "--json"])
        self.assertEqual(code, 0)
        self.assertFalse(json.loads(out)["update_available"])

    def test_check_exits_1_when_newer(self) -> None:
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip()),
        ):
            code, out = _run(["update", "--check", "--plain"])
        self.assertEqual(code, 1)
        self.assertIn("update available", out)
        self.assertIn("-m xstate_statemachine update", out)

    def test_off_tty_without_yes_prints_the_command_and_exits_1(self) -> None:
        run = mock.MagicMock(return_value=0)
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip()),
            mock.patch.object(U, "_run", run),
        ):
            code, out = _run(["update", "--plain"])
        self.assertEqual(code, 1)
        self.assertIn("would run:", out)
        self.assertIn("--yes", out)
        run.assert_not_called()

    def test_yes_runs_installer_and_confirms_with_fresh_interpreter(
        self,
    ) -> None:
        run = mock.MagicMock(return_value=0)
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip("py")),
            mock.patch.object(U, "_run", run),
            mock.patch.object(U, "_installed_version", return_value="99.0.0"),
            mock.patch.object(U.sys, "platform", "linux"),
        ):
            code, out = _run(["update", "--yes", "--plain"])
        self.assertEqual(code, 0)
        run.assert_called_once_with(
            ["py", "-m", "pip", "install", "--upgrade", U.DIST]
        )
        self.assertIn(f"updated {U.DIST} {__version__} -> 99.0.0", out)

    def test_installer_failure_propagates_exit_code(self) -> None:
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip()),
            mock.patch.object(U, "_run", return_value=3),
            mock.patch.object(U.sys, "platform", "linux"),
        ):
            code, out = _run(["update", "-y", "--plain"])
        self.assertEqual(code, 3)
        self.assertIn("exited with 3", out)

    def test_version_mismatch_after_upgrade_is_a_warning(self) -> None:
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip()),
            mock.patch.object(U, "_run", return_value=0),
            mock.patch.object(U, "_installed_version", return_value=None),
            mock.patch.object(U.sys, "platform", "linux"),
        ):
            code, out = _run(["update", "-y", "--plain"])
        self.assertEqual(code, 0)
        self.assertIn("could not confirm", out)

    def test_refuses_editable_with_reason(self) -> None:
        info = U.InstallInfo(
            "editable", "pip", "C:/src", "py", [], "dev checkout -- use git"
        )
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=info),
        ):
            code, out = _run(["update", "-y", "--plain"])
        self.assertEqual(code, 2)
        self.assertIn("not updating: dev checkout", out)

    def test_pypi_unreachable(self) -> None:
        with (
            mock.patch.object(
                U,
                "fetch_latest",
                side_effect=U.urllib.error.URLError("offline"),
            ),
            mock.patch.object(U, "detect_install", return_value=_pip()),
        ):
            code, out = _run(["update", "--plain"])
        self.assertEqual(code, 1)
        self.assertIn("could not reach PyPI", out)
        with (
            mock.patch.object(
                U, "fetch_latest", side_effect=OSError("timeout")
            ),
            mock.patch.object(U, "detect_install", return_value=_pip()),
        ):
            code, out = _run(["update", "--json"])
        self.assertEqual(code, 1)
        self.assertIn("error", json.loads(out))

    def test_windows_reapplies_setup_shim_after_upgrade(self) -> None:
        from src.xstate_statemachine.cli.commands import setup as S

        installed_state = mock.MagicMock(installed=True)
        reinstalled = mock.MagicMock(action="refreshed")
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip()),
            mock.patch.object(U, "_run", return_value=0),
            mock.patch.object(U, "_installed_version", return_value="99.0.0"),
            mock.patch.object(U.sys, "platform", "win32"),
            mock.patch.object(S, "inspect_shim", return_value=installed_state),
            mock.patch.object(
                S, "install_shim", return_value=reinstalled
            ) as ins,
        ):
            code, out = _run(["update", "-y", "--plain"])
        self.assertEqual(code, 0)
        ins.assert_called_once()
        self.assertIn("re-applied the xsm.cmd shim", out)

    def test_interactive_confirm_no_leaves_everything_alone(self) -> None:
        from src.xstate_statemachine.cli.ui import keys as K

        caps = Capabilities(
            tty=True,
            color=False,
            truecolor=False,
            unicode=False,
            animate=True,
            width=80,
            height=24,
        )
        buf = io.StringIO()
        cmds._console = Console(caps, buf)
        self.addCleanup(reset_console)
        run = mock.MagicMock(return_value=0)
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip()),
            mock.patch.object(U, "_run", run),
            mock.patch.object(
                Console,
                "interactive",
                new_callable=mock.PropertyMock,
                return_value=True,
            ),
            mock.patch.object(Console, "confirm", return_value=False),
        ):
            U.run_update()
        run.assert_not_called()
        self.assertIn("nothing changed", buf.getvalue())

    def test_started_via_launcher_reexecs_detached(self) -> None:
        """Under pip's xsm.exe the launcher is our parent; pip cannot delete
        it (WinError 32). update must hand over to a detached
        `python -m xstate_statemachine update --yes` and exit."""
        import os

        launcher = os.path.join(os.path.dirname(sys.executable), "xsm")
        run = mock.MagicMock(return_value=0)
        reexec = mock.MagicMock(return_value=4242)
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip("py")),
            mock.patch.object(U, "_run", run),
            mock.patch.object(U, "_reexec_detached", reexec),
            mock.patch.object(U.sys, "platform", "win32"),
            mock.patch.dict(U.os.environ, {}, clear=False),
        ):
            U.os.environ.pop("XSM_UPDATE_CHILD", None)
            saved, sys.argv = sys.argv, [launcher, "update", "-y", "--plain"]
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    main()
            finally:
                sys.argv = saved
                reset_console()
        run.assert_not_called()
        reexec.assert_called_once()
        self.assertEqual(reexec.call_args.args[0], "py")
        self.assertIn("handing over", buf.getvalue())

    def test_child_of_reexec_does_not_reexec_again(self) -> None:
        run = mock.MagicMock(return_value=0)
        reexec = mock.MagicMock()
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip("py")),
            mock.patch.object(U, "_run", run),
            mock.patch.object(U, "_reexec_detached", reexec),
            mock.patch.object(U, "_installed_version", return_value="99.0.0"),
            mock.patch.object(U.sys, "platform", "win32"),
            mock.patch.object(U, "_started_via_launcher", return_value=True),
            mock.patch.dict(U.os.environ, {"XSM_UPDATE_CHILD": "1"}),
        ):
            code, out = _run(["update", "-y", "--plain"])
        self.assertEqual(code, 0)
        reexec.assert_not_called()
        run.assert_called_once()
        self.assertNotIn("Installed:", out)  # header printed by the parent
        self.assertIn("updated", out)

    def test_launcher_detection(self) -> None:
        with mock.patch.object(U.sys, "platform", "win32"):
            import os

            scripts = os.path.dirname(sys.executable)
            for name in ("xsm", "xsm.exe", "XSM.EXE"):
                with mock.patch.object(
                    U.sys, "argv", [os.path.join(scripts, name)]
                ):
                    self.assertTrue(U._started_via_launcher(), name)
            with mock.patch.object(U.sys, "argv", ["xsm", "update"]):
                self.assertFalse(U._started_via_launcher())  # bare name
            with mock.patch.object(
                U.sys, "argv", [os.path.join(scripts, "..", "other", "xsm")]
            ):
                self.assertFalse(U._started_via_launcher())  # other folder
        with (
            mock.patch.object(U.sys, "platform", "linux"),
            mock.patch.object(U.sys, "argv", ["/usr/bin/xsm.exe"]),
        ):
            self.assertFalse(U._started_via_launcher())

    def test_json_mode_acts_without_asking(self) -> None:
        with (
            mock.patch.object(U, "fetch_latest", return_value="99.0.0"),
            mock.patch.object(U, "detect_install", return_value=_pip()),
            mock.patch.object(U, "_run", return_value=0),
            mock.patch.object(U, "_installed_version", return_value="99.0.0"),
            mock.patch.object(U.sys, "platform", "linux"),
        ):
            code, out = _run(["update", "--json"])
        self.assertEqual(code, 0)
        self.assertIn('"updated_to": "99.0.0"', out)


if __name__ == "__main__":
    unittest.main()
