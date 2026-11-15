"""ALL-07: raster icons at the site root, built from the approved marks."""
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB = PROJECT_ROOT / "web"


def test_favicon_ico_has_16_and_32():
    assert Image.open(WEB / "favicon.ico").info["sizes"] == {(16, 16), (32, 32)}


def test_png_sizes():
    assert Image.open(WEB / "favicon-32.png").size == (32, 32)
    touch = Image.open(WEB / "apple-touch-icon.png")
    assert touch.size == (180, 180)
    assert touch.mode == "RGB", "iOS fills transparent corners with black"


def test_touch_icon_is_the_fjord_tile():
    corner = Image.open(WEB / "apple-touch-icon.png").getpixel((0, 0))
    assert corner == (0x1E, 0x2B, 0x3C)


def test_small_icons_come_from_the_small_mark():
    src = (PROJECT_ROOT / "scripts" / "build_icons.py").read_text(encoding="utf-8")
    assert '"xc-mark-small.svg"' in src and '"xc-mark-fjord.svg"' in src


def test_deploy_ships_them():
    src = (PROJECT_ROOT / "scripts" / "deploy.py").read_text(encoding="utf-8")
    for name in ("favicon.ico", "favicon-32.png", "apple-touch-icon.png"):
        assert f'"{name}"' in src
