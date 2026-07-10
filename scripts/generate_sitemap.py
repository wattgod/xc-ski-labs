#!/usr/bin/env python3
"""
XC Ski Labs — Sitemap Generator

Generates a standard XML sitemap (output/sitemap.xml) from race profile data.

Usage:
    python generate_sitemap.py
    python generate_sitemap.py --data-dir ../race-data --output-dir ../output
    python generate_sitemap.py --domain custom.domain.com
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString

SCRIPT_DIR = Path(__file__).resolve().parent

# Priority and changefreq by tier
TIER_CONFIG = {
    1: {"priority": "0.8", "changefreq": "monthly"},
    2: {"priority": "0.7", "changefreq": "monthly"},
    3: {"priority": "0.6", "changefreq": "monthly"},
    4: {"priority": "0.5", "changefreq": "monthly"},
}


def load_race_profiles(data_dir):
    """Load all race JSON profiles that have a valid nordic_lab_rating.

    Skips files starting with '_' (e.g., _schema.json).
    Returns list of dicts with slug, tier, and overall_score.
    """
    profiles = []
    for path in sorted(data_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            race = data.get("race", {})
            slug = race.get("slug")
            if not slug:
                print(f"  WARNING: no slug in {path.name}, skipping")
                continue
            rating = race.get("nordic_lab_rating")
            if not rating or not isinstance(rating, dict):
                continue
            tier = rating.get("tier")
            overall_score = rating.get("overall_score", 0)
            if tier is None:
                continue
            profiles.append({
                "slug": slug,
                "tier": int(tier),
                "overall_score": int(overall_score) if overall_score else 0,
            })
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"  WARNING: failed to parse {path.name}: {e}")
    return profiles


def sort_profiles(profiles):
    """Sort by tier ascending, then overall_score descending within each tier."""
    return sorted(profiles, key=lambda p: (p["tier"], -p["overall_score"]))


def generate_sitemap(domain, profiles):
    """Build sitemap XML from sorted profiles list.

    Returns (xml_bytes, tier_counts).
    """
    today = date.today().isoformat()

    urlset = Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    def add_url(loc, priority, changefreq):
        url_el = SubElement(urlset, "url")
        SubElement(url_el, "loc").text = loc
        SubElement(url_el, "lastmod").text = today
        SubElement(url_el, "changefreq").text = changefreq
        SubElement(url_el, "priority").text = priority

    # Static pages
    add_url(f"{domain}/", "1.0", "weekly")
    add_url(f"{domain}/search/", "0.8", "weekly")

    # Race pages — already sorted
    tier_counts = {}
    for p in profiles:
        tier = p["tier"]
        config = TIER_CONFIG.get(tier, TIER_CONFIG[4])
        add_url(
            f"{domain}/race/{p['slug']}/",
            config["priority"],
            config["changefreq"],
        )
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    # Pretty-print XML
    raw_xml = tostring(urlset, encoding="unicode")
    dom = parseString(raw_xml)
    pretty = dom.toprettyxml(indent="  ", encoding="UTF-8")

    return pretty, tier_counts


def main():
    parser = argparse.ArgumentParser(
        description="Generate XML sitemap for XC Ski Labs race pages"
    )
    parser.add_argument(
        "--data-dir",
        default=str(SCRIPT_DIR.parent / "race-data"),
        help="Path to race-data directory (default: ../race-data)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(SCRIPT_DIR.parent / "output"),
        help="Path to output directory (default: ../output)",
    )
    parser.add_argument(
        "--domain",
        default="xcskilabs.com",
        help="Domain name without protocol (default: xcskilabs.com)",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_path = output_dir / "sitemap.xml"

    # Normalize domain — ensure https:// prefix, strip trailing slash
    domain = args.domain.rstrip("/")
    if not domain.startswith("http"):
        domain = f"https://{domain}"

    print(f"Generating sitemap for {domain}")
    print(f"Reading race profiles from {data_dir}")

    if not data_dir.is_dir():
        print(f"ERROR: data directory not found: {data_dir}")
        sys.exit(1)

    profiles = load_race_profiles(data_dir)
    if not profiles:
        print("ERROR: No valid race profiles found")
        sys.exit(1)

    sorted_profiles = sort_profiles(profiles)
    xml_bytes, tier_counts = generate_sitemap(domain, sorted_profiles)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(xml_bytes)

    total_urls = 2 + len(sorted_profiles)
    print(f"\nWrote {output_path}")
    print(f"  Total URLs: {total_urls}")
    print(f"  Static:     2 (homepage, search)")
    print(f"  Races:      {len(sorted_profiles)}")
    for tier in sorted(tier_counts):
        print(f"    T{tier}: {tier_counts[tier]}")


if __name__ == "__main__":
    main()
