#!/usr/bin/env python3
"""
XC Ski Labs — Race Page Generator

Generates self-contained HTML race pages from JSON profiles.
Neo-brutalist design system with wintry XC Ski Labs palette.

Usage:
    python generate_race_pages.py              # all races
    python generate_race_pages.py --slug vasaloppet   # single race
    python generate_race_pages.py --data-dir ../race-data --output-dir ../output
"""

import argparse
import html
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_DATA_DIR = SCRIPT_DIR.parent / "race-data"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR.parent / "output"

# ── Rating Criteria ────────────────────────────────────────────

RATING_CRITERIA = [
    ("distance", "Distance"),
    ("elevation", "Elevation"),
    ("altitude", "Altitude"),
    ("field_size", "Field Size"),
    ("prestige", "Prestige"),
    ("international_draw", "Int'l Draw"),
    ("course_technicality", "Technicality"),
    ("snow_reliability", "Snow Reliability"),
    ("grooming_quality", "Grooming"),
    ("accessibility", "Accessibility"),
    ("community", "Community"),
    ("scenery", "Scenery"),
    ("organization", "Organization"),
    ("competitive_depth", "Comp. Depth"),
]

# ── Series Labels ──────────────────────────────────────────────

SERIES_LABELS = {
    "worldloppet": "Worldloppet",
    "ski_classics_pro_tour": "Ski Classics Pro Tour",
    "ski_classics_grand_classic": "Ski Classics Grand Classic",
    "euroloppet": "Euroloppet",
    "china_loppet": "China Loppet",
    "australia_loppet": "Australia Loppet",
}

# ── Discipline Labels ──────────────────────────────────────────

DISCIPLINE_LABELS = {
    "classic": "Classic",
    "skate": "Skate",
    "both": "Classic & Skate",
}


# ── Helpers ────────────────────────────────────────────────────

def esc(text: Any) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


def _safe_json_for_script(obj, **kwargs) -> str:
    """Serialize obj to JSON safe for embedding inside <script> tags.

    json.dumps does NOT escape '</' sequences, so a string containing
    '</script>' would prematurely close the <script> element.
    We replace '</' with '<\\/' which is valid JSON and safe in HTML.
    """
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


def format_distance(km: Any) -> str:
    """Format distance with km suffix."""
    if km is None:
        return "—"
    return f"{km} km"


def format_elevation(m: Any) -> str:
    """Format elevation with m suffix."""
    if m is None:
        return "—"
    return f"{m} m"


def format_altitude(m: Any) -> str:
    """Format altitude with m suffix."""
    if m is None:
        return "—"
    return f"{m} m"


def tier_class(tier: int) -> str:
    """Return CSS class for tier."""
    return f"t{tier}" if tier in (1, 2, 3, 4) else "t4"


def tier_label(tier: int) -> str:
    """Return display label for tier."""
    labels = {1: "TIER 1", 2: "TIER 2", 3: "TIER 3", 4: "TIER 4"}
    return labels.get(tier, "TIER 4")


# ── CSS ────────────────────────────────────────────────────────

