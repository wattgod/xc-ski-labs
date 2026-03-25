#!/usr/bin/env python3
"""
XC Ski Labs — Homepage Generator

Generates index.html from race-data/*.json profiles.
Dynamic stats, tier showcases, and coverage grid — all from data.

Usage:
    python generate_homepage.py                          # default paths
    python generate_homepage.py --output-dir ../output   # custom output
    python generate_homepage.py --data-dir ../race-data --output-dir ../output
"""

import argparse
import html
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Optional

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "race-data"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "output"

# ── Constants ──────────────────────────────────────────────────

CRITERIA_COUNT = 14
TIER_COUNT = 4
TIER_THRESHOLDS = {1: 80, 2: 60, 3: 45}  # T4 is < 45
T2_HIGHLIGHT_COUNT = 6

DISCIPLINE_LABELS = {
    "classic": "Classic",
    "skate": "Skate",
    "both": "Classic &amp; Skate",
}

DISCIPLINE_CSS_CLASS = {
    "classic": "classic",
    "skate": "skate",
    "both": "both",
}


# ── Helpers ────────────────────────────────────────────────────

def esc(text: Any) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


def _safe_json_for_script(obj, **kwargs) -> str:
    """Serialize obj to JSON safe for embedding inside <script> tags."""
    raw = json.dumps(obj, **kwargs)
    return raw.replace("</", "<\\/")


def _parse_score(raw: Any) -> Optional[int]:
    """Safely parse a score value that might be int, float, string, or None."""
    if raw is None or raw == "":
        return None
    try:
        return int(float(str(raw)))
    except (ValueError, TypeError):
        return None


# ── Data Loading ───────────────────────────────────────────────

def load_all_races(data_dir: Path) -> list[dict]:
    """Load all race JSON profiles from data_dir, sorted by score descending."""
    races = []
    for fp in sorted(data_dir.glob("*.json")):
        if fp.name.startswith("_"):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            race = data.get("race", {})
            if not race.get("slug"):
                continue
            rating = race.get("nordic_lab_rating", {})
            score = _parse_score(rating.get("overall_score"))
            if score is None:
                continue
            races.append(race)
        except (json.JSONDecodeError, KeyError) as exc:
            print(f"  WARN: skipping {fp.name}: {exc}", file=sys.stderr)
    races.sort(key=lambda r: _parse_score(r.get("nordic_lab_rating", {}).get("overall_score")) or 0, reverse=True)
    return races


def get_tier(race: dict) -> int:
    """Return tier number from race data."""
    rating = race.get("nordic_lab_rating", {})
    tier = rating.get("tier")
    if tier is not None:
        return int(tier)
    score = _parse_score(rating.get("overall_score")) or 0
    if score >= 80:
        return 1
    if score >= 60:
        return 2
    if score >= 45:
        return 3
    return 4


def get_score(race: dict) -> int:
    return _parse_score(race.get("nordic_lab_rating", {}).get("overall_score")) or 0


def get_country(race: dict) -> str:
    return race.get("vitals", {}).get("country", "Unknown")


def get_discipline(race: dict) -> str:
    """Return discipline from rating or vitals."""
    d = race.get("nordic_lab_rating", {}).get("discipline")
    if d:
        return d
    return race.get("vitals", {}).get("discipline", "classic")


def get_distance_display(race: dict) -> str:
    """Return a clean distance string."""
    vitals = race.get("vitals", {})
    km = vitals.get("distance_km")
    if km is not None:
        return f"{km} km"
    return ""


def get_tagline(race: dict) -> str:
    """Return tagline, truncated if very long."""
    raw = race.get("tagline", "")
    if not raw:
        return ""
    # Trim to first sentence if over 120 chars
    if len(raw) > 150:
        for end in [".", "—", " — "]:
            idx = raw.find(end)
            if 30 < idx < 140:
                return raw[: idx + len(end)].rstrip()
    return raw


# ── HTML Builders ──────────────────────────────────────────────

