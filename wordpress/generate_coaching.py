#!/usr/bin/env python3
"""
XC Ski Labs — Coaching Landing Page Generator ("The Dossier")

Generates the public /coaching/ landing page: hero, five numbered terms
of engagement, three service tiers, a fit check, FAQ, and a dark
application close. Structure and copy mirror the Roadie Labs "Dossier"
coaching page (road-race-automation/wordpress/generate_coaching.py)
verbatim except for XC-specific swaps: monthly billing (not 4-week),
no setup fee, watch/ski-erg language in place of trainer/head-unit,
and no coaching@ contact line (no verified mailbox on this domain yet).

Self-contained HTML matching this repo's convention (see
wordpress/generate_coaching_apply.py): tokens.css embedded, nav/footer/
GA4/consent inline, gl- class prefix. Strictly monochrome — no
swix-red, no klister yellow, no wax-quartet blues — this page is a
still document, not a wax-box ad.

Usage:
    python wordpress/generate_coaching.py
    python wordpress/generate_coaching.py --output-dir output
"""

import html
import json
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"

SITE_BASE_URL = "https://xcskilabs.com"
APPLY_URL = "/coaching/apply/"
GA4_ID = "G-3JQLSQLPPM"


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
    """Read shared Wax Bench tokens for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


# ── CSS ────────────────────────────────────────────────────────

def build_css() -> str:
    """Build the complete CSS for the coaching landing page.

    Strictly monochrome: only --gl-paper / --gl-carbon / --gl-white /
    --gl-hairline / --gl-muted are used. No --gl-swix-red, no
    --gl-klister, no wax-quartet colors anywhere on this page.
    """
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

a { color: var(--gl-carbon); }

a:focus-visible, button:focus-visible {
  outline: 2px solid var(--gl-carbon);
  outline-offset: 2px;
}

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

/* ── Bands ────────────────────────────────────── */

.gl-coach-band {
  padding: 64px 0;
  border-bottom: 1px solid var(--gl-hairline);
}

.gl-coach-band:last-of-type { border-bottom: none; }

.gl-coach-band--dark {
  background: var(--gl-carbon);
  color: var(--gl-paper);
}

.gl-coach-inner {
  max-width: var(--gl-measure);
  margin: 0 auto;
  padding: 0 24px;
}

/* ── Section head — quiet numeral, serif title ─── */

.gl-coach-sec-head {
  display: flex;
  align-items: baseline;
  gap: 16px;
  border-bottom: 1px solid var(--gl-hairline);
  padding-bottom: 12px;
  margin-bottom: 32px;
}

.gl-coach-sec-num {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-muted);
  letter-spacing: 2px;
}

.gl-coach-sec-title {
  font-family: var(--gl-font-editorial);
  font-size: 1.4rem;
  font-weight: 700;
  margin: 0;
  line-height: 1.2;
}

/* ── Hero ─────────────────────────────────────── */

.gl-coach-hero h1 {
  font-family: var(--gl-font-editorial);
  font-size: clamp(1.8rem, 4vw, 2.6rem);
  font-weight: 700;
  line-height: 1.2;
  margin: 0;
  max-width: 24ch;
}

.gl-coach-tagline {
  font-family: var(--gl-font-editorial);
  font-size: 1.1rem;
  line-height: 1.65;
  color: var(--gl-muted);
  max-width: 52ch;
  margin: 24px 0 0;
}

.gl-coach-hero-cta {
  display: inline-block;
  margin-top: 32px;
  border: 2px solid var(--gl-carbon);
  padding: 15px 30px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--gl-carbon);
  text-decoration: none;
}

.gl-coach-hero-cta:hover {
  background: var(--gl-carbon);
  color: var(--gl-paper);
}

/* ── Terms — numbered clauses ─────────────────── */

.gl-coach-terms { padding-bottom: 0; }

.gl-coach-term {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 24px;
  padding: 24px 0;
  border-bottom: 1px solid var(--gl-hairline);
}

.gl-coach-term:last-child { border-bottom: none; }

.gl-coach-term-num {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-muted);
  letter-spacing: 1px;
  padding-top: 4px;
}

.gl-coach-term-body h3 {
  font-family: var(--gl-font-editorial);
  font-size: 1.1rem;
  font-weight: 700;
  margin: 0 0 8px;
  line-height: 1.25;
}

.gl-coach-term-body p {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--gl-muted);
  margin: 0;
  max-width: 60ch;
}

/* ── Tiers — quiet columns, no cards ───────────── */

.gl-coach-tiers-section { padding-top: 0; }

.gl-coach-tiers {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0;
  border-top: 1px solid var(--gl-carbon);
}

.gl-coach-tier-col {
  padding: 32px 24px;
  border-right: 1px solid var(--gl-hairline);
}

.gl-coach-tier-col:first-child { padding-left: 0; }
.gl-coach-tier-col:last-child { border-right: none; padding-right: 0; }

.gl-coach-tier-name {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--gl-muted);
}

.gl-coach-tier-price {
  font-family: var(--gl-font-editorial);
  font-size: 1.9rem;
  font-weight: 700;
  margin: 8px 0 0;
}

.gl-coach-tier-interval {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 400;
  color: var(--gl-muted);
  margin-left: 4px;
  letter-spacing: 0.5px;
}

.gl-coach-tier-desc {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--gl-muted);
  margin: 16px 0 24px;
}

.gl-coach-tier-list {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
}

.gl-coach-tier-list li {
  padding: 8px 0;
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  color: var(--gl-carbon);
  border-bottom: 1px solid var(--gl-hairline);
  line-height: 1.5;
}

.gl-coach-tier-list li:last-child { border-bottom: none; }

.gl-coach-tier-cta {
  display: inline-block;
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--gl-carbon);
  text-decoration: none;
  border-bottom: 1px solid var(--gl-carbon);
  padding-bottom: 2px;
}

.gl-coach-tier-cta:hover { color: var(--gl-muted); border-color: var(--gl-muted); }

.gl-coach-tier-disclaimer {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-muted);
  line-height: 1.6;
  margin-top: 32px;
  margin-bottom: 0;
  max-width: 68ch;
}

/* ── A fit, or not ─────────────────────────────── */

.gl-coach-fit {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 48px;
  max-width: 900px;
}

.gl-coach-fit-heading {
  font-family: var(--gl-font-editorial);
  font-size: 1rem;
  font-weight: 700;
  margin: 0 0 16px;
}

.gl-coach-fit-heading--no { color: var(--gl-muted); }

.gl-coach-fit-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.gl-coach-fit-list li {
  padding: 10px 0;
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-carbon);
  border-bottom: 1px solid var(--gl-hairline);
  line-height: 1.5;
}

.gl-coach-fit-list li:last-child { border-bottom: none; }

.gl-coach-fit-list--no li { color: var(--gl-muted); }

/* ── FAQ accordion ────────────────────────────── */

.gl-coach-faq-list { max-width: 720px; }

.gl-coach-faq-item { border-bottom: 1px solid var(--gl-hairline); }
.gl-coach-faq-item:first-child { border-top: 1px solid var(--gl-hairline); }

.gl-coach-faq-q {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 0;
  cursor: pointer;
  font-family: var(--gl-font-editorial);
  font-size: 1rem;
  font-weight: 700;
  color: var(--gl-carbon);
  user-select: none;
}

.gl-coach-faq-q:hover { color: var(--gl-muted); }

.gl-coach-faq-toggle {
  font-family: var(--gl-font-data);
  font-size: 1.1rem;
  color: var(--gl-muted);
  flex-shrink: 0;
}

.gl-coach-faq-a {
  display: none;
  padding: 0 0 16px;
}

.gl-coach-faq-item.gl-coach-faq-open .gl-coach-faq-a { display: block; }

.gl-coach-faq-a p {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-muted);
  line-height: 1.6;
  margin: 0;
  max-width: 60ch;
}

/* ── Application close — dark band ─────────────── */

.gl-coach-final {
  padding: 8px 0;
}

.gl-coach-final-kicker {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: var(--gl-muted);
  margin: 0 0 24px;
}

.gl-coach-final-hook {
  font-family: var(--gl-font-editorial);
  font-size: 1.5rem;
  line-height: 1.6;
  color: var(--gl-paper);
  margin: 0 0 32px;
  max-width: 26em;
}

.gl-coach-final-cta {
  display: inline-block;
  border: 1px solid var(--gl-paper);
  padding: 14px 28px;
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
  color: var(--gl-paper);
  text-decoration: none;
}

.gl-coach-final-cta:hover { background: var(--gl-paper); color: var(--gl-carbon); }

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
  /* Repo pitfall #32: without bottom padding on the page, the sticky
     CTA overlaps the footer on short pages. */
  .gl-coach-page { padding-bottom: 80px; }
}

/* ── Cookie Consent ───────────────────────────── */

.gl-coach-cookie-consent {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-carbon);
  border-top: 1px solid var(--gl-paper);
  padding: 20px;
  display: none;
}
.gl-coach-cookie-consent.visible { display: block; }
.gl-coach-cookie-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.gl-coach-cookie-text {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  color: var(--gl-white);
  flex: 1;
  min-width: 200px;
}
.gl-coach-cookie-buttons { display: flex; gap: 10px; }
.gl-coach-cookie-btn {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  padding: 10px 20px;
  border: 1px solid var(--gl-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 44px;
  min-height: 44px;
  background: transparent;
  color: var(--gl-white);
}
.gl-coach-cookie-btn.accept { background: var(--gl-white); color: var(--gl-carbon); }

/* ── Responsive ───────────────────────────────── */

@media (max-width: 768px) {
  .gl-coach-inner { padding: 0 20px; }
  .gl-coach-band { padding: 40px 0; }
  .gl-coach-hero h1 { font-size: 1.7rem; }
  .gl-coach-term { grid-template-columns: 1fr; gap: 8px; }
  .gl-coach-term-num { padding-top: 0; }
  .gl-coach-tiers { grid-template-columns: 1fr; }
  .gl-coach-tier-col {
    border-right: none;
    border-bottom: 1px solid var(--gl-hairline);
    padding: 24px 0;
  }
  .gl-coach-tier-col:first-child { padding-top: 0; }
  .gl-coach-tier-col:last-child { border-bottom: none; padding-bottom: 0; }
  .gl-coach-fit { grid-template-columns: 1fr; gap: 24px; }
  .gl-coach-final-hook { font-size: 1.25rem; }
  .gl-coach-nav-links { gap: 12px; }
}

@media (max-width: 400px) {
  .gl-coach-inner { padding: 0 14px; }
  .gl-coach-hero h1 { font-size: 1.4rem; }
}
"""