def build_css() -> str:
    """Build the complete CSS for race pages."""
    return """
:root {
  /* Primary */
  --gl-nordic-night: #1a2332;
  --gl-fjord-blue: #2b4c7e;
  --gl-deep-powder: #354f6e;
  --gl-slate-steel: #4a5568;

  /* Accents */
  --gl-aurora-green: #1b7260;
  --gl-aurora-violet: #7b5ea7;
  --gl-wax-orange: #b34a1a;
  --gl-glacier-teal: #357a88;

  /* Neutrals & Backgrounds */
  --gl-birch-bark: #d4cdc4;
  --gl-silver-mist: #9ca8b8;
  --gl-frost-white: #e8edf2;
  --gl-ice-paper: #f0f3f7;

  /* Tier Colors */
  --gl-tier-1: #1a2332;
  --gl-tier-2: #2b4c7e;
  --gl-tier-3: #4a5568;
  --gl-tier-4: #5a6d7e;

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

.gl-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px;
  padding-bottom: 80px;
}

/* ── [01] Hero ───────────────────────────────────── */

.gl-hero {
  background: var(--gl-nordic-night);
  color: var(--gl-ice-paper);
  padding: 48px 32px 40px;
  border-bottom: var(--gl-border-heavy) solid var(--gl-fjord-blue);
}

.gl-hero-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  flex-wrap: wrap;
}

.gl-hero-name {
  font-family: var(--gl-font-editorial);
  font-size: 2.2rem;
  font-weight: 700;
  line-height: 1.15;
  margin: 0;
}

.gl-hero-tier {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 4px 12px;
  border: var(--gl-border-width) solid var(--gl-frost-white);
  white-space: nowrap;
  letter-spacing: 0.08em;
}

.gl-hero-tier.t1 { background: var(--gl-tier-1); border-color: var(--gl-frost-white); }
.gl-hero-tier.t2 { background: var(--gl-tier-2); border-color: var(--gl-frost-white); }
.gl-hero-tier.t3 { background: var(--gl-tier-3); border-color: var(--gl-frost-white); }
.gl-hero-tier.t4 { background: var(--gl-tier-4); border-color: var(--gl-frost-white); }

.gl-hero-tagline {
  font-family: var(--gl-font-editorial);
  font-size: 1.05rem;
  font-style: italic;
  color: var(--gl-silver-mist);
  margin: 16px 0 0;
  line-height: 1.5;
}

.gl-hero-score {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-frost-white);
  margin-top: 20px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.gl-hero-score-number {
  font-size: 2rem;
  font-weight: 700;
  line-height: 1;
}

.gl-hero-vitals {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--gl-deep-powder);
}

.gl-hero-vital {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
}

.gl-hero-vital-label {
  color: var(--gl-silver-mist);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  display: block;
  margin-bottom: 2px;
}

.gl-hero-vital-value {
  color: var(--gl-frost-white);
  font-weight: 700;
  font-size: 0.85rem;
}

/* ── Section Base ────────────────────────────────── */

.gl-section {
  padding: 36px 0;
  border-bottom: 1px solid var(--gl-birch-bark);
}

.gl-section:last-child {
  border-bottom: none;
}

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
  font-size: 1.4rem;
  font-weight: 700;
  color: var(--gl-nordic-night);
  margin: 0 0 20px;
  line-height: 1.25;
}

.gl-section-prose {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  color: var(--gl-nordic-night);
  line-height: 1.7;
  margin-bottom: 16px;
}

/* ── [02] At a Glance ────────────────────────────── */

.gl-vitals-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0;
  border: var(--gl-border-width) solid var(--gl-border-color);
}

.gl-vital-cell {
  padding: 14px 16px;
  border-bottom: 1px solid var(--gl-birch-bark);
  border-right: 1px solid var(--gl-birch-bark);
  background: var(--gl-frost-white);
}

.gl-vital-label {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-slate-steel);
  margin-bottom: 4px;
}

.gl-vital-value {
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--gl-nordic-night);
}

/* ── [03] Course ─────────────────────────────────── */

.gl-course-meta {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.gl-course-meta-item {
  padding: 12px 16px;
  background: var(--gl-frost-white);
  border: var(--gl-border-width) solid var(--gl-border-color);
}

.gl-course-meta-label {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-slate-steel);
}

.gl-course-meta-value {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-nordic-night);
  margin-top: 2px;
}

.gl-feature-list {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
}

.gl-feature-list li {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-nordic-night);
  padding: 8px 0 8px 20px;
  position: relative;
  border-bottom: 1px solid var(--gl-frost-white);
}

.gl-feature-list li::before {
  content: "\\2014";
  position: absolute;
  left: 0;
  color: var(--gl-fjord-blue);
  font-weight: 700;
}

/* ── [04] Climate ────────────────────────────────── */

.gl-climate-temp {
  display: inline-block;
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  padding: 6px 14px;
  background: var(--gl-frost-white);
  border: var(--gl-border-width) solid var(--gl-border-color);
  color: var(--gl-fjord-blue);
  margin-bottom: 16px;
}

.gl-challenge-list {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
}

.gl-challenge-list li {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-nordic-night);
  padding: 8px 0 8px 24px;
  position: relative;
  border-bottom: 1px solid var(--gl-frost-white);
}

.gl-challenge-list li::before {
  content: "\\2744";
  position: absolute;
  left: 0;
  color: var(--gl-glacier-teal);
  font-size: 0.85rem;
}

/* ── [05] Rating Breakdown ───────────────────────── */

.gl-rating-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gl-rating-row {
  display: grid;
  grid-template-columns: 130px 1fr 36px;
  align-items: center;
  gap: 10px;
}

.gl-rating-label {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--gl-slate-steel);
  text-align: right;
}

.gl-rating-track {
  height: 20px;
  background: var(--gl-frost-white);
  border: 1px solid var(--gl-birch-bark);
  position: relative;
}

.gl-rating-fill {
  height: 100%;
  background: var(--gl-fjord-blue);
  transition: width 0.3s ease;
}

.gl-rating-fill.score-5 { background: var(--gl-nordic-night); }
.gl-rating-fill.score-4 { background: var(--gl-fjord-blue); }
.gl-rating-fill.score-3 { background: var(--gl-deep-powder); }
.gl-rating-fill.score-2 { background: var(--gl-slate-steel); }
.gl-rating-fill.score-1 { background: var(--gl-silver-mist); }

.gl-rating-value {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-nordic-night);
  text-align: center;
}

.gl-score-note {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  font-style: italic;
  color: var(--gl-slate-steel);
  margin-top: 20px;
  padding: 16px;
  background: var(--gl-frost-white);
  border-left: none;
  box-shadow: inset 3px 0 0 var(--gl-fjord-blue) !important;
}

/* ── [06] History ────────────────────────────────── */

.gl-facts-list {
  list-style: none;
  padding: 0;
  margin: 16px 0 0;
}

.gl-facts-list li {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-nordic-night);
  padding: 10px 0 10px 20px;
  position: relative;
  border-bottom: 1px solid var(--gl-frost-white);
  line-height: 1.5;
}

.gl-facts-list li::before {
  content: "\\25A0";
  position: absolute;
  left: 0;
  color: var(--gl-wax-orange);
  font-size: 0.6rem;
  top: 14px;
}

/* ── [07] Series Membership ──────────────────────── */

.gl-series-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.gl-series-badge {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 8px 16px;
  border: var(--gl-border-width) solid var(--gl-border-color);
  background: var(--gl-frost-white);
  color: var(--gl-nordic-night);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.gl-series-badge.worldloppet {
  border-color: var(--gl-aurora-green);
  color: var(--gl-aurora-green);
}

.gl-series-badge.ski-classics {
  border-color: var(--gl-aurora-violet);
  color: var(--gl-aurora-violet);
}

.gl-series-badge.euroloppet {
  border-color: var(--gl-fjord-blue);
  color: var(--gl-fjord-blue);
}

/* ── [08] YouTube Placeholder ────────────────────── */

.gl-placeholder {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  color: var(--gl-silver-mist);
  padding: 24px;
  text-align: center;
  background: var(--gl-frost-white);
  border: var(--gl-border-width) solid var(--gl-birch-bark);
}

/* ── Footer ──────────────────────────────────────── */

.gl-footer {
  padding: 32px 0;
  text-align: center;
  border-top: var(--gl-border-heavy) solid var(--gl-border-color);
  margin-top: 24px;
}

.gl-footer-back {
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--gl-fjord-blue);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.gl-footer-back:hover {
  color: var(--gl-nordic-night);
}

.gl-footer-brand {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-silver-mist);
  margin-top: 12px;
  letter-spacing: 0.04em;
}

/* ── Discipline Badge ────────────────────────────── */

.gl-discipline {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  font-weight: 700;
  padding: 2px 8px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  border: var(--gl-border-width) solid var(--gl-border-color);
  display: inline-block;
}

.gl-discipline.classic { background: var(--gl-nordic-night); color: var(--gl-ice-paper); }
.gl-discipline.skate { background: var(--gl-fjord-blue); color: var(--gl-ice-paper); }
.gl-discipline.both { background: var(--gl-glacier-teal); color: var(--gl-ice-paper); }

/* ── Skip Link (a11y) ────────────────────────────── */

.gl-skip-link {
  position: absolute;
  left: -9999px;
  top: 0;
  background: var(--gl-wax-orange);
  color: var(--gl-ice-paper);
  padding: 8px 16px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  z-index: 9999;
  text-decoration: none;
}

.gl-skip-link:focus {
  left: 0;
}

/* ── Responsive ──────────────────────────────────── */

@media (max-width: 640px) {
  .gl-hero { padding: 32px 20px 28px; }
  .gl-hero-name { font-size: 1.6rem; }
  .gl-hero-vitals { flex-direction: column; gap: 12px; }
  .gl-vitals-grid { grid-template-columns: 1fr 1fr; }
  .gl-course-meta { grid-template-columns: 1fr; }
  .gl-rating-row { grid-template-columns: 90px 1fr 30px; }
  .gl-rating-label { font-size: 0.6rem; }
  .gl-section-title { font-size: 1.2rem; }
}

@media (max-width: 400px) {
  .gl-vitals-grid { grid-template-columns: 1fr; }
  .gl-hero-top { flex-direction: column; }
}

/* ── [09] Training ─────────────────────────────────── */

.gl-training-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin: 24px 0;
}
.gl-training-card {
  border: var(--gl-border-width) solid var(--gl-border-color);
  padding: 20px;
  background: white;
}
.gl-training-card-title {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gl-aurora-green);
  margin: 0 0 8px;
}
.gl-training-card-desc {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-slate-steel);
  margin: 0;
  line-height: 1.5;
}
.gl-training-cta {
  display: inline-block;
  font-family: var(--gl-font-data);
  background: var(--gl-aurora-green);
  color: var(--gl-frost-white);
  padding: 14px 28px;
  border: var(--gl-border-width) solid var(--gl-border-color);
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-top: 20px;
}
.gl-training-cta:hover {
  background: var(--gl-glacier-teal);
}
@media (max-width: 640px) {
  .gl-training-grid { grid-template-columns: 1fr; }
}

/* ── Sticky CTA Bar ────────────────────────────────── */

.gl-sticky-cta {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 200;
  background: var(--gl-nordic-night);
  border-top: var(--gl-border-heavy) solid var(--gl-aurora-green);
  transform: translateY(100%);
  transition: transform 0.3s ease;
  padding: 12px 20px;
}
.gl-sticky-cta.visible {
  transform: translateY(0);
}
.gl-sticky-cta-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.gl-sticky-cta-name {
  font-family: var(--gl-font-editorial);
  color: var(--gl-frost-white);
  font-weight: 700;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}
.gl-sticky-cta-btn {
  font-family: var(--gl-font-data);
  background: var(--gl-aurora-green);
  color: var(--gl-frost-white);
  padding: 10px 20px;
  border: var(--gl-border-width) solid var(--gl-frost-white);
  text-decoration: none;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  white-space: nowrap;
}
.gl-sticky-cta-btn:hover {
  background: var(--gl-glacier-teal);
}
.gl-sticky-cta-dismiss {
  background: none;
  border: none;
  color: var(--gl-silver-mist);
  font-size: 1.4rem;
  cursor: pointer;
  padding: 12px 16px;
  line-height: 1;
  min-width: 44px;
  min-height: 44px;
}
@media (max-width: 640px) {
  .gl-sticky-cta-name { display: none; }
  .gl-sticky-cta-inner { justify-content: center; }
}

/* ── Focus Visible (a11y) ────────────────────────── */

a:focus-visible, button:focus-visible {
  outline: 3px solid var(--gl-wax-orange);
  outline-offset: 2px;
}

/* ── Nav Header ──────────────────────────────────── */

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
.gl-nav-logo:hover {
  color: var(--gl-birch-bark);
}
.gl-nav-links {
  display: flex;
  align-items: center;
  gap: 24px;
  list-style: none;
  margin: 0;
  padding: 0;
}
.gl-nav-links a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--gl-silver-mist);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
}
.gl-nav-links a:hover {
  color: var(--gl-frost-white);
}
.gl-nav-links a.active {
  color: var(--gl-frost-white);
  border-bottom-color: var(--gl-wax-orange);
}
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
@media (max-width: 640px) {
  .gl-nav-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    background: var(--gl-nordic-night);
    flex-direction: column;
    padding: 16px 20px;
    gap: 12px;
    border-bottom: var(--gl-border-heavy) solid var(--gl-fjord-blue);
  }
  .gl-nav-links.open {
    display: flex;
  }
  .gl-nav-hamburger {
    display: block;
  }
}

/* ── Cookie Consent ──────────────────────────────── */

.gl-cookie-consent {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-nordic-night);
  border-top: 3px solid var(--gl-wax-orange);
  padding: 20px;
  display: none;
}
.gl-cookie-consent.visible {
  display: block;
}
.gl-cookie-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.gl-cookie-text {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  color: var(--gl-frost-white);
  flex: 1;
  min-width: 200px;
}
.gl-cookie-buttons {
  display: flex;
  gap: 10px;
}
.gl-cookie-btn {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 10px 20px;
  border: var(--gl-border-width) solid var(--gl-frost-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 44px;
  min-height: 44px;
}
.gl-cookie-btn.accept {
  background: var(--gl-aurora-green);
  color: var(--gl-frost-white);
}
.gl-cookie-btn.decline {
  background: transparent;
  color: var(--gl-frost-white);
}
"""


