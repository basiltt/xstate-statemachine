# src/xstate_statemachine/plugin_discovery.py
# -----------------------------------------------------------------------------
# 🔎 Entry-point plugin discovery (#296)
# -----------------------------------------------------------------------------
# Third parties ship plugins / stores / brokers without a core PR by
# declaring an entry point in their own package metadata:
#
#     [project.entry-points."xstate_statemachine.plugins"]
#     audit = "my_pkg.plugin:AuditPlugin"
#
# 🔐 NEVER implicit (X0.14). Importing the library loads nothing; a
#    discovered plugin runs in-process with full privileges, so loading one
#    is an explicit `discover()` call by the application, filterable with
#    `allow=` and switched off fleet-wide with XSM_DISABLE_PLUGIN_DISCOVERY=1.
#    A loader that raises is logged and skipped (one broken distribution in
#    site-packages must not take the service down) unless `strict=True`.
#
# 🐍 `importlib.metadata.entry_points(group=...)` is 3.10+. On 3.9 the call
#    takes no arguments and returns a dict {group: [EntryPoint, ...]}; the
#    shim below selects the group by key.
# -----------------------------------------------------------------------------
"""Discover third-party plugins declared as package entry points."""

from __future__ import annotations

import inspect
import os
from typing import Dict, Any, Iterable, List, NamedTuple, Optional, Tuple

from .logger import logger

__all__ = [
    "BROKERS_GROUP",
    "DISABLE_ENV",
    "DiscoveredPlugin",
    "SkippedPlugin",
    "GROUPS",
    "PLUGINS_GROUP",
    "STORES_GROUP",
    "attach_discovered",
    "discover",
    "last_failed",
    "last_skipped",
]

PLUGINS_GROUP = "xstate_statemachine.plugins"
STORES_GROUP = "xstate_statemachine.stores"
BROKERS_GROUP = "xstate_statemachine.brokers"
#: Every group `xsm plugins` lists. Stores/brokers are adapters: they are
#: discovered and described, never instantiated by the library.
GROUPS: Tuple[str, ...] = (PLUGINS_GROUP, STORES_GROUP, BROKERS_GROUP)
DISABLE_ENV = "XSM_DISABLE_PLUGIN_DISCOVERY"

_disabled_logged = False


class SkippedPlugin(NamedTuple):
    """An entry point `discover()` could not load (non-strict mode).

    🔥 #296 battle: a skipped loader was a WARNING log line and nothing
    else -- `xsm plugins` listed a marketplace with the broken plugin
    simply missing, and an operator had no way to tell "not installed"
    from "installed but broken" without reading logs.
    """

    name: str
    distribution: str
    version: str
    group: str
    error: str


#: The entry points the LAST `discover()` call skipped (per group), for
#: `xsm plugins` and operators; cleared at the start of every call.
last_skipped: List["SkippedPlugin"] = []
#: Under ``strict=True`` the entry point whose loader raised (name, dist),
#: so a CLI can name it without a traceback; ``{}`` otherwise.
last_failed: Dict[str, str] = {}


class DiscoveredPlugin(NamedTuple):
    """One loaded entry point.

    Attributes:
        name: The entry-point name.
        distribution: The distribution that declared it (``""`` if unknown).
        version: That distribution's version (``""`` if unknown).
        obj: The loaded object (a class, factory or instance).
        hooks: `PluginBase` hook names the object overrides (empty for
            stores/brokers and for objects that are not plugins).
        group: The entry-point group it came from.
    """

    name: str
    distribution: str
    version: str
    obj: Any
    hooks: Tuple[str, ...]
    group: str = PLUGINS_GROUP


def _entry_points(group: str) -> List[Any]:
    """`entry_points(group=)` on 3.10+, dict selection on 3.9."""
    from importlib import metadata

    eps = metadata.entry_points()
    if hasattr(eps, "select"):  # 3.10+: EntryPoints / SelectableGroups
        return list(eps.select(group=group))
    return list(eps.get(group, ()))  # type: ignore[attr-defined]


def _dist_of(ep: Any) -> Tuple[str, str]:
    dist = getattr(ep, "dist", None)  # 3.10+
    if dist is not None:
        name = dist.metadata["Name"] or ""
        return name, dist.version or ""
    # 🐍 3.9: EntryPoint has no `.dist`; find the owning distribution.
    from importlib import metadata

    for d in metadata.distributions():
        for other in d.entry_points:
            if (
                other.group == ep.group
                and other.name == ep.name
                and other.value == ep.value
            ):
                return d.metadata["Name"] or "", d.version or ""
    return "", ""


