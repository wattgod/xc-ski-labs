#!/usr/bin/env python3
"""Generate llms.txt and llms-full.txt per the llmstxt.org standard.

Produces two files:
  output/llms.txt      (~2KB) — brief description + links to machine-readable resources
  output/llms-full.txt (~100KB) — the full rated race index for LLM consumption

Modeled on the road repo's scripts/generate_llms_txt.py, adapted to XC Ski
Labs' 14-criteria/70-denominator scoring (no cultural-impact bonus) and its
race-data/*.json schema (nordic_lab_rating, not fondo_rating).

Usage:
    python scripts/generate_llms_txt.py           # Generate both files
    python scripts/generate_llms_txt.py --dry-run  # Preview sizes only
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
OUTPUT_DIR = PROJECT_ROOT / "output"
SITE_URL = "https://xcskilabs.com"

TIER_LABELS = {1: "Tier 1 (Elite)", 2: "Tier 2 (Strong)", 3: "Tier 3 (Solid)", 4: "Tier 4 (Developing)"}

# Order matches CLAUDE.md's Scoring System section and generate_race_pages.py's
# RATING_CRITERIA — 14 criteria, denominator 70, no bonus criterion.
CRITERIA = [
    "distance", "elevation", "altitude", "field_size", "prestige",
    "international_draw", "course_technicality", "snow_reliability",
    "grooming_quality", "accessibility", "community", "scenery",
    "organization", "competitive_depth",
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


def _fmt_dist(val) -> str:
    n = _num(val)
    if n == 0:
        return "—"
    if n == int(n):
        return f"{int(n)} km"
    return f"{n:.1f} km"


def _md_escape(val) -> str:
    """Escape a value for use inside a markdown table cell."""
    s = str(val) if val is not None else "—"
    return s.replace("|", "\\|").replace("\n", " ")


def race_files(data_dir: Path) -> list[Path]:
    return sorted(p for p in data_dir.glob("*.json") if p.name != "_schema.json")


def load_races(data_dir: Path = RACE_DATA_DIR) -> list[dict[str, Any]]:
    """Load every valid race (slug + nordic_lab_rating present) from race-data/."""
    races = []
    for path in race_files(data_dir):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        race = data.get("race", {})
        if race.get("slug") and race.get("nordic_lab_rating"):
            races.append(race)
    return races


# ---------------------------------------------------------------------------
# llms.txt (brief)
# ---------------------------------------------------------------------------

def generate_llms_txt(races: list[dict]) -> str:
    """Generate the brief llms.txt file."""
    tier_counts: dict[int, int] = {}
    for race in races:
        t = race.get("nordic_lab_rating", {}).get("tier", 4)
        tier_counts[t] = tier_counts.get(t, 0) + 1

    countries = sorted({race.get("vitals", {}).get("country") for race in races if race.get("vitals", {}).get("country")})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = len(races)

    return f"""# XC Ski Labs Race Database

> The definitive cross-country ski race database. {count} races rated on 14 criteria, scored 0-100, and tiered 1-4.
> Last generated: {now}

## Overview

XC Ski Labs is a cross-country ski race database covering {count} races worldwide. Every race is scored on 14 criteria ({', '.join(CRITERIA)}) on a 1-5 scale, producing an overall score out of 100 (round(sum of the 14 criteria / 70 * 100)) and a tier assignment (T1=elite, T2=strong, T3=solid, T4=developing).

- **Tier 1 (Elite)**: {tier_counts.get(1, 0)} races — score >= 80, or prestige=5 + score>=75
- **Tier 2 (Strong)**: {tier_counts.get(2, 0)} races — score >= 60
- **Tier 3 (Solid)**: {tier_counts.get(3, 0)} races — score >= 45
- **Tier 4 (Developing)**: {tier_counts.get(4, 0)} races — score < 45

Prestige overrides: prestige=5 + score>=75 confirms Tier 1; prestige=5 + score<75 caps at Tier 2; prestige=4 promotes one tier (never into Tier 1).

Disciplines: classic, skate, both (a classic/skate combined event).
Countries: {', '.join(countries)}.

## Machine-Readable Resources

