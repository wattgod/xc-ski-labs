#!/usr/bin/env python3
"""Build the raster site icons from the Sledge Stores marks (sweep ALL-07).

Browsers and iOS ask for /favicon.ico and /apple-touch-icon.png directly,
whatever the page links. Sources (docs/brand/sledge-stores/logos/):
- favicon.ico (16 + 32) and favicon-32.png: the small mark, which the book
  requires for favicons and app icons up to 32px (approved 2026-11-14).
- apple-touch-icon.png (180): the fjord mark, the colourway for avatars on
  wool and oat. Its tile is drawn square here because iOS rounds the corners
  itself and fills transparent corners with black.

Needs rsvg-convert (librsvg) and Pillow. Output goes to web/.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGOS = PROJECT_ROOT / "docs" / "brand" / "sledge-stores" / "logos"
WEB = PROJECT_ROOT / "web"
SMALL = LOGOS / "xc-mark-small.svg"
FJORD = LOGOS / "xc-mark-fjord.svg"


def render(svg: str, size: int, out: Path) -> Path:
    with tempfile.NamedTemporaryFile("w", suffix=".svg", delete=False) as fh:
        fh.write(svg)
        src = fh.name
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", str(out), src], check=True)
    Path(src).unlink()
    return out


def square_tile(svg: str) -> str:
    """Drop the tile's corner radius (only the first rect is the tile)."""
    head, sep, tail = svg.partition('<rect width="300" height="300" rx="28"')
    if not sep:
        raise SystemExit("fjord mark changed: tile rect not found")
    return head + '<rect width="300" height="300"' + tail


def main() -> int:
    if not shutil.which("rsvg-convert"):
        print("rsvg-convert not found (brew install librsvg)", file=sys.stderr)
        return 1
    small = SMALL.read_text(encoding="utf-8")
    fjord = square_tile(FJORD.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        p16 = Image.open(render(small, 16, tmp / "16.png")).convert("RGBA")
        p32 = Image.open(render(small, 32, tmp / "32.png")).convert("RGBA")
        p32.save(WEB / "favicon-32.png", optimize=True)
        p32.save(WEB / "favicon.ico", format="ICO", sizes=[(16, 16), (32, 32)], append_images=[p16])
        touch = Image.open(render(fjord, 180, tmp / "180.png")).convert("RGB")
        touch.save(WEB / "apple-touch-icon.png", optimize=True)
    for name in ("favicon.ico", "favicon-32.png", "apple-touch-icon.png"):
        print(f"Wrote web/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
