# tests/recipes/test_recipe_pack.py
"""#308: every recipe has a page, a Stately-importable chart, a working
`xsm simulate --events` line, and a test -- and the pack is in the nav."""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from typing import Any, Dict

import pytest

from .conftest import PAGES, RECIPES, ROOT

#: page slug -> example folder (None: a page without a chart)
RECIPE_PAGES: Dict[str, Any] = {
    "stripe-webhooks": "stripe_webhooks",
    "apscheduler-timers": "apscheduler_timers",
    "task-queue-workers": "task_queue_workers",
    "form-wizard": "form_wizard",
    "slot-filling": "slot_filling",
    "feature-flag-rollout": "feature_flag_rollout",
    "websocket-reconnect": "websocket_reconnect",
    "circuit-breaker-retry": "circuit_breaker_retry",
}
SIMULATE = re.compile(r"^xsm simulate (\S+)((?: [^\n#]+?)?)\n# -> (\S+)", re.M)
WITH_CHART = sorted(RECIPE_PAGES.items())


def _page(slug: str) -> str:
    return (PAGES / f"{slug}.md").read_text("utf-8")


def test_index_lists_every_recipe_and_the_comparison() -> None:
    index = (PAGES / "recipes.md").read_text("utf-8")
    assert "permalink: /guide/recipes/" in index
    for slug in [*RECIPE_PAGES, "vs-step-functions"]:
        assert f"](../{slug}/)" in index, slug


@pytest.mark.parametrize("slug,folder", WITH_CHART)
def test_recipe_has_page_example_chart_and_test(
    slug: str, folder: str
) -> None:
    text = _page(slug)
    assert f"permalink: /guide/{slug}/" in text
    assert f"examples/recipes/{folder}/" in text
    assert (RECIPES / folder / "machine.json").is_file()
    assert (ROOT / "tests" / "recipes" / f"test_{folder}.py").is_file()


@pytest.mark.parametrize("slug,folder", WITH_CHART)
def test_chart_is_stately_json_and_builds_strict(
    slug: str, folder: str
) -> None:
    from xstate_statemachine import create_machine, stub_logic

    cfg = json.loads((RECIPES / folder / "machine.json").read_text("utf-8"))
    assert cfg["id"] and cfg["initial"] in cfg["states"]
    json.dumps(cfg)  # plain JSON: Stately imports it as-is
    m = create_machine(cfg, logic=stub_logic(cfg), strict_config=True)
    assert m.id == cfg["id"]


@pytest.mark.parametrize("slug,folder", WITH_CHART)
def test_chart_passes_xsm_validate(slug: str, folder: str) -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "xstate_statemachine", "validate",
         str(RECIPES / folder / "machine.json"), "--plain"],
        capture_output=True, text=True, encoding="utf-8", timeout=120,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
    )  # fmt: skip
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("slug,folder", WITH_CHART)
def test_the_simulate_line_reproduces_the_flow(slug: str, folder: str) -> None:
    lines = SIMULATE.findall(_page(slug))
    assert lines, f"{slug}: no `xsm simulate ... / # -> state` block"
    for path, args, expected in lines:
        assert path == f"examples/recipes/{folder}/machine.json"
        proc = subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", "simulate",
             str(ROOT / path), *shlex.split(args), "--json"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(ROOT), timeout=120,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        )  # fmt: skip
        assert proc.returncode == 0, proc.stderr
        active = json.loads(proc.stdout)["active"]
        assert expected in active, f"{slug}: {args!r} -> {active}"


@pytest.mark.parametrize(
    "slug", ["stripe-webhooks", "apscheduler-timers", "task-queue-workers"]
)
def test_persistent_recipes_carry_a_guarantees_box(slug: str) -> None:
    text = _page(slug)
    assert "## Guarantees" in text
    assert "**What this does:**" in text
    assert "**What this does not do:**" in text


def test_stripe_guarantees_cite_x0_2_and_x0_7() -> None:
    text = _page("stripe-webhooks")
    box = text.split("## Guarantees", 1)[1].split("\n## ", 1)[0]
    assert "X0.2" in box and "X0.7" in box
