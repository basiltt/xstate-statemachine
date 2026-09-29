# src/xstate_statemachine/cli/commands/generate.py
# -----------------------------------------------------------------------------
# 🏗️ Companion outputs for `xsm generate-template`
# -----------------------------------------------------------------------------
# The companion templates (`pytest`, `typed`, `plugin`, `pydantic-models`,
# `fastapi-router`) produce ONE file each, next to the primary artefacts,
# and are verified by compiling (the web companions are also imported --
# and the router mounted and its OpenAPI built -- when their extra is
# installed). They run either as the primary `--template` or as
# `--with-tests` / `--with-types` / `--with-plugin` / `--with-models` /
# `--with-api` add-ons to any other template.
# -----------------------------------------------------------------------------
"""Companion-template emission shared by the CLI and the launcher wizard."""

from __future__ import annotations

import argparse
import dataclasses
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..postprocess import build_provenance_header, polish
from ..strategies import GenerationContext, get_strategy
from ..validation import verify_generated
from . import get_console

#: template id -> (flag attribute, file suffix)
COMPANIONS: Dict[str, Tuple[str, str]] = {
    "pytest": ("with_tests", "test_{name}.py"),
    "typed": ("with_types", "{name}_types.py"),
    "plugin": ("with_plugin", "{name}_observer.py"),
    # 📝 models BEFORE router: the router imports the models module when
    #    both are emitted, and its verification needs that code.
    "pydantic-models": ("with_models", "{name}_models.py"),
    "fastapi-router": ("with_api", "{name}_api.py"),
}


def is_companion(template: str) -> bool:
    return template in COMPANIONS


def companion_path(template: str, out_dir: Path, base_name: str) -> Path:
    return out_dir / COMPANIONS[template][1].format(name=base_name)


def requested_companions(args: argparse.Namespace, primary: str) -> List[str]:
    """Which companion templates to emit for this run."""
    wanted = [
        t for t, (flag, _) in COMPANIONS.items() if getattr(args, flag, False)
    ]
    if is_companion(primary) and primary not in wanted:
        wanted.insert(0, primary)
    return wanted


def render_companion(
    template: str,
    ctx: GenerationContext,
    *,
    json_paths: List[str],
    version: str,
) -> str:
    """Generate + polish one companion file."""
    code = get_strategy(template).generate_logic(ctx)
    sources = [Path(p).name for p in json_paths]
    header = build_provenance_header(
        source_files=sources,
        template=template,
        version=version,
        command="xsm generate-template "
        + " ".join(sources)
        + f" --template {template}",
    )
    return polish(code, header=header)


def emit_companions(
    args: argparse.Namespace,
    ctx: GenerationContext,
    *,
    out_dir: Path,
    base_name: str,
    json_paths: List[str],
    primary: str,
    check_mode: bool,
) -> List[Path]:
    """Write (or check) every requested companion; returns paths written."""
    from ... import __version__

    c = get_console()
    written: List[Path] = []
    wanted = requested_companions(args, primary)
    # 📝 The router last (stable sort): it may import the models module.
    wanted = sorted(wanted, key=lambda t: t == "fastapi-router")
    ctx = dataclasses.replace(ctx, companions=tuple(wanted))
    rendered: Dict[str, str] = {}
    stale = False
    for template in wanted:
        code = render_companion(
            template, ctx, json_paths=json_paths, version=__version__
        )
        rendered[template] = code
        problems = verify_generated(
            ctx.configs[0], code, template=template, strict=False
        )
        if not problems and not getattr(args, "no_verify", False):
            problems = _verify_web(template, code, ctx, rendered, base_name)
        if problems and not getattr(args, "no_verify", False):
            for p in problems:
                c.error(f"{template}: {p}")
            raise SystemExit(1)
        path = companion_path(template, out_dir, base_name)
        if check_mode:
            on_disk = (
                path.read_text(encoding="utf-8") if path.exists() else None
            )
            if on_disk != code:
                # 📝 Keep going: report EVERY stale companion, then fail.
                c.error(f"{path} is out of date (--template {template})")
                if getattr(args, "diff", False):
                    c.print(_unified(on_disk or "", code, path.name))
                stale = True
            else:
                c.ok(f"{path.name} is up to date")
            continue
        path.write_text(code, encoding="utf-8")
        c.ok(f"Generated {template} file: {c.style(str(path), 'path')}")
        written.append(path)
    if stale:
        raise SystemExit(1)
    return written


def _verify_web(
    template: str,
    code: str,
    ctx: GenerationContext,
    rendered: Dict[str, str],
    base_name: str,
) -> List[str]:
    """Import / mount / OpenAPI check for the web companions (a note, not a
    failure, when the extra is not installed)."""
    from ..strategies._web import collect_events
    from ..web_validation import REQUIRES, verify_web_companion

    if template not in REQUIRES:
        return []
    siblings: Optional[Dict[str, str]] = None
    if template == "fastapi-router" and "pydantic-models" in rendered:
        siblings = {f"{base_name}_models": rendered["pydantic-models"]}
    problems, note = verify_web_companion(
        template,
        code,
        expected_events=len(collect_events(ctx.configs[0])),
        siblings=siblings,
    )
    if note:
        get_console().info(note)
    return problems


def _unified(old: str, new: str, name: str) -> str:
    import difflib

    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"{name} (on disk)",
            tofile=f"{name} (generated)",
        )
    )
