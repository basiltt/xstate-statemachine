"""Re-capture the README diagrams from the public Stately project.

Usage:  python docs/assets/images/machines/capture.py [name ...]

Each chart is opened in the Stately *embed* view with ``colorMode=dark`` at
3x device pixels, the canvas is fitted to the viewport, the chrome (header,
simulate bar) is hidden, and the screenshot is auto-cropped to the drawing
plus a margin.  The machine ids live in ``links.json`` next to this file;
they are the same ids the README links to under every image.
"""

import json
import pathlib
import sys

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

HERE = pathlib.Path(__file__).parent
LINKS = json.loads((HERE / "links.json").read_text())
PROJECT = LINKS["project"]
SCALE = 3  # 📝 HD: 3 device pixels per CSS pixel
BG = (16, 17, 25)  # Stately dark canvas
MARGIN = 48 * SCALE
VIEWPORT = (1600, 1200)

HIDE_CHROME = """
() => {
  const hide = el => { if (el) el.style.visibility = 'hidden'; };
  // Header: "Edit this machine in Stately"
  for (const a of document.querySelectorAll('a')) {
    if ((a.innerText || '').includes('Edit this machine')) {
      hide(a.parentElement);
    }
  }
  // Bottom-right toolbar (Simulate / zoom / fit) and the Stately badge:
  // anything fixed/absolute-positioned hugging the bottom-right corner.
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    if (cs.position !== 'fixed' && cs.position !== 'absolute') continue;
    const b = el.getBoundingClientRect();
    if (b.width === 0 || b.width > innerWidth * 0.5) continue;
    if (el.closest('[data-viz], svg, canvas')) continue;
    if (el.querySelector('[data-viz="edge"], path')) {
      const sim = (el.innerText || '').trim() === 'Simulate';
      if (!sim && !el.closest('button')) continue;
    }
    const corner = b.bottom > innerHeight - 80 && b.right > innerWidth - 400;
    if (corner && b.top > innerHeight - 160) hide(el);
  }
}
"""


def embed_url(machine_id: str) -> str:
    return (
        f"https://stately.ai/registry/editor/embed/{PROJECT}"
        f"?mode=design&colorMode=dark&machineId={machine_id}"
    )


def autocrop(path: pathlib.Path) -> None:
    im = Image.open(path).convert("RGB")
    # 📝 Flatten the faint grid so only the drawing counts as content.
    bg = Image.new("RGB", im.size, BG)
    diff = (
        ImageChops.difference(im, bg)
        .convert("L")
        .point(lambda v: 255 if v > 40 else 0)
    )
    box = diff.getbbox()
    if not box:
        return
    l, t, r, b = box
    box = (
        max(0, l - MARGIN),
        max(0, t - MARGIN),
        min(im.width, r + MARGIN),
        min(im.height, b + MARGIN),
    )
    im.crop(box).save(path, optimize=True)


def capture(page, name: str, machine_id: str) -> None:
    w, h = VIEWPORT
    page.set_viewport_size({"width": w, "height": h})
    page.goto(embed_url(machine_id), wait_until="load", timeout=90_000)
    page.wait_for_timeout(6000)
    page.evaluate(HIDE_CHROME)
    page.mouse.click(20, h // 2)  # focus the canvas on empty space
    page.keyboard.press("Shift+1")
    page.wait_for_timeout(2000)
    page.mouse.move(0, 0)
    page.evaluate(HIDE_CHROME)
    out = HERE / f"{name}.png"
    page.screenshot(path=str(out), full_page=False)
    autocrop(out)
    im = Image.open(out)
    print(f"✅ {name}.png {im.size}  <- {machine_id}")


def main(argv) -> None:
    names = argv or list(LINKS["machines"])
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            device_scale_factor=SCALE, color_scheme="dark"
        )
        page = ctx.new_page()
        for name in names:
            capture(page, name, LINKS["machines"][name])
        browser.close()


if __name__ == "__main__":
    main(sys.argv[1:])
