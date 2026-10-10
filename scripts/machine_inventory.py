"""Inventory every machine config used across docs/ and examples/.

Writes docs/_data/machine_inventory.json: one entry per distinct machine
(by normalised config hash) with the pages/files it appears on.
"""

import ast
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from xstate_statemachine import create_machine  # noqa: E402

FENCE = re.compile(r"```(\w*)[^\n]*\n(.*?)```", re.S)


def try_parse(text: str):
    text = text.strip()
    for loader in (json.loads, ast.literal_eval):
        try:
            v = loader(text)
            if isinstance(v, dict) and "states" in v:
                return v
        except Exception:  # noqa: BLE001
            pass
    # Python: find a top-level dict literal assigned to a NAME
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            try:
                v = ast.literal_eval(node)
            except Exception:  # noqa: BLE001
                continue
            if (
                isinstance(v, dict)
                and "states" in v
                and ("initial" in v or v.get("type") == "parallel")
            ):
                return v
    return None


def strip_impls(cfg):
    """Drop non-JSON values (callables leak through literal_eval as None)."""
    return json.loads(json.dumps(cfg, default=lambda o: str(o)))


def valid(cfg) -> bool:
    try:
        create_machine(cfg)
        return True
    except Exception:  # noqa: BLE001
        return False


def scan():
    found = {}

    def add(cfg, where):
        cfg = strip_impls(cfg)
        key = hashlib.sha1(
            json.dumps(cfg, sort_keys=True).encode()
        ).hexdigest()[:10]
        e = found.setdefault(
            key,
            {
                "id": cfg.get("id", "machine"),
                "config": cfg,
                "valid": valid(cfg),
                "where": [],
            },
        )
        if where not in e["where"]:
            e["where"].append(where)

    for md in sorted((ROOT / "docs").rglob("*.md")):
        if "superpowers" in md.parts or "research" in md.parts:
            continue
        rel = md.relative_to(ROOT).as_posix()
        for lang, body in FENCE.findall(md.read_text(encoding="utf-8")):
            if lang in ("mermaid", "bash", "sh", "text", "yaml"):
                continue
            cfg = try_parse(body)
            if cfg:
                add(cfg, rel)
    for jf in sorted((ROOT / "examples").rglob("*.json")):
        try:
            cfg = json.loads(jf.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if isinstance(cfg, dict) and "states" in cfg:
            add(cfg, jf.relative_to(ROOT).as_posix())
    for py in sorted((ROOT / "examples").rglob("*.py")):
        cfg = try_parse(py.read_text(encoding="utf-8"))
        if cfg:
            add(cfg, py.relative_to(ROOT).as_posix())
    return found


if __name__ == "__main__":
    inv = scan()
    out = ROOT / "docs" / "_data" / "machine_inventory.json"
    out.write_text(json.dumps(inv, indent=1), encoding="utf-8")
    print(
        len(inv),
        "distinct machines,",
        sum(e["valid"] for e in inv.values()),
        "valid",
    )
    for k, e in inv.items():
        print(
            k,
            e["id"],
            "OK" if e["valid"] else "BAD",
            len(e["where"]),
            e["where"][0],
        )
