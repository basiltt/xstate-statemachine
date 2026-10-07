# tests/contrib/django/test_battle_280_b.py
"""#280 battle, adversary B: migrations, the data-migration helper, the
management commands, the admin and the docs.

The migration tests build a throw-away Django project in ``tmp_path`` and
drive ``manage.py`` in subprocesses (Django configures one project per
process; this one is the library's test project).
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import textwrap
import threading
from pathlib import Path
from typing import Any, Dict, List

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.urls import reverse

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PROJECT = Path(__file__).resolve().parent / "project"
CHART = {
    "id": "m",
    "initial": "a",
    "states": {"a": {"on": {"GO": "b"}}, "b": {}},
}


# -----------------------------------------------------------------------------
# 🧪 a throw-away project
# -----------------------------------------------------------------------------
SETTINGS = """
import os
SECRET_KEY = "x"
INSTALLED_APPS = ["django.contrib.contenttypes", "django.contrib.auth",
                  "xstate_statemachine.contrib.django", "wf"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3",
                         "NAME": os.path.join(os.path.dirname(__file__),
                                              "db.sqlite3")}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
"""
MANAGE = """
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"
from django.core.management import execute_from_command_line
execute_from_command_line(sys.argv)
"""
MODELS = """
from django.db import models
from xstate_statemachine.contrib.django.fields import StatechartField
from xstate_statemachine.contrib.django.mixin import StatechartModelMixin

CHART = {chart!r}


class Doc(StatechartModelMixin, models.Model):
    statechart_machine = CHART
    statechart_field_name = "{name}"
    {name} = StatechartField(state_max_length=100)
    legacy = StatechartField(denormalize=False)
