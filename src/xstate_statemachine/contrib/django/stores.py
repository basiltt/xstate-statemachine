# src/xstate_statemachine/contrib/django/stores.py
# -----------------------------------------------------------------------------
# 🗄️ DjangoStore / DjangoModelStore -- the A2 `StateStore` contract on the ORM
# -----------------------------------------------------------------------------
# 🏛️ Two shapes, like the SQLAlchemy extra:
#
#      * `DjangoStore(namespace)` -- key-value records in
#        ``xsm_django_snapshot`` for `persisted()`, registries and the web
#        adapters. Passes the SAME contract suite as the stdlib stores.
#        Optimistic writes lead with a conditional UPDATE; `lock()` is a
#        lease row in ``xsm_django_lock`` (portable: SQLite has no row
#        locks), reclaimed after ``lock_ttl_s``.
#      * `DjangoModelStore(Model)` -- a VIEW over `StatechartModelMixin`
#        rows (key = pk) so `DueTimerScanner` fires a model's persisted
#        `after` deadlines (``manage.py xsm_deadlines``). Rows are never
#        created or deleted through it; its fence is ``<field>_version``.
#
# 🔐 X0: key validation, size cap on save AND load (X0.4), `forget()`
#    erases the record, its deadlines and its lease (X0.5).
# -----------------------------------------------------------------------------
"""`DjangoStore`, `DjangoModelStore`."""

from __future__ import annotations

import contextlib
import json
import threading
import time
import uuid
from typing import (
    Any,
    ContextManager,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
)

from django.db import IntegrityError, OperationalError, transaction
from django.db.models import F

from ...exceptions import ConflictError, LockTimeoutError
from ...persistence.deadline import Deadline
from ...persistence.store import BaseStore
from . import _deadlines
from .fields import sibling_values

__all__ = ["DjangoModelStore", "DjangoStore"]

_LOCK_POLL_S = 0.01
DEFAULT_LOCK_TTL_S = 60.0
DEFAULT_NAMESPACE = "default"


def _app_model(name: str) -> Any:
    # 📝 Via the registry (see `_deadlines._model`).
    from django.apps import apps

    return apps.get_model("xsm_django", name)


