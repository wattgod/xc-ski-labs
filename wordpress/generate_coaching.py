#!/usr/bin/env python3
"""
XC Ski Labs: Coaching Landing Page Generator ("Field Notes", Sledge Stores)

Generates the public /coaching/ landing page. Rebuilt 2026-11-15 with the
same structure as the Gravel God "Field Notes" coaching page (Matti picked
mock Opus C with the Astra B photo card, and asked for the same page on
every brand, with the copy tuned to the brand and the brand's character):

  hero (H1 + ID card: my real photo crossfading to the v6.7 character in the
  xc outfit) -> fit -> terms (what you get) -> week -> how-it-works ->
  tiers (three crates + 3-question picker) -> faq -> final-cta

Drawn in the Sledge Stores book (docs/brand/sledge-stores/README.md): the
hero is a stitched oat panel, the ID card and the lists are checklists,
the levels are crates with stencilled prices, the fine print is shipping
tags. Salmon appears on one object only: the crate the picker marks, with
the word Recommended. Before an answer there is no salmon object.

Billing matches the real checkout (athlete-custom-training-plan-pipeline
brands.yaml xcskilabs.coaching: billing_period_days 28, setup_fee_cents
9900, trainingpeaks_premium_included true): every 4 weeks, plus a
one-time $99 setup fee. Never "monthly" in billing copy.

Not built, on purpose (no stand-ins): an athlete-words proof section and a
capacity line. Both wait on real words and a real number from Matti.

Usage:
    python wordpress/generate_coaching.py
    python wordpress/generate_coaching.py --output-dir output
"""

import html
import json
import shutil
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_race_pages import build_nav_header as build_canonical_nav_header
from scripts.consent import get_consent_banner_html, get_ga4_head  # noqa: E402

XL_GA4_HEAD = get_ga4_head()
XL_CONSENT_BANNER = get_consent_banner_html()
from scripts.endure_offer import get_endure_offer_html

SITE_BASE_URL = "https://xcskilabs.com"
APPLY_URL = "/coaching/apply/"
GA4_ID = "G-3JQLSQLPPM"

# Images. generate_page() copies them to <output>/coaching/img/ and
# scripts/deploy.py sync_coaching uploads that folder before the page.
# A missing file stops the build: no stand-in picture.
IMG_SRC_DIR = SCRIPT_DIR / "assets" / "coaching"
IMG_URL_BASE = "/coaching/img"
IMAGES = {
    # Real photo: grocery aisle, felt hat, frozen pizza.
    "photo": ("matti-pizza.webp", 720, 960),
    # v6.7 character (gravel-god-character rig), xc outfit, same pose.
    "cartoon": ("matti-pizza-xc.webp", 720, 960),
}


# ── Helpers ────────────────────────────────────────────────────

def esc(text) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


def _safe_json_for_script(obj, **kwargs) -> str:
    """Serialize obj to JSON safe for embedding inside <script> tags.

    json.dumps does NOT escape '</' sequences, so a string containing
    '</script>' would prematurely close the <script> element. We
    replace '</' with '<\\/' which is valid JSON and safe in HTML.
    (Repo pitfall #4.)
    """
    raw = json.dumps(obj, **kwargs)
    return raw.replace("</", "<\\/")


def load_tokens_css() -> str:
    """Read the Sledge Stores tokens + components for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


def _img(key: str) -> tuple:
    name, w, h = IMAGES[key]
    return f"{IMG_URL_BASE}/{name}", w, h


# ── Copy ───────────────────────────────────────────────────────

# Hero (Matti, 2026-11-15): he picked this H1 and sub-line and asked for the
# page to read "like Johnny Klister would write it", the wax-bench voice.
# No positioning against AI or software anywhere on the page (Matti,
# 2026-11-14); tests/test_no_ai_positioning.py enforces this.
HERO_H1 = "Ski coaching for people who&rsquo;ll roller ski in July to pass people in February."
HERO_SUB = (
    "I plan your dryland and your snow weeks around your races, read the "
    "sessions you upload, and move the week when life or a thaw gets in the "
    "way. From $199 every 4 weeks."
)
APPLY_CTA = "APPLY FOR SKI COACHING &rarr;"
REPLY_TIME = "48 hours"
CONTACT_EMAIL = "gravelgodcoaching@gmail.com"

TIERS = (
    ("min", "Min", "$199"),
    ("mid", "Mid", "$299"),
    ("max", "Max", "$1,200"),
)
TIER_INTERVAL = "every 4 weeks"
TIER_BLURBS = {
    "min": "You keep your own training going and want my eyes on it each week.",
    "mid": "I check each session as it comes in and adjust the next days to match.",
    "max": "Every session read the day you upload it. For the season built around one race.",
}
TIER_FEATURES = {
    "min": ("Weekly training review", "File analysis", "Quarterly strategy calls",
            "Structured workouts for your watch or ski erg", "Race-day nutrition plan",
            "Custom training guide", "TrainingPeaks Premium"),
    "mid": ("Everything in Min", "Detailed training-file analysis", "Every-4-week strategy calls",
            "Weekly plan adjustments", "Direct message access", "Blindspot detection"),
    "max": ("Everything in Mid", "Daily file review", "On-demand calls", "Race-week strategy",
            "Multi-race season planning", "Priority response"),
}

# ID card. Matti's bio line (2026-11-15), tuned for skiing, and a
# self-deprecating resume of public facts only (GG about page, XC about
# page, the XC course). No ski results: none are on record.
ID_BIO = "I&rsquo;m Matti Rowe. Peddler of skis, bikes and hot takes, and really fast clients."
ID_ROWS = (
    ("Skis", "Classic and skate. I teach both in my technique course."),
    ("Day job", "Twelve years at TrainingPeaks, teaching coaches and athletes. Promoted twice."),
    ("Bikes", "Cat 1 road racer on the NRC. Cat 5 bike handling."),
    ("Team", "Rio Grande Elite, until it folded the same year my third kid was born."),
    ("Talent", "Short supply. Very few people have gone farther on less of it."),
)

PICKER_INTRO = "Answer three questions and I&rsquo;ll mark the one I&rsquo;d pick."
PICKER_QUESTIONS = (
    ("How closely should I watch your sessions?", (
        "Once a week is enough",
        "As they come in",
        "The day each one lands",
    )),
    ("A thaw wipes out your week. How fast should the plan change?", (
        "At the weekly review",
        "That same week",
        "Today, on a call",
    )),
    ("What&rsquo;s your winter built around?", (
        "One race, my own way",
        "One race, done right",
        "A full race season",
    )),
)
PICKER_EMPTY = "Answer all three and I&rsquo;ll mark a level."


# ── CSS ────────────────────────────────────────────────────────

def build_css() -> str:
    """Tokens + Sledge Stores components, then this page's layout.

    Colours come only from the book's tokens (ground, panel, paper, ink,
    ink-2, rule, action, splash and friends). Salmon (--splash) is used for
    the one picked crate and the button underline the components draw.
    """
    return load_tokens_css() + """

