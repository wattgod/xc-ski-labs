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

# ── Price per week (cents) — derived from stripe-products.json ──

PRICE_PER_WEEK_CENTS = 1500  # $15/week


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


def load_stripe_products():
    """Load Stripe products/prices from data/stripe-products.json."""
    filepath = DATA_DIR / "stripe-products.json"
    if not filepath.exists():
        print(f"  WARNING: {filepath} not found — using default pricing")
        return None
    with open(filepath, "r", encoding="utf-8") as fh:
        return json.load(fh)


def get_price_per_week(stripe_data):
    """Extract price-per-week from Stripe data (4-week plan / 4)."""
    if not stripe_data:
        return PRICE_PER_WEEK_CENTS
    for p in stripe_data.get("prices", []):
        if "4-week" in p.get("nickname", "").lower():
            return p["amount"] // 4
    return PRICE_PER_WEEK_CENTS


def count_race_profiles():
    """Count race JSON files in race-data/."""
    data_dir = PROJECT_ROOT / "race-data"
    if not data_dir.exists():
        return 229
    files = [f for f in data_dir.glob("*.json") if f.name != "_schema.json"]
    return len(files)


# ── CSS ────────────────────────────────────────────────────────

def build_css():
    """Build the complete CSS for the training plans landing page."""
    return """
:root {
  /* Primary */
  --gl-nordic-night: #1a2332;
  --gl-fjord-blue: #2b4c7e;
  --gl-deep-powder: #354f6e;
  --gl-slate-steel: #4a5568;

  /* Accents */
  --gl-aurora-green: #1b7260;
  --gl-glacier-teal: #357a88;
  --gl-wax-orange: #b34a1a;
  --gl-wax-orange-hover: #9a3e15;

  /* Neutrals & Backgrounds */
  --gl-birch-bark: #d4cdc4;
  --gl-silver-mist: #9ca8b8;
  --gl-frost-white: #e8edf2;
  --gl-ice-paper: #f0f3f7;

  /* Typography */
  --gl-font-data: 'Sometype Mono', monospace;
  --gl-font-editorial: 'Source Serif 4', serif;

  /* Borders (neo-brutalist) */
  --gl-border-width: 2px;
  --gl-border-heavy: 3px;
  --gl-border-color: var(--gl-nordic-night);
}

*, *::before, *::after {
  box-sizing: border-box;
  border-radius: 0 !important;
  box-shadow: none !important;
}

body {
  margin: 0;
  padding: 0;
  background: var(--gl-ice-paper);
  color: var(--gl-nordic-night);
  font-family: var(--gl-font-editorial);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

a { color: var(--gl-fjord-blue); }
a:hover { color: var(--gl-glacier-teal); }

a:focus-visible, button:focus-visible {
  outline: 3px solid var(--gl-wax-orange);
  outline-offset: 2px;
}

.gl-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
}

/* ── Nav ─────────────────────────────────────────── */

.gl-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-nordic-night);
  border-bottom: var(--gl-border-heavy) solid var(--gl-fjord-blue);
  padding: 0 20px;
}
.gl-nav-inner {
  max-width: 900px;
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
  color: var(--gl-frost-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-logo:hover { color: var(--gl-birch-bark); }
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
  color: var(--gl-silver-mist);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 16px 14px;
  display: block;
}
.gl-nav-item > a:hover { color: var(--gl-frost-white); }
.gl-nav-item > a.active { color: var(--gl-frost-white); }
.gl-nav-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  background: var(--gl-nordic-night);
  border: var(--gl-border-width) solid var(--gl-fjord-blue);
  min-width: 200px;
  z-index: 1001;
  padding: 8px 0;
}
.gl-nav-item:hover .gl-nav-dropdown { display: block; }
.gl-nav-dropdown a {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  color: var(--gl-silver-mist);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 10px 16px;
  display: block;
}
.gl-nav-dropdown a:hover { color: var(--gl-frost-white); background: var(--gl-fjord-blue); }
.gl-nav-hamburger {
  display: none;
  background: none;
  border: none;
  color: var(--gl-frost-white);
  font-size: 1.5rem;
  cursor: pointer;
  padding: 8px;
  min-width: 44px;
  min-height: 44px;
}

/* ── Hero ────────────────────────────────────────── */

.gl-hero {
  background: var(--gl-nordic-night);
  color: var(--gl-ice-paper);
  padding: 64px 32px 56px;
  text-align: center;
}

.gl-hero-label {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--gl-wax-orange);
  margin-bottom: 16px;
}

.gl-hero h1 {
  font-family: var(--gl-font-editorial);
  font-size: 2.6rem;
  font-weight: 700;
  line-height: 1.1;
  margin: 0 0 20px;
}

.gl-hero-sub {
  font-family: var(--gl-font-editorial);
  font-size: 1.1rem;
  color: var(--gl-silver-mist);
  max-width: 600px;
  margin: 0 auto 28px;
  line-height: 1.6;
}

.gl-hero-stats {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-frost-white);
  letter-spacing: 0.04em;
  margin-bottom: 32px;
}

.gl-hero-stats span {
  color: var(--gl-wax-orange);
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
  background: var(--gl-wax-orange);
  color: var(--gl-frost-white);
  text-decoration: none;
  border: var(--gl-border-heavy) solid var(--gl-frost-white);
  transition: background 0.15s;
}

.gl-cta-btn:hover {
  background: var(--gl-wax-orange-hover);
  color: var(--gl-frost-white);
}

.gl-cta-btn--outline {
  background: transparent;
  border-color: var(--gl-frost-white);
}

.gl-cta-btn--outline:hover {
  background: var(--gl-frost-white);
  color: var(--gl-nordic-night);
}

/* ── Section Base ────────────────────────────────── */

.gl-section {
  padding: 48px 0;
  border-bottom: 1px solid var(--gl-birch-bark);
}

.gl-section:last-child { border-bottom: none; }

.gl-section-label {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--gl-slate-steel);
  margin-bottom: 6px;
}

.gl-section-title {
  font-family: var(--gl-font-editorial);
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--gl-nordic-night);
  margin: 0 0 24px;
  line-height: 1.25;
}

.gl-section-prose {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  color: var(--gl-nordic-night);
  line-height: 1.7;
  margin-bottom: 16px;
}

/* ── How It Works ────────────────────────────────── */

.gl-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  border: var(--gl-border-width) solid var(--gl-border-color);
}

.gl-step {
  padding: 28px 24px;
  border-right: var(--gl-border-width) solid var(--gl-border-color);
}

.gl-step:last-child { border-right: none; }

.gl-step-num {
  font-family: var(--gl-font-data);
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--gl-wax-orange);
  line-height: 1;
  margin-bottom: 12px;
}

.gl-step-title {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--gl-nordic-night);
  margin-bottom: 8px;
}

.gl-step-desc {
  font-family: var(--gl-font-editorial);
  font-size: 0.88rem;
  color: var(--gl-slate-steel);
  line-height: 1.55;
}

/* ── Deliverables ────────────────────────────────── */

.gl-deliverables {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0;
  border: var(--gl-border-width) solid var(--gl-border-color);
}

.gl-deliverable {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: var(--gl-border-width) solid var(--gl-border-color);
}

.gl-deliverable:last-child { border-bottom: none; }

.gl-deliverable-icon {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-frost-white);
  background: var(--gl-nordic-night);
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: var(--gl-border-width) solid var(--gl-nordic-night);
  flex-shrink: 0;
}

.gl-deliverable-title {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--gl-nordic-night);
  margin-bottom: 4px;
}

.gl-deliverable-desc {
  font-family: var(--gl-font-editorial);
  font-size: 0.88rem;
  color: var(--gl-slate-steel);
  line-height: 1.5;
}

/* ── Sample Week ─────────────────────────────────── */

.gl-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0;
  border: var(--gl-border-width) solid var(--gl-border-color);
}

.gl-day {
  padding: 16px 10px;
  border-right: var(--gl-border-width) solid var(--gl-border-color);
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
  color: var(--gl-slate-steel);
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
  color: var(--gl-slate-steel);
  line-height: 1.4;
}

.gl-day--rest { background: var(--gl-frost-white); }
.gl-day--rest .gl-day-type { color: var(--gl-silver-mist); }
.gl-day--intensity .gl-day-type { color: var(--gl-wax-orange); }
.gl-day--endurance .gl-day-type { color: var(--gl-aurora-green); }
.gl-day--strength .gl-day-type { color: var(--gl-glacier-teal); }
.gl-day--threshold .gl-day-type { color: var(--gl-fjord-blue); }

/* ── Pricing ─────────────────────────────────────── */

.gl-pricing-box {
  border: var(--gl-border-heavy) solid var(--gl-nordic-night);
  padding: 40px 32px;
  text-align: center;
  background: var(--gl-frost-white);
}

.gl-pricing-headline {
  font-family: var(--gl-font-editorial);
  font-size: 1.8rem;
  font-weight: 700;
  color: var(--gl-nordic-night);
  margin: 0 0 8px;
}

.gl-pricing-sub {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  color: var(--gl-slate-steel);
  letter-spacing: 0.04em;
  margin-bottom: 24px;
}

.gl-pricing-example {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-nordic-night);
  margin-bottom: 8px;
}

.gl-pricing-example strong {
  color: var(--gl-wax-orange);
}

.gl-pricing-note {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  font-style: italic;
  color: var(--gl-slate-steel);
  margin: 20px 0 28px;
}

.gl-pricing-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  border: var(--gl-border-width) solid var(--gl-border-color);
  margin: 24px 0;
  text-align: center;
}

.gl-pricing-cell {
  padding: 12px 8px;
  border-right: var(--gl-border-width) solid var(--gl-border-color);
  border-bottom: var(--gl-border-width) solid var(--gl-border-color);
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
}

.gl-pricing-cell:nth-child(3n) { border-right: none; }
.gl-pricing-cell:nth-last-child(-n+3) { border-bottom: none; }

.gl-pricing-cell--header {
  background: var(--gl-nordic-night);
  color: var(--gl-frost-white);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-size: 0.68rem;
}

/* ── FAQ ─────────────────────────────────────────── */

.gl-faq-item {
  border-bottom: 1px solid var(--gl-birch-bark);
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
  color: var(--gl-nordic-night);
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.gl-faq-q:hover { color: var(--gl-fjord-blue); }

.gl-faq-q::after {
  content: '+';
  font-family: var(--gl-font-data);
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--gl-wax-orange);
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
  color: var(--gl-slate-steel);
  line-height: 1.65;
}

.gl-faq-a.open { display: block; }

/* ── Final CTA ───────────────────────────────────── */

.gl-final-cta {
  background: var(--gl-nordic-night);
  color: var(--gl-ice-paper);
  padding: 56px 32px;
  text-align: center;
  border-top: var(--gl-border-heavy) solid var(--gl-fjord-blue);
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
  color: var(--gl-silver-mist);
  margin: 0 0 28px;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

/* ── Footer ──────────────────────────────────────── */

.gl-footer {
  background: var(--gl-nordic-night);
  color: var(--gl-silver-mist);
  padding: 28px 32px;
  text-align: center;
  border-top: 1px solid var(--gl-deep-powder);
}

.gl-footer a {
  color: var(--gl-silver-mist);
  text-decoration: none;
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  letter-spacing: 0.04em;
}

.gl-footer a:hover { color: var(--gl-frost-white); }

.gl-footer-brand {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-top: 12px;
  color: var(--gl-slate-steel);
}

/* ── Responsive ──────────────────────────────────── */

@media (max-width: 640px) {
  .gl-hero h1 { font-size: 1.8rem; }
  .gl-hero { padding: 40px 20px 36px; }
  .gl-steps { grid-template-columns: 1fr; }
  .gl-step { border-right: none; border-bottom: var(--gl-border-width) solid var(--gl-border-color); }
  .gl-step:last-child { border-bottom: none; }
  .gl-week { grid-template-columns: repeat(2, 1fr); }
  .gl-day:nth-child(2n) { border-right: none; }
  .gl-day { border-bottom: var(--gl-border-width) solid var(--gl-border-color); }
  .gl-day:last-child { border-bottom: none; }
  .gl-pricing-grid { grid-template-columns: repeat(2, 1fr); }
  .gl-pricing-cell:nth-child(3n) { border-right: var(--gl-border-width) solid var(--gl-border-color); }
  .gl-pricing-cell:nth-child(2n) { border-right: none; }
  .gl-nav-hamburger { display: block; }
  .gl-nav-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    background: var(--gl-nordic-night);
    flex-direction: column;
    padding: 16px 20px;
    gap: 0;
    border-bottom: var(--gl-border-heavy) solid var(--gl-fjord-blue);
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
  .gl-pricing-cell:nth-child(2n) { border-right: var(--gl-border-width) solid var(--gl-border-color); }
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
  background: var(--gl-nordic-night);
  color: var(--gl-frost-white);
  border-top: var(--gl-border-heavy) solid var(--gl-wax-orange);
  padding: 16px 20px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  display: none;
}

.xl-consent-banner.show { display: block; }

.xl-consent-inner {
  max-width: 900px;
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
  color: var(--gl-glacier-teal);
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
  border: var(--gl-border-width) solid var(--gl-frost-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.xl-consent-accept {
  background: var(--gl-aurora-green);
  color: var(--gl-frost-white);
}

.xl-consent-accept:hover { background: var(--gl-glacier-teal); }

.xl-consent-decline {
  background: transparent;
  color: var(--gl-silver-mist);
  border-color: var(--gl-slate-steel);
}

.xl-consent-decline:hover { color: var(--gl-frost-white); border-color: var(--gl-frost-white); }
"""


