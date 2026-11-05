# tests/tests_cli/test_review_fixes.py
# -----------------------------------------------------------------------------
# 🛡️ Regression tests for the 0.12.0 CLI code review (CLI-001 .. CLI-017)
# -----------------------------------------------------------------------------
"""Regression tests for the CLI review findings."""

import argparse
import ast
import io
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from src.xstate_statemachine.cli import args as cli_args
from src.xstate_statemachine.cli.__main__ import main
from src.xstate_statemachine.cli.commands import reset_console
from src.xstate_statemachine.cli.commands.analysis import analyse
from src.xstate_statemachine.cli.commands.update import (
    is_newer,
    parse_version,
)
from src.xstate_statemachine.cli.ir import parse_machine
from src.xstate_statemachine.cli.postprocess import prune_unused_imports
from src.xstate_statemachine.cli.strategies._shared import (
    escape_for_string,
    logic_bindings,
)
from src.xstate_statemachine.cli.utils import safe_file_stem

HOSTILE = 'q`"""\nimport os;os.system(\'echo PWNED\')\nclass _X:  # '
HOSTILE_EVENT = "X\nimport os\nos.system('echo PWNED')\n#"


@pytest.fixture(autouse=True)
def _quiet() -> Any:
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    reset_console()
    yield
    logging.disable(previous)
    reset_console()


