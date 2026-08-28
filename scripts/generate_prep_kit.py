#!/usr/bin/env python3
"""Generate static XC Ski Labs race prep-kit pages.

Each profile renders to ``output/{slug}/prep-kit/index.html``. The content is
derived from the profile itself; generic preparation advice is deliberately
kept free of race-specific claims that are not present in race-data.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

try:
    from scripts.generate_race_pages import (
        build_cookie_consent,
        build_ga4_snippet,
        esc,
    )
except ModuleNotFoundError:  # Supports direct execution from scripts/.
    from generate_race_pages import build_cookie_consent, build_ga4_snippet, esc


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "race-data"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "output"
TOKENS_CSS = SCRIPT_DIR.parent / "tokens" / "tokens.css"


def load_race(path: Path) -> Optional[dict]:
    """Load one rated race profile, or return None for non-profile JSON."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"  SKIP {path.name}: {exc}")
        return None
    race = data.get("race")
    if not isinstance(race, dict) or not race.get("slug"):
        return None
    if not isinstance(race.get("nordic_lab_rating"), dict):
        return None
    return race


def _value(value: Any, fallback: str = "Check the organizer's latest details") -> str:
    return str(value).strip() if value not in (None, "") else fallback


def _distance_options(vitals: dict) -> list[str]:
    options = vitals.get("distance_options")
    if isinstance(options, list):
        clean = [str(option).strip() for option in options if str(option).strip()]
        if clean:
            return clean
    distance = vitals.get("distance_km")
    return [f"{distance:g} km" if isinstance(distance, (int, float)) else str(distance)] if distance else []


def _discipline_label(value: Any) -> str:
    return {
        "classic": "Classic",
        "skate": "Skate",
        "both": "Classic and skate",
    }.get(str(value).lower(), _value(value, "Confirm with the organizer"))


def _distance_number(option: str) -> Optional[float]:
    """Read the leading kilometre value from a profile distance option."""
    import re

    match = re.search(r"(\d+(?:\.\d+)?)\s*km\b", option, re.IGNORECASE)
    return float(match.group(1)) if match else None


def _effort_band(distance_km: Optional[float]) -> tuple[str, str, str]:
    """Return qualitative pacing/fueling guidance for a distance proxy.

    Profiles do not contain athlete pace or duration, so the bands avoid pace,
    calorie, carbohydrate, and fluid quantities. Skiers must validate their
    own effort duration and organizer support before race day.
    """
    if distance_km is None:
        return (
            "Course effort",
            "Start below your ceiling, settle into sustainable technique, and save a deliberate gear change for the final section.",
            "Base the carry on your expected effort duration. Use familiar food and drink, and confirm what the course provides.",
        )
    if distance_km <= 15:
        return (
            "Short effort",
            "Protect the opening minutes from an over-fast start, then build toward race effort once technique is settled.",
            "Arrive fed and hydrated. Carry a familiar backup if your expected duration or conditions call for it.",
        )
    if distance_km <= 30:
        return (
            "Middle-distance effort",
            "Hold a controlled opening pace, keep technique efficient through the middle, and commit after the last major course feature.",
            "Plan intake around your expected duration. Start with familiar fuel and map any organizer feed stations before race day.",
        )
    if distance_km <= 60:
        return (
            "Long-distance effort",
            "Ski the first section conservatively, pace climbs by repeatable effort, and preserve technique for the final third.",
            "Use an early, repeatable fueling rhythm based on your tested duration plan. Know what each feed station offers and carry a familiar fallback.",
        )
    return (
        "Very long effort",
        "Keep the opening well below the effort that feels available, manage climbs consistently, and protect technique before chasing places late.",
        "Build a sustained, tested fueling plan around expected duration. Carry redundancy and confirm every organizer feed before relying on it.",
    )


def build_logistics(race: dict) -> str:
    vitals = race.get("vitals", {})
    options = _distance_options(vitals)
    distances = ", ".join(options) if options else "Confirm with the organizer"
    rows = [
        ("Date", _value(vitals.get("date_specific") or vitals.get("date"))),
        ("Venue", _value(vitals.get("location") or vitals.get("location_badge"))),
        ("Distances", distances),
        ("Technique", _discipline_label(vitals.get("discipline"))),
        ("Registration", _value(vitals.get("registration"))),
        ("Course support", _value(vitals.get("aid_stations"))),
    ]
    cells = "".join(
        f'<div class="pk-detail"><dt>{esc(label)}</dt><dd>{esc(value)}</dd></div>'
        for label, value in rows
    )
    return f'<dl class="pk-details">{cells}</dl>'


