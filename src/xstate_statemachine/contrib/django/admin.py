# src/xstate_statemachine/contrib/django/admin.py
# -----------------------------------------------------------------------------
# 🛠️ StatechartAdminMixin -- transition buttons in the Django admin
# -----------------------------------------------------------------------------
# 🏛️ Half of a Django team never leaves the admin. On the change form this
#    adds one button per event THIS user may send right now
#    (`has_event_permission`: the live `can()` as that user + every
#    permission guard), the audit history inline, a state badge and a
#    Mermaid diagram view; on the changelist a state column, a state
#    filter and one bulk action per event.
#
# 🔐 Security (X0.7, the admin amendment):
#      * buttons are POST forms carrying Django's CSRF token -- never GET
#        links; a GET to the transition URL renders the confirm form and
#        changes NOTHING; a POST without the token is 403 (CsrfViewMiddleware
#        + `csrf_protect` on the view);
#      * the permission is RE-CHECKED on POST (the page may be stale, or
#        forged): the admin's change permission AND `has_event_permission`;
#      * events tagged ``meta.confirm`` (or in `xsm_confirm_events`) go
#        through a confirmation page with a ``reason`` field; the reason
#        and ``actor=request.user`` land in the audit row;
#      * all UI strings are ``gettext_lazy``; labels come from the
#        transition's ``meta.title`` / ``description``, falling back to
#        the event id.
# -----------------------------------------------------------------------------
"""`StatechartAdminMixin`, `TransitionLogInline`, `StateListFilter`."""

from __future__ import annotations

import logging
import sys
import re
from typing import Any, Dict, List, Optional, Tuple

from django.contrib import admin, messages
from django.contrib.contenttypes.admin import GenericTabularInline
from django.core.exceptions import AppRegistryNotReady, PermissionDenied
from django.http import Http404, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.decorators import method_decorator
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_protect

from ...exceptions import (
    ConflictError,
    LockTimeoutError,
    StoreUnavailableError,
    XStateMachineError,
)
from ._events import declared_events
from .permissions import has_event_permission, permitted_events

logger = logging.getLogger(__name__)
#: Bulk-action errors the operator should retry.
_RETRYABLE = (LockTimeoutError, ConflictError, StoreUnavailableError)

__all__ = [
    "StateListFilter",
    "StatechartAdminMixin",
    "TransitionLogAdmin",
    "TransitionLogInline",
    "event_label",
]

csrf_protect_m = method_decorator(csrf_protect)
EVENT_FIELD = "_xsm_event"


def _transition_meta(machine: Any, event: str) -> Dict[str, Any]:
    """The first ``meta`` found on a transition for *event*."""
    stack = [machine]
    while stack:
        node = stack.pop()
        for t in (node.on or {}).get(event, []):
            meta = getattr(t, "meta", None) or {}
            if meta:
                return dict(meta)
        stack.extend(node.states.values())
    return {}


def event_label(machine: Any, event: str) -> str:
    """``meta.title`` → ``meta.description`` → the event id."""
    meta = _transition_meta(machine, event)
    return str(meta.get("title") or meta.get("description") or event)


def _state_label(machine: Any, state_id: str) -> str:
    node = machine.get_state_by_id(state_id)
    meta = getattr(node, "meta", None) or {}
    return str(
        meta.get("title")
        or getattr(node, "description", None)
        or state_id.split(".", 1)[-1]
    )