def build_race_card(race: dict) -> str:
    """Generate a single race card HTML."""
    slug = esc(race.get("slug", ""))
    name = esc(race.get("display_name") or race.get("name", ""))
    tagline = esc(get_tagline(race))
    country = esc(get_country(race))
    distance = esc(get_distance_display(race))
    score = get_score(race)
    tier = get_tier(race)
    discipline = get_discipline(race)
    disc_label = DISCIPLINE_LABELS.get(discipline, esc(discipline.title()))
    disc_class = DISCIPLINE_CSS_CLASS.get(discipline, "classic")

    return f"""    <div class="race-card">
      <a href="race/{slug}/">
        <div class="rc-header">
          <h3>{name}</h3>
          <span class="tier-badge t{tier}">TIER {tier}</span>
        </div>
        <div class="rc-tagline">{tagline}</div>
        <div class="rc-meta">
          <span class="lbl">Country</span><span class="val">{country}</span>
          <span class="lbl">Distance</span><span class="val">{distance}</span>
        </div>
        <div class="rc-footer">
          <span class="discipline-badge {disc_class}">{disc_label}</span>
          <span class="score-display">{score}/100</span>
        </div>
      </a>
    </div>"""


def build_coverage_data(races: list[dict]) -> list[tuple[str, int]]:
    """Return sorted (country, count) pairs."""
    counter: Counter = Counter()
    for race in races:
        country = get_country(race)
        if country and country != "Unknown":
            counter[country] += 1
    return sorted(counter.items(), key=lambda x: (-x[1], x[0]))


def build_coverage_js(coverage: list[tuple[str, int]]) -> str:
    """Build the coverage grid JavaScript using safe JSON + textContent."""
    safe = _safe_json_for_script(coverage)
    return f"""<script>
var coverage = {safe};
coverage.sort(function(a, b) {{ return b[1] - a[1]; }});
var grid = document.getElementById("coverageGrid");
coverage.forEach(function(c) {{
  var div = document.createElement("div");
  div.className = "coverage-item";
  var countrySpan = document.createElement("span");
  countrySpan.className = "country";
  countrySpan.textContent = c[0];
  var countSpan = document.createElement("span");
  countSpan.className = "count";
  countSpan.textContent = c[1];
  div.appendChild(countrySpan);
  div.appendChild(countSpan);
  grid.appendChild(div);
}});
</script>"""


# ── Full Page ──────────────────────────────────────────────────

def generate_homepage(races: list[dict]) -> str:
    """Generate the complete homepage HTML."""
    # ── Compute stats ──
    race_count = len(races)
    countries = set(get_country(r) for r in races if get_country(r) != "Unknown")
    country_count = len(countries)

    # ── Tier buckets ──
    t1_races = [r for r in races if get_tier(r) == 1]
    t2_races = [r for r in races if get_tier(r) == 2]

    # ── T1 cards ──
    t1_cards = "\n\n".join(build_race_card(r) for r in t1_races)

    # ── T2 top N cards ──
    t2_top = t2_races[:T2_HIGHLIGHT_COUNT]
    t2_cards = "\n\n".join(build_race_card(r) for r in t2_top)
    t2_total = len(t2_races)

    # ── Coverage ──
    coverage = build_coverage_data(races)
    coverage_js = build_coverage_js(coverage)

    # ── JSON-LD ──
    jsonld_obj = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "XC Ski Labs",
        "url": "https://xcskilabs.com/",
        "description": (
            f"The world's most comprehensive cross-country ski race database. "
            f"{race_count}+ races across {country_count} countries."
        ),
        "potentialAction": {
            "@type": "SearchAction",
            "target": "https://xcskilabs.com/search/?q={search_term_string}",
            "query-input": "required name=search_term_string",
        },
    }
    jsonld_block = (
        '<script type="application/ld+json">\n'
        + _safe_json_for_script(jsonld_obj, indent=2)
        + "\n</script>"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XC Ski Labs — XC Ski Race Database</title>
<meta name="description" content="The world's most comprehensive cross-country ski race database. {race_count}+ races across {country_count} countries. Scored, ranked, and searchable.">
<meta name="keywords" content="cross-country ski races, XC skiing, marathon skiing, Worldloppet, Ski Classics, classic skiing, skate skiing">
<link rel="canonical" href="https://xcskilabs.com/">
<meta property="og:title" content="XC Ski Labs — XC Ski Race Database">
<meta property="og:description" content="{race_count}+ cross-country ski races across {country_count} countries. Scored, ranked, and searchable.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://xcskilabs.com/">
<script>
window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
(function(){{var c=(document.cookie.match(/xl_consent=([^;]+)/)||[])[1];
gtag('consent','default',{{'analytics_storage':c==='accepted'?'granted':'denied','ad_storage':'denied'}});
if(c==='declined')return;
var s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id=G-3JQLSQLPPM';document.head.appendChild(s);
gtag('js',new Date());gtag('config','G-3JQLSQLPPM')}})();
</script>
{jsonld_block}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --gl-nordic-night: #1a2332;
  --gl-fjord-blue: #2b4c7e;
  --gl-deep-powder: #354f6e;
  --gl-slate-steel: #4a5568;
  --gl-aurora-green: #1b7260;
  --gl-wax-orange: #b34a1a;
  --gl-glacier-teal: #357a88;
  --gl-birch-bark: #d4cdc4;
  --gl-silver-mist: #9ca8b8;
  --gl-frost-white: #e8edf2;
  --gl-ice-paper: #f0f3f7;
  --gl-tier-1: #1a2332;
  --gl-tier-2: #2b4c7e;
  --gl-tier-3: #4a5568;
  --gl-tier-4: #5a6d7e;
  --gl-font-data: 'Sometype Mono', monospace;
  --gl-font-editorial: 'Source Serif 4', serif;
  --gl-font-ui: 'Inter', sans-serif;
  --gl-border-width: 2px;
  --gl-border-heavy: 3px;
}}