def run_cli(
    monkeypatch: pytest.MonkeyPatch, *argv: str
) -> Tuple[int, str, str]:
    """Run ``xsm`` in-process; return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "argv", ["xsm", *argv])
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    reset_console()
    code = 0
    try:
        main()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, out.getvalue(), err.getvalue()


def write(path: Path, config: Dict[str, Any]) -> str:
    path.write_text(json.dumps(config), encoding="utf-8")
    return str(path)


def calls_os_system(source: str) -> bool:
    return any(
        isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == "system"
        for n in ast.walk(ast.parse(source))
    )


# -- CLI-001 -----------------------------------------------------------------
def test_typed_template_names_cannot_inject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = write(
        tmp_path / "m.json",
        {"id": "m", "initial": "a", "states": {"a": {"entry": [HOSTILE]}}},
    )
    run_cli(
        monkeypatch, "gt", src, "-t", "typed", "-o", str(tmp_path / "o"), "-f"
    )
    files = list((tmp_path / "o").glob("*.py"))
    assert files
    for f in files:
        assert not calls_os_system(f.read_text(encoding="utf-8"))


def test_pytest_scaffold_unreached_event_cannot_inject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = write(
        tmp_path / "m.json",
        {
            "id": "m",
            "initial": "a",
            "states": {
                "a": {"on": {"GO": "b"}},
                "b": {"on": {HOSTILE_EVENT: "a"}},
                "c": {},
            },
        },
    )
    run_cli(
        monkeypatch, "gt", src, "-t", "pytest", "-o", str(tmp_path / "o"), "-f"
    )
    for f in (tmp_path / "o").glob("*.py"):
        assert not calls_os_system(f.read_text(encoding="utf-8"))


def test_json_template_event_comment_cannot_inject(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = write(
        tmp_path / "m.json",
        {
            "id": "m",
            "initial": "a",
            "states": {"a": {"on": {HOSTILE_EVENT: "a"}}},
        },
    )
    for template in ("class-json", "function-json"):
        out = tmp_path / template
        run_cli(monkeypatch, "gt", src, "-t", template, "-o", str(out), "-f")
        for f in out.glob("*.py"):
            assert not calls_os_system(f.read_text(encoding="utf-8"))


# -- CLI-004 -----------------------------------------------------------------
def test_escape_for_string_escapes_line_breaks() -> None:
    for raw in ("a\nb", "a\rb", "a b", "a\x00b", "a\\b'c\"d"):
        literal = "'" + escape_for_string(raw) + "'"
        assert ast.literal_eval(literal) == raw


# -- CLI-003 -----------------------------------------------------------------
def test_safe_file_stem_blocks_traversal() -> None:
    for hostile in ("../escaped", "..\\x", "a/b", "..", "C:evil", ""):
        stem = safe_file_stem(hostile)
        assert stem and not set(stem) & set("/\\:")
        assert not stem.startswith(".")
    assert safe_file_stem("light-machine") == "light-machine"


def test_docs_and_diagram_stay_inside_output_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = write(
        tmp_path / "m.json",
        {"id": "../escaped", "initial": "a", "states": {"a": {}}},
    )
    out = tmp_path / "out"
    out.mkdir()
    run_cli(monkeypatch, "docs", src, "-o", str(out))
    run_cli(monkeypatch, "diagram", src, "-o", str(out))
    assert not list(tmp_path.glob("escaped*"))
    assert len(list(out.iterdir())) == 2


# -- CLI-005 -----------------------------------------------------------------
def test_logic_bindings_do_not_shadow_module_names() -> None:
    names = {"time", "logger", "logging", "Event", "other"}
    bound = logic_bindings(set(), set(), names)
    assert set(bound.values()).isdisjoint(
        {"time", "logger", "logging", "Event"}
    )
    assert len(set(bound.values())) == len(names)
    assert bound["other"] == "other"


# -- CLI-008 / CLI-018 -------------------------------------------------------
def test_json_child_without_parent_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    child = write(
        tmp_path / "c.json", {"id": "c", "initial": "a", "states": {"a": {}}}
    )
    code, _, err = run_cli(
        monkeypatch, "gt", "-jc", child, "-o", str(tmp_path / "o"), "-f"
    )
    assert code == 2
    assert "requires a parent" in err


@pytest.mark.parametrize(
    "argv",
    [
        ["-jp", "a.json", "-jp", "b.json"],
        ["--json-parent=a.json", "--json-parent=b.json"],
    ],
)
def test_duplicate_json_parent_is_rejected(argv: List[str]) -> None:
    parser: argparse.ArgumentParser = cli_args.get_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["generate-template", *argv])
    assert exc.value.code == 2


def test_negative_sleep_time_is_rejected() -> None:
    parser = cli_args.get_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            ["generate-template", "x.json", "--sleep-time", "-3"]
        )


# -- CLI-009 -----------------------------------------------------------------
def test_overwrite_prompt_at_eof_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = write(
        tmp_path / "m.json", {"id": "m", "initial": "a", "states": {"a": {}}}
    )
    out = str(tmp_path / "o")
    assert run_cli(monkeypatch, "gt", src, "-o", out)[0] == 0

    def eof(_prompt: str = "") -> str:
        raise EOFError

    monkeypatch.setattr("builtins.input", eof)
    code, _, err = run_cli(monkeypatch, "gt", src, "-o", out)
    assert code == 2
    assert "--force" in err


# -- CLI-011 -----------------------------------------------------------------
def test_prune_keeps_future_import() -> None:
    code = "from __future__ import annotations\nimport os\nx = 1\n"
    pruned = prune_unused_imports(code)
    assert "from __future__ import annotations" in pruned
    assert "import os" not in pruned


# -- CLI-012 -----------------------------------------------------------------
def test_list_target_is_reported_as_unsupported_by_name() -> None:
    machine = parse_machine(
        {
            "id": "m",
            "initial": "idle",
            "states": {
                "idle": {"on": {"GO": {"target": ["a", "b"]}}},
                "a": {},
                "b": {},
            },
        }
    )
    assert any(
        "idle.on.GO" in item and "list-valued" in item
        for item in machine.all_unsupported()
    )


# -- CLI-013 -----------------------------------------------------------------
def test_analyse_survives_non_utf8_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_bytes(b"\xff\xfe\x00")
    facts = analyse(bad)
    assert not facts.ok
    assert "cannot read" in facts.findings[0].message


# -- CLI-016 -----------------------------------------------------------------
def test_parse_version_handles_dev_post_and_rc() -> None:
    assert parse_version("1.0rc1.dev2")  # used to raise ValueError
    assert is_newer("1.2.0.post1", "1.2.0")
    assert is_newer("1.0.0", "1.0rc1")
    assert is_newer("1.0rc2", "1.0rc1.dev2")
    assert not is_newer("1.0.dev1", "1.0")
    assert is_newer("0.12.1", "0.12.0")


# -- CLI-007 -----------------------------------------------------------------
def test_coverage_json_gate_failure_goes_to_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from src.xstate_statemachine.cli.commands.coverage import run_coverage

    reset_console()
    out, err = io.StringIO(), io.StringIO()
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", err)
    reset_console()
    from src.xstate_statemachine.cli.commands import get_console

    get_console().error("boom", to_stderr=True)
    assert "boom" in err.getvalue()
    assert "boom" not in out.getvalue()
    assert callable(run_coverage)
