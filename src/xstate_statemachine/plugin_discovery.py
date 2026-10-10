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
import re
import threading
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
    "plugin_factory",
]

PLUGINS_GROUP = "xstate_statemachine.plugins"
STORES_GROUP = "xstate_statemachine.stores"
BROKERS_GROUP = "xstate_statemachine.brokers"
#: Every group `xsm plugins` lists. Stores/brokers are adapters: they are
#: discovered and described, never instantiated by the library.
GROUPS: Tuple[str, ...] = (PLUGINS_GROUP, STORES_GROUP, BROKERS_GROUP)
DISABLE_ENV = "XSM_DISABLE_PLUGIN_DISCOVERY"

_disabled_logged = False
# 🔥 #296 battle (A): "TRUE", "on", " yes " left discovery ON -- an
#    operator's kill switch must not depend on spelling.
_TRUTHY = frozenset({"1", "true", "yes", "on"})
#: Guards publication of `last_skipped` / `last_failed` (see `discover`).
_PUBLISH_LOCK = threading.Lock()


def _normalise(name: str) -> str:
    """PEP 503 name normalisation (``Foo_Bar.baz`` → ``foo-bar-baz``)."""
    return re.sub(r"[-_.]+", "-", name).lower()


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
        obj: The loaded object (normally a class or an instance).
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


_Index = Dict[Tuple[str, str, str], Tuple[str, str]]


def _dist_index() -> _Index:
    """🐍 3.9: (group, name, value) → (dist, version), first dist wins.

    🔥 #296 battle (A): `_dist_of` rescanned EVERY distribution per entry
    point (O(dists x eps)); one index is now built per `discover()` call.
    """
    from importlib import metadata

    index: _Index = {}
    for d in metadata.distributions():
        try:
            meta = (d.metadata.get("Name") or "", d.version or "")
            for o in d.entry_points:
                index.setdefault((o.group, o.name, o.value), meta)
        except Exception:  # noqa: BLE001 -- malformed third-party metadata
            continue
    return index


def _dist_of(ep: Any, index: Optional[_Index] = None) -> Tuple[str, str]:
    dist = getattr(ep, "dist", None)  # 3.10+
    if dist is not None:
        name = dist.metadata.get("Name") or ""
        return name, dist.version or ""
    # 🐍 3.9: EntryPoint has no `.dist`; find the owning distribution.
    if index is None:
        index = _dist_index()
    return index.get((ep.group, ep.name, ep.value), ("", ""))


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
    if os.environ.get(DISABLE_ENV, "").strip().lower() not in _TRUTHY:
        return False
    if not _disabled_logged:
        _disabled_logged = True
        logger.info(
            "Plugin discovery disabled by %s=%s.",
            DISABLE_ENV,
            os.environ.get(DISABLE_ENV, "").strip(),
        )
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
            Matching is PEP 503 normalised (case, ``-``/``_``/``.``).
        strict: Re-raise a failing loader instead of logging and skipping.

    Returns:
        The loaded entry points, sorted by (distribution, name). ``[]`` when
        ``XSM_DISABLE_PLUGIN_DISCOVERY=1``.
    """
    # 🔥 #296 battle (A): the module-level lists were mutated in place
    #    while loading, so two threads (or a plugin whose import calls
    #    discover() re-entrantly) interleaved/wiped each other's results.
    #    Collected locally, published once under a lock: the globals hold
    #    the result of the most recently FINISHED call (thread-affinity is
    #    not promised -- `xsm plugins` is single-threaded).
    skipped: List[SkippedPlugin] = []
    try:
        return _discover(group, allow, strict, skipped)
    finally:
        with _PUBLISH_LOCK:
            last_skipped[:] = skipped


def _discover(
    group: str,
    allow: Optional[Iterable[str]],
    strict: bool,
    skipped: List[SkippedPlugin],
) -> List[DiscoveredPlugin]:
    # 📝 #296 review (5): a failure BEFORE loading (corrupt metadata)
    #    left the previous call's `last_failed` in place.
    with _PUBLISH_LOCK:
        last_failed.clear()
    if _disabled():
        return []
    # 🔥 #296 review (3): `allow="acme-audit"` iterated the STRING -- one
    #    letter per name, matched nothing, said nothing.
    if isinstance(allow, (str, bytes)):
        raise TypeError(
            "allow= must be a collection of names, not a bare string "
            f"(got {allow!r}); allow=[] loads nothing"
        )
    # 🔥 #296 battle (A): `allow=["xsm_thirdparty_plugin"]` did not match
    #    distribution "xsm-thirdparty-plugin"; names are PEP 503 normalised.
    allowed = None if allow is None else {_normalise(a) for a in allow}
    eps = _entry_points(group)
    index = (
        _dist_index()
        if eps and getattr(eps[0], "dist", None) is None
        else None
    )
    found: List[DiscoveredPlugin] = []
    for ep in eps:
        dist, version = _dist_of(ep, index)
        if allowed is not None and not (
            _normalise(ep.name) in allowed or _normalise(dist) in allowed
        ):
            continue
        try:
            obj = ep.load()
        except Exception as exc:  # noqa: BLE001 -- third-party loader
            if strict:
                with _PUBLISH_LOCK:
                    last_failed.clear()
                    last_failed.update(name=ep.name, dist=dist)
                raise
            skipped.append(
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
    with _PUBLISH_LOCK:
        last_failed.clear()
    return found


_FACTORY_MARK = "__xsm_plugin_factory__"


def plugin_factory(fn: Any) -> Any:
    """Mark *fn* as a zero-argument factory `attach_discovered` may CALL.

    An entry point naming an unmarked function is refused unexecuted
    (#296 battle A): ``"os:system"`` must never be invoked by discovery.
    """
    setattr(fn, _FACTORY_MARK, True)
    return fn


def _instantiate(obj: Any) -> Any:
    """A `PluginBase` subclass is instantiated; an instance is kept.

    🔥 #296 battle (A): ANY zero-arg callable used to be CALLED -- an
    entry point ``= "os:getpid"`` / ``"atexit:_run_exitfuncs"`` (or a
    hostile ``"os:abort"``) executed it before the PluginBase check ran.
    A factory must opt in with `plugin_factory`; anything else is refused
    unexecuted.
    """
    from .plugins import PluginBase

    if inspect.isclass(obj):
        if issubclass(obj, PluginBase):
            return obj()
        raise TypeError(f"{obj.__name__} is not a PluginBase subclass")
    if isinstance(obj, PluginBase):
        return obj
    if callable(obj) and getattr(obj, _FACTORY_MARK, False) is True:
        return obj()  # opt-in factory; its RESULT is checked by the caller
    raise TypeError(
        f"{type(obj).__name__} object is not a PluginBase subclass or "
        "instance (unmarked factories are not called; see plugin_factory)"
    )


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
        # 📝 #296 battle (integrator): `instrument_all(discovered=True)`
        #    called twice attached a second instance of every plugin --
        #    one class per interpreter; a re-run is a no-op for it.
        present = {
            type(existing) for existing in _attached_plugins(interpreter)
        }
        if type(plugin) in present:
            logger.debug(
                "Plugin %r from %r already attached; skipping duplicate.",
                found.name,
                found.distribution or "?",
            )
            continue
        interpreter.use(plugin)
        attached.append(plugin)
    return attached


def _attached_plugins(interpreter: Any) -> List[Any]:
    """The plugin instances already on *interpreter* (unwrapping the
    engine's fail-open wrapper), or ``[]`` for a duck-typed collector."""
    raw = getattr(interpreter, "_plugins", None) or ()
    return [getattr(p, "wrapped", p) for p in raw]
