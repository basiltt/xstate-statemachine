# src/xstate_statemachine/contrib/__init__.py
# -----------------------------------------------------------------------------
# 🔌 contrib -- optional framework integrations, one pip extra each
# -----------------------------------------------------------------------------
# 🏛️ Architecture decision: this file imports NOTHING from its subpackages,
#    and must never start to. `import xstate_statemachine` has to stay
#    third-party-free, and every integration here has a third-party target
#    (Django, FastAPI, SQLAlchemy, ...). Each subpackage begins with
#    `require_extra("<extra>", "<module>")` from `_compat`, which turns a
#    missing dependency into a `MissingExtraError` that names the exact
#    `pip install "xstate-statemachine[<extra>]"` command instead of a bare
#    `ModuleNotFoundError` deep inside the import.
#
# 📦 Layout (programme #257; each subpackage lands with its own issue):
#    contrib/pydantic       #266     contrib/django       #280-#282
#    contrib/observability  #273     contrib/drf          #283
#    contrib/testing        #268-#272 contrib/channels    #283
#    contrib/redis          #306     contrib/sqlalchemy   #284
#    contrib/starlette      #275     contrib/flask        #285
#    contrib/fastapi        #276     contrib/celery       #292
#    contrib/litestar       #278     contrib/brokers      #293-#294
#    contrib/agents         #287-#291
#
# 🧪 `tests/test_zero_dependency.py` asserts that importing the core leaves
#    no `xstate_statemachine.contrib.*` module in `sys.modules`, and
#    `tests/contrib/test_extras_matrix.py` asserts every subpackage raises
#    `MissingExtraError` when its dependency is blocked.
# -----------------------------------------------------------------------------
"""Optional integrations. Import a subpackage directly, e.g.
``from xstate_statemachine.contrib.fastapi import StatechartRouter``.

Each subpackage requires its pip extra::

    pip install "xstate-statemachine[fastapi]"

Nothing is imported here on purpose -- see the module comment.
"""

from __future__ import annotations

__all__: list = []
