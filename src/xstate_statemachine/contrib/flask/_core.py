# src/xstate_statemachine/contrib/flask/_core.py
# -----------------------------------------------------------------------------
# 🧩 The per-app registry, shared by the Flask extension and the Quart shim
# -----------------------------------------------------------------------------
# 🏛️ Flask's extension rule: the extension OBJECT holds no app state; each
#    app's state lives in ``app.extensions["xstate"]``. `AppRegistry` is that
#    state -- store, lock, plugins, inbox, principal, log, the machine
#    registrations and the in-process SSE fan-out. Two apps built from one
#    `XState()` never share a store or a subscriber (the application-factory
#    guarantee the tests pin).
#
# 🔐 X0.1: `register(authorize=)` is REQUIRED (`allow_all` is explicit and
#    warns once); X0.2: the idempotency scope is the caller's PRINCIPAL, so
#    `principal=` is required with `inbox=`.
# -----------------------------------------------------------------------------
"""`AppRegistry`, `Registration`, `allow_all` (internal)."""

from __future__ import annotations

import inspect
import itertools
import json
import logging
import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from ...factory import create_machine
from ...models import MachineNode
from ...persistence.idempotency import IdempotencyPlugin
from ...persistence.store import DEFAULT_MAX_SNAPSHOT_BYTES, validate_key
from ._http import ForbiddenError

logger = logging.getLogger(__name__)

__all__ = ["AppRegistry", "Registration", "REQUIRED", "allow_all"]

KEY_SEP = "."
EXTENSION_KEY = "xstate"
#: Sentinel: `register(authorize=)` has no default (X0.1).
REQUIRED: Any = type("_Required", (), {"__repr__": lambda s: "REQUIRED"})()
Authorizer = Callable[..., Any]

_allow_all_warned = threading.Event()


def allow_all(
    request: Any, *, name: str, key: Optional[str], event: Optional[str]
) -> bool:
    """Authorizer that admits everything. Logs a WARNING the first time
    it is USED, so an accidental production deployment is visible."""
    if not _allow_all_warned.is_set():
        _allow_all_warned.set()
        logger.warning(
            "⚠️ xstate-statemachine: `allow_all` authorizer in use for "
            "machine %r -- every client may read and drive every "
            "instance. Do not ship this to production (X0.1).",
            name,
        )
    return True


@dataclass
class Registration:
    name: str
    machine: MachineNode[Any]
    key: Optional[Callable[[], Any]]
    authorize: Authorizer
    context_serializer: Optional[Callable[[Any], Any]]
    strict: Optional[bool]
    #: JSON path or config dict for the `flask xsm` commands, or None.
    source: Any


def resolve_machine(machine: Any, source: Any) -> Tuple[MachineNode[Any], Any]:
    """Accept a `MachineNode`, a JSON path, or a config dict. Returns the
    node and the JSON *source* (a path, a config dict, or ``None``) the
    ``flask xsm`` commands analyse."""
    if isinstance(machine, MachineNode):
        return machine, source
    if isinstance(machine, (str, Path)):
        path = Path(machine)
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return create_machine(cfg), source or path
    if isinstance(machine, dict):
        return create_machine(machine), source or machine
    raise TypeError(
        "register(machine=) takes a MachineNode, a JSON path or a config "
        f"dict, got {type(machine).__name__}"
    )


def make_registration(
    name: str,
    machine: Any,
    *,
    key: Optional[Callable[[], Any]],
    authorize: Any,
    context_serializer: Optional[Callable[[Any], Any]],
    strict: Optional[bool],
    source: Any,
) -> Registration:
    if authorize is REQUIRED or not callable(authorize):
        raise TypeError(
            "register(authorize=) is required and must be callable; "
            "pass `allow_all` to opt out explicitly (X0.1)."
        )
    if not name or KEY_SEP in name or "/" in name:
        raise ValueError(
            f"Machine name {name!r} must be non-empty and must not "
            f"contain {KEY_SEP!r} or '/'."
        )
    if key is not None and not callable(key):
        raise TypeError("register(key=) must be a zero-argument callable")
    node, src = resolve_machine(machine, source)
    return Registration(
        name, node, key, authorize, context_serializer, strict, src
    )


# -----------------------------------------------------------------------------
# 📡 In-process fan-out for SSE (thread-safe; one per app)
# -----------------------------------------------------------------------------
class Fanout:
    """Committed transitions → subscriber queues, per (name, key)."""

    def __init__(self, max_connections_per_key: int) -> None:
        self.max_connections_per_key = int(max_connections_per_key)
        self._lock = threading.Lock()
        self._subs: Dict[Tuple[str, str], List["queue.Queue[Any]"]] = {}
        self._seq: Dict[Tuple[str, str], "itertools.count[int]"] = {}
        self._last: Dict[Tuple[str, str], int] = {}

    def subscribe(self, name: str, key: str) -> Optional["queue.Queue[Any]"]:
        with self._lock:
            subs = self._subs.setdefault((name, key), [])
            if len(subs) >= self.max_connections_per_key:
                return None
            q: "queue.Queue[Any]" = queue.Queue(maxsize=256)
            subs.append(q)
            return q

    def unsubscribe(self, name: str, key: str, q: "queue.Queue[Any]") -> None:
        with self._lock:
            subs = self._subs.get((name, key), [])
            if q in subs:
                subs.remove(q)
            if not subs:
                self._subs.pop((name, key), None)

    def connections(self, name: str, key: str) -> int:
        with self._lock:
            return len(self._subs.get((name, key), []))

    def seq(self, name: str, key: str) -> int:
        with self._lock:
            return self._last.get((name, key), 0)

    def publish(
        self, name: str, key: str, bodies: Iterable[Dict[str, Any]]
    ) -> None:
        with self._lock:
            counter = self._seq.setdefault(
                (name, key),
                itertools.count(self._last.get((name, key), 0) + 1),
            )
            subs = list(self._subs.get((name, key), []))
            items = []
            for b in bodies:
                n = next(counter)
                self._last[(name, key)] = n
                items.append((n, b))
        for q in subs:
            for item in items:
                try:
                    q.put_nowait(item)
                except queue.Full:  # a stalled client drops, never blocks
                    logger.warning("SSE subscriber queue full; dropping")


