# tests/tests_cli/test_new_project.py
"""`xsm new` (#309): scaffold a project from an example app."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.xstate_statemachine.cli.commands import new as N

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "integrations" / "fastapi_orders"


def test_scaffold_writes_the_project(tmp_path: Path) -> None:
    files = N.scaffold("fastapi", tmp_path / "p", name="shop_orders")
    names = sorted(f.relative_to(tmp_path / "p").as_posix() for f in files)
    assert names == [
        "README.md",
        "app.py",
        "logic.py",
        "machine.json",
        "models.py",
        "requirements.txt",
        "static/index.html",
        "tests/conftest.py",
        "tests/test_app.py",
    ]
    app = (tmp_path / "p" / "app.py").read_text("utf-8")
    assert 'MACHINE_NAME = "shopOrders"' in app
    assert 'prefix="/shop_orders"' in app
    req = (tmp_path / "p" / "requirements.txt").read_text("utf-8")
    assert "xstate-statemachine[fastapi]>=" in req
    assert '"id": "shopOrders"' in (tmp_path / "p" / "machine.json").read_text(
        "utf-8"
    )


# 📝 battle #279-b: `app.py` is deliberately NOT pinned. The example app
#    has grown deployment features (chart versioning + migrations, a
#    circuit breaker, dead-letter plugin, bounded routes) that a starter
#    scaffold should not carry; the template is a reduced copy. Its
#    health is pinned instead by rendering + parsing it
#    (test_battle_279_cli_plumbing) and by its own tests/ running green.
@pytest.mark.parametrize("fname", ["logic.py", "models.py", "machine.json"])
def test_template_has_not_drifted_from_the_example(
    tmp_path: Path, fname: str
) -> None:
    """The template is the example app; re-copy it when the example
    changes. Only the header path and the machine id may differ."""
    N.scaffold("fastapi", tmp_path, name="order")
    got = (tmp_path / fname).read_text("utf-8").splitlines()[1:]
    want = (EXAMPLE / fname).read_text("utf-8").splitlines()[1:]
    assert got == want


def test_refuses_non_empty_dir_without_force(tmp_path: Path) -> None:
    (tmp_path / "keep.txt").write_text("x")
    with pytest.raises(N.NewProjectError, match="--force"):
        N.scaffold("fastapi", tmp_path)
    N.scaffold("fastapi", tmp_path, force=True)
    assert (tmp_path / "keep.txt").exists()
    assert (tmp_path / "app.py").exists()


@pytest.mark.parametrize(
    "template,match",
    [("django", "django_approvals"), ("x", "--list")],
)
def test_planned_and_unknown_templates_are_refused(
    tmp_path: Path, template: str, match: str
) -> None:
    with pytest.raises(N.NewProjectError, match=match):
        N.scaffold(template, tmp_path / "p")
    assert not (tmp_path / "p").exists()


FLASK_EXAMPLE = ROOT / "examples" / "integrations" / "flask_wizard"


def test_flask_template_is_the_example_verbatim(tmp_path: Path) -> None:
    """battle #309-a: #285 shipped, so `--template flask` scaffolds the
    flask_wizard example (it used to refuse with "arrives with #285")."""
    files = N.scaffold("flask", tmp_path)
    rels = {f.relative_to(tmp_path).as_posix() for f in files}
    assert {"requirements.txt", "README.md"} <= rels
    for rel in rels - {"requirements.txt", "README.md"}:
        got = (tmp_path / rel).read_text("utf-8").splitlines()
        assert got == (FLASK_EXAMPLE / rel).read_text("utf-8").splitlines()
    req = (tmp_path / "requirements.txt").read_text("utf-8")
    assert "xstate-statemachine[flask]>=" in req
    # 📝 review #309 M4: the OTHER direction -- a file added to the example
    #    later and missing from the template must fail here, not drift
    example = {
        f.relative_to(FLASK_EXAMPLE).as_posix()
        for f in FLASK_EXAMPLE.rglob("*")
        if f.is_file()
        and "__pycache__" not in f.parts
        and f.name != "README.md"
        and not f.name.endswith((".pyc", ".db", ".sqlite"))
    }
    assert example <= rels, sorted(example - rels)


def test_flask_scaffold_tests_pass(tmp_path: Path) -> None:
    pytest.importorskip("flask")
    N.scaffold("flask", tmp_path / "w")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-p"]
        + ["no:cacheprovider", "-o", "addopts=", "--rootdir"]
        + [str(tmp_path / "w")],
        cwd=tmp_path / "w",
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]


@pytest.mark.parametrize("bad", ["Orders", "1x", "class", "a-b", ""])
def test_bad_names_are_refused(tmp_path: Path, bad: str) -> None:
    with pytest.raises(N.NewProjectError, match="invalid --name"):
        N.scaffold("fastapi", tmp_path / "p", name=bad)


def test_run_new_list_and_errors(tmp_path: Path, capsys) -> None:
    from src.xstate_statemachine.cli.commands import reset_console

    reset_console()  # another test may have cached a console on old stdout
    N.run_new(None, list_only=True)
    out = capsys.readouterr().out
    assert "fastapi" in out and "flask" in out and "planned, #309" in out
    with pytest.raises(SystemExit) as exc:
        N.run_new(str(tmp_path / "p"), template="django")
    assert exc.value.code == 2
    with pytest.raises(SystemExit) as exc:
        N.run_new(None)
    assert exc.value.code == 2
    N.run_new(str(tmp_path / "ok"))
    assert "Created 9 files" in capsys.readouterr().out


def test_next_hint_quotes_a_path_with_spaces(tmp_path: Path, capsys) -> None:
    from src.xstate_statemachine.cli.commands import reset_console

    reset_console()
    target = tmp_path / "my service"
    N.run_new(str(target))
    assert f'cd "{target}" &&' in capsys.readouterr().out


def test_cli_entry_point(tmp_path: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "xstate_statemachine.cli", "--plain"]
        + ["new", str(tmp_path / "p"), "--name", "tickets"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert (tmp_path / "p" / "tests" / "test_app.py").is_file()


def test_scaffolded_project_tests_pass(tmp_path: Path) -> None:
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    target = tmp_path / "svc"
    N.scaffold("fastapi", target, name="shop_orders")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-p"]
        + ["no:cacheprovider", "-o", "addopts=", "--rootdir", str(target)],
        cwd=target,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    assert " passed" in proc.stdout
