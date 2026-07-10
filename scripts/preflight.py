#!/usr/bin/env python3
"""
XC Ski Labs — Pre-deploy Validation

Run before every deploy. Catches:
  - Score math errors across all profiles
  - Missing required fields
  - Stale homepage stats
  - Search index drift from profiles
  - Branding inconsistencies
  - Orphaned YouTube quotes
  - Broken cross-references

Usage:
    python preflight.py             # validate only
    python preflight.py --deploy    # validate then deploy if clean
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
WEB_DIR = PROJECT_ROOT / "web"
OUTPUT_DIR = PROJECT_ROOT / "output"

REQUIRED_CRITERIA = [
    "distance", "elevation", "altitude", "field_size", "prestige",
    "international_draw", "course_technicality", "snow_reliability",
    "grooming_quality", "accessibility", "community", "scenery",
    "organization", "competitive_depth",
]
VALID_DISCIPLINES = {"classic", "skate", "both"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PreflightResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = {}

    def error(self, msg):
        self.errors.append(msg)
        print(f"  ERROR: {msg}")

    def warn(self, msg):
        self.warnings.append(msg)
        print(f"  WARN:  {msg}")

    @property
    def ok(self):
        return len(self.errors) == 0


def check_profiles(result: PreflightResult):
    """Validate all race profiles."""
    print("\n[1/6] Validating race profiles...")

    profiles = []
    for f in sorted(RACE_DATA_DIR.glob("*.json")):
        if f.name == "_schema.json":
            continue
        try:
            with open(f) as fh:
                data = json.load(fh)
        except json.JSONDecodeError as e:
            result.error(f"{f.name}: Invalid JSON — {e}")
            continue

        race = data.get("race")
        if not race:
            result.error(f"{f.name}: Missing 'race' key")
            continue

        slug = f.stem
        profiles.append((slug, race))

        # Slug match
        if race.get("slug") != slug:
            result.error(f"{f.name}: slug '{race.get('slug')}' != filename '{slug}'")

        # Slug format
        if not SLUG_RE.match(slug):
            result.error(f"{f.name}: Invalid slug format")

        # Required fields
        for field in ["name", "display_name", "tagline"]:
            if not race.get(field):
                result.error(f"{f.name}: Missing '{field}'")

        # Vitals
        vitals = race.get("vitals", {})
        if not vitals.get("country"):
            result.error(f"{f.name}: Missing vitals.country")
        if not vitals.get("discipline"):
            result.error(f"{f.name}: Missing vitals.discipline")
        elif vitals["discipline"] not in VALID_DISCIPLINES:
            result.error(f"{f.name}: Invalid discipline '{vitals['discipline']}'")

        # Rating
        rating = race.get("nordic_lab_rating", {})
        if not rating:
            result.error(f"{f.name}: Missing nordic_lab_rating")
            continue

        # All 14 criteria
        missing = [c for c in REQUIRED_CRITERIA if c not in rating]
        if missing:
            result.error(f"{f.name}: Missing criteria: {missing}")
            continue

        # Criteria in range
        for c in REQUIRED_CRITERIA:
            val = rating.get(c)
            if not isinstance(val, (int, float)) or val < 1 or val > 5:
                result.error(f"{f.name}: {c}={val} not in [1,5]")

        # Score math
        criteria_sum = sum(rating.get(c, 0) for c in REQUIRED_CRITERIA)
        expected_score = round((criteria_sum / 70) * 100)
        actual_score = rating.get("overall_score")
        if actual_score != expected_score:
            result.error(
                f"{f.name}: Score mismatch — sum={criteria_sum}, "
                f"expected={expected_score}, actual={actual_score}"
            )

        # Tier math
        score = actual_score or 0
        prestige = rating.get("prestige", 0)
        if score >= 80:
            base_tier = 1
        elif score >= 60:
            base_tier = 2
        elif score >= 45:
            base_tier = 3
        else:
            base_tier = 4

        expected_tier = base_tier
        if prestige == 5 and score >= 75:
            expected_tier = 1
        elif prestige == 5 and score < 75:
            expected_tier = min(base_tier, 2)
        elif prestige == 4:
            expected_tier = max(base_tier - 1, 2)

        actual_tier = rating.get("tier")
        if actual_tier != expected_tier:
            result.error(
                f"{f.name}: Tier mismatch — score={score}, prestige={prestige}, "
                f"expected={expected_tier}, actual={actual_tier}"
            )

        # YouTube data structure
        yt = race.get("youtube_data")
        if yt is None:
            result.error(f"{f.name}: Missing youtube_data")
        elif not isinstance(yt.get("videos"), list):
            result.error(f"{f.name}: youtube_data.videos should be a list")

        # Orphaned quotes
        if yt and yt.get("videos") and yt.get("quotes"):
            curated_ids = {v.get("video_id") for v in yt["videos"]}
            for q in yt.get("quotes", []):
                src = q.get("source_video_id")
                if src and src not in curated_ids:
                    result.error(f"{f.name}: Orphaned quote references video '{src}'")

        # Video ID types
        if yt:
            for v in yt.get("videos", []):
                vid = v.get("video_id")
                if vid is not None and not isinstance(vid, str):
                    result.error(f"{f.name}: video_id should be str, got {type(vid).__name__}")

    # Duplicate check
    slugs = [s for s, _ in profiles]
    dupes = [s for s in slugs if slugs.count(s) > 1]
    if dupes:
        result.error(f"Duplicate slugs: {set(dupes)}")

    result.stats["profiles"] = len(profiles)
    tiers = {}
    for _, r in profiles:
        t = r.get("nordic_lab_rating", {}).get("tier", 0)
        tiers[t] = tiers.get(t, 0) + 1
    result.stats["tiers"] = tiers

    countries = set()
    for _, r in profiles:
        c = r.get("vitals", {}).get("country")
        if c:
            countries.add(c)
    result.stats["countries"] = len(countries)

    print(f"  Checked {len(profiles)} profiles, {len(countries)} countries")
    print(f"  Tiers: {tiers}")


def check_search_index(result: PreflightResult):
    """Verify search index matches profiles."""
    print("\n[2/6] Validating search index...")

    index_file = WEB_DIR / "race-index.json"
    if not index_file.exists():
        result.error("race-index.json not found — run generate_race_index.py")
        return

    with open(index_file) as f:
        data = json.load(f)

    index_count = len(data.get("races", []))
    profile_count = result.stats.get("profiles", 0)

    if index_count != profile_count:
        result.error(
            f"Search index has {index_count} races but {profile_count} profiles exist — "
            f"run generate_race_index.py"
        )
    else:
        print(f"  Index matches: {index_count} races")


def check_output_pages(result: PreflightResult):
    """Verify output pages exist and match profiles."""
    print("\n[3/6] Validating output pages...")

    if not OUTPUT_DIR.exists():
        result.error("output/ directory not found — run generate_race_pages.py")
        return

    NON_RACE_DIRS = {"about", "coaching", "feed", "questionnaire", "search", "thanks", "training-plans"}
    page_slugs = set()
    for d in OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name not in NON_RACE_DIRS and (d / "index.html").exists():
            page_slugs.add(d.name)

    profile_count = result.stats.get("profiles", 0)
    if len(page_slugs) != profile_count:
        result.error(
            f"Output has {len(page_slugs)} pages but {profile_count} profiles exist — "
            f"run generate_race_pages.py"
        )
    else:
        print(f"  Pages match: {len(page_slugs)} pages")

    # Check homepage exists
    hp = OUTPUT_DIR / "index.html"
    if not hp.exists():
        result.error("Homepage missing at output/index.html")

    # Check search deployed
    search = OUTPUT_DIR / "search" / "index.html"
    if not search.exists():
        result.warn("Search not in output/search/ — will need to copy before deploy")


def check_branding(result: PreflightResult):
    """Check for stale branding (Nordic Lab, Glide Labs)."""
    print("\n[4/6] Checking branding consistency...")

    # Search page
    search_html = WEB_DIR / "nordic-lab-search.html"
    if search_html.exists():
        content = search_html.read_text()
        if "NORDIC LAB" in content and "XC SKI LABS" not in content:
            result.error("Search page still branded 'NORDIC LAB'")

    # Race page titles
    checked = 0
    stale = 0
    for d in OUTPUT_DIR.iterdir():
        if d.is_dir() and d.name != "search" and (d / "index.html").exists():
            content = (d / "index.html").read_text()[:500]
            title_match = re.search(r"<title>(.*?)</title>", content)
            if title_match and "Nordic Lab" in title_match.group(1):
                stale += 1
                if stale <= 3:
                    result.error(f"{d.name}: Title still says 'Nordic Lab'")
            checked += 1

    if stale > 3:
        result.error(f"...and {stale - 3} more pages with stale branding")
    if stale == 0:
        print(f"  Branding OK across {checked} pages")


def check_homepage_stats(result: PreflightResult):
    """Verify homepage stats match actual data."""
    print("\n[5/6] Checking homepage stats...")

    hp = OUTPUT_DIR / "index.html"
    if not hp.exists():
        result.warn("Homepage not found — skipping stats check")
        return

    content = hp.read_text()
    profile_count = result.stats.get("profiles", 0)
    country_count = result.stats.get("countries", 0)

    # Check race count
    race_match = re.search(r'id="statRaces">(\d+)', content)
    if race_match:
        hp_count = int(race_match.group(1))
        if hp_count != profile_count:
            result.warn(
                f"Homepage shows {hp_count} races but {profile_count} profiles exist"
            )
    else:
        result.warn("Could not find race count in homepage")

    # Check country count
    country_match = re.search(r'id="statCountries">(\d+)', content)
    if country_match:
        hp_countries = int(country_match.group(1))
        if hp_countries != country_count:
            result.warn(
                f"Homepage shows {hp_countries} countries but {country_count} exist"
            )

    print(f"  Homepage stats checked")


def check_security(result: PreflightResult):
    """Check for security issues."""
    print("\n[6/6] Security checks...")

    # .env not tracked
    gitignore = PROJECT_ROOT / ".gitignore"
    if gitignore.exists():
        gi_content = gitignore.read_text()
        if ".env" not in gi_content:
            result.error(".env not in .gitignore — API keys could be exposed")
    else:
        result.error("No .gitignore found")

    # Check for hardcoded API keys in scripts (skip this file)
    key_patterns = [
        re.compile(r'sk-ant-api\d{2}-[A-Za-z0-9]{20,}'),
        re.compile(r'AIzaSy[A-Za-z0-9_-]{30,}'),
    ]
    for f in SCRIPT_DIR.glob("*.py"):
        if f.name == "preflight.py":
            continue
        content = f.read_text()
        for kp in key_patterns:
            if kp.search(content):
                result.error(f"{f.name}: Possible hardcoded API key")

    print("  Security checks done")


def main():
    parser = argparse.ArgumentParser(description="XC Ski Labs pre-deploy validation")
    parser.add_argument("--deploy", action="store_true", help="Deploy if validation passes")
    args = parser.parse_args()

    print("=" * 50)
    print("XC Ski Labs — Pre-deploy Validation")
    print("=" * 50)

    result = PreflightResult()

    check_profiles(result)
    check_search_index(result)
    check_output_pages(result)
    check_branding(result)
    check_homepage_stats(result)
    check_security(result)

    print("\n" + "=" * 50)
    print(f"ERRORS:   {len(result.errors)}")
    print(f"WARNINGS: {len(result.warnings)}")
    print("=" * 50)

    if result.errors:
        print("\nFAILED — fix errors before deploying")
        sys.exit(1)
    else:
        print("\nPASSED")
        if args.deploy:
            print("\nRunning deploy...")
            subprocess.run([sys.executable, str(SCRIPT_DIR / "deploy.py"), "--deploy-all"])
        sys.exit(0)


if __name__ == "__main__":
    main()
