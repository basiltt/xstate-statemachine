# tests/contrib/django/test_battle_310_b.py
"""#310 battle, adversary B: ``xsm_migrate_fsm``'s CLI surface and docs.

Defects pinned here:

* ``--dry-run | python -m json.tool`` failed: the recipe text followed
  the JSON on stdout. stdout is now the chart only; the recipe is stderr.
* raw tracebacks instead of `CommandError` (exit 1): an unknown
  ``--database``, a wrong ``--statechart-field``, an unwritable
  ``--write-chart``, an unmigrated database (step 2 not applied).
* ``--map a=b=c`` blamed a state ``'b=c'``; ``--map x=`` / a
  contradictory repeat were accepted; a ``--map`` whose OLD value no row
  holds (a typo) silently did nothing -- now flagged.
* the summary said "N remaining" without saying the skipped rows are in
  it -- the numbers now add up on the page.
* ``xsm gt --from-django-fsm app.Model`` (in the issue's design) did not
  exist.
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Dict, List

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

pytest.importorskip("django_fsm")

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parent / "project"
COMPARE = ROOT / "docs" / "_guide" / "comparisons" / "vs-django-fsm.md"
DJANGO_DOC = ROOT / "docs" / "_guide" / "integration-django.md"
CLI_DOC = ROOT / "docs" / "_guide" / "cli.md"
API_DOC = ROOT / "docs" / "api" / "index.md"
CMD = "xsm_migrate_fsm"
FLAGS = (
    "--field",
    "--statechart-field",
    "--dry-run",
    "--write-chart",
    "--machine-id",
    "--batch",
    "--database",
    "--map",
)


def _env(**extra: str) -> Dict[str, str]:
    e = {k: v for k, v in os.environ.items() if k != "PYTHONUTF8"}
    e.pop("DJANGO_SETTINGS_MODULE", None)
    e["PYTHONPATH"] = os.pathsep.join([str(ROOT / "src"), str(PROJECT)])
    e.update(extra)
    return e


def _run(argv: List[str], cwd: Path = PROJECT, **env: str) -> Any:
    return subprocess.run(
        argv,
        cwd=cwd,
        env=_env(**env),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=180,
    )


def _manage(*args: str, **env: str) -> Any:
    return _run([sys.executable, "manage.py", *args], **env)


# 📝 Every manage.py process gets its own per-pid SQLite file, so a flow
#    that needs data across commands runs them in ONE driver process.
DRIVER = textwrap.dedent("""
    import os, shlex, sys
    os.environ["DJANGO_SETTINGS_MODULE"] = "project.settings"
    import django
    django.setup()
    from django.core.management import call_command
    from django.core.management import execute_from_command_line
    call_command("migrate", verbosity=0)
    from legacy.models import Ticket
    seed = {seed!r}
    for value, n in seed.items():
        Ticket.objects.bulk_create([Ticket(state=value) for _ in range(n)])
    for line in {lines!r}:
        sys.stdout.write("$ " + line + "\\n")
        sys.stdout.flush()
        argv = shlex.split(line)
        assert argv[:2] == ["python", "manage.py"], argv
        try:
            execute_from_command_line(["manage.py", *argv[2:]])
        except SystemExit as exc:
            if exc.code:
                raise
        sys.stdout.flush()
