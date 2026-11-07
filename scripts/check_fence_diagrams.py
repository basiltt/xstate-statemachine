"""Render every ```mermaid fence in the docs and fail on unreadable output.

The 245 generated statecharts take their colours from style.css; the
hand-authored fences (sequence diagrams, flowcharts, state diagrams written
by hand) are coloured by Mermaid's own theme, which diagrams.js now derives
from the same palette and re-applies when the theme changes. This script
serves the repository, renders every fence with the real stylesheet, fonts
and renderer at a page width and a phone width, in both themes, and checks:

* clipped text (a label wider or taller than its box, as for the statecharts),
* low-contrast text (below 4.5:1 against its effective backdrop; below 3:1
  is an error, 3-4.5 a warning),
* a figure whose SVG overflows its column at the phone width.

``--shots DIR`` writes one PNG per fence per theme and width for review.

Usage::

    uv run --with playwright python scripts/check_fence_diagrams.py
    uv run --with playwright python scripts/check_fence_diagrams.py --theme light --widths 375 --shots out/fences
"""

# -------------------------------------------------------------------------
# 📦 Standard Library Imports
# -------------------------------------------------------------------------
import argparse
import json
import pathlib
import re
import sys
from typing import Any, Dict, List, Optional, Sequence

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import check_diagrams as cd  # noqa: E402

FENCE = re.compile(r"^```mermaid\n(.*?)^```", re.S | re.M)
KIND = re.compile(
    r"^\s*(stateDiagram(-v2)?|flowchart|graph|sequenceDiagram)\b", re.M
)
DEFAULT_WIDTHS = (760, 375)
CONTRAST_ERROR = 3.0
CONTRAST_WARN = 4.5


