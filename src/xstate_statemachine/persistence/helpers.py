# src/xstate_statemachine/persistence/helpers.py
# -----------------------------------------------------------------------------
# 🔁 load_interpreter / save_interpreter -- the request-scoped idiom (#259)
# -----------------------------------------------------------------------------
# 🏛️ create → act → persist → discard in two calls. `load_interpreter`
#    returns a STARTED interpreter (review amendment: `from_snapshot` alone
#    does not start, and a caller who forgot got a machine that accepted
#    events and did nothing) and creates one when the key is missing. The
#    version travels with it so `save_interpreter(expected_version=...)`
#    is the optimistic-locking retry loop's whole surface.
# -----------------------------------------------------------------------------
"""Convenience pair for the create → act → persist → discard idiom."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple, Type

from ..clock import Clock
from ..exceptions import StoreError
from ..models import MachineNode
from ..interpreter import Interpreter
from ..sync_interpreter import SyncInterpreter
from .store import StateStore

__all__ = [
    "aload_interpreter",
    "load_interpreter",
    "save_interpreter",
    "KeyNotFoundError",
]


class KeyNotFoundError(StoreError, KeyError):
    """`load_interpreter(create_if_missing=False)` found no record."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"No snapshot stored under '{key}'.")


def _build(
    store: StateStore,
    key: str,
    machine: MachineNode[Any],
    interpreter_cls: Type[Any],
    clock: Optional[Clock],
    plugins: Iterable[Any],
    create_if_missing: bool,
    verify_machine_hash: bool,
    from_snapshot_kwargs: Dict[str, Any],
) -> Tuple[Any, int]:
    record = store.load(key)
    if record is None:
        if not create_if_missing:
            raise KeyNotFoundError(key)
        interp = interpreter_cls(machine, clock=clock)
        for p in plugins:
            interp.use(p)
        return interp, 0
    # ⏰ #264: durable timers resume with their remaining wall time unless
    #    the caller chose otherwise.
    from_snapshot_kwargs.setdefault("restart_timers", "resume")
    interp = interpreter_cls.from_snapshot(
        record.snapshot,
        machine,
        clock=clock,
        plugins=list(plugins),
        verify_machine_hash=verify_machine_hash,
        **from_snapshot_kwargs,
    )
    return interp, record.version


def load_interpreter(
    store: StateStore,
    key: str,
    machine: MachineNode[Any],
    *,
    clock: Optional[Clock] = None,
    plugins: Iterable[Any] = (),
    create_if_missing: bool = True,
    verify_machine_hash: bool = True,
    **from_snapshot_kwargs: Any,
) -> Tuple[SyncInterpreter[Any], int]:
    """Load *key* from *store* into a **started** `SyncInterpreter`.

    Returns ``(interpreter, version)``; ``version`` is ``0`` for a freshly
    created machine (the key did not exist), so a following
    ``save_interpreter(..., expected_version=version)`` succeeds only if
    nobody else created it meanwhile. Extra keyword arguments go to
    `from_snapshot` (``minimum_version``, ``expected_machine_hash``, ...).

    Raises:
        KeyNotFoundError: the key is missing and ``create_if_missing`` is
            ``False``.
    """
    interp, version = _build(
        store,
        key,
        machine,
        SyncInterpreter,
        clock,
        plugins,
        create_if_missing,
        verify_machine_hash,
        from_snapshot_kwargs,
    )
    interp.store_key = key  # #261
    interp.start()
    return interp, version


async def aload_interpreter(
    store: StateStore,
    key: str,
    machine: MachineNode[Any],
    *,
    clock: Optional[Clock] = None,
    plugins: Iterable[Any] = (),
    create_if_missing: bool = True,
    verify_machine_hash: bool = True,
    **from_snapshot_kwargs: Any,
) -> Tuple[Interpreter[Any], int]:
    """Async twin of `load_interpreter`: a **started** `Interpreter`.

    The store call itself is synchronous (stdlib stores are fast and
    local); wrap the store with `as_async()` and call it yourself if your
    store does real I/O.
    """
    interp, version = _build(
        store,
        key,
        machine,
        Interpreter,
        clock,
        plugins,
        create_if_missing,
        verify_machine_hash,
        from_snapshot_kwargs,
    )
    interp.store_key = key  # #261
    await interp.start()
    return interp, version


def save_interpreter(
    store: StateStore,
    key: str,
    interpreter: Any,
    *,
    expected_version: Optional[int] = None,
) -> int:
    """Persist *interpreter*'s snapshot under *key*; return the new version.

    Reads `machine.version` for the record's ``machine_version`` and the
    engine's persisted deadlines (#264; ``[]`` today). Raises
    `ConflictError` when ``expected_version`` does not match -- the caller
    reloads, re-applies its event(s) and retries.
    """
    snapshot = interpreter.get_snapshot()
    machine_version = getattr(interpreter.machine, "version", None) or ""
    deadlines = ()
    persist = getattr(interpreter, "_persist_deadlines", None)
    if callable(persist):
        deadlines = tuple(persist())
    return store.save(
        key,
        snapshot,
        expected_version=expected_version,
        machine_version=machine_version,
        deadlines=deadlines,
    )
