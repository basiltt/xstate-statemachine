"""Verification for #268 (B1 `[testing]` pytest plugin).

    python scripts/verify/268_testing_plugin.py

Runs against the installed package (``pip install -e ".[testing]"``).
Exercises, in a throw-away directory: plugin discovery through the
`pytest11` entry point, ``--xsm-version``, every ``xsm_*`` fixture and both
markers on the sync engine (and the async one when pytest-asyncio is
present), the corpus machine from the issue, snapshot record → verify →
mismatch-diff, ``-p no:xstate_statemachine``, the ``MissingExtraError``
contract, the ``--fixtures`` codegen companion, then the plugin's own test
folder. Plain Python; Windows-safe (``tempfile``, no shell heredocs).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"

DEMO = """
import pytest

CHECKOUT = {
    "id": "checkout", "initial": "cart", "context": {"items": 0},
    "states": {
        "cart": {"on": {"PAY": {"target": "paying", "guard": "hasItems",
                                 "actions": "charge"}}},
        "paying": {"after": {"3000": "confirmed"}},
        "confirmed": {"type": "final"},
    },
}


@pytest.mark.xstate_machine(CHECKOUT)
def test_sync(xsm_machine, xsm_interp, xsm_clock, xsm_ran, xsm_store,
              xsm_send_all):
    from xstate_statemachine.persistence import MemoryStore, persisted
    assert xsm_machine.id == "checkout"
    assert isinstance(xsm_store, MemoryStore)
    xsm_send_all(xsm_interp, "PAY", "+3000")
    assert xsm_interp.matches("checkout.confirmed")
    assert xsm_ran == ["charge"]
    assert xsm_clock.now() * 1000 == pytest.approx(3000)
    with persisted(xsm_store, "k", xsm_machine) as m:
        m.send("PAY")
    assert xsm_store.load("k").version == 1


@pytest.mark.xstate_machine(CHECKOUT)
@pytest.mark.xstate_guards_false("hasItems")
def test_guards(xsm_interp, xsm_guards):
    assert xsm_interp.send("PAY", wait=True).denied
    xsm_guards["hasItems"] = True
    xsm_interp.send("PAY")
    assert xsm_interp.matches("checkout.paying")


@pytest.mark.xstate_machine(%(corpus)r)
def test_corpus(xsm_interp, xsm_send_all, xsm_ran):
    # The issue's script: SUBMIT -> challenge, +2001 ms -> success. The
    # chart declares no actions on that path, so xsm_ran stays empty.
    xsm_send_all(xsm_interp, "SUBMIT", "+2001")
    assert xsm_interp.matches("Advance payment flow.success")
    assert xsm_ran == []


@pytest.mark.xstate_machine(CHECKOUT)
def test_snapshot(xsm_interp, xsm_snapshot):
    xsm_interp.send("PAY")
    xsm_snapshot(xsm_interp, "snapshots/paying.json")


@pytest.mark.asyncio
@pytest.mark.xstate_machine(CHECKOUT)
async def test_async(xsm_ainterp, xsm_asend_all, xsm_ran):
    await xsm_asend_all(xsm_ainterp, "PAY", "+3000")
    assert xsm_ainterp.matches("checkout.confirmed")
    assert xsm_ran == ["charge"]


def test_unmarked_test_is_untouched():
    assert True