def fences(root: pathlib.Path = DOCS) -> List[Dict[str, Any]]:
    """Every Mermaid fence under *root*, in file order."""
    out: List[Dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for index, match in enumerate(FENCE.finditer(text)):
            source = match.group(1)
            kind = KIND.search(source)
            if not kind:
                continue
            line = text.count("\n", 0, match.start()) + 1
            out.append(
                {
                    "file": str(path.relative_to(root.parent)),
                    "line": line,
                    "index": index,
                    "kind": kind.group(1),
                    "source": source,
                }
            )
    return out


MEASURE_JS = r"""
() => {
  const parseColor = value => {
    if (!value) return null;
    const m = value.match(/rgba?\(([^)]+)\)/);
    if (m) {
      const p = m[1].split(',').map(Number);
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    }
    if (value.startsWith('#')) {
      let h = value.slice(1);
      if (h.length === 3) h = h.split('').map(c => c + c).join('');
      const n = parseInt(h.slice(0, 6), 16);
      return { r: (n >> 16) & 255, g: (n >> 8) & 255, b: n & 255, a: 1 };
    }
    return null;
  };
  const over = (top, bottom) => {
    const a = top.a + bottom.a * (1 - top.a);
    if (!a) return { r: 0, g: 0, b: 0, a: 0 };
    return {
      r: Math.round((top.r * top.a + bottom.r * bottom.a * (1 - top.a)) / a),
      g: Math.round((top.g * top.a + bottom.g * bottom.a * (1 - top.a)) / a),
      b: Math.round((top.b * top.a + bottom.b * bottom.a * (1 - top.a)) / a),
      a
    };
  };
  const backdrop = el => {
    const layers = [];
    for (let cur = el; cur; cur = cur.parentElement) {
      const c = parseColor(getComputedStyle(cur).backgroundColor);
      if (c && c.a > 0.02) layers.push(c);
      if (cur === document.body) break;
    }
    let base = { r: 255, g: 255, b: 255, a: 1 };
    for (let i = layers.length - 1; i >= 0; i--) base = over(layers[i], base);
    return base;
  };
  const lum = c => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  const hex = c => '#' + [c.r, c.g, c.b].map(v => v.toString(16).padStart(2, '0')).join('');
  const figures = [...document.querySelectorAll('.statechart[data-kind="fence"]')];
  const out = [];
  figures.forEach((fig, index) => {
    const svg = fig.querySelector('.statechart-canvas svg');
    const canvas = fig.querySelector('.statechart-canvas');
    const entry = { index, text: '', errors: [], warnings: [], low: [], rect: null };
    if (!svg) { entry.errors.push('not drawn'); out.push(entry); return; }
    const figRect = fig.getBoundingClientRect();
    const svgRect = svg.getBoundingClientRect();
    const canvasStyle = getComputedStyle(canvas);
    const inner = canvas.clientWidth - parseFloat(canvasStyle.paddingLeft) - parseFloat(canvasStyle.paddingRight);
    entry.rect = [Math.round(figRect.width), Math.round(svgRect.width), Math.round(inner)];
    const vb = svg.viewBox && svg.viewBox.baseVal;
    const natural = vb && vb.width ? vb.width : svgRect.width;
    const scale = natural ? svgRect.width / natural : 1;
    entry.scale = +scale.toFixed(3);
    // diagrams.js keeps anything below 75% at natural size with a scroll;
    // below 70% measured here means that floor was lost.
    if (scale < 0.7) {
      entry.errors.push('chart shrunk to ' + Math.round(scale * 100) + '% (labels unreadable)');
    }
    if (svgRect.width > inner + 2) {
      const overflowX = canvasStyle.overflowX;
      const scrolls = overflowX === 'auto' || overflowX === 'scroll';
      if (!scrolls || canvas.scrollWidth <= canvas.clientWidth + 1) {
        entry.errors.push('wider than its canvas and the canvas does not scroll');
      }
    }
    // Clipped text, as for the statecharts.
    svg.querySelectorAll('foreignObject').forEach(fo => {
      const d = fo.firstElementChild;
      if (!d) return;
      const w = parseFloat(fo.getAttribute('width'));
      const h = parseFloat(fo.getAttribute('height'));
      if (d.scrollWidth > w + 1.5 || d.scrollHeight > h + 1.5) {
        entry.errors.push('clipped label ' + JSON.stringify((d.textContent || '').trim().slice(0, 40)));
      }
    });
    // Contrast of every painted text run against its effective backdrop.
    // 📝 Mermaid paints sequence labels on the `tspan` children; the parent
    //    `text` can carry the actor box's fill (22 February 2026: measuring
    //    the parent reported box-on-canvas instead of label-on-box).
    const runs = [];
    svg.querySelectorAll('text').forEach(t => {
      const spans = [...t.querySelectorAll('tspan')]
        .filter(s => (s.textContent || '').trim());
      const nodes = spans.length ? spans : ((t.textContent || '').trim() ? [t] : []);
      nodes.forEach(n => runs.push({ el: n, paint: getComputedStyle(n).fill, color: getComputedStyle(n).color }));
    });
    svg.querySelectorAll('foreignObject div, foreignObject span, foreignObject p').forEach(n => {
      if (n.querySelector('*') && [...n.querySelectorAll('*')].some(c => (c.textContent || '').trim())) return;
      runs.push({ el: n, paint: getComputedStyle(n).color, color: getComputedStyle(n).color });
    });
    const seen = new Set();
    runs.forEach(run => {
      const node = run.el;
      const text = (node.textContent || '').trim().replace(/\s+/g, ' ');
      if (!text || seen.has(node)) return;
      const rect = node.getBoundingClientRect();
      if (rect.width < 2 || rect.height < 2) return;
      let raw = run.paint;
      if (!raw || raw === 'none' || raw.startsWith('url(')) raw = run.color;
      const fg = parseColor(raw);
      if (!fg || fg.a < 0.05) return;
      const bg = backdrop(node);
      const r = ratio(over(fg, bg), bg);
      if (r < 3.0) entry.errors.push(`low contrast ${JSON.stringify(text.slice(0, 40))} ${r.toFixed(2)}:1`);
      else if (r < 4.5) entry.warnings.push(`${JSON.stringify(text.slice(0, 40))} ${r.toFixed(2)}:1`);
      if (r < 4.5) entry.low.push({ text: text.slice(0, 60), fg: hex(over(fg, bg)), bg: hex(bg), ratio: +r.toFixed(2) });
      seen.add(node);
    });
    out.push(entry);
  });
  return { width: innerWidth, pageOverflow: document.documentElement.scrollWidth > innerWidth + 1, figures: out };
}
"""


def render(
    page: Any, sources: Sequence[str], theme: str, width: int, port: int
) -> List[Dict[str, Any]]:
    page.add_init_script(
        "window.__fenceSources = " + json.dumps(list(sources)) + ";"
    )
    page.goto(
        f"http://127.0.0.1:{port}/scripts/diagram_harness.html"
        f"?theme={theme}&width={width}",
        wait_until="load",
    )
    page.wait_for_function("window.xsmDiagrams && window.xsmDiagrams.ready")
    page.wait_for_function(
        "document.querySelectorAll('.statechart[data-kind=\"fence\"]').length === %d "
        "&& [...document.querySelectorAll('.statechart[data-kind=\"fence\"]')]"
        ".every(f => f.hasAttribute('data-rendered'))" % len(sources)
    )
    page.wait_for_timeout(200)
    return page.evaluate(MEASURE_JS)


def run(
    theme: str,
    widths: Sequence[int],
    shots: Optional[pathlib.Path],
    verbose: bool,
) -> int:
    from playwright.sync_api import sync_playwright

    found = fences()
    if not found:
        print("no fences found")
        return 1
    if shots:
        shots.mkdir(parents=True, exist_ok=True)
    themes = ("light", "dark") if theme == "both" else (theme,)
    errors = warnings = 0
    server, port = cd.serve(ROOT)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for name in themes:
                for width in widths:
                    page = browser.new_page(
                        viewport={"width": width, "height": 900}
                    )
                    data = render(
                        page, [f["source"] for f in found], name, width, port
                    )
                    page_overflow = data["pageOverflow"]
                    for fence, result in zip(found, data["figures"]):
                        where = f"{fence['file']}:{fence['line']} ({fence['kind']})"
                        if result["errors"]:
                            errors += len(result["errors"])
                            print(f"[FAIL] {name} {width}px {where}")
                            for message in result["errors"]:
                                print(f"    error: {message}")
                        if result["warnings"] and verbose:
                            warnings += len(result["warnings"])
                            print(f"[WARN] {name} {width}px {where}")
                            for message in result["warnings"]:
                                print(f"    warn: {message}")
                        elif result["warnings"]:
                            warnings += len(result["warnings"])
                        if shots:
                            slug = (
                                pathlib.Path(fence["file"]).stem
                                + "-"
                                + str(fence["index"])
                            )
                            page.locator('.statechart[data-kind="fence"]').nth(
                                result["index"]
                            ).screenshot(
                                path=str(shots / f"{name}-{width}-{slug}.png")
                            )
                    if page_overflow:
                        errors += 1
                        print(f"[FAIL] {name} {width}px page scrolls sideways")
                    page.close()
            browser.close()
    finally:
        server.shutdown()
    print(
        f"{len(found)} fence(s) checked, {errors} error(s), "
        f"{warnings} warning(s), theme={theme}, widths={','.join(map(str, widths))}"
    )
    return 1 if errors else 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--theme", choices=("both", "light", "dark"), default="both"
    )
    parser.add_argument(
        "--widths", default=",".join(str(w) for w in DEFAULT_WIDTHS)
    )
    parser.add_argument("--shots", type=pathlib.Path)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    widths = tuple(int(w) for w in args.widths.split(",") if w)
    return run(args.theme, widths, args.shots, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