class TransitionLogInline(GenericTabularInline):
    """Read-only audit history (newest first) on the change form."""

    ct_field = "content_type"
    ct_fk_field = "object_id"
    extra = 0
    can_delete = False
    ordering = ("-seq",)
    verbose_name = _("transition")
    verbose_name_plural = _("transition history")
    fields = (
        "seq",
        "event",
        "disposition",
        "from_states",
        "to_states",
        "actor",
        "reason",
        "created",
    )
    readonly_fields = fields
    #: Newest rows shown on the change form. A long-lived row can have
    #: thousands of audit rows; rendering them all made the change page
    #: megabytes large (#280 battle). ``None`` shows everything.
    max_rows: Optional[int] = 50

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        from django.apps import apps

        self.model = apps.get_model("xsm_django", "TransitionLog")
        super().__init__(*args, **kwargs)

    def get_queryset(self, request: Any) -> Any:
        return super().get_queryset(request).select_related("actor")

    def get_formset(self, request: Any, obj: Any = None, **kw: Any) -> Any:
        formset = super().get_formset(request, obj, **kw)
        limit = self.max_rows
        if limit is None:
            return formset

        class Capped(formset):  # type: ignore[misc, valid-type]
            # 📝 The generic formset FILTERS the queryset it is given, so
            #    the slice must happen here, after that filter.
            def get_queryset(self) -> Any:
                if not hasattr(self, "_xsm_capped"):
                    self._xsm_capped = super().get_queryset()[:limit]
                return self._xsm_capped

        Capped.__name__ = formset.__name__
        return Capped

    def has_add_permission(self, request: Any, obj: Any = None) -> bool:
        return False

    def has_view_permission(self, request: Any, obj: Any = None) -> bool:
        # 🔥 #280 battle: the default asks for ``xsm_django.view_
        #    transitionlog`` -- a permission nobody grants -- so every
        #    non-superuser saw NO history. Whoever may view the row may
        #    view its audit trail.
        opts = self.parent_model._meta
        return bool(
            request.user.has_perm(f"{opts.app_label}.view_{opts.model_name}")
            or request.user.has_perm(
                f"{opts.app_label}.change_{opts.model_name}"
            )
        )

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        return False


class TransitionLogAdmin(admin.ModelAdmin):
    """Append-only audit changelist: filter by event / disposition /
    actor, search by object id or reason. Nobody -- superusers included
    -- can add, edit or delete a row here; erasure is `forget_statechart`
    (redact by default), which keeps the ``seq`` chain gapless.
    Registered automatically unless ``XSM_ADMIN_TRANSITIONLOG = False``."""

    list_display = (
        "created",
        "content_type",
        "object_id",
        "seq",
        "event",
        "disposition",
        "actor",
        "short_payload",
    )
    list_filter = ("disposition", "event", "content_type")
    search_fields = ("object_id", "event", "reason", "correlation_id")
    list_select_related = ("actor", "content_type")
    date_hierarchy = "created"
    #: The changelist cuts ``payload`` to this many characters.
    payload_preview = 120

    @admin.display(description=_("payload"))
    def short_payload(self, obj: Any) -> str:
        import json

        text = json.dumps(obj.payload, default=str, sort_keys=True)
        cap = self.payload_preview
        return text if len(text) <= cap else text[: cap - 1] + "…"

    def get_list_filter(self, request: Any) -> Any:
        return tuple(self.list_filter) + (
            ("actor", admin.RelatedOnlyFieldListFilter),
        )

    def get_readonly_fields(self, request: Any, obj: Any = None) -> Any:
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request: Any) -> bool:
        return False

    def has_change_permission(self, request: Any, obj: Any = None) -> bool:
        return False

    def has_delete_permission(self, request: Any, obj: Any = None) -> bool:
        return False


def _register_log_admin() -> None:
    from django.apps import apps
    from django.conf import settings

    if not getattr(settings, "XSM_ADMIN_TRANSITIONLOG", True):
        return
    if not apps.is_installed("django.contrib.admin"):  # pragma: no cover
        return
    model = apps.get_model("xsm_django", "TransitionLog")
    if not admin.site.is_registered(model):
        admin.site.register(model, TransitionLogAdmin)


class StateListFilter(admin.SimpleListFilter):
    """Filter the changelist by active state (any leaf, or an ancestor)."""

    title = _("state")
    parameter_name = "xsm_state"

    def lookups(self, request: Any, model_admin: Any) -> List[Tuple[str, str]]:
        from ...validation import walk

        machine = model_admin.model().statechart_machine_node()
        return [
            (n.id, n.id.split(".", 1)[-1])
            for n in walk(machine)
            if n is not machine
        ]

    def queryset(self, request: Any, queryset: Any) -> Any:
        value = self.value()
        if not value:
            return queryset
        return queryset.in_state(value)