# ── Section Builders ───────────────────────────────────────────

def build_nav():
    """Top navigation bar."""
    return """
<nav class="gl-nav">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo">XC SKI LABS</a>
    <button class="gl-nav-hamburger" aria-label="Toggle navigation" onclick="document.querySelector('.gl-nav-links').classList.toggle('open')">&#9776;</button>
    <ul class="gl-nav-links">
      <li class="gl-nav-item">
        <a href="/search/">Races</a>
        <div class="gl-nav-dropdown"><a href="/search/">All XC Ski Races</a></div>
      </li>
      <li class="gl-nav-item">
        <a href="/training-plans/" class="active">Products</a>
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
</nav>
"""


def build_hero(race_count):
    """Hero section with value prop and CTA."""
    return f"""
<section class="gl-hero">
  <div class="gl-hero-label">Custom XC Ski Training</div>
  <h1>Your Race. Your Hours.<br>Your Plan.</h1>
  <p class="gl-hero-sub">
    Race-specific periodization built around your goal event, your schedule,
    and the demands of the course. Classic, skate, or both &mdash; we build the
    blocks that get you to the start line ready.
  </p>
  <div class="gl-hero-stats">
    <span>{esc(str(race_count))}</span> races indexed &middot;
    <span>14</span> scoring criteria &middot;
    <span>4&ndash;17</span> week plans
  </div>
  <a href="/questionnaire/" class="gl-cta-btn">Build My Plan</a>
</section>
"""


