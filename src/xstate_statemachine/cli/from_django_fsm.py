# src/xstate_statemachine/cli/from_django_fsm.py
# -----------------------------------------------------------------------------
# 🔁 xsm gt --from-django-fsm app.Model [--fsm-field state]  (#310)
# -----------------------------------------------------------------------------
"""Step 1 of the django-fsm migration outside ``manage.py``.

Import-only introspection: Django is configured from
``DJANGO_SETTINGS_MODULE`` and the model's ``@transition`` decorators are
read; no database connection is opened. The extracted chart is written
as ``<machine id>.json`` (into ``-o`` or the current directory) and then
generated from like any other JSON input.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, NoReturn, Optional

__all__ = ["chart_from_django_fsm"]


def _fail(msg: str) -> NoReturn:
    from .commands import get_console

    get_console().error(msg)
    raise SystemExit(2)


def chart_from_django_fsm(
    label: str,
    field: str = "state",
    out_dir: Optional[str] = None,
    *,
    dry_run: bool = False,
) -> str:
    """Extract *label*'s FSMField *field* to a chart JSON file; return
    its path. Every failure is one clear line and exit status 2."""
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        _fail(
            "--from-django-fsm needs DJANGO_SETTINGS_MODULE (e.g. "
            "DJANGO_SETTINGS_MODULE=mysite.settings, with the project on "
            "PYTHONPATH); or run `python manage.py xsm_migrate_fsm "
            f"{label} --dry-run`"
        )
    try:
        import django
        from django.apps import apps

        django.setup()
        model: Any = apps.get_model(label)
        from ..contrib.django.fsm import extract_chart

        chart = extract_chart(model, field)
    except ImportError as exc:
        _fail(f"--from-django-fsm: {exc}")
    except Exception as exc:  # 📝 settings / label / field errors
        _fail(f"--from-django-fsm {label}: {type(exc).__name__}: {exc}")
    target = Path(out_dir) if out_dir else Path.cwd()
    if dry_run:
        # 🔥 CLI-017: `--check` / `--diff` must not touch the checkout, but
        #    the generator still reads the chart from a file: park it in a
        #    throw-away directory.
        target = Path(tempfile.mkdtemp(prefix="xsm-fsm-"))
    path = target / f"{chart['id']}.json"
    try:
        target.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(chart, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        _fail(f"--from-django-fsm: cannot write {path}: {exc}")
    return str(path)
