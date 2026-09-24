# src/xstate_statemachine/cli/commands/generate.py
# -----------------------------------------------------------------------------
# 🏗️ Companion outputs for `xsm generate-template`
# -----------------------------------------------------------------------------
# The three companion templates (`pytest`, `typed`, `plugin`) produce ONE
# file each, next to the primary artefacts, and are verified by compiling
# (the pytest scaffold additionally imports cleanly). They run either as
# the primary `--template` or as `--with-tests` / `--with-types` /
# `--with-plugin` add-ons to any other template.
# -----------------------------------------------------------------------------
"""Companion-template emission shared by the CLI and the launcher wizard."""

from __future__ import annotations

import argparse
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
    for template in requested_companions(args, primary):
        code = render_companion(
            template, ctx, json_paths=json_paths, version=__version__
        )
        problems = verify_generated(
            ctx.configs[0], code, template=template, strict=False
        )
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
                c.error(f"{path} is out of date (--template {template})")
                raise SystemExit(1)
            c.ok(f"{path.name} is up to date")
            continue
        path.write_text(code, encoding="utf-8")
        c.ok(f"Generated {template} file: {c.style(str(path), 'path')}")
        written.append(path)
    return written