def build_how_it_works():
    """3-step process section."""
    return """
<div class="gl-page">
<section class="gl-section">
  <div class="gl-section-label">Process</div>
  <div class="gl-section-title">How It Works</div>
  <div class="gl-steps">
    <div class="gl-step">
      <div class="gl-step-num">01</div>
      <div class="gl-step-title">Tell Us Your Race</div>
      <div class="gl-step-desc">
        Pick your target event &mdash; Vasaloppet, Birkebeinerrennet, American Birkebeiner,
        or any of the 229 races in our database. We analyze the course profile, altitude,
        snow conditions, and competitive field to map what the race actually demands.
      </div>
    </div>
    <div class="gl-step">
      <div class="gl-step-num">02</div>
      <div class="gl-step-title">Get Your Plan</div>
      <div class="gl-step-desc">
        A periodized training block lands in your TrainingPeaks calendar: on-snow sessions,
        roller ski progressions, SkiErg intervals, and the strength work your
        posterior chain actually needs. Base through taper, calibrated to your
        zones and available hours.
      </div>
    </div>
    <div class="gl-step">
      <div class="gl-step-num">03</div>
      <div class="gl-step-title">Train Smarter</div>
      <div class="gl-step-desc">
        No guessing whether today is V2 intervals or easy distance. Every session has
        power targets, RPE, cadence cues, and technique notes. You train; the plan
        adapts across your base, build, peak, and taper phases.
      </div>
    </div>
  </div>
</section>
"""


