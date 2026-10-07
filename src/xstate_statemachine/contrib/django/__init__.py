# src/xstate_statemachine/contrib/django/__init__.py
# -----------------------------------------------------------------------------
# 🦄 [django] -- a real statechart on a Django model
# -----------------------------------------------------------------------------
# 🏛️ The ORM twin of `contrib.sqlalchemy`. A Django app
#    (``INSTALLED_APPS += ["xstate_statemachine.contrib.django"]``) that
#    gives a model:
#
#      * `StatechartField` -- the snapshot (JSON) plus generated sibling
#        columns ``<name>_state`` / ``_state_ids`` / ``_version`` /
#        ``_machine_version`` so ``filter(statechart__state=...)`` and
#        ``Model.objects.in_state(...)`` are plain indexed queries;
#      * `StatechartModelMixin` -- ``send / can / available_events /
#        machine``; ``send()`` runs inside ``transaction.atomic()`` with a
#        row lock (``select_for_update``) by default, or an optimistic
#        ``version`` fence (`ConflictError`, ``send_with_retry``);
#      * `DjangoStore` -- the A2 `StateStore` contract on the ORM, and a
#        deadlines table that `DueTimerScanner` / ``manage.py
#        xsm_deadlines`` fire.
#
# 📝 Everything that touches a Django MODEL is imported lazily: this
#    package is importable before ``django.setup()`` (the extras matrix
#    and ``settings.INSTALLED_APPS`` both import it), models are not.
# -----------------------------------------------------------------------------
"""Django integration.

Install with ``pip install "xstate-statemachine[django]"`` and add
``"xstate_statemachine.contrib.django"`` to ``INSTALLED_APPS``.
"""

from __future__ import annotations

import importlib
from typing import Any

from .._compat import require_extra

require_extra("django", "django")

#: public name -> submodule (resolved on first attribute access).
_LAZY = {
    "StatechartField": ".fields",
    "StatechartModelMixin": ".mixin",
    "StatechartQuerySet": ".mixin",
    "StatechartManager": ".mixin",
    "send_with_retry": ".mixin",
    "DjangoStore": ".stores",
    "DjangoModelStore": ".stores",
    "StatechartDeadline": ".models",
    "refresh_statechart_columns": ".migration_helpers",
    "resolve_machine": "._machine",
    # 📣 #281 -- signals, audit, permissions, outbox
    "pre_transition": ".signals",
    "post_transition": ".signals",
    "statechart_error": ".signals",
    "TransitionVetoed": ".signals",
    "DjangoSignalPlugin": ".signals",
    "TransitionLog": ".models",
    "DjangoAuditPlugin": ".audit",
    "DjangoTransitionLogStore": ".audit",
    "PermissionGuard": ".permissions",
    "RoleGuard": ".permissions",
    "AnyOf": ".permissions",
    "AllOf": ".permissions",
    "StatechartPermission": ".permissions",
    "has_event_permission": ".permissions",
    "permitted_events": ".permissions",
    "DjangoOutboxStore": ".outbox",
    "DjangoInbox": ".inbox",  # #283 Idempotency-Key
    # 🛠️ #282 -- admin
    "StatechartAdminMixin": ".admin",
    "TransitionLogInline": ".admin",
    "TransitionLogAdmin": ".admin",
    "StateListFilter": ".admin",
    # 🔁 #310 -- migrating from django-fsm
    "extract_chart": ".fsm",
    "migrate_rows": ".fsm",
    "FSMDualWriteMixin": ".fsm",
}

__all__ = sorted(_LAZY)


def __getattr__(name: str) -> Any:
    module = _LAZY.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return getattr(importlib.import_module(module, __name__), name)
