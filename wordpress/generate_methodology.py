#!/usr/bin/env python3
"""Generate the XC Ski Labs scoring methodology at /methodology/."""

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

from generate_about import build_cookie_consent, build_css, build_ga4_snippet


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "race-data"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

import sys

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_race_pages import build_nav_header
from scripts.scoring import CRITERIA, TIER_THRESHOLDS, calculate_overall_score


DIMENSION_GROUPS = (
    ("Race profile", ("distance", "elevation", "altitude", "field_size")),
    ("Standing", ("prestige", "international_draw", "competitive_depth")),
    ("Course and conditions", ("course_technicality", "snow_reliability", "grooming_quality", "accessibility")),
    ("Race-day experience", ("community", "scenery", "organization")),
)

DIMENSION_DESCRIPTIONS = {
    "distance": "The scale of the event&rsquo;s course distance.",
    "elevation": "The amount and character of climbing on the course.",
    "altitude": "The effect of the event&rsquo;s elevation above sea level.",
    "field_size": "The size of the participant field.",
    "prestige": "The event&rsquo;s standing and historical significance in the sport.",
    "international_draw": "The extent to which the race attracts skiers from outside its home region.",
    "competitive_depth": "The strength and depth of the competitive field.",
    "course_technicality": "The technical demands of the course and skiing.",
    "snow_reliability": "The likelihood of dependable snow conditions.",
    "grooming_quality": "The quality and consistency of course preparation.",
    "accessibility": "How practical the event is to reach and take part in.",
    "community": "The community and participant atmosphere around the event.",
    "scenery": "The quality of the landscape and setting along the course.",
    "organization": "The quality of event operations and logistics.",
}


def esc(value: object) -> str:
    return html.escape(str(value))


def load_races(data_dir: Path) -> list[dict]:
    races = []
    for path in sorted(data_dir.glob("*.json")):
        if path.name == "_schema.json":
            continue
        races.append(json.loads(path.read_text(encoding="utf-8"))["race"])
    return races


def tier_examples(races: list[dict]) -> dict[int, dict]:
    examples: dict[int, dict] = {}
    by_tier: dict[int, list[dict]] = defaultdict(list)
    for race in races:
        by_tier[race["nordic_lab_rating"]["tier"]].append(race)
    for tier, candidates in by_tier.items():
        examples[tier] = sorted(candidates, key=lambda race: race["name"].casefold())[0]
    return examples


def tier_range(tier: int) -> str:
    threshold = TIER_THRESHOLDS[tier]
    if tier == 1:
        return f"{threshold}&ndash;100"
    return f"{threshold}&ndash;{TIER_THRESHOLDS[tier - 1] - 1}"


def build_nav() -> str:
    return build_nav_header() + """
<script>
(function(){
  var toggle=document.querySelector('[data-nav-toggle]');
  var links=document.querySelector('.gl-nav-links');
  if(toggle&&links){toggle.addEventListener('click',function(){var open=links.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false')});}
})();
</script>
"""


def build_tier_rows(examples: dict[int, dict]) -> str:
    rows = []
    for tier in sorted(TIER_THRESHOLDS):
        example = examples[tier]
        rating = example["nordic_lab_rating"]
        rows.append(
            "<tr>"
            f"<td>TIER {tier}</td>"
            f"<td>{tier_range(tier)}</td>"
            f"<td><a href=\"/race/{esc(example['slug'])}/\">{esc(example['name'])}</a> ({rating['overall_score']})</td>"
            "</tr>"
        )
    return "\n".join(rows)


def build_dimensions() -> str:
    sections = []
    for group, dimensions in DIMENSION_GROUPS:
        items = "".join(
            f"<li><strong>{esc(dimension.replace('_', ' ').title())}.</strong> {DIMENSION_DESCRIPTIONS[dimension]}</li>"
            for dimension in dimensions
        )
        sections.append(f"<h3>{group}</h3><ul>{items}</ul>")
    return "\n".join(sections)


