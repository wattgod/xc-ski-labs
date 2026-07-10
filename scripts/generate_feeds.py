#!/usr/bin/env python3
"""Generate crawler support feeds for XC Ski Labs."""

from __future__ import annotations

import argparse
import email.utils
import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
RACE_DATA_DIR = PROJECT_ROOT / "race-data"
OUTPUT_DIR = PROJECT_ROOT / "output"
SITE_URL = "https://xcskilabs.com"


MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def race_files(data_dir: Path) -> list[Path]:
    return sorted(p for p in data_dir.glob("*.json") if p.name != "_schema.json")


def load_races(data_dir: Path) -> list[dict[str, Any]]:
    races = []
    for path in race_files(data_dir):
        data = json.loads(path.read_text(encoding="utf-8"))
        race = data.get("race", {})
        if race.get("slug") and race.get("nordic_lab_rating"):
            races.append(race)
    return races


def date_specific(race: dict[str, Any]) -> str:
    return str((race.get("vitals") or {}).get("date_specific") or race.get("date_specific") or "").strip()


def parse_race_date(raw: str, today: date) -> date | None:
    text = raw.strip()
    if not text:
        return None
    iso = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", text)
    if iso:
        parsed = date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
        while parsed < today:
            try:
                parsed = parsed.replace(year=parsed.year + 1)
            except ValueError:
                parsed = parsed.replace(year=parsed.year + 1, day=28)
        return parsed
    match = re.search(
        r"(?:(20\d{2})\s*:\s*)?"
        r"(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2})",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    year = int(match.group(1)) if match.group(1) else today.year
    month = MONTHS[match.group(2).lower()]
    day = int(match.group(3))
    try:
        parsed = date(year, month, day)
    except ValueError:
        return None
    while parsed < today:
        try:
            parsed = parsed.replace(year=parsed.year + 1)
        except ValueError:
            parsed = parsed.replace(year=parsed.year + 1, day=28)
    return parsed


def race_name(race: dict[str, Any]) -> str:
    return str(race.get("display_name") or race.get("name") or race.get("slug"))


def write_llms(races: list[dict[str, Any]], output_dir: Path) -> None:
    count = len(races)
    text = f"""# XC Ski Labs

XC Ski Labs is a cross-country ski race guide and training site.

The site currently has {count} scored race profiles with course notes, climate context, logistics, ratings, and training links.

Key URLs:
- {SITE_URL}/
- {SITE_URL}/search/
- {SITE_URL}/training-plans/
- {SITE_URL}/questionnaire/
- {SITE_URL}/coaching/apply/
- {SITE_URL}/sitemap.xml
- {SITE_URL}/feed/races.xml
- {SITE_URL}/race-dates.json

Race profile URLs use: {SITE_URL}/race/{{slug}}/
"""
    (output_dir / "llms.txt").write_text(text, encoding="utf-8")


def write_race_dates(races: list[dict[str, Any]], output_dir: Path) -> None:
    mapping = {
        str(race.get("slug")): date_specific(race)
        for race in races
        if race.get("slug") and date_specific(race)
    }
    (output_dir / "race-dates.json").write_text(
        json.dumps(dict(sorted(mapping.items())), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_rss(races: list[dict[str, Any]], output_dir: Path, today: date) -> None:
    dated = []
    for race in races:
        parsed = parse_race_date(date_specific(race), today)
        if parsed and parsed >= today:
            dated.append((parsed, race))
    dated.sort(key=lambda item: (item[0], race_name(item[1]).lower()))

    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "XC Ski Labs Upcoming Races"
    ET.SubElement(channel, "link").text = SITE_URL + "/search/"
    ET.SubElement(channel, "description").text = "The next upcoming cross-country ski races in the XC Ski Labs index."
    ET.SubElement(channel, "lastBuildDate").text = email.utils.format_datetime(datetime.now(timezone.utc))

    for parsed, race in dated[:25]:
        slug = str(race.get("slug"))
        url = f"{SITE_URL}/race/{slug}/"
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = f"{race_name(race)} — {parsed.isoformat()}"
        ET.SubElement(item, "link").text = url
        ET.SubElement(item, "guid", isPermaLink="true").text = url
        ET.SubElement(item, "pubDate").text = email.utils.formatdate(
            datetime.combine(parsed, datetime.min.time()).timestamp(),
            usegmt=True,
        )
        vitals = race.get("vitals") or {}
        parts = [date_specific(race)]
        if vitals.get("location_badge"):
            parts.append(str(vitals.get("location_badge")))
        if vitals.get("distance_km"):
            parts.append(f"{vitals.get('distance_km')} km")
        ET.SubElement(item, "description").text = " · ".join(parts)

    feed_dir = output_dir / "feed"
    feed_dir.mkdir(parents=True, exist_ok=True)
    ET.indent(rss)
    ET.ElementTree(rss).write(feed_dir / "races.xml", encoding="utf-8", xml_declaration=True)


def write_robots(output_dir: Path) -> None:
    robots = output_dir / "robots.txt"
    if robots.exists():
        text = robots.read_text(encoding="utf-8")
        additions = []
        if "Sitemap:" not in text:
            additions.append(f"Sitemap: {SITE_URL}/sitemap.xml")
        if "llms.txt" not in text:
            additions.append(f"LLMs: {SITE_URL}/llms.txt")
        if additions:
            robots.write_text(text.rstrip() + "\n" + "\n".join(additions) + "\n", encoding="utf-8")
        return
    robots.write_text(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\nLLMs: {SITE_URL}/llms.txt\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate llms.txt, race RSS, and race date JSON")
    parser.add_argument("--data-dir", default=str(RACE_DATA_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    races = load_races(Path(args.data_dir))
    today = date.today()
    write_llms(races, output_dir)
    write_rss(races, output_dir, today)
    write_race_dates(races, output_dir)
    write_robots(output_dir)
    print(f"Generated feeds for {len(races)} races")


if __name__ == "__main__":
    main()
