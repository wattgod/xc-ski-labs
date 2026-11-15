#!/usr/bin/env python3
"""XC Ski Labs — Training Plans Landing Page Generator

Generates a self-contained landing page for custom XC ski training plans.
Neo-brutalist design system matching the race page generator palette.

Usage:
    python generate_training_plans.py
"""

import json
import html
import os
import re
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
DATA_DIR = PROJECT_ROOT / "data"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_race_pages import build_nav_header as build_canonical_nav_header
from scripts.endure_offer import get_endure_offer_html
from scripts.xsl_loops import LOOP_CSS, LOOP_JS, loop_figure  # noqa: E402

# Gravel God skiing, motion-captured from Matti's course videos (scripts/xsl_loops.py); caption only, no new copy
PAGE_MOTION = f'<section class="xsl-page-motion">{loop_figure("doublepole", "wide")}</section>'
XSL_PAGE_MOTION_CSS = """
.xsl-page-motion { max-width: var(--gl-measure); margin: 0 auto; padding: 40px 20px 8px; }
"""
from plan_simulator import (get_plan_simulator_css, get_plan_simulator_js,
                            render_plan_simulator)
import plan_offer  # noqa: E402  (wordpress/plan_offer.py: price and terms)

# ── Helpers ────────────────────────────────────────────────────

def esc(text):
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


def _safe_json_for_script(obj, **kwargs):
    """Serialize obj to JSON safe for embedding inside <script> tags.

    json.dumps does NOT escape '</' sequences, so a string containing
    '</script>' would prematurely close the <script> element.
    We replace '</' with '<\\/' which is valid JSON and safe in HTML.
    """
    raw = json.dumps(obj, **kwargs)
    return raw.replace("</", "<\\/")


def count_race_profiles():
    """Count race JSON files in race-data/."""
    data_dir = PROJECT_ROOT / "race-data"
    if not data_dir.exists():
        return 229
    files = [f for f in data_dir.glob("*.json") if f.name != "_schema.json"]
    return len(files)


def load_simulator_races():
    """Project every indexed race's rated demands for the preview selector."""
    criteria = (
        "distance", "elevation", "altitude", "field_size", "prestige",
        "international_draw", "course_technicality", "snow_reliability",
        "grooming_quality", "accessibility", "community", "scenery",
        "organization", "competitive_depth",
    )
    races = []
    for path in sorted((PROJECT_ROOT / "race-data").glob("*.json")):
        if path.name == "_schema.json":
            continue
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        race = document.get("race", document)
        rating = race.get("nordic_lab_rating") or {}
        demands = {}
        for key in criteria:
            value = rating.get(key)
            if isinstance(value, (int, float)):
                demands[key] = max(0, min(10, int(round(value * 2))))
        if not demands:
            continue
        races.append({
            "slug": race.get("slug"),
            "name": race.get("display_name") or race.get("name"),
            "vitals": {"discipline": (race.get("vitals") or {}).get("discipline")},
            "demands": demands,
            "score": rating.get("overall_score") or 0,
        })
    races.sort(key=lambda race: (
        race["slug"] != "birkebeinerrennet", -race["score"], race["name"]))
    return races


def load_tokens_css():
    """Read shared Wax Bench tokens for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


# ── CSS ────────────────────────────────────────────────────────

OFFER_CSS = """
.gl-offer-lines {
  max-width: 640px;
  margin: 0 auto 20px;
  text-align: left;
  padding-left: 1.2em;
  font-family: var(--gl-font-editorial);
  font-size: 1rem;
  line-height: 1.55;
}
.gl-offer-lines li { margin-bottom: 6px; }
"""


def build_css():
    """Build the complete CSS for the training plans landing page."""
    return load_tokens_css() + """

*, *::before, *::after {
  box-sizing: border-box;
  border-radius: 0 !important;
  box-shadow: none !important;
}

body {
  margin: 0;
  padding: 0;
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-editorial);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--gl-swix-red); }
a:hover { color: var(--gl-klister); }

