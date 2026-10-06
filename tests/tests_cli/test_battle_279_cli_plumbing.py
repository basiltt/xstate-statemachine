# tests/tests_cli/test_battle_279_cli_plumbing.py
"""#279 battle, adversary B: the CLI plumbing around the web companions.

Pinned here:

* ``-o`` naming an existing FILE is a one-line usage error (exit 2), not
  a ``FileExistsError`` traceback;
* ``--check`` / ``--diff`` write NOTHING -- not even the output
  directory -- and a missing companion is exit 1 ("would be created");
* ``--diff`` goes to stdout as a unified diff naming the companion;
* ``--check`` does not import/mount the web companions (it compares
  text), so it is fast and needs no extra beyond generation;
* a companion left behind by an earlier ``--with-api`` run is NAMED when
  a later run does not request it (it was invisible to ``--check``);
* overwriting a generated file whose banner names a different source
  chart (two charts with one ``id`` into one ``-o``) warns;
* every ``xsm new`` template renders with no leftover ``${...}`` and
  pins the CURRENT package version;
* the launcher's Companion multiselect reaches ``--with-api`` /
  ``--with-models``.
"""

from __future__ import annotations

import ast
import io
import json
import logging
import os
import pathlib
import sys
from contextlib import redirect_stdout
from typing import List, Tuple
from unittest import mock

import pytest

from src.xstate_statemachine.cli.__main__ import main

ROOT = pathlib.Path(__file__).resolve().parents[2]
CHART = ROOT / "examples" / "integrations" / "fastapi_orders" / "machine.json"
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"


def _run(argv: List[str]) -> Tuple[int, str]:
    from src.xstate_statemachine.cli.commands import reset_console

    reset_console()
    saved, sys.argv = sys.argv, ["xsm", *argv]
    buf = io.StringIO()
    logging.disable(logging.CRITICAL)
    try:
        with redirect_stdout(buf):
            main()
        code = 0
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    finally:
        sys.argv = saved
        logging.disable(logging.NOTSET)
        reset_console()
    return code, buf.getvalue()


def _src(tmp: pathlib.Path, name: str = "m.json") -> pathlib.Path:
    p = tmp / name
    p.write_text(CHART.read_text("utf-8"), encoding="utf-8")
    return p


def _gt(src: pathlib.Path, out: pathlib.Path, *extra: str) -> Tuple[int, str]:
    return _run(["gt", str(src), "-o", str(out), "--plain", *extra])


def _snapshot(d: pathlib.Path) -> dict:
    return {
        p.name: (p.stat().st_mtime_ns, p.read_bytes()) for p in d.iterdir()
    }


# -----------------------------------------------------------------------------
# -o and --check never write
# -----------------------------------------------------------------------------
def test_output_pointing_at_a_file_is_a_usage_error(
    tmp_path: pathlib.Path,
) -> None:
    src = _src(tmp_path)
    afile = tmp_path / "afile"
    afile.write_text("x")
    code, text = _gt(src, afile, "-f")
    assert code == 2, text
    assert "not a directory" in text
    assert afile.read_text() == "x"


def test_check_creates_nothing_and_missing_companion_is_stale(
    tmp_path: pathlib.Path,
) -> None:
    src = _src(tmp_path)
    out = tmp_path / "nested" / "o#'x"
    code, text = _gt(src, out, "--with-api", "--check")
    assert code == 1, text
    assert not (tmp_path / "nested").exists()


def test_check_and_diff_write_nothing_when_stale(
    tmp_path: pathlib.Path,
) -> None:
    src = _src(tmp_path)
    out = tmp_path / "o #'é"
    assert _gt(src, out, "--with-api", "--with-models", "-f")[0] == 0
    api = out / "order_api.py"
    api.write_text(api.read_text("utf-8") + "# edit\n", encoding="utf-8")
    (out / "order_logic.py").write_text("stale\n", encoding="utf-8")
    before = _snapshot(out)
    for flag in ("--check", "--diff"):
        code, text = _gt(src, out, "--with-api", "--with-models", flag)
        assert code == 1, text
        assert "order_api.py" in text
    assert _snapshot(out) == before
    _, text = _gt(src, out, "--with-api", "--with-models", "--diff")
    assert "--- order_api.py (on disk)" in text
    assert "+++ order_api.py (generated)" in text
    assert "-# edit" in text


def test_check_with_force_is_still_a_check(tmp_path: pathlib.Path) -> None:
    """`-f` only answers the overwrite prompt; `--check` wins."""
    src = _src(tmp_path)
    out = tmp_path / "o"
    code, _ = _gt(src, out, "--with-api", "--check", "-f")
    assert code == 1
    assert not out.exists()


def test_check_does_not_import_the_web_companions(
    tmp_path: pathlib.Path,
) -> None:
    from src.xstate_statemachine.cli.commands import generate as G

    src = _src(tmp_path)
    out = tmp_path / "o"
    assert _gt(src, out, "--with-api", "--with-models", "-f")[0] == 0
    with mock.patch.object(
        G, "_verify_web", side_effect=AssertionError("verified in --check")
    ):
        code, text = _gt(src, out, "--with-api", "--with-models", "--check")
    assert code == 0, text


