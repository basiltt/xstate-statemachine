"""Place Stately embeds in the docs.

Reads scripts/stately/machine_inventory.json (what is where) and
scripts/stately/stately_ids.json (inventory key -> Stately machineId), then:

* writes docs/assets/data/stately.json  (the map stately.js fetches),
* inserts  <div class="stately" data-machine="KEY" …></div>  after the
  fenced block that defines each machine in every docs page (idempotent:
  a page that already has the div for that key is left alone),
* writes docs/_guide/example-gallery.md with one embed per machine that
  lives under examples/ (the shipped example apps and recipes).
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INV = json.loads(
    (ROOT / "scripts" / "stately" / "machine_inventory.json").read_text()
)
IDS = json.loads(
    (ROOT / "scripts" / "stately" / "stately_ids.json").read_text()
)
PROJECT = "4dbe1227-e533-4104-9772-dd7c7b3a86df"
FENCE = re.compile(r"```(\w*)[^\n]*\n(.*?)```\n", re.S)


def nstates(c) -> int:
    n = 0
    for s in (c.get("states") or {}).values():
        n += 1 + (nstates(s) if isinstance(s, dict) else 0)
    return n


def height_for(cfg) -> int:
    n = nstates(cfg)
    return 320 if n <= 3 else 420 if n <= 6 else 520 if n <= 10 else 640


def div(key, cfg, title=None) -> str:
    t = title or cfg.get("id") or key
    return (
        f'<div class="stately" data-machine="{key}" '
        f'data-height="{height_for(cfg)}" data-title="{t}"></div>\n'
    )


def place_in_pages() -> int:
    # 📝 From scripts/machine_inventory.py: the same parser decides which
    # fence a key came from, so we re-run it per page to find the fence.
    import machine_inventory as mi  # noqa: WPS433

    placed = 0
    by_page = {}
    for key, e in INV.items():
        if key not in IDS:
            continue
        for w in e["where"]:
            if w.startswith("docs/") and w.endswith(".md"):
                by_page.setdefault(w, []).append((key, e["config"]))
    for rel, wanted in by_page.items():
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        out, pos = [], 0
        for m in FENCE.finditer(text):
            out.append(text[pos : m.end()])  # noqa: E203
            pos = m.end()
            lang, body = m.group(1), m.group(2)
            if lang in ("mermaid", "bash", "sh", "text", "yaml"):
                continue
            cfg = mi.try_parse(body)
            if not cfg:
                continue
            cfg = mi.strip_impls(cfg)
            key = next((k for k, c in wanted if c == cfg), None)
            if not key:
                continue
            marker = f'data-machine="{key}"'
            if marker in text:
                continue
            out.append("\n" + div(key, cfg))
            placed += 1
        out.append(text[pos:])
        new = "".join(out)
        if new != text:
            path.write_text(new, encoding="utf-8")
    return placed


def write_map() -> None:
    (DOCS / "assets" / "data").mkdir(parents=True, exist_ok=True)
    (DOCS / "assets" / "data" / "stately.json").write_text(
        json.dumps({"project": PROJECT, "machines": IDS}, indent=1),
        encoding="utf-8",
    )


def write_gallery() -> None:
    groups = {}
    for key, e in INV.items():
        if key not in IDS:
            continue
        src = next((w for w in e["where"] if w.startswith("examples/")), None)
        if not src:
            continue
        parts = src.split("/")
        group = "/".join(parts[1:3]) if len(parts) > 3 else parts[1]
        groups.setdefault(group, []).append((key, e["config"], src))
    lines = [
        "---",
        "title: Example gallery",
        "description: Every statechart shipped under examples/, "
        "drawn live by the Stately editor.",
        "---",
        "",
        "# Example gallery",
        "",
        "Every machine under [`examples/`]"
        "(https://github.com/basiltt/xstate-statemachine/tree/main/examples)",
        "as the Stately editor draws it. The diagrams follow the site "
        "theme; each one links to the",
        "public editor page where you can simulate it. The JSON next to "
        "each diagram is what the",
        "example runs unchanged.",
        "",
    ]
    for group in sorted(groups):
        lines += [f"## `{group}`", ""]
        for key, cfg, src in sorted(groups[group], key=lambda t: t[2]):
            gh = (
                "https://github.com/basiltt/xstate-statemachine/blob/main/"
                + src
            )
            lines += [
                f"### {cfg.get('id', key)}",
                "",
                f"Source: [`{src}`]({gh})",
                "",
                div(key, cfg).rstrip(),
                "",
            ]
    (DOCS / "_guide" / "example-gallery.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT / "scripts"))
    write_map()
    n = place_in_pages()
    write_gallery()
    print(f"placed {n} embeds; map has {len(IDS)} machines")
