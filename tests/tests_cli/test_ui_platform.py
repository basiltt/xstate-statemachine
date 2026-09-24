"""Platform-facing halves of `cli.ui.keys` / `cli.ui.term`, exercised with
fakes so they run on every OS: key normalisation, the Windows reader, VT
enablement and the unicode probe."""

from __future__ import annotations

import io
import sys
import unittest
from unittest import mock

from src.xstate_statemachine.cli.ui import keys, term

ESC_CHAR = chr(27)
NUL = chr(0)
WIN_PREFIX = chr(0xE0)


class TestKeyNormalisation(unittest.TestCase):
    def test_control_chars_map_to_names(self) -> None:
        self.assertEqual(keys._normalise("\r"), keys.ENTER)
        self.assertEqual(keys._normalise("\n"), keys.ENTER)
        self.assertEqual(keys._normalise(ESC_CHAR), keys.ESC)
        self.assertEqual(keys._normalise("\t"), keys.TAB)
        self.assertEqual(keys._normalise(chr(0x7F)), keys.BACKSPACE)
        self.assertEqual(keys._normalise(chr(8)), keys.BACKSPACE)
        self.assertEqual(keys._normalise(" "), keys.SPACE)
        self.assertEqual(keys._normalise("x"), "x")

    def test_ctrl_c_is_keyboard_interrupt(self) -> None:
        with self.assertRaises(KeyboardInterrupt):
            keys._normalise(chr(3))


class TestWindowsReader(unittest.TestCase):
    def test_arrow_prefix_and_plain_keys(self) -> None:
        fake = mock.MagicMock()
        fake.getwch.side_effect = [WIN_PREFIX, "H", "q", NUL, "P", NUL, "?"]
        with mock.patch.dict(sys.modules, {"msvcrt": fake}):
            self.assertEqual(keys._read_windows(), keys.UP)
            self.assertEqual(keys._read_windows(), "q")
            self.assertEqual(keys._read_windows(), keys.DOWN)
            self.assertEqual(keys._read_windows(), "")  # unknown scan code

    def test_read_key_dispatches_by_platform(self) -> None:
        with (
            mock.patch.object(keys.sys, "platform", "win32"),
            mock.patch.object(keys, "_read_windows", return_value="w"),
        ):
            self.assertEqual(keys.read_key(), "w")
        with (
            mock.patch.object(keys.sys, "platform", "linux"),
            mock.patch.object(keys, "_read_posix", return_value="p"),
        ):
            self.assertEqual(keys.read_key(), "p")


class TestSources(unittest.TestCase):
    def test_interactive_available(self) -> None:
        self.assertFalse(keys.interactive_available(io.StringIO()))
        tty_like = mock.MagicMock()
        tty_like.isatty.return_value = True
        self.assertTrue(keys.interactive_available(tty_like))
        broken = mock.MagicMock()
        broken.isatty.side_effect = ValueError
        self.assertFalse(keys.interactive_available(broken))

    def test_default_source_is_the_real_reader(self) -> None:
        self.assertIs(keys.default_source(), keys.read_key)


class TestTermProbes(unittest.TestCase):
    def test_unicode_probe(self) -> None:
        class Latin1(io.StringIO):
            encoding = "latin-1"

        class NoEnc(io.StringIO):
            encoding = None  # type: ignore[assignment]

        class Bogus(io.StringIO):
            encoding = "not-a-codec"

        self.assertFalse(term._unicode_ok(Latin1()))
        self.assertTrue(term._unicode_ok(NoEnc()))  # defaults to utf-8
        self.assertFalse(term._unicode_ok(Bogus()))

    def test_enable_windows_vt_is_a_noop_off_windows(self) -> None:
        with mock.patch.object(term.sys, "platform", "linux"):
            self.assertTrue(term._enable_windows_vt(io.StringIO()))

    def test_enable_windows_vt_paths(self) -> None:
        kernel = mock.MagicMock()
        ctypes_mod = mock.MagicMock()
        ctypes_mod.windll.kernel32 = kernel
        mode = mock.MagicMock(value=0)
        ctypes_mod.c_uint32.return_value = mode
        msvcrt_mod = mock.MagicMock()
        msvcrt_mod.get_osfhandle.return_value = 7
        stream = mock.MagicMock()
        stream.fileno.return_value = 1
        with (
            mock.patch.object(term.sys, "platform", "win32"),
            mock.patch.dict(
                sys.modules, {"ctypes": ctypes_mod, "msvcrt": msvcrt_mod}
            ),
        ):
            kernel.GetConsoleMode.return_value = 0  # not a console handle
            self.assertFalse(term._enable_windows_vt(stream))
            kernel.GetConsoleMode.return_value = 1
            kernel.SetConsoleMode.return_value = 1
            self.assertTrue(term._enable_windows_vt(stream))
            mode.value = 0x0004  # already enabled -> no SetConsoleMode call
            kernel.SetConsoleMode.reset_mock()
            self.assertTrue(term._enable_windows_vt(stream))
            kernel.SetConsoleMode.assert_not_called()

    def test_detect_honours_term_dumb_and_no_anim_env(self) -> None:
        import os

        env = {"FORCE_COLOR": "1", "TERM": "dumb"}
        for k in ("NO_COLOR", "XSM_NO_COLOR", "XSM_PLAIN"):
            os.environ.pop(k, None)
        with mock.patch.dict(os.environ, env):
            self.assertFalse(term.detect(io.StringIO()).color)
        tty = mock.MagicMock()
        tty.isatty.return_value = True
        tty.encoding = "utf-8"
        with (
            mock.patch.dict(
                os.environ, {"XSM_NO_ANIM": "1", "COLORTERM": "truecolor"}
            ),
            mock.patch.object(term, "_enable_windows_vt", return_value=True),
        ):
            caps = term.detect(tty)
        self.assertTrue(caps.color)
        self.assertFalse(caps.animate)
        self.assertTrue(caps.truecolor)


if __name__ == "__main__":
    unittest.main()
