# tests/test_machine_schema.py
"""The published editor schema (#309) cannot drift and accepts the corpus."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "schemas" / "xstate-machine.schema.json"
CORPUS = ROOT / "tests" / "tests_cli" / "stately_machines"
EXAMPLE = ROOT / "examples" / "integrations" / "fastapi_orders"


def _gen():
    spec = importlib.util.spec_from_file_location(
        "gen_machine_schema", ROOT / "scripts" / "gen_machine_schema.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_committed_schema_is_regenerated_byte_identical() -> None:
    pytest.importorskip("pydantic")
    # 📝 read_text: universal newlines, so a `core.autocrlf` checkout of
    #    the LF-committed file still compares equal.
    assert SCHEMA.read_text("utf-8") == _gen().render(), (
        "schemas/xstate-machine.schema.json is stale: "
        "python scripts/gen_machine_schema.py"
    )


def _machines():
    files = sorted(CORPUS.rglob("*.json")) + [EXAMPLE / "machine.json"]
    assert len(files) > 50, "corpus discovery broke"
    return files


def test_schema_accepts_every_corpus_machine() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text("utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    bad = []
    for f in _machines():
        errs = list(validator.iter_errors(json.loads(f.read_text("utf-8"))))
        if errs:
            bad.append(f"{f.name}: {errs[0].message[:120]}")
    assert bad == []


def test_schema_rejects_a_broken_machine() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA.read_text("utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    broken = {"id": "m", "states": {"a": {"type": "nope"}}}
    assert list(validator.iter_errors(broken))
    assert list(validator.iter_errors({"states": {"a": {}}}))  # no id
