# src/xstate_statemachine/cli/commands/setup.py
# -----------------------------------------------------------------------------
# 🪟 `xsm setup` -- make the `xsm` command work where pip's launcher cannot
# -----------------------------------------------------------------------------
# 🏛️ The problem this solves: on Windows, pip realises the `xsm` console
#    script as a generic, UNSIGNED `Scripts\xsm.exe` launcher. Machines
#    governed by Windows Defender Application Control / AppLocker / Smart
#    App Control refuse it ("An Application Control policy has blocked this
#    file") while `python.exe` itself is trusted. Nothing shipped in the
#    wheel can sign or replace a file pip generates on the user's disk, and
#    pip has no post-install hook -- so the fix has to be a command the
#    user runs once, via the interpreter: `python -m xstate_statemachine
#    setup`. It swaps the blocked launcher for a batch shim that runs
#    through the trusted `cmd.exe`.
#
# 🔬 Verified on a WDAC-managed machine from PowerShell and cmd. Two
#    non-obvious facts drove the design:
#      1. `cmd`/PowerShell resolve `xsm.exe` BEFORE `xsm.cmd` in the same
#         folder (PATHEXT order), so the exe must be moved aside, not just
#         shadowed. We rename rather than delete so `--undo` is lossless
#         and pip's uninstall bookkeeping still finds a file to remove.
#      2. `pip install --upgrade` regenerates `xsm.exe`, undoing the swap.
#         The command is idempotent so "re-run after upgrading" is the
#         whole maintenance story; `--check` reports the current state.
#
# 🧪 Everything takes an explicit `scripts_dir` / `platform` so the tests
#    exercise every branch in a temp directory on every OS.
# -----------------------------------------------------------------------------
"""The `setup` subcommand: install / remove the Windows batch shim."""

from __future__ import annotations

import json
import os
import sys
import sysconfig
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from . import get_console

#: The blocked launcher is parked under this name (never deleted).
PARKED_SUFFIX = ".blocked"

#: 🐚 What the shim contains. `%~dp0` is the shim's own folder, so it calls
#:    the interpreter it was installed for even when several Pythons are on
#:    PATH; `%*` forwards every argument verbatim. If that interpreter is
#:    not where we left it (venv moved), fall back to whatever `python`
#:    resolves to on PATH so the shim degrades rather than dies.
SHIM_TEMPLATE = (
    "@echo off\r\n"
    'if exist "{python}" (\r\n'
    '  "{python}" -m xstate_statemachine %*\r\n'
    ") else (\r\n"
    "  python -m xstate_statemachine %*\r\n"
    ")\r\n"
)


@dataclass
class ShimState:
    """What `xsm setup` found and did."""

    platform: str
    scripts_dir: str
    exe: str
    exe_present: bool
    parked_present: bool
    shim_present: bool
    shim_current: bool  # shim exists AND matches this interpreter
    action: str = (
        "none"  # none | installed | refreshed | removed | unsupported
    )

    @property
    def installed(self) -> bool:
        return self.shim_current and not self.exe_present


def default_scripts_dir() -> Path:
    """Where pip put (or would put) `xsm.exe` for this interpreter."""
    return Path(sysconfig.get_path("scripts"))


def _render_shim(python: Path) -> str:
    return SHIM_TEMPLATE.format(python=str(python))


def inspect_shim(
    scripts_dir: Optional[Path] = None,
    *,
    platform: Optional[str] = None,
    python: Optional[Path] = None,
) -> ShimState:
    """Report the launcher / shim situation without changing anything."""
    plat = platform or sys.platform
    sd = scripts_dir or default_scripts_dir()
    py = python or Path(sys.executable)
    exe = sd / "xsm.exe"
    parked = sd / ("xsm.exe" + PARKED_SUFFIX)
    shim = sd / "xsm.cmd"
    shim_current = False
    if shim.is_file():
        try:
            # 🔤 Bytes, not text: text mode would turn our CRLF into CRCRLF
            #    on Windows and the comparison would never match.
            shim_current = shim.read_bytes() == _render_shim(py).encode(
                "utf-8"
            )
        except OSError:  # pragma: no cover -- unreadable shim: treat as stale
            shim_current = False
    return ShimState(
        platform=plat,
        scripts_dir=str(sd),
        exe=str(exe),
        exe_present=exe.is_file(),
        parked_present=parked.is_file(),
        shim_present=shim.is_file(),
        shim_current=shim_current,
    )