def worked_example(races: list[dict]) -> str:
    race = next((race for race in races if race["slug"] == "vasaloppet"), races[0])
    rating = race["nordic_lab_rating"]
    values = [rating[criterion] for criterion in CRITERIA]
    total = sum(values)
    calculated = calculate_overall_score(rating)
    return (
        f"<p><strong>{esc(race['name'])}.</strong> Its {len(CRITERIA)} dimension scores total "
        f"{total}. The calculation is round(({total} / {len(CRITERIA) * 5}) &times; 100) = "
        f"<strong>{calculated}</strong>. Its stored profile score is {rating['overall_score']} and its tier is TIER {rating['tier']}.</p>"
    )


def generate_html(races: list[dict]) -> str:
    title = "Methodology | XC Ski Labs"
    dimension_count = len(CRITERIA)
    denominator = dimension_count * 5
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="How XC Ski Labs scores and tiers cross-country ski races.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/methodology/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  {build_ga4_snippet()}
  <style>{build_css()}
  .gl-method-table {{ width: 100%; border-collapse: collapse; font-size: 0.95rem; }}
  .gl-method-table th, .gl-method-table td {{ padding: 12px 8px; border-bottom: 1px solid var(--gl-hairline); text-align: left; }}
  .gl-method-table th {{ border-top: 3px solid var(--gl-carbon); font-family: var(--gl-font-data); font-size: 0.7rem; letter-spacing: 0.06em; text-transform: uppercase; }}
  .gl-section h3 {{ font-family: var(--gl-font-data); font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }}
  .gl-section li {{ color: var(--gl-muted); margin: 0 0 10px; max-width: 680px; }}
  </style>
</head>
<body>
<a href="#main" class="gl-skip-link">Skip to content</a>
{build_nav()}
<main class="gl-page" id="main">
  <section class="gl-hero">
    <p class="gl-kicker">METHODOLOGY</p>
    <h1>How XC Ski Labs rates races.</h1>
    <p class="gl-hero-sub">Every race profile is scored by hand against the same {dimension_count} dimensions.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Overview</h2>
    <p>Ratings are a consistent way to compare cross-country ski races. Each profile is reviewed and scored by hand. The score is then calculated from the dimensions below; no separate cultural-impact bonus is added.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Tier system</h2>
    <table class="gl-method-table">
      <thead><tr><th>Tier</th><th>Score range</th><th>Example</th></tr></thead>
      <tbody>{build_tier_rows(tier_examples(races))}</tbody>
    </table>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Rated dimensions</h2>
    <p>Each dimension is rated from 1 to 5. The groups below organize the criteria for reading; the calculation gives every listed dimension equal weight.</p>
    {build_dimensions()}
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Scoring formula</h2>
    <p>The overall score is <strong>round((sum of {dimension_count} dimension scores / {denominator}) &times; 100)</strong>.</p>
    {worked_example(races)}
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Prestige overrides</h2>
    <p>A prestige score of 5 places a race in TIER 1 when its overall score is at least 75; otherwise it cannot fall below TIER 2. A prestige score of 4 can promote a race by one tier, but never into TIER 1.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">FAQ</h2>
    <h3>Who rates the races?</h3><p>XC Ski Labs reviews and scores every profile by hand.</p>
    <h3>How often are ratings updated?</h3><p>Ratings are updated when material race information or the scoring record changes.</p>
    <h3>Can organizers pay for a rating?</h3><p>No. Organizers cannot pay for a rating or a tier.</p>
  </section>
  <footer class="gl-footer">XC Ski Labs</footer>
</main>
{build_cookie_consent()}
</body>
</html>"""


def generate_page(data_dir: Path = DEFAULT_DATA_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Write output/methodology/index.html and return the generated path."""
    races = load_races(data_dir)
    if not races:
        raise ValueError(f"No race profiles found in {data_dir}")
    output_path = output_dir / "methodology" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(races), encoding="utf-8")
    print(f"Generated {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs methodology page.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    generate_page(args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
