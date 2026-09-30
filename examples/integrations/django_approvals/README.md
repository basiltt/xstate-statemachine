# Django approvals — parallel review, two roles, admin, DRF, Channels

An expense-approval app on `xstate-statemachine[django,drf,channels]`.
Legal and finance review **in parallel**. Each region needs its own role,
and the chart states the rule once. The admin, the REST API and the
WebSocket all ask it the same question.

```
draft ──SUBMIT──▶ review ═══════════════════════════════╗ ──onDone──▶ approved (publish)
                  ║ legal:   pending ──LEGAL_APPROVE [isLegal]──▶ approved   ║
                  ║ finance: pending ──FINANCE_APPROVE [isFinance]──▶ approved║
                  ║ after 48 h: escalate (xsm_deadlines)                     ║
                  ╚══ REJECT [isReviewer] (confirm + reason) ──▶ rejected ═══╝
```

| File | What it is |
|:--|:--|
| `machine.json` | The chart. It passes `xsm validate --plain`. |
| `approvals/models.py` | `Expense(StatechartModelMixin)`. Two roles as `RoleGuard`s (the `legal` and `finance` groups), `AnyOf` for REJECT, and the `escalate` action. |
| `approvals/admin.py` | `StatechartAdminMixin`. Transition buttons are CSRF-protected POST forms, computed for the logged-in user. REJECT asks for a reason. The audit history is inline. |
| `approvals/api.py` | `StatechartViewSetMixin`: one `@action` per event (`/api/expenses/{id}/legal-approve/`), with the drf-spectacular schema at `/api/schema/`. |
| `approvals/ws.py`, `config/asgi.py` | `StatechartConsumer` at `/ws/expenses/<id>/`, behind `AuthMiddlewareStack` and the origin validator. |
| `approvals/templates/approvals/status.html` | A status page that shows the live state over the WebSocket. |
| `tests/` | pytest with pytest-django. It covers both roles, the admin, DRF + schema, Channels and the escalation. |

## Run it

```bash
pip install "xstate-statemachine[django,drf,channels]" drf-spectacular daphne pytest-django
cd examples/integrations/django_approvals
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver                         # daphne: HTTP + WebSocket
python manage.py xsm_deadlines --forever           # in another shell: fires the 48 h escalation
python manage.py xsm_inspect approvals.Expense     # the chart, same output as `xsm inspect`
python -m pytest tests -q
```

In the admin, create the groups `legal` and `finance` and put a user in
each. Open an expense as either user: you only see the buttons your role
can press. A request that forges another event is refused on POST. Watch
`/expenses/<id>/` in a second tab while you approve.

## What it shows

- **Parallel regions**: the expense is approved only when both regions
  reach their final state (`onDone`).
- **Permissions in the chart**: `RoleGuard` / `AnyOf`, enforced the same
  way by `send()`, the admin buttons, the API (403) and the WebSocket.
- **Audit in the same transaction**: every attempt is recorded in
  `TransitionLog`, refused ones included, with the actor and the reason.
- **Durable timers**: the 48 h `after` is a row in the deadlines table;
  `xsm_deadlines` fires it even if nobody touches the expense.
- **Integration event**: `approved` is tagged `publish`. Attach an
  `OutboxPlugin(DjangoOutboxStore())` through `statechart_plugins` to emit
  it transactionally (#293).
