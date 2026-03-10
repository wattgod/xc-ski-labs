"""
Nordic Lab — Race Index Generator
Reads all race-data/*.json profiles and generates web/race-index.json
for the search UI.
"""

import json
import glob
import os
import sys

RACE_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "race-data")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "web")


def build_index():
    """Build a compact race index for the search UI."""
    races = []
    files = sorted(glob.glob(os.path.join(RACE_DATA_DIR, "*.json")))
    files = [f for f in files if "_schema" not in f]

    for filepath in files:
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)

        r = data["race"]
        v = r["vitals"]
        rating = r["nordic_lab_rating"]

        entry = {
            "n": r["name"],                              # name
            "s": r["slug"],                              # slug
            "dn": r.get("display_name", r["name"]),      # display_name
            "tg": r.get("tagline", ""),                   # tagline
            "d": v.get("distance_km", 0),                 # distance_km
            "do": v.get("distance_options", []),           # distance_options
            "el": v.get("elevation_m"),                    # elevation_m
            "al": v.get("altitude_m"),                     # altitude_m
            "loc": v.get("location", ""),                  # location
            "lb": v.get("location_badge", ""),             # location_badge
            "co": v.get("country", ""),                    # country
            "cc": v.get("country_code", ""),               # country_code
            "rg": v.get("region", ""),                     # region
            "dt": v.get("date", ""),                       # date
            "ds": v.get("date_specific"),                  # date_specific
            "di": rating.get("discipline", ""),            # discipline
            "fs": v.get("field_size", ""),                  # field_size
            "yr": v.get("founded"),                        # founded
            "sc": rating["overall_score"],                 # overall_score
            "t": rating["tier"],                           # tier
            "tl": rating["tier_label"],                    # tier_label
            "lat": v.get("lat"),                           # latitude
            "lng": v.get("lng"),                           # longitude
            "sm": r.get("series_membership", []),          # series_membership
            "w": v.get("website", ""),                     # website
            # YouTube presence
            "yt": len(r.get("youtube_data", {}).get("videos", [])) > 0,
            # Search text (name + location + country + tagline + region)
            "st": " ".join(filter(None, [
                r["name"],
                r.get("display_name", ""),
                v.get("location", ""),
                v.get("country", ""),
                v.get("region", ""),
                r.get("tagline", ""),
            ])).lower(),
        }
        races.append(entry)

    # Sort by score descending, then name
    races.sort(key=lambda x: (-x["sc"], x["n"]))

    index = {
        "generated": __import__("datetime").datetime.now().isoformat(),
        "count": len(races),
        "races": races,
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "race-index.json")
    with open(output_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))

    print(f"Generated race index: {len(races)} races → {output_path}")

    # Stats
    tiers = {}
    countries = set()
    disciplines = {}
    for r in races:
        tiers[r["t"]] = tiers.get(r["t"], 0) + 1
        countries.add(r["cc"])
        disciplines[r["di"]] = disciplines.get(r["di"], 0) + 1

    print(f"Tiers: {dict(sorted(tiers.items()))}")
    print(f"Countries: {len(countries)}")
    print(f"Disciplines: {dict(sorted(disciplines.items()))}")


if __name__ == "__main__":
    build_index()