*, *::before, *::after {{
  box-sizing: border-box;
  border-radius: 0 !important;
  box-shadow: none !important;
}}

body {{
  margin: 0;
  padding: 0;
  background: var(--gl-ice-paper);
  color: var(--gl-nordic-night);
  font-family: var(--gl-font-ui);
  line-height: 1.6;
}}

a {{ color: var(--gl-fjord-blue); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ── Hero ── */
.hero {{
  background: var(--gl-nordic-night);
  color: var(--gl-frost-white);
  padding: 80px 24px 64px;
  border-bottom: var(--gl-border-heavy) solid var(--gl-nordic-night);
}}

.hero-inner {{
  max-width: 960px;
  margin: 0 auto;
}}

.hero h1 {{
  font-family: var(--gl-font-editorial);
  font-size: clamp(2.5rem, 6vw, 4rem);
  font-weight: 700;
  line-height: 1.1;
  margin: 0 0 20px;
  letter-spacing: -0.02em;
}}

.hero-sub {{
  font-family: var(--gl-font-data);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--gl-glacier-teal);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 20px;
}}

.hero-desc {{
  font-family: var(--gl-font-editorial);
  font-size: 1.15rem;
  color: var(--gl-silver-mist);
  max-width: 600px;
  line-height: 1.5;
  margin-bottom: 40px;
}}

.hero-stats {{
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  margin-bottom: 40px;
}}

.hero-stat {{
  display: flex;
  flex-direction: column;
}}

.hero-stat .num {{
  font-family: var(--gl-font-data);
  font-size: 2.5rem;
  font-weight: 700;
  color: var(--gl-frost-white);
  line-height: 1;
}}

.hero-stat .label {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-silver-mist);
  margin-top: 4px;
}}

.hero-cta {{
  display: inline-block;
  padding: 14px 32px;
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: var(--gl-glacier-teal);
  color: var(--gl-frost-white);
  border: var(--gl-border-width) solid var(--gl-frost-white);
  text-decoration: none;
  transition: background 0.15s;
}}

.hero-cta:hover {{
  background: var(--gl-aurora-green);
  text-decoration: none;
}}

/* ── Tier Showcase ── */
.section {{
  max-width: 1200px;
  margin: 0 auto;
  padding: 64px 24px;
}}

.section-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 32px;
  border-bottom: var(--gl-border-width) solid var(--gl-nordic-night);
  padding-bottom: 12px;
}}

.section-title {{
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
}}

.section-link {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--gl-fjord-blue);
}}

/* ── Race Cards ── */
.race-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}}

.race-card {{
  background: #fff;
  border: var(--gl-border-width) solid var(--gl-nordic-night);
  display: flex;
  flex-direction: column;
  transition: transform 0.1s;
}}

.race-card:hover {{ transform: translateY(-2px); }}
.race-card a {{ color: inherit; text-decoration: none; display: block; }}
.race-card a:hover {{ text-decoration: none; }}

.rc-header {{
  padding: 14px 16px 8px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}}

.rc-header h3 {{
  font-family: var(--gl-font-editorial);
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1.3;
  margin: 0;
}}

.tier-badge {{
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 8px;
  color: var(--gl-frost-white);
  border: var(--gl-border-width) solid var(--gl-nordic-night);
  white-space: nowrap;
  flex-shrink: 0;
}}