a:focus-visible, button:focus-visible {
  outline: 3px solid var(--gl-swix-red);
  outline-offset: 2px;
}

.gl-page {
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: 0 20px;
}

/* ── Nav ─────────────────────────────────────────── */

.gl-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-swix-red);
  padding: 0 20px;
}
.gl-nav-inner {
  max-width: var(--gl-measure);
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 52px;
}
.gl-nav-logo {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-logo:hover { color: var(--gl-hairline); }
.gl-nav-links {
  display: flex;
  gap: 0;
  align-items: center;
  list-style: none;
  margin: 0;
  padding: 0;
}
.gl-nav-item { position: relative; }
.gl-nav-item > a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 16px 14px;
  display: block;
}
.gl-nav-item > a:hover { color: var(--gl-white); }
.gl-nav-item > a.active { color: var(--gl-white); }
.gl-nav-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  background: var(--gl-carbon);
  border: 2px solid var(--gl-swix-red);
  min-width: 200px;
  z-index: 1001;
  padding: 8px 0;
}
.gl-nav-item:hover .gl-nav-dropdown { display: block; }
.gl-nav-dropdown a {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 16px;
  display: block;
}
.gl-nav-dropdown a:hover { color: var(--gl-white); background: var(--gl-swix-red); }
.gl-nav-hamburger {
  display: none;
  background: none;
  border: none;
  color: var(--gl-white);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 8px;
  min-width: 44px;
  min-height: 44px;
}

/* ── Hero ────────────────────────────────────────── */

.gl-hero {
  background: var(--gl-carbon);
  color: var(--gl-paper);
  padding: 64px 32px 56px;
  text-align: center;
}

.gl-hero-label {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--gl-swix-red);
  margin-bottom: 16px;
}

.gl-hero h1 {
  font-family: var(--gl-font-editorial);
  font-size: 2.6rem;
  font-weight: 700;
  line-height: 1.1;
  margin: 0 0 20px;
}

/* ── Interactive plan preview ────────────────────── */

.gl-hero-sub {
  font-family: var(--gl-font-editorial);
  font-size: 1.1rem;
  color: var(--gl-muted);
  max-width: 600px;
  margin: 0 auto 28px;
  line-height: 1.6;
}

.gl-hero-stats {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-white);
  letter-spacing: 0.04em;
  margin-bottom: 32px;
}

.gl-hero-stats span {
  color: var(--gl-swix-red);
  font-weight: 700;
}

.gl-cta-btn {
  display: inline-block;
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 14px 36px;
  background: var(--gl-swix-red);
  color: var(--gl-white);
  text-decoration: none;
  border: 3px solid var(--gl-white);
  transition: background 0.15s;
}

.gl-cta-btn:hover {
  background: var(--gl-red-deep);
  color: var(--gl-white);
}

.gl-cta-btn--outline {
  background: transparent;
  border-color: var(--gl-white);
}

.gl-cta-btn--outline:hover {
  background: var(--gl-white);
  color: var(--gl-carbon);
}

/* ── Section Base ────────────────────────────────── */

.gl-section {
  padding: 48px 0;
  border-bottom: 1px solid var(--gl-hairline);
}

.gl-section:last-child { border-bottom: none; }

.gl-section-label {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--gl-muted);
  margin-bottom: 6px;
}

.gl-section-title {
  font-family: var(--gl-font-editorial);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0 0 24px;
  line-height: 1.25;
}

.gl-section-prose {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  color: var(--gl-carbon);
  line-height: 1.7;
  margin-bottom: 16px;
}

/* ── How It Works ────────────────────────────────── */

.gl-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  border: 2px solid var(--gl-carbon);
}

.gl-step {
  padding: 28px 24px;
  border-right: 2px solid var(--gl-carbon);
}

.gl-step:last-child { border-right: none; }

.gl-step-num {
  font-family: var(--gl-font-data);
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--gl-swix-red);
  line-height: 1;
  margin-bottom: 12px;
}

