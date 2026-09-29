# scripts/gen_machine_schema.py
"""Regenerate ``schemas/xstate-machine.schema.json`` (#309).

The editor schema for machine JSON files, derived from the `[pydantic]`
config model (`MachineConfig`, #266) -- the same model
`validate_machine_json()` uses, which a parity test keeps in lock-step with
the parser. `tests/test_machine_schema.py` regenerates it and asserts the
committed file is byte-identical, so it cannot drift.

    python scripts/gen_machine_schema.py          # rewrite the file
    python scripts/gen_machine_schema.py --check  # exit 1 if stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "schemas" / "xstate-machine.schema.json"
SCHEMA_ID = (
    "https://raw.githubusercontent.com/basiltt/xstate-statemachine/main/"
    "schemas/xstate-machine.schema.json"
)


def build() -> Dict[str, Any]:
    sys.path.insert(0, str(ROOT / "src"))
    from xstate_statemachine.contrib.pydantic.config import MachineConfig

    body = MachineConfig.model_json_schema()
    doc: Dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_ID,
        "title": "xstate-statemachine machine JSON",
        "description": (
            "The XState JSON subset xstate-statemachine implements. "
            "Generated from contrib.pydantic.MachineConfig by "
            "scripts/gen_machine_schema.py -- do not edit by hand."
        ),
    }
    doc.update({k: v for k, v in body.items() if k not in doc})
    return doc


def render() -> str:
    return json.dumps(build(), indent=2, sort_keys=True) + "\n"


def main(argv: list) -> int:
    text = render()
    if "--check" in argv:
        current = OUT.read_text("utf-8") if OUT.is_file() else ""
        if current != text:
            print(f"{OUT} is stale; run scripts/gen_machine_schema.py")
            return 1
        return 0
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