def _locked(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return "locked" in msg or "busy" in msg


class DjangoStore(BaseStore):
    """`StateStore` in the ``xsm_django`` app's tables.

    Args:
        namespace: Separates independent stores in the shared tables
            (``source`` column); default ``"default"``.
        using: Database alias (default: ``"default"``).
        lock_ttl_s: Lease lifetime for `lock()`.
        codec / max_snapshot_bytes: As for every `BaseStore`.

    Calls made inside an enclosing ``transaction.atomic()`` join it --
    use that (or `transaction()`) to commit a save with your own rows.
    """

    backend = "django"

    def __init__(
        self,
        namespace: str = DEFAULT_NAMESPACE,
        *,
        using: str = "default",
        lock_ttl_s: float = DEFAULT_LOCK_TTL_S,
        **kw: Any,
    ) -> None:
        super().__init__(**kw)
        if not namespace or len(namespace) > 128:
            raise ValueError("namespace must be 1..128 characters")
        if lock_ttl_s <= 0:
            raise ValueError("lock_ttl_s must be > 0")
        self.namespace = namespace
        self.using = using
        self.lock_ttl_s = float(lock_ttl_s)
        self._local = threading.local()

    @property
    def _model(self) -> Any:
        return _app_model("StatechartSnapshot")

    def _qs(self) -> Any:
        return self._model.objects.using(self.using).filter(
            source=self.namespace
        )

    def transaction(self) -> Any:
        """``transaction.atomic(using=...)`` on this store's database."""
        return transaction.atomic(using=self.using)

    # -- primitives ---------------------------------------------------------------
    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        row = self._qs().filter(key=key).first()
        if row is None:
            return None
        return (
            row.snapshot,
            int(row.version),
            row.machine_version or "",
            float(row.updated_at),
            _deadlines.read(self.using, self.namespace, key),
        )

    def _current(self, key: str) -> Optional[int]:
        v = self._qs().filter(key=key).values_list("version", flat=True)
        return next(iter(v), None)

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        values = {
            "snapshot": data,
            "machine_version": machine_version,
            "updated_at": time.time(),
        }
        try:
            with transaction.atomic(using=self.using):
                new = self._write(key, values, expected_version)
                _deadlines.write(self.using, self.namespace, key, deadlines)
            return new
        except OperationalError as exc:
            if _locked(exc):
                raise LockTimeoutError(key, 0.0) from exc
            raise

    def _write(
        self, key: str, values: Dict[str, Any], expected: Optional[int]
    ) -> int:
        if expected == 0:
            try:
                with transaction.atomic(using=self.using):
                    self._model.objects.using(self.using).create(
                        source=self.namespace, key=key, version=1, **values
                    )
            except IntegrityError:
                raise ConflictError(key, 0, self._current(key))
            return 1
        if expected is not None:
            n = (
                self._qs()
                .filter(key=key, version=expected)
                .update(version=expected + 1, **values)
            )
            if n != 1:
                raise ConflictError(key, expected, self._current(key))
            return expected + 1
        n = (
            self._qs()
            .filter(key=key)
            .update(version=F("version") + 1, **values)
        )
        if n == 1:
            return int(self._current(key) or 1)
        self._model.objects.using(self.using).create(
            source=self.namespace, key=key, version=1, **values
        )
        return 1

    def _delete_raw(self, key: str) -> bool:
        with transaction.atomic(using=self.using):
            n, _ = self._qs().filter(key=key).delete()
            _deadlines.write(self.using, self.namespace, key, ())
        return bool(n)

    def _forget_raw(self, key: str) -> Dict[str, int]:
        StatechartLock = _app_model("StatechartLock")

        with transaction.atomic(using=self.using):
            dl = _deadlines.write(self.using, self.namespace, key, ())
            lk, _ = (
                StatechartLock.objects.using(self.using)
                .filter(source=self.namespace, key=key)
                .delete()
            )
            sn, _ = self._qs().filter(key=key).delete()
        return {"snapshots": int(sn), "deadlines": int(dl), "locks": int(lk)}

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        qs = self._qs()
        if prefix:
            # 📝 `startswith` escapes LIKE wildcards; on SQLite LIKE is
            #    case-insensitive, so re-check exactly in Python.
            qs = qs.filter(key__startswith=prefix)
        keys = [
            k
            for k in qs.order_by("key").values_list("key", flat=True)
            if k.startswith(prefix)
        ]
        return keys[:limit]

    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        """``(key, earliest due_at)`` from the deadline index."""
        return _deadlines.due(self.using, self.namespace, until_wall, limit)

    # -- lease ----------------------------------------------------------------------
    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return self._lease(key, timeout)

    def _try_lock(self, key: str, owner: str) -> bool:
        now = time.time()
        mgr = _app_model("StatechartLock").objects.using(self.using)
        try:
            with transaction.atomic(using=self.using):
                mgr.filter(
                    source=self.namespace, key=key, expires_at__lt=now
                ).delete()
                mgr.create(
                    source=self.namespace,
                    key=key,
                    owner=owner,
                    expires_at=now + self.lock_ttl_s,
                )
            return True
        except IntegrityError:
            return False
        except OperationalError as exc:
            if _locked(exc):
                return False
            raise

    @contextlib.contextmanager
    def _lease(self, key: str, timeout: float) -> Iterator[None]:
        StatechartLock = _app_model("StatechartLock")

        held = getattr(self._local, "held", None)
        if held is None:
            held = self._local.held = set()
        if key in held:  # re-entrant on this thread
            yield
            return
        owner = uuid.uuid4().hex
        deadline = time.monotonic() + timeout
        while not self._try_lock(key, owner):
            if time.monotonic() >= deadline:
                raise LockTimeoutError(key, timeout)
            time.sleep(_LOCK_POLL_S)
        held.add(key)
        try:
            yield
        finally:
            held.discard(key)
            with contextlib.suppress(Exception):
                StatechartLock.objects.using(self.using).filter(
                    source=self.namespace, key=key, owner=owner
                ).delete()

    def health(self) -> Dict[str, Any]:
        try:
            n = self._qs().count()
            from django.db import connections

            return {
                "ok": True,
                "backend": self.backend,
                "vendor": connections[self.using].vendor,
                "namespace": self.namespace,
                "keys": int(n),
            }
        except Exception as exc:  # noqa: BLE001 - a probe never raises
            return {
                "ok": False,
                "backend": self.backend,
                "error": type(exc).__name__,
            }


# -----------------------------------------------------------------------------
# ⏰ DjangoModelStore -- the scanner's view of a model
# -----------------------------------------------------------------------------
class DjangoModelStore(BaseStore):
    """Row-backed store over a `StatechartModelMixin` model (see module
    notes). `lock()` is a no-op (the fence is ``<field>_version``); use
    the default `OptimisticLock`."""

    backend = "django-model"

    def __init__(
        self, model: Any, *, using: str = "default", **kw: Any
    ) -> None:
        from .mixin import statechart_field

        super().__init__(**kw)
        self.model = model
        self.using = using
        self.field = statechart_field(model).name
        self.vcol = f"{self.field}_version"
        self.source = model._meta.db_table

    def _mgr(self) -> Any:
        return self.model._base_manager.using(self.using)

    def _pk(self, key: str) -> Any:
        return self.model._meta.pk.to_python(key)

    def _load_raw(
        self, key: str
    ) -> Optional[Tuple[str, int, str, float, Sequence[Deadline]]]:
        row = (
            self._mgr()
            .filter(pk=self._pk(key))
            .values_list(self.field, self.vcol)
            .first()
        )
        if row is None or row[0] is None:
            return None
        snap = row[0]
        if isinstance(snap, str):
            snap = json.loads(snap)
        mv = snap.get("machine_version")
        return (
            json.dumps(snap),
            int(row[1] or 0),
            "" if mv is None else str(mv),
            float(snap.get("taken_at") or time.time()),
            _deadlines.read(self.using, self.source, key),
        )

    def _save_raw(
        self,
        key: str,
        data: str,
        expected_version: Optional[int],
        machine_version: str,
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        snap = json.loads(data)
        # 🐛 #264 battle: `DjangoStore` mapped a busy database to the typed
        #    `LockTimeoutError`; this twin leaked Django's bare
        #    `OperationalError('database is locked')` -- 4 `xsm_deadlines`
        #    workers on SQLite filed 12 of 20 rows under `errors`.
        try:
            return self._save_row(key, snap, expected_version, deadlines)
        except OperationalError as exc:
            if _locked(exc):
                raise LockTimeoutError(key, 0.0) from exc
            raise

    def _save_row(
        self,
        key: str,
        snap: Any,
        expected_version: Optional[int],
        deadlines: Tuple[Deadline, ...],
    ) -> int:
        with transaction.atomic(using=self.using):
            cur = (
                self._mgr()
                .filter(pk=self._pk(key))
                .values_list(self.vcol, flat=True)
                .first()
            )
            if cur is None:
                raise ConflictError(key, expected_version, None)
            cur = int(cur or 0)
            if expected_version is not None and expected_version != cur:
                raise ConflictError(key, expected_version, cur)
            values = sibling_values(self.field, snap)
            values[self.field] = snap
            values[self.vcol] = cur + 1
            n = (
                self._mgr()
                .filter(pk=self._pk(key), **{self.vcol: cur})
                .update(**values)
            )
            if n != 1:
                raise ConflictError(key, expected_version, None)
            _deadlines.write(self.using, self.source, key, deadlines)
        return cur + 1

    def _delete_raw(self, key: str) -> bool:
        raise NotImplementedError(
            "DjangoModelStore never deletes rows; delete the model instance."
        )

    def _forget_raw(self, key: str) -> Dict[str, int]:
        row = self._mgr().filter(pk=self._pk(key)).first()
        if row is None:
            return {"snapshots": 0, "deadlines": 0}
        return row.forget_statechart(using=self.using)

    def _list_keys_raw(self, prefix: str, limit: int) -> List[str]:
        pks = (
            self._mgr()
            .exclude(**{f"{self.field}__isnull": True})
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        keys = sorted(str(p) for p in pks if str(p).startswith(prefix))
        return keys[:limit]

    def due_keys(
        self, until_wall: float, *, limit: int = 1000
    ) -> List[Tuple[str, float]]:
        return _deadlines.due(self.using, self.source, until_wall, limit)

    def _lock_raw(self, key: str, timeout: float) -> ContextManager[None]:
        return contextlib.nullcontext()
