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
from scripts.consent import get_consent_banner_html, get_ga4_head  # noqa: E402

XL_GA4_HEAD = get_ga4_head()
XL_CONSENT_BANNER = get_consent_banner_html()
from scripts.endure_offer import get_endure_offer_html
from scripts.xsl_loops import LOOP_CSS, LOOP_JS, loop_figure  # noqa: E402

# Gravel God skiing, motion-captured from Matti's course videos (scripts/xsl_loops.py); caption only, no new copy
PAGE_MOTION = f'<section class="xsl-page-motion">{loop_figure("doublepole", "wide")}</section>'
XSL_PAGE_MOTION_CSS = """
.xsl-page-motion { max-width: var(--gl-measure); margin: 0 auto; padding: 40px 20px 8px; }
"""
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
.gl-included {
  list-style: none; padding: 0; margin: 0 0 24px;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 8px 32px;
}
.gl-included li { padding-left: 22px; position: relative; line-height: 1.4; }
.gl-included li::before { content: "✓"; position: absolute; left: 0; font-weight: 700; }
.gl-fine-print { font-size: 13px; line-height: 1.5; opacity: 0.75; margin: 16px 0 0; }
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
a:hover { text-decoration: underline; }

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
.gl-nav-logo:hover { text-decoration: underline; }
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
  --gl-muted: var(--gl-caption-on-dark);
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
"""


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
  <h1>{esc(plan_offer.HEADLINE)}</h1>
  <p class="gl-hero-sub">{esc(plan_offer.PRICE_LINE)}.</p>
  <a href="/questionnaire/" class="gl-cta-btn">Build My Plan</a>
</section>
"""


# Rider-facing copy on this page (Matti speaking). The headline, the list of
# what's included and the fine print live in plan_offer.py; each claim is
# something the ski engine builds (athletes/scripts/ski_engine.py,
# ALGORITHM_EVIDENCE §20), the course grant opens or the plan's emails send.
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


def build_included():
    """Everything the plan includes, as a fast list (plan_offer.INCLUDED)."""
    items = "".join(f"<li>{esc(line)}</li>" for line in plan_offer.INCLUDED)
    return f"""
<div class="gl-page">
<section class="gl-section" id="included">
  <div class="gl-section-title">What&rsquo;s Included</div>
  <ul class="gl-included">{items}
  </ul>
  <a href="/questionnaire/" class="gl-cta-btn">Build My Plan</a>
</section>
</div>
"""


def build_offer():
    """The plan billed every 4 weeks: price and terms (wordpress/plan_offer.py)."""
    # Opens .gl-page; build_final_cta closes it after the FAQ.
    return f"""
<div class="gl-page">
<section class="gl-section" id="price">
  <div class="gl-pricing-box">
    <div class="gl-pricing-headline">{esc(plan_offer.PRICE_LINE)}.</div>
    <a href="/questionnaire/" class="gl-cta-btn">Build My Plan</a>
    <p class="gl-fine-print">{esc(plan_offer.FINE_PRINT)}</p>
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
    included = build_included()
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
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/training-plans/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Stencil+Display:wght@700;900&family=Big+Shoulders+Text:wght@600;800&family=Libre+Franklin:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">

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

  <!-- Consent Mode v2 default + GA4 config (scripts/consent.py) -->
  {XL_GA4_HEAD}

  <!-- JSON-LD -->
  <script type="application/ld+json">
{jsonld_data}
  </script>

  <style>{css}</style>
</head>
<body>
{nav}
{hero}
{included}
{pricing}
{faq}
{final_cta}
{footer}

{XL_CONSENT_BANNER}
<script>
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
