"""Tests for `xsm setup`, the Windows batch-shim installer, exercised in a
temp directory on every OS by passing `platform=` explicitly."""

from __future__ import annotations

import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from typing import List

import src.xstate_statemachine.cli.commands as cmds
from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands import setup as S


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


class _Tmp(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sd = pathlib.Path(self.tmp.name)
        self.exe = self.sd / "xsm.exe"
        self.parked = self.sd / ("xsm.exe" + S.PARKED_SUFFIX)
        self.shim = self.sd / "xsm.cmd"
        self.py = pathlib.Path("C:/Py/python.exe")

    def _fake_exe(self) -> None:
        self.exe.write_bytes(b"MZ fake launcher")


class TestShimLifecycle(_Tmp):
    def test_install_parks_exe_and_writes_shim(self) -> None:
        self._fake_exe()
        st = S.install_shim(self.sd, platform="win32", python=self.py)
        self.assertEqual(st.action, "installed")
        self.assertTrue(st.installed)
        self.assertFalse(self.exe.exists())
        self.assertEqual(self.parked.read_bytes(), b"MZ fake launcher")
        body = self.shim.read_bytes().decode("utf-8")
        self.assertIn('"C:\\Py\\python.exe" -m xstate_statemachine %*', body)
        self.assertIn("python -m xstate_statemachine %*", body)  # fallback
        self.assertTrue(body.endswith("\r\n"))
        self.assertNotIn("\r\r\n", body)

    def test_install_is_idempotent(self) -> None:
        self._fake_exe()
        S.install_shim(self.sd, platform="win32", python=self.py)
        st = S.install_shim(self.sd, platform="win32", python=self.py)
        self.assertEqual(st.action, "none")
        self.assertTrue(st.installed)

    def test_reinstall_after_pip_upgrade_recreated_exe(self) -> None:
        self._fake_exe()
        S.install_shim(self.sd, platform="win32", python=self.py)
        self.exe.write_bytes(b"MZ new launcher")  # what pip --upgrade does
        st = S.install_shim(self.sd, platform="win32", python=self.py)
        self.assertEqual(st.action, "refreshed")
        self.assertTrue(st.installed)
        self.assertEqual(self.parked.read_bytes(), b"MZ new launcher")

    def test_stale_shim_for_another_interpreter_is_rewritten(self) -> None:
        self.shim.write_bytes(b"@echo old\r\n")
        st = S.inspect_shim(self.sd, platform="win32", python=self.py)
        self.assertTrue(st.shim_present)
        self.assertFalse(st.shim_current)
        st = S.install_shim(self.sd, platform="win32", python=self.py)
        self.assertEqual(st.action, "refreshed")
        self.assertTrue(st.shim_current)

    def test_remove_restores_exe(self) -> None:
        self._fake_exe()
        S.install_shim(self.sd, platform="win32", python=self.py)
        st = S.remove_shim(self.sd, platform="win32", python=self.py)
        self.assertEqual(st.action, "removed")
        self.assertTrue(self.exe.exists())
        self.assertFalse(self.shim.exists())
        self.assertFalse(self.parked.exists())
        self.assertEqual(
            S.remove_shim(self.sd, platform="win32", python=self.py).action,
            "none",
        )

    def test_remove_keeps_parked_copy_if_pip_recreated_exe(self) -> None:
        self._fake_exe()
        S.install_shim(self.sd, platform="win32", python=self.py)
        self.exe.write_bytes(b"MZ new")
        S.remove_shim(self.sd, platform="win32", python=self.py)
        self.assertEqual(self.exe.read_bytes(), b"MZ new")  # not clobbered
        self.assertTrue(self.parked.exists())

    def test_non_windows_is_unsupported_and_touches_nothing(self) -> None:
        self._fake_exe()
        for fn in (S.install_shim, S.remove_shim):
            st = fn(self.sd, platform="linux", python=self.py)
            self.assertEqual(st.action, "unsupported")
        self.assertTrue(self.exe.exists())
        self.assertFalse(self.shim.exists())

    def test_default_scripts_dir_is_this_interpreters(self) -> None:
        self.assertTrue(S.default_scripts_dir().is_absolute())


class TestSetupCommand(_Tmp):
    def _argv(self, *more: str) -> List[str]:
        return ["setup", "--scripts-dir", str(self.sd), "--plain", *more]

    def test_check_exits_1_until_installed_on_windows(self) -> None:
        from unittest import mock

        self._fake_exe()
        with mock.patch.object(S.sys, "platform", "win32"):
            code, out = _run(self._argv("--check"))
            self.assertEqual(code, 1)
            self.assertIn("still resolves to pip's xsm.exe", out)
            code, out = _run(self._argv())
            self.assertEqual(code, 0)
            self.assertIn("now runs through cmd.exe", out)
            self.assertIn("setup --undo", out)
            code, out = _run(self._argv("--check"))
            self.assertEqual(code, 0)
            self.assertIn("resolves to the batch shim", out)
            code, out = _run(self._argv())
            self.assertIn("already set up", out)
            code, out = _run(self._argv("--undo"))
            self.assertEqual(code, 0)
            self.assertIn("launcher restored", out)
            code, out = _run(self._argv("--undo"))
            self.assertIn("no shim to remove", out)

    def test_json_output(self) -> None:
        from unittest import mock

        self._fake_exe()
        with mock.patch.object(S.sys, "platform", "win32"):
            code, out = _run(self._argv("--json"))
            d = json.loads(out)
            self.assertEqual(d["action"], "installed")
            self.assertTrue(d["installed"])
            code, out = _run(self._argv("--check", "--json"))
            self.assertEqual(code, 0)
            _run(self._argv("--undo"))
            code, _ = _run(self._argv("--check", "--json"))
            self.assertEqual(code, 1)

    def test_no_op_message_off_windows(self) -> None:
        from unittest import mock

        with mock.patch.object(S.sys, "platform", "darwin"):
            code, out = _run(self._argv())
            self.assertEqual(code, 0)
            self.assertIn("nothing to do", out)
            self.assertIn("-m xstate_statemachine", out)
            code, _ = _run(self._argv("--check", "--json"))
            self.assertEqual(code, 0)  # not a failure where there is no exe

    def test_undo_and_check_are_exclusive(self) -> None:
        code, _ = _run(self._argv("--undo", "--check"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