.gl-step-title {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--gl-carbon);
  margin-bottom: 8px;
}

.gl-step-desc {
  font-family: var(--gl-font-editorial);
  font-size: 0.88rem;
  color: var(--gl-muted);
  line-height: 1.55;
}

/* ── Deliverables ────────────────────────────────── */

.gl-deliverables {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  border: 2px solid var(--gl-carbon);
}

.gl-deliverable {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 2px solid var(--gl-carbon);
}

.gl-deliverable:last-child { border-bottom: none; }

.gl-deliverable-icon {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-white);
  background: var(--gl-carbon);
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid var(--gl-carbon);
  flex-shrink: 0;
}

.gl-deliverable-title {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--gl-carbon);
  margin-bottom: 4px;
}

.gl-deliverable-desc {
  font-family: var(--gl-font-editorial);
  font-size: 0.88rem;
  color: var(--gl-muted);
  line-height: 1.5;
}

/* ── Sample Week ─────────────────────────────────── */

.gl-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0;
  border: 2px solid var(--gl-carbon);
}

.gl-day {
  padding: 16px 10px;
  border-right: 2px solid var(--gl-carbon);
  text-align: center;
  min-height: 120px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gl-day:last-child { border-right: none; }

.gl-day-label {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-muted);
}

.gl-day-type {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.gl-day-desc {
  font-family: var(--gl-font-editorial);
  font-size: 0.75rem;
  color: var(--gl-muted);
  line-height: 1.4;
}

.gl-day--rest { background: var(--gl-white); }
.gl-day--rest .gl-day-type { color: var(--gl-muted); }
.gl-day--intensity .gl-day-type { color: var(--gl-swix-red); }
.gl-day--endurance .gl-day-type { color: var(--gl-swix-red); }
.gl-day--strength .gl-day-type { color: var(--gl-klister); }
.gl-day--threshold .gl-day-type { color: var(--gl-swix-red); }

/* ── Pricing ─────────────────────────────────────── */

.gl-pricing-box {
  border: 3px solid var(--gl-carbon);
  padding: 40px 32px;
  text-align: center;
  background: var(--gl-white);
}

.gl-pricing-headline {
  font-family: var(--gl-font-editorial);
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0 0 8px;
}

.gl-pricing-sub {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  color: var(--gl-muted);
  letter-spacing: 0.04em;
  margin-bottom: 24px;
}

.gl-pricing-example {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-carbon);
  margin-bottom: 8px;
}

.gl-pricing-example strong {
  color: var(--gl-swix-red);
}

.gl-pricing-note {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  font-style: italic;
  color: var(--gl-muted);
  margin: 20px 0 28px;
}

.gl-pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  border: 2px solid var(--gl-carbon);
  margin: 24px 0;
  text-align: center;
}
.gl-pricing-grid.has-checkout {
  grid-template-columns: repeat(4, 1fr);
}

.gl-pricing-cell {
  padding: 12px 8px;
  border-right: 2px solid var(--gl-carbon);
  border-bottom: 2px solid var(--gl-carbon);
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
}

.gl-pricing-cell:nth-child(3n) { border-right: none; }
.gl-pricing-cell:nth-last-child(-n+3) { border-bottom: none; }
.gl-pricing-grid.has-checkout .gl-pricing-cell:nth-child(3n) { border-right: 2px solid var(--gl-carbon); }
.gl-pricing-grid.has-checkout .gl-pricing-cell:nth-child(4n) { border-right: none; }
.gl-pricing-grid.has-checkout .gl-pricing-cell:nth-last-child(-n+4) { border-bottom: none; }

.gl-pricing-cell--header {
  background: var(--gl-carbon);
  color: var(--gl-white);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.68rem;
}

.gl-pricing-checkout {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  justify-content: center;
  background: var(--gl-carbon);
  color: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  padding: 8px 12px;
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  text-decoration: none;
}
.gl-pricing-checkout:hover {
  background: var(--gl-swix-red);
  color: var(--gl-white);
}