""")


def _drive(lines: List[str], seed: Dict[str, int], **env: str) -> Any:
    code = DRIVER.format(seed=seed, lines=lines)
    return _run([sys.executable, "-c", code], **env)


def _out(*args: Any) -> str:
    buf = io.StringIO()
    call_command(*args, stdout=buf, stderr=io.StringIO())
    return buf.getvalue()


def _section(text: str, title: str) -> str:
    start = text.index(title)
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


# -----------------------------------------------------------------------------
# 🔥 Operator errors are CommandErrors (exit 1), validated up front
# -----------------------------------------------------------------------------
class TestOperatorErrors:
    @pytest.mark.parametrize("n", ["0", "-5"])
    def test_bad_batch(self, n: str) -> None:
        with pytest.raises(CommandError, match="--batch must be >= 1"):
            _out(CMD, "legacy.Ticket", "--batch", n)

    @pytest.mark.parametrize("item", ["foo", "a=b=c", "x=", "="])
    def test_malformed_map(self, item: str) -> None:
        with pytest.raises(CommandError, match="expects OLD=NEW"):
            _out(CMD, "legacy.Ticket", "--map", item)

    def test_contradictory_map(self) -> None:
        with pytest.raises(CommandError, match="given twice"):
            _out(CMD, "legacy.Ticket", "--map", "a=new", "--map", "a=closed")
        # the same pair twice is harmless
        _out(CMD, "legacy.Ticket", "--map", "a=new", "--map", "a=new")

    def test_map_to_an_unknown_state_touches_nothing(self) -> None:
        from legacy.models import Ticket

        Ticket.objects.create(state="new")
        with pytest.raises(CommandError, match="no state 'nope'"):
            _out(CMD, "legacy.Ticket", "--map", "x=nope")
        assert Ticket.objects.filter(statechart__isnull=True).count() == 1

    def test_unused_map_is_flagged_as_a_typo(self) -> None:
        from legacy.models import Ticket

        Ticket.objects.create(state="new")
        out = _out(CMD, "legacy.Ticket", "--map", "opne=new")
        assert "no row has state = 'opne' (typo?)" in out, out

    def test_wrong_statechart_field_names_the_candidates(self) -> None:
        with pytest.raises(CommandError, match="one of: statechart"):
            _out(CMD, "legacy.Ticket", "--statechart-field", "nope")

    def test_unknown_database(self) -> None:
        with pytest.raises(CommandError, match="unknown --database 'x'"):
            _out(CMD, "legacy.Ticket", "--database", "x")

    def test_model_errors(self) -> None:
        with pytest.raises(CommandError, match="unknown model"):
            _out(CMD, "Legacy.Ticket", "--dry-run")
        # a model with no FSMField at all
        with pytest.raises(CommandError, match="no field named 'state'"):
            _out(CMD, "shop.Order", "--dry-run")
        with pytest.raises(CommandError, match="FSMFields on the model"):
            _out(CMD, "legacy.Ticket", "--field", "status", "--dry-run")

    def test_unwritable_write_chart(self, tmp_path: Path) -> None:
        blocker = tmp_path / "file"
        blocker.write_text("x", encoding="utf-8")
        with pytest.raises(CommandError, match="cannot write"):
            _out(
                CMD, "legacy.Ticket", "--dry-run", "--write-chart",
                str(blocker / "sub" / "t.json"),
            )  # fmt: skip


def test_summary_counts_add_up() -> None:
    from legacy.models import Ticket

    for value, n in (("new", 7), ("closed", 3), ("open", 4), ("", 2)):
        Ticket.objects.bulk_create([Ticket(state=value) for _ in range(n)])
    before = Ticket.objects.filter(statechart__isnull=True).count()
    out = _out(CMD, "legacy.Ticket", "--batch", "3")
    m = re.search(r"migrated (\d+) row\(s\).*; (\d+) remaining", out)
    assert m, out
    done, remaining = int(m[1]), int(m[2])
    skipped = int(re.search(r"skipped (\d+) row", out)[1])  # type: ignore
    assert (done, skipped, remaining) == (10, 6, 6)
    assert "(6 of them skipped, below)" in out
    assert done + remaining == before
    assert "'open': 4 row(s)" in out and "'': 2 row(s)" in out
    out = _out(CMD, "legacy.Ticket", "--map", "open=new", "--map", "=new")
    assert "migrated 6 row(s)" in out and "0 remaining" in out, out
    assert "skipped" not in out


# -----------------------------------------------------------------------------
# 🖥️ Real processes: help, pipes, consoles, unmigrated database
# -----------------------------------------------------------------------------
def test_help_lists_every_flag() -> None:
    p = _manage(CMD, "--help")
    assert p.returncode == 0
    text = p.stdout.decode("utf-8")
    for flag in FLAGS:
        assert flag in text, flag


def test_dry_run_stdout_is_pipeable_json() -> None:
    p = _manage(CMD, "legacy.Ticket", "--dry-run")
    assert p.returncode == 0, p.stderr
    chart = json.loads(p.stdout.decode("utf-8"))
    assert chart["id"] == "ticket"
    assert b"Migrating legacy.Ticket.state" in p.stderr
    tool = subprocess.run(
        [sys.executable, "-m", "json.tool"],
        input=p.stdout,
        capture_output=True,
        timeout=60,
    )
    assert tool.returncode == 0, tool.stderr


def test_unmigrated_database_is_exit_1_not_a_traceback() -> None:
    p = _manage(CMD, "legacy.Ticket")
    assert p.returncode == 1 and b"Traceback" not in p.stderr, p.stderr
    assert b"is the database migrated?" in p.stderr


@pytest.mark.parametrize("env", [{}, {"NO_COLOR": "1"}, {"TERM": "dumb"}])
def test_warning_on_cp1252_pipe(env: Dict[str, str]) -> None:
    line = "python manage.py xsm_migrate_fsm legacy.Ticket --map opne=new"
    p = _drive([line], {"new": 3, "open": 2}, PYTHONIOENCODING="cp1252", **env)
    assert p.returncode == 0, p.stderr
    assert b"Traceback" not in p.stderr
    out = p.stdout.decode("cp1252")
    assert "\x1b[" not in out  # a pipe is not a TTY: no ANSI style
    assert "skipped 2 row(s)" in out and "(typo?)" in out


# -----------------------------------------------------------------------------
# 🔁 xsm gt --from-django-fsm (step 1 outside manage.py)
# -----------------------------------------------------------------------------
def _xsm(*args: str, cwd: Path, **env: str) -> Any:
    argv = [sys.executable, "-c", "from xstate_statemachine.cli.__main__ "
            "import main; main()", *args]  # fmt: skip
    return _run(argv, cwd=cwd, **env)


def test_gt_from_django_fsm(tmp_path: Path) -> None:
    p = _xsm("gt", "--from-django-fsm", "legacy.Ticket", "-o",
             str(tmp_path), cwd=PROJECT)  # fmt: skip
    assert p.returncode == 2 and b"Traceback" not in p.stderr
    err = (p.stdout + p.stderr).decode("utf-8", "replace")
    assert "DJANGO_SETTINGS_MODULE" in err
    dsm = {"DJANGO_SETTINGS_MODULE": "project.settings"}
    p = _xsm("gt", "--from-django-fsm", "legacy.Ticket", "-o",
             str(tmp_path), cwd=PROJECT, **dsm)  # fmt: skip
    assert p.returncode == 0, p.stderr
    chart = json.loads((tmp_path / "ticket.json").read_text("utf-8"))
    assert set(chart["states"]) == {"new", "in_progress", "resolved",
                                    "closed"}  # fmt: skip
    assert (tmp_path / "ticket_logic.py").is_file()
    p = _xsm("gt", "--from-django-fsm", "shop.Order", "-o",
             str(tmp_path), cwd=PROJECT, **dsm)  # fmt: skip
    assert p.returncode == 2 and b"Traceback" not in p.stderr
    err = (p.stdout + p.stderr).decode("utf-8", "replace")
    assert "no field named 'state'" in err


# -----------------------------------------------------------------------------
# 📚 The recipe, run literally; the verification script; docs truth
# -----------------------------------------------------------------------------
def _recipe() -> str:
    return _section(COMPARE.read_text(encoding="utf-8"), "## Migration recipe")


def test_recipe_runs_literally() -> None:
    cmds = re.findall(
        r"`(python manage\.py xsm_migrate_fsm [^`]+)`", _recipe()
    )
    assert len(cmds) == 2, cmds  # step 1 (--dry-run) and step 3
    # the docs use the shop.Order example; the test project's FSM model
    # is legacy.Ticket -- same flags, literally
    lines = [c.replace("shop.Order", "legacy.Ticket") for c in cmds]
    lines.insert(1, "python manage.py makemigrations legacy --check "
                    "--dry-run")  # fmt: skip
    p = _drive(lines, {"new": 5, "resolved": 2, "open": 1})
    assert p.returncode == 0, p.stderr
    out = p.stdout.decode("utf-8")
    step1 = out.split("$ ")[1]
    json.loads(step1.split("\n", 1)[1])  # step 1: the chart, only
    assert "No changes detected" in out  # step 2: field already added
    assert "migrated 7 row(s)" in out and "'open': 1 row(s)" in out


def test_recipe_text_is_current() -> None:
    sec = _recipe()
    for needle in ("two-way", "--map", "skipped and reported per value",
                   "re-adopts the snapshot", "stderr",
                   "--from-django-fsm"):  # fmt: skip
        assert needle in sec, needle
    from xstate_statemachine.contrib.django.management.commands import (
        xsm_migrate_fsm,
    )

    for needle in ("two-way", "--map OLD=NEW", "re-adopts"):
        assert needle in xsm_migrate_fsm.RECIPE.replace("\n     ", " ")


def test_verification_script_runs() -> None:
    script = ROOT / "scripts" / "verify" / "django_fsm_migration.py"
    p = _run([sys.executable, str(script)], cwd=ROOT)
    assert p.returncode == 0, p.stderr
    assert p.stdout.decode("utf-8").rstrip().endswith("ALL OK")


def test_docs_name_the_new_surface() -> None:
    dj = DJANGO_DOC.read_text(encoding="utf-8")
    row = re.search(r"^\| `xsm_migrate_fsm ([^`]*)`", dj, re.M)
    assert row, "management command table row"
    for flag in FLAGS:
        assert flag in row[1], flag
    assert "--map OLD=NEW" in dj and "both directions" in dj
    api = API_DOC.read_text(encoding="utf-8")
    for needle in ("value_map=", "unknown=", "`fsm_fields`", "two-way"):
        assert needle in api, needle
    from xstate_statemachine.contrib.django import fsm

    assert hasattr(fsm, "fsm_fields")
    cli = CLI_DOC.read_text(encoding="utf-8")
    assert "`--from-django-fsm`" in cli and "`--fsm-field`" in cli
    sec = _section(cli, "## `manage.py xsm_")
    assert "xsm_migrate_fsm" in sec and "--map" in sec
    import argparse

    from xstate_statemachine.cli.args import get_parser

    sub = next(
        a
        for a in get_parser()._actions
        if isinstance(a, argparse._SubParsersAction)
    )
    gen = sub.choices["generate-template"].format_help()
    assert "--from-django-fsm" in gen and "--fsm-field" in gen
