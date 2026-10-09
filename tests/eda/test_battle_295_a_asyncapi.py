# tests/eda/test_battle_295_a_asyncapi.py
"""#295 battle (adversary A): `asyncapi_document` over the 100+ real charts
in the CLI corpus, key collisions after sanitising, odd ids and titles,
byte-stable output, and `xsm asyncapi` failure paths (one line, exit 2)."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Dict, List
from unittest import mock

import pytest

from src.xstate_statemachine import create_machine
from src.xstate_statemachine.cli.commands.asyncapi import run_asyncapi
from src.xstate_statemachine.eda import asyncapi_document
from src.xstate_statemachine.eda import asyncapi as asyncapi_mod
from src.xstate_statemachine.exceptions import (
    InvalidConfigError,
    MissingExtraError,
)
from src.xstate_statemachine.testing_utils import stub_logic

jsonschema = pytest.importorskip("jsonschema")
validate_asyncapi = asyncapi_mod.validate_asyncapi

CORPUS = Path(__file__).resolve().parents[1] / "tests_cli" / "stately_machines"


def _corpus() -> List[Path]:
    return sorted(CORPUS.rglob("*.json"))


# -----------------------------------------------------------------------------
# 📚 The real-chart corpus
# -----------------------------------------------------------------------------
class TestCorpus(unittest.TestCase):
    def test_every_chart_documents_validates_and_is_stable(self) -> None:
        files = _corpus()
        self.assertGreaterEqual(len(files), 100)
        built = 0
        for f in files:
            cfg = json.loads(f.read_text(encoding="utf-8"))
            try:
                m = create_machine(cfg, logic=stub_logic(cfg))
            except InvalidConfigError:
                continue  # 📝 not a machine (a fixture fragment)
            with self.subTest(chart=f.name):
                doc = asyncapi_document(m)
                validate_asyncapi(doc)
                again = json.dumps(asyncapi_document(m), sort_keys=False)
                self.assertEqual(json.dumps(doc, sort_keys=False), again)
                consumed = {
                    v["payload"]["allOf"][1]["properties"]["type"]["const"]
                    for k, v in doc["components"]["messages"].items()
                    if k.startswith("consume.")
                }
                self.assertEqual(
                    len(consumed),
                    len(asyncapi_mod.consumed_events(m)),
                )
                built += 1
        self.assertGreaterEqual(built, 100)


# -----------------------------------------------------------------------------
# 🔑 Component keys
# -----------------------------------------------------------------------------
def _collide() -> Dict[str, Any]:
    return {
        "id": 'm.x-y "q',
        "initial": "a",
        "states": {
            "a": {
                "on": {
                    "GO NOW": {
                        "target": "b",
                        "meta": {"publish": {"type": "x y"}},
                    },
                    "GO_NOW": {
                        "target": "b",
                        "meta": {"publish": {"type": "x_y"}},
                    },
                }
            },
            "b": {"type": "final", "tags": ["publish"]},
        },
    }


def _types(doc: Dict[str, Any], prefix: str) -> List[str]:
    return sorted(
        v["name"]
        for k, v in doc["components"]["messages"].items()
        if k.startswith(prefix)
    )


class TestKeys(unittest.TestCase):
    def test_sanitised_collisions_keep_every_message(self) -> None:
        # 🐛 "GO NOW" and "GO_NOW" both became `consume.GO_NOW` (one lost);
        #    published "x y" was silently dropped behind "x_y".
        doc = asyncapi_document(create_machine(_collide()), title='a"b')
        validate_asyncapi(doc)
        self.assertEqual(
            _types(doc, "consume."),
            ['xsm.m.x-y "q.GO NOW', 'xsm.m.x-y "q.GO_NOW'],
        )
        self.assertIn("x y", _types(doc, "publish."))
        self.assertIn("x_y", _types(doc, "publish."))
        ops = doc["operations"]
        refs = [r["$ref"] for op in ops.values() for r in op["messages"]]
        self.assertEqual(len(refs), len(set(refs)))
        self.assertEqual(doc["info"]["title"], 'a"b')

    def test_same_published_type_twice_is_one_message(self) -> None:
        cfg = _collide()
        cfg["states"]["a"]["on"]["GO_NOW"]["meta"]["publish"] = "x y"
        doc = asyncapi_document(create_machine(cfg))
        self.assertEqual(_types(doc, "publish.").count("x y"), 1)

    def test_publish_forms_and_inbound_equals_outbound(self) -> None:
        cfg = {
            "id": "p",
            "type": "parallel",
            "states": {
                "r1": {
                    "initial": "a",
                    "states": {
                        "a": {"on": {"T": {"target": "h", "meta": {}}}},
                        "h": {"type": "history"},
                    },
                },
                "r2": {
                    "initial": "x",
                    "states": {"x": {"tags": ["publish"]}},
                },
            },
        }
        doc = asyncapi_document(
            create_machine(cfg), inbound_topic="t", outbound_topic="t"
        )
        validate_asyncapi(doc)
        addrs = {c["address"] for c in doc["channels"].values()}
        self.assertEqual(addrs, {"t"})


# -----------------------------------------------------------------------------
# 🖥️ `xsm asyncapi` failure paths
# -----------------------------------------------------------------------------
class TestCli(unittest.TestCase):
    def _chart(self, d: str) -> str:
        p = Path(d) / "m.json"
        p.write_text(json.dumps(_collide()), encoding="utf-8")
        return str(p)

    def _exit2(self, **kw: Any) -> str:
        err = io.StringIO()
        with TemporaryDirectory() as d, redirect_stderr(err):
            with self.assertRaises(SystemExit) as cm:
                run_asyncapi(self._chart(d), **kw)
        self.assertEqual(cm.exception.code, 2)
        text = err.getvalue()
        self.assertEqual(text.count("\n"), 1, text)
        self.assertNotIn("Traceback", text)
        return text

    def test_unwritable_output_is_one_line(self) -> None:
        with TemporaryDirectory() as d:
            bad = str(Path(d) / "missing" / "dir" / "x.json")
            self.assertIn("cannot write", self._exit2(output=bad))

    def test_validate_without_jsonschema_is_one_line(self) -> None:
        exc = MissingExtraError("asyncapi", "jsonschema")
        with mock.patch.object(
            asyncapi_mod, "validate_asyncapi", side_effect=exc
        ):
            self._exit2(validate=True)

    def test_validate_invalid_document_is_one_line(self) -> None:
        bad = jsonschema.ValidationError("boom")
        with mock.patch.object(
            asyncapi_mod, "validate_asyncapi", side_effect=bad
        ):
            self.assertIn("not valid AsyncAPI", self._exit2(validate=True))

    def test_missing_jsonschema_message_names_a_real_install(self) -> None:
        # 🐛 told users to `pip install "xstate-statemachine[asyncapi]"` --
        #    there is no such extra.
        import builtins

        real = builtins.__import__

        def imp(name: str, *a: Any, **k: Any) -> Any:
            if name == "jsonschema":
                raise ImportError(name)
            return real(name, *a, **k)

        with mock.patch.object(builtins, "__import__", imp):
            with self.assertRaises(MissingExtraError) as cm:
                validate_asyncapi({})
        self.assertNotIn("[asyncapi]", str(cm.exception))
        self.assertIn("pip install jsonschema", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
