#!/usr/bin/env python3
"""
XC Ski Labs -- generate the trail-map design preview from race-data.

Why this exists: the first cut of the preview had race figures typed by hand
into the markup -- a record number, coordinates, an ascent, and a "surveyed
14 March 2026, on skis" line. Some of those matched race-data and some were
invented. On the Amundsen direction, whose whole argument is that the page is
a field record, a fabricated survey line is not a placeholder, it is the exact
failure the design claims to prevent. So the preview is generated now, and
anything the schema cannot back is declared in PROPOSED_SCHEMA below rather
than quietly written into HTML.

Every rendered value is recorded in a manifest with its provenance
("race-data" or "proposed"), and tests/test_trailmap.py asserts that the
race-data values round-trip and that the proposed set has not grown.

Usage:
    python trailmap_preview.py
    python trailmap_preview.py --template ... --out ... --manifest ...
"""

import argparse
import glob
import html
import json
import math
from pathlib import Path
from typing import Any, Optional

from trailmap_network import build_network_svg, load_races as load_network_races

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = ROOT / "race-data"
DEFAULT_TEMPLATE = ROOT / "docs" / "brand" / "trailmap-site.template.html"
DEFAULT_OUT = ROOT / "docs" / "brand" / "trailmap-site.html"
DEFAULT_MANIFEST = ROOT / "docs" / "brand" / "trailmap-preview-manifest.json"

# Races the preview renders in full.
FEATURED = "birkebeinerrennet"      # tier 1, written note, provenance present
EMPTY_STATE = "gantrisch-loppet"    # tier 4, no note, provenance absent

# ─────────────────────────────────────────────────────────────────────────────
# PROPOSED SCHEMA
#
# None of these fields exist in race-data/*.json today. The provenance
# treatment ("Someone's Copy") and the Amundsen field record both depend on
# them, so the port CANNOT ship those directions until a migration adds them.
# They live here, declared and named, so that (a) nothing is invented inside
# markup and (b) a test fails the moment this set grows.
#
# Required columns, per race:
#   surveyed_on      date | null   -- when someone from the Labs was there
#   surveyed_how     text | null   -- "on skis", "in person", "desk-checked"
#   fact_checked_on  date | null   -- last verification pass
#   source_count     int  | null   -- citations backing the profile
#   note_written_on  date | null   -- when the groomer's note was written
#   note_method      text | null   -- how the note was researched
# A race with these null renders the dashed "not visited" state, which is the
# state ~220 of 229 races are actually in.
# ─────────────────────────────────────────────────────────────────────────────
PROPOSED_SCHEMA = {
    "birkebeinerrennet": {
        "surveyed_on": "2026-03-14",
        "surveyed_how": "on skis",
        "fact_checked_on": "2026-03-14",
        "source_count": 11,
        "note_written_on": "2026-03",
        "note_method": "course walked, organiser interviewed",
    },
    "gantrisch-loppet": {
        "surveyed_on": None,
        "surveyed_how": None,
        "fact_checked_on": "2026-01-15",
        "source_count": 3,
        "note_written_on": None,
        "note_method": None,
    },
}
PROPOSED_FIELD_NAMES = sorted(
    {k for race in PROPOSED_SCHEMA.values() for k in race}
)

CRITERIA = [
    ("prestige", "Prestige"), ("field_size", "Field size"),
    ("international_draw", "International draw"), ("snow_reliability", "Snow reliability"),
    ("grooming_quality", "Grooming"), ("community", "Community"),
    ("organization", "Organization"), ("competitive_depth", "Competitive depth"),
    ("distance", "Distance"), ("elevation", "Elevation"),
    ("course_technicality", "Course technicality"), ("accessibility", "Accessibility"),
    ("scenery", "Scenery"), ("altitude", "Altitude"),
]
GLYPH_FOR_TECH = {1: "circle", 2: "circle", 3: "square", 4: "diamond", 5: "dbldiamond"}
DIFF_CLASS = {1: "x1", 2: "x2", 3: "x3", 4: "x4", 5: "x5"}
DISCIPLINE = {"classic": "classic", "skate": "skate", "both": "skate and classic"}


def esc(value: Any) -> str:
    """HTML-escape. None and empty both collapse to ''."""
    if value is None or value == "":
        return ""
    return html.escape(str(value))