def hooks_of(obj: Any) -> Tuple[str, ...]:
    """The `PluginBase` hook names *obj* (class or instance) overrides."""
    from .plugins import PluginBase

    cls = obj if inspect.isclass(obj) else type(obj)
    if not (inspect.isclass(cls) and issubclass(cls, PluginBase)):
        return ()
    names = [n for n in dir(PluginBase) if n.startswith("on_")]
    return tuple(
        sorted(
            n
            for n in names
            if getattr(cls, n, None) is not getattr(PluginBase, n)
        )
    )


def _disabled() -> bool:
    global _disabled_logged
    if os.environ.get(DISABLE_ENV, "").strip() not in ("1", "true", "yes"):
        return False
    if not _disabled_logged:
        _disabled_logged = True
        logger.info("Plugin discovery disabled by %s=1.", DISABLE_ENV)
    return True


def discover(
    *,
    group: str = PLUGINS_GROUP,
    allow: Optional[Iterable[str]] = None,
    strict: bool = False,
) -> List[DiscoveredPlugin]:
    """Load the entry points declared under *group*.

    Args:
        group: Entry-point group (`PLUGINS_GROUP`, `STORES_GROUP`,
            `BROKERS_GROUP`, or any custom group).
        allow: If given, only entry points whose name OR distribution name
            is in this collection are loaded; others are never imported.
        strict: Re-raise a failing loader instead of logging and skipping.

    Returns:
        The loaded entry points, sorted by (distribution, name). ``[]`` when
        ``XSM_DISABLE_PLUGIN_DISCOVERY=1``.
    """
    del last_skipped[:]
    last_failed.clear()
    if _disabled():
        return []
    allowed = None if allow is None else set(allow)
    found: List[DiscoveredPlugin] = []
    for ep in _entry_points(group):
        dist, version = _dist_of(ep)
        if allowed is not None and not (ep.name in allowed or dist in allowed):
            continue
        try:
            obj = ep.load()
        except Exception as exc:  # noqa: BLE001 -- third-party loader
            if strict:
                last_failed.clear()
                last_failed.update(name=ep.name, dist=dist)
                raise
            last_skipped.append(
                SkippedPlugin(
                    ep.name,
                    dist,
                    version,
                    group,
                    f"{type(exc).__name__}: {exc}",
                )
            )
            logger.warning(
                "Skipping plugin entry point %r (%s) from %r: its loader "
                "raised.",
                ep.name,
                ep.value,
                dist or "?",
                exc_info=True,
            )
            continue
        hooks = hooks_of(obj) if group == PLUGINS_GROUP else ()
        found.append(
            DiscoveredPlugin(ep.name, dist, version, obj, hooks, group)
        )
    found.sort(key=lambda p: (p.distribution, p.name))
    return found


def _instantiate(obj: Any) -> Any:
    """A class or zero-arg factory becomes an instance; an instance stays."""
    if inspect.isclass(obj) or (
        callable(obj) and not hasattr(obj, "on_interpreter_start")
    ):
        return obj()
    return obj


def attach_discovered(
    interpreter: Any,
    *,
    allow: Optional[Iterable[str]] = None,
    strict: bool = False,
) -> List[Any]:
    """Discover `PLUGINS_GROUP` and ``.use()`` each plugin on *interpreter*.

    The core hook behind ``instrument_all(discovered=True)`` in the
    ``[observability]`` extra. An entry point that fails to load or to
    instantiate is logged and skipped unless ``strict=True``.

    Returns:
        The plugin instances attached, in discovery order.
    """
    from .plugins import PluginBase

    attached: List[Any] = []
    for found in discover(group=PLUGINS_GROUP, allow=allow, strict=strict):
        try:
            plugin = _instantiate(found.obj)
            # 🔥 #296 battle: an entry point naming a class that is NOT a
            #    PluginBase was `.use()`d anyway -- the engine then called
            #    hooks that do not exist on every step. Refused (strict) or
            #    skipped, like a failing loader.
            if not isinstance(plugin, PluginBase):
                raise TypeError(
                    f"{type(plugin).__name__} is not a PluginBase subclass"
                )
        except Exception:  # noqa: BLE001 -- third-party constructor
            if strict:
                raise
            logger.warning(
                "Skipping plugin %r from %r: constructing it raised.",
                found.name,
                found.distribution or "?",
                exc_info=True,
            )
            continue
        interpreter.use(plugin)
        attached.append(plugin)
    return attached
