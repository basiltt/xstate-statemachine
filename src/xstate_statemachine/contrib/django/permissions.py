# src/xstate_statemachine/contrib/django/permissions.py
# -----------------------------------------------------------------------------
# 🔐 PermissionGuard / RoleGuard / has_event_permission
# -----------------------------------------------------------------------------
# 🏛️ A permission is a GUARD, so the chart states the rule once and every
#    surface (``send``, ``can``, admin buttons, DRF actions, Channels)
#    answers "may THIS user do it" the same way:
#
#        guards={"canApprove": PermissionGuard("shop.approve_order")}
#
#    The guard reads the acting user from the send in progress
#    (``send(actor=user)`` → `current_actor`; the payload carries only
#    ``actor_id``, so snapshots and audit rows stay JSON) and evaluates
#    ``user.has_perm(perm, obj=row)`` -- object-level permissions work
#    whenever the auth backend supports them. No actor → ``False``.
#
# 📝 `has_event_permission(user, instance, event)` is the single answer
#    the admin (D3) and DRF (D4) use: ``can(event)`` as *user* AND every
#    guard on the event's enabled transitions that is a permission guard
#    passes. A chart with no permission guard on an event is NOT open by
#    that fact alone -- the web surfaces still require an explicit policy
#    (DRF permission classes, the admin's change permission) (X0.1).
# -----------------------------------------------------------------------------
"""`PermissionGuard`, `RoleGuard`, `AnyOf`, `AllOf`, `has_event_permission`."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Tuple

from .mixin import current_actor, current_instance

__all__ = [
    "AllOf",
    "AnyOf",
    "PermissionGuard",
    "RoleGuard",
    "StatechartPermission",
    "has_event_permission",
]


def _actor(event: Any) -> Any:
    """The user object for this evaluation, or ``None``."""
    user = current_actor.get()
    if user is not None:
        return user
    payload = getattr(event, "payload", None) or {}
    actor = payload.get("actor")
    return actor if hasattr(actor, "has_perm") else None


class _PermissionGuardBase:
    """Marker base: `has_event_permission` treats these as permission
    guards. Callable as ``(context, event) -> bool``."""

    def check(self, user: Any, obj: Any) -> bool:  # pragma: no cover
        raise NotImplementedError

    def __call__(self, context: Any, event: Any) -> bool:
        user = _actor(event)
        if user is None or not getattr(user, "is_active", True):
            return False
        return bool(self.check(user, current_instance.get()))


class PermissionGuard(_PermissionGuardBase):
    """``user.has_perm(perm, obj=row)`` for every *perms* (all required).

    Args:
        perms: ``"app_label.codename"`` strings.
        object_level: Also pass the row (``obj=``) to the backend
            (default ``True``); the model backend then answers ``False``
            for object checks, so rely on it only with an object-aware
            backend -- a global permission is also accepted via
            ``fallback_global=True`` (default).
    """

    def __init__(
        self,
        *perms: str,
        object_level: bool = True,
        fallback_global: bool = True,
    ) -> None:
        if not perms or not all(
            isinstance(p, str) and "." in p for p in perms
        ):
            raise ValueError(
                "PermissionGuard needs 'app_label.codename' permission names"
            )
        self.perms: Tuple[str, ...] = tuple(perms)
        self.object_level = object_level
        self.fallback_global = fallback_global

    def check(self, user: Any, obj: Any) -> bool:
        for perm in self.perms:
            ok = False
            if self.object_level and obj is not None:
                ok = bool(user.has_perm(perm, obj))
            if not ok and (self.fallback_global or obj is None):
                ok = bool(user.has_perm(perm))
            if not ok:
                return False
        return True

    def __repr__(self) -> str:
        return f"PermissionGuard{self.perms!r}"


class RoleGuard(_PermissionGuardBase):
    """Member of ANY of *groups* (Django ``Group`` names); superusers pass
    when ``allow_superuser`` (default)."""

    def __init__(self, *groups: str, allow_superuser: bool = True) -> None:
        if not groups:
            raise ValueError("RoleGuard needs at least one group name")
        self.groups = tuple(groups)
        self.allow_superuser = allow_superuser

    def check(self, user: Any, obj: Any) -> bool:
        if self.allow_superuser and getattr(user, "is_superuser", False):
            return True
        return bool(user.groups.filter(name__in=self.groups).exists())

    def __repr__(self) -> str:
        return f"RoleGuard{self.groups!r}"


class AnyOf(_PermissionGuardBase):
    """Passes when any child permission guard passes."""

    def __init__(self, *guards: _PermissionGuardBase) -> None:
        if not guards:
            raise ValueError("AnyOf needs at least one guard")
        self.guards = guards

    def check(self, user: Any, obj: Any) -> bool:
        return any(g.check(user, obj) for g in self.guards)


class AllOf(_PermissionGuardBase):
    """Passes when every child permission guard passes."""

    def __init__(self, *guards: _PermissionGuardBase) -> None:
        if not guards:
            raise ValueError("AllOf needs at least one guard")
        self.guards = guards

    def check(self, user: Any, obj: Any) -> bool:
        return all(g.check(user, obj) for g in self.guards)


# -----------------------------------------------------------------------------
# 🧮 has_event_permission
# -----------------------------------------------------------------------------
def _guard_names(guard_def: Any) -> List[str]:
    if guard_def is None:
        return []
    if getattr(guard_def, "is_composite", False):
        out: List[str] = []
        for child in guard_def.children:
            out += _guard_names(child)
        return out
    return [guard_def.type]


def permission_guards_for(instance: Any, event: str) -> List[Any]:
    """The permission guards on *event*'s transitions from the row's
    active states (the ones `has_event_permission` re-checks)."""
    interp = instance.machine
    guards = interp.machine.logic.guards
    out: List[Any] = []
    for node in interp._active_state_nodes:
        for t in node.on.get(event, []) if node.on else []:
            for name in _guard_names(getattr(t, "guard_def", None)):
                g = guards.get(name)
                if isinstance(g, _PermissionGuardBase):
                    out.append(g)
    return out


def has_event_permission(user: Any, instance: Any, event: str) -> bool:
    """May *user* send *event* to *instance* right now?

    ``instance.can(event, actor=user)`` -- guards run with *user* as the
    actor -- AND every permission guard on the event's candidate
    transitions passes for *user*. Anonymous / inactive users → ``False``.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", True):
        return False
    if not instance.can(event, actor=user):
        return False
    token_a = current_actor.set(user)
    token_i = current_instance.set(instance)
    try:
        return all(
            g.check(user, instance)
            for g in permission_guards_for(instance, event)
        )
    finally:
        current_instance.reset(token_i)
        current_actor.reset(token_a)


def permitted_events(user: Any, instance: Any) -> List[str]:
    """The declared events *user* may send to *instance* now."""
    from ._events import declared_events

    return [
        e
        for e in declared_events(instance.statechart_machine_node())
        if has_event_permission(user, instance, e)
    ]


class StatechartPermission:
    """Framework-neutral policy object: subclass to add a rule, reuse in
    the admin and DRF. ``has_event_permission`` is the whole contract."""

    def has_event_permission(
        self, user: Any, instance: Any, event: Optional[str]
    ) -> bool:
        if event is None:  # a read
            return bool(
                user is not None and getattr(user, "is_authenticated", False)
            )
        return has_event_permission(user, instance, event)

    def permitted_events(self, user: Any, instance: Any) -> List[str]:
        return [
            e
            for e in _declared(instance)
            if self.has_event_permission(user, instance, e)
        ]


def _declared(instance: Any) -> Iterable[str]:
    from ._events import declared_events

    return declared_events(instance.statechart_machine_node())
