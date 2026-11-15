"""The live site runs the Sledge Stores book (docs/brand/sledge-stores).

tokens/tokens.css is built from the book's tokens.json and bundle.css by
scripts/build_brand_tokens.py; every page generator embeds it, and every page
loads the book's three families and the approved small mark as its favicon.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_brand_tokens  # noqa: E402
from brand_head import BRAND_FONT_URL  # noqa: E402

BOOK = ROOT / "docs" / "brand" / "sledge-stores"
OUTPUT = ROOT / "output"
RETIRED_FACES = ("Sometype", "Source+Serif", "Source Serif", "family=Inter")


def test_tokens_css_is_built_from_the_book():
    assert build_brand_tokens.main(["--check"]) == 0


def test_every_book_colour_is_a_variable():
    css = (ROOT / "tokens" / "tokens.css").read_text(encoding="utf-8")
    tokens = build_brand_tokens.load_tokens()
    for tok in tokens["color"]["tokens"]:
        name = tok["name"]
        assert f"--xc-light-{name}: {tok['value']['light'].lower()};" in css
        assert f"--xc-dark-{name}: {tok['value']['dark'].lower()};" in css
        assert f"--{name}: var(--xc-light-{name});" in css


def test_hex_literals_live_only_in_the_raw_theme_values():
    css = (ROOT / "tokens" / "tokens.css").read_text(encoding="utf-8")
    for line in css.splitlines():
        if re.search(r"#[0-9a-fA-F]{3,8}\b", line):
            assert re.match(r"\s*--xc-(light|dark)-[a-z0-9-]+: #[0-9a-f]{6,8};$", line), line


def test_retired_print_palette_is_gone():
    css = (ROOT / "tokens" / "tokens.css").read_text(encoding="utf-8")
    for retired in ("#f0e8d8", "#202822", "#a83d2d", "#efc65f", "#315f70", "#654a68"):
        assert retired not in css.lower()


def test_component_previews_link_the_tokens():
    previews = sorted((BOOK / "components").glob("*/preview.html"))
    assert previews
    for preview in previews:
        html = preview.read_text(encoding="utf-8")
        assert 'href="../../../../../tokens/tokens.css"' in html, preview
        assert (preview.parent / "../../../../../tokens/tokens.css").resolve().exists()


def test_site_marks_are_the_book_marks():
    assert (ROOT / "web" / "favicon.svg").read_bytes() == (BOOK / "logos" / "xc-mark-small.svg").read_bytes()
    assert (ROOT / "web" / "xc-logo.svg").read_bytes() == (BOOK / "logos" / "xc-mark-wool.svg").read_bytes()


def test_deploy_uploads_the_favicon():
    deploy = (ROOT / "scripts" / "deploy.py").read_text(encoding="utf-8")
    assert '"favicon.svg"' in deploy


def _generator_sources():
    files = sorted((ROOT / "scripts").glob("generate_*.py")) + sorted((ROOT / "wordpress").glob("generate_*.py"))
    files.append(ROOT / "web" / "nordic-lab-search.html")
    return files


@pytest.mark.parametrize("path", _generator_sources(), ids=lambda p: p.name)
def test_generators_load_only_the_book_faces(path):
    src = path.read_text(encoding="utf-8")
    for face in RETIRED_FACES:
        assert face not in src, f"{path.name} still loads {face}"
    for url in re.findall(r"https://fonts\.googleapis\.com/css2\?[^\"'\s]*", src):
        assert url == BRAND_FONT_URL, f"{path.name}: {url}"
    assert 'href="/xc-logo.svg">' not in src or 'rel="icon"' not in src.split('href="/xc-logo.svg">')[0][-80:]


def _built_pages():
    if not OUTPUT.exists():
        return []
    return [p for p in OUTPUT.rglob("index.html") if p.parent.parent == OUTPUT or p.parent == OUTPUT]


def test_built_pages_use_the_favicon_and_fonts():
    pages = _built_pages()
    if not pages:
        pytest.skip("output/ not generated")
    for page in pages:
        html = page.read_text(encoding="utf-8")
        if "<head" not in html:
            continue
        rel = page.relative_to(OUTPUT)
        assert 'href="/favicon.svg"' in html, f"{rel}: no favicon"
        if "fonts.googleapis.com" in html:
            assert BRAND_FONT_URL.replace("&", "&amp;") in html or BRAND_FONT_URL in html, f"{rel}: other font URL"
        for face in RETIRED_FACES:
            assert face not in html, f"{rel}: loads {face}"