# ── HTML Builders ──────────────────────────────────────────────

def build_ga4_snippet() -> str:
    """GA4 tracking snippet with cookie consent gating."""
    return """<script async src="https://www.googletagmanager.com/gtag/js?id=G-3JQLSQLPPM"></script>
<script>
window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments)}
(function(){var c=(document.cookie.match(/xl_consent=([^;]+)/)||[])[1];
if(c==='declined')return;gtag('js',new Date());gtag('config','G-3JQLSQLPPM')})();
</script>"""


def build_cookie_consent() -> str:
    """Cookie consent banner with accept/decline buttons."""
    return """
<div class="gl-cookie-consent" id="gl-cookie-consent">
  <div class="gl-cookie-inner">
    <p class="gl-cookie-text">We use cookies for analytics to improve your experience. You can accept or decline.</p>
    <div class="gl-cookie-buttons">
      <button class="gl-cookie-btn accept" id="gl-cookie-accept">Accept</button>
      <button class="gl-cookie-btn decline" id="gl-cookie-decline">Decline</button>
    </div>
  </div>
</div>
<script>
(function(){
  var banner=document.getElementById('gl-cookie-consent');
  if(!banner)return;
  if(document.cookie.match(/xl_consent=/)){return;}
  banner.classList.add('visible');
  document.getElementById('gl-cookie-accept').addEventListener('click',function(){
    document.cookie='xl_consent=accepted;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'granted'});gtag('js',new Date());gtag('config','G-3JQLSQLPPM');}
  });
  document.getElementById('gl-cookie-decline').addEventListener('click',function(){
    document.cookie='xl_consent=declined;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'denied'});}
  });
})();
</script>
"""


