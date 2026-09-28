"""Verification for #303 (X0 security & operability baseline, Phase A
close-out). Runs on any OS: `python scripts/verify/303_x0_baseline.py`.

Checks the deliverables end to end: the trust-model document, the two
guide pages and their nav wiring, the FileStore format version (X0.10),
the supply-chain job (X0.14), and the two tree-level guards (X0.2 bans,
Action pins) by running their tests.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def step(name: str) -> None:
    print(f"\n== {name}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def main() -> int:
    step("1. SECURITY.md states the trust model and how to report")
    sec = read("SECURITY.md")
    for needle in (
        "## Reporting a vulnerability",
        "## Trust model",
        "Installed packages are fully trusted",
        "events and snapshots are not",
        "#303",
    ):
        assert needle in sec, needle
    print("   OK")

    step("2. Guarantees + Security pages exist, are in the nav, cross-link")
    guar = read("docs/_guide/guarantees.md")
    secp = read("docs/_guide/security.md")
    layout = read("docs/_layouts/default.html")
    assert "## The order of operations" in guar
    assert "## Crash windows, one by one" in guar
    for n in range(1, 18):
        assert f"| X0.{n} |" in secp, f"X0.{n} row missing"
    for page in ("guarantees", "security"):
        assert f"/guide/{page}/" in layout, page
        assert f"{page}," in layout, f"{page} not in pages_order"
    assert "../guarantees/" in secp and "job **`audit`**" in secp
    tests_dir = ROOT / "tests"
    have = {p.name for p in tests_dir.rglob("test_*.py")}
    named = set(re.findall(r"`(test_[a-z_]+\.py)::", guar + secp))
    missing = sorted(named - have)
    assert not missing, f"pages name tests that do not exist: {missing}"
    print(f"   OK ({len(named)} test files referenced, all present)")

    step("3. X0.10: FileStore record carries `format`; newer is refused")
    from xstate_statemachine.exceptions import SnapshotCorruptError
    from xstate_statemachine.persistence import FileStore
    from xstate_statemachine.persistence.file_store import FORMAT_VERSION

    with tempfile.TemporaryDirectory() as d:
        store = FileStore(d)
        store.save("k", '{"x":1}')
        rec_path = next(Path(d).glob("*.xsm.json"))
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
        assert rec["format"] == FORMAT_VERSION, rec
        rec["format"] = FORMAT_VERSION + 1
        rec_path.write_text(json.dumps(rec), encoding="utf-8")
        try:
            store.load("k")
        except SnapshotCorruptError as exc:
            assert "newer" in str(exc), exc
        else:
            raise AssertionError("newer format was accepted")
    print(f"   OK (format {FORMAT_VERSION})")

    step("4. X0.14: pip-audit job over [all]; [all] lists shipped extras")
    ci = read(".github/workflows/ci.yml")
    assert "  audit:" in ci and "pip_audit --strict" in ci, "audit job"
    assert '".[all]" pip-audit' in ci
    py = read("pyproject.toml")
    block = py.split("[project.optional-dependencies]", 1)[1].split("\n[", 1)[
        0
    ]
    m = re.search(r"^all\s*=\s*\[(.*?)\]", block, re.M | re.S)
    assert m, "[all] missing"
    all_reqs = re.findall(r'"([^"]+)"', re.sub(r"#[^\n]*", "", m.group(1)))
    assert any(r.startswith("redis") for r in all_reqs), all_reqs
    assert any(r.startswith("pydantic") for r in all_reqs), all_reqs
    print("   OK", all_reqs)

    step("5. X0.2 bans + Action pins + docs-site guards (pytest)")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_security_baseline.py",
            "tests/test_docs_site.py::TestSecurityBaseline",
            "tests/test_docs_site.py::TestGuideChangelogMirrorsRoot",
            "-q",
            "-p",
            "no:cacheprovider",
            "--no-header",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    print(proc.stdout.strip().splitlines()[-1])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    print("   OK")

    step("6. Changelog entry in both files")
    for rel in ("CHANGELOG.md", "docs/_guide/changelog.md"):
        assert "baseline X0 (#303)" in read(rel), rel
    print("   OK")

    print("\nALL OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
