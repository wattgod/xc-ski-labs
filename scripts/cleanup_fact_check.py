#!/usr/bin/env python3
"""
Clean up after fact-check auto-fix:
1. Remove invalid fields added to vitals by Perplexity response
2. Normalize discipline values to valid schema values
3. Remove valtellina-orobie profile (not XC skiing)
4. Remove string field_size values (must be int)
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Fields that should NOT exist in vitals
JUNK_VITALS_FIELDS = {
    "race_date", "typical_race_date", "official_website", "official_website_url",
    "typical_participants", "year_founded", "region_state_province",
}

# Valid discipline values
VALID_DISCIPLINES = {"classic", "skate", "both"}
DISCIPLINE_MAP = {
    "freestyle": "skate",
    "freestyle (skate)": "skate",
    "freestyle (free technique) only": "skate",
    "libre (skate and classic)": "both",
    "freestyle and classic": "both",
    "ski-mountaineering": None,  # Flag for removal
}

# Profiles to remove (not XC skiing)
REMOVE_PROFILES = ["valtellina-orobie-ski-marathon"]

fixes = 0
removed_fields = 0

for path in sorted(RACE_DATA_DIR.glob("*.json")):
    if path.name == "_schema.json":
        continue

    with open(path) as f:
        data = json.load(f)

    race = data.get("race", {})
    vitals = race.get("vitals", {})
    modified = False

    # Remove junk fields from vitals
    for junk in JUNK_VITALS_FIELDS:
        if junk in vitals:
            del vitals[junk]
            removed_fields += 1
            modified = True
            print(f"  REMOVE {path.stem}.vitals.{junk}")

    # Normalize discipline
    discipline = vitals.get("discipline")
    if discipline and discipline not in VALID_DISCIPLINES:
        mapped = DISCIPLINE_MAP.get(discipline)
        if mapped is not None:
            vitals["discipline"] = mapped
            print(f"  NORMALIZE {path.stem}.discipline: {discipline!r} → {mapped!r}")
            modified = True
            fixes += 1
        elif discipline == "ski-mountaineering":
            print(f"  FLAG {path.stem}: ski-mountaineering (not XC)")
        else:
            print(f"  WARN {path.stem}: unknown discipline {discipline!r}")

    # Clean string field_size values that got written as strings
    for fs_key in ("field_size", "field_size_estimate"):
        val = vitals.get(fs_key)
        if isinstance(val, str):
            # Try to parse to int
            import re
            nums = re.findall(r'\d+', val.replace(",", ""))
            if nums:
                vitals[fs_key] = int(nums[0])
                print(f"  COERCE {path.stem}.{fs_key}: {val!r} → {vitals[fs_key]}")
                modified = True
                fixes += 1

    # Clean website fields that got weird long strings
    website = vitals.get("website")
    if website and len(website) > 100:
        # Probably a Perplexity note, not a URL
        vitals["website"] = None
        print(f"  CLEAN {path.stem}.website: too long, set to null")
        modified = True
        fixes += 1

    if modified:
        with open(path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")

# Remove non-XC profiles
for slug in REMOVE_PROFILES:
    race_path = RACE_DATA_DIR / f"{slug}.json"
    if race_path.exists():
        os.remove(race_path)
        print(f"\n  DELETED {slug}.json (not XC skiing)")
        fixes += 1
    # Also remove output dir
    out_dir = OUTPUT_DIR / slug
    if out_dir.exists():
        import shutil
        shutil.rmtree(out_dir)
        print(f"  DELETED output/{slug}/")

print(f"\n{'=' * 50}")
print(f"Cleanup: {fixes} fixes, {removed_fields} junk fields removed")