def build_nav_header(active: str = "") -> str:
    """Sticky top nav bar with logo and links."""
    def _active(page: str) -> str:
        return ' class="active"' if active == page else ""

    return f"""
<nav class="gl-nav">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo">XC SKI LABS</a>
    <button class="gl-nav-hamburger" aria-label="Toggle navigation" onclick="document.querySelector('.gl-nav-links').classList.toggle('open')">&#9776;</button>
    <ul class="gl-nav-links">
      <li><a href="/search/"{_active("races")}>Races</a></li>
      <li><a href="/training-plans/"{_active("training")}>Training Plans</a></li>
      <li><a href="/coaching/apply/"{_active("coaching")}>Coaching</a></li>
    </ul>
  </div>
</nav>
"""


def build_hero(race: dict) -> str:
    """[01] Hero section."""
    v = race["vitals"]
    r = race["nordic_lab_rating"]
    tier = r["tier"]
    score = r["overall_score"]
    discipline = r.get("discipline", v.get("discipline", "classic"))

    discipline_badge = (
        f'<span class="gl-discipline {esc(discipline)}">'
        f'{esc(DISCIPLINE_LABELS.get(discipline, discipline))}</span>'
    )

    vitals_items = []
    if v.get("distance_km"):
        vitals_items.append(("Distance", format_distance(v["distance_km"])))
    if v.get("elevation_m"):
        vitals_items.append(("Elevation", format_elevation(v["elevation_m"])))
    if discipline:
        vitals_items.append(("Technique", DISCIPLINE_LABELS.get(discipline, discipline)))
    if v.get("date"):
        vitals_items.append(("Date", v["date"]))

    vitals_html = ""
    for label, value in vitals_items:
        vitals_html += (
            f'<div class="gl-hero-vital">'
            f'<span class="gl-hero-vital-label">{esc(label)}</span>'
            f'<span class="gl-hero-vital-value">{esc(value)}</span>'
            f'</div>'
        )

    return f"""
<section class="gl-hero">
  <div class="gl-hero-top">
    <div>
      <h1 class="gl-hero-name">{esc(race.get("display_name", race["name"]))}</h1>
      {discipline_badge}
    </div>
    <span class="gl-hero-tier {tier_class(tier)}">{esc(tier_label(tier))}</span>
  </div>
  <p class="gl-hero-tagline">{esc(race.get("tagline", ""))}</p>
  <div class="gl-hero-score">
    <span class="gl-hero-score-number">{score}</span>
    <span>/ 100</span>
  </div>
  <div class="gl-hero-vitals">
    {vitals_html}
  </div>
</section>
"""


