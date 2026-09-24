# src/xstate_statemachine/cli/commands/update.py
# -----------------------------------------------------------------------------
# ⬆️ `xsm update` -- upgrade the library to the latest release
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: a self-updater must upgrade with the installer
#    that installed us, or it corrupts the environment. So `detect_install`
#    reads the dist-info (`INSTALLER`, `direct_url.json`) and the interpreter
#    prefix and classifies the install:
#      pip       -> `<python> -m pip install --upgrade xstate-statemachine`
#      pipx      -> `pipx upgrade xstate-statemachine`
#      uv-tool   -> `uv tool upgrade xstate-statemachine`
#      editable  -> refuse: a dev checkout is updated with git, not pip
#      conda     -> refuse: conda owns that env; print the conda command
#      unknown   -> refuse with the manual pip command
#    Everything else is deliberately boring: the latest version comes from
#    PyPI's JSON API over stdlib `urllib` (zero dependencies), the upgrade
#    runs in a subprocess with the user's terminal attached, and the result
#    is confirmed by asking a FRESH interpreter for `--version` -- the
#    running process still has the old module loaded.
#
# 🪟 Windows follow-through: `pip --upgrade` regenerates the unsigned
#    `xsm.exe` launcher. If `xsm setup` had parked it (Application Control
#    policy), `update` re-applies the shim afterwards -- otherwise the very
#    machine that needed `setup` would break right after updating.
#
# 🧪 Every I/O seam (`fetch_latest`, `detect_install`, `_run`) is a
#    module-level function the tests patch; nothing here talks to the
#    network or spawns pip under test.
# -----------------------------------------------------------------------------
"""The `update` subcommand: check for and install the latest release."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import List, Optional, Tuple

from ... import __version__
from . import get_console

DIST = "xstate-statemachine"
PYPI_JSON = f"https://pypi.org/pypi/{DIST}/json"
TIMEOUT_S = 10.0


# =============================================================================
# Version arithmetic (stdlib only -- no `packaging`)
# =============================================================================
def parse_version(text: str) -> Tuple[Tuple[int, ...], int, int]:
    """PEP 440 subset sufficient for this project's tags: ``N(.N)*`` with an
    optional ``aN`` / ``bN`` / ``rcN`` / ``.devN`` suffix. Returns a sortable
    key; a final release sorts above any pre-release of the same number."""
    s = text.strip().lower().lstrip("v")
    pre_rank, pre_num = 3, 0  # final
    for tag, rank in (("rc", 2), ("b", 1), ("a", 0)):
        if tag in s:
            head, _, num = s.partition(tag)
            s, pre_rank, pre_num = head, rank, int(num or 0)
            break
    dev = 0
    if ".dev" in s:
        s, _, d = s.partition(".dev")
        dev = -(int(d or 0) + 1)
    nums = tuple(int(p) for p in s.split(".") if p.isdigit())
    return (nums or (0,), pre_rank, pre_num + dev)


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


# =============================================================================
# Facts
# =============================================================================
@dataclass
class InstallInfo:
    kind: str  # pip | pipx | uv-tool | editable | conda | unknown
    installer: str
    location: str
    python: str
    command: List[str]  # how to upgrade; empty when refused
    reason: str = ""  # why refused

    @property
    def upgradable(self) -> bool:
        return bool(self.command)


def _read(dist: metadata.Distribution, name: str) -> str:
    try:
        return (dist.read_text(name) or "").strip()
    except Exception:  # noqa: BLE001 -- any metadata oddity: treat as absent
        return ""


def detect_install(python: Optional[str] = None) -> InstallInfo:
    """Classify how this package was installed and how to upgrade it."""
    py = python or sys.executable
    try:
        dist = metadata.distribution(DIST)
    except metadata.PackageNotFoundError:
        return InstallInfo(
            "unknown",
            "",
            "",
            py,
            [],
            f"{DIST} is not installed as a distribution",
        )
    installer = _read(dist, "INSTALLER").lower()
    location = str(dist.locate_file(""))
    direct = _read(dist, "direct_url.json")
    try:
        direct_info = json.loads(direct) if direct else {}
    except ValueError:
        direct_info = {}

    if direct_info.get("dir_info", {}).get("editable"):
        return InstallInfo(
            "editable",
            installer,
            str(direct_info.get("url", location)).replace("file:///", ""),
            py,
            [],
            "this is an editable (development) install -- update it with git",
        )
    if "conda-meta" in (
        os.listdir(sys.prefix) if os.path.isdir(sys.prefix) else []
    ):
        return InstallInfo(
            "conda",
            installer,
            location,
            py,
            [],
            f"this environment is managed by conda -- run `conda update {DIST}` "
            f"(or `pip install --upgrade {DIST}` if you installed it with pip)",
        )
    if "pipx" in location.replace("\\", "/").lower().split("/"):
        return InstallInfo(
            "pipx", installer, location, py, ["pipx", "upgrade", DIST]
        )
    if installer == "uv" and "/tools/" in location.replace("\\", "/").lower():
        return InstallInfo(
            "uv-tool", installer, location, py, ["uv", "tool", "upgrade", DIST]
        )
    if installer in ("pip", "uv", ""):
        return InstallInfo(
            "pip",
            installer or "pip",
            location,
            py,
            [py, "-m", "pip", "install", "--upgrade", DIST],
        )
    return InstallInfo(
        "unknown",
        installer,
        location,
        py,
        [],
        f"installed by `{installer}`, which xsm does not know how to drive -- "
        f"upgrade with that tool, or `{Path(py).name} -m pip install --upgrade {DIST}`",
    )


def fetch_latest(timeout: float = TIMEOUT_S) -> str:
    """Latest non-prerelease, non-yanked version on PyPI."""
    req = urllib.request.Request(
        PYPI_JSON, headers={"User-Agent": f"xsm/{__version__}"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
        data = json.loads(resp.read().decode("utf-8"))
    return str(data["info"]["version"])


def _run(cmd: List[str]) -> int:
    """Run the upgrade with the user's terminal attached (pip's own output
    is the progress report)."""
    return subprocess.call(cmd)


def _installed_version(python: str) -> Optional[str]:
    """Ask a FRESH interpreter -- this process still has the old module."""
    try:
        out = subprocess.run(
            [python, "-m", "xstate_statemachine", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return out.strip().split()[-1] if out.strip() else None


# =============================================================================
# Entry
# =============================================================================
def run_update(
    *, check: bool = False, yes: bool = False, as_json: bool = False
) -> None:
    c = get_console()
    info = detect_install()
    try:
        latest = fetch_latest()
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        if as_json:
            c.print(json.dumps({"error": f"could not reach PyPI: {exc}"}))
        else:
            c.error(f"could not reach PyPI: {exc}")
            c.print(c.style(f"  {PYPI_JSON}", "muted"))
        raise SystemExit(1)
    newer = is_newer(latest, __version__)

    if as_json:
        c.print(
            json.dumps(
                {
                    "current": __version__,
                    "latest": latest,
                    "update_available": newer,
                    "install": asdict(info),
                },
                indent=2,
            )
        )
        if check:
            raise SystemExit(1 if newer else 0)
    else:
        c.kv(
            [
                ("Installed:", __version__),
                (
                    "Latest:",
                    c.style(latest, "ok" if newer else "muted")
                    + ("  (update available)" if newer else "  (up to date)"),
                ),
                ("Install:", f"{info.kind}  {c.style(info.location, 'path')}"),
            ]
        )
        c.blank()

    if not newer:
        if not as_json:
            c.ok(f"{DIST} {__version__} is the latest release")
        return
    if check:
        if not as_json:
            c.info(
                f"run `{Path(info.python).name} -m xstate_statemachine update` to upgrade"
            )
        raise SystemExit(1)
    if not info.upgradable:
        if as_json:
            raise SystemExit(2)
        c.warn(f"not updating: {info.reason}")
        raise SystemExit(2)
    if as_json:
        # A machine-readable caller asked us to act, not to chat.
        pass
    elif not yes:
        cmd = " ".join(info.command)
        if c.interactive:
            if not c.confirm(f"Upgrade to {latest} with `{cmd}`?"):
                c.print(c.style("nothing changed", "muted"))
                return
        else:
            c.info(f"would run: {cmd}   (pass --yes to proceed)")
            raise SystemExit(1)

    # 🪟 Remember the shim state BEFORE pip regenerates xsm.exe.
    from .setup import inspect_shim, install_shim

    had_shim = sys.platform.startswith("win") and inspect_shim().installed

    code = _run(info.command)
    if code != 0:
        if not as_json:
            c.error(f"`{' '.join(info.command)}` exited with {code}")
        raise SystemExit(code)

    if had_shim:
        st = install_shim()
        if not as_json and st.action != "none":
            c.ok("re-applied the xsm.cmd shim (pip recreated xsm.exe)")

    now = _installed_version(info.python)
    if as_json:
        c.print(json.dumps({"updated_to": now, "expected": latest}))
        return
    if now == latest:
        c.ok(f"updated {DIST} {__version__} -> {now}")
    elif now:
        c.warn(f"pip finished but `--version` reports {now}, not {latest}")
    else:
        c.warn("pip finished; could not confirm the new version")
