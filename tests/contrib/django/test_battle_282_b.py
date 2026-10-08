# tests/contrib/django/test_battle_282_b.py
"""#282 battle, adversary B: the ``xsm_*`` management commands and docs.

Defects pinned here (each was a raw traceback, not a `CommandError`):
a malformed *pk*; an unknown ``--database``; an unwritable ``-o``; a
model whose `StatechartField` cannot be chosen. ``xsm_snapshots`` and
``xsm_inspect <pk>`` had no ``--database`` at all.
"""

from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db

ROOT = Path(__file__).resolve().parents[3]
PROJECT = Path(__file__).resolve().parent / "project"
DOC = ROOT / "docs" / "_guide" / "integration-django.md"
CLI_DOC = ROOT / "docs" / "_guide" / "cli.md"
TEMPLATES = (
    ROOT / "src" / "xstate_statemachine" / "contrib" / "django" / "templates"
)
EXAMPLE = ROOT / "examples" / "integrations" / "django_approvals"
COMMANDS = (
    "xsm_inspect",
    "xsm_diagram",
    "xsm_docs",
    "xsm_simulate",
    "xsm_deadlines",
    "xsm_snapshots",
    "xsm_refresh_columns",
    "xsm_migrate_fsm",
)
HAS_OTHER = "other" in settings.DATABASES


def _cmd(*args: Any) -> str:
    out = io.StringIO()
    call_command(*args, stdout=out, stderr=io.StringIO())
    return out.getvalue()


def _manage(*args: str, **env: str) -> Any:
    e = {k: v for k, v in os.environ.items() if k != "PYTHONUTF8"}
    e.pop("DJANGO_SETTINGS_MODULE", None)
    e.update(env)
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=PROJECT,
        env=e,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=120,
    )


# -----------------------------------------------------------------------------
# 🔥 Defects: operator errors are CommandErrors, never tracebacks
# -----------------------------------------------------------------------------
class TestOperatorErrors:
    def test_malformed_pk_is_a_command_error_before_any_output(self) -> None:
        out = io.StringIO()
        with pytest.raises(CommandError, match="bad pk 'abc'"):
            call_command("xsm_inspect", "shop.Order", "abc", stdout=out)
        assert out.getvalue() == ""
        with pytest.raises(CommandError, match="not found"):
            call_command("xsm_inspect", "shop.Order", "999999", stdout=out)
        assert out.getvalue() == ""

    @pytest.mark.parametrize(
        "args",
        [
            ("xsm_inspect", "shop.Order", "1"),
            ("xsm_snapshots", "shop.Order"),
            ("xsm_refresh_columns", "shop.Order"),
            ("xsm_deadlines",),
        ],
    )
    def test_unknown_database_alias(self, args: Any) -> None:
        with pytest.raises(CommandError, match="unknown --database 'nope'"):
            _cmd(*args, "--database", "nope")

    def test_unwritable_output_is_a_command_error(self, tmp_path: Any) -> None:
        blocker = tmp_path / "file"
        blocker.write_text("x")
        with pytest.raises(CommandError, match="Error"):
            _cmd("xsm_docs", "shop.Order", "-o", str(blocker / "d"))
        with pytest.raises(CommandError, match="Error"):
            _cmd("xsm_diagram", "shop.Order", "-o", str(blocker / "d.mmd"))

    def test_unchoosable_field_is_a_command_error(self, monkeypatch) -> None:
        from shop.models import Order

        monkeypatch.setattr(Order, "statechart_field_name", "nope", False)
        for args in (
            ("xsm_snapshots", "shop.Order"),
            ("xsm_refresh_columns", "shop.Order"),
        ):
            with pytest.raises(CommandError, match="exactly one"):
                _cmd(*args)

    def test_label_errors(self) -> None:
        for label in ("shop", "shop.Nope", "nope.Model", "auth.User"):
            with pytest.raises(CommandError):
                _cmd("xsm_snapshots", label)

    def test_snapshots_limit_must_be_positive(self) -> None:
        with pytest.raises(CommandError, match="--limit"):
            _cmd("xsm_snapshots", "shop.Order", "--limit", "0")


# -----------------------------------------------------------------------------
# 🗄️ --database other
# -----------------------------------------------------------------------------
@pytest.mark.skipif(not HAS_OTHER, reason="SQLite-only second alias")
@pytest.mark.django_db(databases=["default", "other"])
class TestOtherDatabase:
    def test_snapshots_and_inspect_read_the_named_alias(self) -> None:
        from shop.models import Order

        o = Order.objects.using("other").create(title="o")
        got = json.loads(
            _cmd(
                "xsm_snapshots", "shop.Order", "--json", "--database", "other"
            )
        )
        assert [r["key"] for r in got["snapshots"]] == [str(o.pk)]
        assert json.loads(_cmd("xsm_snapshots", "shop.Order", "--json"))[
            "count"
        ] == (Order.objects.count())
        got = _cmd(
            "xsm_inspect", "shop.Order", str(o.pk), "--database", "other"
        )
        assert f"row {o.pk}:" in got


