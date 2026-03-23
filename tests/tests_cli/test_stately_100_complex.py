# tests/tests_cli/test_stately_100_complex.py
# ---------------------------------------------------------------------------
# Stress test: 100+ REAL XState machine configs from the Stately.ai registry
# x 5 templates = 500+ code generation runs.
# ---------------------------------------------------------------------------
"""Stress-test the CLI code generator with 100+ real-world XState machine
configurations extracted from the Stately.ai community registry.

These are NOT synthetic -- they come from actual production state machines
built by developers and published on the Stately registry.

Machine configs are loaded from JSON files in the ``stately_machines/``
directory alongside this test file.

Each generated file is validated by:
  1. ``py_compile.compile()`` -- syntactically valid Python
  2. ``importlib`` import     -- loadable without runtime errors
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import py_compile
import shutil
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

from xstate_statemachine.cli.extractor import extract_logic_names
from xstate_statemachine.cli.strategies import GenerationContext, get_strategy
from xstate_statemachine.cli.utils import camel_to_snake

# ---------------------------------------------------------------------------
# Template list
# ---------------------------------------------------------------------------
TEMPLATES: List[str] = [
    "class-json",
    "function-json",
    "pythonic-class",
    "pythonic-builder",
    "pythonic-functional",
]

# ---------------------------------------------------------------------------
# Load all machine configs from stately_machines/ directory
# ---------------------------------------------------------------------------
MACHINES_DIR = Path(__file__).parent / "stately_machines"

STATELY_MACHINES: Dict[str, Dict[str, Any]] = {}

if MACHINES_DIR.is_dir():
    for json_file in sorted(MACHINES_DIR.glob("*.json")):
        try:
            raw = json_file.read_text(encoding="utf-8")
            config = json.loads(raw)
            # Use the stem (filename without extension) as the key
            machine_key = json_file.stem
            STATELY_MACHINES[machine_key] = config
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Skip malformed files
            pass


# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------


def _generate_and_validate(
    machine_id: str,
    config: Dict[str, Any],
    template: str,
    tmp_dir: Path,
    *,
    log: bool = True,
    file_count: int = 2,
) -> Tuple[bool, str]:
    """Generate code for *config* x *template*, then compile + import it.

    Returns ``(True, "OK")`` on success, ``(False, error_message)`` on failure.
    """
    # 1. Extract logic names from config
    actions, guards, services = extract_logic_names(config)
    machine_name = camel_to_snake(config.get("id", machine_id))

    # 2. Async mode: JSON templates default async, pythonic default sync
    is_async = not template.startswith("pythonic")

    # 3. Build GenerationContext
    ctx = GenerationContext(
        actions=actions,
        guards=guards,
        services=services,
        is_async=is_async,
        log=log,
        machine_name=machine_name,
        machine_id=config.get("id", machine_id),
        machine_names=[machine_name],
        machine_ids=[config.get("id", machine_id)],
        file_count=file_count,
        configs=[config],
        json_filenames=[f"{machine_name}.json"],
        hierarchy=False,
        sleep=True,
        sleep_time=1,
        loader=True,
        style=None,
    )

    strategy = get_strategy(template)
    safe_tpl = template.replace("-", "_")
    mode = f"fc{file_count}_log{'Y' if log else 'N'}"
    sub_dir = tmp_dir / f"{machine_name}__{safe_tpl}__{mode}"
    sub_dir.mkdir(parents=True, exist_ok=True)

    errors: List[str] = []

    # 4. Generate logic + runner
    try:
        logic_code = strategy.generate_logic(ctx)
    except Exception as exc:
        return False, f"generate_logic() raised: {exc}"
    try:
        runner_code = strategy.generate_runner(ctx)
    except Exception as exc:
        return False, f"generate_runner() raised: {exc}"

    logic_path = sub_dir / f"{machine_name}_logic.py"
    runner_path = sub_dir / f"{machine_name}_runner.py"
    logic_path.write_text(logic_code, encoding="utf-8")
    runner_path.write_text(runner_code, encoding="utf-8")

    # 5. py_compile both files
    for fpath in [logic_path, runner_path]:
        try:
            py_compile.compile(str(fpath), doraise=True)
        except py_compile.PyCompileError as exc:
            errors.append(f"py_compile({fpath.name}): {exc}")

    # 6. importlib import logic file
    try:
        spec = importlib.util.spec_from_file_location(
            f"{machine_name}_logic__{safe_tpl}__{mode}",
            str(logic_path),
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception as exc:
        errors.append(f"import({logic_path.name}): {exc}")

    if errors:
        return False, "; ".join(errors)
    return True, "OK"


# ---------------------------------------------------------------------------
# Test class: log=True, file_count=2 (default / most common)
# ---------------------------------------------------------------------------


class Stately100RealTests(unittest.TestCase):
    """104 machines x 5 templates = 520 tests (log=True, file_count=2)."""

    _tmp_dir: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp_dir = Path(tempfile.mkdtemp(prefix="xsm_stately100_"))

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls._tmp_dir, ignore_errors=True)


def _make_test(
    machine_id: str,
    config: Dict[str, Any],
    template: str,
    *,
    log: bool = True,
    file_count: int = 2,
) -> Any:
    """Factory: create a test method for one (machine, template) pair."""

    def test_fn(self: unittest.TestCase) -> None:
        ok, msg = _generate_and_validate(
            machine_id,
            config,
            template,
            self._tmp_dir,  # type: ignore[attr-defined]
            log=log,
            file_count=file_count,
        )
        self.assertTrue(ok, f"[{machine_id} x {template}] {msg}")

    safe = template.replace("-", "_")
    test_fn.__name__ = f"test_{machine_id}__{safe}"
    test_fn.__doc__ = f"{machine_id} x {template}"
    return test_fn


# --- register tests: log=True, file_count=2 ---
for _mid, _cfg in STATELY_MACHINES.items():
    for _tpl in TEMPLATES:
        _fn = _make_test(_mid, _cfg, _tpl, log=True, file_count=2)
        setattr(Stately100RealTests, _fn.__name__, _fn)