*, *::before, *::after {
  box-sizing: border-box;
  border-radius: 0 !important;
}

body {
  margin: 0;
  padding: 0;
  background-color: var(--ground);
  color: var(--ink);
  font: 400 17px/1.6 var(--font-body);
  -webkit-font-smoothing: antialiased;
}

a { color: var(--ink); }

/* ── Nav ──────────────────────────────────────── */

.gl-coach-nav {
  background: var(--gl-carbon);
  border-bottom: 1px solid var(--gl-carbon);
  padding: 14px 24px;
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.gl-coach-nav-brand {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 2px;
}

.gl-coach-nav-links {
  display: flex;
  gap: 20px;
  margin-left: auto;
  flex-wrap: wrap;
}

.gl-coach-nav-links a {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: color 0.15s;
}

.gl-coach-nav-links a:hover { color: var(--gl-white); }

.gl-coach-nav-links a.active {
  color: var(--gl-white);
  border-bottom: 2px solid var(--gl-white);
  padding-bottom: 2px;
}

/* Shared site navigation */
.gl-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-white);
  padding: 0 24px;
}
.gl-nav-inner {
  max-width: var(--gl-measure);
  min-height: 52px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.gl-nav-logo {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-logo em { color: var(--gl-white); }
.gl-nav-links {
  display: flex;
  align-items: center;
  list-style: none;
  margin: 0;
  padding: 0;
}
.gl-nav-item { position: relative; }
.gl-nav-item > a {
  display: block;
  padding: 16px 14px;
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-decoration: none;
  text-transform: uppercase;
}
.gl-nav-item > a:hover, .gl-nav-item > a.active { color: var(--gl-white); }
.gl-nav-dropdown {
  display: none;
  position: absolute;
  top: 100%;
  left: 0;
  min-width: 200px;
  padding: 8px 0;
  background: var(--gl-carbon);
  border: 2px solid var(--gl-white);
}
.gl-nav-item:hover .gl-nav-dropdown { display: block; }
.gl-nav-dropdown a {
  display: block;
  padding: 10px 16px;
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-decoration: none;
  text-transform: uppercase;
}
.gl-nav-dropdown a:hover { background: var(--gl-white); color: var(--gl-carbon); }
.gl-nav-hamburger {
  display: none;
  min-width: 44px;
  min-height: 44px;
  padding: 8px;
  background: transparent;
  border: 0;
  color: var(--gl-white);
  cursor: pointer;
  font-size: 1.5rem;
}

/* ── Page layout ─────────────────────────────── */

.gl-coach-inner { max-width: 1200px; margin: 0 auto; padding: 0 clamp(16px, 4vw, 48px); }
.gl-coach-band { padding: clamp(56px, 8vw, 104px) 0; }
.gl-coach-band--panel { background: var(--panel); border-top: var(--stroke-band) solid var(--ink); border-bottom: var(--stroke-band) solid var(--ink); }
.gl-coach-band--panel + .gl-coach-band--panel { border-top: 0; }
.gl-coach-sec-head { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: flex-end; margin: 0 0 32px; padding-bottom: 10px; border-bottom: var(--stroke-rule) solid var(--ink); }
.gl-coach-sec-num { justify-self: start; padding: 6px 12px; background: var(--ink); color: var(--ground); font: 800 16px/1.2 var(--font-label); letter-spacing: .4em; }
.gl-coach-sec-title { margin: 0; font: 900 clamp(36px, 5.6vw, 72px)/.9 var(--font-stencil); text-transform: uppercase; }
.gl-coach-sec-sub { margin: 0 0 28px; max-width: 58ch; font: 600 clamp(18px, 1.7vw, 21px)/1.5 var(--font-body); }
.gl-coach-label { margin: 0; font: 800 14px/1.2 var(--font-label); letter-spacing: .16em; text-transform: uppercase; color: var(--ink-2); }
.gl-coach-fine { font-size: 15px; }

/* ── Hero: stitched oat panel ────────────────── */

.gl-coach-hero { position: relative; background: var(--panel); border-bottom: var(--stroke-band) solid var(--ink); }
.gl-coach-hero::before { content: ""; position: absolute; inset: 12px; border: var(--stroke-stitch) dashed var(--stitch-soft); pointer-events: none; }
.gl-coach-hero-grid { position: relative; display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(0, 1fr); gap: clamp(24px, 4vw, 56px); padding: clamp(40px, 7vw, 96px) clamp(28px, 4vw, 48px); max-width: 1200px; margin: 0 auto; align-items: start; }
.gl-coach-hero h1 { margin: 0 0 24px; font: 800 clamp(34px, 4.6vw, 60px)/1.04 var(--font-label); text-transform: uppercase; letter-spacing: .01em; max-width: 18ch; }
.gl-coach-tagline { margin: 0 0 32px; max-width: 38ch; font: 600 clamp(18px, 1.7vw, 21px)/1.5 var(--font-body); }
.gl-coach-hero-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 20px; }
.gl-coach-hero-actions .gl-coach-fine { margin: 0; }

/* ── ID card: a checklist-style file card ────── */

.gl-coach-id { background: var(--paper); border: var(--stroke-stitch) solid var(--ink); }
.gl-coach-id-head { display: flex; justify-content: space-between; padding: 12px 18px; background: var(--ink); color: var(--ground); font: 800 16px/1.2 var(--font-label); letter-spacing: .1em; text-transform: uppercase; }
.gl-coach-id-photo { position: relative; margin: 14px; aspect-ratio: 3 / 4; overflow: hidden; background: var(--panel); outline: var(--stroke-stitch) dashed var(--ink); outline-offset: -8px; }
.gl-coach-id-photo img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: center 20%; }
.gl-coach-id-toon { opacity: 0; animation: gl-coach-idswap 9s ease-out 2s infinite; }
@keyframes gl-coach-idswap { 0%, 38% { opacity: 0; } 50%, 88% { opacity: 1; } 100% { opacity: 0; } }
.gl-coach-id-bio { margin: 0 18px 14px; font: 800 clamp(20px, 1.8vw, 24px)/1.2 var(--font-label); text-transform: uppercase; letter-spacing: .01em; }
.gl-coach-id-rows { margin: 0; padding: 0 18px 12px; }
.gl-coach-id-rows div { display: grid; grid-template-columns: 72px 1fr; gap: 10px; padding: 9px 0; border-top: var(--stroke-weave) dashed var(--rule); font-size: 15px; line-height: 1.45; }
.gl-coach-id-rows dt { font: 800 13px/1.5 var(--font-label); letter-spacing: .12em; text-transform: uppercase; color: var(--ink-2); }
.gl-coach-id-rows dd { margin: 0; }

