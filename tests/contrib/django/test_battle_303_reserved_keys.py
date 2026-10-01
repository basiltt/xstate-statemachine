# tests/contrib/django/test_battle_303_reserved_keys.py
"""Battle #303 (X0.7): Django's ``RESERVED_PAYLOAD_KEYS`` must cover every
keyword-only option of the engine's ``send()`` so a client body can never
set one. Lives here (not in the root battle file) so the Django project
is configured by this folder's conftest, not mid-session.
"""

from __future__ import annotations

import inspect


def test_reserved_payload_keys_cover_every_send_option() -> None:
    from xstate_statemachine.base_interpreter import BaseInterpreter
    from xstate_statemachine.contrib.django.mixin import RESERVED_PAYLOAD_KEYS
    from xstate_statemachine.interpreter import Interpreter
    from xstate_statemachine.sync_interpreter import SyncInterpreter

    assert set(BaseInterpreter._RESERVED_SEND_KWARGS) <= RESERVED_PAYLOAD_KEYS
    kwonly = set()
    for cls in (Interpreter, SyncInterpreter):
        kwonly |= {
            n
            for n, p in inspect.signature(cls.send).parameters.items()
            if p.kind is inspect.Parameter.KEYWORD_ONLY
        }
    # 🔐 A future `send(..., new_option=)` must land here too, or a JSON
    #    body could smuggle it (the Starlette/Flask lists are checked the
    #    same way in tests/test_battle_303_x0_integrations.py).
    assert kwonly <= RESERVED_PAYLOAD_KEYS, kwonly - RESERVED_PAYLOAD_KEYS
