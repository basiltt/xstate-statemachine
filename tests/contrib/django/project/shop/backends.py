# tests/contrib/django/project/shop/backends.py
"""A fake object-level permission backend for the #281 tests."""

from __future__ import annotations

from typing import Any, Dict, Tuple

#: (user pk, row pk) -> granted
GRANTS: Dict[Tuple[Any, Any], bool] = {}


class OwnRowBackend:
    """Grants ``shop.approve_approval`` on specific rows only."""

    def authenticate(self, request: Any, **kw: Any) -> None:
        return None

    def has_perm(self, user: Any, perm: str, obj: Any = None) -> bool:
        if obj is None or perm != "shop.approve_approval":
            return False
        return GRANTS.get((user.pk, obj.pk), False)
