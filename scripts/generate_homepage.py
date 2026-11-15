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
import shutil
import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xsl_loops import BAND_CSS, LOOP_CSS, LOOP_JS, copy_media, loop_figure, loops_band  # noqa: E402
from tiers import TIER_NAMES  # noqa: E402
from newsletter_signup import newsletter_css, newsletter_form_html  # noqa: E402
from consent import get_consent_banner_html, get_ga4_head  # noqa: E402

XL_GA4_HEAD = get_ga4_head()

# Who runs the site, for search engines and assistants (sweep XC-07 / ALL-10).
# Only facts on the site itself: the seller named in /terms/ and the contact
# address published there. No sameAs: XC Ski Labs has no social accounts yet.
# No logo: Google needs a raster image, and the brand port will supply one.
ORGANIZATION_JSONLD = {
    "@type": "Organization",
    "@id": "https://xcskilabs.com/#organization",
    "name": "XC Ski Labs",
    "url": "https://xcskilabs.com/",
    "email": "gravelgodcoaching@gmail.com",
    "parentOrganization": {
        "@type": "Organization",
        "name": "Gravel God Cycling LLC",
        "url": "https://gravelgodcycling.com/",
    },
}
XL_CONSENT_BANNER = get_consent_banner_html()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "wordpress"))
import plan_offer  # noqa: E402  (wordpress/plan_offer.py: the custom plan's price)

try:
    from scripts.endure_offer import get_endure_offer_html
except ModuleNotFoundError:
    from endure_offer import get_endure_offer_html

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "race-data"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "output"

# The homepage never pitches the XC ski course (Matti, 2026-11-15).
TOKENS_CSS = SCRIPT_DIR.parent / "tokens" / "tokens.css"

# ── Constants ──────────────────────────────────────────────────

CRITERIA_COUNT = 14
TIER_COUNT = 4
TIER_THRESHOLDS = {1: 80, 2: 60, 3: 45}  # T4 is < 45

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


# ── Full Page ──────────────────────────────────────────────────

def generate_homepage(races: list[dict]) -> str:
    """Generate the complete homepage HTML."""
    # ── Compute stats ──
    race_count = len(races)
    countries = set(get_country(r) for r in races if get_country(r) != "Unknown")
    country_count = len(countries)

    # ── Tier buckets ──
    t1_races = [r for r in races if get_tier(r) == 1]

    t1_rows = "\n".join(build_tier_row(r) for r in t1_races)

    # ── JSON-LD ──
    jsonld_obj = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "@id": "https://xcskilabs.com/#website",
                "name": "XC Ski Labs",
                "url": "https://xcskilabs.com/",
                "description": (
                    f"{race_count} cross-country ski races across {country_count} countries, scored, "
                    f"with training plans built around your race and the technique to ski it fast."
                ),
                "publisher": {"@id": ORGANIZATION_JSONLD["@id"]},
                "potentialAction": {
                    "@type": "SearchAction",
                    "target": "https://xcskilabs.com/search/?q={search_term_string}",
                    "query-input": "required name=search_term_string",
                },
            },
            ORGANIZATION_JSONLD,
        ],
    }
    jsonld_block = (
        '<script type="application/ld+json">\n'
        + _safe_json_for_script(jsonld_obj, indent=2)
        + "\n</script>"
    )
    tokens_css = load_tokens_css()
    # Classic technique loops (Gravel God, motion-captured from the technique videos). Words match the guide's
    # "Classic gears" section, which the band links to.
    motion_band = loops_band(
        "Classic skiing has three gears.",
        "Diagonal stride for the climbs, kick double-pole for the rollers, double-pole for the flats.",
        ["diagonal", "kickdp", "doublepole"],
        "/guide/the-gears/", "Read the technique chapter", band_id="motion")
    loop_css = BAND_CSS + LOOP_CSS + newsletter_css()
    # Hero: Gravel God skating V2 straight at you, front-on (rig/print_skate.py). No caption under it.
    hero_loop = loop_figure("v2_front", "portrait", caption=False, extra_class="hero-loop")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>XC Ski Labs — Find Your Race, Train Right, Race Fast</title>
