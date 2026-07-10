#!/usr/bin/env python3
"""
XC Ski Labs — Normalize Race Profiles

Fixes schema inconsistencies across all race profiles:
1. Convert string field_size to numeric field_size_estimate
2. Remove _fact_check_fixes metadata
3. Standardize website field (all in vitals.website)
4. Fix http:// URLs → https://
5. Ensure elevation_gain_m exists (numeric or null)
6. Ensure youtube_data.videos exists as a list

Usage:
    python scripts/normalize_profiles.py
    python scripts/normalize_profiles.py --dry-run
"""

import json
import re
import sys
from pathlib import Path

RACE_DATA_DIR = Path(__file__).resolve().parent.parent / "race-data"


def parse_field_size(value):
    """Parse a string field_size like '~8,000 starters' to an integer.

    Returns int or None if unparseable.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if not isinstance(value, str):
        return None

    s = value.strip()
    if not s:
        return None

    # Remove leading ~
    s = s.lstrip("~").strip()

    # Handle ranges like "500-800 participants" → take midpoint
    range_match = re.match(r"^([\d,]+)\s*[-–]\s*([\d,]+)", s)
    if range_match:
        lo = int(range_match.group(1).replace(",", ""))
        hi = int(range_match.group(2).replace(",", ""))
        return (lo + hi) // 2

    # Extract leading number: "8,000 starters" → 8000
    num_match = re.match(r"^([\d,]+)", s)
    if num_match:
        return int(num_match.group(1).replace(",", ""))

    return None


def normalize_profile(filepath, dry_run=False):
    """Normalize a single race profile. Returns list of changes made."""
    changes = []
    slug = filepath.stem

    with open(filepath) as f:
        data = json.load(f)

    race = data.get("race", {})
    vitals = race.get("vitals", {})
    modified = False

    # 1. Convert field_size string → field_size_estimate int
    if "field_size" in vitals:
        raw = vitals["field_size"]
        if isinstance(raw, str):
            parsed = parse_field_size(raw)
            vitals["field_size_estimate"] = parsed
            changes.append(f"  field_size_estimate: '{raw}' → {parsed}")
            modified = True
        elif isinstance(raw, (int, float)):
            # Already numeric, just ensure field_size_estimate exists
            if "field_size_estimate" not in vitals:
                vitals["field_size_estimate"] = int(raw)
                changes.append(f"  field_size_estimate: copied from numeric field_size={raw}")
                modified = True
    elif "field_size_estimate" not in vitals:
        vitals["field_size_estimate"] = None
        changes.append("  field_size_estimate: added as null (no field_size found)")
        modified = True

    # 2. Remove _fact_check_fixes metadata
    if "_fact_check_fixes" in race:
        del race["_fact_check_fixes"]
        changes.append("  _fact_check_fixes: removed")
        modified = True

    # 3. Standardize website field
    # All profiles already use vitals.website — check for logistics.official_site
    logistics = race.get("logistics", {})
    if isinstance(logistics, dict) and "official_site" in logistics:
        url = logistics.pop("official_site")
        if not vitals.get("website") and url:
            vitals["website"] = url
            changes.append(f"  website: moved from logistics.official_site → vitals.website: {url}")
        else:
            changes.append(f"  logistics.official_site: removed (vitals.website already set)")
        if not logistics:
            del race["logistics"]
        modified = True

    # 4. Fix http:// URLs → https://
    website = vitals.get("website")
    if isinstance(website, str) and website.startswith("http://"):
        vitals["website"] = website.replace("http://", "https://", 1)
        changes.append(f"  website: http → https: {website} → {vitals['website']}")
        modified = True

    # 5. Ensure elevation_gain_m exists (numeric or null)
    if "elevation_gain_m" not in vitals:
        # Copy from elevation_m if it exists and is numeric
        elev = vitals.get("elevation_m")
        if isinstance(elev, (int, float)):
            vitals["elevation_gain_m"] = elev
            changes.append(f"  elevation_gain_m: set to {elev} (from elevation_m)")
        elif isinstance(elev, str):
            # Try to parse string elevation
            try:
                val = float(elev)
                vitals["elevation_gain_m"] = int(val) if val == int(val) else val
                changes.append(f"  elevation_gain_m: parsed '{elev}' → {vitals['elevation_gain_m']}")
            except (ValueError, TypeError):
                vitals["elevation_gain_m"] = None
                changes.append(f"  elevation_gain_m: set to null (unparseable: '{elev}')")
        else:
            vitals["elevation_gain_m"] = None
            changes.append("  elevation_gain_m: set to null (no elevation_m found)")
        modified = True
    else:
        # Verify it's numeric or null
        egm = vitals["elevation_gain_m"]
        if isinstance(egm, str):
            try:
                val = float(egm)
                vitals["elevation_gain_m"] = int(val) if val == int(val) else val
                changes.append(f"  elevation_gain_m: converted string '{egm}' → {vitals['elevation_gain_m']}")
                modified = True
            except (ValueError, TypeError):
                vitals["elevation_gain_m"] = None
                changes.append(f"  elevation_gain_m: set to null (unparseable string: '{egm}')")
                modified = True

    # 6. Ensure youtube_data.videos exists as a list
    yt = race.get("youtube_data")
    if yt is None:
        race["youtube_data"] = {"videos": [], "quotes": []}
        changes.append("  youtube_data: added with empty videos list")
        modified = True
    elif not isinstance(yt, dict):
        race["youtube_data"] = {"videos": [], "quotes": []}
        changes.append(f"  youtube_data: replaced non-dict ({type(yt).__name__}) with empty structure")
        modified = True
    else:
        if "videos" not in yt or not isinstance(yt.get("videos"), list):
            old = yt.get("videos")
            yt["videos"] = [] if old is None else (old if isinstance(old, list) else [])
            changes.append(f"  youtube_data.videos: fixed (was {type(old).__name__ if old is not None else 'missing'})")
            modified = True

    if modified and not dry_run:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

    return changes


def main():
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("=== DRY RUN — no files will be modified ===\n")

    profiles = sorted(RACE_DATA_DIR.glob("*.json"))
    profiles = [p for p in profiles if p.name != "_schema.json"]

    print(f"Scanning {len(profiles)} race profiles...\n")

    total_changes = 0
    profiles_changed = 0
    change_summary = {
        "field_size_estimate": 0,
        "_fact_check_fixes": 0,
        "website_moved": 0,
        "http_to_https": 0,
        "elevation_gain_m": 0,
        "youtube_data": 0,
    }

    for filepath in profiles:
        changes = normalize_profile(filepath, dry_run=dry_run)
        if changes:
            profiles_changed += 1
            total_changes += len(changes)
            print(f"{filepath.stem}:")
            for c in changes:
                print(c)
                # Categorize
                if "field_size_estimate" in c:
                    change_summary["field_size_estimate"] += 1
                elif "_fact_check_fixes" in c:
                    change_summary["_fact_check_fixes"] += 1
                elif "moved from logistics" in c or "logistics.official_site" in c:
                    change_summary["website_moved"] += 1
                elif "http → https" in c:
                    change_summary["http_to_https"] += 1
                elif "elevation_gain_m" in c:
                    change_summary["elevation_gain_m"] += 1
                elif "youtube_data" in c:
                    change_summary["youtube_data"] += 1
            print()

    print("=" * 60)
    print(f"SUMMARY: {total_changes} changes across {profiles_changed}/{len(profiles)} profiles")
    print(f"  field_size_estimate conversions: {change_summary['field_size_estimate']}")
    print(f"  _fact_check_fixes removed:       {change_summary['_fact_check_fixes']}")
    print(f"  website field moves:             {change_summary['website_moved']}")
    print(f"  http → https fixes:              {change_summary['http_to_https']}")
    print(f"  elevation_gain_m additions:       {change_summary['elevation_gain_m']}")
    print(f"  youtube_data fixes:              {change_summary['youtube_data']}")

    if dry_run:
        print("\n(Dry run — no files were modified)")


if __name__ == "__main__":
    main()
