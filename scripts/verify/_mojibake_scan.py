"""Scan tracked text files for UTF-8-read-as-cp1252 mojibake (``--fix`` to
reverse it line by line). Used before the RC; keeps generated comments and
docs honest after PowerShell edits that re-encoded emoji."""

from __future__ import annotations

import re
import subprocess
import sys

PAT = re.compile(
    "\u00f0\u0178|\u00e2\u20ac|\u00e2\u2020\u2019|\u00c3\u00a9|\u00c2\u00b7|\u00e2\u0161|\u00c3\u00a2"
    # \ud83d\udcdd Variation selector U+FE0F and combining keycap U+20E3 (the "1\ufe0f\u20e3"
    #    family) double-encode to these; the keycap one was missed once
    #    and reached CI (battle #258).
    "|\u00ef\u00b8\u008f|\u00e2\u0192\u00a3"
)
EXT = (".py", ".md", ".html", ".json", ".yml", ".yaml", ".toml", ".txt")


def reverse(line: str) -> str:
    b = bytearray()
    for ch in line:
        o = ord(ch)
        if o < 0x80 or 0x80 <= o <= 0x9F:
            b.append(o)
        else:
            try:
                b += ch.encode("cp1252")
            except UnicodeError:
                b += ch.encode("latin-1")
    return b.decode("utf-8")


def main(argv: list) -> int:
    fix = "--fix" in argv
    # 📝 Tracked AND untracked-but-not-ignored files: the handover doc for
    #    the battle programme was untracked when the local scan ran, passed
    #    here, and then failed `TestNoMojibake` in all ten CI cells.
    files = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    bad = 0
    for f in files:
        if not f.endswith(EXT):
            continue
        try:
            with open(f, encoding="utf-8", newline="") as fh:
                text = fh.read()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        if not PAT.search(text):
            continue
        bad += 1
        out = []
        for n, line in enumerate(text.splitlines(keepends=True), 1):
            if PAT.search(line):
                print(f"{f}:{n}: {line.strip()[:90]}")
                if fix:
                    try:
                        line = reverse(line)
                    except UnicodeError:
                        print("   (could not reverse)")
            out.append(line)
        if fix:
            with open(f, "w", encoding="utf-8", newline="") as fh:
                fh.write("".join(out))
    print(f"mojibake files: {bad}" + (" (fixed)" if fix and bad else ""))
    return 0 if (fix or not bad) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