<meta name="description" content="{race_count} cross-country ski races across {country_count} countries, scored on {CRITERIA_COUNT} criteria. Find your race, get a plan built around it, and learn the technique to ski it fast.">
<meta name="keywords" content="cross-country ski races, XC skiing, marathon skiing, Worldloppet, Ski Classics, classic skiing, skate skiing">
<link rel="canonical" href="https://xcskilabs.com/">
<meta property="og:title" content="XC Ski Labs — Find Your Race, Train Right, Race Fast">
<meta property="og:description" content="{race_count} cross-country ski races scored on {CRITERIA_COUNT} criteria, plans built around your race, and the technique to ski it fast.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://xcskilabs.com/">
{XL_GA4_HEAD}
{jsonld_block}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Stencil+Display:wght@700;900&family=Big+Shoulders+Text:wght@600;800&family=Libre+Franklin:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
<style>
{tokens_css}
{loop_css}

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

/* ── Hero: the book's Hero (oat panel, inset stitch, kicker, stencil title) ── */
.hero {{
  background: var(--panel);
  color: var(--ink);
  position: relative;
  padding: clamp(56px, 8vw, 104px) clamp(28px, 4vw, 48px);
  border-bottom: var(--stroke-band) solid var(--ink);
}}

.hero::before {{
  content: "";
  position: absolute;
  inset: var(--space-3);
  border: var(--stroke-stitch) dashed var(--stitch-soft);
  pointer-events: none;
}}

.hero-inner {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 44px;
}}
.hero-copy {{ min-width: 0; }}
/* The skate loop: under the buttons on a phone, kept narrow so it never crowds the title */
.hero-loop {{ width: min(100%, 340px); justify-self: center; }}
@media (min-width: 900px) {{
  /* Title and buttons on the left, the loop on the right */
  .hero-inner {{ grid-template-columns: minmax(0, 1fr) clamp(260px, 30vw, 400px); align-items: center; gap: clamp(32px, 4vw, 64px); }}
  .hero-loop {{ width: 100%; }}
}}

.hero h1 {{
  font: var(--type-stencil-xl-weight) clamp(40px, 8.5vw, 132px)/var(--type-stencil-xl-line-height) var(--font-stencil);
  letter-spacing: var(--type-stencil-xl-tracking);
  text-transform: uppercase;
  margin: 0 0 28px;
  color: var(--ink);
}}
/* One line per promise: find, train, race. */
.hero h1 span {{ display: block; }}
/* Beside the loop the title gets about two thirds of the row */
@media (min-width: 900px) {{ .hero h1 {{ font-size: clamp(40px, 6.4vw, 104px); }} }}

.hero-sub {{
  display: inline-block;
  margin: 0 0 20px;
  padding: 6px 12px 6px 16px;
  background: var(--ink);
  color: var(--ground);
  font: var(--type-kicker-weight) var(--type-kicker-size)/var(--type-kicker-line-height) var(--font-label);
  letter-spacing: var(--type-kicker-tracking);
  text-transform: uppercase;
}}

.hero-desc {{
  font: var(--type-lede-weight) clamp(18px, 1.7vw, 21px)/var(--type-lede-line-height) var(--font-body);
  color: var(--ink);
  max-width: 38ch;
  margin: 0 0 32px;
}}


/* Buttons: the book's Button. Primary is the action slab with the salmon
   underline; the others are quiet outlines in ink. */
.hero-cta, .hero-getready-cta {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 56px;
  padding: 10px 22px;
  margin: 0 10px 10px 0;
  font: var(--type-button-weight) var(--type-button-size)/var(--type-button-line-height) var(--font-label);
  letter-spacing: var(--type-button-tracking);
  text-transform: uppercase;
  text-decoration: none;
  background: var(--action);
  color: var(--on-action);
  border: var(--stroke-button) solid var(--action);
  box-shadow: inset 0 calc(-1 * var(--stroke-underline)) 0 var(--splash) !important;
  transition: background-color 150ms ease-out, color 150ms ease-out;
}}

.hero-cta.secondary, .hero-getready-cta {{
  background: transparent;
  color: var(--ink);
  border-color: var(--ink);
  box-shadow: none !important;
}}

.hero-cta:hover, .hero-getready-cta:hover {{
  background: var(--ground);
  color: var(--ink);
  border-color: var(--ink);
  text-decoration: none;
}}