def build_deliverables():
    """What You Get section — 5 deliverables."""
    return """
<section class="gl-section">
  <div class="gl-section-label">Deliverables</div>
  <div class="gl-section-title">What You Get</div>
  <div class="gl-section-prose">
    Every plan is built for your specific race. Not a template &mdash; a structured
    training block that accounts for the course, the climate, and the hours you
    actually have.
  </div>
  <div class="gl-deliverables">
    <div class="gl-deliverable">
      <div class="gl-deliverable-icon">TP</div>
      <div>
        <div class="gl-deliverable-title">TrainingPeaks Calendar</div>
        <div class="gl-deliverable-desc">
          Every session pushed directly to your TrainingPeaks calendar. Open your watch,
          see today&rsquo;s workout. Intervals have HR zones, RPE, and duration. On-snow,
          roller ski, and SkiErg sessions all include technique cues for classic stride,
          V1, V2, and double pole.
        </div>
      </div>
    </div>
    <div class="gl-deliverable">
      <div class="gl-deliverable-icon">P</div>
      <div>
        <div class="gl-deliverable-title">Periodized Plan</div>
        <div class="gl-deliverable-desc">
          Base &rarr; Build &rarr; Peak &rarr; Taper. Each phase has a purpose,
          each week has a structure, each session has a reason. Volume and intensity
          progress through the block so you arrive at race day sharp, not shattered.
        </div>
      </div>
    </div>
    <div class="gl-deliverable">
      <div class="gl-deliverable-icon">C</div>
      <div>
        <div class="gl-deliverable-title">Climate &amp; Altitude Prep</div>
        <div class="gl-deliverable-desc">
          Racing at altitude in Engadin or dealing with March slush at Vasaloppet?
          Your plan includes acclimatization protocols, heat/cold management,
          and wax-day contingencies based on the race&rsquo;s historical weather data.
        </div>
      </div>
    </div>
    <div class="gl-deliverable">
      <div class="gl-deliverable-icon">N</div>
      <div>
        <div class="gl-deliverable-title">Nutrition &amp; Fueling Strategy</div>
        <div class="gl-deliverable-desc">
          Carb-loading protocol, race-day fueling timeline, and feed-zone strategy.
          Calibrated to distance and expected effort &mdash; a 50&thinsp;km skate race
          demands different fueling than a 90&thinsp;km classic marathon.
        </div>
      </div>
    </div>
    <div class="gl-deliverable">
      <div class="gl-deliverable-icon">S</div>
      <div>
        <div class="gl-deliverable-title">Strength &amp; Mobility Program</div>
        <div class="gl-deliverable-desc">
          Nordic-specific strength work: single-leg stability for classic technique,
          hip flexor mobility for V2, posterior chain loading for double pole.
          3 sessions per week in base, tapering to maintenance before race day.
        </div>
      </div>
    </div>
  </div>
</section>
"""