def build_distance_guidance(race: dict) -> str:
    options = _distance_options(race.get("vitals", {})) or ["Your distance"]
    cards = []
    seen = set()
    for option in options:
        band, pacing, fueling = _effort_band(_distance_number(option))
        key = (option, band)
        if key in seen:
            continue
        seen.add(key)
        cards.append(f"""
        <article class="pk-card">
          <p class="pk-card-kicker">{esc(band)}</p>
          <h3>{esc(option)}</h3>
          <h4>Pacing</h4><p>{esc(pacing)}</p>
          <h4>Fueling outline</h4><p>{esc(fueling)}</p>
        </article>""")
    return '<div class="pk-card-grid">' + "".join(cards) + "</div>"


def build_course_notes(race: dict) -> str:
    course = race.get("course", {})
    primary = course.get("primary")
    features = course.get("features") if isinstance(course.get("features"), list) else []
    if not primary and not features:
        return ""
    feature_html = ""
    if features:
        feature_html = "<ul>" + "".join(f"<li>{esc(item)}</li>" for item in features) + "</ul>"
    return f"""
      <section class="pk-section">
        <div class="pk-heading"><span>02</span><h2>Course notes</h2></div>
        {f'<p class="pk-lead">{esc(primary)}</p>' if primary else ''}
        {feature_html}
      </section>"""


def build_checklist(race: dict) -> str:
    discipline = str(race.get("vitals", {}).get("discipline", "")).lower()
    technique_items = []
    if discipline in {"classic", "both"}:
        technique_items.append("Classic skis, poles, boots, and tested kick system")
    if discipline in {"skate", "both"}:
        technique_items.append("Skate skis, poles, and boots")
    if not technique_items:
        technique_items.append("Technique-specific skis, poles, and boots")
    items = technique_items + [
        "Bib, timing chip, and organizer instructions",
        "Race layers plus dry warm clothing for before and after",
        "Familiar food and drink matched to your tested duration plan",
        "Gloves, eyewear, hat or headband, and cold-weather backups",
        "Scraper, brush, cork, cleaning supplies, and ski ties",
        "Several tested wax options for the measured conditions",
        "Final wax decision made from current snow, air temperature, and organizer guidance",
    ]
    return "<ul class=\"pk-checklist\">" + "".join(
        f'<li><span aria-hidden="true">□</span>{esc(item)}</li>' for item in items
    ) + "</ul>"