# -----------------------------------------------------------------------------
# 🗂️ AppRegistry
# -----------------------------------------------------------------------------
class AppRegistry:
    """Everything one app knows about its statecharts (see module notes)."""

    def __init__(
        self,
        store: Any,
        *,
        lock: Optional[Any] = None,
        plugins: Iterable[Any] = (),
        inbox: Optional[Any] = None,
        principal: Optional[Callable[[Any], Any]] = None,
        log: Optional[Any] = None,
        clock: Optional[Any] = None,
        migrator: Optional[Any] = None,
        max_body_bytes: Optional[int] = None,
        heartbeat_s: float = 15.0,
        max_connections_per_key: int = 16,
        allowed_origins: Iterable[str] = (),
    ) -> None:
        if store is None:
            raise TypeError("init_app(store=) is required")
        if inbox is not None and principal is None:
            raise ValueError(
                "init_app(principal=) is required with inbox= -- the "
                "idempotency scope is the caller's principal (X0.2)."
            )
        if max_connections_per_key < 1:
            raise ValueError("max_connections_per_key must be >= 1")
        self.store = store
        self.lock = lock
        self.plugins = list(plugins)
        self.inbox = inbox
        self.principal = principal
        self.log = log
        self.clock = clock
        self.migrator = migrator
        self.max_body_bytes = (
            DEFAULT_MAX_SNAPSHOT_BYTES
            if max_body_bytes is None
            else int(max_body_bytes)
        )
        self.heartbeat_s = float(heartbeat_s)
        self.allowed_origins = frozenset(allowed_origins)
        self.regs: Dict[str, Registration] = {}
        #: Declarations shared by every app of one extension (read-only
        #: here; set by `XState.init_app`).
        self.shared: Dict[str, Registration] = {}
        self.fanout = Fanout(max_connections_per_key)

    # -- registrations ------------------------------------------------------------
    def add(self, reg: Registration) -> None:
        if reg.name in self.regs and self.regs[reg.name] is not reg:
            raise ValueError(
                f"Machine name {reg.name!r} is already registered."
            )
        self.regs[reg.name] = reg

    def reg(self, name: str) -> Registration:
        """The registration for *name*: app-local first, then the ones
        declared on the extension (`XState.register` without ``app=``)."""
        found = self.regs.get(name) or self.shared.get(name)
        if found is None:
            raise KeyError(f"No machine registered as {name!r}.")
        return found

    def names(self) -> List[str]:
        return sorted(set(self.regs) | set(self.shared))

    def store_key(self, name: str, key: Any) -> str:
        self.reg(name)
        return validate_key(f"{name}{KEY_SEP}{key}")

    def key_for(self, name: str, key: Any) -> str:
        if key is not None:
            return str(key)
        fn = self.reg(name).key
        if fn is None:
            raise TypeError(
                f"act({name!r}) needs key= (no key callable was registered)"
            )
        return str(fn())

    # -- authorization / principal -----------------------------------------------
    def authorize(
        self, request: Any, name: str, key: Optional[str], event: Optional[str]
    ) -> None:
        verdict = self.reg(name).authorize(
            request, name=name, key=key, event=event
        )
        if inspect.isawaitable(verdict):
            raise TypeError(
                "an async authorizer needs the Quart shim; Flask views are "
                "synchronous"
            )
        if not verdict:
            raise ForbiddenError()

    async def aauthorize(
        self, request: Any, name: str, key: Optional[str], event: Optional[str]
    ) -> None:
        verdict = self.reg(name).authorize(
            request, name=name, key=key, event=event
        )
        if inspect.isawaitable(verdict):
            verdict = await verdict
        if not verdict:
            raise ForbiddenError()

    def plugins_for(self, principal: Optional[Any]) -> List[Any]:
        plugins = list(self.plugins)
        if self.inbox is not None:
            if principal is None:
                raise ValueError(
                    "act(principal=) is required when the app has an "
                    "idempotency inbox (X0.2)."
                )
            who = str(principal)
            plugins.append(
                IdempotencyPlugin(self.inbox, principal=lambda e: who)
            )
        return plugins

    def origin_allowed(self, origin: Optional[str], host: str) -> bool:
        """Same-origin (Origin's host == Host) or allow-listed (X0.7)."""
        if not origin:
            return True
        if origin in self.allowed_origins:
            return True
        netloc = origin.split("://", 1)[-1].rstrip("/")
        return netloc == host