def build_sample_week():
    """Visual weekly layout for a sample build-phase week."""
    return """
<section class="gl-section">
  <div class="gl-section-label">Sample Week</div>
  <div class="gl-section-title">Build Phase &mdash; Week 3 of 4</div>
  <div class="gl-section-prose">
    This is what a typical build-phase week looks like for a skier targeting a 50&thinsp;km
    classic race with 8&ndash;10 hours available. Your plan will vary based on your
    race distance, discipline, and schedule.
  </div>
  <div class="gl-week">
    <div class="gl-day gl-day--rest">
      <div class="gl-day-label">Mon</div>
      <div class="gl-day-type">Rest</div>
      <div class="gl-day-desc">Full recovery. Foam roll, mobility.</div>
    </div>
    <div class="gl-day gl-day--intensity">
      <div class="gl-day-label">Tue</div>
      <div class="gl-day-type">VO2max</div>
      <div class="gl-day-desc">4&times;4 min @ 95% HR max. Roller ski or SkiErg.</div>
    </div>
    <div class="gl-day gl-day--endurance">
      <div class="gl-day-label">Wed</div>
      <div class="gl-day-type">Easy Ski</div>
      <div class="gl-day-desc">60&ndash;75 min zone 2. Technique focus: diagonal stride.</div>
    </div>
    <div class="gl-day gl-day--threshold">
      <div class="gl-day-label">Thu</div>
      <div class="gl-day-type">Threshold</div>
      <div class="gl-day-desc">2&times;15 min @ LT. Double-pole intervals on flats.</div>
    </div>
    <div class="gl-day gl-day--strength">
      <div class="gl-day-label">Fri</div>
      <div class="gl-day-type">Strength</div>
      <div class="gl-day-desc">Single-leg squats, pull-ups, core. 45 min.</div>
    </div>
    <div class="gl-day gl-day--endurance">
      <div class="gl-day-label">Sat</div>
      <div class="gl-day-type">Long Ski</div>
      <div class="gl-day-desc">2&ndash;2.5 hr classic distance. Steady pace, race nutrition practice.</div>
    </div>
    <div class="gl-day gl-day--rest">
      <div class="gl-day-label">Sun</div>
      <div class="gl-day-type">Recovery</div>
      <div class="gl-day-desc">30 min easy spin or walk. Stretching.</div>
    </div>
  </div>
</section>
"""