/* Season review entry: set a goal, learn from last winter, beat yourself. */
.gl-hp-goals {{ background: var(--gl-paper); border-bottom: 3px solid var(--gl-ink); }}
.gl-hp-goals-inner {{ max-width: var(--gl-measure); margin: 0 auto; padding: 36px 24px; }}
.gl-hp-goals-kicker {{ font: 700 11px var(--gl-font-data); letter-spacing: .12em; text-transform: uppercase; color: var(--gl-rust); margin: 0 0 12px; }}
.gl-hp-goals h2 {{ font-family: var(--gl-font-display); font-weight: 900; font-size: clamp(1.8rem, 4vw, 2.8rem); line-height: 1; text-transform: uppercase; margin: 0 0 10px; color: var(--gl-ink); }}
.gl-hp-goals-copy > p:not(.gl-hp-goals-kicker) {{ font-family: var(--gl-font-editorial); font-size: 1.05rem; line-height: 1.55; max-width: 52ch; margin: 0 0 20px; color: var(--gl-ink); }}
.gl-hp-goals-cta {{ min-height: 44px; display: inline-flex; align-items: center; padding: 9px 16px; background: var(--gl-rust); color: var(--gl-snow); font: 700 12px var(--gl-font-data); letter-spacing: .08em; text-transform: uppercase; border: 2px solid var(--gl-rust); text-decoration: none; }}
.gl-hp-goals-cta:hover, .gl-hp-goals-cta:focus-visible {{ background: var(--gl-ink); border-color: var(--gl-ink); color: var(--gl-snow); text-decoration: none; }}
.mono {{ font-family: var(--gl-font-data); }}
.r {{ text-align: right; }}

/* ── Ladder Strip (homepage) ──
   3-cell band: pick a race / get a plan / coaching. Tokens only, no hex. */
.gl-hp-ladder {{
  border-top: 1px solid var(--gl-carbon);
  border-bottom: 1px solid var(--gl-carbon);
  background: var(--gl-paper);
}}

.gl-hp-ladder-inner {{
  max-width: var(--gl-measure);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
}}

.gl-hp-ladder-cell {{
  padding: var(--gl-space-6) var(--gl-space-5);
  border-left: 1px solid var(--gl-hairline);
}}

.gl-hp-ladder-cell:first-child {{
  border-left: none;
}}

.gl-hp-ladder-num {{
  display: block;
  margin-bottom: var(--gl-space-3);
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: var(--gl-muted);
}}

.gl-hp-ladder-headline {{
  margin: 0 0 var(--gl-space-2);
  font-family: var(--gl-font-editorial);
  font-size: 1.3rem;
  font-weight: 600;
  line-height: 1.25;
  color: var(--gl-carbon);
}}

.gl-hp-ladder-body {{
  margin: 0 0 var(--gl-space-4);
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.5;
  color: var(--gl-muted);
}}
.gl-hp-ladder-body a {{ color: inherit; text-decoration: underline; text-underline-offset: 3px; }}

.gl-hp-ladder-cta {{
  display: inline-block;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--gl-swix-red);
  text-decoration: none;
}}

.gl-hp-ladder-cta:hover {{
  text-decoration: underline;
}}

@media (max-width: 719px) {{
  .gl-hp-ladder-inner {{
    grid-template-columns: 1fr;
  }}
  .gl-hp-ladder-cell {{
    border-left: none;
    border-top: 1px solid var(--gl-hairline);
    padding: var(--gl-space-5);
  }}
  .gl-hp-ladder-cell:first-child {{
    border-top: none;
  }}
}}

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

.section-link {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--gl-swix-red);
}}

/* ── Race Cards ── */


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

/* ── About ── */

/* ── Footer ── */
footer {{
  background: var(--gl-swix-red);
  color: var(--gl-white);
  padding: 0 24px;
  border-top: 0;
}}

.footer-inner {{
  max-width: var(--gl-measure);
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
  color: var(--gl-caption-on-dark);
}}