# -----------------------------------------------------------------------------
# ✅ Confirmations
# -----------------------------------------------------------------------------
class TestConfirmations:
    def test_snapshots_json_is_valid_with_non_ascii(self) -> None:
        from shop.models import Approval

        Approval.objects.create(title="Café ✓ 審査")
        data = json.loads(_cmd("xsm_snapshots", "shop.Approval", "--json"))
        assert data["count"] == 1 and data["model"] == "shop.Approval"

    def test_refresh_dry_run_counts_and_writes_nothing(self) -> None:
        from shop.models import Order

        o = Order.objects.create()
        Order.objects.filter(pk=o.pk).update(statechart_state="bogus")
        got = _cmd("xsm_refresh_columns", "shop.Order", "--dry-run")
        assert got == "shop.Order: would change 1 row(s)\n"
        assert Order.objects.get(pk=o.pk).statechart_state == "bogus"
        assert "changed 1 row(s)" in _cmd("xsm_refresh_columns", "shop.Order")
        assert Order.objects.get(pk=o.pk).statechart_state != "bogus"

    def test_unicode_chart_matches_cli_byte_for_byte(
        self, tmp_path: Any, monkeypatch: Any
    ) -> None:
        from shop.models import Order

        from xstate_statemachine.cli.commands import reset_console
        from xstate_statemachine.cli.commands.diagram import run_diagram
        from xstate_statemachine.cli.commands.docs import run_docs
        from xstate_statemachine.cli.commands.inspect import run_inspect

        chart = tmp_path / "u.json"
        chart.write_text(
            json.dumps(
                {
                    "id": "u",
                    "description": "Café ✓ → 審査",
                    "initial": "a",
                    "states": {
                        "a": {"description": "ünï ✓", "on": {"GO": "b"}},
                        "b": {},
                    },
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(Order, "statechart_machine", str(chart))
        monkeypatch.setattr(Order, "_xsm_machine_cache", None, False)

        def direct(fn: Any, *a: Any, **kw: Any) -> str:
            from contextlib import redirect_stdout

            from django.core.management.base import OutputWrapper

            from xstate_statemachine.contrib.django.management.commands._resolve import (  # noqa: E501
                console,
            )

            buf = io.StringIO()
            console({"plain": True}, OutputWrapper(buf))
            with redirect_stdout(buf):
                try:
                    fn(*a, **kw)
                finally:
                    reset_console()
            return buf.getvalue()

        p = str(chart)
        assert _cmd("xsm_inspect", "shop.Order", "--plain") == direct(
            run_inspect, p
        )
        assert _cmd("xsm_docs", "shop.Order", "--plain") == direct(
            run_docs, [p]
        )
        got = _cmd("xsm_diagram", "shop.Order", "-f", "ascii", "--plain")
        assert got == direct(run_diagram, p, fmt="ascii")
        assert "· 1 events" in _cmd("xsm_docs", "shop.Order", "--plain")

    @pytest.mark.django_db(transaction=True)
    def test_forever_off_the_main_thread_stops_cleanly(
        self, monkeypatch: Any
    ) -> None:
        import signal

        from xstate_statemachine.contrib.django.management.commands import (
            xsm_deadlines,
        )

        stop = threading.Event()
        orig = xsm_deadlines.Command._forever
        monkeypatch.setattr(
            xsm_deadlines.Command,
            "_forever",
            lambda self, sc, iv: orig(self, sc, iv, stop),
        )
        before = signal.getsignal(signal.SIGINT)
        out = io.StringIO()
        errors: list = []

        def run() -> None:
            try:
                call_command(
                    "xsm_deadlines",
                    "shop.Order",
                    "--forever",
                    "--interval",
                    "0.05",
                    stdout=out,
                )
            except BaseException as exc:  # pragma: no cover - failure
                errors.append(exc)
            finally:
                from django.db import connections

                connections.close_all()

        t = threading.Thread(target=run)
        t.start()
        t.join(0.5)
        stop.set()
        t.join(10)
        assert not t.is_alive() and not errors
        assert out.getvalue().endswith("xsm_deadlines: stopped\n")
        assert signal.getsignal(signal.SIGINT) is before
        with pytest.raises(CommandError, match="--interval"):
            _cmd("xsm_deadlines", "--interval", "0")


# -----------------------------------------------------------------------------
# 🖥️ Real processes: exit codes, help, consoles, stdin
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("cmd", COMMANDS)
def test_help_is_0_and_bad_flag_is_2(cmd: str) -> None:
    assert _manage(cmd, "--help").returncode == 0
    p = _manage(cmd, "--bogus")
    assert p.returncode == 2 and b"Traceback" not in p.stderr


def test_exit_codes_and_consoles() -> None:
    p = _manage("xsm_diagram", "shop.Order", "-f", "svg")
    assert p.returncode == 2 and b"invalid choice" in p.stderr
    p = _manage("xsm_inspect", "shop.Nope")
    assert p.returncode == 1 and b"Traceback" not in p.stderr
    for env in ({}, {"NO_COLOR": "1"}, {"TERM": "dumb"}):
        p = _manage(
            "xsm_inspect", "shop.Approval", PYTHONIOENCODING="cp1252", **env
        )
        assert p.returncode == 0, p.stderr
        if env:
            assert b"\x1b[" not in p.stdout
    p = _manage("xsm_inspect", "shop.Approval", "--plain")
    assert b"\x1b[" not in p.stdout and "\u2500" not in p.stdout.decode(
        "utf-8", "replace"
    )


def test_simulate_with_closed_stdin_never_hangs() -> None:
    p = _manage("xsm_simulate", "shop.Order", "--plain")
    assert p.returncode == 0 and b"order" in p.stdout
    p = _manage("xsm_simulate", "shop.Order", "-e", "SUBMIT,NOPE", "--json")
    assert p.returncode == 0
    json.loads(p.stdout.decode("utf-8"))


# -----------------------------------------------------------------------------
# 📚 Docs truth
# -----------------------------------------------------------------------------
def _help(cmd: str) -> str:
    from django.core.management import load_command_class

    c = load_command_class("xstate_statemachine.contrib.django", cmd)
    return c.create_parser("manage.py", cmd).format_help()


def _section(text: str, title: str) -> str:
    start = text.index(title)
    nxt = text.find("\n## ", start + 1)
    nxt3 = text.find("\n### ", start + 1)
    ends = [n for n in (nxt, nxt3) if n != -1]
    return text[start : min(ends) if ends else len(text)]


def test_command_table_flags_exist_in_help() -> None:
    sec = _section(DOC.read_text(encoding="utf-8"), "### Management commands")
    rows = re.findall(r"^\| `(xsm_\w+) ([^`]*)`", sec, re.M)
    assert sorted(r[0] for r in rows) == sorted(COMMANDS)
    for cmd, usage in rows:
        helptext = _help(cmd)
        for flag in re.findall(r"(?<![\w-])(--?[a-z][\w-]*)", usage):
            assert flag in helptext, (cmd, flag)


def test_admin_section_names_are_real() -> None:
    from xstate_statemachine.contrib.django import admin as xadmin

    sec = _section(DOC.read_text(encoding="utf-8"), "### Admin")
    for tpl, blocks in re.findall(
        r"`(admin/xsm/[\w.]+\.html)` \(blocks? ([^)]*)\)", sec
    ):
        html = (TEMPLATES / tpl).read_text(encoding="utf-8")
        for b in re.findall(r"`(xsm_\w+)`", blocks):
            assert "{% block " + b + " %}" in html, (tpl, b)
    for attr in ("xsm_confirm_events", "xsm_bulk_actions"):
        assert attr in sec and hasattr(xadmin.StatechartAdminMixin, attr)
    assert "max_rows = 50" in sec
    assert xadmin.TransitionLogInline.max_rows == 50
    assert "XSM_ADMIN_TRANSITIONLOG = False" in sec
    assert "/statechart/" in sec and "xsm_diagram" in sec


def test_cli_doc_manage_py_section_names_real_events() -> None:
    sec = _section(CLI_DOC.read_text(encoding="utf-8"), "## `manage.py xsm_")
    chart = (EXAMPLE / "machine.json").read_text(encoding="utf-8")
    for events in re.findall(r"-e ([A-Z_,]+)", sec):
        for ev in events.split(","):
            assert f'"{ev}"' in chart, ev


def test_example_readme_celery_names_exist() -> None:
    pytest.importorskip("celery")
    import xstate_statemachine.contrib.celery as cel

    text = (EXAMPLE / "README.md").read_text(encoding="utf-8")
    for name in ("xsm_deadlines_every", "DurableTimerScheduler"):
        assert name in text and name in cel.__all__