def build_pricing(stripe_data):
    """Pricing section with dynamic calculation from Stripe data."""
    ppw = get_price_per_week(stripe_data)
    ppw_dollars = ppw // 100

    # Build example rows from stripe prices
    examples = []
    if stripe_data:
        for p in stripe_data.get("prices", []):
            nick = p.get("nickname", "")
            if "week plan" in nick.lower() and "17" not in nick:
                amount = p["amount"] // 100
                # Extract week count (handles "4-week", "12-Week", etc.)
                m = re.search(r'(\d+)', nick)
                if m:
                    weeks = int(m.group(1))
                    examples.append((weeks, amount))

    # Fallback if no stripe data
    if not examples:
        examples = [
            (4, 60), (6, 90), (8, 120), (10, 150), (12, 180),
            (14, 210), (16, 240),
        ]

    examples.sort()

    # Build pricing grid rows (show a representative subset)
    show = [e for e in examples if e[0] in (4, 6, 8, 10, 12, 16)]
    if not show:
        show = examples[:6]

    grid_cells = ""
    for weeks, total in show:
        grid_cells += f"""
    <div class="gl-pricing-cell">{weeks} weeks</div>
    <div class="gl-pricing-cell">${ppw_dollars}/wk</div>
    <div class="gl-pricing-cell"><strong>${total}</strong></div>"""

    # Cap note
    cap_price = 249
    if stripe_data:
        for p in stripe_data.get("prices", []):
            if "17" in p.get("nickname", ""):
                cap_price = p["amount"] // 100
                break

    return f"""
<section class="gl-section">
  <div class="gl-section-label">Investment</div>
  <div class="gl-section-title">Pricing</div>
  <div class="gl-pricing-box">
    <div class="gl-pricing-headline">${ppw_dollars}/week. That&rsquo;s it.</div>
    <div class="gl-pricing-sub">No subscription. No recurring charges. One plan, one price.</div>
    <div class="gl-pricing-example">
      12-week plan = <strong>$180</strong>
    </div>
    <div class="gl-pricing-example">
      8-week plan = <strong>$120</strong>
    </div>
    <div class="gl-pricing-grid">
      <div class="gl-pricing-cell gl-pricing-cell--header">Duration</div>
      <div class="gl-pricing-cell gl-pricing-cell--header">Rate</div>
      <div class="gl-pricing-cell gl-pricing-cell--header">Total</div>
      {grid_cells}
    </div>
    <div class="gl-pricing-note">
      Plans 17 weeks or longer cap at ${cap_price}. Less than a single wax session
      at a Worldloppet feed zone.
    </div>
    <a href="/questionnaire/" class="gl-cta-btn">Start Your Plan</a>
  </div>
</section>
"""


def build_faq():
    """FAQ accordion section."""
    faqs = [
        (
            "How do I get the workouts?",
            "Every session is pushed to your TrainingPeaks calendar. Sync your Garmin, "
            "COROS, or Polar watch and the workout is on your wrist. On-snow and roller ski "
            "sessions include heart rate zones, RPE, cadence targets, and technique cues. "
            "SkiErg sessions have full interval structure with rest periods."
        ),
        (
            "I race both classic and skate. Can the plan cover both?",
            "Yes. If your target race offers both techniques (or you have two target races "
            "in different disciplines), we structure the plan around your primary goal and "
            "weave in technique-specific sessions for the secondary discipline. Double-pole "
            "work carries over to both."
        ),
        (
            "How do you account for roller skiing vs. on-snow training?",
            "We build plans assuming a mixed environment. Early-season blocks lean on roller "
            "skis, SkiErg, and running with poles. As snow arrives, sessions shift to on-snow "
            "with the same intensity targets. If you train year-round on snow (lucky you), we "
            "adjust accordingly."
        ),
        (
            "What if I only have 5 hours per week?",
            "We build with what you have. A 5-hour week means fewer sessions but sharper "
            "prioritization: the key intervals stay, the junk miles go. Every plan is "
            "calibrated to your available hours &mdash; we do not pad volume for the sake of it."
        ),
        (
            "Do you cover race-day logistics like waxing and feed zones?",
            "Your plan includes a race-week checklist covering wax prep, feed-zone strategy, "
            "warm-up protocol, and pacing guidance. For major Worldloppet and Ski Classics "
            "events, we include course-specific notes from our database of "
            "229 scored race profiles."
        ),
        (
            "Can I get a plan for an ultramarathon ski race?",
            "Absolutely. We have profiles for events from 10&thinsp;km sprints to "
            "220&thinsp;km ultra-distance races like Nordenskioldsloppet. Longer races "
            "get additional fueling protocols, pacing strategy, and durability-focused "
            "training blocks."
        ),
    ]

    items = ""
    for i, (q, a) in enumerate(faqs):
        items += f"""
    <div class="gl-faq-item">
      <button class="gl-faq-q" aria-expanded="false" aria-controls="faq-{i}"
              onclick="this.setAttribute('aria-expanded',this.getAttribute('aria-expanded')==='true'?'false':'true');this.nextElementSibling.classList.toggle('open')">
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
    Tell us your race, your hours, and when you need to be ready.
    We handle the periodization.
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
  <a href="/training-plans/">Training Plans</a>
  <div class="gl-footer-brand">XC Ski Labs &mdash; Built for skiers who chase start lines.</div>
</footer>
"""


