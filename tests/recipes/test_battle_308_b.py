# tests/recipes/test_battle_308_b.py
"""#308 battle, adversary B: the recipe pages tell the truth.

* every ```python block runs VERBATIM from a bare temp dir that holds only
  a copy of the recipe folder (the copy-paste path), with PYTHONPATH=src;
* every fragment at least compiles;
* every ``<!-- test: path::name -->`` anchor names a test that exists;
* every Troubleshooting row quotes an error the code really produces;
* the charts use only XState keys (Stately imports them unchanged);
* the vs-Step-Functions side-by-side is valid ASL and valid XState.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from .conftest import PAGES, RECIPES, ROOT, load_recipe

SLUGS: Dict[str, str] = {
    "stripe-webhooks": "stripe_webhooks",
    "apscheduler-timers": "apscheduler_timers",
    "task-queue-workers": "task_queue_workers",
    "form-wizard": "form_wizard",
    "slot-filling": "slot_filling",
    "feature-flag-rollout": "feature_flag_rollout",
    "websocket-reconnect": "websocket_reconnect",
    "circuit-breaker-retry": "circuit_breaker_retry",
}
VS_SFN = ROOT / "docs" / "_guide" / "comparisons" / "vs-step-functions.md"
FENCE = re.compile(r"```python\n(.*?)```", re.S)
REQUIRES = re.compile(r"<!--\s*doc-requires:\s*([\w.,\s]+?)\s*-->\s*$")
ANCHOR = re.compile(r"<!-- test: (\S+?)::(\w+) -->")


def _page(slug: str) -> str:
    return (PAGES / f"{slug}.md").read_text("utf-8")


def _blocks() -> List[Tuple[str, int, str, bool, List[str]]]:
    out = []
    for slug in SLUGS:
        text = _page(slug)
        for m in FENCE.finditer(text):
            before = text[: m.start()].rstrip()
            req = REQUIRES.search(before)
            needs = [r.strip() for r in req.group(1).split(",")] if req else []
            line = text[: m.start()].count("\n") + 1
            frag = before.endswith("<!-- doc-fragment -->")
            out.append((slug, line, m.group(1), frag, needs))
    return out


BLOCKS = _blocks()
RUNNABLE = [b for b in BLOCKS if not b[3]]
FRAGMENTS = [b for b in BLOCKS if b[3]]


def _id(b: Tuple[Any, ...]) -> str:
    return f"{b[0]}:{b[1]}"


def test_block_discovery_is_not_empty() -> None:
    assert len(RUNNABLE) >= 9 and len(FRAGMENTS) >= 4


# -----------------------------------------------------------------------------
# 1. the copy-paste path
# -----------------------------------------------------------------------------
@pytest.mark.parametrize("block", RUNNABLE, ids=_id)
def test_block_runs_from_a_copied_recipe_folder(
    block: Tuple[Any, ...], tmp_path: Path
) -> None:
    slug, line, src, _, needs = block
    missing = [n for n in needs if importlib.util.find_spec(n) is None]
    if missing:
        pip = " ".join(missing)
        pytest.skip(f"soft dependency missing: pip install {pip}")
    folder = tmp_path / SLUGS[slug]
    shutil.copytree(RECIPES / SLUGS[slug], folder)
    (folder / "block.py").write_text(src, "utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update(PYTHONPATH=str(ROOT / "src"), PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, "-X", "utf8", "block.py"], cwd=str(folder),
        capture_output=True, text=True, encoding="utf-8", env=env,
        timeout=120,
    )  # fmt: skip
    assert proc.returncode == 0, f"{slug}:{line}\n{proc.stderr[-2000:]}"


@pytest.mark.parametrize("block", FRAGMENTS, ids=_id)
def test_fragment_compiles(block: Tuple[Any, ...]) -> None:
    """A fragment need not run, but it must be Python (a broken nested
    fence once ended a block mid-f-string)."""
    compile(
        block[2], _id(block), "exec", flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT
    )


# -----------------------------------------------------------------------------
# 2. the simulate line replays without a denied/erroring step
# -----------------------------------------------------------------------------
SIMULATE = re.compile(r"^xsm simulate (\S+)((?: [^\n#]+?)?)\n# -> (\S+)", re.M)


@pytest.mark.parametrize("slug", sorted(SLUGS))
def test_simulate_line_has_no_failing_step(slug: str) -> None:
    import shlex

    for path, args, expected in SIMULATE.findall(_page(slug)):
        proc = subprocess.run(
            [sys.executable, "-m", "xstate_statemachine", "simulate",
             str(ROOT / path), *shlex.split(args), "--json"],
            capture_output=True, text=True, encoding="utf-8",
            cwd=str(ROOT), timeout=120,
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        )  # fmt: skip
        out = json.loads(proc.stdout)
        assert out["active"][-1] == expected or expected in out["active"]
        bad = [h for h in out["history"] if h["error"] or h["denied"]]
        assert bad == [], f"{slug}: {args!r} has a failing step {bad}"


# -----------------------------------------------------------------------------
# 3. every claim anchor names a real test; boxes and troubleshooting exist
# -----------------------------------------------------------------------------
ANCHORS = sorted(
    {(slug, f, n) for slug in SLUGS for f, n in ANCHOR.findall(_page(slug))}
)


def test_anchor_discovery_is_not_empty() -> None:
    assert len(ANCHORS) >= 25
    persistent = ("stripe-webhooks", "apscheduler-timers",
                  "task-queue-workers")  # fmt: skip
    for slug in persistent:
        assert any(a[0] == slug for a in ANCHORS), slug


@pytest.mark.parametrize("anchor", ANCHORS, ids=lambda a: f"{a[0]}:{a[2]}")
def test_anchored_test_exists(anchor: Tuple[str, str, str]) -> None:
    slug, path, name = anchor
    src = (ROOT / path).read_text("utf-8")
    assert re.search(rf"^\s*(async )?def {name}\(", src, re.M), (
        f"{slug} cites {path}::{name}, which no longer exists"
    )


@pytest.mark.parametrize("slug", sorted(SLUGS))
def test_every_recipe_has_troubleshooting(slug: str) -> None:
    text = _page(slug)
    assert "## Troubleshooting" in text
    table = text.split("## Troubleshooting", 1)[1].split("\n## ", 1)[0]
    assert table.count("\n| ") >= 3, slug


@pytest.mark.parametrize(
    "slug",
    ["stripe-webhooks", "apscheduler-timers", "task-queue-workers",
     "websocket-reconnect"],
)  # fmt: skip
def test_persistence_or_concurrency_recipes_say_what_they_do_not_do(
    slug: str,
) -> None:
    text = _page(slug)
    assert "does not do" in text, slug


def test_stripe_box_matches_the_409_behaviour() -> None:
    box = _page("stripe-webhooks").split("## Guarantees", 1)[1]
    box = box.split("\n## ", 1)[0]
    assert "409/500" not in box  # the old, untrue "or 500"
    assert '409 {"error": "conflict", "detail": "retry the delivery"}' in box


# -----------------------------------------------------------------------------
# 4. troubleshooting rows quote the code
# -----------------------------------------------------------------------------
def test_stripe_every_emitted_detail_is_documented_and_vice_versa() -> None:
    src = (RECIPES / "stripe_webhooks" / "stripe_webhooks.py").read_text(
        "utf-8"
    )
    emitted = set(re.findall(r'SignatureError\("([^"]+)"\)', src))
    emitted |= set(re.findall(r'"detail": "([^"]+)"', src))
    page = _page("stripe-webhooks").split("## Troubleshooting", 1)[1]
    page = page.split("\n## ", 1)[0]
    documented = set(re.findall(r'"detail": "([^"]+)"', page))
    documented |= set(re.findall(r'`"([^"`]+)"`', page))
    assert emitted - documented == set(), "undocumented error details"
    assert documented - emitted == set(), "documented details nobody emits"


@pytest.fixture
def stripe_env(tmp_path: Path) -> Any:
    sw = load_recipe("stripe_webhooks", "stripe_webhooks")
    from xstate_statemachine.persistence import MemoryInbox, SQLiteStore

    store = SQLiteStore(str(tmp_path / "s.db"))
    yield sw, store, MemoryInbox()
    store.close()


def test_stripe_conflict_is_409_with_a_fixed_body(
    stripe_env: Any, monkeypatch: Any
) -> None:
    sw, store, inbox = stripe_env
    from xstate_statemachine.exceptions import ConflictError

    body = json.dumps(
        {"id": "evt_1", "type": "invoice.paid",
         "data": {"object": {"id": "in_1", "subscription": "sub_1"}}}
    ).encode()  # fmt: skip

    def racing_persisted(*a: Any, **k: Any) -> Any:
        raise ConflictError("subscription.sub_1", 1, 2)

    monkeypatch.setattr(sw, "persisted", racing_persisted)
    status, payload = sw.handle_webhook(
        body, sw.sign(body, "whsec_x", 1_000), secret="whsec_x",
        store=store, inbox=inbox, machine=sw.build_machine(), now=1_000,
    )  # fmt: skip
    assert (status, payload) == (
        409,
        {"error": "conflict", "detail": "retry the delivery"},
    )


def test_stripe_error_bodies_never_echo_input(stripe_env: Any) -> None:
    sw, store, inbox = stripe_env
    marker = "<script>SECRET-INPUT</script>"
    for body in (marker.encode(), json.dumps([marker]).encode()):
        status, payload = sw.handle_webhook(
            body, sw.sign(body, "whsec_x", 1_000), secret="whsec_x",
            store=store, inbox=inbox, machine=sw.build_machine(), now=1_000,
        )  # fmt: skip
        assert status == 400 and marker not in json.dumps(payload)


def test_stripe_missing_secret_is_the_documented_keyerror(
    monkeypatch: Any,
) -> None:
    pytest.importorskip("flask")
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    app = load_recipe("stripe_webhooks", "app_flask")
    with pytest.raises(KeyError, match="STRIPE_WEBHOOK_SECRET"):
        app.create_app()
    assert "`KeyError: 'STRIPE_WEBHOOK_SECRET'`" in _page("stripe-webhooks")


def test_task_queue_rows_quote_real_errors(tmp_path: Path) -> None:
    from xstate_statemachine.exceptions import ConflictError

    qw = load_recipe("task_queue_workers", "queue_workers")
    page = _page("task-queue-workers")
    msg = str(ConflictError("shipment.42", 3, 4))
    assert f"`ConflictError: {msg}`" in page
    assert f"({qw.RETRIES} in `queue_workers.py`)" in page
    saved = qw.STORE, qw.MACHINE
    try:
        qw.STORE = None
        with pytest.raises(AttributeError) as exc:
            qw.apply_event("shipment.1", "LABEL_PRINTED")
        assert f"`AttributeError: {exc.value}`" in page
    finally:
        qw.STORE, qw.MACHINE = saved


def test_slot_filling_row_matches_max_slot_chars() -> None:
    sf = load_recipe("slot_filling", "slot_filling")
    page = _page("slot-filling")
    assert f"`MAX_SLOT_CHARS` ({sf.MAX_SLOT_CHARS})" in page
    ok = "x" * sf.MAX_SLOT_CHARS
    assert sf.valid_slot_value(ok) and sf.valid_slot_value(4)
    for bad in (ok + "x", {"a": 1}, ["a"], True, None, "", "  "):
        assert not sf.valid_slot_value(bad), bad


def test_rollout_metrics_that_raise_roll_back() -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter

    ro = load_recipe("feature_flag_rollout", "rollout")

    def down() -> Dict[str, float]:
        raise RuntimeError("prometheus down")

    clock = SimulatedClock()
    logging.disable(logging.CRITICAL)
    try:
        i = SyncInterpreter(ro.build_machine(down), clock=clock).start()
        i.send("START")
        clock.increment(3_600_000)
        assert i.value == "rolled_back" and i.context["percent"] == 0
        i.stop()
    finally:
        logging.disable(logging.NOTSET)


def test_rollout_apply_percent_that_raises_is_not_retried() -> None:
    from xstate_statemachine import SimulatedClock, SyncInterpreter

    ro = load_recipe("feature_flag_rollout", "rollout")
    pushed: List[float] = []

    def flaky(flag: str, pct: float) -> None:
        pushed.append(pct)
        if pct == 1:
            raise RuntimeError("flag api down")

    clock = SimulatedClock()
    logging.disable(logging.CRITICAL)
    try:
        m = ro.build_machine(lambda: {"error_rate": 0.0, "p99_ms": 1.0}, flaky)
        i = SyncInterpreter(m, clock=clock).start()
        i.send("START")
        clock.increment(3_600_000)  # -> canary_1, apply_percent raises
        assert i.context["percent"] == 1  # the chart moved on anyway
        clock.increment(3_600_000)
        assert i.value == {"exposed": "canary_25"}
        assert pushed.count(1) == 1  # never retried
        i.stop()
    finally:
        logging.disable(logging.NOTSET)


def test_circuit_breaker_error_strings() -> None:
    from xstate_statemachine import SimulatedClock
    from xstate_statemachine.patterns import CircuitBreaker

    hc = load_recipe("circuit_breaker_retry", "http_client")
    page = _page("circuit-breaker-retry")
    seen = []
    for status in (404, 503):
        clock = SimulatedClock()
        breaker = CircuitBreaker(failure_threshold=99, clock=clock)
        m = hc.build_machine(lambda me, u, s=status: (s, b""), breaker)
        r = hc.fetch(m, "https://x", clock=clock)
        for _ in range(30):
            clock.increment(10_000)
        assert r.value == "failed"
        seen.append(r.context["error"])
        r.stop()
    clock = SimulatedClock()
    breaker = CircuitBreaker(failure_threshold=1, clock=clock)
    m = hc.build_machine(lambda me, u: (503, b""), breaker)
    for _ in range(2):
        r = hc.fetch(m, "https://x", clock=clock)
        for _ in range(30):
            clock.increment(10)
        r.stop()
    seen.append(r.context["error"])
    for err in seen:
        assert f"`{err}`" in page, err


def test_websocket_row_quotes_max_attempts() -> None:
    src = (RECIPES / "websocket_reconnect" / "ws_reconnect.py").read_text(
        "utf-8"
    )
    n = re.search(r"max_attempts=(\d+)", src).group(1)  # type: ignore
    assert f"({n} in `ws_reconnect.py`" in _page("websocket-reconnect")


# -----------------------------------------------------------------------------
# 5. charts: XState keys only
# -----------------------------------------------------------------------------
STATE_KEYS = {
    "id", "initial", "states", "on", "after", "always", "entry", "exit",
    "invoke", "type", "context", "description", "tags", "meta", "history",
    "output", "target", "version",
}  # fmt: skip
TRANSITION_KEYS = {
    "target", "actions", "guard", "reenter", "description", "meta",
}  # fmt: skip
ACTION_KEYS = {"type", "params"}
INVOKE_KEYS = {"id", "src", "input", "onDone", "onError", "onSnapshot"}


def _check(node: Dict[str, Any], where: str, bad: List[str]) -> None:
    bad += [f"{where}.{k}" for k in node if k not in STATE_KEYS]
    trans: List[Any] = []
    for key in ("on", "after"):
        trans += list((node.get(key) or {}).values())
    trans.append(node.get("always"))
    inv = node.get("invoke") or []
    for i in inv if isinstance(inv, list) else [inv]:
        bad += [f"{where}.invoke.{k}" for k in i if k not in INVOKE_KEYS]
        trans += [i.get("onDone"), i.get("onError")]
    acts: List[Any] = [node.get("entry"), node.get("exit")]
    for t in trans:
        for t1 in t if isinstance(t, list) else [t]:
            if isinstance(t1, dict):
                bad += [
                    f"{where}.transition.{k}"
                    for k in t1
                    if k not in TRANSITION_KEYS
                ]
                acts.append(t1.get("actions"))
    for a in acts:
        for a1 in a if isinstance(a, list) else [a]:
            if isinstance(a1, dict):
                bad += [
                    f"{where}.action.{k}" for k in a1 if k not in ACTION_KEYS
                ]
    for name, child in (node.get("states") or {}).items():
        _check(child, f"{where}.{name}", bad)


@pytest.mark.parametrize("folder", sorted(SLUGS.values()))
def test_chart_uses_only_xstate_keys(folder: str) -> None:
    cfg = json.loads((RECIPES / folder / "machine.json").read_text("utf-8"))
    bad: List[str] = []
    _check(cfg, cfg["id"], bad)
    assert bad == [], f"{folder}: Stately would drop {bad}"


# -----------------------------------------------------------------------------
# 7. vs Step Functions: both sides are valid
# -----------------------------------------------------------------------------
def _json_blocks() -> List[Dict[str, Any]]:
    text = VS_SFN.read_text("utf-8")
    found = re.findall(r"```json\n(.*?)```", text, re.S)
    return [json.loads(b) for b in found]


def test_asl_side_is_valid_asl() -> None:
    asl = next(b for b in _json_blocks() if "StartAt" in b)
    states = asl["States"]
    assert asl["StartAt"] in states
    terminal = {"Succeed", "Fail"}
    for name, st in states.items():
        assert st["Type"] in {"Task", "Pass", "Choice", "Wait", "Parallel",
                              "Map", "Succeed", "Fail"}, name  # fmt: skip
        nexts = [st.get("Next")] + [c["Next"] for c in st.get("Catch", [])]
        for n in filter(None, nexts):
            assert n in states, f"{name}: Next {n!r} names no state"
        if st["Type"] not in terminal:
            assert "Next" in st or st.get("End") is True, name
        for r in st.get("Retry", []):
            assert r["ErrorEquals"] and r["MaxAttempts"] >= 0
    reached, todo = set(), [asl["StartAt"]]
    while todo:
        n = todo.pop()
        if n in reached:
            continue
        reached.add(n)
        st = states[n]
        todo += [st.get("Next")] if st.get("Next") else []
        todo += [c["Next"] for c in st.get("Catch", [])]
    assert reached == set(states), "unreachable ASL states"


def test_xstate_side_builds_strict_and_matches_the_python_block() -> None:
    from xstate_statemachine import create_machine, stub_logic

    cfg = next(b for b in _json_blocks() if "StartAt" not in b)
    m = create_machine(cfg, logic=stub_logic(cfg), strict_config=True)
    assert m.id == "order"
    text = VS_SFN.read_text("utf-8")
    src = FENCE.search(text).group(1)  # type: ignore[union-attr]
    ns: Dict[str, Any] = {}
    exec(  # noqa: S102 -- our own doc block, to read its `chart`
        src.split("outcomes =", 1)[0], ns
    )
    assert ns["chart"]["states"] == cfg["states"]