/* ── FAQ ─────────────────────────────────────────── */

.gl-faq-item {
  border-bottom: 1px solid var(--gl-hairline);
}

.gl-faq-item:last-child { border-bottom: none; }

.gl-faq-q {
  width: 100%;
  background: none;
  border: none;
  padding: 18px 0;
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  text-align: left;
  color: var(--gl-carbon);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.gl-faq-q:hover { color: var(--gl-swix-red); }

.gl-faq-q::after {
  content: '+';
  font-family: var(--gl-font-data);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--gl-swix-red);
  flex-shrink: 0;
  transition: transform 0.2s;
}

.gl-faq-q[aria-expanded="true"]::after {
  content: '\\2212';
}

.gl-faq-a {
  display: none;
  padding: 0 0 18px;
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-muted);
  line-height: 1.65;
}

.gl-faq-a.open { display: block; }

/* ── Final CTA ───────────────────────────────────── */

.gl-final-cta {
  background: var(--gl-carbon);
  color: var(--gl-paper);
  padding: 56px 32px;
  text-align: center;
  border-top: 3px solid var(--gl-swix-red);
}

.gl-final-cta h2 {
  font-family: var(--gl-font-editorial);
  font-size: 2rem;
  font-weight: 700;
  margin: 0 0 12px;
}

.gl-final-cta p {
  font-family: var(--gl-font-editorial);
  font-size: 1rem;
  color: var(--gl-muted);
  margin: 0 0 28px;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

/* ── Footer ──────────────────────────────────────── */

.gl-footer {
  background: var(--gl-carbon);
  color: var(--gl-muted);
  padding: 28px 32px;
  text-align: center;
  border-top: 1px solid var(--gl-carbon);
}

.gl-footer a {
  color: var(--gl-muted);
  text-decoration: none;
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
}

.gl-footer a:hover { color: var(--gl-white); }

.gl-footer-brand {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 12px;
  color: var(--gl-muted);
}

/* ── Responsive ──────────────────────────────────── */

@media (max-width: 640px) {
  .gl-hero h1 { font-size: 1.8rem; }
  .gl-hero { padding: 40px 20px 36px; }
  .gl-steps { grid-template-columns: 1fr; }
  .gl-step { border-right: none; border-bottom: 2px solid var(--gl-carbon); }
  .gl-step:last-child { border-bottom: none; }
  .gl-week { grid-template-columns: repeat(2, 1fr); }
  .gl-day:nth-child(2n) { border-right: none; }
  .gl-day { border-bottom: 2px solid var(--gl-carbon); }
  .gl-day:last-child { border-bottom: none; }
  .gl-pricing-grid { grid-template-columns: repeat(2, 1fr); }
  .gl-pricing-cell:nth-child(3n) { border-right: 2px solid var(--gl-carbon); }
  .gl-pricing-cell:nth-child(2n) { border-right: none; }
  .gl-nav-hamburger { display: block; }
  .gl-nav-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    background: var(--gl-carbon);
    flex-direction: column;
    padding: 16px 20px;
    gap: 0;
    border-bottom: 3px solid var(--gl-swix-red);
  }
  .gl-nav-links.open { display: flex; }
  .gl-nav-dropdown { position: static; border: none; padding: 0 0 0 16px; display: block; }
  .gl-nav-item > a { padding: 12px 0; }
  .gl-final-cta { padding: 40px 20px; }
  .gl-final-cta h2 { font-size: 1.5rem; }
  .gl-pricing-headline { font-size: 1.4rem; }
}

