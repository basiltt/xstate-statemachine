# tests/contrib/testing/test_battle_268_snapshots.py
"""#268 battle (adversary A): `xsm_snapshot` files -- determinism across
hash seeds and wall time, CRLF, rootdir confinement, duplicate writers,
atomic writes under xdist."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import subprocess
import sys
import textwrap
from typing import Any

import pytest

from src.xstate_statemachine.contrib.testing._snapshots import (
    _atomic_write,
    render_snapshot,
)

from .conftest import PLUGIN_ARGS, SRC, run

pytestmark = pytest.mark.timeout(300)

MOD = """
import enum, pytest
from decimal import Decimal

class Color(enum.Enum):
    RED = "red"

CFG = {"id": "s", "initial": "a",
       "context": {"tags": None, "t": None, "c": None, "b": None, "u": "é"},
       "states": {"a": {"on": {"GO": "b"}}, "b": {}}}

@pytest.mark.xstate_machine(CFG)
def test_snap(xsm_interp, xsm_snapshot):
    xsm_interp.context.update(
        tags={"alpha", "beta", "gamma", "delta"}, t=(1, 2),
        c=Color.RED, b=b"x", d=Decimal("1.10"))
    xsm_interp.send("GO", amount=Decimal("2.5"))
    xsm_snapshot(xsm_interp, PATH)
"""


def _snap_module(path: str = "snaps/s.json") -> str:
    return f"PATH = {path!r}\n" + MOD


def _session(tmp: pathlib.Path, seed: str, *args: str) -> int:
    env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(SRC))
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        *PLUGIN_ARGS,
        *args,
    ]
    if importlib.util.find_spec("pytest_django") is not None:
        cmd += ["-p", "no:django"]
    (tmp / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    return subprocess.run(cmd, cwd=str(tmp), env=env).returncode


class TestDeterminism:
    def test_set_context_same_bytes_under_any_hash_seed(
        self, tmp_path: pathlib.Path
    ) -> None:
        # 🛑 Was: `default=str` rendered a set in hash order, so a file
        #    recorded under one PYTHONHASHSEED failed under another.
        (tmp_path / "test_s.py").write_text(_snap_module(), encoding="utf-8")
        assert _session(tmp_path, "1", "--xsm-update-snapshots") == 0
        first = (tmp_path / "snaps" / "s.json").read_bytes()
        for seed in ("2", "3", "4"):
            assert _session(tmp_path, seed) == 0
        assert b"\r\n" not in first
        text = first.decode("utf-8")
        # 📝 ASCII-escaped, as before the split: existing files must not
        #    churn on upgrade.
        assert '"alpha",\n' in text and "\\u00e9" in text

    def test_render_is_canonical_for_rich_types(self) -> None:
        out = render_snapshot({"context": {"s": {3, 1, 2}, "f": frozenset()}})
        assert '"s": [\n      1,\n      2,\n      3\n    ]' in out
        assert '"f": []' in out


class TestFiles:
    def test_crlf_file_still_matches(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(test_s=_snap_module())
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        f = xsm_pytester.path / "snaps" / "s.json"
        f.write_bytes(f.read_bytes().replace(b"\n", b"\r\n"))
        run(xsm_pytester).assert_outcomes(passed=1)

    def test_replay_after_wall_time_moves(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(test_s=_snap_module())
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        text = (xsm_pytester.path / "snaps" / "s.json").read_text("utf-8")
        assert "taken_at" not in text and "version" not in text

    @pytest.mark.parametrize(
        "path, ok",
        [("../up/x.json", True), ("../../../../../x.json", False)],
    )
    def test_relative_paths_inside_and_outside_rootdir(
        self, xsm_pytester: Any, path: str, ok: bool
    ) -> None:
        sub = xsm_pytester.mkpydir("pkg")
        (sub / "test_s.py").write_text(_snap_module(path), encoding="utf-8")
        result = run(xsm_pytester, "--xsm-update-snapshots")
        if ok:
            result.assert_outcomes(passed=1)
            assert (xsm_pytester.path / "up" / "x.json").is_file()
        else:
            assert "outside the project" in str(result.stdout)

    def test_absolute_path_inside_rootdir(self, xsm_pytester: Any) -> None:
        target = xsm_pytester.path / "abs" / "x.json"
        xsm_pytester.makepyfile(test_s=_snap_module(str(target)))
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        assert target.is_file()

    def test_symlink_escape_refused(
        self, xsm_pytester: Any, tmp_path_factory: Any
    ) -> None:
        outside = tmp_path_factory.mktemp("outside")
        link = xsm_pytester.path / "link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not permitted here")
        xsm_pytester.makepyfile(test_s=_snap_module("link/x.json"))
        result = run(xsm_pytester, "--xsm-update-snapshots")
        assert "outside the project" in str(result.stdout)
        assert not (outside / "x.json").exists()

    def test_two_tests_same_path_different_content_refused(
        self, xsm_pytester: Any
    ) -> None:
        xsm_pytester.makepyfile(textwrap.dedent("""
            import pytest
            CFG = {"id": "s", "initial": "a",
                   "states": {"a": {"on": {"GO": "b"}}, "b": {}}}

            @pytest.mark.xstate_machine(CFG)
            def test_one(xsm_interp, xsm_snapshot):
                xsm_snapshot(xsm_interp, "same.json")

            @pytest.mark.xstate_machine(CFG)
            def test_two(xsm_interp, xsm_snapshot):
                xsm_interp.send("GO")
                xsm_snapshot(xsm_interp, "same.json")

            @pytest.mark.xstate_machine(CFG)
            def test_three_same_content(xsm_interp, xsm_snapshot):
                xsm_snapshot(xsm_interp, "same.json")
            """))
        result = run(xsm_pytester, "--xsm-update-snapshots")
        result.assert_outcomes(passed=2, failed=1)
        assert "already recorded with different content" in str(result.stdout)

    def test_large_context_round_trips(self, xsm_pytester: Any) -> None:
        xsm_pytester.makepyfile(textwrap.dedent("""
            import pytest
            CFG = {"id": "s", "initial": "a", "states": {"a": {}}}

            @pytest.mark.xstate_machine(CFG)
            def test_big(xsm_interp, xsm_snapshot):
                xsm_interp.context["blob"] = ["x" * 100] * 10_000
                xsm_snapshot(xsm_interp, "big.json")
            """))
        run(xsm_pytester, "--xsm-update-snapshots").assert_outcomes(passed=1)
        run(xsm_pytester).assert_outcomes(passed=1)


class TestAtomicWrite:
    def test_replace_leaves_no_temp_and_lf(
        self, tmp_path: pathlib.Path
    ) -> None:
        target = tmp_path / "d" / "x.json"
        _atomic_write(target, "a\nb\n")
        _atomic_write(target, "c\n")
        assert target.read_bytes() == b"c\n"
        assert [p.name for p in target.parent.iterdir()] == ["x.json"]

    def test_failed_write_cleans_temp(
        self, tmp_path: pathlib.Path, monkeypatch: Any
    ) -> None:
        def boom(*a: Any) -> None:
            raise OSError("disk full")

        monkeypatch.setattr(os, "replace", boom)
        with pytest.raises(OSError):
            _atomic_write(tmp_path / "x.json", "a\n")
        assert list(tmp_path.iterdir()) == []
