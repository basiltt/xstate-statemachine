# examples/integrations/django_approvals/approvals/views.py
"""A tiny status page that opens the WebSocket (no framework JS)."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Expense


@login_required
def status(request, pk: int):
    expense = get_object_or_404(Expense, pk=pk)
    return render(request, "approvals/status.html", {"expense": expense})