def build_jsonld(stripe_data):
    """Build Product JSON-LD structured data."""
    ppw = get_price_per_week(stripe_data)
    ppw_dollars = f"{ppw / 100:.2f}"

    # Extract lowPrice, highPrice, offerCount from Stripe data
    low_price = "60.00"
    high_price = "249.00"
    offer_count = "14"
    if stripe_data:
        amounts = []
        for p in stripe_data.get("prices", []):
            amt = p.get("amount", 0)
            if amt > 0:
                amounts.append(amt)
        if amounts:
            low_price = f"{min(amounts) / 100:.2f}"
            high_price = f"{max(amounts) / 100:.2f}"
            offer_count = str(len(amounts))

    product = {
        "@context": "https://schema.org",
        "@type": "Product",
        "name": "Custom XC Ski Training Plan",
        "description": (
            "Race-specific periodized training plan for cross-country skiing. "
            "Includes structured workouts, nutrition strategy, strength program, "
            "and climate preparation. 4-17 week plans available."
        ),
        "brand": {
            "@type": "Organization",
            "name": "XC Ski Labs",
        },
        "offers": {
            "@type": "AggregateOffer",
            "priceCurrency": "USD",
            "lowPrice": low_price,
            "highPrice": high_price,
            "offerCount": offer_count,
            "availability": "https://schema.org/InStock",
        },
        "category": "Sports Training Plans",
    }

    return _safe_json_for_script(product, indent=2)


# ── Page Assembly ──────────────────────────────────────────────

def generate_page():
    """Generate the complete training plans landing page."""
    stripe_data = load_stripe_products()
    race_count = count_race_profiles()

    css = build_css()
    jsonld_data = build_jsonld(stripe_data)

    nav = build_nav()
    hero = build_hero(race_count)
    how_it_works = build_how_it_works()
    deliverables = build_deliverables()
    sample_week = build_sample_week()
    pricing = build_pricing(stripe_data)
    faq = build_faq()
    final_cta = build_final_cta()
    footer = build_footer()

    title = "Custom XC Ski Training Plans | XC Ski Labs"
    description = (
        "Race-specific periodized training plans for cross-country skiing. "
        "229 races indexed. Structured workouts, nutrition strategy, and "
        "strength programming. $15/week."
    )

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/training-plans/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%231a2332'/><text x='16' y='24' text-anchor='middle' font-family='monospace' font-size='22' font-weight='700' fill='%23e8edf2'>GL</text></svg>">

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
{how_it_works}
{deliverables}
{sample_week}
{pricing}
{faq}
{final_cta}
{footer}

<!-- Cookie Consent Banner -->
<div class="xl-consent-banner" id="xl-consent-banner">
    <div class="xl-consent-inner">
        <div class="xl-consent-text">
            We use cookies for analytics to improve the experience.
            <a href="/privacy/">Privacy policy</a>.
        </div>
        <div class="xl-consent-btns">
            <button class="xl-consent-btn xl-consent-accept" onclick="xlConsent('accepted')">Accept</button>
            <button class="xl-consent-btn xl-consent-decline" onclick="xlConsent('declined')">Decline</button>
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
    if (!/xl_consent=/.test(document.cookie)) {{
        document.getElementById('xl-consent-banner').classList.add('show');
    }}
}})();
</script>
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
    print(f"  Stripe data: {'loaded' if stripe_data else 'defaults'}")


if __name__ == "__main__":
    generate_page()