def build_at_a_glance(race: dict) -> str:
    """[02] At a Glance vitals grid."""
    v = race["vitals"]
    r = race["nordic_lab_rating"]
    discipline = r.get("discipline", v.get("discipline", ""))

    cells = [
        ("Distance", format_distance(v.get("distance_km"))),
        ("Elevation", format_elevation(v.get("elevation_m"))),
        ("Altitude", format_altitude(v.get("altitude_m"))),
        ("Field Size", v.get("field_size", "—")),
        ("Founded", str(v.get("founded", "—")) if v.get("founded") else "—"),
        ("Technique", DISCIPLINE_LABELS.get(discipline, discipline or "—")),
        ("Format", (race.get("course", {}).get("format", "—") or "—").replace("-", " ").title()),
        ("Date", v.get("date", "—")),
    ]

    # Add distance options if present
    dist_opts = v.get("distance_options", [])
    if dist_opts:
        cells.append(("Distances", " | ".join(dist_opts)))

    # Add location
    loc_badge = v.get("location_badge", v.get("location", ""))
    if loc_badge:
        cells.append(("Location", loc_badge))

    cells_html = ""
    for label, value in cells:
        cells_html += (
            f'<div class="gl-vital-cell">'
            f'<div class="gl-vital-label">{esc(label)}</div>'
            f'<div class="gl-vital-value">{esc(value)}</div>'
            f'</div>'
        )

    return f"""
<section class="gl-section" id="vitals">
  <div class="gl-section-label">02 — At a Glance</div>
  <h2 class="gl-section-title">Race Vitals</h2>
  <div class="gl-vitals-grid">
    {cells_html}
  </div>
</section>
"""


def build_course(race: dict) -> str:
    """[03] Course section."""
    course = race.get("course", {})
    if not course:
        return ""

    primary = course.get("primary", "")
    fmt = (course.get("format") or "").replace("-", " ").title()
    surface = course.get("surface", "")
    tech = _parse_score(course.get("technical_rating"))
    grooming = course.get("grooming", "")
    features = course.get("features", [])

    meta_items = []
    if fmt:
        meta_items.append(("Format", fmt))
    if surface:
        meta_items.append(("Surface", surface))
    if tech is not None:
        meta_items.append(("Technical Rating", f"{tech} / 5"))
    if grooming:
        meta_items.append(("Grooming", grooming))

    meta_html = ""
    for label, value in meta_items:
        meta_html += (
            f'<div class="gl-course-meta-item">'
            f'<div class="gl-course-meta-label">{esc(label)}</div>'
            f'<div class="gl-course-meta-value">{esc(value)}</div>'
            f'</div>'
        )

    features_html = ""
    if features:
        items = "".join(f"<li>{esc(f)}</li>" for f in features)
        features_html = f'<ul class="gl-feature-list">{items}</ul>'

    return f"""
<section class="gl-section" id="course">
  <div class="gl-section-label">03 — Course</div>
  <h2 class="gl-section-title">The Course</h2>
  <div class="gl-course-meta">{meta_html}</div>
  <p class="gl-section-prose">{esc(primary)}</p>
  {features_html}
</section>
"""