# ── Nav / Footer ───────────────────────────────────────────────

def build_nav() -> str:
    """Site navigation bar. Coaching is the active item — this IS /coaching/."""
    return """
<nav class="gl-coach-nav">
  <a href="/" class="gl-coach-nav-brand">XC Ski Labs</a>
  <div class="gl-coach-nav-links">
    <a href="/">Home</a>
    <a href="/search/">Search</a>
    <a href="/training-plans/">Training Plans</a>
    <a href="/guide/">Guide</a>
    <a href="/coaching/" class="active">Coaching</a>
  </div>
</nav>"""


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
  </div>
  <div class="gl-coach-footer-copy">&copy; 2026 XC Ski Labs. All rights reserved.</div>
</footer>"""


# ── Section builders ─────────────────────────────────────────────

def _sec_head(num: str, title: str) -> str:
    return (
        f'<div class="gl-coach-sec-head">'
        f'<span class="gl-coach-sec-num">{num}</span>'
        f'<h2 class="gl-coach-sec-title">{title}</h2>'
        f'</div>'
    )


# SANCTIONED EXCEPTION to the anti-defensive-messaging rule (see
# docs/BRAND_GUIDELINES.md, section 7 "Voice" — phrases naming what
# something ISN'T are normally banned because they plant doubt nobody
# had). The sub-line below ("Not an AI, not a dashboard, not a coach
# who reads you like a spreadsheet") is an explicit, owner-approved
# exception. Matti sanctioned this specific line 2026-07-18 as an
# aspirational "corner" frame — it names what you're getting, not a
# defensive rebuttal to an objection nobody raised. This /coaching/
# hero is the precedent-setting instance for XC Ski Labs (it mirrors
# the separately-approved exception already shipped on Roadie Labs'
# /coaching/ hero).
def build_hero() -> str:
    return f'''<section class="gl-coach-band gl-coach-hero" id="hero">
    <div class="gl-coach-inner">
      <h1>You could be better than you think. That is not encouragement &mdash; it&rsquo;s an observation about people who train alone.</h1>
      <p class="gl-coach-tagline">The fix is a human in your corner. Not an AI, not a dashboard, not a coach who reads you like a spreadsheet. The terms are below.</p>
      <a href="{APPLY_URL}" class="gl-coach-hero-cta">GET ME IN YOUR CORNER &rarr;</a>
    </div>
  </section>'''


def build_terms() -> str:
    clauses = [
        (
            "01",
            "Every file, read by a person",
            "Software flags a number. I notice the interval you bailed on and ask why.",
        ),
        (
            "02",
            "The patterns you can&rsquo;t see",
            "You can know everything about training and still train wrong. Knowledge isn&rsquo;t the limiter &mdash; application is. Every athlete is their own worst blindspot: too fresh to rest, too stubborn to taper, too close to their own data to see the shape of it. Seeing it is the job.",
        ),
        (
            "03",
            "The plan moves when your life does",
            "Sick kid, work trip, tender knee &mdash; the week adjusts that week, not after three missed targets teach an algorithm what a person would have seen on Tuesday.",
        ),
        (
            "04",
            "The truth, on schedule",
            "&ldquo;You&rsquo;re sandbagging&rdquo; and &ldquo;take the rest week&rdquo; are both part of the service.",
        ),
        (
            "05",
            "Involvement is the only variable",
            "Same coach, same standards. The difference is how often I&rsquo;m looking.",
        ),
    ]
    rows = "\n        ".join(
        f'<div class="gl-coach-term">'
        f'<div class="gl-coach-term-num">{num}</div>'
        f'<div class="gl-coach-term-body"><h3>{title}</h3><p>{body}</p></div>'
        f'</div>'
        for num, title, body in clauses
    )
    return f'''<section class="gl-coach-band gl-coach-terms" id="terms">
    <div class="gl-coach-inner">
      {rows}
    </div>
  </section>'''


def build_tiers() -> str:
    return f'''<section class="gl-coach-band gl-coach-tiers-section" id="tiers">
    <div class="gl-coach-inner">
      <div class="gl-coach-tiers">
        <div class="gl-coach-tier-col">
          <div class="gl-coach-tier-name">Min</div>
          <div class="gl-coach-tier-price">$199<span class="gl-coach-tier-interval">/ MONTH</span></div>
          <p class="gl-coach-tier-desc">The plan, plus a weekly check of your training. For athletes who execute on their own and want the thinking done right.</p>
          <ul class="gl-coach-tier-list">
            <li>Weekly training review</li>
            <li>File analysis</li>
            <li>Quarterly strategy calls</li>
            <li>Structured workouts for your watch or ski erg</li>
            <li>Race-day nutrition plan</li>
            <li>Custom training guide</li>
          </ul>
          <a href="{APPLY_URL}?tier=min" class="gl-coach-tier-cta">GET STARTED</a>
        </div>
        <div class="gl-coach-tier-col">
          <div class="gl-coach-tier-name">Mid</div>
          <div class="gl-coach-tier-price">$299<span class="gl-coach-tier-interval">/ MONTH</span></div>
          <p class="gl-coach-tier-desc">The plan, watched. Someone reads the data between sessions and adjusts the same week life changes. Most athletes belong here.</p>
          <ul class="gl-coach-tier-list">
            <li>Everything in Min</li>
            <li>Detailed training-file analysis</li>
            <li>Every-4-week strategy calls</li>
            <li>Weekly plan adjustments</li>
            <li>Direct message access</li>
            <li>Blindspot detection</li>
          </ul>
          <a href="{APPLY_URL}?tier=mid" class="gl-coach-tier-cta">GET STARTED</a>
        </div>
        <div class="gl-coach-tier-col">
          <div class="gl-coach-tier-name">Max</div>
          <div class="gl-coach-tier-price">$1,200<span class="gl-coach-tier-interval">/ MONTH</span></div>
          <p class="gl-coach-tier-desc">Everything, daily. For the race where you want nothing left to chance.</p>
          <ul class="gl-coach-tier-list">
            <li>Everything in Mid</li>
            <li>Daily file review</li>
            <li>On-demand calls</li>
            <li>Race-week strategy</li>
            <li>Multi-race season planning</li>
            <li>Priority response</li>
          </ul>
          <a href="{APPLY_URL}?tier=max" class="gl-coach-tier-cta">GET STARTED</a>
        </div>
      </div>
      <p class="gl-coach-tier-disclaimer">Coaching doesn&rsquo;t fix skipped workouts or feedback you don&rsquo;t act on. If this isn&rsquo;t a fit, I&rsquo;ll tell you within 24 hours.</p>
    </div>
  </section>'''


def build_fit() -> str:
    return f'''<section class="gl-coach-band" id="fit">
    <div class="gl-coach-inner">
      {_sec_head("06", "A fit, or not")}
      <div class="gl-coach-fit">
        <div>
          <h3 class="gl-coach-fit-heading">Coaching is for you if:</h3>
          <ul class="gl-coach-fit-list">
            <li>You&rsquo;ll do the training when the thinking is done right</li>
            <li>You have a race and a reason</li>
            <li>You&rsquo;re ready to be honest about your habits</li>
            <li>You want a plan smarter than the one you&rsquo;d build alone</li>
          </ul>
        </div>
        <div>
          <h3 class="gl-coach-fit-heading gl-coach-fit-heading--no">It isn&rsquo;t:</h3>
          <ul class="gl-coach-fit-list gl-coach-fit-list--no">
            <li>Accountability texts when you skip a Tuesday</li>
            <li>Validation dressed up as feedback</li>
            <li>A rescue for a race that&rsquo;s next week</li>
            <li>A substitute for doing the work</li>
          </ul>
        </div>
      </div>
    </div>
  </section>'''


def build_faq() -> str:
    faqs = [
        (
            "What&rsquo;s the difference between a plan and coaching?",
            "A plan is a document. Coaching is the relationship that changes the document when your life changes.",
        ),
        (
            "How often will I hear from you?",
            "Weekly at minimum, more near your race. You can message me anytime.",
        ),
        (
            "What data do I need?",
            "A watch with heart rate is plenty. Every workout carries effort-based targets you can train by feel.",
        ),
        (
            "What if I miss workouts?",
            "Life happens. I adjust. The plan serves you, not the other way around.",
        ),
        (
            "How do I know if coaching is working?",
            "We set baselines at intake and measure against them. You&rsquo;ll know.",
        ),
        (
            "What&rsquo;s the time commitment?",
            "The training you&rsquo;re already doing, but smarter. I&rsquo;m not adding hours &mdash; I&rsquo;m making the ones you have count.",
        ),
        (
            "Can I cancel anytime?",
            "Yes. No contracts, no cancellation fees. Your coaching access continues through the end of your current monthly cycle.",
        ),
    ]

    items = []
    for idx, (q, a) in enumerate(faqs):
        ans_id = f'gl-coach-faq-ans-{idx}'
        items.append(
            f'<div class="gl-coach-faq-item">'
            f'<div class="gl-coach-faq-q" role="button" tabindex="0" aria-expanded="false" aria-controls="{ans_id}">'
            f'{q}'
            f'<span class="gl-coach-faq-toggle" aria-hidden="true">+</span>'
            f'</div>'
            f'<div class="gl-coach-faq-a" id="{ans_id}" role="region"><p>{a}</p></div>'
            f'</div>'
        )
    inner = "\n      ".join(items)
    return f'''<section class="gl-coach-band" id="faq">
    <div class="gl-coach-inner">
      {_sec_head("07", "FAQ")}
      <div class="gl-coach-faq-list">
      {inner}
      </div>
    </div>
  </section>'''


def build_close() -> str:
    return f'''<section class="gl-coach-band gl-coach-band--dark" id="final-cta">
    <div class="gl-coach-inner">
      <div class="gl-coach-final">
        <p class="gl-coach-final-kicker">APPLICATION</p>
        <p class="gl-coach-final-hook">Ten minutes of honest answers. I read every one myself. You&rsquo;ll hear from me within 48 hours &mdash; including if I don&rsquo;t think coaching is what you need.</p>
        <a href="{APPLY_URL}" class="gl-coach-final-cta">GET ME IN YOUR CORNER &rarr;</a>
      </div>
    </div>
  </section>'''


def build_mobile_sticky_cta() -> str:
    return f'''<div class="gl-coach-sticky-cta">
    <a href="{APPLY_URL}">GET ME IN YOUR CORNER &rarr;</a>
  </div>'''


def build_cookie_consent() -> str:
    """Cookie consent banner — monochrome variant of the repo's standard pattern."""
    return """
<div class="gl-coach-cookie-consent" id="gl-coach-cookie-consent">
  <div class="gl-coach-cookie-inner">
    <p class="gl-coach-cookie-text">We use cookies for analytics to improve your experience. You can accept or decline.</p>
    <div class="gl-coach-cookie-buttons">
      <button class="gl-coach-cookie-btn accept" id="gl-coach-cookie-accept">Accept</button>
      <button class="gl-coach-cookie-btn" id="gl-coach-cookie-decline">Decline</button>
    </div>
  </div>
</div>
<script>
(function(){
  var banner=document.getElementById('gl-coach-cookie-consent');
  if(!banner)return;
  if(document.cookie.match(/xl_consent=/)){return;}
  banner.classList.add('visible');
  document.getElementById('gl-coach-cookie-accept').addEventListener('click',function(){
    document.cookie='xl_consent=accepted;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'granted'});gtag('js',new Date());gtag('config','""" + GA4_ID + """');}
  });
  document.getElementById('gl-coach-cookie-decline').addEventListener('click',function(){
    document.cookie='xl_consent=declined;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'denied'});}
  });
})();
</script>
"""


