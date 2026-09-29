# src/xstate_statemachine/cli/commands/new.py
# -----------------------------------------------------------------------------
# 🌱 `xsm new` -- scaffold a minimal project from a shipped example app
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: stdlib only (`string.Template` + `pathlib`), no
#    cookiecutter. Templates live in `cli/project_templates/<name>/` as
#    `*.tmpl` files copied from the example apps, so the scaffold is the
#    same code the example's own tests exercise. `$` is reserved for
#    placeholders; the template files contain no other `$`.
# -----------------------------------------------------------------------------
"""The `new` subcommand."""

from __future__ import annotations

import keyword
import re
from pathlib import Path
from string import Template
from typing import Dict, List, Optional, Tuple

from . import get_console

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "project_templates"

#: ``name -> (status, description)``. ``status`` is ``"shipped"`` or the
#: issue number that will ship it.
TEMPLATES: Dict[str, Tuple[str, str]] = {
    "fastapi": (
        "shipped",
        "FastAPI order service: StatechartRouter, SQLite/Redis, tests",
    ),
    "django": ("#280", "Django app with StatechartField"),
    "flask": ("#285", "Flask app with the XState extension"),
}

_NAME = re.compile(r"^[a-z][a-z0-9_]{0,39}$")


class NewProjectError(Exception):
    """A scaffold request that cannot be honoured (exit status 2)."""


def _machine_id(name: str) -> str:
    """``snake_name`` -> ``camelName`` (the JSON id convention)."""
    head, *rest = name.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in rest if p)


def _check_name(name: str) -> None:
    if not _NAME.match(name) or keyword.iskeyword(name):
        raise NewProjectError(
            f"invalid --name {name!r}: use lower_snake_case, starting "
            "with a letter (it becomes a URL prefix and a machine id)"
        )


def _check_target(target: Path, force: bool) -> None:
    if target.exists() and not target.is_dir():
        raise NewProjectError(f"{target} exists and is not a directory")
    if target.is_dir() and any(target.iterdir()) and not force:
        raise NewProjectError(
            f"{target} is not empty; pass --force to write into it"
        )


def scaffold(
    template: str, target: Path, *, name: str = "orders", force: bool = False
) -> List[Path]:
    """Render *template* into *target*; return the files written.

    Raises:
        NewProjectError: unknown / planned template, bad name, or a
            non-empty target without *force*.
    """
    if template not in TEMPLATES:
        raise NewProjectError(
            f"unknown template {template!r}; see `xsm new --list`"
        )
    status = TEMPLATES[template][0]
    if status != "shipped":
        raise NewProjectError(
            f"the {template!r} template is planned and arrives with {status}"
        )
    _check_name(name)
    _check_target(target, force)
    from ... import __version__

    values = {
        "name": name,
        "machine_id": _machine_id(name),
        "min_version": __version__,
    }
    root = TEMPLATES_DIR / template
    written: List[Path] = []
    for src in sorted(root.rglob("*.tmpl")):
        rel = src.relative_to(root).with_suffix("")  # drop .tmpl
        out = target / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        text = Template(src.read_text("utf-8")).substitute(values)
        out.write_text(text, encoding="utf-8", newline="\n")
        written.append(out)
    return written


def run_new(
    target: Optional[str],
    *,
    template: str = "fastapi",
    name: str = "orders",
    force: bool = False,
    list_only: bool = False,
) -> None:
    """CLI entry: list templates or scaffold one; exit 2 on refusal."""
    c = get_console()
    if list_only or not target:
        c.print("Project templates (xsm new --template NAME DIR):")
        for key, (status, desc) in TEMPLATES.items():
            tag = "" if status == "shipped" else f"  [planned, {status}]"
            c.print(f"  {key:<8} {desc}{tag}")
        if not list_only:
            raise SystemExit(2)
        return
    try:
        files = scaffold(template, Path(target), name=name, force=force)
    except NewProjectError as exc:
        c.print(f"error: {exc}")
        raise SystemExit(2) from None
    c.print(f"Created {len(files)} files in {target}:")
    for f in files:
        c.print(f"  {f.relative_to(Path(target)).as_posix()}")
    c.print(
        f"Next: cd {target} && pip install -r requirements.txt "
        "&& python -m pytest tests -q"
    )