- [Full LLM context (this database as text)]({SITE_URL}/llms-full.txt)
- [Race index JSON ({count} entries)]({SITE_URL}/search/race-index.json)
- [RSS feed]({SITE_URL}/feed/races.xml)
- [Race dates JSON]({SITE_URL}/race-dates.json)
- [Source code & data (GitHub)](https://github.com/wattgod/xc-ski-labs)
- [Individual race profiles]({SITE_URL}/race/{{slug}}/)
- [Markdown profiles]({SITE_URL}/race/{{slug}}.md)
- [Training plans]({SITE_URL}/training-plans/)
- [Coaching]({SITE_URL}/coaching/apply/)

## Markdown Mirrors

Every race profile is also published as clean Markdown with YAML
frontmatter, one file per race, at:

`{SITE_URL}/race/{{slug}}.md`

e.g. {SITE_URL}/race/vasaloppet.md

## Contact

- Website: {SITE_URL}
- Email: coaching@xcskilabs.com
"""


# ---------------------------------------------------------------------------
# llms-full.txt (comprehensive)
# ---------------------------------------------------------------------------

def generate_llms_full_txt(races: list[dict]) -> str:
    """Generate the comprehensive llms-full.txt file: every race, one row."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    count = len(races)

    lines = []
    lines.append("# XC Ski Labs Race Database — Full Context")
    lines.append("")
    lines.append(f"> {count} cross-country ski races rated on 14 criteria (distance, elevation, altitude, field_size, prestige, international_draw, course_technicality, snow_reliability, grooming_quality, accessibility, community, scenery, organization, competitive_depth).")
    lines.append(f"> Produced by XC Ski Labs ({SITE_URL.replace('https://', '')}). Generated: {now}")
    lines.append("")

    # Scoring methodology
    lines.append("## Scoring Methodology")
    lines.append("")
    lines.append("Each race is scored on 14 criteria (1-5 scale):")
    lines.append(", ".join(CRITERIA) + ".")
    lines.append("")
    lines.append("Overall score = round((sum of the 14 criteria / 70) * 100).")
    lines.append("")
    lines.append("Tier assignment:")
    lines.append("- Tier 1 (Elite): score >= 80, OR prestige=5 + score>=75")
    lines.append("- Tier 2 (Strong): score >= 60, OR prestige=5 + score<75 (capped at T2)")
    lines.append("- Tier 3 (Solid): score >= 45")
    lines.append("- Tier 4 (Developing): score < 45")
    lines.append("- Prestige 4 promotes one tier (but not into T1)")
    lines.append("")

    # Sort: T1 first, then T2, T3, T4, each by score desc
    def sort_key(race: dict) -> tuple:
        r = race.get("nordic_lab_rating", {})
        return (r.get("tier", 99), -(r.get("overall_score") or 0))

    sorted_races = sorted(races, key=sort_key)

    lines.append(f"## Full Rated Index ({count} races)")
    lines.append("")
    lines.append(f"Each race's Markdown mirror is at {SITE_URL}/race/{{slug}}.md — the Slug column below gives {{slug}}.")
    lines.append("")
    lines.append("| Name | Slug | Tier | Score | Discipline | Country | Distance | Tagline |")
    lines.append("|------|------|------|-------|------------|---------|----------|---------|")

    for race in sorted_races:
        r = race.get("nordic_lab_rating", {})
        vitals = race.get("vitals", {})
        name = _md_escape(race.get("display_name") or race.get("name") or race.get("slug"))
        slug = _md_escape(race["slug"])
        tier = r.get("tier", "?")
        score = r.get("overall_score", "?")
        disc = _md_escape(r.get("discipline") or vitals.get("discipline") or "—")
        country = _md_escape(vitals.get("country", "—"))
        dist = _fmt_dist(vitals.get("distance_km"))
        tagline = _md_escape(race.get("tagline", ""))
        lines.append(f"| {name} | {slug} | {tier} | {score} | {disc} | {country} | {dist} | {tagline} |")

    lines.append("")

    # Data schema
    lines.append("## Data Schema")
    lines.append("")
    lines.append("Each race profile (JSON) contains:")
    lines.append("- `race.name`, `race.slug`, `race.display_name`, `race.tagline`")
    lines.append("- `race.vitals`: distance_km, elevation_m, altitude_m, location, country, region, date, discipline, field_size, founded, website")
    lines.append("- `race.nordic_lab_rating`: overall_score, tier, discipline, the 14 criteria scores")
    lines.append("- `race.climate`: primary, description, typical_temp_c, challenges")
    lines.append("- `race.course`: primary, format, surface, technical_rating, grooming, features")
    lines.append("- `race.history`: summary, notable_facts")
    lines.append("- `race.series_membership`: e.g. worldloppet, ski_classics_grand_classic")
    lines.append("- `race.youtube_data`: videos, quotes")
    lines.append("")
    lines.append(f"Access individual profiles at: {SITE_URL}/race/{{slug}}/")
    lines.append(f"Machine-readable JSON index: {SITE_URL}/search/race-index.json")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate llms.txt and llms-full.txt")
    parser.add_argument("--data-dir", default=str(RACE_DATA_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--dry-run", action="store_true", help="Preview sizes only")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)

    races = load_races(data_dir)
    if not races:
        print(f"ERROR: No races loaded from {data_dir}")
        return 1
    print(f"Loaded {len(races)} races")

    llms_txt = generate_llms_txt(races)
    print(f"  llms.txt: {len(llms_txt):,} bytes")

    llms_full = generate_llms_full_txt(races)
    print(f"  llms-full.txt: {len(llms_full):,} bytes")

    if args.dry_run:
        print(f"\n  [dry run] Would write to {output_dir}/llms.txt and {output_dir}/llms-full.txt")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "llms.txt").write_text(llms_txt, encoding="utf-8")
    print(f"  Wrote: {output_dir / 'llms.txt'}")

    (output_dir / "llms-full.txt").write_text(llms_full, encoding="utf-8")
    print(f"  Wrote: {output_dir / 'llms-full.txt'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
