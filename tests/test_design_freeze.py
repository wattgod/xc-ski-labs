"""Design freeze: ratchets that prevent banned patterns from growing.

These are NOT cleanup tests. The existing occurrences are grandfathered in;
the assertions pin the count at its current level so new ones cannot be
added without someone deliberately raising the constant.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Source globs only. Anything under output/ is generated and is never counted.
SOURCE_GLOBS = (
    "scripts/*.py",
    "wordpress/*.py",
    "web/*.html",
    "tokens/*.css",
)

# Measured on the tam-phase0 branch. A prior audit reported 13; the actual
# measured figure is 17 (the audit appears to have excluded the five
# `border-left-color` longhands). Raising this number means you are adding a
# colored side rule -- the owner has a standing ban on those, with a narrow
# exception for true prose blockquotes. See docs/BRAND_GUIDELINES.md section 5.
MAX_BORDER_LEFT = 17

BORDER_LEFT_RE = re.compile(r"border-left")


def _source_files():
    files = []
    for pattern in SOURCE_GLOBS:
        files.extend(sorted(REPO_ROOT.glob(pattern)))
    return [f for f in files if "output" not in f.parts]


def count_border_left():
    """Return {relative path: occurrence count} for every source file with a hit."""
    counts = {}
    for path in _source_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = len(BORDER_LEFT_RE.findall(text))
        if hits:
            counts[str(path.relative_to(REPO_ROOT))] = hits
    return counts


def test_source_files_are_discoverable():
    """Guard the guard: if the globs stop matching, the ratchet is vacuous."""
    files = _source_files()
    assert len(files) > 20, f"expected to scan many source files, found {len(files)}"


def test_border_left_does_not_grow():
    counts = count_border_left()
    total = sum(counts.values())
    assert total <= MAX_BORDER_LEFT, (
        f"border-left count rose to {total}, above the frozen maximum of "
        f"{MAX_BORDER_LEFT}. Colored side rules are banned outside true prose "
        f"blockquotes; use a mono label plus spacing instead.\n"
        f"Per-file: {counts}"
    )


def test_output_directory_is_never_counted():
    assert all("output" not in f.parts for f in _source_files())


def test_race_pages_and_prep_kit_ship_the_radius_shadow_reset():
    """The 467 highest-traffic pages must carry the same reset the
    WordPress generators use (neo-brutalist: no radius, no shadow)."""
    for name in ("generate_race_pages.py", "generate_prep_kit.py"):
        text = (REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
        assert "border-radius: 0 !important" in text, f"{name} missing border-radius reset"
        assert "box-shadow: none !important" in text, f"{name} missing box-shadow reset"


# ── Selected / hover states must survive the global reset ──────────────


def _race_pages_css():
    return (REPO_ROOT / "scripts" / "generate_race_pages.py").read_text(encoding="utf-8")


def test_selected_rating_tile_uses_solid_signal_background():
    """A selected state must read as deliberate at a glance: solid signal
    background, high-contrast text. Pale tints are rejected, and the old
    red inset LEFT bar is a banned side strip -- it must not come back."""
    css = _race_pages_css()
    rule = '.gl-rating-tile[aria-pressed="true"] {{ background: var(--gl-swix-red); color: var(--gl-white); }}'
    assert rule in css, "selected rating tile lost its solid signal background"
    assert "inset 5px 0 0" not in css, "banned red inset left strip was reintroduced"


def test_hover_underlines_survive_the_box_shadow_reset():
    """The klister hover underlines are underlines, not side strips, so they
    are allowed -- but they must not be drawn with box-shadow, which the
    global `box-shadow: none !important` reset strips."""
    css = _race_pages_css()
    for selector in (".gl-breakdown-tile:hover", ".gl-related-card:hover"):
        start = css.index(selector + " {{")
        body = css[start:css.index("}}", start)]
        assert "var(--gl-klister)" in body, f"{selector} lost its klister underline"
        assert "box-shadow" not in body, f"{selector} underline would be stripped by the reset"


def test_no_inset_box_shadow_marks_remain_in_race_page_css():
    """Any inset mark is dead on arrival under the global reset."""
    assert "box-shadow: inset" not in _race_pages_css()