/* ── Lists (fit, what you get, steps, week) ──── */

.gl-coach-lists { display: grid; grid-template-columns: 1fr 1fr; gap: clamp(18px, 2.4vw, 28px); }
.gl-coach-lists--3 { grid-template-columns: repeat(3, 1fr); }
.gl-coach-list { background: var(--paper); border: var(--stroke-stitch) solid var(--ink); }
.gl-coach-list h3 { margin: 0; padding: 12px 18px; background: var(--ink); color: var(--ground); font: 800 18px/1.2 var(--font-label); letter-spacing: .1em; text-transform: uppercase; }
.gl-coach-list--quiet h3 { background: var(--panel); color: var(--ink); border-bottom: var(--stroke-stitch) solid var(--ink); }
.gl-coach-list ul, .gl-coach-list ol { list-style: none; margin: 0; padding: 10px 18px 16px; }
.gl-coach-list li { display: flex; gap: 12px; align-items: flex-start; padding: 10px 0; border-bottom: var(--stroke-weave) dashed var(--rule); font-weight: 600; }
.gl-coach-list li:last-child { border-bottom: 0; }
.gl-coach-mark { flex: none; display: grid; place-items: center; width: 18px; height: 18px; margin-top: 4px; font: 800 13px/1 var(--font-body); }
.gl-coach-mark--yes { background: var(--ink); color: var(--ground); border: var(--stroke-stitch) solid var(--ink); }
.gl-coach-mark--no { border: var(--stroke-stitch) dotted var(--rule); color: var(--ink-2); }

.gl-coach-get { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 clamp(24px, 4vw, 56px); }
.gl-coach-get li { padding: 18px 0; border-top: var(--stroke-weave) dashed var(--rule); }
.gl-coach-get li:first-child { grid-column: 1 / -1; padding-top: 0; border-top: 0; }
.gl-coach-get h3 { margin: 6px 0 6px; font: 800 clamp(22px, 2vw, 26px)/1.1 var(--font-label); text-transform: uppercase; letter-spacing: .02em; }
.gl-coach-get li:first-child h3 { font-size: clamp(28px, 3vw, 40px); }
.gl-coach-get p { margin: 0; max-width: 58ch; }
.gl-coach-get li:first-child p { font: 600 clamp(18px, 1.7vw, 21px)/1.5 var(--font-body); }

.gl-coach-week li { display: grid; grid-template-columns: 112px 1fr; gap: 10px; }
.gl-coach-week dt, .gl-coach-week .gl-coach-label { padding-top: 3px; }
.gl-coach-week-off { color: var(--ink-2); font-weight: 400; }
.gl-coach-note { margin: 22px 0 0; font-style: italic; font-size: 18px; max-width: 58ch; }

.gl-coach-steps li { display: grid; grid-template-columns: 44px 150px 1fr; gap: 6px 16px; align-items: baseline; }
.gl-coach-steps .gl-coach-num { font: 900 32px/1 var(--font-stencil); }
.gl-coach-steps h4 { margin: 0 0 2px; font: 800 20px/1.2 var(--font-label); text-transform: uppercase; letter-spacing: .02em; }
.gl-coach-steps p { margin: 0; font-weight: 400; }

/* ── Levels: picker + crates ─────────────────── */