def build_climate(race: dict) -> str:
    """[04] Climate section."""
    climate = race.get("climate", {})
    if not climate:
        return ""

    desc = climate.get("description", "")
    temp = climate.get("typical_temp_c", "")
    challenges = climate.get("challenges", [])

    temp_html = ""
    if temp:
        temp_html = f'<div class="gl-climate-temp">Typical: {esc(temp)}</div>'

    challenges_html = ""
    if challenges:
        items = "".join(f"<li>{esc(c)}</li>" for c in challenges)
        challenges_html = f'<ul class="gl-challenge-list">{items}</ul>'

    return f"""
<section class="gl-section" id="climate">
  <div class="gl-section-label">04 — Climate</div>
  <h2 class="gl-section-title">Weather &amp; Conditions</h2>
  {temp_html}
  <p class="gl-section-prose">{esc(desc)}</p>
  {challenges_html}
</section>
"""


def build_rating_breakdown(race: dict) -> str:
    """[05] Rating Breakdown with horizontal bars."""
    r = race["nordic_lab_rating"]

    rows_html = ""
    for key, label in RATING_CRITERIA:
        score = _parse_score(r.get(key))
        if score is None:
            continue
        pct = (score / 5) * 100
        score_class = f"score-{score}" if 1 <= score <= 5 else "score-3"
        rows_html += (
            f'<div class="gl-rating-row">'
            f'<div class="gl-rating-label">{esc(label)}</div>'
            f'<div class="gl-rating-track">'
            f'<div class="gl-rating-fill {score_class}" style="width:{pct}%"></div>'
            f'</div>'
            f'<div class="gl-rating-value">{score}</div>'
            f'</div>'
        )

    # Score note
    note_html = ""
    score_note = r.get("score_note", "")
    if score_note:
        note_html = f'<div class="gl-score-note">{esc(score_note)}</div>'

    return f"""
<section class="gl-section" id="rating">
  <div class="gl-section-label">05 — Rating Breakdown</div>
  <h2 class="gl-section-title">14-Criteria Analysis</h2>
  <div class="gl-rating-bars">
    {rows_html}
  </div>
  {note_html}
</section>
"""


def build_history(race: dict) -> str:
    """[06] History section."""
    history = race.get("history", {})
    if not history:
        return ""

    summary = history.get("summary", "")
    facts = history.get("notable_facts", [])

    facts_html = ""
    if facts:
        items = "".join(f"<li>{esc(f)}</li>" for f in facts)
        facts_html = f'<ul class="gl-facts-list">{items}</ul>'

    return f"""
<section class="gl-section" id="history">
  <div class="gl-section-label">06 — History</div>
  <h2 class="gl-section-title">History &amp; Heritage</h2>
  <p class="gl-section-prose">{esc(summary)}</p>
  {facts_html}
</section>
"""


def build_series(race: dict) -> str:
    """[07] Series Membership badges."""
    series = race.get("series_membership", [])
    if not series:
        return ""

    badges_html = ""
    for s in series:
        label = SERIES_LABELS.get(s, s.replace("_", " ").title())
        css_class = "worldloppet" if "worldloppet" in s else (
            "ski-classics" if "ski_classics" in s else (
                "euroloppet" if "euroloppet" in s else ""
            )
        )
        badges_html += f'<span class="gl-series-badge {css_class}">{esc(label)}</span>'

    return f"""
<section class="gl-section" id="series">
  <div class="gl-section-label">07 — Series Membership</div>
  <h2 class="gl-section-title">Race Series</h2>
  <div class="gl-series-badges">
    {badges_html}
  </div>
</section>
"""


def build_youtube_placeholder(race: dict) -> str:
    """[08] YouTube placeholder section."""
    videos = race.get("youtube_data", {}).get("videos", [])
    if videos:
        # Future: render actual videos here
        return ""

    return f"""
<section class="gl-section" id="videos">
  <div class="gl-section-label">08 — Video</div>
  <h2 class="gl-section-title">Race Videos</h2>
  <div class="gl-placeholder">VIDEO ENRICHMENT COMING SOON</div>
</section>
"""


