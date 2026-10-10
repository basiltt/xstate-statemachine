# tests/test_battle_296_review.py
"""#296 independent review -- regressions.

* **R3** `allow="name"` (a bare string) is refused, never iterated letter
  by letter; `allow=[]` loads nothing;
* **R4** `xsm plugins` without `--strict` does not blame `--strict`;
* **R5** a failure before loading clears the previous `last_failed`;
* **R6** `attach_discovered` skips a discovered plugin whose class is
  already attached (documented);
* **R-HIGH** the changelog bullet does not trip the prose to-do check
  (covered by the scenario test itself; kept here as the anchor).
"""

from __future__ import annotations

import pathlib

import pytest

from xstate_statemachine import SyncInterpreter, create_machine
from xstate_statemachine import plugin_discovery as pd
from xstate_statemachine.plugins import PluginBase

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_r3_bare_string_allow_is_refused() -> None:
    with pytest.raises(TypeError, match="bare string"):
        pd.discover(allow="acme-audit")
    assert pd.discover(allow=[]) == []


def test_r5_last_failed_cleared_before_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pd.last_failed.update(name="stale", dist="old")

    def boom(group: str) -> list:
        raise RuntimeError("corrupt metadata")

    monkeypatch.setattr(pd, "_entry_points", boom)
    with pytest.raises(RuntimeError):
        pd.discover()
    assert pd.last_failed == {}


def test_r4_cli_without_strict_surfaces_a_real_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from xstate_statemachine.cli.commands import plugins as cli

    def boom(group: str) -> list:
        raise RuntimeError("corrupt metadata")

    monkeypatch.setattr(pd, "_entry_points", boom)
    with pytest.raises(RuntimeError, match="corrupt metadata"):
        cli.run_plugins(as_json=False, strict=False)
    assert cli.run_plugins(as_json=False, strict=True) == 1


def test_r6_discovered_class_already_attached_is_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Audit(PluginBase):
        def __init__(self, tag: str = "default") -> None:
            self.tag = tag

    monkeypatch.setattr(
        pd,
        "discover",
        lambda **kw: [
            pd.DiscoveredPlugin(
                "audit", "acme", "1.0", Audit, (), pd.PLUGINS_GROUP
            )
        ],
    )
    m = create_machine({"id": "m", "initial": "a", "states": {"a": {}}})
    i = SyncInterpreter(m)
    mine = Audit(tag="configured")
    i.use(mine)
    assert pd.attach_discovered(i) == []  # my configured one is kept
    plugins = [getattr(p, "wrapped", p) for p in i._plugins]
    assert [p.tag for p in plugins if isinstance(p, Audit)] == ["configured"]
    j = SyncInterpreter(m)
    assert len(pd.attach_discovered(j)) == 1
    assert pd.attach_discovered(j) == []  # second run: no-op
    text = (ROOT / "docs/_guide/plugins.md").read_text("utf-8")
    assert "already attached" in text and "allow=[]" in text