.gl-coach-picker { display: grid; grid-template-columns: repeat(3, 1fr); gap: clamp(18px, 2.4vw, 28px); margin: 0 0 20px; }
.gl-coach-picker[hidden], .gl-coach-picker-out[hidden] { display: none; }
.gl-coach-picker fieldset { margin: 0; padding: 0; min-width: 0; background: var(--paper); border: var(--stroke-stitch) solid var(--ink); }
.gl-coach-picker legend { float: left; width: 100%; margin: 0; padding: 12px 18px; background: var(--ink); color: var(--ground); font: 800 16px/1.2 var(--font-label); letter-spacing: .1em; text-transform: uppercase; }
.gl-coach-picker p { clear: both; margin: 0; padding: 12px 18px 4px; font-weight: 600; }
.gl-coach-picker label { display: flex; gap: 12px; align-items: center; min-height: 44px; margin: 0 18px; border-bottom: var(--stroke-weave) dashed var(--rule); cursor: pointer; }
.gl-coach-picker label:last-child { border-bottom: 0; margin-bottom: 6px; }
.gl-coach-picker input { appearance: none; -webkit-appearance: none; flex: none; width: 18px; height: 18px; margin: 0; border: var(--stroke-stitch) dotted var(--rule); background: transparent; cursor: pointer; }
.gl-coach-picker input:checked { border-style: solid; border-color: var(--ink); background: var(--ink); }
.gl-coach-picker input:checked + span { font-weight: 600; }
.gl-coach-picker-out { margin: 0 0 40px; font: 800 18px/1.3 var(--font-label); letter-spacing: .1em; text-transform: uppercase; }

.gl-coach-crates { display: grid; grid-template-columns: repeat(3, 1fr); gap: clamp(18px, 2.4vw, 28px); list-style: none; margin: 0; padding: 0; }
.gl-coach-crates .xc-crate__in { gap: 0; }
.gl-coach-crates .xc-price { margin: 10px 0 4px; }
.gl-coach-per { margin: 0 0 14px; font: 800 16px/1.2 var(--font-label); letter-spacing: .12em; text-transform: uppercase; }
.gl-coach-crates ul { list-style: none; margin: 0 0 22px; padding: 0; }
.gl-coach-crates li { padding: 7px 0; border-top: var(--stroke-weave) dashed currentColor; font-size: 15px; font-weight: 600; }
.gl-coach-crates .xc-ribbon { display: none; }
.gl-coach-crates .xc-crate--splash .xc-ribbon { display: block; }
.gl-coach-tags { margin-top: 40px; }
.gl-coach-tags h3 { margin: 0 0 8px; font: 800 18px/1.2 var(--font-label); letter-spacing: .1em; text-transform: uppercase; }

/* ── FAQ ─────────────────────────────────────── */

.gl-coach-faq-list { max-width: 860px; }
.gl-coach-faq-item { border-top: var(--stroke-stitch) solid var(--ink); }
.gl-coach-faq-item:last-child { border-bottom: var(--stroke-stitch) solid var(--ink); }
.gl-coach-faq-item summary { list-style: none; cursor: pointer; display: grid; grid-template-columns: 52px 1fr 24px; gap: 8px; min-height: 56px; align-items: center; padding: 10px 0; font: 800 clamp(18px, 1.8vw, 22px)/1.25 var(--font-label); text-transform: uppercase; letter-spacing: .02em; }
.gl-coach-faq-item summary::-webkit-details-marker { display: none; }
.gl-coach-faq-item summary::after { content: "+"; font: 900 28px/1 var(--font-stencil); }
.gl-coach-faq-item[open] summary::after { content: "\\2212"; }
.gl-coach-faq-item p { margin: 0 0 20px 60px; max-width: 58ch; }

/* ── Close ───────────────────────────────────── */

.gl-coach-close h2 { margin: 0 0 20px; font: 900 clamp(48px, 8vw, 112px)/.86 var(--font-stencil); text-transform: uppercase; }
.gl-coach-close-hook { margin: 0 0 28px; max-width: 38ch; font: 600 clamp(18px, 1.7vw, 21px)/1.5 var(--font-body); }
.gl-coach-close .xc-btn { max-width: 420px; }
.gl-coach-close-contact { margin: 20px 0 0; }

/* ── Footer ───────────────────────────────────── */

.gl-coach-footer {
  background: var(--gl-carbon);
  color: var(--gl-muted);
  padding: 32px 24px;
  border-top: 1px solid var(--gl-hairline);
  text-align: center;
}

.gl-coach-footer-brand {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-white);
  text-transform: uppercase;
  letter-spacing: 2px;
}

.gl-coach-footer-links {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
}

.gl-coach-footer-links a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.gl-coach-footer-links a:hover { color: var(--gl-white); }

.gl-coach-footer-copy {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  color: var(--gl-muted);
  margin-top: 16px;
}

/* ── Mobile sticky CTA ────────────────────────── */

.gl-coach-sticky-cta { display: none; }

@media (max-width: 768px) {
  .gl-coach-sticky-cta {
    display: block;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 999;
    background: var(--gl-carbon);
    padding: 12px 16px;
    text-align: center;
    border-top: 2px solid var(--gl-paper);
  }
  .gl-coach-sticky-cta a {
    display: block;
    color: var(--gl-paper);
    font-family: var(--gl-font-data);
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    text-decoration: none;
    padding: 6px 0;
    min-height: 44px;
  }
  /* Repo pitfall #32: the fixed sticky CTA must not cover the end of the
     page. The padding sits on body, not .gl-coach-page, because the
     Privacy choices strip comes after the page wrapper and must stay
     tappable. */
  body { padding-bottom: 80px; }
}

/* ── Responsive ──────────────────────────────── */

