"""Render every docs statechart headlessly and fail on overlaps or clipped text.

The docs draw their machine embeds in the browser (``docs/assets/js/
diagrams.js`` + ``docs/assets/data/diagrams.json``). This script serves the
repository, opens ``scripts/diagram_harness.html`` in headless Chromium,
renders the charts with the real stylesheet and fonts, and measures the SVG:

* an error when two state boxes, a box and a transition label, two labels,
  or a label and a composite title overlap, when a transition line crosses
  a state box that is not one of its ends, or when a label is clipped;
* a warning when a transition line crosses another transition's label or a
  composite title band.

``--tune`` tries the alternative layout direction for every chart with
errors, keeps the first clean one in ``scripts/stately/diagram_layout.json``
and regenerates ``diagrams.json``.

Usage::

    uv run --with playwright python scripts/check_diagrams.py
    uv run --with playwright python scripts/check_diagrams.py --keys a41e6929ac,9f2c54a0a3
    uv run --with playwright python scripts/check_diagrams.py --theme light --shots out/shots
    uv run --with playwright python scripts/check_diagrams.py --tune

Needs the ``playwright`` package and a Chromium it can launch
(``python -m playwright install chromium``).
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import argparse
import functools
import http.server
import json
import pathlib
import sys
import threading
from typing import Any, Dict, List, Optional, Sequence, Tuple

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import diagram_mermaid as dm  # noqa: E402

Box = Tuple[float, float, float, float]  # x, y, w, h (CSS px, SVG origin)

MEASURE_JS = r"""
(key) => {
  const fig = document.querySelector('.statechart[data-machine="' + key + '"]');
  if (!fig) return { error: 'figure missing' };
  const svg = fig.querySelector('.statechart-canvas svg');
  if (!svg) {
    const d = (window.xsmDiagrams.figures || []).find(f => f.key === key);
    return { error: (d && d.error) || 'not rendered' };
  }
  // Natural size: the page scales a wide chart down, the check does not.
  const vb = svg.viewBox && svg.viewBox.baseVal;
  if (vb && vb.width) { svg.style.width = vb.width + 'px'; svg.style.height = vb.height + 'px'; svg.style.maxWidth = 'none'; }
  const base = svg.getBoundingClientRect();
  const box = el => { const r = el.getBoundingClientRect(); return [r.left - base.left, r.top - base.top, r.width, r.height]; };
  const text = el => (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  const leaves = [], markers = [], clusters = [], labels = [], edges = [], clipped = [];
  svg.querySelectorAll('g.node').forEach(n => {
    const shape = n.querySelector(':scope > rect, :scope > g > rect, :scope > circle, :scope > polygon, :scope > path') || n;
    const cls = n.getAttribute('class') || '';
    (cls.includes('statediagram-state') ? leaves : markers).push({ id: n.id, box: box(shape), text: text(n) });
  });
  svg.querySelectorAll('g.statediagram-cluster').forEach(c => {
    const outer = c.querySelector('rect.outer') || c.querySelector('rect') || c;
    const title = c.querySelector(':scope > g.cluster-label, :scope > .cluster-label');
    clusters.push({ id: c.id, box: box(outer), title: title && title.getBoundingClientRect().width ? box(title) : null, text: title ? text(title) : '' });
  });
  svg.querySelectorAll('g.edgeLabel').forEach(g => {
    const t = text(g);
    if (!t) return;
    const inner = g.querySelector('.xsm-pill, .labelBkg, foreignObject') || g;
    const lab = g.querySelector('g.label');
    labels.push({ edge: lab ? lab.getAttribute('data-id') : null, box: box(inner), text: t });
  });
  svg.querySelectorAll('path.transition').forEach(p => {
    const len = p.getTotalLength(), m = p.getScreenCTM(), pts = [];
    for (let s = 0; s <= len; s += 5) {
      const pt = p.getPointAtLength(s).matrixTransform(m);
      pts.push([pt.x - base.left, pt.y - base.top]);
    }
    edges.push({ id: p.getAttribute('data-id'), len, points: pts });
  });
  svg.querySelectorAll('foreignObject').forEach(fo => {
    const d = fo.firstElementChild;
    if (!d) return;
    const w = parseFloat(fo.getAttribute('width')), h = parseFloat(fo.getAttribute('height'));
    if (d.scrollWidth > w + 1.5 || d.scrollHeight > h + 1.5) clipped.push({ text: text(d), fo: [w, h], content: [d.scrollWidth, d.scrollHeight] });
  });
  return { width: base.width, height: base.height, leaves, markers, clusters, labels, edges, clipped };
}
"""


# -------------------------------------------------------------------------
# 🧮 Geometry
# -------------------------------------------------------------------------
def _intersects(a: Box, b: Box, slack: float = 0.5) -> bool:
    return not (
        a[0] + a[2] <= b[0] + slack
        or b[0] + b[2] <= a[0] + slack
        or a[1] + a[3] <= b[1] + slack
        or b[1] + b[3] <= a[1] + slack
    )


def _contains(outer: Box, inner: Box, slack: float = 1.0) -> bool:
    return (
        inner[0] >= outer[0] - slack
        and inner[1] >= outer[1] - slack
        and inner[0] + inner[2] <= outer[0] + outer[2] + slack
        and inner[1] + inner[3] <= outer[1] + outer[3] + slack
    )


def _inside(point: Sequence[float], box: Box, shrink: float) -> bool:
    return (
        box[0] + shrink < point[0] < box[0] + box[2] - shrink
        and box[1] + shrink < point[1] < box[1] + box[3] - shrink
    )


def analyse(geometry: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Return ``(errors, warnings)`` for one rendered chart."""
    if "error" in geometry:
        return [f"render failed: {geometry['error']}"], []
    errors = [
        f"clipped label {item['text']!r}: box {item['fo']} < content "
        f"{item['content']}"
        for item in geometry["clipped"]
    ]
    errors += _box_collisions(
        geometry["leaves"], geometry["labels"], geometry["markers"]
    )
    errors += _cluster_collisions(
        geometry["clusters"], geometry["leaves"], geometry["labels"]
    )
    errors += _bounds_errors(geometry["clusters"], geometry["labels"])
    edge_errors, warnings = _edge_collisions(
        geometry["edges"],
        geometry["leaves"],
        geometry["labels"],
        geometry["clusters"],
    )
    return errors + edge_errors, warnings


def _box_collisions(leaves, labels, markers) -> List[str]:
    """States, transition labels and start/end markers must not overlap."""
    errors: List[str] = []
    for i, a in enumerate(leaves):
        for b in leaves[i + 1 :]:  # noqa: E203
            if _intersects(a["box"], b["box"]):
                errors.append(
                    f"state {a['text']!r} overlaps state {b['text']!r}"
                )
        for lab in labels:
            if _intersects(a["box"], lab["box"]):
                errors.append(
                    f"state {a['text']!r} overlaps label {lab['text']!r}"
                )
        for m in markers:
            if _intersects(a["box"], m["box"]):
                errors.append(
                    f"state {a['text']!r} overlaps a start/end marker"
                )
    for i, a in enumerate(labels):
        for b in labels[i + 1 :]:  # noqa: E203
            if _intersects(a["box"], b["box"]):
                errors.append(
                    f"label {a['text']!r} overlaps label {b['text']!r}"
                )
        for m in markers:
            if _intersects(a["box"], m["box"]):
                errors.append(
                    f"label {a['text']!r} overlaps a start/end marker"
                )
    return errors


def _cluster_collisions(clusters, leaves, labels) -> List[str]:
    """Composite title bands stay clear; boxes nest, they never cross."""
    errors: List[str] = []
    for c in clusters:
        if c["title"]:
            for lab in labels:
                if _intersects(c["title"], lab["box"]):
                    errors.append(
                        f"title {c['text']!r} overlaps label {lab['text']!r}"
                    )
            for leaf in leaves:
                if _intersects(c["title"], leaf["box"]):
                    errors.append(
                        f"title {c['text']!r} overlaps state {leaf['text']!r}"
                    )
        for leaf in leaves:
            if _intersects(c["box"], leaf["box"]) and not _contains(
                c["box"], leaf["box"]
            ):
                errors.append(
                    f"state {leaf['text']!r} crosses the border of "
                    f"{c['text']!r}"
                )
    for i, a in enumerate(clusters):
        for b in clusters[i + 1 :]:  # noqa: E203
            if (
                _intersects(a["box"], b["box"])
                and not _contains(a["box"], b["box"])
                and not _contains(b["box"], a["box"])
            ):
                errors.append(
                    f"composite {a['text']!r} overlaps composite "
                    f"{b['text']!r}"
                )
    return errors


def _bounds_errors(clusters, labels) -> List[str]:
    """A transition label must stay inside the machine box (the largest
    composite), not hang over its border."""
    if not clusters:
        return []
    root = max(clusters, key=lambda c: c["box"][2] * c["box"][3])
    return [
        f"label {lab['text']!r} hangs outside the machine box"
        for lab in labels
        if not _contains(root["box"], lab["box"], slack=2.0)
    ]


def _edge_collisions(
    edges, leaves, labels, clusters
) -> Tuple[List[str], List[str]]:
    """A transition line through a state that is not one of its ends is an
    error; one crossing another transition's label or a composite title
    band is a warning."""
    errors: List[str] = []
    warnings: List[str] = []
    trim = 12.0
    for edge in edges:
        points = edge["points"]
        if len(points) < 4:
            continue
        body = [
            p
            for p in points
            if _dist(p, points[0]) > trim and _dist(p, points[-1]) > trim
        ]
        hit_leaf = {
            leaf["text"]
            for p in body
            for leaf in leaves
            if _inside(p, leaf["box"], 2.0)
        }
        hit_label = {
            lab["text"]
            for p in body
            for lab in labels
            if lab["edge"] != edge["id"] and _inside(p, lab["box"], 1.0)
        }
        hit_title = {
            c["text"]
            for p in body
            for c in clusters
            if c["title"] and _inside(p, c["title"], 1.0)
        }
        for name in sorted(hit_leaf):
            errors.append(
                f"transition {edge['id']} runs through state {name!r}"
            )
        for name in sorted(hit_label):
            warnings.append(f"transition {edge['id']} crosses label {name!r}")
        for name in sorted(hit_title):
            warnings.append(f"transition {edge['id']} crosses title {name!r}")
    return errors, warnings


def _dist(a: Sequence[float], b: Sequence[float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


# -------------------------------------------------------------------------
# 🌐 Serving and driving the browser
# -------------------------------------------------------------------------
class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_: Any) -> None:  # noqa: D401 - silence
        return


def serve(root: pathlib.Path) -> Tuple[http.server.ThreadingHTTPServer, int]:
    handler = functools.partial(_Quiet, directory=str(root))
    # 📝 Loopback only; port 0 lets the OS pick a free port without a race.
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def _chunks(items: Sequence[str], size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]  # noqa: E203


def run(
    keys: Sequence[str],
    theme: str,
    shots: Optional[pathlib.Path],
    batch: int,
    tune: bool,
    verbose: bool,
) -> int:
    from playwright.sync_api import sync_playwright

    asset = json.loads(dm.DATA_FILE.read_text(encoding="utf-8"))
    inventory = json.loads(
        (ROOT / "scripts" / "stately" / "machine_inventory.json").read_text(
            "utf-8"
        )
    )
    layout = dm.load_layout()
    layout_changed = False
    server, port = serve(ROOT)
    results: Dict[str, Tuple[List[str], List[str]]] = {}
    sizes: Dict[str, Tuple[float, float]] = {}
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 2600, "height": 1800}, device_scale_factor=1
            )
            console: List[str] = []
            page.on(
                "console",
                lambda m: (
                    console.append(m.text) if m.type == "error" else None
                ),
            )
            for group in _chunks(list(keys), batch):
                url = f"http://127.0.0.1:{port}/scripts/diagram_harness.html?keys={','.join(group)}&theme={theme}"
                page.goto(url, wait_until="load")
                page.wait_for_function(
                    "window.xsmDiagrams && window.xsmDiagrams.ready"
                )
                page.evaluate("() => window.xsmDiagrams.renderAll()")
                for key in group:
                    geometry = page.evaluate(MEASURE_JS, key)
                    errors, warnings = analyse(geometry)
                    if errors and tune:
                        errors, warnings, geometry, changed = _tune(
                            page,
                            key,
                            inventory,
                            layout,
                            errors,
                            warnings,
                            geometry,
                        )
                        layout_changed = layout_changed or changed
                    results[key] = (errors, warnings)
                    if "width" in geometry:
                        sizes[key] = (geometry["width"], geometry["height"])
                    if shots:
                        fig = page.query_selector(
                            f'.statechart[data-machine="{key}"]'
                        )
                        if fig:
                            fig.screenshot(path=str(shots / f"{key}.png"))
            browser.close()
    finally:
        server.shutdown()

    if layout_changed:
        clean = {k: v for k, v in layout.items() if v}
        dm.LAYOUT_FILE.write_text(
            json.dumps(clean, indent=1, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        import place_stately_embeds  # noqa: WPS433

        place_stately_embeds.write_map()
        print(
            f"layout overrides written for {len(clean)} chart(s); diagrams.json regenerated"
        )

    failed = {k: v for k, v in results.items() if v[0]}
    warned = sum(1 for v in results.values() if v[1])
    for key in sorted(results):
        errors, warnings = results[key]
        title = asset["machines"].get(key, {}).get("title", key)
        if errors or (verbose and warnings):
            size = sizes.get(key)
            dims = f" {int(size[0])}x{int(size[1])}" if size else ""
            print(f"[{'FAIL' if errors else 'warn'}] {key} {title}{dims}")
            for line in errors[:12]:
                print(f"    error: {line}")
            for line in warnings[:6]:
                print(f"    warn:  {line}")
    print(
        f"{len(results)} chart(s) checked, {len(failed)} with errors, "
        f"{warned} with warnings, theme={theme}"
    )
    if console:
        print(f"{len(console)} console error(s); first: {console[0][:200]}")
    return 1 if failed else 0


def _candidates(
    key: str, config: Dict[str, Any], layout: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Layouts to try for a failing chart: the other top-level direction,
    then each compound state laid out left to right (a wide title fits a
    wider box)."""
    current = layout.get(key, {})
    top = current.get("direction") or dm.default_direction(config)
    out = [dict(current, direction=d) for d in dm.DIRECTIONS if d != top]
    for state_id in dm.compound_ids(config):
        composites = dict(current.get("composites", {}))
        composites[state_id] = "LR"
        out.append(dict(current, composites=composites))
    return out


def _tune(
    page: Any,
    key: str,
    inventory: Dict[str, Any],
    layout: Dict[str, Dict[str, Any]],
    errors: List[str],
    warnings: List[str],
    geometry: Dict[str, Any],
):
    """Try the alternative layouts; keep the first clean rendering.

    Returns ``(errors, warnings, geometry, changed)``; the page is left
    showing the rendering that matches the returned geometry.
    """
    config = inventory[key]["config"]
    best = (errors, warnings, geometry, None)
    for candidate in _candidates(key, config, layout):
        source = dm.render_entry(key, config, {key: candidate})
        page.evaluate(
            "([k, s]) => window.xsmDiagrams.renderInto(k, s)", [key, source]
        )
        geo = page.evaluate(MEASURE_JS, key)
        errs, warns = analyse(geo)
        if len(errs) < len(best[0]):
            best = (errs, warns, geo, candidate)
        if not errs:
            break
    if best[3] is None:
        # Nothing better: put the committed rendering back for the shots.
        source = dm.render_entry(key, config, layout)
        page.evaluate(
            "([k, s]) => window.xsmDiagrams.renderInto(k, s)", [key, source]
        )
        return best[0], best[1], best[2], False
    layout[key] = best[3]
    return best[0], best[1], best[2], True


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--keys", help="comma-separated inventory keys (default: all)"
    )
    parser.add_argument("--theme", choices=("dark", "light"), default="dark")
    parser.add_argument(
        "--shots", type=pathlib.Path, help="write a PNG per chart here"
    )
    parser.add_argument(
        "--batch", type=int, default=12, help="charts per page load"
    )
    parser.add_argument(
        "--tune", action="store_true", help="fix layouts via direction"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="also list warnings"
    )
    args = parser.parse_args(argv)
    asset = json.loads(dm.DATA_FILE.read_text(encoding="utf-8"))
    keys = args.keys.split(",") if args.keys else sorted(asset["machines"])
    return run(
        keys, args.theme, args.shots, args.batch, args.tune, args.verbose
    )


if __name__ == "__main__":
    sys.exit(main())
