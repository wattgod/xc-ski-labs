#!/usr/bin/env python3
"""
XC Ski Labs — trail-map network, preview generator, and design-token tests.

Three things are guarded here:

1. The network drawing is generated from race-data. Its glyphs encode
   course.technical_rating and its trails encode series_membership, so a
   wrong mapping is a factual error on a page, not a cosmetic one.
2. The preview is generated, not hand-written. An earlier cut had a record
   number and a "surveyed on skis" line typed straight into markup for a
   field the schema does not have. These tests assert every rendered value
   round-trips from race-data, and fail if the set of fields we admit are
   NOT backed by data grows without being declared.
3. The accent token was doing three jobs and measured 4.04:1 as small text.
   Contrast is now asserted per direction against that direction's own
   ground, so the palette cannot regress silently.

Run: pytest tests/test_trailmap.py -v
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import trailmap_network as network      # noqa: E402
import trailmap_preview as preview      # noqa: E402

DATA_DIR = ROOT / "race-data"
TEMPLATE = ROOT / "docs" / "brand" / "trailmap-site.template.html"
BUILT = ROOT / "docs" / "brand" / "trailmap-site.html"
MANIFEST = ROOT / "docs" / "brand" / "trailmap-preview-manifest.json"


@pytest.fixture(scope="module")
def races():
    return network.load_races(DATA_DIR)


@pytest.fixture(scope="module")
def svg(races):
    return network.build_network_svg(races)


@pytest.fixture(scope="module")
def built():
    text, manifest = preview.build(DATA_DIR, TEMPLATE)
    return text, manifest


def _series(race):
    s = race.get("series") if "series" in race else race.get("series_membership") or []
    if isinstance(s, dict):
        return [k for k, v in s.items() if v]
    return s or []


# ── network: the drawing is data, not decoration ─────────────────────────────

def test_every_use_reference_resolves(svg):
    """A <use href> with no matching symbol renders nothing at all — an
    invisible node reads as 'this race does not exist'."""
    defs = set(re.findall(r'id="(g-[a-z]+)"', (ROOT / "docs" / "brand" / "trailmap-site.template.html").read_text()))
    used = set(re.findall(r'<use href="#(g-[a-z]+)"', svg))
    assert used - defs == set(), f"unresolved glyph references: {sorted(used - defs)}"


def test_node_count_matches_races_on_marked_trails(races, svg):
    on_trail = {
        slug for slug, race in races.items()
        if any(t["key"] in race["series"] for t in network.TRAILS)
    }
    # 'class="nw-nodes"' is the group wrapper and also matches 'class="nw-node';
    # counting loosely shipped an off-by-one to the database page.
    assert len(re.findall(r'<a class="nw-node ', svg)) == len(on_trail)


def test_ungroomed_tick_count_matches_races_with_no_series(races, svg):
    ungroomed = [r for r in races.values() if not r["series"]]
    assert svg.count('class="nw-un"') == len(ungroomed)
    assert f"{len(ungroomed)} races off the marked trails" in svg


def test_glyph_matches_technical_rating(races, svg):
    """circle 1-2, square 3, diamond 4, double 5 — the trail-signage system."""
    for slug, race in races.items():
        if not any(t["key"] in race["series"] for t in network.TRAILS):
            continue
        match = re.search(rf'nw-x(\d)"[^>]*href="/{re.escape(slug)}/"', svg)
        if not match:
            continue
        assert int(match.group(1)) == (race["tech"] or 0)
    assert 'nw-x4' in svg and 'nw-x2' in svg


def test_unrated_course_gets_dashed_node_not_a_guessed_glyph(races):
    """A race with no technical_rating must not be drawn as 'easiest'."""
    sample = dict(next(iter(races.values())))
    sample.update(slug="unrated-test", name="Unrated Test", tech=None,
                  series=["worldloppet"], tier=3, score=50)
    out = network.build_network_svg({"unrated-test": sample})
    assert "nw-unrated" in out
    assert "<use href=\"#g-circle\"" not in out


def test_layout_is_deterministic(races):
    """Two builds of the same corpus must be byte-identical, or a record
    number printed on a page cannot be reproduced from the data."""
    assert network.build_network_svg(races) == network.build_network_svg(races)


def test_all_geometry_lands_inside_the_canvas(svg):
    for x, y in re.findall(r'transform="translate\((-?[\d.]+) (-?[\d.]+)\)"', svg):
        assert -20 <= float(x) <= network.CANVAS_W + 20
        assert -20 <= float(y) <= network.CANVAS_H + 20


def test_empty_corpus_does_not_crash():
    out = network.build_network_svg({})
    assert "0 races off the marked trails" in out
    assert re.findall(r'<a class="nw-node ', out) == []


# ── preview: every figure traces to a file ───────────────────────────────────

def test_no_unfilled_placeholders(built):
    text, _ = built
    assert re.findall(r"\{\{[A-Z0-9_]+\}\}", text) == []


def test_record_numbers_are_unique_and_deterministic(races):
    profiles = preview.load_races(DATA_DIR)
    first = preview.record_numbers(profiles)
    assert first == preview.record_numbers(profiles)
    assert len(set(first.values())) == len(first)
    assert min(first.values()) == 1 and max(first.values()) == len(profiles)


def test_log_values_round_trip_from_race_data(built):
    """The field record is the Amundsen direction's entire claim. Every row
    marked race-data must be reproducible from the JSON."""
    _, manifest = built
    profiles = preview.load_races(DATA_DIR)
    birken = profiles[preview.FEATURED]
    vitals = birken["vitals"]
    values = manifest["values"]
    assert str(vitals["lat"]) in values[f"{preview.FEATURED}.position"]["value"]
    assert str(vitals["lng"]) in values[f"{preview.FEATURED}.position"]["value"]
    assert f"{vitals['elevation_m']:,}" in values[f"{preview.FEATURED}.ascent"]["value"]
    assert f"{vitals['field_size']:,}" in values[f"{preview.FEATURED}.field"]["value"]
    assert values[f"{preview.FEATURED}.cutoff"]["value"] == vitals["cutoff_time"]
    assert values[f"{preview.FEATURED}.first_held"]["value"] == vitals["founded"]


def test_proposed_fields_are_declared_and_have_not_grown(built):
    """These fields do NOT exist in race-data. The provenance treatment cannot
    ship until a migration adds them. If this list grows, something was
    invented in markup again."""
    _, manifest = built
    assert manifest["proposed_fields"] == [
        "fact_checked_on", "note_method", "note_written_on",
        "source_count", "surveyed_how", "surveyed_on",
    ]
    for name, entry in manifest["values"].items():
        assert entry["source"] in {"race-data", "derived", "proposed"}
        if entry["source"] == "proposed":
            assert name.endswith(".surveyed"), name


def test_race_without_provenance_renders_the_unvisited_state(built):
    """~220 of 229 races are in this state. It has to be first-class."""
    text, _ = built
    assert 'class="stamp none"' in text
    assert "Not visited" in text
    assert "Note pending a visit" in text


def test_missing_vital_renders_as_not_recorded_never_omitted(built):
    """Gantrisch has no cutoff and no founding year. An absent field is
    information; dropping the row would hide that we do not know."""
    text, _ = built
    gantrisch = text[text.index('id="r-gantrisch"'):]
    assert gantrisch.count('class="unset">Not recorded') >= 2
    assert "{{" not in gantrisch


def test_both_race_sheets_have_a_field_record(built):
    """The Gantrisch log was silently missing from the hand-written mock —
    the Amundsen direction rendered that race with no record block at all."""
    text, _ = built
    for anchor in ('id="r-birken"', 'id="r-gantrisch"'):
        sheet = text[text.index(anchor):text.index("</article>", text.index(anchor))]
        assert '<div class="log">' in sheet, f"{anchor} has no field record"
        assert "<dt>Record</dt>" in sheet


def test_corpus_stats_match_the_data(built):
    text, manifest = built
    profiles = preview.load_races(DATA_DIR)
    assert manifest["values"]["stat.races"]["value"] == len(profiles)
    ungroomed = [r for r in profiles.values() if not _series(r)]
    assert manifest["values"]["stat.ungroomed"]["value"] == len(ungroomed)
    assert f"{len(profiles)} races" in text


def test_committed_build_is_current(built):
    """A stale checked-in build is the divergence this generator exists to
    prevent."""
    text, manifest = built
    assert BUILT.read_text(encoding="utf-8") == text
    assert json.loads(MANIFEST.read_text(encoding="utf-8"))["values"] == manifest["values"]


# ── design tokens: contrast, per direction, against its own ground ───────────

def _luminance(hex_colour: str) -> float:
    hex_colour = hex_colour.lstrip("#")
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(a: str, b: str) -> float:
    la, lb = _luminance(a), _luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _tokens(css: str, selector: str) -> dict[str, str]:
    match = re.search(re.escape(selector) + r"\s*\{(.*?)\}", css, re.S)
    assert match, f"token block not found: {selector}"
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{6})", match.group(1)))


@pytest.fixture(scope="module")
def css():
    return BUILT.read_text(encoding="utf-8")


DIRECTIONS = [
    ("paper", ":root"),
    ("amundsen", ':root[data-dir="amundsen"]'),
    ("ralph", ':root[data-dir="ralph"]'),
]


@pytest.mark.parametrize("name,selector", DIRECTIONS)
def test_text_tokens_meet_wcag_aa_on_their_own_ground(css, name, selector):
    """--accent-ink shipped at 4.04:1 once. Never again, in any direction."""
    base = _tokens(css, ":root")
    tokens = {**base, **(_tokens(css, selector) if selector != ":root" else {})}
    ground = tokens["--paper"]
    for token in ("--ink", "--ink-2", "--ink-3", "--accent-ink"):
        ratio = contrast(tokens[token], ground)
        assert ratio >= 4.5, f"{name} {token} is {ratio:.2f}:1 on {ground}, needs 4.5"


@pytest.mark.parametrize("name,selector", DIRECTIONS)
def test_text_on_the_accent_fill_is_readable(css, name, selector):
    base = _tokens(css, ":root")
    tokens = {**base, **(_tokens(css, selector) if selector != ":root" else {})}
    ratio = contrast(tokens["--accent-on"], tokens["--accent"])
    assert ratio >= 4.5, f"{name} accent-on is {ratio:.2f}:1 on the accent fill"


def test_difficulty_glyphs_are_perceivable_as_marks(css):
    """Glyph strokes are non-text UI, so 3:1 — but they carry
    course.technical_rating, so they cannot be decorative-faint."""
    base = _tokens(css, ":root")
    signage = dict(re.findall(r"(--c-(?:easy|more)):\s*(#[0-9a-fA-F]{6})",
                              css[css.index(':root[data-color="signage"]'):][:400]))
    for token, value in signage.items():
        ratio = contrast(value, base["--paper-lit"])
        assert ratio >= 3.0, f"{token} is {ratio:.2f}:1 on paper-lit, needs 3.0"


def test_accent_is_not_reused_as_body_text_colour(css):
    """The original bug: one token used as both a fill and small text."""
    assert "--accent-ink" in css and "--accent-on" in css
    assert re.search(r"\.kick\{[^}]*color:var\(--c-kick\)", css) or "--c-kick:var(--accent-ink)" in css