def load_races(data_dir: Path) -> dict[str, dict]:
    races: dict[str, dict] = {}
    for path in sorted(glob.glob(str(data_dir / "*.json"))):
        if "_schema" in path:
            continue
        races[json.loads(Path(path).read_text(encoding="utf-8"))["race"]["slug"]] = \
            json.loads(Path(path).read_text(encoding="utf-8"))["race"]
    return races


def record_numbers(races: dict[str, dict]) -> dict[str, int]:
    """Stable 1-based record number: score descending, slug as tiebreak.

    Deterministic so the same corpus always numbers the same way, and so a
    record number printed on a page can be reproduced from the data alone.
    """
    ordered = sorted(
        races.values(),
        key=lambda r: (-(((r.get("nordic_lab_rating") or {}).get("overall_score")) or 0), r["slug"]),
    )
    return {race["slug"]: i + 1 for i, race in enumerate(ordered)}


def _fmt_int(value: Any) -> Optional[str]:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return None


def _fmt_km(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    number = float(value)
    return f"{number:g} km"


# ── fragment builders ────────────────────────────────────────────────────────

def build_chips(race: dict, log: list[dict]) -> str:
    """Chips for the Paper/Ralph directions. A missing field renders dashed,
    never omitted — an absent cutoff is information."""
    out = []
    for row in log:
        if not row["chip"]:
            continue
        if row["value"] is None:
            out.append(f'<span class="chip unknown">{esc(row["label"])} unknown</span>')
        else:
            out.append(f'<span class="chip">{esc(row["chip_text"] or row["value"])}</span>')
    return "\n            ".join(out)


def build_log_rows(race: dict, recno: int, total: int, proposed: dict) -> list[dict]:
    """The field record. Every row names where it came from."""
    v = race.get("vitals") or {}
    c = race.get("course") or {}
    lat, lng = v.get("lat"), v.get("lng")
    position = (f"{abs(lat):.4f} {'N' if lat >= 0 else 'S'}, "
                f"{abs(lng):.4f} {'E' if lng >= 0 else 'W'}") if lat is not None and lng is not None else None
    distance = _fmt_km(v.get("distance_km"))
    discipline = DISCIPLINE.get(v.get("discipline"), v.get("discipline"))
    ascent = _fmt_int(v.get("elevation_m"))
    high = _fmt_int(v.get("altitude_m"))
    field = _fmt_int(v.get("field_size"))
    surveyed_on, surveyed_how = proposed.get("surveyed_on"), proposed.get("surveyed_how")
    surveyed = f"{surveyed_on} · {surveyed_how}" if surveyed_on and surveyed_how else None

    return [
        dict(label="Record", value=f"{recno:03d} of {total}", src="derived", chip=False, chip_text=None),
        dict(label="Position", value=position, src="race-data", chip=False, chip_text=None),
        dict(label="Route", value=(f"{v.get('location')}, {c.get('format', '').replace('-', ' ')}".strip(", ")
                                   if v.get("location") else None),
             src="race-data", chip=False, chip_text=None),
        dict(label="Distance", value=(f"{distance}, {discipline}" if distance else None),
             src="race-data", chip=True, chip_text=distance),
        dict(label="Discipline", value=discipline, src="race-data", chip=True, chip_text=discipline),
        dict(label="Ascent", value=(f"{ascent} m · high point {high} m" if ascent and high
                                    else (f"{ascent} m" if ascent else None)),
             src="race-data", chip=True, chip_text=(f"{ascent} m" if ascent else None)),
        dict(label="Field", value=(f"{field} starters" if field else None),
             src="race-data", chip=True, chip_text=(f"{field} starters" if field else None)),
        dict(label="Cutoff", value=v.get("cutoff_time"), src="race-data", chip=True, chip_text=v.get("cutoff_time")),
        dict(label="First held", value=v.get("founded"), src="race-data", chip=False, chip_text=None),
        dict(label="Surveyed", value=surveyed, src="proposed", chip=False, chip_text=None),
    ]


def render_log(rows: list[dict]) -> str:
    parts = []
    for row in rows:
        if row["value"] is None:
            parts.append(f'<dt>{esc(row["label"])}</dt><dd class="unset">Not recorded</dd>')
        else:
            parts.append(f'<dt>{esc(row["label"])}</dt><dd>{esc(row["value"])}</dd>')
    return ('<div class="log">\n            <dl>\n              '
            + "\n              ".join(parts) + "\n            </dl>\n          </div>")


def render_recno(recno: int, total: int, proposed: dict) -> str:
    surveyed = proposed.get("surveyed_on")
    tail = f"surveyed {surveyed}" if surveyed else "not visited"
    return f'<p class="recno">Record {recno:03d} of {total} &#183; {esc(tail)}</p>'


def render_stamp(proposed: dict) -> str:
    checked = proposed.get("fact_checked_on")
    if proposed.get("surveyed_on") and checked:
        pretty = " &#183; ".join(reversed(checked.split("-")))
        return f'<div class="stamp"><b>Verified</b><span>{pretty}</span></div>'
    return '<div class="stamp none"><b>Not visited</b><span>Desk-checked only</span></div>'


def render_criteria(race: dict) -> str:
    rating = race.get("nordic_lab_rating") or {}
    scored = [(label, rating.get(key)) for key, label in CRITERIA]
    scored = [(label, int(value)) for label, value in scored if isinstance(value, (int, float))]
    scored.sort(key=lambda pair: -pair[1])
    parts = []
    for label, value in scored:
        rungs = "".join(f'<i class="rung{"" if i < value else " off"}"></i>' for i in range(5))
        parts.append(f'<div class="critrow"><span>{esc(label)}</span>'
                     f'<span class="ladder" role="img" aria-label="{value} of 5">{rungs}</span></div>')
    return "\n        ".join(parts)


def render_rows(races: list[dict], show_series: bool = False) -> str:
    parts = []
    for race in races:
        v = race.get("vitals") or {}
        rating = race.get("nordic_lab_rating") or {}
        tech = (race.get("course") or {}).get("technical_rating")
        glyph = GLYPH_FOR_TECH.get(tech)
        cls = DIFF_CLASS.get(tech, "")
        width = ' style="width:1.5em"' if glyph == "dbldiamond" else ""
        mark = (f'<svg class="glyph" aria-hidden="true"{width}><use href="#g-{glyph}"/></svg>'
                if glyph else '<span aria-hidden="true">&ndash;</span>')
        meta = [v.get("country"), _fmt_km(v.get("distance_km")), DISCIPLINE.get(v.get("discipline"))]
        if show_series:
            series = race.get("series_membership") or []
            if isinstance(series, dict):
                series = [k for k, val in series.items() if val]
            if series:
                meta.append(series[0].replace("_", " ").title())
        tier = rating.get("tier") or 4
        parts.append(
            f'<a class="row" href="/{esc(race["slug"])}/">'
            f'<span class="diff {cls}">{mark}</span>'
            f'<span><span class="rname">{esc(race.get("display_name") or race["name"])}</span>'
            f'<span class="rmeta">{esc(" · ".join(m for m in meta if m))}</span></span>'
            f'<span class="tier{" t1" if tier == 1 else ""}">T{tier}</span>'
            f'<span class="sc">{rating.get("overall_score") or 0}</span></a>')
    return "\n      ".join(parts)


def render_sources(race: dict, proposed: dict) -> str:
    rating = race.get("nordic_lab_rating") or {}
    bits = [f'{rating.get("overall_score")} of 100 &#183; Tier {rating.get("tier")}']
    count = proposed.get("source_count")
    bits.append(f"{count} sources cited" if count else "Sources not yet counted")
    checked = proposed.get("fact_checked_on")
    bits.append(f"Fact-checked {checked}" if checked else "Not fact-checked")
    if not proposed.get("surveyed_on"):
        bits.append("Note pending a visit")
    return "".join(f"<span>{b}</span>" for b in bits)


# ── assembly ─────────────────────────────────────────────────────────────────

def build(data_dir: Path, template: Path) -> tuple[str, dict]:
    races = load_races(data_dir)
    if FEATURED not in races or EMPTY_STATE not in races:
        raise SystemExit(f"missing required race profile: {FEATURED} / {EMPTY_STATE}")
    total = len(races)
    recnos = record_numbers(races)
    ranked = sorted(races.values(),
                    key=lambda r: (-(((r.get("nordic_lab_rating") or {}).get("overall_score")) or 0), r["slug"]))
    tier_ones = [r for r in ranked if (r.get("nordic_lab_rating") or {}).get("tier") == 1]

    def series_of(race):
        s = race.get("series_membership") or []
        return [k for k, v in s.items() if v] if isinstance(s, dict) else s

    ungroomed = [r for r in races.values() if not series_of(r)]
    marked_series = {s for r in races.values() for s in series_of(r)}

    manifest: dict[str, Any] = {"generated_from": str(data_dir.name), "race_count": total,
                                "proposed_fields": PROPOSED_FIELD_NAMES, "values": {}}

    def record(key: str, value: Any, src: str) -> Any:
        manifest["values"][key] = {"value": value, "source": src}
        return value

    fields: dict[str, str] = {}
    net = build_network_svg(load_network_races(data_dir))
    fields["NETWORK"] = net

    fields["STAT_RACES"] = str(record("stat.races", total, "race-data"))
    fields["STAT_CRITERIA"] = str(record("stat.criteria", len(CRITERIA), "derived"))
    fields["STAT_SERIES"] = str(record("stat.series", len(marked_series), "race-data"))
    fields["STAT_T1"] = str(record("stat.tier_one", len(tier_ones), "race-data"))
    fields["UNGROOMED"] = str(record("stat.ungroomed", len(ungroomed), "race-data"))
    fields["TIER_COUNTS"] = " &#183; ".join(
        f"{sum(1 for r in races.values() if (r.get('nordic_lab_rating') or {}).get('tier') == t)} T{t}"
        for t in (1, 2, 3, 4))
    fields["ROWS_TIER1"] = render_rows(tier_ones)
    fields["ROWS_DB"] = render_rows(ranked[:8] + [races[EMPTY_STATE]], show_series=True)
    fields["TIER1_COUNT"] = str(len(tier_ones))
    fields["DB_RESULTS"] = str(total)
    # Counted from the data, not from the markup: 'class="nw-nodes"' (the group
    # wrapper) also matches 'class="nw-node', which shipped an off-by-one to the
    # database page for several revisions.
    trail_keys = {t["key"] for t in __import__("trailmap_network").TRAILS}
    on_trail = {slug for slug, r in races.items() if trail_keys & set(series_of(r))}
    fields["NETWORK_PLACED"] = str(record("stat.on_marked_trails", len(on_trail), "race-data"))

    for tag, slug in (("BIRKEN", FEATURED), ("GANTRISCH", EMPTY_STATE)):
        race = races[slug]
        proposed = PROPOSED_SCHEMA.get(slug, {})
        log_rows = build_log_rows(race, recnos[slug], total, proposed)
        for row in log_rows:
            record(f"{slug}.{row['label'].lower().replace(' ', '_')}", row["value"], row["src"])
        v = race.get("vitals") or {}
        fields[f"{tag}_NAME"] = esc(race.get("display_name") or race["name"])
        fields[f"{tag}_TAGLINE"] = esc(race.get("tagline"))
        fields[f"{tag}_KICKER"] = esc(" · ".join(
            x for x in [", ".join(s.replace("_", " ").title() for s in series_of(race)) or None,
                        v.get("country"),
                        f"since {v.get('founded')}" if v.get("founded") else None] if x))
        fields[f"{tag}_CHIPS"] = build_chips(race, log_rows)
        fields[f"{tag}_LOG"] = render_log(log_rows)
        fields[f"{tag}_RECNO"] = render_recno(recnos[slug], total, proposed)
        fields[f"{tag}_STAMP"] = render_stamp(proposed)
        fields[f"{tag}_CRIT"] = render_criteria(race)
        fields[f"{tag}_SOURCES"] = render_sources(race, proposed)
        fields[f"{tag}_SCORE"] = str((race.get("nordic_lab_rating") or {}).get("overall_score"))
        fields[f"{tag}_CRITCOUNT"] = str(len(CRITERIA))
        note_on, note_how = proposed.get("note_written_on"), proposed.get("note_method")
        fields[f"{tag}_NOTEBY"] = (f"<span>Written {esc(note_on)}</span><span>{esc(note_how)}</span>"
                                   if note_on and note_how else "")

    text = template.read_text(encoding="utf-8")
    for key, value in fields.items():
        text = text.replace("{{" + key + "}}", value)
    leftover = sorted(set(__import__("re").findall(r"\{\{([A-Z0-9_]+)\}\}", text)))
    if leftover:
        raise SystemExit(f"unfilled template placeholders: {leftover}")
    return text, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    text, manifest = build(args.data_dir, args.template)
    args.out.write_text(text, encoding="utf-8")
    args.manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    proposed = sum(1 for v in manifest["values"].values() if v["source"] == "proposed")
    print(f"wrote {args.out} ({len(text):,} bytes)")
    print(f"wrote {args.manifest} — {len(manifest['values'])} values, {proposed} from proposed schema")


if __name__ == "__main__":
    main()