@media (max-width: 400px) {
  .gl-hero h1 { font-size: 1.5rem; }
  .gl-hero-sub { font-size: 0.95rem; }
  .gl-section-title { font-size: 1.25rem; }
  .gl-cta-btn { padding: 12px 24px; font-size: 0.78rem; }
  .gl-week { grid-template-columns: 1fr; }
  .gl-day { border-right: none; }
  .gl-pricing-grid { grid-template-columns: 1fr; font-size: 0.68rem; }
  .gl-pricing-cell:nth-child(2n) { border-right: 2px solid var(--gl-carbon); }
  .gl-pricing-cell { border-right: none; }
  .gl-pricing-cell { padding: 8px 4px; }
}

/* ── Cookie Consent ─────────────────────────────── */

.xl-consent-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-carbon);
  color: var(--gl-white);
  border-top: 3px solid var(--gl-swix-red);
  padding: 16px 20px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  display: none;
}

.xl-consent-banner.show { display: block; }

.xl-consent-inner {
  max-width: var(--gl-measure);
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.xl-consent-text {
  flex: 1;
  min-width: 200px;
  line-height: 1.5;
}

.xl-consent-text a {
  color: var(--gl-klister);
  text-decoration: underline;
}

.xl-consent-btns {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.xl-consent-btn {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 8px 16px;
  border: 2px solid var(--gl-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.xl-consent-accept {
  background: var(--gl-swix-red);
  color: var(--gl-white);
}

.xl-consent-accept:hover { background: var(--gl-klister); }

.xl-consent-decline {
  background: transparent;
  color: var(--gl-muted);
  border-color: var(--gl-muted);
}

.xl-consent-decline:hover { color: var(--gl-white); border-color: var(--gl-white); }
""" + get_plan_simulator_css(
        ink="var(--gl-carbon)",
        paper="var(--gl-paper)",
        panel="var(--gl-white)",
        line="var(--gl-hairline)",
        accent="var(--gl-swix-red)",
        data_font="var(--gl-font-data)",
        body_font="var(--gl-font-editorial)",
    )


# ── Section Builders ───────────────────────────────────────────

def build_nav():
    """Top navigation bar."""
    return build_canonical_nav_header(active="plans") + """
<script>
(function(){
  var toggle=document.querySelector('[data-nav-toggle]');
  var links=document.querySelector('.gl-nav-links');
  if(toggle&&links){toggle.addEventListener('click',function(){var open=links.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false')});}
})();
</script>
"""


def build_hero(race_count):
    """Hero section with value prop and CTA."""
    return f"""
<section class="gl-hero">
  <div class="gl-hero-label">Custom XC Ski Training</div>
  <h1>Your Race. Your Hours.<br>Your Plan.</h1>
  <p class="gl-hero-sub">
    {esc(HERO_SUB)}
  </p>
  <div class="gl-hero-stats">
    <span>{esc(str(race_count))}</span> races indexed &middot;
    <span>14</span> scoring criteria &middot;
    <span>{esc(plan_offer.BLOCK_PRICE)}</span> every {plan_offer.BLOCK_WEEKS} weeks
  </div>
  <a href="/questionnaire/" class="gl-cta-btn">Build My Plan</a>
</section>
"""


def build_plan_preview():
    """Contract-backed calendar preview with every indexed race available."""
    races = load_simulator_races()
    if not races:
        return ""
    race = races[0]
    return render_plan_simulator(
        brand="xc_ski_labs",
        race=race,
        demands=race["demands"],
        race_options=races,
        questionnaire_url="/questionnaire/",
        heading=f"See a {race['name']} week before you buy.",
        lede=("Choose your race and the week you have. See how those "
              "constraints and the race's demands shape a calendar preview."),
    )


# Rider-facing copy on this page (Matti speaking). Every line is in the PR's
# approval list; each claim is something the ski engine builds
# (athletes/scripts/ski_engine.py, ALGORITHM_EVIDENCE §20) or the plan's
# emails send (race_plan_emails).
HERO_SUB = ("A plan built around your race, the hours you have and when you're on snow, "
            "one 4-week block at a time. Classic, skate or skiathlon.")

STEPS = (
    ("01", "Answer the questionnaire",
     "Your race, the hours you can keep up, the longest session each day allows, when "
     "you're on snow, and what you have to train on before then."),
    ("02", "I check every block",
     "Your plan comes one 4-week block at a time. I look over each block before it goes "
     "on your TrainingPeaks calendar, and a few days before each payment I email to ask "
     "what's changed."),
    ("03", "Train it",
     "Each block also comes by email with a guide that lists every workout in it."),
)

PLAN_PARTS = (
    ("S", "Built around your snow",
     "Before your snow date, sessions use the rollerskis, running, SkiErg or bike you told "
     "me you have. Once you're on snow, they move to snow."),
    ("W", "Your week, your days",
     "Every session fits the longest time you gave me for its day. Your long session lands "
     "on the day you picked, and days you can't train stay rest days."),
    ("L", "Load and taper",
     "Three weeks of building, then a lighter week, and a two-week taper into your race."),
    ("G", "Strength every week",
     "Strength work for where you can lift, whether that's a gym, dumbbells at home or "
     "only your own bodyweight."),
    ("H", "Effort and heart rate",
     "Hard sessions are written by effort. If you've seen your max heart rate on skis with a "
     "chest strap in the last 3 years, sessions in that technique also get heart-rate ranges."),
    ("F", "Fueling",
     "Long sessions carry a carbohydrate target that starts from what you've practised. A "
     "race of 42 km or more gets a two-day carb-load before it."),
    ("T", "Heat training",
     "If you have a sauna or a bath, and the health questions don't rule it out, I add up to "
     "three short heat sessions a week after training, from August until your taper."),
)

FAQS = (
    ("How do I get the workouts?",
     "Each block goes on your TrainingPeaks calendar after I've looked it over. The email "
     "you get after paying tells you how to connect your account. Every block also comes "
     "by email with a guide that lists its workouts."),
    ("Which races can I get a plan for?",
     f"{plan_offer.FIT_LINES[0]} Pick your race from the list in the questionnaire, or "
     "enter its date, distance and technique yourself."),
    ("I race classic and skate. Can the plan cover both?",
     "The plan follows your target race's technique. For a skiathlon, classic and skate "
     "sessions alternate, with the hard sessions split evenly between them. Other races you "
     "list in the questionnaire go into the plan with their own date, distance and technique."),
    ("What if I don't have rollerskis?",
     "You can still get a plan. Before snow, the hard sessions go on running or a SkiErg "
     "instead. If you have neither rollerskis nor running, I can't set your training zones "
     "with a test, so I can't build the plan yet."),
    ("What if I only have 5 hours a week?",
     "Every week is built to the hours you say you can keep up for months, and every "
     "session fits the longest time you gave me for its day."),
    ("Can I cancel?",
     f"{plan_offer.CANCEL_LINE} {plan_offer.REFUND_LINE}"),
)


def build_how_it_works():
    """3-step process section."""
    steps = "".join(f"""
    <div class="gl-step">
      <div class="gl-step-num">{num}</div>
      <div class="gl-step-title">{esc(title)}</div>
      <div class="gl-step-desc">{esc(desc)}</div>
    </div>""" for num, title, desc in STEPS)
    return f"""
<div class="gl-page">
<section class="gl-section">
  <div class="gl-section-label">Process</div>
  <div class="gl-section-title">How It Works</div>
  <div class="gl-steps">{steps}
  </div>
</section>
"""


def build_deliverables():
    """What the ski engine puts in the plan."""
    parts = "".join(f"""
    <div class="gl-deliverable">
      <div class="gl-deliverable-icon">{esc(icon)}</div>
      <div>
        <div class="gl-deliverable-title">{esc(title)}</div>
        <div class="gl-deliverable-desc">{esc(desc)}</div>
      </div>
    </div>""" for icon, title, desc in PLAN_PARTS)
    return f"""
<section class="gl-section">
  <div class="gl-section-label">Deliverables</div>
  <div class="gl-section-title">What&rsquo;s In The Plan</div>
  <div class="gl-deliverables">{parts}
  </div>
</section>
"""


def build_offer():
    """The plan billed every 4 weeks: price and terms (wordpress/plan_offer.py)."""
    lines = "".join(f"<li>{esc(line)}</li>" for line in plan_offer.OFFER_LINES)
    fit = "".join(f"<li>{esc(line)}</li>" for line in plan_offer.FIT_LINES)
    return f"""
<section class="gl-section" id="price">
  <div class="gl-section-label">Price</div>
  <div class="gl-section-title">What It Costs</div>
  <div class="gl-pricing-box">
    <div class="gl-pricing-headline">{esc(plan_offer.PRICE_LINE)}.</div>
    <div class="gl-pricing-sub">Until race week.</div>
    <ul class="gl-offer-lines">{lines}
    </ul>
    <div class="gl-pricing-note">I build this plan for:</div>
    <ul class="gl-offer-lines">{fit}
    </ul>
    <a href="/questionnaire/" class="gl-cta-btn">Build My Plan</a>
  </div>
</section>
"""


def build_faq():
    """FAQ accordion section."""
    items = ""
    for i, (q, a) in enumerate(FAQS):
        items += f"""
    <div class="gl-faq-item">
      <button class="gl-faq-q" aria-expanded="false" aria-controls="faq-{i}" data-faq-toggle>
        {esc(q)}
      </button>
      <div class="gl-faq-a" id="faq-{i}">
        {esc(a)}
      </div>
    </div>"""

    return f"""
<section class="gl-section">
  <div class="gl-section-label">Questions</div>
  <div class="gl-section-title">FAQ</div>
  {items}
</section>
"""


def build_final_cta():
    """Final CTA section."""
    return """
</div><!-- close .gl-page -->
<section class="gl-final-cta">
  <h2>Ready?</h2>
  <p>
    Tell me your race, your week and when you&rsquo;re on snow.
  </p>
  <a href="/questionnaire/" class="gl-cta-btn gl-cta-btn--outline">Build My Plan</a>
</section>
"""


def build_footer():
    """Footer with nav links and branding."""
    return """
<footer class="gl-footer">
  <a href="/">Home</a> &middot;
  <a href="/search/">Search</a> &middot;
  <a href="/training-plans/">Training Plans</a> &middot;
  <a href="/privacy/">Privacy</a> &middot;
  <a href="/terms/">Terms</a>
  <div class="gl-footer-brand">XC Ski Labs &mdash; Built for skiers who chase start lines.</div>
</footer>
""".replace("</footer>", get_endure_offer_html() + "</footer>")


def build_jsonld():
    """Product JSON-LD: one plan, $49.99 per 4-week block."""
    price = f"{plan_offer.BLOCK_PRICE_CENTS / 100:.2f}"
    product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Custom XC Ski Training Plan",
        "description": (
            "A custom cross-country ski training plan built around your race, your hours "
            "and your snow, delivered one 4-week block at a time until race week."
        ),
        "brand": {
            "@type": "Organization",
            "name": "XC Ski Labs",
        },
        "offers": {
            "@type": "Offer",
            "url": "https://xcskilabs.com/questionnaire/",
            "price": price,
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "priceSpecification": {
                "@type": "UnitPriceSpecification",
                "price": price,
                "priceCurrency": "USD",
                "billingDuration": plan_offer.BLOCK_WEEKS,
                "unitCode": "WEE",
            },
        },
        "category": "Sports Training Plans",
    }

    return _safe_json_for_script(product, indent=2)


# ── Page Assembly ──────────────────────────────────────────────

def generate_page():
    """Generate the complete training plans landing page."""
    race_count = count_race_profiles()

    css = build_css()
    css = css + LOOP_CSS + XSL_PAGE_MOTION_CSS + OFFER_CSS
    jsonld_data = build_jsonld()

    nav = build_nav()
    hero = build_hero(race_count) + PAGE_MOTION
    preview = build_plan_preview()
    plan_simulator_js = get_plan_simulator_js()
    how_it_works = build_how_it_works()
    deliverables = build_deliverables()
    pricing = build_offer()
    faq = build_faq()
    final_cta = build_final_cta()
    footer = build_footer()

    title = "Custom XC Ski Training Plans | XC Ski Labs"
    description = (
        "A custom cross-country ski training plan built around your race, your hours "
        f"and your snow. {plan_offer.PRICE_TO_RACE}."
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/xc-logo.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/training-plans/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">

  <!-- OG Meta -->
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://xcskilabs.com/training-plans/">
  <meta property="og:site_name" content="XC Ski Labs">
  <meta property="og:image" content="https://xcskilabs.com/images/og-training.jpg">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">
  <meta name="twitter:image" content="https://xcskilabs.com/images/og-training.jpg">

  <!-- Consent Mode v2 (must fire BEFORE GA4) -->
  <script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  (function() {{
      var consent = (document.cookie.match(/xl_consent=([^;]+)/) || [])[1];
      var granted = (consent === 'accepted') ? 'granted' : 'denied';
      gtag('consent', 'default', {{
          'analytics_storage': granted,
          'ad_storage': 'denied',
          'ad_user_data': 'denied',
          'ad_personalization': 'denied',
          'functionality_storage': 'granted',
          'security_storage': 'granted'
      }});
  }})();
  </script>

  <!-- GA4 -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=G-3JQLSQLPPM"></script>
  <script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', 'G-3JQLSQLPPM');
  </script>

  <!-- JSON-LD -->
  <script type="application/ld+json">
{jsonld_data}
  </script>

  <style>{css}</style>
</head>
<body>
{nav}
{hero}
{preview}
{how_it_works}
{deliverables}
{pricing}
{faq}
{final_cta}
{footer}
<script>{plan_simulator_js}</script>

<!-- Cookie Consent Banner -->
<div class="xl-consent-banner" id="xl-consent-banner">
    <div class="xl-consent-inner">
        <div class="xl-consent-text">
            We use cookies for analytics to improve the experience.
            <a href="/privacy/">Privacy policy</a>.
        </div>
        <div class="xl-consent-btns">
            <button class="xl-consent-btn xl-consent-accept" data-consent-choice="accepted">Accept</button>
            <button class="xl-consent-btn xl-consent-decline" data-consent-choice="declined">Decline</button>
        </div>
    </div>
</div>
<script>
function xlConsent(choice) {{
    document.cookie = 'xl_consent=' + choice + ';path=/;max-age=31536000;SameSite=Lax;Secure';
    var storage = (choice === 'accepted') ? 'granted' : 'denied';
    if (typeof gtag === 'function') {{
        gtag('consent', 'update', {{ 'analytics_storage': storage }});
    }}
    document.getElementById('xl-consent-banner').classList.remove('show');
}}
(function() {{
    document.querySelectorAll('[data-faq-toggle]').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            var open = btn.getAttribute('aria-expanded') === 'true';
            btn.setAttribute('aria-expanded', open ? 'false' : 'true');
            if (btn.nextElementSibling) {{
                btn.nextElementSibling.classList.toggle('open');
            }}
        }});
    }});
    document.querySelectorAll('[data-consent-choice]').forEach(function(btn) {{
        btn.addEventListener('click', function() {{
            xlConsent(btn.getAttribute('data-consent-choice'));
        }});
    }});
    if (!/xl_consent=/.test(document.cookie)) {{
        document.getElementById('xl-consent-banner').classList.add('show');
    }}
}})();
</script>
{LOOP_JS}
</body>
</html>"""

    # Write output
    output_dir = OUTPUT_DIR / "training-plans"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "index.html"

    with open(output_file, "w", encoding="utf-8") as fh:
        fh.write(page)

    print(f"  Generated: {output_file}")
    print(f"  Race count: {race_count}")


if __name__ == "__main__":
    generate_page()