.tier-badge.t1 {{ background: var(--gl-tier-1); }}
.tier-badge.t2 {{ background: var(--gl-tier-2); }}
.tier-badge.t3 {{ background: var(--gl-tier-3); }}

.rc-tagline {{
  padding: 0 16px 10px;
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  color: var(--gl-slate-steel);
  font-style: italic;
  line-height: 1.4;
}}

.rc-meta {{
  padding: 0 16px 12px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px 16px;
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
}}

.rc-meta .lbl {{
  color: var(--gl-silver-mist);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.rc-meta .val {{
  font-weight: 700;
}}

.rc-footer {{
  margin-top: auto;
  padding: 8px 16px;
  border-top: 1px solid var(--gl-birch-bark);
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.discipline-badge {{
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 8px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border: var(--gl-border-width) solid var(--gl-nordic-night);
}}

.discipline-badge.classic {{ background: var(--gl-nordic-night); color: var(--gl-frost-white); }}
.discipline-badge.skate {{ background: var(--gl-fjord-blue); color: var(--gl-frost-white); }}
.discipline-badge.both {{ background: var(--gl-wax-orange); color: var(--gl-frost-white); }}

.score-display {{
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--gl-slate-steel);
}}

/* ── Coverage Map (text version) ── */
.coverage-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}}

.coverage-item {{
  background: #fff;
  border: var(--gl-border-width) solid var(--gl-nordic-night);
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.coverage-item .country {{
  font-family: var(--gl-font-ui);
  font-size: 0.9rem;
  font-weight: 600;
}}

.coverage-item .count {{
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-fjord-blue);
}}

/* ── About ── */
.about-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}}

.about-card {{
  background: #fff;
  border: var(--gl-border-width) solid var(--gl-nordic-night);
  padding: 24px;
}}

.about-card h3 {{
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 12px;
  color: var(--gl-fjord-blue);
}}

.about-card p {{
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--gl-slate-steel);
  margin: 0;
}}

/* ── Footer ── */
footer {{
  background: var(--gl-nordic-night);
  color: var(--gl-silver-mist);
  padding: 40px 24px;
  border-top: var(--gl-border-heavy) solid var(--gl-nordic-night);
}}

.footer-inner {{
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
}}

.footer-brand {{
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gl-glacier-teal);
}}

.footer-tagline {{
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  font-style: italic;
  color: var(--gl-silver-mist);
}}

.footer-link {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-glacier-teal);
}}

/* ── Focus ── */
a:focus-visible, button:focus-visible {{
  outline: 3px solid var(--gl-wax-orange);
  outline-offset: 2px;
}}

/* ── Nav Header ── */
.gl-nav-header {{
  background: var(--gl-nordic-night);
  border-bottom: var(--gl-border-heavy) solid var(--gl-fjord-blue);
  position: sticky;
  top: 0;
  z-index: 999;
}}
.gl-nav-inner {{
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
}}
.gl-nav-logo {{
  font-family: var(--gl-font-data);
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--gl-frost-white);
  text-decoration: none;
  letter-spacing: 0.05em;
}}
.gl-nav-logo:hover {{ color: var(--gl-glacier-teal); }}
.gl-nav-links {{
  display: flex;
  gap: 0;
  align-items: center;
  list-style: none;
  margin: 0;
  padding: 0;
}}
.gl-nav-item {{
  position: relative;
}}
.gl-nav-item > a {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-silver-mist);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 16px 14px;
  display: block;
}}
.gl-nav-item > a:hover {{
  color: var(--gl-frost-white);
}}
.gl-nav-dropdown {{
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  background: var(--gl-nordic-night);
  border: 2px solid var(--gl-fjord-blue);
  min-width: 200px;
  z-index: 1001;
  padding: 8px 0;
}}
.gl-nav-item:hover .gl-nav-dropdown {{
  display: block;
}}
.gl-nav-dropdown a {{
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--gl-silver-mist);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 16px;
  display: block;
}}
.gl-nav-dropdown a:hover {{
  color: var(--gl-frost-white);
  background: var(--gl-fjord-blue);
}}
.gl-nav-hamburger {{
  display: none;
  background: none;
  border: none;
  color: var(--gl-frost-white);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 4px;
}}