def build_page_js() -> str:
    """FAQ accordion toggle — single-open behavior, no CSS transitions."""
    return """
<script>
(function() {
  var items = document.querySelectorAll('.gl-coach-faq-item');
  items.forEach(function(item) {
    var q = item.querySelector('.gl-coach-faq-q');
    if (!q) return;
    function toggle() {
      var wasOpen = item.classList.contains('gl-coach-faq-open');
      items.forEach(function(i) {
        i.classList.remove('gl-coach-faq-open');
        var iq = i.querySelector('.gl-coach-faq-q');
        if (iq) iq.setAttribute('aria-expanded', 'false');
      });
      if (!wasOpen) {
        item.classList.add('gl-coach-faq-open');
        q.setAttribute('aria-expanded', 'true');
      } else {
        q.setAttribute('aria-expanded', 'false');
      }
    }
    q.addEventListener('click', toggle);
    q.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    });
  });
})();
</script>"""


def build_jsonld() -> str:
    """WebPage + Service JSON-LD, serialized via the safe-json helper."""
    webpage = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Coaching | XC Ski Labs",
        "description": "1:1 cross-country ski coaching from one coach. A human who reads your training data, adjusts the plan when your life changes, and tells you the truth.",
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
        "description": "Cross-country ski coaching: three tiers of involvement from weekly review to daily high-touch support. One coach reads every file — built around your race, your schedule, and your training history.",
    }
    wp_tag = f'<script type="application/ld+json">{_safe_json_for_script(webpage, separators=(",", ":"))}</script>'
    svc_tag = f'<script type="application/ld+json">{_safe_json_for_script(service, separators=(",", ":"))}</script>'
    return f'{wp_tag}\n  {svc_tag}'


