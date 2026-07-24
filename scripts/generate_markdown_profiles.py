#!/usr/bin/env python3
"""Generate machine-readable Markdown profiles for all races.

Produces web/markdown/{slug}.md for each race with YAML frontmatter
and structured sections. Designed for AI agents, scrapers, and the
llmstxt.org ecosystem.

Modeled on the road repo's scripts/generate_markdown_profiles.py, adapted
to XC Ski Labs' race-data/*.json schema (nordic_lab_rating, 14 criteria,
no separate index-file fallback needed — every profile carries its own
rating and vitals directly).

Usage:
    python scripts/generate_markdown_profiles.py           # Generate all
    python scripts/generate_markdown_profiles.py --dry-run  # Preview only
    python scripts/generate_markdown_profiles.py --slug vasaloppet  # Single race
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
OUTPUT_DIR = PROJECT_ROOT / "web" / "markdown"
SITE_URL = "https://xcskilabs.com"

# Order matches CLAUDE.md's Scoring System section and generate_race_pages.py's
# RATING_CRITERIA — 14 criteria, denominator 70, no bonus criterion.
CRITERIA = [
    ("distance", "Distance"),
    ("elevation", "Elevation"),
    ("altitude", "Altitude"),
    ("field_size", "Field Size"),
    ("prestige", "Prestige"),
    ("international_draw", "Int'l Draw"),
    ("course_technicality", "Technicality"),
    ("snow_reliability", "Snow Reliability"),
    ("grooming_quality", "Grooming"),
    ("accessibility", "Accessibility"),
    ("community", "Community"),
    ("scenery", "Scenery"),
    ("organization", "Organization"),
    ("competitive_depth", "Comp. Depth"),
]


def _num(val) -> float:
    if val is None:
        return 0
    if isinstance(val, (int, float)):
        return float(val)
    try:
        return float(str(val).replace(",", ""))
    except (ValueError, TypeError):
        return 0


def _safe(val, default=""):
    """Return val if not None, else default. Preserves 0 and empty string.

    Repo pitfall: `not 0` is True in Python, so callers must check `is None`
    rather than plain falsiness (elevation_m/altitude_m can legitimately be 0).
    """
    if val is None:
        return default
    return val


def _md_escape(val) -> str:
    """Escape a value for use inside a markdown table cell."""
    if val is None:
        return ""
    s = str(val)
    return s.replace("|", "\\|").replace("\n", " ")


def _fmt_dist(val) -> str:
    n = _num(val)
    if val is None:
        return ""
    if n == int(n):
        return f"{int(n)} km"
    return f"{n:.1f} km"


def _fmt_elev(val) -> str:
    if val is None:
        return ""
    return f"{int(_num(val)):,} m"


race_files_glob = lambda data_dir: sorted(p for p in data_dir.glob("*.json") if p.name != "_schema.json")


# ---------------------------------------------------------------------------
# YAML frontmatter
# ---------------------------------------------------------------------------

def _yaml_escape(val) -> str:
    """Escape a value for YAML. Always wraps strings in double quotes for
    safety; handles internal double quotes by escaping them with backslash.
    Numeric and boolean types are returned as-is.
    """
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val)
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"'


def _frontmatter(slug: str, rd: dict) -> str:
    """Build YAML frontmatter block."""
    vitals = rd.get("vitals", {})
    rating = rd.get("nordic_lab_rating", {})

    fields = {
        "slug": slug,
        "name": rd.get("name", slug),
        "tier": _safe(rating.get("tier"), 4),
        "score": _safe(rating.get("overall_score"), 0),
        "distance_km": _safe(vitals.get("distance_km"), 0),
        "discipline": _safe(rating.get("discipline"), _safe(vitals.get("discipline"), "classic")),
        "country": _safe(vitals.get("country"), ""),
        "region": _safe(vitals.get("region"), ""),
        "location": _safe(vitals.get("location"), ""),
        "date": _safe(vitals.get("date_specific"), _safe(vitals.get("date"), "")),
        "url": f"{SITE_URL}/race/{slug}/",
    }

    lines = ["---"]
    for k, v in fields.items():
        if v is None or v == "":
            continue
        lines.append(f"{k}: {_yaml_escape(v)}")
    lines.append("---")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _section_vitals(rd: dict) -> str:
    """Build Vitals table."""
    vitals = rd.get("vitals", {})
    if not vitals:
        return ""

    rows = []
    if vitals.get("distance_km") is not None:
        rows.append(f"| Distance | {_md_escape(_fmt_dist(vitals['distance_km']))} |")
    if vitals.get("distance_options"):
        rows.append(f"| Distance Options | {_md_escape(', '.join(vitals['distance_options']))} |")
    if vitals.get("elevation_m") is not None:
        rows.append(f"| Elevation Gain | {_md_escape(_fmt_elev(vitals['elevation_m']))} |")
    if vitals.get("altitude_m") is not None:
        rows.append(f"| Altitude | {_md_escape(_fmt_elev(vitals['altitude_m']))} |")
    if vitals.get("location"):
        rows.append(f"| Location | {_md_escape(vitals['location'])} |")
    if vitals.get("country"):
        rows.append(f"| Country | {_md_escape(vitals['country'])} |")
    date_val = _safe(vitals.get("date_specific"), _safe(vitals.get("date"), ""))
    if date_val:
        rows.append(f"| Date | {_md_escape(date_val)} |")
    if vitals.get("discipline"):
        rows.append(f"| Discipline | {_md_escape(vitals['discipline'])} |")
    if vitals.get("field_size"):
        rows.append(f"| Field Size | {_md_escape(vitals['field_size'])} |")
    if vitals.get("founded") is not None:
        rows.append(f"| Founded | {_md_escape(vitals['founded'])} |")
    if vitals.get("registration"):
        rows.append(f"| Registration | {_md_escape(vitals['registration'])} |")
    if vitals.get("website"):
        rows.append(f"| Website | {_md_escape(vitals['website'])} |")

    if not rows:
        return ""

    header = "## Vitals\n\n| | |\n|---|---|\n"
    return header + "\n".join(rows)


def _section_course(rd: dict) -> str:
    """Build Course section."""
    course = rd.get("course", {})
    if not course:
        return ""

    parts = ["## Course"]

    if course.get("primary"):
        parts.append(f"\n{course['primary']}")

    details = []
    if course.get("format"):
        details.append(f"Format: {course['format']}")
    if course.get("surface"):
        details.append(f"Surface: {course['surface']}")
    if course.get("technical_rating") is not None:
        details.append(f"Technical rating: {course['technical_rating']}/5")
    if course.get("grooming"):
        details.append(f"Grooming: {course['grooming']}")
    if details:
        parts.append("\n" + "  \n".join(details))

    if course.get("features"):
        parts.append("\n### Features\n")
        for feat in course["features"]:
            parts.append(f"- {feat}")

    return "\n".join(parts)


def _section_climate(rd: dict) -> str:
    """Build Climate section."""
    climate = rd.get("climate", {})
    if not climate:
        return ""

    parts = ["## Climate"]
    if climate.get("primary"):
        parts.append(f"\n{climate['primary']}")
    if climate.get("description"):
        parts.append(f"\n{climate['description']}")
    if climate.get("typical_temp_c"):
        parts.append(f"\nTypical race-day temperature: {climate['typical_temp_c']}°C")
    if climate.get("challenges"):
        parts.append("\nChallenges:")
        for c in climate["challenges"]:
            parts.append(f"- {c}")

    return "\n".join(parts)


def _section_rating(rd: dict) -> str:
    """Build XC Ski Labs Rating section with the 14-criterion table."""
    rating = rd.get("nordic_lab_rating", {})
    if not rating:
        return ""

    parts = [
        "## XC Ski Labs Rating",
        f"\n**Overall Score**: {_safe(rating.get('overall_score'), '?')}/100",
        f"**Tier**: {_safe(rating.get('tier'), '?')}",
        f"**Discipline**: {_safe(rating.get('discipline'), 'classic')}",
        "\n| Criterion | Score |",
        "|-----------|-------|",
    ]

    for key, label in CRITERIA:
        val = rating.get(key)
        val = val if val is not None else "—"
        parts.append(f"| {label} | {val}/5 |")

    if rating.get("score_note"):
        parts.append(f"\n{rating['score_note']}")
    if rating.get("tier_note"):
        parts.append(f"\n{rating['tier_note']}")

    return "\n".join(parts)


def _section_history(rd: dict) -> str:
    """Build History section."""
    history = rd.get("history", {})
    if not history:
        return ""

    parts = ["## History"]
    if history.get("summary"):
        parts.append(f"\n{history['summary']}")
    if history.get("notable_facts"):
        parts.append("\n### Notable Facts\n")
        for fact in history["notable_facts"]:
            parts.append(f"- {fact}")

    return "\n".join(parts)


def _section_series(rd: dict) -> str:
    """Build Series Membership section."""
    series = rd.get("series_membership", [])
    if not series:
        return ""

    parts = ["## Series Membership\n"]
    for s in series:
        parts.append(f"- {s}")

    return "\n".join(parts)


def _section_videos(rd: dict) -> str:
    """Build Race Footage section from youtube_data video titles."""
    yt = rd.get("youtube_data", {})
    videos = yt.get("videos", [])
    if not videos:
        return ""

    parts = ["## Race Footage\n"]
    parts.append("*YouTube titles referenced during research (not embedded).*\n")
    for v in videos:
        title = v.get("title")
        if not title:
            continue
        channel = v.get("channel", "")
        if channel:
            parts.append(f"- {title} ({channel})")
        else:
            parts.append(f"- {title}")

    if len(parts) <= 2:
        return ""

    quotes = yt.get("quotes", [])
    if quotes:
        parts.append("\n### Rider Quotes\n")
        for q in quotes:
            text = q.get("text", "")
            if text:
                parts.append(f"> {text}")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Profile builder
# ---------------------------------------------------------------------------

def generate_profile(slug: str, race_data_dir: Path = RACE_DATA_DIR, race_count: int = 0) -> str | None:
    """Generate a complete Markdown profile for a single race."""
    f = race_data_dir / f"{slug}.json"
    if not f.exists():
        return None

    try:
        data = json.loads(f.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    rd = data.get("race", data)
    if not rd.get("slug") or not rd.get("nordic_lab_rating"):
        return None

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sections = [
        _frontmatter(slug, rd),
        f"\n# {rd.get('display_name') or rd.get('name', slug)}",
        (
            f"\n> *Source: [XC Ski Labs]({SITE_URL}/) — a cross-country ski "
            f"race database covering {race_count} races, scored on 14 "
            f"criteria. Canonical page: {SITE_URL}/race/{slug}/*"
        ),
    ]

    tagline = rd.get("tagline", "")
    if tagline:
        sections.append(f"\n> {tagline}")

    for builder in [
        _section_vitals,
        _section_course,
        _section_climate,
        _section_rating,
        _section_history,
        _section_series,
        _section_videos,
    ]:
        section = builder(rd)
        if section:
            sections.append(f"\n{section}")

    race_name = rd.get("display_name") or rd.get("name", slug)
    sections.append(
        f'\n---\n*This profile is by XC Ski Labs (xcskilabs.com). '
        f'Cite as: "XC Ski Labs — {race_name}". Canonical: '
        f"{SITE_URL}/race/{slug}/. Generated {now}.*\n"
    )

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Markdown race profiles")
    parser.add_argument("--data-dir", default=str(RACE_DATA_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--slug", help="Generate a single race profile")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    if not data_dir.exists():
        print(f"ERROR: Race data directory not found: {data_dir}")
        return 1

    if args.slug:
        slugs = [args.slug]
    else:
        slugs = [p.stem for p in race_files_glob(data_dir)]

    print(f"Found {len(slugs)} race profile(s)")

    generated = 0
    skipped = 0
    total_bytes = 0

    for slug in slugs:
        md = generate_profile(
            slug, data_dir, race_count=len(race_files_glob(data_dir)))
        if md is None:
            print(f"  WARNING: {slug} produced no output, skipping")
            skipped += 1
            continue

        total_bytes += len(md)

        if not args.dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            out_file = output_dir / f"{slug}.md"
            out_file.write_text(md, encoding="utf-8")

        generated += 1

    print(f"  Generated: {generated} profiles")
    print(f"  Skipped: {skipped}")
    print(f"  Total size: {total_bytes:,} bytes ({total_bytes / 1024:.0f} KB)")

    if args.dry_run:
        print(f"\n  [dry run] Would write to {output_dir}/")
    else:
        print(f"  Wrote to: {output_dir}/")

    return 0


if __name__ == "__main__":
    sys.exit(main())