def install_shim(
    scripts_dir: Optional[Path] = None,
    *,
    platform: Optional[str] = None,
    python: Optional[Path] = None,
) -> ShimState:
    """Park `xsm.exe` and write `xsm.cmd` (idempotent)."""
    st = inspect_shim(scripts_dir, platform=platform, python=python)
    if not st.platform.startswith("win"):
        st.action = "unsupported"
        return st
    sd = Path(st.scripts_dir)
    sd.mkdir(parents=True, exist_ok=True)
    exe, parked, shim = (
        Path(st.exe),
        sd / ("xsm.exe" + PARKED_SUFFIX),
        sd / "xsm.cmd",
    )
    changed = False
    if exe.is_file():
        # A stale parked copy from a previous round is superseded by the
        # launcher pip just regenerated.
        if parked.exists():
            parked.unlink()
        os.replace(exe, parked)
        changed = True
    if not st.shim_current:
        shim.write_bytes(
            _render_shim(python or Path(sys.executable)).encode("utf-8")
        )
        changed = True
    out = inspect_shim(sd, platform=st.platform, python=python)
    out.action = (
        "installed"
        if changed and not st.shim_present
        else "refreshed" if changed else "none"
    )
    return out


def remove_shim(
    scripts_dir: Optional[Path] = None,
    *,
    platform: Optional[str] = None,
    python: Optional[Path] = None,
) -> ShimState:
    """Delete `xsm.cmd` and restore the parked `xsm.exe` (idempotent)."""
    st = inspect_shim(scripts_dir, platform=platform, python=python)
    if not st.platform.startswith("win"):
        st.action = "unsupported"
        return st
    sd = Path(st.scripts_dir)
    exe, parked, shim = (
        Path(st.exe),
        sd / ("xsm.exe" + PARKED_SUFFIX),
        sd / "xsm.cmd",
    )
    changed = False
    if shim.is_file():
        shim.unlink()
        changed = True
    if parked.is_file() and not exe.exists():
        os.replace(parked, exe)
        changed = True
    out = inspect_shim(sd, platform=st.platform, python=python)
    out.action = "removed" if changed else "none"
    return out


# =============================================================================
# Entry
# =============================================================================
def run_setup(
    *,
    undo: bool = False,
    check: bool = False,
    as_json: bool = False,
    scripts_dir: Optional[Path] = None,
) -> None:
    c = get_console()
    if check:
        st = inspect_shim(scripts_dir)
    elif undo:
        st = remove_shim(scripts_dir)
    else:
        st = install_shim(scripts_dir)

    if as_json:
        c.print(
            json.dumps({**asdict(st), "installed": st.installed}, indent=2)
        )
        if check and not (st.installed or not st.platform.startswith("win")):
            raise SystemExit(1)
        return

    module = f"{Path(sys.executable).name} -m xstate_statemachine"
    if not st.platform.startswith("win"):
        c.ok("nothing to do: the `xsm` entry point is a script on this OS")
        c.print(
            c.style(f"  (the launcher-free spelling is `{module}`)", "muted")
        )
        return

    c.kv(
        [
            ("Scripts dir:", c.style(st.scripts_dir, "path")),
            (
                "xsm.exe:",
                (
                    "present"
                    if st.exe_present
                    else (
                        "parked as xsm.exe.blocked"
                        if st.parked_present
                        else "absent"
                    )
                ),
            ),
            (
                "xsm.cmd:",
                (
                    "current"
                    if st.shim_current
                    else "present (stale)" if st.shim_present else "absent"
                ),
            ),
        ]
    )
    c.blank()
    if check:
        if st.installed:
            c.ok(
                "`xsm` resolves to the batch shim; the blocked launcher is parked"
            )
        else:
            c.info(
                "`xsm` still resolves to pip's xsm.exe launcher; run "
                f"`{module} setup` if your machine blocks it"
            )
            raise SystemExit(1)
        return
    if undo:
        if st.action == "removed":
            c.ok("shim removed; pip's xsm.exe launcher restored")
        else:
            c.info("no shim to remove")
        return
    if st.action == "installed":
        c.ok("`xsm` now runs through cmd.exe -> python; try `xsm info`")
    elif st.action == "refreshed":
        c.ok("shim refreshed for this interpreter; try `xsm info`")
    else:
        c.ok("already set up; nothing changed")
    c.print(
        c.style(
            "  pip install --upgrade recreates xsm.exe; re-run "
            f"`{module} setup` afterwards. `{module} setup --undo` reverts.",
            "muted",
        )
    )