@media (max-width: 979.98px) {
  .gl-coach-picker { grid-template-columns: 1fr; }
  .gl-coach-crates { grid-template-columns: 1fr 1fr; }
  .gl-coach-lists--3 { grid-template-columns: 1fr; }
}
@media (max-width: 900px) {
  .gl-coach-hero-grid { grid-template-columns: 1fr; }
  .gl-coach-id { max-width: 420px; }
}
@media (max-width: 768px) {
  .gl-coach-hero-grid { padding: 32px 24px 48px; }
  .gl-coach-hero h1 { font-size: 30px; margin-bottom: 16px; }
  .gl-coach-tagline { font-size: 17px; margin-bottom: 20px; }
  .gl-coach-hero-actions .xc-btn { width: 100%; }
  .gl-coach-lists, .gl-coach-get { grid-template-columns: 1fr; }
  .gl-coach-steps li { grid-template-columns: 36px 1fr; }
  .gl-coach-steps .gl-coach-label { grid-column: 2; }
  .gl-coach-steps li > div { grid-column: 2; }
  .gl-coach-faq-item summary { grid-template-columns: 40px 1fr 20px; }
  .gl-coach-faq-item p { margin-left: 48px; }
  .gl-nav { padding: 0 20px; }
  .gl-nav-hamburger { display: block; }
  .gl-nav-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    flex-direction: column;
    align-items: stretch;
    background: var(--gl-carbon);
    border-bottom: 3px solid var(--gl-white);
  }
  .gl-nav-links.open { display: flex; }
  .gl-nav-dropdown { display: block; position: static; border: 0; padding: 0 0 0 16px; }
  .gl-nav-item > a { padding: 12px 0; }
}
@media (max-width: 639.98px) {
  .gl-coach-crates { grid-template-columns: 1fr; gap: 30px; }
}

/* Reduced motion: the photo stays, the character never fades in. */
@media (prefers-reduced-motion: reduce) {
  .gl-coach-id-toon { animation: none; opacity: 0; }
}
"""


# ── Nav / Footer ───────────────────────────────────────────────

def build_nav() -> str:
    """Site navigation bar. Coaching is the active item — this IS /coaching/."""
    return build_canonical_nav_header(active="coaching") + """