def build_training_section(race: dict) -> str:
    """[09] Train for This Race section."""
    name = esc(race.get("display_name", race["name"]))
    slug = esc(race["slug"])
    v = race["vitals"]
    distance = v.get("distance_km")
    elevation = v.get("elevation_m")
    country = esc(v.get("country", "this region"))

    if distance is not None and elevation is not None:
        course_desc = f"Build a periodized plan tailored to {name}&#39;s {distance}km course with {elevation}m of climbing."
    elif distance is not None:
        course_desc = f"Build a periodized plan tailored to {name}&#39;s {distance}km course."
    elif elevation is not None:
        course_desc = f"Build a periodized plan tailored to {name}&#39;s course with {elevation}m of climbing."
    else:
        course_desc = f"Build a periodized plan tailored to {name}&#39;s unique course demands."

    return f"""
<section class="gl-section" id="training">
  <div class="gl-section-label">09 — Training</div>
  <h2 class="gl-section-title">Train for {name}</h2>
  <p class="gl-section-prose">{course_desc}</p>
  <div class="gl-training-grid">
    <div class="gl-training-card">
      <div class="gl-training-card-title">Structured Workouts</div>
      <p class="gl-training-card-desc">.zwo files for Zwift, TrainerRoad, or standalone</p>
    </div>
    <div class="gl-training-card">
      <div class="gl-training-card-title">Periodized Plan</div>
      <p class="gl-training-card-desc">Base &rarr; Build &rarr; Peak &rarr; Taper, timed to race day</p>
    </div>
    <div class="gl-training-card">
      <div class="gl-training-card-title">Race-Specific Prep</div>
      <p class="gl-training-card-desc">Climate, altitude, and terrain protocols for {country}</p>
    </div>
  </div>
  <a href="/questionnaire/?race={slug}" class="gl-training-cta">BUILD MY {name} PLAN</a>
</section>
"""


def build_sticky_cta(race: dict) -> str:
    """Sticky CTA bar fixed to bottom of page."""
    name = esc(race.get("display_name", race["name"]))
    slug = esc(race["slug"])

    return f"""
<div class="gl-sticky-cta" id="gl-sticky-cta">
  <div class="gl-sticky-cta-inner">
    <span class="gl-sticky-cta-name">{name}</span>
    <div style="display:flex;align-items:center;gap:12px">
      <a href="/questionnaire/?race={slug}" class="gl-sticky-cta-btn" id="gl-sticky-cta-link">
        <span id="gl-sticky-cta-text">BUILD MY PLAN &mdash; $15/WK</span>
      </a>
      <button class="gl-sticky-cta-dismiss" onclick="document.getElementById('gl-sticky-cta').style.display='none';try{{sessionStorage.setItem('xl-cta-dismissed','1')}}catch(e){{}}" aria-label="Dismiss">&times;</button>
    </div>
  </div>
</div>
"""


def build_sticky_js() -> str:
    """JavaScript for sticky CTA bar visibility logic."""
    return """
<script>
(function() {
  var cta = document.getElementById('gl-sticky-cta');
  if (!cta) return;
  try { if (sessionStorage.getItem('xl-cta-dismissed')) { cta.style.display = 'none'; return; } } catch(e) {}
  var hero = document.getElementById('hero') || document.querySelector('.gl-hero');
  var training = document.getElementById('training');
  if (!hero) return;
  var heroVisible = true;
  var trainingVisible = false;
  function update() {
    requestAnimationFrame(function() {
      if (heroVisible || trainingVisible) {
        cta.classList.remove('visible');
      } else {
        cta.classList.add('visible');
      }
    });
  }
  var heroObs = new IntersectionObserver(function(entries) {
    if (entries.length > 0) { heroVisible = entries[0].isIntersecting; }
    update();
  }, { threshold: 0 });
  heroObs.observe(hero);
  if (training) {
    var trainObs = new IntersectionObserver(function(entries) {
      if (entries.length > 0) { trainingVisible = entries[0].isIntersecting; }
      update();
    }, { threshold: 0 });
    trainObs.observe(training);
  }
})();
</script>
"""


def build_footer(race: dict) -> str:
    """Footer with back link and branding."""
    return """
<footer class="gl-footer">
  <a href="/search/" class="gl-footer-back">&larr; Back to Search</a> | <a href="/" class="gl-footer-back">Home</a>
  <div class="gl-footer-brand">XC SKI LABS &mdash; Built for skiers who chase start lines.</div>
</footer>
"""