"""


def step(name: str) -> None:
    print(f"\n== {name}")


def pytest_run(cwd: Path, *args: str, expect: int = 0) -> str:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            f"--rootdir={cwd}",
            *args,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        env=env,
        timeout=600,
    )
    out = proc.stdout + proc.stderr
    if proc.returncode != expect:
        print(out[-4000:])
        raise SystemExit(
            f"pytest exited {proc.returncode}, expected {expect} ({args})"
        )
    return out


def main() -> int:
    step("0. entry point + import contract")
    from importlib.metadata import entry_points

    eps = entry_points()
    group = (
        eps.select(group="pytest11")
        if hasattr(eps, "select")
        else eps.get("pytest11", [])
    )
    assert any(
        e.value == "xstate_statemachine.contrib.testing.pytest_plugin"
        for e in group
    ), "pytest11 entry point not registered -- pip install -e .[testing]"
    from xstate_statemachine.contrib.testing import (
        PLUGIN_NAME,
        normalize_snapshot,
        render_snapshot,
    )

    assert PLUGIN_NAME == "xstate_statemachine"
    assert render_snapshot(normalize_snapshot('{"state_ids": ["a"]}')) == (
        '{\n  "state_ids": [\n    "a"\n  ]\n}\n'
    )
    print("   OK  entry point registered; helpers importable")

    has_asyncio = (
        subprocess.run(
            [sys.executable, "-c", "import pytest_asyncio"],
            capture_output=True,
        ).returncode
        == 0
    )
    print("   pytest-asyncio installed:", has_asyncio)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = Path(tmp)
        (cwd / "pytest.ini").write_text(
            "[pytest]\nasyncio_mode = strict\n"
            "asyncio_default_fixture_loop_scope = function\n",
            encoding="utf-8",
        )
        demo = DEMO % {"corpus": (CORPUS / "AdvancePayment.json").as_posix()}
        (cwd / "test_demo.py").write_text(demo, encoding="utf-8")

        step("1. --xsm-version")
        out = pytest_run(cwd, "--xsm-version")
        assert out.strip().startswith("xstate-statemachine "), out
        print("   OK ", out.strip())

        step("2. record snapshots, then verify (sync + corpus + async)")
        out = pytest_run(cwd, "--xsm-update-snapshots", "-rs")
        print("   record:", out.strip().splitlines()[-1])
        snap = cwd / "snapshots" / "paying.json"
        first = snap.read_text(encoding="utf-8")
        assert json.loads(first)["state_ids"] == ["checkout.paying"], first
        out = pytest_run(cwd, "-rs")
        summary = out.strip().splitlines()[-1]
        print("   verify:", summary)
        expected_passed = 6 if has_asyncio else 5
        assert f"{expected_passed} passed" in summary, summary
        if not has_asyncio:
            assert "xsm_ainterp needs pytest-asyncio" in out, out[-2000:]
            print("   async fixture skipped with the install hint (expected)")
        assert snap.read_text(encoding="utf-8") == first, "snapshot churned"
        print("   OK  snapshot file byte-identical across runs")

        step("3. snapshot mismatch shows a unified diff, does not rewrite")
        tampered = first.replace("checkout.paying", "checkout.cart")
        snap.write_text(tampered, encoding="utf-8")
        out = pytest_run(cwd, "test_demo.py::test_snapshot", expect=1)
        assert (
            "SnapshotMismatchError" in out
            and "+++ " in out
            and ('-    "checkout.cart"' in out)
        ), out[-3000:]
        assert snap.read_text(encoding="utf-8") == tampered
        print("   OK  diff shown, file untouched")

        step("4. -p no:xstate_statemachine removes the plugin")
        out = pytest_run(
            cwd, "-p", "no:xstate_statemachine", "--xsm-version", expect=4
        )
        assert "unrecognized arguments: --xsm-version" in out, out[-1000:]
        print("   OK  option gone with the plugin")

        step("5. xsm gt -t pytest --fixtures generates a green module")
        gen = cwd / "gen"
        gen.mkdir()
        src = gen / "kettle.json"
        src.write_text(
            (CORPUS / "kettle.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "xstate_statemachine",
                "gt",
                str(src),
                "-t",
                "pytest",
                "--fixtures",
                "-o",
                str(gen),
                "-f",
                "--plain",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            timeout=300,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        [generated] = gen.glob("test_*.py")
        text = generated.read_text(encoding="utf-8")
        assert "pytest.mark.xstate_machine" in text and "xsm_interp" in text
        assert "def stub_logic(" not in text
        out = pytest_run(cwd, str(gen))
        print("   generated:", out.strip().splitlines()[-1])

    step("6. MissingExtraError contract when pytest is absent")
    child = (
        "import importlib.abc, sys\n"
        "class B(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, n, p=None, t=None):\n"
        "        if n.split('.')[0] == 'pytest':\n"
        "            raise ImportError('blocked')\n"
        "sys.meta_path.insert(0, B())\n"
        "try:\n"
        "    import xstate_statemachine.contrib.testing\n"
        "except ImportError as e:\n"
        "    from xstate_statemachine import MissingExtraError\n"
        "    assert isinstance(e, MissingExtraError), type(e)\n"
        "    assert 'xstate-statemachine[testing]' in str(e), e\n"
        "    print('   OK ', e)\n"
        "else:\n"
        "    raise SystemExit('imported without pytest?!')\n"
    )
    subprocess.run([sys.executable, "-I", "-c", child], check=True)

    step("7. plugin test folder + import-surface guard")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/contrib/testing",
            "tests/contrib/test_extras_matrix.py",
            "tests/test_import_surface.py",
            "-q",
            "-p",
            "no:cacheprovider",
        ],
        cwd=ROOT,
        check=True,
    )
    print("\nALL OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