# -----------------------------------------------------------------------------
# leftovers and foreign overwrites
# -----------------------------------------------------------------------------
def test_leftover_companion_is_named(tmp_path: pathlib.Path) -> None:
    src = _src(tmp_path)
    out = tmp_path / "o"
    assert _gt(src, out, "--with-api", "-f")[0] == 0
    code, text = _gt(src, out, "--check")
    assert code == 0, text
    assert "order_api.py (fastapi-router) exists but was not" in text
    assert "--with-api" in text
    code, text = _gt(src, out, "-f")
    assert "order_api.py (fastapi-router) exists" in text
    assert (out / "order_api.py").exists()  # never deleted


def test_overwriting_another_charts_output_warns(
    tmp_path: pathlib.Path,
) -> None:
    a, b = _src(tmp_path, "a.json"), _src(tmp_path, "b.json")
    out = tmp_path / "o"
    assert _gt(a, out, "--with-api", "-f")[0] == 0
    code, text = _gt(a, out, "--with-api", "-f")
    assert "was generated from" not in text
    code, text = _gt(b, out, "--with-api", "-f")
    assert code == 0, text
    assert "order_logic.py was generated from a.json" in text
    assert "order_api.py was generated from a.json" in text


def test_standalone_router_writes_only_the_router(
    tmp_path: pathlib.Path,
) -> None:
    src = _src(tmp_path)
    out = tmp_path / "o"
    code, text = _gt(src, out, "-t", "fastapi-router", "--no-verify")
    assert code == 0, text
    assert sorted(p.name for p in out.iterdir()) == ["order_api.py"]


# -----------------------------------------------------------------------------
# list-templates / launcher
# -----------------------------------------------------------------------------
def test_list_templates_names_the_web_companions() -> None:
    code, text = _run(["list-templates", "--plain"])
    assert code == 0
    section = text.split("Companion outputs", 1)[1].split("Feature", 1)[0]
    assert "fastapi-router" in section and "pydantic-models" in section


def test_launcher_multiselect_reaches_with_api_and_models(
    tmp_path: pathlib.Path,
) -> None:
    from src.xstate_statemachine.cli.commands import launcher

    seen = {}

    class _C:
        def select(self, *a, **k):
            return 0

        def multiselect(self, title, items, **k):
            if title == "Companion files":
                labels = [i[0] for i in items]
                return [
                    labels.index("FastAPI router"),
                    labels.index("Pydantic models"),
                ]
            return []

        def text(self, *a, **k):
            return str(tmp_path)

        def __getattr__(self, name):
            raise _Stop

    class _Stop(Exception):
        pass

    with (
        mock.patch.object(launcher, "_pick_files", return_value=[str(CHART)]),
        mock.patch.object(launcher, "get_console", return_value=_C()),
        mock.patch.object(
            launcher,
            "_default_namespace",
            side_effect=lambda f: _capture_ns(f, seen),
        ),
    ):
        try:
            launcher.generate_wizard(None)
        except _Stop:
            pass
    ns = seen["ns"]
    assert ns.with_api and ns.with_models
    assert not (ns.with_tests or ns.with_types or ns.with_plugin)


def _capture_ns(files, seen):
    import argparse

    ns = argparse.Namespace()
    seen["ns"] = ns
    return ns


# -----------------------------------------------------------------------------
# xsm new
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("template", ["fastapi"])
def test_every_project_template_renders_cleanly(
    tmp_path: pathlib.Path, template: str
) -> None:
    from src.xstate_statemachine import __version__
    from src.xstate_statemachine.cli.commands import new as N

    assert N.TEMPLATES[template][0] == "shipped"
    files = N.scaffold(template, tmp_path, name="shop_orders")
    for f in files:
        text = f.read_text("utf-8")
        assert "${" not in text, f
        if f.suffix == ".py":
            ast.parse(text, filename=str(f))
        if f.suffix == ".json":
            json.loads(text)
    req = (tmp_path / "requirements.txt").read_text("utf-8")
    assert f"xstate-statemachine[{template}]>={__version__}" in req
    readme = (tmp_path / "README.md").read_text("utf-8")
    assert "shop_orders" in readme or "shopOrders" in readme


def test_every_shipped_template_is_parametrised_above() -> None:
    from src.xstate_statemachine.cli.commands import new as N

    shipped = [k for k, (s, _) in N.TEMPLATES.items() if s == "shipped"]
    assert shipped == ["fastapi"], "add the new template to the test above"


def test_force_writes_into_non_empty_dir_keeping_other_files(
    tmp_path: pathlib.Path,
) -> None:
    from src.xstate_statemachine.cli.commands import new as N

    (tmp_path / "keep.txt").write_text("k")
    N.scaffold("fastapi", tmp_path, force=True)
    assert (tmp_path / "keep.txt").read_text() == "k"
    assert (tmp_path / "app.py").exists()
    assert os.path.isdir(tmp_path / "tests")