def build_jsonld(race: dict) -> str:
    """Build SportsEvent JSON-LD structured data."""
    v = race["vitals"]
    r = race["nordic_lab_rating"]

    event = {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": race["name"],
        "sport": "Cross-Country Skiing",
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "location": {
            "@type": "Place",
            "name": v.get("location", ""),
            "address": {
                "@type": "PostalAddress",
                "addressCountry": v.get("country_code", ""),
            },
        },
    }

    if v.get("lat") and v.get("lng"):
        event["location"]["geo"] = {
            "@type": "GeoCoordinates",
            "latitude": v["lat"],
            "longitude": v["lng"],
        }

    if v.get("website"):
        event["url"] = v["website"]

    event["review"] = {
        "@type": "Review",
        "author": {
            "@type": "Organization",
            "name": "XC Ski Labs",
        },
        "reviewRating": {
            "@type": "Rating",
            "ratingValue": str(r["overall_score"]),
            "bestRating": "100",
            "worstRating": "0",
        },
    }

    return (
        '<script type="application/ld+json">'
        + _safe_json_for_script(event, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


# ── Page Assembly ──────────────────────────────────────────────

def generate_page(race: dict) -> str:
    """Generate a complete HTML page for a race."""
    name = race.get("display_name", race["name"])
    slug = race["slug"]
    r = race["nordic_lab_rating"]
    tier = r["tier"]
    score = r["overall_score"]
    v = race["vitals"]
    country = v.get("country", "")

    title = f"{esc(name)} | XC Ski Labs XC Ski Race Review"
    description = (
        f"{esc(race.get('tagline', name))} "
        f"Rated {score}/100 (Tier {tier}) in {esc(country)}. "
        f"Course, climate, ratings &amp; full breakdown."
    )

    css = build_css()
    jsonld = build_jsonld(race)
    ga4_snippet = build_ga4_snippet()

    nav_header = build_nav_header()
    hero = build_hero(race)
    vitals = build_at_a_glance(race)
    course = build_course(race)
    climate = build_climate(race)
    rating = build_rating_breakdown(race)
    training = build_training_section(race)
    history = build_history(race)
    series = build_series(race)
    youtube = build_youtube_placeholder(race)
    sticky_cta = build_sticky_cta(race)
    sticky_js = build_sticky_js()
    cookie_consent = build_cookie_consent()
    footer = build_footer(race)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%231a2332'/><text x='16' y='24' text-anchor='middle' font-family='monospace' font-size='22' font-weight='700' fill='%23e8edf2'>GL</text></svg>">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:type" content="article">
  {jsonld}
  {ga4_snippet}
  <style>{css}</style>
</head>
<body>
<a href="#course" class="gl-skip-link">Skip to content</a>
{nav_header}
<div class="gl-page">
{hero}
{vitals}
{course}
{climate}
{rating}
{training}
{history}
{series}
{youtube}
{footer}
</div>
{sticky_cta}
{sticky_js}
{cookie_consent}
</body>
</html>"""


# ── File I/O ───────────────────────────────────────────────────

def load_race(filepath: Path) -> Optional[dict]:
    """Load and validate a race JSON file."""
    try:
        with open(filepath, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        race = data.get("race")
        if not race:
            print(f"  SKIP {filepath.name}: no 'race' key")
            return None
        if not race.get("slug"):
            print(f"  SKIP {filepath.name}: no 'slug'")
            return None
        if not race.get("nordic_lab_rating"):
            print(f"  SKIP {filepath.name}: no 'nordic_lab_rating'")
            return None
        return race
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ERROR {filepath.name}: {e}")
        return None


def generate_all(data_dir: Path, output_dir: Path, slug_filter: Optional[str] = None):
    """Generate HTML pages for all races (or a single slug)."""
    files = sorted(data_dir.glob("*.json"))
    files = [f for f in files if f.name != "_schema.json"]

    if slug_filter:
        target = data_dir / f"{slug_filter}.json"
        if not target.exists():
            print(f"ERROR: No race file found for slug '{slug_filter}'")
            print(f"  Expected: {target}")
            sys.exit(1)
        files = [target]

    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    errors = 0
    tiers = {1: 0, 2: 0, 3: 0, 4: 0}

    for filepath in files:
        race = load_race(filepath)
        if not race:
            errors += 1
            continue

        slug = race["slug"]
        tier = race["nordic_lab_rating"]["tier"]

        page_html = generate_page(race)

        # Write to output/{slug}/index.html
        page_dir = output_dir / slug
        page_dir.mkdir(parents=True, exist_ok=True)
        out_path = page_dir / "index.html"
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(page_html)

        total += 1
        tiers[tier] = tiers.get(tier, 0) + 1

    print(f"\nGenerated {total} race pages → {output_dir}/")
    if errors:
        print(f"  Skipped/errors: {errors}")
    print(f"  T1: {tiers.get(1, 0)} | T2: {tiers.get(2, 0)} | T3: {tiers.get(3, 0)} | T4: {tiers.get(4, 0)}")


# ── CLI ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate XC Ski Labs race pages from JSON profiles."
    )
    parser.add_argument(
        "--slug",
        type=str,
        default=None,
        help="Generate a single race by slug (e.g., vasaloppet)",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=str(DEFAULT_DATA_DIR),
        help=f"Race data directory (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    if not data_dir.exists():
        print(f"ERROR: Data directory not found: {data_dir}")
        sys.exit(1)

    print(f"XC Ski Labs Race Page Generator")
    print(f"  Data: {data_dir}")
    print(f"  Output: {output_dir}")
    if args.slug:
        print(f"  Slug: {args.slug}")
    print()

    generate_all(data_dir, output_dir, args.slug)


if __name__ == "__main__":
    main()