/* ── Cookie Consent ── */
.gl-cookie-banner {{
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-nordic-night);
  border-top: var(--gl-border-heavy) solid var(--gl-wax-orange);
  padding: 16px 20px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  color: var(--gl-frost-white);
  display: none;
}}
.gl-cookie-banner.show {{ display: block; }}
.gl-cookie-inner {{
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}}
.gl-cookie-btns {{
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}}
.gl-cookie-btn {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 8px 16px;
  border: 2px solid var(--gl-frost-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.gl-cookie-accept {{
  background: var(--gl-aurora-green);
  color: var(--gl-frost-white);
}}
.gl-cookie-decline {{
  background: transparent;
  color: var(--gl-silver-mist);
  border-color: var(--gl-slate-steel);
}}

/* ── Responsive ── */
@media (max-width: 640px) {{
  .hero {{ padding: 48px 16px 40px; }}
  .hero-stats {{ gap: 20px; }}
  .hero-stat .num {{ font-size: 2rem; }}
  .section {{ padding: 40px 16px; }}
  .race-grid {{ grid-template-columns: 1fr; }}
  .coverage-grid {{ grid-template-columns: 1fr 1fr; }}
  .footer-inner {{ flex-direction: column; text-align: center; }}
  .gl-nav-hamburger {{ display: block; }}
  .gl-nav-links {{
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--gl-nordic-night);
    flex-direction: column;
    padding: 16px 20px;
    gap: 0;
    border-bottom: var(--gl-border-heavy) solid var(--gl-fjord-blue);
  }}
  .gl-nav-links.open {{ display: flex; }}
  .gl-nav-dropdown {{
    position: static;
    border: none;
    padding: 0 0 0 16px;
    display: block;
  }}
  .gl-nav-item > a {{ padding: 12px 0; }}
}}
</style>
</head>
<body>

<!-- ── Nav Header ── -->
<header class="gl-nav-header">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo">XC SKI LABS</a>
    <button class="gl-nav-hamburger" onclick="document.querySelector('.gl-nav-links').classList.toggle('open')" aria-label="Menu">&#9776;</button>
    <ul class="gl-nav-links">
      <li class="gl-nav-item">
        <a href="/search/">Races</a>
        <div class="gl-nav-dropdown"><a href="/search/">All XC Ski Races</a></div>
      </li>
      <li class="gl-nav-item">
        <a href="/training-plans/">Products</a>
        <div class="gl-nav-dropdown"><a href="/training-plans/">Training Plans</a></div>
      </li>
      <li class="gl-nav-item">
        <a href="/coaching/apply/">Services</a>
        <div class="gl-nav-dropdown"><a href="/coaching/apply/">Coaching</a></div>
      </li>
      <li class="gl-nav-item">
        <a href="/about/">About</a>
      </li>
    </ul>
  </div>
</header>

<!-- ── Hero ── -->
<section class="hero">
  <div class="hero-inner">
    <h1>XC SKI LABS</h1>
    <p class="hero-sub">XC Ski Race Database &mdash; Classic &amp; Skate</p>
    <p class="hero-desc">Every marathon, every loppet, every citizen race worth lining up for. Scored on {CRITERIA_COUNT} criteria. Ranked into tiers. Searchable.</p>
    <div class="hero-stats">
      <div class="hero-stat">
        <span class="num" id="statRaces">{race_count}</span>
        <span class="label">Races</span>
      </div>
      <div class="hero-stat">
        <span class="num" id="statCountries">{country_count}</span>
        <span class="label">Countries</span>
      </div>
      <div class="hero-stat">
        <span class="num">{CRITERIA_COUNT}</span>
        <span class="label">Criteria</span>
      </div>
      <div class="hero-stat">
        <span class="num">{TIER_COUNT}</span>
        <span class="label">Tiers</span>
      </div>
    </div>
    <a href="/search/" class="hero-cta">Search All Races</a>
  </div>
</section>

<!-- ── Tier 1 Showcase ── -->
<div class="section">
  <div class="section-header">
    <span class="section-title">Tier 1 &mdash; The Monuments</span>
    <a href="/search/" class="section-link">View All &rarr;</a>
  </div>
  <div class="race-grid" id="tier1Grid">
{t1_cards}
  </div>
</div>

<!-- ── Tier 2 Highlights ── -->
<div class="section" style="background: #fff; margin: 0; max-width: none; padding-left: calc((100% - 1200px)/2 + 24px); padding-right: calc((100% - 1200px)/2 + 24px);">
  <div class="section-header">
    <span class="section-title">Tier 2 &mdash; Must-Do Races</span>
    <a href="/search/" class="section-link">View All {t2_total} &rarr;</a>
  </div>
  <div class="race-grid">
{t2_cards}
  </div>
</div>

<!-- ── Coverage ── -->
<div class="section">
  <div class="section-header">
    <span class="section-title">Global Coverage</span>
  </div>
  <div class="coverage-grid" id="coverageGrid"></div>
</div>

<!-- ── What We Score ── -->
<div class="section" style="background: #fff; margin: 0; max-width: none; padding-left: calc((100% - 1200px)/2 + 24px); padding-right: calc((100% - 1200px)/2 + 24px);">
  <div class="section-header">
    <span class="section-title">How We Score</span>
  </div>
  <div class="about-grid">
    <div class="about-card">
      <h3>{CRITERIA_COUNT} Criteria</h3>
      <p>Distance, elevation, altitude, field size, prestige, international draw, course technicality, snow reliability, grooming quality, accessibility, community, scenery, organization, and competitive depth. Each rated 1-5.</p>
    </div>
    <div class="about-card">
      <h3>{TIER_COUNT} Tiers</h3>
      <p>Tier 1 (&ge;80) &mdash; the monuments. Tier 2 (&ge;60) &mdash; must-do races. Tier 3 (&ge;45) &mdash; solid events. Tier 4 (&lt;45) &mdash; niche picks. Prestige overrides promote races with outsized cultural significance.</p>
    </div>
    <div class="about-card">
      <h3>Every Race, Every Detail</h3>
      <p>Course profiles, climate data, wax conditions, travel logistics, YouTube video curation with skier intel &mdash; everything you need to pick your next start line.</p>
    </div>
  </div>
</div>

<!-- ── Footer ── -->
<footer>
  <div class="footer-inner">
    <span class="footer-brand">XC Ski Labs</span>
    <span class="footer-tagline">Built for skiers who chase start lines.</span>
    <div style="display:flex;gap:16px;flex-wrap:wrap">
      <a href="/search/" class="footer-link">Races</a>
      <a href="/training-plans/" class="footer-link">Training Plans</a>
      <a href="/coaching/apply/" class="footer-link">Coaching</a>
    </div>
  </div>
</footer>

<!-- ── Cookie Consent ── -->
<div class="gl-cookie-banner" id="gl-cookie-banner">
  <div class="gl-cookie-inner">
    <div>We use cookies for analytics to improve the experience. <a href="/privacy/" style="color:var(--gl-glacier-teal)">Privacy policy</a>.</div>
    <div class="gl-cookie-btns">
      <button class="gl-cookie-btn gl-cookie-accept" onclick="xlConsent('accepted')">Accept</button>
      <button class="gl-cookie-btn gl-cookie-decline" onclick="xlConsent('declined')">Decline</button>
    </div>
  </div>
</div>
<script>
function xlConsent(c){{document.cookie='xl_consent='+c+';path=/;max-age=31536000;SameSite=Lax;Secure';if(typeof gtag==='function')gtag('consent','update',{{'analytics_storage':c==='accepted'?'granted':'denied'}});document.getElementById('gl-cookie-banner').classList.remove('show')}}
(function(){{if(!/xl_consent=/.test(document.cookie))document.getElementById('gl-cookie-banner').classList.add('show')}})();
</script>

{coverage_js}
</body>
</html>"""


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate XC Ski Labs homepage from race data."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing race JSON profiles (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for index.html (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    output_dir = args.output_dir.resolve()

    if not data_dir.is_dir():
        print(f"ERROR: data directory not found: {data_dir}", file=sys.stderr)
        sys.exit(1)

    # ── Load races ──
    print(f"Loading race profiles from {data_dir} ...")
    races = load_all_races(data_dir)
    if not races:
        print("ERROR: no valid race profiles found.", file=sys.stderr)
        sys.exit(1)

    # ── Stats ──
    countries = set(get_country(r) for r in races if get_country(r) != "Unknown")
    t1 = [r for r in races if get_tier(r) == 1]
    t2 = [r for r in races if get_tier(r) == 2]
    t3 = [r for r in races if get_tier(r) == 3]
    t4 = [r for r in races if get_tier(r) == 4]
    print(f"  {len(races)} races | {len(countries)} countries")
    print(f"  T1: {len(t1)} | T2: {len(t2)} | T3: {len(t3)} | T4: {len(t4)}")

    # ── Generate ──
    html_content = generate_homepage(races)

    # ── Write ──
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "index.html"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"  Wrote {out_path} ({len(html_content):,} bytes)")


if __name__ == "__main__":
    main()
