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
TOKENS_CSS = SCRIPT_DIR.parent / "tokens" / "tokens.css"

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


def load_tokens_css() -> str:
    """Read shared Wax Bench tokens for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


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


def build_tier_row(race: dict) -> str:
    """Generate a single Tier 1 table row."""
    slug = esc(race.get("slug", ""))
    name = esc(race.get("display_name") or race.get("name", ""))
    country = esc(get_country(race))
    distance = esc(get_distance_display(race))
    score = get_score(race)
    tier = get_tier(race)
    discipline = DISCIPLINE_LABELS.get(get_discipline(race), esc(get_discipline(race).title()))
    score_class = " score-red" if tier == 1 else ""

    return f"""    <tr>
      <td><span class="tchip">T{tier}</span> {name}</td>
      <td>{country}</td>
      <td class="mono r">{distance}</td>
      <td>{discipline}</td>
      <td class="mono r{score_class}">{score}</td>
      <td class="r"><a class="rowlink" href="/race/{slug}/">READ &rarr;</a></td>
    </tr>"""


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
    t1_rows = "\n".join(build_tier_row(r) for r in t1_races)

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
    tokens_css = load_tokens_css()

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
{tokens_css}

*, *::before, *::after {{
  box-sizing: border-box;
  border-radius: 0 !important;
  box-shadow: none !important;
}}

body {{
  margin: 0;
  padding: 0;
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-editorial);
  line-height: 1.6;
}}

a {{ color: var(--gl-swix-red); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* ── Hero ── */
.hero {{
  background: var(--gl-swix-red);
  color: var(--gl-white);
  position: relative;
  overflow: hidden;
  padding: 80px 24px 64px;
  border-bottom: 4px solid var(--gl-carbon);
}}

.hero::after {{
  content: "";
  position: absolute;
  top: 0;
  right: -60px;
  bottom: 0;
  width: 420px;
  background: repeating-linear-gradient(115deg, var(--gl-red-deep) 0 28px, var(--gl-swix-red) 28px 56px);
}}

.hero-inner {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  position: relative;
  z-index: 1;
}}

.hero h1 {{
  font-family: var(--gl-font-display);
  font-size: clamp(3rem, 8vw, 5rem);
  font-weight: 900;
  font-style: italic;
  line-height: .92;
  text-transform: uppercase;
  margin: 0 0 20px;
  letter-spacing: 0;
  max-width: 13ch;
}}

.hero-sub {{
  font-family: var(--gl-font-data);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--gl-klister);
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 20px;
}}

.hero-desc {{
  font-family: var(--gl-font-editorial);
  font-size: 1.15rem;
  color: var(--gl-white);
  max-width: 600px;
  line-height: 1.5;
  margin-bottom: 28px;
}}

.hero-stats {{
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
  margin-top: 28px;
  margin-bottom: 0;
  color: var(--gl-klister);
}}

.hero-stat {{
  display: flex;
  flex-direction: column;
}}

.hero-stat .num {{
  font-family: var(--gl-font-data);
  font-size: 1rem;
  font-weight: 700;
  color: var(--gl-klister);
  line-height: 1;
}}

.hero-stat .label {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-muted);
  margin-top: 4px;
}}

.hero-cta {{
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 14px 32px;
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  background: var(--gl-white);
  color: var(--gl-carbon);
  border: 2px solid var(--gl-white);
}}

.hero-cta.secondary {{
  background: var(--gl-carbon);
  color: var(--gl-white);
  border-color: var(--gl-carbon);
  margin-left: 10px;
}}

.hero-cta:hover {{
  text-decoration: none;
}}

.mono {{ font-family: var(--gl-font-data); }}
.r {{ text-align: right; }}

.db-band {{
  background: var(--gl-paper);
  border-bottom: 4px solid var(--gl-carbon);
}}

.db-inner {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: 44px 24px;
}}

.section-heading {{
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin: 0 0 20px;
}}

.section-heading .num {{
  color: var(--gl-swix-red);
  font-family: var(--gl-font-display);
  font-weight: 900;
  font-style: italic;
}}

.section-heading h2 {{
  margin: 0;
  font-family: var(--gl-font-display);
  font-size: 1.45rem;
  font-weight: 900;
  font-style: italic;
  line-height: 1;
  text-transform: uppercase;
}}

.tier-table {{
  width: 100%;
  border-collapse: collapse;
}}

.tier-table th {{
  padding: 8px 10px;
  border-bottom: 3px solid var(--gl-carbon);
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: .62rem;
  font-weight: 700;
  letter-spacing: .2em;
  text-align: left;
  text-transform: uppercase;
}}

.tier-table td {{
  padding: 13px 10px;
  border-bottom: 1px solid var(--gl-hairline);
  font-size: .98rem;
}}

.tchip {{
  display: inline-block;
  margin-right: 8px;
  background: var(--gl-carbon);
  color: var(--gl-white);
  padding: 3px 8px;
  font-family: var(--gl-font-data);
  font-size: .56rem;
  font-weight: 700;
  letter-spacing: .1em;
}}

.score-red,
.rowlink {{
  color: var(--gl-swix-red);
  font-weight: 700;
}}

.rowlink {{
  font-family: var(--gl-font-data);
  font-size: .64rem;
  letter-spacing: .14em;
  text-decoration: none;
  white-space: nowrap;
}}

/* ── Tier Showcase ── */
.section {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: 64px 24px;
}}

.section-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 32px;
  border-bottom: 2px solid var(--gl-carbon);
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
  color: var(--gl-swix-red);
}}

/* ── Race Cards ── */
.race-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}}

.race-card {{
  background: var(--gl-white);
  border: 2px solid var(--gl-carbon);
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
  color: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  white-space: nowrap;
  flex-shrink: 0;
}}

.tier-badge.t1 {{ background: var(--gl-carbon); }}
.tier-badge.t2 {{ background: var(--gl-carbon); }}
.tier-badge.t3 {{ background: var(--gl-carbon); }}

.rc-tagline {{
  padding: 0 16px 10px;
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  color: var(--gl-muted);
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
  color: var(--gl-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}

.rc-meta .val {{
  font-weight: 700;
}}

.rc-footer {{
  margin-top: auto;
  padding: 8px 16px;
  border-top: 1px solid var(--gl-hairline);
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
  border: 2px solid var(--gl-carbon);
}}

.discipline-badge.classic {{ background: var(--gl-carbon); color: var(--gl-white); }}
.discipline-badge.skate {{ background: var(--gl-swix-red); color: var(--gl-white); }}
.discipline-badge.both {{ background: var(--gl-swix-red); color: var(--gl-white); }}

.score-display {{
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--gl-muted);
}}

/* ── Coverage Map (text version) ── */
.coverage-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}}

.coverage-item {{
  background: var(--gl-white);
  border: 2px solid var(--gl-carbon);
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
  color: var(--gl-swix-red);
}}

/* ── About ── */
.about-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}}

.about-card {{
  background: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  padding: 24px;
}}

.about-card h3 {{
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 0 0 12px;
  color: var(--gl-swix-red);
}}

.about-card p {{
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--gl-muted);
  margin: 0;
}}

/* ── Footer ── */
footer {{
  background: var(--gl-swix-red);
  color: var(--gl-white);
  padding: 0 24px;
  border-top: 0;
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
  font-family: var(--gl-font-display);
  font-size: 1rem;
  font-weight: 900;
  font-style: italic;
  text-transform: uppercase;
  color: var(--gl-white);
}}

.footer-tagline {{
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  font-style: italic;
  color: var(--gl-muted);
}}

.footer-link {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-klister);
}}

.gl-ladder {{
  background: var(--gl-carbon);
  color: var(--gl-white);
}}

.gl-ladder-inner {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: 52px var(--gl-space-5) 56px;
}}

.gl-ladder h2 {{
  margin: 0 0 4px;
  font-family: var(--gl-font-display);
  font-size: 1.9rem;
  font-weight: 900;
  font-style: italic;
  line-height: 1;
  text-transform: uppercase;
}}

.gl-ladder-lead {{
  margin: 0 0 var(--gl-space-6);
  color: var(--gl-hairline);
  font-style: italic;
}}

.gl-rungs {{
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--gl-space-4);
}}

.gl-rung {{
  background: var(--gl-carbon);
  border: 1px solid var(--gl-muted);
  border-top: 6px solid var(--gl-swix-red);
  padding: var(--gl-space-5);
}}

.gl-rung-kicker,
.gl-rung-price {{
  color: var(--gl-klister);
  font-family: var(--gl-font-data);
  font-size: .62rem;
  font-weight: 700;
  letter-spacing: .2em;
  text-transform: uppercase;
}}

.gl-rung h3 {{
  margin: var(--gl-space-2) 0;
  font-family: var(--gl-font-display);
  font-size: 1.05rem;
  font-weight: 900;
  font-style: italic;
  text-transform: uppercase;
}}

.gl-rung p {{
  margin: 0 0 var(--gl-space-4);
  color: var(--gl-hairline);
  font-size: .9rem;
  line-height: 1.55;
}}

.gl-rung-btn {{
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  margin-top: var(--gl-space-3);
  border: 2px solid var(--gl-white);
  color: var(--gl-white);
  padding: 0 var(--gl-space-4);
  font-family: var(--gl-font-data);
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .14em;
  text-decoration: none;
  text-transform: uppercase;
}}

.gl-rung-btn.apply {{
  border-color: var(--gl-swix-red);
  background: var(--gl-swix-red);
}}

/* ── Focus ── */
a:focus-visible, button:focus-visible {{
  outline: 3px solid var(--gl-swix-red);
  outline-offset: 2px;
}}

/* ── Nav Header ── */
.gl-nav-header {{
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-swix-red);
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
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.05em;
}}
.gl-nav-logo:hover {{ color: var(--gl-klister); }}
.gl-nav-logo em {{ color: var(--gl-swix-red); font-style: italic; }}
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
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 16px 14px;
  display: block;
}}
.gl-nav-item > a:hover {{
  color: var(--gl-white);
}}
.gl-nav-dropdown {{
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  background: var(--gl-carbon);
  border: 2px solid var(--gl-swix-red);
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
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 16px;
  display: block;
}}
.gl-nav-dropdown a:hover {{
  color: var(--gl-white);
  background: var(--gl-swix-red);
}}
.gl-nav-hamburger {{
  display: none;
  background: none;
  border: none;
  color: var(--gl-white);
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
  background: var(--gl-carbon);
  border-top: 3px solid var(--gl-swix-red);
  padding: 16px 20px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  color: var(--gl-white);
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
  border: 2px solid var(--gl-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}}
.gl-cookie-accept {{
  background: var(--gl-swix-red);
  color: var(--gl-white);
}}
.gl-cookie-decline {{
  background: transparent;
  color: var(--gl-muted);
  border-color: var(--gl-muted);
}}

/* ── Responsive ── */
@media (max-width: 640px) {{
  .hero {{ padding: 48px 16px 40px; }}
  .hero-stats {{ gap: 20px; }}
  .hero-cta.secondary {{ margin: 10px 0 0; }}
  .section {{ padding: 40px 16px; }}
  .race-grid {{ grid-template-columns: 1fr; }}
  .coverage-grid {{ grid-template-columns: 1fr 1fr; }}
  .gl-rungs {{ grid-template-columns: 1fr; }}
  .tier-table th:nth-child(3),
  .tier-table td:nth-child(3),
  .tier-table th:nth-child(4),
  .tier-table td:nth-child(4) {{ display: none; }}
  .footer-inner {{ flex-direction: column; text-align: center; }}
  .gl-nav-hamburger {{ display: block; }}
  .gl-nav-links {{
    display: none;
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    background: var(--gl-carbon);
    flex-direction: column;
    padding: 16px 20px;
    gap: 0;
    border-bottom: 3px solid var(--gl-swix-red);
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
    <a href="/" class="gl-nav-logo" aria-label="XC SKI LABS">XC SKI <em>LABS</em></a>
    <button class="gl-nav-hamburger" onclick="document.querySelector('.gl-nav-links').classList.toggle('open')" aria-label="Menu">&#9776;</button>
    <ul class="gl-nav-links">
      <li class="gl-nav-item">
        <a href="/search/">Races</a>
        <div class="gl-nav-dropdown"><a href="/search/">All XC Ski Races</a></div>
      </li>
      <li class="gl-nav-item">
        <a href="/training-plans/">Plans</a>
              </li>
      <li class="gl-nav-item">
        <a href="/coaching/apply/">Coaching</a>
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
    <p class="hero-sub">The XC Ski Race Database</p>
    <h1>Every loppet, rated.</h1>
    <p class="hero-desc">{race_count} races scored on {CRITERIA_COUNT} criteria and ranked into four tiers, from the Birkebeiner to the backyard classics.</p>
    <a href="/search/" class="hero-cta">Search the races</a>
    <a href="/about/" class="hero-cta secondary">How we rate</a>
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
  </div>
</section>

<!-- ── Tier 1 Table ── -->
<section class="db-band">
  <div class="db-inner">
    <div class="section-heading"><span class="num">01</span><h2>Tier 1 — The monuments</h2></div>
    <table class="tier-table">
      <thead><tr><th>Race</th><th>Country</th><th class="r">Distance</th><th>Style</th><th class="r">Score</th><th></th></tr></thead>
      <tbody>
{t1_rows}
      </tbody>
    </table>
  </div>
</section>

<!-- ── Tier 2 Highlights ── -->
<div class="section" style="background: var(--gl-white); margin: 0; max-width: none; padding-left: calc((100% - var(--gl-measure))/2 + 24px); padding-right: calc((100% - var(--gl-measure))/2 + 24px);">
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
<div class="section" style="background: var(--gl-white); margin: 0; max-width: none; padding-left: calc((100% - var(--gl-measure))/2 + 24px); padding-right: calc((100% - var(--gl-measure))/2 + 24px);">
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

<!-- ── Ladder ── -->
<section class="gl-ladder" id="training">
  <div class="gl-ladder-inner">
    <h2>Get race ready</h2>
    <p class="gl-ladder-lead">Choose the amount of structure you want around the start line.</p>
    <div class="gl-rungs">
      <div class="gl-rung">
        <span class="gl-rung-kicker">Plans</span>
        <h3>Training plans</h3>
        <p>Structured plans for classic races, skate races, and long winter builds.</p>
        <span class="gl-rung-price">FROM $60</span><br>
        <a class="gl-rung-btn" href="/training-plans/">Browse</a>
      </div>
      <div class="gl-rung">
        <span class="gl-rung-kicker">Custom</span>
        <h3>Custom plan</h3>
        <p>Your race, your hours, your history. Built from the intake.</p>
        <span class="gl-rung-price">$60-$249</span><br>
        <a class="gl-rung-btn" href="/questionnaire/">Start the intake</a>
      </div>
      <div class="gl-rung">
        <span class="gl-rung-kicker">Course</span>
        <h3>XC ski course</h3>
        <p>Lessons from first glide to race preparation.</p>
        <span class="gl-rung-price">SELF-PACED</span><br>
        <a class="gl-rung-btn" href="/learn/">See the course</a>
      </div>
      <div class="gl-rung">
        <span class="gl-rung-kicker">Coaching</span>
        <h3>Coaching</h3>
        <p>Direct support when the season needs more than a template.</p>
        <span class="gl-rung-price">APPLICATION</span><br>
        <a class="gl-rung-btn apply" href="/coaching/apply/">Apply</a>
      </div>
    </div>
  </div>
</section>

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
    <div>We use cookies for analytics to improve the experience. <a href="/privacy/" style="color:var(--gl-klister)">Privacy policy</a>.</div>
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