<script>
(function(){
  var toggle=document.querySelector('[data-nav-toggle]');
  var links=document.querySelector('.gl-nav-links');
  if(toggle&&links){toggle.addEventListener('click',function(){var open=links.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false')});}
})();
</script>"""


def build_footer() -> str:
    """Page footer."""
    return """
<footer class="gl-coach-footer">
  <div class="gl-coach-footer-brand">XC Ski Labs</div>
  <div class="gl-coach-footer-links">
    <a href="/">Home</a>
    <a href="/search/">Search</a>
    <a href="/training-plans/">Training Plans</a>
    <a href="/coaching/">Coaching</a>
    <a href="/privacy/">Privacy</a>
    <a href="/terms/">Terms</a>
  </div>
  <div class="gl-coach-footer-copy">&copy; 2026 XC Ski Labs. All rights reserved.</div>
</footer>""".replace("</footer>", get_endure_offer_html() + "</footer>")


# ── Section builders ─────────────────────────────────────────────

def _sec_head(num: str, title: str) -> str:
    return (
        f'<div class="gl-coach-sec-head">'
        f'<span class="gl-coach-sec-num">{num}</span>'
        f'<h2 class="gl-coach-sec-title">{title}</h2>'
        f'</div>'
    )


def build_id_card() -> str:
    photo, pw, ph = _img("photo")
    toon, tw, th = _img("cartoon")
    rows = "\n          ".join(
        f'<div><dt>{label}</dt><dd>{value}</dd></div>' for label, value in ID_ROWS
    )
    return f'''<aside class="gl-coach-id" aria-label="Who I am">
        <div class="gl-coach-id-head"><span>File: Matti Rowe</span><span>XC-01</span></div>
        <figure class="gl-coach-id-photo">
          <img class="gl-coach-id-real" src="{photo}" alt="Me in a felt hat, grinning in the grocery aisle with a frozen pizza." width="{pw}" height="{ph}">
          <img class="gl-coach-id-toon" src="{toon}" alt="" aria-hidden="true" width="{tw}" height="{th}" loading="lazy">
        </figure>
        <p class="gl-coach-id-bio">{ID_BIO}</p>
        <dl class="gl-coach-id-rows">
          {rows}
        </dl>
      </aside>'''


def build_hero() -> str:
    return f'''<section class="gl-coach-hero" id="hero">
    <div class="gl-coach-hero-grid">
      <div>
        <p class="xc-kicker">Coaching</p>
        <h1>{HERO_H1}</h1>
        <p class="gl-coach-tagline">{HERO_SUB}</p>
        <div class="gl-coach-hero-actions">
          <a href="{APPLY_URL}" class="xc-btn xc-btn--inline gl-coach-hero-cta" data-cta="hero_apply">{APPLY_CTA}</a>
          <p class="gl-coach-fine">About 10 minutes. I reply within {REPLY_TIME}.</p>
        </div>
      </div>
      {build_id_card()}
    </div>
  </section>'''


def build_fit() -> str:
    yes = (
        "You have a ski race picked out and time to train for it.",
        "You&rsquo;ll train through summer and fall, while race day is still a long way off.",
        "You&rsquo;ll upload your sessions and tell me how they felt.",
    )
    no = (
        "Race day is a week away.",
        "You need an injury managed. See a physio for that one first.",
        "You won&rsquo;t wear a heart rate monitor or log what you did.",
    )
    li = lambda items, kind, glyph: "\n            ".join(
        f'<li><span class="gl-coach-mark gl-coach-mark--{kind}" aria-hidden="true">{glyph}</span><span>{t}</span></li>'
        for t in items
    )
    return f'''<section class="gl-coach-band" id="fit">
    <div class="gl-coach-inner">
      {_sec_head("01", "Fit check")}
      <p class="gl-coach-sec-sub">Tick the boxes before you fill anything in.</p>
      <div class="gl-coach-lists">
        <div class="gl-coach-list">
          <h3>Coaching fits if</h3>
          <ul>
            {li(yes, "yes", "&#10003;")}
          </ul>
        </div>
        <div class="gl-coach-list gl-coach-list--quiet">
          <h3>Probably not a fit if</h3>
          <ul>
            {li(no, "no", "&#10005;")}
          </ul>
        </div>
      </div>
    </div>
  </section>'''


def build_terms() -> str:
    clauses = (
        ("I read your sessions.",
         "Heart rate, pace and how it felt. I look for the intervals that drifted and the easy distance that crept up into threshold."),
        ("Dryland that counts.",
         "Roller skis, running, bounding and strength from spring until the trails open. Then the snow block goes to skiing."),
        ("Classic, skate or both.",
         "Your plan follows your technique and your races, from a club 10k to the Birkie."),
        ("Plans that follow the snow.",
         "At Mid and Max, a work trip, a head cold or a thaw that turns the trails to mashed potatoes changes the week that week."),
        ("Plain feedback.",
         "If your easy days are too hard, I&rsquo;ll tell you. If you&rsquo;re waxing for a race you haven&rsquo;t trained for, I&rsquo;ll tell you that too."),
    )
    rows = "\n        ".join(
        f'<li><p class="gl-coach-label">{i:02d}</p><h3>{t}</h3><p>{b}</p></li>'
        for i, (t, b) in enumerate(clauses, start=1)
    )
    return f'''<section class="gl-coach-band gl-coach-band--panel" id="terms">
    <div class="gl-coach-inner">
      {_sec_head("02", "What you get")}
      <ol class="gl-coach-get">
        {rows}
      </ol>
    </div>
  </section>'''


WEEK_ROWS = (
    ("Each session", ("off", "Read at the weekly review"), ("on", "Checked as it comes in"), ("on", "Read the day you upload it")),
    ("Each week", ("on", "Weekly review and file analysis"), ("on", "Plan adjustments, detailed file analysis, blindspot detection"), ("on", "Everything in Mid")),
    ("A thaw, a cold, a trip", ("off", "Sorted at the weekly review"), ("on", "Message me; the week changes that week"), ("on", "On-demand calls, priority response")),
    ("Strategy calls", ("on", "Quarterly"), ("on", "Every 4 weeks"), ("on", "Every 4 weeks, plus on demand")),
    ("Race week", ("on", "Race-day nutrition plan"), ("on", "Race-day nutrition plan"), ("on", "Race-week strategy and nutrition plan")),
    ("The season", ("on", "Custom training guide"), ("on", "Custom training guide"), ("on", "Multi-race season planning")),
)


def build_week() -> str:
    cols = []
    for idx, (key, name, _p) in enumerate(TIERS):
        rows = "\n            ".join(
            f'<li><span class="gl-coach-label">{when}</span>'
            f'<span class="{"gl-coach-week-off" if cells[idx][0] == "off" else ""}">{cells[idx][1]}</span></li>'
            for when, *cells in WEEK_ROWS
        )
        cols.append(f'''<div class="gl-coach-list gl-coach-week" data-t="{name.upper()}">
          <h3>{name}</h3>
          <ul>
            {rows}
          </ul>
        </div>''')
    cols_html = "\n        ".join(cols)
    return f'''<section class="gl-coach-band" id="week">
    <div class="gl-coach-inner">
      {_sec_head("03", "A week with me")}
      <p class="gl-coach-sec-sub">Same plan, same race. The levels differ in how often I look and how fast the week moves.</p>
      <div class="gl-coach-lists gl-coach-lists--3">
        {cols_html}
      </div>
      <p class="gl-coach-note">The thaw row is the one that separates the levels.</p>
    </div>
  </section>'''


def build_how_it_works() -> str:
    steps = (
        ("About 10 min", "You apply.", "Questions about your skiing, your races and your week."),
        (REPLY_TIME, "You hear back from me.", "Yes or no, with the reason."),
        ("If it&rsquo;s a fit", "Agreement, then checkout.", "A short agreement and consent, then a link for your first 4 weeks plus the $99 setup fee."),
        ("Setup", "Your first plan.", "I set you up on TrainingPeaks and build your first plan from your intake."),
        ("After that", "Your level&rsquo;s rhythm.", "The week above, every week, at the level you picked."),
    )
    rows = "\n          ".join(
        f'<li><span class="gl-coach-num">{i:02d}</span><span class="gl-coach-label">{when}</span>'
        f'<div><h4>{t}</h4><p>{b}</p></div></li>'
        for i, (when, t, b) in enumerate(steps, start=1)
    )
    return f'''<section class="gl-coach-band gl-coach-band--panel" id="how-it-works">
    <div class="gl-coach-inner">
      {_sec_head("04", "How it works")}
      <div class="gl-coach-list gl-coach-steps">
        <h3>After you click apply</h3>
        <ol>
          {rows}
        </ol>
      </div>
    </div>
  </section>'''


def build_fit_check() -> str:
    """Three-question picker. Rendered `hidden`; build_page_js() shows it,
    so without JS the crates stand alone."""
    sets = []
    for qi, (text, options) in enumerate(PICKER_QUESTIONS, start=1):
        labels = "\n          ".join(
            f'<label><input type="radio" name="gl-coach-q{qi}" value="{ai}"><span>{opt}</span></label>'
            for ai, opt in enumerate(options, start=1)
        )
        sets.append(f'''<fieldset><legend>Q{qi}</legend><p>{text}</p>
          {labels}</fieldset>''')
    fieldsets = "\n        ".join(sets)
    return f'''<form class="gl-coach-picker" id="gl-coach-picker" aria-label="Three questions to pick a level" hidden>
        {fieldsets}
      </form>
      <p class="gl-coach-picker-out" id="gl-coach-picker-out" aria-live="polite" hidden>{PICKER_EMPTY}</p>'''


def build_tiers() -> str:
    crates = []
    for key, name, price in TIERS:
        feats = "".join(f"<li>{f}</li>" for f in TIER_FEATURES[key])
        crates.append(f'''<li class="xc-crate gl-coach-tier" data-tier="{key}">
          <span class="xc-ribbon">Recommended</span>
          <div class="xc-crate__in">
            <h3>{name}</h3>
            <p class="xc-price">{price}</p>
            <p class="gl-coach-per">{TIER_INTERVAL}</p>
            <p class="xc-crate__d">{TIER_BLURBS[key]}</p>
            <ul>{feats}</ul>
            <a href="{APPLY_URL}?tier={key}" class="xc-btn gl-coach-tier-cta" data-cta="tier_{key}">Apply for {name}</a>
          </div>
        </li>''')
    crates_html = "\n        ".join(crates)
    return f'''<section class="gl-coach-band" id="tiers">
    <div class="gl-coach-inner">
      {_sec_head("05", "Levels and prices")}
      <p class="gl-coach-sec-sub">Every level is billed every 4 weeks and includes TrainingPeaks Premium. {PICKER_INTRO}</p>
      {build_fit_check()}
      <ul class="gl-coach-crates" id="gl-coach-crates">
        {crates_html}
      </ul>
      <ul class="xc-tags gl-coach-tags">
        <li class="xc-ship"><h3>Setup</h3><p>A one-time $99 setup fee with your first 4 weeks covers intake analysis, a look through your training history and your first plan build. Any waiver is offered privately, case by case.</p></li>
        <li class="xc-ship"><h3>Cancelling</h3><p>Coaching renews every 4 weeks. Cancel before the next renewal and you keep coaching through the weeks you&rsquo;ve paid for. No cancellation fee.</p></li>
        <li class="xc-ship"><h3>Fit</h3><p>Coaching won&rsquo;t fix skipped sessions or feedback you ignore. If it isn&rsquo;t a fit for you, I&rsquo;ll say so within {REPLY_TIME}.</p></li>
      </ul>
    </div>
  </section>'''


FAQS = (
    ("What happens after I apply?",
     f"You hear back from me within {REPLY_TIME}, yes or no, with the reason."),
    ("Can I ask you something before I apply?",
     f'Yes. Write to <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> with anything you want to ask before applying.'),
    ("How often will I hear from you?",
     "At least once a week, more in the last weeks before your race. Mid and Max can message me any time."),
    ("What data do I need?",
     "A watch with heart rate is plenty. Every session has effort targets you can ski by feel."),
    ("I live where snow is short. Can you still coach me?",
     "Yes. Most of the year is dryland anyway, and I plan the snow weeks around when you can get on snow."),
    ("What if I miss sessions?",
     "Let me know. At Mid and Max I shift the week right away, and at Min it gets sorted in the weekly review. Either way, a missed interval session doesn&rsquo;t get made up on tired legs."),
    ("How will I know it&rsquo;s working?",
     "We set baselines at intake and check against them as the season goes."),
    ("What&rsquo;s the $99 setup fee?",
     "It covers intake analysis, a look through your training history and your first plan build. It&rsquo;s charged once, with your first 4 weeks."),
    ("Can I cancel anytime?",
     "Yes. No contracts and no cancellation fee. Your coaching runs through the end of the 4-week cycle you&rsquo;ve paid for."),
)


def build_faq() -> str:
    items = "\n        ".join(
        f'<details class="gl-coach-faq-item"><summary><span class="gl-coach-label">Q{i:02d}</span>'
        f'<span class="gl-coach-faq-q">{q}</span></summary><p>{a}</p></details>'
        for i, (q, a) in enumerate(FAQS, start=1)
    )
    return f'''<section class="gl-coach-band gl-coach-band--panel" id="faq">
    <div class="gl-coach-inner">
      {_sec_head("06", "Questions")}
      <div class="gl-coach-faq-list">
        {items}
      </div>
    </div>
  </section>'''


def build_close() -> str:
    return f'''<section class="gl-coach-band gl-coach-close" id="final-cta">
    <div class="gl-coach-inner">
      <p class="xc-kicker">07 Application</p>
      <h2>Start your file</h2>
      <p class="gl-coach-close-hook">Ten minutes on your skiing, your races and your week. You hear back within {REPLY_TIME}.</p>
      <a href="{APPLY_URL}" class="xc-btn gl-coach-final-cta" data-cta="final_fill_intake">{APPLY_CTA}</a>
      <p class="gl-coach-fine gl-coach-close-contact">Write to <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> with anything you want to ask before you apply.</p>
    </div>
  </section>'''


def build_mobile_sticky_cta() -> str:
    return f'''<div class="gl-coach-sticky-cta">
    <a href="{APPLY_URL}" data-cta="sticky_cta">{APPLY_CTA}</a>
  </div>'''


def build_cookie_consent() -> str:
    """Shared consent banner and Privacy choices strip (scripts/consent.py)."""
    return get_consent_banner_html()


def build_page_js() -> str:
    """Picker, FAQ open events and cta_click events with Gravel God's
    coaching-page cta_name values (data-cta): hero_apply, tier_min /
    tier_mid / tier_max, final_fill_intake, sticky_cta."""
    labels = {key: f"I&rsquo;d pick {name}: {price} every 4 weeks." for key, name, price in TIERS}
    labels = {k: html.unescape(v) for k, v in labels.items()}
    labels_js = _safe_json_for_script(labels, separators=(",", ":"))
    return """
<script>
(function() {
  document.querySelectorAll('[data-cta]').forEach(function(el) {
    el.addEventListener('click', function() {
      if (typeof gtag === 'function') gtag('event', 'cta_click', { source: 'coaching', cta_name: el.getAttribute('data-cta') });
    });
  });
  document.querySelectorAll('.gl-coach-faq-item').forEach(function(d) {
    d.addEventListener('toggle', function() {
      if (d.open && typeof gtag === 'function') gtag('event', 'coaching_faq_open', { question: d.querySelector('.gl-coach-faq-q').textContent.trim().slice(0, 60) });
    });
  });

  /* Picker: the rounded mean of three answers (1-3) marks one crate. The
     marked crate becomes the page's one salmon object, labelled
     Recommended. Rendered hidden; shown here, so no JS = crates only. */
  var form = document.getElementById('gl-coach-picker');
  var out = document.getElementById('gl-coach-picker-out');
  var crates = document.querySelectorAll('.gl-coach-tier[data-tier]');
  if (!form || !out) return;
  var names = { 1: 'min', 2: 'mid', 3: 'max' };
  var labels = """ + labels_js + """;
  var current = null;
  form.addEventListener('change', function(e) {
    if (e.target && e.target.name && typeof gtag === 'function') gtag('event', 'coaching_fitcheck_answer', { question: e.target.name.slice(-1), answer: e.target.value });
    var v = [1, 2, 3].map(function(q) { var c = form.querySelector('input[name=gl-coach-q' + q + ']:checked'); return c ? +c.value : 0; });
    if (v.indexOf(0) !== -1) return;
    var tier = names[Math.round((v[0] + v[1] + v[2]) / 3)];
    out.textContent = labels[tier];
    crates.forEach(function(c) { c.classList.toggle('xc-crate--splash', c.getAttribute('data-tier') === tier); });
    if (tier !== current && typeof gtag === 'function') gtag('event', 'coaching_fitcheck_result', { tier: tier });
    current = tier;
  });
  form.hidden = false;
  out.hidden = false;
})();
</script>"""


def build_jsonld() -> str:
    """WebPage + Service JSON-LD, serialized via the safe-json helper."""
    webpage = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Coaching | XC Ski Labs",
        "description": "Ski coaching for people who'll roller ski in July to pass people in February. I plan dryland and snow around your races and read the sessions you upload.",
        "url": f"{SITE_BASE_URL}/coaching/",
        "isPartOf": {
            "@type": "WebSite",
            "name": "XC Ski Labs",
            "url": SITE_BASE_URL,
        },
    }
    service = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": "XC Ski Coaching",
        "provider": {
            "@type": "Organization",
            "name": "XC Ski Labs",
            "url": SITE_BASE_URL,
        },
        "description": "Cross-country ski coaching in three levels, from a weekly review to every session read the day you upload it. From $199 every 4 weeks.",
    }
    wp_tag = f'<script type="application/ld+json">{_safe_json_for_script(webpage, separators=(",", ":"))}</script>'
    svc_tag = f'<script type="application/ld+json">{_safe_json_for_script(service, separators=(",", ":"))}</script>'
    return f'{wp_tag}\n  {svc_tag}'


# ── Page assembly ─────────────────────────────────────────────

def write_coaching_images(output_dir: Path) -> Path:
    """Copy the page's images to <output>/coaching/img/. Raises if one is
    missing: the page never ships with a stand-in picture."""
    dest = output_dir / "coaching" / "img"
    dest.mkdir(parents=True, exist_ok=True)
    for name, _w, _h in IMAGES.values():
        src = IMG_SRC_DIR / name
        if not src.is_file():
            raise FileNotFoundError(f"coaching image missing: {src}")
        shutil.copy2(src, dest / name)
    return dest


def generate_page(output_dir: Path = None) -> Path:
    """Generate the coaching landing page and copy its images."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "coaching" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_coaching_images(output_dir)

    canonical_url = f"{SITE_BASE_URL}/coaching/"
    title = "1:1 XC Ski Coaching | XC Ski Labs"
    description = (
        "Cross-country ski coaching from me, from roller-ski season to race "
        "day. Three levels, from a weekly review to every session read the "
        "day you upload it. From $199 every 4 weeks."
    )

    sections = "\n\n  ".join((
        build_hero(),
        build_fit(),
        build_terms(),
        build_week(),
        build_how_it_works(),
        build_tiers(),
        build_faq(),
        build_close(),
    ))
    nav = build_nav()
    sticky = build_mobile_sticky_cta()
    footer = build_footer()
    consent = build_cookie_consent()
    page_js = build_page_js()
    jsonld = build_jsonld()
    css = build_css()
    photo_src = _img("photo")[0]

    og_tags = f'''<meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{esc(canonical_url)}">
  <meta property="og:site_name" content="XC Ski Labs">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">'''

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{esc(canonical_url)}">
  <link rel="preload" as="image" href="{photo_src}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Stencil+Display:wght@700;900&family=Big+Shoulders+Text:wght@600;800&family=Libre+Franklin:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  {og_tags}
  {jsonld}
  <style>{css}</style>
  {XL_GA4_HEAD}
</head>
<body>

{nav}

<div class="gl-coach-page">

  {sections}

</div>

{footer}

{sticky}

{consent}

{page_js}

</body>
</html>"""

    out_path.write_text(page_html, encoding="utf-8")
    return out_path


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate XC Ski Labs coaching landing page")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Output directory (default: project output/)")
    args = parser.parse_args()

    out = generate_page(output_dir=args.output_dir)
    print(f"Generated: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")
