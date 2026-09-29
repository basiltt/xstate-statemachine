# tests/test_security_baseline.py
# -----------------------------------------------------------------------------
# 🔒 X0.2 + X0.14 (#303): the two baseline items that are properties of the
#    SOURCE TREE, not of any runtime object, so they are checked by reading
#    the tree.
# -----------------------------------------------------------------------------
"""No code-in-data under ``src/``; every GitHub Action pinned to a SHA."""

from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "xstate_statemachine"
WORKFLOWS = ROOT / ".github" / "workflows"

#: 📝 X0.2: deserialisers that execute or construct arbitrary objects. A
#: line may opt out with the marker `xsm:allow-<name>` next to a comment
#: explaining why (today: one `exec` in `cli/validation.py` that runs the
#: generator's OWN freshly emitted output, never external text).
_BANNED = {
    "pickle": re.compile(
        r"^\s*(import pickle\b|from pickle\b)|\bpickle\.loads?\("
    ),
    "marshal": re.compile(r"\bmarshal\.loads?\("),
    "shelve": re.compile(r"^\s*(import shelve\b|from shelve\b)"),
    "yaml": re.compile(r"\byaml\.(unsafe_)?load\("),
    "eval": re.compile(r"(?<![\w.])eval\("),
    "exec": re.compile(r"(?<![\w.])exec\("),
}

#: X0.14: `uses: owner/repo@<40-hex sha>`; a version tag is not a pin.
_USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)
_SHA_PIN = re.compile(r"^[\w.-]+/[\w.-]+(/[\w./-]+)?@[0-9a-f]{40}$")


class TestNoUnsafeDeserialisation(unittest.TestCase):
    def test_no_banned_deserialiser_under_src(self) -> None:
        hits = []
        for path in sorted(SRC.rglob("*.py")):
            for no, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                for name, pat in _BANNED.items():
                    if pat.search(line) and f"xsm:allow-{name}" not in line:
                        hits.append(
                            f"{path.relative_to(ROOT)}:{no}: {line.strip()}"
                        )
        self.assertEqual(hits, [], "\n".join(hits))

    def test_the_one_exemption_is_still_justified(self) -> None:
        """The marker must sit on a line that the surrounding comment
        explains -- an unexplained `xsm:allow-*` is a ban bypass."""
        for path in sorted(SRC.rglob("*.py")):
            lines = path.read_text(encoding="utf-8").splitlines()
            for no, line in enumerate(lines):
                if "xsm:allow-" in line:
                    window = "\n".join(lines[max(0, no - 6) : no])
                    self.assertIn(
                        "#", window, f"{path.name}:{no + 1} marker unexplained"
                    )


class TestActionsArePinned(unittest.TestCase):
    def test_every_uses_is_a_full_sha(self) -> None:
        bad = []
        for wf in sorted(WORKFLOWS.glob("*.yml")):
            for ref in _USES.findall(wf.read_text(encoding="utf-8")):
                if ref.startswith("./"):  # local composite action
                    continue
                if not _SHA_PIN.match(ref):
                    bad.append(f"{wf.name}: uses: {ref}")
        self.assertEqual(bad, [], "\n".join(bad))

    def test_audit_job_covers_every_shipped_extra(self) -> None:
        """X0.14: `pip-audit` runs over `[all]`, so `[all]` must carry every
        requirement of every SHIPPED extra (one whose contrib subpackage
        exists on disk). An extra missing from `[all]` is a dependency
        nobody audits."""
        from src.xstate_statemachine.contrib._registry import EXTRAS

        extras = _pyproject_extras()
        self.assertIn("all", extras)
        ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
        self.assertIn('".[all]" pip-audit', ci)
        self.assertIn("pip_audit --strict", ci)
        unaudited = []
        for name, extra in EXTRAS.items():
            if not extra.subpackage:
                continue
            if not SRC.joinpath(
                "contrib", *extra.subpackage.split(".")
            ).is_dir():
                continue  # not shipped yet
            reqs = extras.get(name, [])
            self.assertTrue(reqs, f"shipped extra [{name}] declares nothing")
            for req in reqs:
                if req not in extras["all"]:
                    unaudited.append(f"[{name}] -> {req}")
        self.assertEqual(unaudited, [], "\n".join(unaudited))


def _pyproject_extras() -> dict:
    """``{extra: [requirement, ...]}`` from ``[project.optional-dependencies]``
    -- a small regex reader because 3.9 has no ``tomllib``."""
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("[project.optional-dependencies]", 1)[1].split(
        "\n[", 1
    )[0]
    out: dict = {}
    # 📝 Match to the closing `]` that ENDS the list -- `]` followed by a
    #    comment or a newline -- not the first `]` inside a requirement such
    #    as "sqlalchemy[asyncio]>=2.0" (PEP 508 extras are legitimate).
    for m in re.finditer(
        r"^([a-z]+)\s*=\s*\[(.*?)\][ \t]*(?:#[^\n]*)?$", block, re.M | re.S
    ):
        body = re.sub(r"#[^\n]*", "", m.group(2))
        out[m.group(1)] = re.findall(r'"([^"]+)"', body)
    return out


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