# ── Page assembly ─────────────────────────────────────────────

def generate_page(output_dir: Path = None) -> Path:
    """Generate the coaching landing page."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "coaching" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    canonical_url = f"{SITE_BASE_URL}/coaching/"
    title = "1:1 XC Ski Coaching | XC Ski Labs"
    description = (
        "1:1 cross-country ski coaching from one coach. Three tiers of "
        "involvement, weekly review to daily support, and a plan that "
        "moves when your life does. From $199/month."
    )

    nav = build_nav()
    hero = build_hero()
    terms = build_terms()
    tiers = build_tiers()
    fit = build_fit()
    faq = build_faq()
    close = build_close()
    sticky = build_mobile_sticky_cta()
    footer = build_footer()
    consent = build_cookie_consent()
    page_js = build_page_js()
    jsonld = build_jsonld()
    css = build_css()

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
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{esc(canonical_url)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%23141414'/><text x='16' y='24' text-anchor='middle' font-family='monospace' font-size='22' font-weight='700' fill='%23f2f0eb'>GL</text></svg>">
  {og_tags}
  {jsonld}
  <style>{css}</style>
  <script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
  <script>
  window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments)}}
  (function(){{var c=(document.cookie.match(/xl_consent=([^;]+)/)||[])[1];
  if(c==='declined')return;gtag('js',new Date());gtag('config','{GA4_ID}')}})();
  </script>
</head>
<body>

{nav}

<div class="gl-coach-page">

  {hero}

  {terms}

  {tiers}

  {fit}

  {faq}

  {close}

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