def build_page(race: dict) -> str:
    slug = race["slug"]
    name = race.get("display_name") or race.get("name") or slug
    canonical = f"https://xcskilabs.com/race/{slug}/prep-kit/"
    course_notes = build_course_notes(race)
    section_offset = 1 if course_notes else 0
    tokens = TOKENS_CSS.read_text(encoding="utf-8")
    ga4 = build_ga4_snippet()
    consent = build_cookie_consent()

    css = """
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--gl-paper);color:var(--gl-carbon);font-family:var(--gl-font-editorial);line-height:1.6}.pk-nav{background:var(--gl-carbon);color:var(--gl-white);min-height:60px}.pk-nav-inner,.pk-wrap{width:min(100% - 40px,960px);margin:0 auto}.pk-nav-inner{min-height:60px;display:flex;align-items:center;justify-content:space-between;gap:20px}.pk-wordmark{font-family:var(--gl-font-display);font-weight:900;font-style:italic;letter-spacing:-.01em;color:var(--gl-white);text-decoration:none}.pk-wordmark span{color:var(--gl-swix-red)}.pk-nav a:last-child{min-height:44px;display:inline-flex;align-items:center;color:var(--gl-white);font-family:var(--gl-font-data);font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase}.pk-hero{background:var(--gl-carbon);color:var(--gl-white);border-bottom:6px solid var(--gl-swix-red);padding:64px 0}.pk-kicker,.pk-card-kicker{font-family:var(--gl-font-data);font-size:.68rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase}.pk-kicker{color:var(--gl-klister)}h1,h2{font-family:var(--gl-font-display);font-weight:900;font-style:italic;text-transform:uppercase;line-height:.96;letter-spacing:-.01em}h1{font-size:clamp(2.7rem,8vw,5.8rem);max-width:13ch;margin:12px 0 18px}.pk-hero p:last-child{max-width:58ch;margin:0;font-size:1.1rem}.pk-main{padding:56px 0 72px}.pk-section{padding:36px 0;border-bottom:3px solid var(--gl-carbon)}.pk-heading{display:flex;align-items:baseline;gap:12px;margin-bottom:24px}.pk-heading span{font-family:var(--gl-font-data);font-weight:700;color:var(--gl-swix-red)}.pk-heading h2{font-size:clamp(1.7rem,4vw,2.7rem);margin:0}.pk-lead{max-width:66ch}.pk-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border:3px solid var(--gl-carbon);margin:0}.pk-detail{padding:16px;border-bottom:1px solid var(--gl-hairline)}.pk-detail:nth-child(odd){border-right:1px solid var(--gl-hairline)}.pk-detail dt,.pk-card h4{font-family:var(--gl-font-data);font-size:.66rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase}.pk-detail dd{margin:6px 0 0}.pk-card-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.pk-card{background:var(--gl-white);border:3px solid var(--gl-carbon);padding:20px}.pk-card-kicker{color:var(--gl-swix-red);margin:0 0 8px}.pk-card h3{margin:0 0 18px;font-family:var(--gl-font-data);font-size:1.05rem}.pk-card h4{margin:18px 0 4px}.pk-card p{margin:0}.pk-checklist{list-style:none;padding:0;margin:0;columns:2;column-gap:24px}.pk-checklist li{break-inside:avoid;display:flex;gap:10px;padding:10px 0;border-bottom:1px solid var(--gl-hairline)}.pk-checklist span{font-family:var(--gl-font-data);font-weight:700}.pk-note{max-width:66ch;border-left:6px solid var(--gl-swix-red);padding:4px 0 4px 18px;font-style:italic}.pk-back{display:inline-flex;min-height:44px;align-items:center;margin-top:28px;background:var(--gl-carbon);color:var(--gl-white);padding:0 18px;font-family:var(--gl-font-data);font-size:.7rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;text-decoration:none}.pk-footer{background:var(--gl-carbon);color:var(--gl-white);border-top:6px solid var(--gl-swix-red);padding:28px 0;font-family:var(--gl-font-data);font-size:.68rem;letter-spacing:.12em;text-transform:uppercase}.pk-footer p{margin:0}@media(max-width:640px){.pk-nav-inner,.pk-wrap{width:min(100% - 28px,960px)}.pk-hero{padding:44px 0}.pk-details,.pk-card-grid{grid-template-columns:1fr}.pk-detail:nth-child(odd){border-right:0}.pk-checklist{columns:1}}
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(name)} Prep Kit | XC Ski Labs</title>
  <meta name="description" content="Race logistics, pacing, fueling, and a wax-day checklist for {esc(name)}.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{canonical}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&amp;family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&amp;display=swap" rel="stylesheet">
  {ga4}
  <style>{tokens}\n{css}</style>
</head>
<body>
  <nav class="pk-nav"><div class="pk-nav-inner"><a class="pk-wordmark" href="/">XC SKI <span>LABS</span></a><a href="/race/{esc(slug)}/">Race profile</a></div></nav>
  <header class="pk-hero"><div class="pk-wrap"><p class="pk-kicker">Race prep kit</p><h1>{esc(name)}</h1><p>Use the profile facts. Check the organizer. Make the final calls in race week.</p></div></header>
  <main class="pk-wrap pk-main">
    <section class="pk-section"><div class="pk-heading"><span>01</span><h2>Race logistics</h2></div>{build_logistics(race)}</section>
    {course_notes}
    <section class="pk-section"><div class="pk-heading"><span>{2 + section_offset:02d}</span><h2>Pacing and fueling</h2></div><p class="pk-lead">Distance is only a proxy for duration. Choose the outline that matches your event, then adjust it to your tested pace, conditions, and organizer support.</p>{build_distance_guidance(race)}</section>
    <section class="pk-section"><div class="pk-heading"><span>{3 + section_offset:02d}</span><h2>Gear and wax day</h2></div>{build_checklist(race)}<p class="pk-note">This profile does not contain a race-specific wax prescription. Measure current conditions and make the final wax call with products and processes you have already tested.</p></section>
    <a class="pk-back" href="/race/{esc(slug)}/">Back to the {esc(name)} race page &rarr;</a>
  </main>
  <footer class="pk-footer"><div class="pk-wrap"><p>XC Ski Labs &middot; Built for skiers who chase start lines &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/terms/">Terms</a></p></div></footer>
  {consent}
</body>
</html>"""


def generate_race(race: dict, output_dir: Path) -> Path:
    target = output_dir / race["slug"] / "prep-kit" / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_page(race), encoding="utf-8")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate XC Ski Labs prep-kit pages")
    parser.add_argument("--slug", help="Generate one race slug")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    paths = [data_dir / f"{args.slug}.json"] if args.slug else sorted(data_dir.glob("*.json"))
    generated = 0
    for path in paths:
        if path.name.startswith("_"):
            continue
        race = load_race(path)
        if race is None:
            if args.slug:
                print(f"ERROR: no valid race profile at {path}")
                return 1
            continue
        target = generate_race(race, output_dir)
        print(f"  OK {race['slug']} -> {target}")
        generated += 1
    if generated == 0:
        print("ERROR: no prep kits generated")
        return 1
    print(f"Generated {generated} prep kit{'s' if generated != 1 else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