"""


class Proj:
    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "wf" / "migrations").mkdir(parents=True)
        (root / "wf" / "__init__.py").write_text("")
        (root / "wf" / "migrations" / "__init__.py").write_text("")
        (root / "settings.py").write_text(SETTINGS)
        (root / "manage.py").write_text(MANAGE)

    def models(self, name: str) -> None:
        (self.root / "wf" / "models.py").write_text(
            MODELS.format(chart=CHART, name=name)
        )

    def run(self, *args: str, stdin: str = "", ok: bool = True) -> str:
        env = dict(os.environ, PYTHONPATH=str(SRC), PYTHONUTF8="1")
        env.pop("DJANGO_SETTINGS_MODULE", None)
        p = subprocess.run(
            [sys.executable, "manage.py", *args],
            cwd=self.root,
            env=env,
            input=stdin,
            capture_output=True,
            text=True,
            timeout=300,
        )
        out = p.stdout + p.stderr
        assert (p.returncode == 0) is ok, out
        return out

    def migration(self, prefix: str) -> str:
        (f,) = (self.root / "wf" / "migrations").glob(prefix + "*.py")
        return f.read_text()


@pytest.fixture
def proj(tmp_path: Path) -> Proj:
    return Proj(tmp_path)


class TestMigrations:
    def test_shipped_migrations_are_complete_and_reversible(
        self, proj: Proj
    ) -> None:
        proj.models("workflow")
        proj.run("makemigrations", "xsm_django", "--check", "--dry-run")
        proj.run("migrate", "-v0")
        out = proj.run("migrate", "xsm_django", "zero")
        assert "Unapplying xsm_django.0001_initial... OK" in out
        proj.run("migrate", "-v0")  # and forwards again

    def test_custom_name_second_field_rename_and_sqlmigrate(
        self, proj: Proj
    ) -> None:
        proj.models("workflow")
        proj.run("makemigrations", "wf", "-v0")
        initial = proj.migration("0001")
        for col in ("workflow_state", "workflow_state_ids"):
            # 📝 Django quotes field names with ' or " depending on the
            #    installed version / formatter -- match either
            assert f'"{col}"' in initial or f"'{col}'" in initial, initial
        assert "workflow_version" in initial
        assert "workflow_machine_version" in initial
        assert "legacy_state" not in initial  # denormalize=False
        assert "denormalize=False" in initial
        assert "state_max_length=100" in initial
        proj.run("makemigrations", "--check", "--dry-run")  # stable
        sql = proj.run("sqlmigrate", "wf", "0001")
        assert re.search(r'CREATE INDEX .*\(["`]?workflow_state["`]?\)', sql)
        proj.run("migrate", "-v0")
        proj.run(
            "shell", "-c", "from wf.models import Doc; Doc.objects.create()"
        )
        # 🔥 the classic footgun: renaming the field must rename the
        #    siblings too, keeping the data (the autodetector asks once
        #    per column; answer yes to each).
        proj.models("flow")
        proj.run("makemigrations", "wf", "-v0", stdin="y\n" * 10)
        rename = proj.migration("0002")
        assert "RemoveField" not in rename and "AddField" not in rename
        for suffix in (
            "",
            "_state",
            "_state_ids",
            "_version",
            "_machine_version",
        ):
            assert f'old_name="workflow{suffix}"' in rename, suffix
            assert f'new_name="flow{suffix}"' in rename, suffix
        proj.run("migrate", "-v0")
        proj.run("makemigrations", "--check", "--dry-run")
        out = proj.run(
            "shell",
            "-c",
            "from wf.models import Doc; d = Doc.objects.get();"
            "print('STATE', d.flow_state, d.state);"
            "d.send('GO'); print('AFTER', Doc.objects.in_state('m.b').count())",
        )
        assert "STATE m.a m.a" in out and "AFTER 1" in out
        proj.run("migrate", "wf", "zero", "-v0")  # reverse the rename too

    def test_deconstruct_round_trips_every_argument(self) -> None:
        from xstate_statemachine.contrib.django.fields import StatechartField

        for kw in (
            {},
            {"denormalize": False},
            {"state_max_length": 64, "max_snapshot_bytes": 2048},
            {"editable": True},
        ):
            f = StatechartField(**kw)
            name, path, args, kwargs = f.deconstruct()
            assert path.endswith("fields.StatechartField")
            g = StatechartField(*args, **kwargs)
            assert g.deconstruct()[2:] == (args, kwargs), kw
            for attr in (
                "denormalize",
                "state_max_length",
                "max_snapshot_bytes",
                "null",
                "editable",
            ):
                assert getattr(g, attr) == getattr(f, attr), (kw, attr)

    def test_deconstruct_keeps_null_false(self) -> None:
        from xstate_statemachine.contrib.django.fields import StatechartField

        for key in ("null", "blank"):
            f = StatechartField(**{key: False})
            _, _, args, kwargs = f.deconstruct()
            assert getattr(StatechartField(*args, **kwargs), key) is False

    def test_data_migration_uses_the_helper(self, proj: Proj) -> None:
        proj.models("workflow")
        proj.run("makemigrations", "wf", "-v0")
        proj.run("migrate", "-v0")
        proj.run(
            "shell",
            "-c",
            "from wf.models import Doc\n"
            "for _ in range(3): Doc.objects.create().send('GO')\n"
            "Doc.objects.update(workflow_state='stale', workflow_state_ids=None)",
        )
        (proj.root / "wf" / "migrations" / "0002_refresh.py").write_text(
            textwrap.dedent("""
                from django.db import migrations
                from xstate_statemachine.contrib.django.migration_helpers import (
                    refresh_statechart_columns_op,
                )

                def tag(snap):
                    snap["context"]["migrated"] = True
                    return snap

                class Migration(migrations.Migration):
                    dependencies = [("wf", "0001_initial")]
                    operations = [
                        refresh_statechart_columns_op(
                            "wf", "Doc", "workflow", batch=2, migrate=tag
                        )
                    ]
                """)
        )
        proj.run("migrate", "-v0")
        out = proj.run(
            "shell",
            "-c",
            "from wf.models import Doc\n"
            "for d in Doc.objects.all(): print('ROW', d.workflow_state,"
            " d.workflow_state_ids, d.workflow['context'], d.workflow_version)",
        )
        rows = [ln for ln in out.splitlines() if ln.startswith("ROW")]
        assert len(rows) == 3
        for ln in rows:
            assert "ROW m.b ['m.b'] {'migrated': True}" in ln, ln
        proj.run("migrate", "wf", "0001", "-v0")  # reversible (noop)


# -----------------------------------------------------------------------------
# 🧰 the helper and xsm_refresh_columns
# -----------------------------------------------------------------------------
@pytest.mark.django_db
class TestRefreshColumns:
    def test_migrate_step_mutating_in_place_is_written(self) -> None:
        from shop.models import Approval
        from xstate_statemachine.contrib.django import (
            refresh_statechart_columns,
        )

        a = Approval.objects.create()

        def mig(snap: Dict[str, Any]) -> Dict[str, Any]:
            snap["context"]["notes"] = ["imported"]  # nested, in place
            return snap

        assert refresh_statechart_columns(Approval, migrate=mig) == 1
        a.refresh_from_db()
        assert a.statechart["context"]["notes"] == ["imported"]
        assert a.statechart_version == 1  # fenced writers conflict
        # nothing left to do: no write, no count
        assert refresh_statechart_columns(Approval) == 0

    def test_command_batches_dry_run_and_bad_args(self) -> None:
        from shop.models import Counter

        Counter.objects.bulk_create(
            [Counter(statechart=_snap("counter.on")) for _ in range(2500)]
        )
        assert Counter.objects.filter(statechart_state=None).count() == 2500
        out = _call("xsm_refresh_columns", "shop.Counter", "--dry-run")
        assert "would change 2500 row(s)" in out
        assert Counter.objects.filter(statechart_state=None).count() == 2500
        out = _call("xsm_refresh_columns", "shop.Counter", "--batch", "333")
        assert "changed 2500 row(s)" in out
        assert Counter.objects.in_state("counter.on").count() == 2500
        out = _call("xsm_refresh_columns", "shop.Counter")
        assert "changed 0 row(s)" in out
        with pytest.raises(CommandError, match="--batch"):
            _call("xsm_refresh_columns", "shop.Counter", "--batch", "0")
        with pytest.raises(CommandError, match="unknown model"):
            _call("xsm_refresh_columns", "nope.Model")

    def test_memory_is_bounded_by_the_batch(self, monkeypatch: Any) -> None:
        from shop.models import Counter
        from xstate_statemachine.contrib.django import migration_helpers

        Counter.objects.bulk_create(
            [Counter(statechart=_snap("counter.on")) for _ in range(50)]
        )
        sizes: List[int] = []
        real = migration_helpers._row_update

        seen = {"batch": 0}

        def spy(row: Any, *a: Any) -> Any:
            seen["batch"] += 1
            return real(row, *a)

        monkeypatch.setattr(migration_helpers, "_row_update", spy)
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as q:
            migration_helpers.refresh_statechart_columns(Counter, batch=7)
        selects = [
            x["sql"]
            for x in q.captured_queries
            if x["sql"].startswith("SELECT")
        ]
        sizes = [int(re.search(r"LIMIT (\d+)", s).group(1)) for s in selects]
        assert sizes and set(sizes) == {7}
        assert len(selects) == 50 // 7 + 2  # 8 pages incl. the last + empty
        assert seen["batch"] == 50


def _snap(state: str) -> Dict[str, Any]:
    return {"state_ids": [state], "context": {"n": 0}, "version": 4}


def _call(*args: str) -> str:
    import io

    out = io.StringIO()
    call_command(*args, stdout=out, stderr=out)
    return out.getvalue()


# -----------------------------------------------------------------------------
# ⌨️ commands: help, exit codes, xsm_deadlines --forever stop, cp1252
# -----------------------------------------------------------------------------
COMMANDS = (
    "xsm_deadlines",
    "xsm_diagram",
    "xsm_docs",
    "xsm_inspect",
    "xsm_migrate_fsm",
    "xsm_refresh_columns",
    "xsm_simulate",
    "xsm_snapshots",
)


def _manage(*args: str, env: Any = None, timeout: int = 120) -> Any:
    e = dict(os.environ, PYTHONPATH=str(SRC), **(env or {}))
    e.pop("DJANGO_SETTINGS_MODULE", None)
    return subprocess.run(
        [sys.executable, "manage.py", *args],
        cwd=PROJECT,
        env=e,
        capture_output=True,
        timeout=timeout,
    )


class TestCommandsCli:
    @pytest.mark.parametrize("cmd", COMMANDS)
    def test_help_exits_zero(self, cmd: str) -> None:
        p = _manage(cmd, "--help")
        assert p.returncode == 0, p.stderr
        assert b"usage:" in p.stdout

    def test_plain_on_a_cp1252_console(self) -> None:
        p = _manage(
            "xsm_inspect",
            "shop.Approval",
            "--plain",
            env={"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"},
        )
        assert p.returncode == 0, p.stderr
        assert b"approval" in p.stdout
        # 📝 no crash, and the output is valid cp1252 (the CLI's path
        #    truncation glyph "…" is cp1252 0x85, so not pure ASCII).
        p.stdout.decode("cp1252")
        assert b"Traceback" not in p.stderr

    def test_bad_label_and_bad_options_are_command_errors(self) -> None:
        for args in (
            ("xsm_deadlines", "nope.Model"),
            ("xsm_deadlines", "--limit", "0"),
            ("xsm_deadlines", "--interval", "0"),
            ("xsm_deadlines", "auth.User"),
            ("xsm_inspect", "nope.Model"),
        ):
            p = _manage(*args, env={"PYTHONUTF8": "1"})
            assert p.returncode == 1, args
            assert b"CommandError" in p.stderr, args
            assert b"Traceback" not in p.stderr, args


@pytest.mark.django_db
class TestDeadlinesCommand:
    def test_unmigrated_database_is_a_command_error(
        self, monkeypatch: Any
    ) -> None:
        from django.db import OperationalError

        from xstate_statemachine.contrib.django import _deadlines

        def boom(*a: Any, **k: Any) -> Any:
            raise OperationalError(
                "no such table: xsm_django_statechartdeadline"
            )

        monkeypatch.setattr(_deadlines, "due", boom)
        with pytest.raises(CommandError, match="manage.py migrate"):
            _call("xsm_deadlines", "shop.Order")

    def test_forever_stops_on_signal_after_the_current_pass(self) -> None:
        from xstate_statemachine.contrib.django.management.commands import (
            xsm_deadlines,
        )

        cmd = xsm_deadlines.Command()
        passes = []

        class Scanner:
            def run_once(self) -> int:
                passes.append(1)
                if len(passes) == 3:
                    stop.set()
                return 0

        stop = threading.Event()
        cmd._forever([(None, Scanner())], 0.001, stop)
        assert len(passes) == 3

    def test_sigint_handler_is_installed_and_restored(self) -> None:
        from xstate_statemachine.contrib.django.management.commands import (
            xsm_deadlines,
        )

        before = signal.getsignal(signal.SIGINT)
        stop = threading.Event()
        restore = xsm_deadlines._on_stop_signals(stop)
        try:
            handler = signal.getsignal(signal.SIGINT)
            assert handler is not before
            handler(signal.SIGINT, None)
            assert stop.is_set()
        finally:
            restore()
        assert signal.getsignal(signal.SIGINT) is before


# -----------------------------------------------------------------------------
# 🛠️ admin
# -----------------------------------------------------------------------------
def _staff(username: str, *perms: str) -> Any:
    U = get_user_model()
    u = U.objects.create_user(username, password="p", is_staff=True)
    for codename in perms:
        u.user_permissions.add(Permission.objects.get(codename=codename))
    return U.objects.get(pk=u.pk)


def _client(user: Any, csrf: bool = False) -> Client:
    c = Client(enforce_csrf_checks=csrf)
    c.force_login(user)
    return c


@pytest.mark.django_db
class TestAdmin:
    def _urls(self, obj: Any) -> Any:
        return (
            reverse("admin:shop_approval_change", args=[obj.pk]),
            reverse("admin:shop_approval_xsm_transition", args=[obj.pk]),
        )

    def test_view_only_user_post_is_403_and_nothing_audited(self) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        viewer = _staff("viewer", "view_approval", "approve_approval")
        change, url = self._urls(a)
        html = _client(viewer).get(change).content.decode()
        assert "_xsm_submit" not in html
        for ev in ("REJECT", "COMMENT"):
            r = _client(viewer).post(
                url, {"_xsm_event": ev, "_xsm_confirmed": "1"}
            )
            assert r.status_code == 403, ev
        a.refresh_from_db()
        assert a.state == "approval.pending" and a.history.count() == 0

    def test_confirm_form_carries_csrf_and_refuses_tokenless_post(
        self,
    ) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        boss = _staff(
            "boss", "view_approval", "change_approval", "approve_approval"
        )
        _, url = self._urls(a)
        c = _client(boss, csrf=True)
        page = c.get(url, {"_xsm_event": "APPROVE"}).content.decode()
        assert "csrfmiddlewaretoken" in page and 'name="reason"' in page
        r = c.post(url, {"_xsm_event": "APPROVE", "_xsm_confirmed": "1"})
        assert r.status_code == 403
        token = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', page)
        r = c.post(
            url,
            {
                "_xsm_event": "APPROVE",
                "_xsm_confirmed": "1",
                "reason": "ok",
                "csrfmiddlewaretoken": token.group(1),
            },
        )
        assert r.status_code == 302
        a.refresh_from_db()
        assert a.state == "approval.approved"

    def test_failing_action_is_a_message_not_a_500(self) -> None:
        from shop.models import Approval

        a = Approval.objects.create()
        boss = _staff("boss2", "view_approval", "change_approval")
        _, url = self._urls(a)
        r = _client(boss).post(url, {"_xsm_event": "BOOM"}, follow=True)
        assert r.status_code == 200

    def test_history_inline_is_capped(self) -> None:
        from shop.models import Approval
        from xstate_statemachine.contrib.django.admin import (
            TransitionLogInline,
        )

        a = Approval.objects.create()
        for i in range(120):
            a.send("COMMENT", text=str(i))
        boss = _staff("boss3", "view_approval", "change_approval")
        change, _ = self._urls(a)
        html = _client(boss).get(change).content.decode()
        rows = re.findall(r'class="field-seq">\s*<p>(\d+)</p>', html)
        assert len(rows) == TransitionLogInline.max_rows == 50
        assert rows[0] == "120"  # newest first
        assert len(html) < 400_000

    def test_state_list_filter_lists_every_state(self) -> None:
        from shop.models import Approval

        boss = _staff("boss4", "view_approval", "change_approval")
        html = (
            _client(boss)
            .get(reverse("admin:shop_approval_changelist"))
            .content.decode()
        )
        for sid in (
            "approval.pending",
            "approval.approved",
            "approval.rejected",
        ):
            assert f"xsm_state={sid}" in html

    def test_script_in_meta_title_and_state_is_escaped(
        self, monkeypatch: Any
    ) -> None:
        from shop.models import Approval
        from xstate_statemachine import create_machine

        evil = "<script>alert(1)</script>"
        chart = {
            "id": "approval",
            "initial": "pending",
            "states": {
                "pending": {
                    "meta": {"title": evil},
                    "on": {"COMMENT": {"meta": {"title": evil}}},
                }
            },
        }
        node = create_machine(chart)
        monkeypatch.setattr(
            Approval, "statechart_machine_node", lambda self: node
        )
        a = Approval.objects.create()
        boss = _staff("boss5", "view_approval", "change_approval")
        c = _client(boss)
        change, url = self._urls(a)
        for page in (
            c.get(change),
            c.get(reverse("admin:shop_approval_changelist")),
            c.get(url, {"_xsm_event": "COMMENT"}),
            c.post(url, {"_xsm_event": "COMMENT"}, follow=True),
        ):
            body = page.content.decode()
            assert evil not in body
        assert "&lt;script&gt;" in body