.footer-link {{
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-klister);
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
  max-width: var(--gl-measure);
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
  color: var(--gl-caption-on-dark);
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
  color: var(--gl-caption-on-dark);
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

/* ── Responsive ── */
@media (max-width: 640px) {{
  .hero {{ padding: 56px 28px 48px; }}
  .tier-table th:nth-child(2),
  .tier-table td:nth-child(2),
  .tier-table th:nth-child(3),
  .tier-table td:nth-child(3),
  .tier-table th:nth-child(4),
  .tier-table td:nth-child(4) {{ display: none; }}
  .tier-table {{ display: block; max-width: 100%; overflow-x: auto; }}
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

/* ── Page rhythm (Matti, 2026-11-15: no strange transitions) ──
   Every section after the hero sits on the same wool ground, with the same
   inner width and padding, separated by exactly one 3px ink rule. Section
   titles share one style. The hero keeps its 6px band edge. */
.gl-hp-ladder, .db-band, .xsl-motion, .gl-hp-goals {{
  background: var(--gl-paper); border: 0;
}}
.hero + section {{ border-top: 0; }}
.gl-hp-ladder + section, .db-band + section, .xsl-motion + section {{ border-top: var(--stroke-button) solid var(--xc-light-ink); }}
.db-inner, .xsl-motion-inner, .gl-hp-goals-inner {{ max-width: var(--gl-measure); margin: 0 auto; padding: 64px 24px; }}
.xsl-motion-inner {{ gap: 18px; }}
.db-band .section-heading {{ align-items: baseline; justify-content: space-between; margin: 0 0 24px; }}
.db-band .section-heading h2, .xsl-motion-title, .gl-hp-goals h2 {{
  font-family: var(--font-label); font-weight: 800; font-style: normal; font-stretch: normal;
  font-size: clamp(30px, 4.4vw, 46px); line-height: 1; letter-spacing: .01em;
  text-transform: uppercase; color: var(--xc-light-ink); margin: 0;
}}
.gl-hp-goals h2 {{ margin: 0 0 12px; }}
.gl-hp-goals-kicker {{ color: var(--xc-light-ink-2); }}
/* Footer: the book's lockup type, no italics, one strap. */
.footer-brand {{ font-family: var(--font-label); font-weight: 800; font-style: normal; letter-spacing: .2em; }}
.footer-tagline {{ font-style: normal; }}
@media (max-width: 640px) {{
  .db-inner, .xsl-motion-inner, .gl-hp-goals-inner {{ padding: 48px 20px; }} .gl-hp-ladder-cell {{ padding-left: 20px; padding-right: 20px; }}
}}
</style>
</head>
<body>

<!-- ── Nav Header ── -->
<header class="gl-nav-header">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo" aria-label="XC Ski Labs, powered by Endure Labs"><img class="gl-brand-mark" src="/xc-logo.svg" alt="" width="30" height="30"><span class="gl-brand-name">XC SKI <em>LABS</em></span></a>
    <button class="gl-nav-hamburger" data-nav-toggle aria-expanded="false" aria-label="Menu">&#9776;</button>
    <ul class="gl-nav-links">
      <li class="gl-nav-item">
        <a href="/search/">Races</a>
        <div class="gl-nav-dropdown"><a href="/search/">All XC Ski Races</a></div>
      </li>
      <li class="gl-nav-item">
        <a href="/guide/">Guide</a>
              </li>
      <li class="gl-nav-item">
        <a href="/training-plans/">Plans</a>
              </li>
      <li class="gl-nav-item">
        <a href="/coaching/">Coaching</a>
              </li>
      <li class="gl-nav-item">
        <a href="/consulting/">Consulting</a>
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
    <div class="hero-copy">
      <p class="hero-sub">XC ski races, training and technique</p>
      <h1><span>Find your race.</span> <span>Train right.</span> <span>Race fast.</span></h1>
      <p class="hero-desc">{race_count} races scored on {CRITERIA_COUNT} criteria, a plan built around the one you pick, and the technique to ski it fast.</p>
      <a href="/search/" class="hero-cta">Search the races</a>
      <a href="#ladder" class="hero-getready-cta" data-ga="hero_get_race_ready">GET RACE-READY &darr;</a>
    </div>
    {hero_loop}
  </div>
</section>

<!-- ── Find / train / race: the three things the site does ── -->
<section class="gl-hp-ladder" id="ladder">
  <div class="gl-hp-ladder-inner">
    <div class="gl-hp-ladder-cell">
      <span class="gl-hp-ladder-num">01</span>
      <h2 class="gl-hp-ladder-headline">Find your race</h2>
      <p class="gl-hp-ladder-body"><span id="statRaces">{race_count}</span> races in <span id="statCountries">{country_count}</span> countries, scored on {CRITERIA_COUNT} criteria. <a href="/methodology/">How we rate</a></p>
      <a href="/search/" class="gl-hp-ladder-cta" data-ga="ladder_pick_race">SEARCH THE RACES &rarr;</a>
    </div>
    <div class="gl-hp-ladder-cell">
      <span class="gl-hp-ladder-num">02</span>
      <h2 class="gl-hp-ladder-headline">Train right</h2>
      <p class="gl-hp-ladder-body">A plan built around your race and the hours you actually have, {esc(plan_offer.BLOCK_PRICE)} every {plan_offer.BLOCK_WEEKS} weeks. Want me reading every session? <a href="/coaching/" data-ga="ladder_coaching">Coaching</a></p>
      <a href="/training-plans/" class="gl-hp-ladder-cta" data-ga="ladder_get_plan">GET A TRAINING PLAN &rarr;</a>
    </div>
    <div class="gl-hp-ladder-cell">
      <span class="gl-hp-ladder-num">03</span>
      <h2 class="gl-hp-ladder-headline">Race fast</h2>
      <p class="gl-hp-ladder-body">Technique, pacing, wax and fueling for the day that counts.</p>
      <a href="/guide/" class="gl-hp-ladder-cta" data-ga="ladder_guide">READ THE GUIDE &rarr;</a>
    </div>
  </div>
</section>

<!-- ── The top tier, then the rest live in search ── -->
<section class="db-band">
  <div class="db-inner">
    <div class="section-heading"><h2>Tier 1 — {TIER_NAMES[1]}</h2><a href="/search/" class="section-link">All {race_count} races &rarr;</a></div>
    <table class="tier-table">
      <thead><tr><th>Race</th><th>Country</th><th class="r">Distance</th><th>Style</th><th class="r">Score</th><th></th></tr></thead>
      <tbody>
{t1_rows}
      </tbody>
    </table>
  </div>
</section>

<!-- ── Classic technique, in motion ── -->
{motion_band}

<!-- ── Season review: set a goal, learn from last winter, beat yourself ── -->
<section class="gl-hp-goals" aria-labelledby="gl-hp-goals-title">
  <div class="gl-hp-goals-inner">
    <div class="gl-hp-goals-copy">
      <p class="gl-hp-goals-kicker">2026–27 GOALS</p>
      <h2 id="gl-hp-goals-title">Beat last winter&rsquo;s you.</h2>
      <p>Fifteen minutes. Look back at last season honestly, set one goal for this one, and name the habit most likely to wreck it.</p>
      <a href="/goals/?src=home" class="gl-hp-goals-cta" data-ga="goal_hero_click">Set my goal &rarr;</a>
    </div>
  </div>
</section>

<!-- ── The weekly round-up sign-up ── -->
<section class="gl-hp-goals gl-hp-weekly" aria-labelledby="gl-hp-weekly-title">
  <div class="gl-hp-goals-inner">
    <div class="gl-hp-goals-copy">
      <p class="gl-hp-goals-kicker">THE WEEKLY</p>
      <h2 id="gl-hp-weekly-title">The week in cross-country, once a week.</h2>
      <p>The news from Langrenn.com, NRK, FasterSkier and the Swedish and German ski press, the podcast episodes worth hearing, and a paragraph or two of my take. Every item links to the original. <a href="/weekly/" class="xc-link">What&rsquo;s in it &rarr;</a></p>
      {newsletter_form_html("homepage")}
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
      <a href="/coaching/" class="footer-link">Coaching</a>
      <a href="/weekly/" class="footer-link">Weekly</a>
      <a href="/privacy/" class="footer-link">Privacy</a>
      <a href="/terms/" class="footer-link">Terms</a>
    </div>
  </div>
{get_endure_offer_html()}
</footer>

{XL_CONSENT_BANNER}
<script>
(function(){{
var navToggle=document.querySelector('[data-nav-toggle]');var navLinks=document.querySelector('.gl-nav-links');
if(navToggle&&navLinks){{navToggle.addEventListener('click',function(){{var open=navLinks.classList.toggle('open');navToggle.setAttribute('aria-expanded',open?'true':'false')}})}}
document.querySelectorAll('[data-ga="goal_hero_click"]').forEach(function(link){{link.addEventListener('click',function(){{if(typeof gtag==='function')gtag('event','goal_hero_click',{{src:'home'}})}})}});
}})();
</script>

{LOOP_JS}
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
    shutil.copy2(SCRIPT_DIR.parent / "web" / "xc-logo.svg", output_dir / "xc-logo.svg")
    print(f"  Copied {copy_media(output_dir)} technique-loop files to {output_dir / 'media' / 'loops'}")
    print(f"  Wrote {out_path} ({len(html_content):,} bytes)")


if __name__ == "__main__":
    main()