class StatechartAdminMixin:
    """Mix into a ``ModelAdmin`` for a `StatechartModelMixin` model::

        @admin.register(Order)
        class OrderAdmin(StatechartAdminMixin, admin.ModelAdmin):
            xsm_confirm_events = ["CANCEL"]

    Template blocks (override ``admin/xsm/change_form.html``):
    ``xsm_badge``, ``xsm_transitions``; the confirm page is
    ``admin/xsm/confirm_transition.html`` (block ``xsm_confirm_form``).
    """

    change_form_template = "admin/xsm/change_form.html"
    #: Events that always need the confirmation page (+ ``meta.confirm``).
    xsm_confirm_events: Tuple[str, ...] = ()
    #: Add the history inline / bulk actions / list column + filter.
    xsm_history_inline: bool = True
    xsm_bulk_actions: bool = True
    #: Provided by `ModelAdmin` (declared for type checkers).
    model: Any

    # -- wiring ---------------------------------------------------------------------
    def get_inlines(self, request: Any, obj: Any) -> List[Any]:
        inlines = list(super().get_inlines(request, obj))  # type: ignore[misc]
        if self.xsm_history_inline and obj is not None:
            if TransitionLogInline not in inlines:
                inlines.append(TransitionLogInline)
        return inlines

    def get_readonly_fields(self, request: Any, obj: Any = None) -> Any:
        base = tuple(super().get_readonly_fields(request, obj))  # type: ignore[misc]
        return base + ("statechart_state_display",)

    def get_list_display(self, request: Any) -> Any:
        base = tuple(super().get_list_display(request))  # type: ignore[misc]
        if "statechart_state_display" not in base:
            base = base + ("statechart_state_display",)
        return base

    def get_list_filter(self, request: Any) -> Any:
        base = tuple(super().get_list_filter(request))  # type: ignore[misc]
        return base + (StateListFilter,)

    @admin.display(description=_("state"))
    def statechart_state_display(self, obj: Any) -> Any:
        if obj is None or obj.pk is None:
            return "-"
        machine = obj.statechart_machine_node()
        labels = ", ".join(_state_label(machine, s) for s in obj.state_ids)
        info = self.model._meta.app_label, self.model._meta.model_name
        url = reverse("admin:%s_%s_xsm_diagram" % info, args=[obj.pk])
        return format_html(
            '<span class="xsm-state" title="{}">{}</span> '
            '<a href="{}">{}</a>',
            obj.state or "",
            labels or "-",
            url,
            _("diagram"),
        )

    # -- change form ------------------------------------------------------------------
    def xsm_buttons(self, request: Any, obj: Any) -> List[Dict[str, Any]]:
        """``[{event, label, confirm}]`` this user may press now."""
        if obj is None or not self.has_change_permission(request, obj):  # type: ignore[attr-defined]
            return []
        machine = obj.statechart_machine_node()
        return [
            {
                "event": e,
                "label": event_label(machine, e),
                "confirm": self._needs_confirm(machine, e),
            }
            for e in permitted_events(request.user, obj)
        ]

    def _needs_confirm(self, machine: Any, event: str) -> bool:
        if event in self.xsm_confirm_events:
            return True
        return bool(_transition_meta(machine, event).get("confirm"))

    def render_change_form(
        self, request: Any, context: Dict[str, Any], *args: Any, **kw: Any
    ) -> Any:
        obj = kw.get("obj") or (args[2] if len(args) > 2 else None)
        context["xsm_buttons"] = self.xsm_buttons(request, obj)
        context["xsm_event_field"] = EVENT_FIELD
        if obj is not None and obj.pk is not None:
            info = self.model._meta.app_label, self.model._meta.model_name
            context["xsm_transition_url"] = reverse(
                "admin:%s_%s_xsm_transition" % info, args=[obj.pk]
            )
        return super().render_change_form(request, context, *args, **kw)  # type: ignore[misc]

    # -- urls / views -----------------------------------------------------------------
    def get_urls(self) -> List[Any]:
        info = self.model._meta.app_label, self.model._meta.model_name  # type: ignore[attr-defined]
        wrap = self.admin_site.admin_view  # type: ignore[attr-defined]
        return [
            path(
                "<path:object_id>/xsm-transition/",
                wrap(self.xsm_transition_view),
                name="%s_%s_xsm_transition" % info,
            ),
            path(
                "<path:object_id>/statechart/",
                wrap(self.xsm_diagram_view),
                name="%s_%s_xsm_diagram" % info,
            ),
        ] + super().get_urls()  # type: ignore[misc]

    def _xsm_object(self, request: Any, object_id: str) -> Any:
        """The row, or 404 -- but only to a user who may see the model at
        all (anyone else gets 403 and learns nothing about which pks
        exist)."""
        obj = self.get_object(request, object_id)  # type: ignore[attr-defined]
        if obj is None:
            if not self.has_view_permission(request):  # type: ignore[attr-defined]
                raise PermissionDenied
            raise Http404
        return obj

    def _change_url(self, obj: Any) -> str:
        info = self.model._meta.app_label, self.model._meta.model_name  # type: ignore[attr-defined]
        return reverse("admin:%s_%s_change" % info, args=[obj.pk])

    @csrf_protect_m
    def xsm_transition_view(self, request: Any, object_id: str) -> Any:
        """GET: the confirm form (no state change). POST: re-check the
        permission, then send with ``actor=request.user``."""
        obj = self._xsm_object(request, object_id)
        if not self.has_view_permission(request, obj):  # type: ignore[attr-defined]
            # 🔐 #282 battle: the confirm page named the object and the
            #    event to a staff user with no permission on the model.
            raise PermissionDenied
        event = request.POST.get(EVENT_FIELD) or request.GET.get(EVENT_FIELD)
        machine = obj.statechart_machine_node()
        if not event or event not in declared_events(machine):
            raise PermissionDenied
        confirmed = request.POST.get("_xsm_confirmed") == "1"
        needs = self._needs_confirm(machine, event)
        if request.method != "POST" or (needs and not confirmed):
            return self._confirm_page(request, obj, event, machine)
        return self._apply(request, obj, event)

    def _confirm_page(
        self, request: Any, obj: Any, event: str, machine: Any
    ) -> Any:
        opts = self.model._meta  # type: ignore[attr-defined]
        ctx = {
            **self.admin_site.each_context(request),  # type: ignore[attr-defined]
            "opts": opts,
            "object": obj,
            "title": _("Confirm transition"),
            "event": event,
            "label": event_label(machine, event),
            "event_field": EVENT_FIELD,
            "allowed": self._allowed(request, obj, event),
            "change_url": self._change_url(obj),
        }
        return TemplateResponse(
            request, "admin/xsm/confirm_transition.html", ctx
        )

    def _allowed(self, request: Any, obj: Any, event: str) -> bool:
        return bool(
            self.has_change_permission(request, obj)  # type: ignore[attr-defined]
            and has_event_permission(request.user, obj, event)
        )

    def _apply(self, request: Any, obj: Any, event: str) -> Any:
        if not self.has_change_permission(request, obj):  # type: ignore[attr-defined]
            # 🔐 #280 battle: no change permission at all is a forged
            #    request (no button was ever rendered) -- 403, like
            #    Django's own change view, not a friendly redirect.
            raise PermissionDenied
        machine = obj.statechart_machine_node()
        label = event_label(machine, event)
        if not self._allowed(request, obj, event):
            self.message_user(  # type: ignore[attr-defined]
                request,
                _("You may not perform “%(event)s” on this object now.")
                % {"event": label},
                messages.WARNING,
            )
            return HttpResponseRedirect(self._change_url(obj))
        reason = (request.POST.get("reason") or "").strip()[:2000] or None
        try:
            receipt = obj.send(event, actor=request.user, reason=reason)
        except XStateMachineError as exc:
            # 🔥 #281 battle: a lock timeout / conflict / vetoing receiver
            #    is an answer for the operator, not a 500 page.
            self.message_user(  # type: ignore[attr-defined]
                request,
                _("“%(event)s” failed: %(error)s")
                % {"event": label, "error": exc},
                messages.ERROR,
            )
            return HttpResponseRedirect(self._change_url(obj))
        if receipt.error is not None:
            self.message_user(  # type: ignore[attr-defined]
                request,
                _("“%(event)s” ran with an error: %(error)s")
                % {"event": label, "error": receipt.error},
                messages.ERROR,
            )
        elif receipt.changed:
            self.message_user(  # type: ignore[attr-defined]
                request,
                _("“%(event)s” done.") % {"event": label},
                messages.SUCCESS,
            )
        else:
            self.message_user(  # type: ignore[attr-defined]
                request,
                _("“%(event)s” was refused.") % {"event": label},
                messages.WARNING,
            )
        return HttpResponseRedirect(self._change_url(obj))

    def xsm_diagram_view(self, request: Any, object_id: str) -> Any:
        """The chart as Mermaid, active states highlighted (needs view
        permission)."""
        obj = self._xsm_object(request, object_id)
        if not self.has_view_permission(request, obj):  # type: ignore[attr-defined]
            raise PermissionDenied
        machine = obj.statechart_machine_node()
        ctx = {
            **self.admin_site.each_context(request),  # type: ignore[attr-defined]
            "opts": self.model._meta,  # type: ignore[attr-defined]
            "object": obj,
            "title": _("Statechart"),
            "mermaid": highlighted_mermaid(machine, obj.state_ids),
            "change_url": self._change_url(obj),
        }
        return TemplateResponse(request, "admin/xsm/diagram.html", ctx)

    # -- bulk actions -----------------------------------------------------------------
    def get_actions(
        self, request: Any, action_location: Any = None
    ) -> Dict[str, Any]:
        # 📝 Django 6.1 passes ``action_location`` (and warns when an
        #    override does not accept it); older releases never do.
        if action_location is None:
            actions = super().get_actions(request)  # type: ignore[misc]
        else:
            actions = super().get_actions(  # type: ignore[misc]
                request, action_location=action_location
            )
        if not self.xsm_bulk_actions:
            return actions
        # 🔐 #282 battle: these are added AFTER Django's own
        #    ``allowed_permissions`` filter, so a view-only user was
        #    offered every transition in the dropdown. Gate them here.
        if not self.has_change_permission(request):  # type: ignore[attr-defined]
            return actions
        machine = self.model().statechart_machine_node()  # type: ignore[attr-defined]
        for event in declared_events(machine):
            name = f"xsm_{event}"
            fn = self._bulk_action(event, event_label(machine, event))
            actions[name] = (fn, name, fn.short_description)
        return actions

    def _bulk_action(self, event: str, label: str) -> Any:
        def action(modeladmin: Any, request: Any, queryset: Any) -> None:
            changed = denied = failed = 0
            # 📝 ``iterator()``: a 10k-row selection is streamed, not
            #    cached on the queryset for the life of the request.
            for obj in queryset.iterator(chunk_size=500):
                if not modeladmin._allowed(request, obj, event):
                    denied += 1
                    continue
                try:
                    r = obj.send(event, actor=request.user)
                except _RETRYABLE:
                    # 🔥 #282 battle: a lock timeout / conflict / store
                    #    outage is not a refusal -- the operator must know
                    #    to retry it (review: ONLY those; a config error
                    #    such as a missing implementation is a denial --
                    #    retrying cannot help, and it is logged).
                    failed += 1
                    continue
                except modeladmin.model.DoesNotExist:
                    # 📝 review #282: a row deleted mid-bulk ended the whole
                    #    action in a 500 with no counts at all
                    denied += 1
                    continue
                except XStateMachineError:
                    logger.warning(
                        "bulk %s on %s refused: %s",
                        event,
                        getattr(obj, "pk", "?"),
                        type(sys.exc_info()[1]).__name__,
                    )
                    denied += 1
                    continue
                if r.changed:
                    changed += 1
                else:
                    denied += 1
            text = _("%(event)s: %(changed)d changed / %(denied)d denied") % {
                "event": label,
                "changed": changed,
                "denied": denied,
            }
            level = messages.SUCCESS if not denied else messages.WARNING
            if failed:
                text = _("%(text)s / %(failed)d failed (retry them)") % {
                    "text": text,
                    "failed": failed,
                }
                level = messages.ERROR
            modeladmin.message_user(request, text, level)

        action.short_description = _("Send “%(event)s”") % {"event": label}  # type: ignore[attr-defined]
        action.__name__ = f"xsm_{event}"
        return action


_MERMAID_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def _walk(machine: Any) -> Any:
    from ...validation import walk

    return walk(machine)


def highlighted_mermaid(machine: Any, active: Optional[List[str]]) -> str:
    """`to_mermaid()` plus a ``classDef`` marking the active leaves."""
    text = machine.to_mermaid()
    # 🔐 #282 battle: only keys of real states, and only Mermaid-safe
    #    ones -- a hostile column value must not add directives such as
    #    ``click x call fn()`` to the diagram.
    known = {n.key for n in _walk(machine)}
    ids = [
        k
        for k in (s.split(".")[-1] for s in (active or ()))
        if k in known and _MERMAID_ID.match(k)
    ]
    if not ids:
        return text
    lines = [text, "    classDef xsmActive fill:#ffd54f,stroke:#e65100"]
    for sid in ids:
        lines.append(f"    class {sid} xsmActive")
    return "\n".join(lines)


try:  # 📝 runs on admin autodiscovery (this IS the app's admin module)
    _register_log_admin()
except (LookupError, AppRegistryNotReady):  # pragma: no cover
    pass
