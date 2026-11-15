#!/usr/bin/env python3
"""
XC Ski Labs — Coaching Landing Page Generator ("The Dossier")

Generates the public /coaching/ landing page: hero, five numbered terms
of engagement, three service tiers, a fit check, FAQ, and a dark
application close. Structure and copy mirror the Roadie Labs "Dossier"
coaching page (road-race-automation/wordpress/generate_coaching.py)
verbatim except for XC-specific swaps: watch/ski-erg language in place
of trainer/head-unit,
and no coaching@ contact line (no verified mailbox on this domain yet).

Billing matches the real checkout (athlete-custom-training-plan-pipeline
brands.yaml xcskilabs.coaching: billing_period_days 28, setup_fee_cents
9900, trainingpeaks_premium_included true): every 4 weeks, plus a
one-time $99 setup fee. Never "monthly" in billing copy.

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

.gl-coach-tier-setup-fee {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  color: var(--gl-muted);
  line-height: 1.6;
  margin-top: 8px;
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
  /* Repo pitfall #32: the fixed sticky CTA must not cover the end of the
     page. The padding sits on body, not .gl-coach-page, because the
     Privacy choices strip comes after the page wrapper and must stay
     tappable. */
  body { padding-bottom: 80px; }
}

/* ── Cookie Consent ───────────────────────────── */


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

@media (max-width: 400px) {
  .gl-coach-inner { padding: 0 14px; }
  .gl-coach-hero h1 { font-size: 1.4rem; }
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


# Hero (Matti, 2026-11-15): he picked this H1 and sub-line and asked for the
# page to read "like Johnny Klister would write it", the wax-bench voice.
# The H1 says what is for sale: ski coaching. No positioning against AI or
# software anywhere on the page (Matti, 2026-11-14);
# tests/test_no_ai_positioning.py enforces this on every generated page.
HERO_H1 = "Ski coaching for people who&rsquo;ll roller ski in July to pass people in February."
HERO_SUB = (
    "I plan your dryland and your snow weeks around your races, read the "
    "sessions you upload, and move the week when life or a thaw gets in the "
    "way. From $199 every 4 weeks."
)
APPLY_CTA = "APPLY FOR SKI COACHING &rarr;"
REPLY_TIME = "48 hours"
CONTACT_EMAIL = "gravelgodcoaching@gmail.com"


def build_hero() -> str:
    return f'''<section class="gl-coach-band gl-coach-hero" id="hero">
    <div class="gl-coach-inner">
      <h1>{HERO_H1}</h1>
      <p class="gl-coach-tagline">{HERO_SUB}</p>
      <a href="{APPLY_URL}" class="gl-coach-hero-cta">{APPLY_CTA}</a>
    </div>
  </section>'''


def build_terms() -> str:
    clauses = [
        (
            "01",
            "I read your sessions",
            "Heart rate, pace and how it felt. I look for the intervals that drifted and the easy distance that crept up into threshold.",
        ),
        (
            "02",
            "Dryland that counts",
            "Roller skis, running, bounding and strength from spring until the trails open. Then the snow block goes to skiing.",
        ),
        (
            "03",
            "Classic, skate or both",
            "Your plan follows your technique and your races, from a club 10k to the Birkie.",
        ),
        (
            "04",
            "Plans that follow the snow",
            "At Mid and Max, a work trip, a head cold or a thaw that turns the trails to mashed potatoes changes the week that week.",
        ),
        (
            "05",
            "Plain feedback",
            "If your easy days are too hard, I&rsquo;ll tell you. If you&rsquo;re waxing for a race you haven&rsquo;t trained for, I&rsquo;ll tell you that too.",
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
          <div class="gl-coach-tier-price">$199<span class="gl-coach-tier-interval">/ 4 WEEKS</span></div>
          <p class="gl-coach-tier-desc">You keep your own training going and want my eyes on it each week.</p>
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
          <div class="gl-coach-tier-price">$299<span class="gl-coach-tier-interval">/ 4 WEEKS</span></div>
          <p class="gl-coach-tier-desc">I check each session as it comes in and adjust the next days to match.</p>
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
          <div class="gl-coach-tier-price">$1,200<span class="gl-coach-tier-interval">/ 4 WEEKS</span></div>
          <p class="gl-coach-tier-desc">Every session read the day you upload it. For the season built around one race.</p>
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
      <p class="gl-coach-tier-disclaimer">Coaching won&rsquo;t fix skipped sessions or feedback you ignore. If it isn&rsquo;t a fit for you, I&rsquo;ll say so within {REPLY_TIME}.</p>
      <p class="gl-coach-tier-setup-fee">TrainingPeaks Premium is included with every tier. Checkout includes a one-time $99 setup fee for intake analysis and your first plan build. Any waiver is offered privately, case by case.</p>
    </div>
  </section>'''


def build_fit() -> str:
    return f'''<section class="gl-coach-band" id="fit">
    <div class="gl-coach-inner">
      {_sec_head("06", "A fit, or not")}
      <div class="gl-coach-fit">
        <div>
          <h3 class="gl-coach-fit-heading">Coaching fits if:</h3>
          <ul class="gl-coach-fit-list">
            <li>You have a ski race picked out and time to train for it</li>
            <li>You&rsquo;ll train through summer and fall, while race day is still a long way off</li>
            <li>You&rsquo;ll upload your sessions and tell me how they felt</li>
          </ul>
        </div>
        <div>
          <h3 class="gl-coach-fit-heading gl-coach-fit-heading--no">Probably not a fit if:</h3>
          <ul class="gl-coach-fit-list gl-coach-fit-list--no">
            <li>Race day is a week away</li>
            <li>You need an injury managed. See a physio for that one first</li>
            <li>You won&rsquo;t wear a heart rate monitor or log what you did</li>
          </ul>
        </div>
      </div>
    </div>
  </section>'''


def build_faq() -> str:
    faqs = [
        (
            "What happens after I apply?",
            f"I reply within {REPLY_TIME}, yes or no, with the reason.",
        ),
        (
            "Can I ask you something before I apply?",
            f'Yes. Write to <a href="mailto:{CONTACT_EMAIL}">{CONTACT_EMAIL}</a> with anything you want to ask before applying.',
        ),
        (
            "How often will I hear from you?",
            "At least once a week, more in the last weeks before your race. Mid and Max can message me any time.",
        ),
        (
            "What data do I need?",
            "A watch with heart rate is plenty. Every session has effort targets you can ski by feel.",
        ),
        (
            "I live where snow is short. Can you still coach me?",
            "Yes. Most of the year is dryland anyway, and I plan the snow weeks around when you can get on snow.",
        ),
        (
            "What if I miss sessions?",
            "Let me know. At Mid and Max I shift the week right away, and at Min it gets sorted in the weekly review. Either way, a missed interval session doesn&rsquo;t get made up on tired legs.",
        ),
        (
            "How will I know it&rsquo;s working?",
            "We set baselines at intake and check against them as the season goes.",
        ),
        (
            "What&rsquo;s the $99 setup fee?",
            "It covers intake analysis, a look through your training history and your first plan build. It&rsquo;s charged once, with your first 4 weeks.",
        ),
        (
            "Can I cancel anytime?",
            "Yes. No contracts and no cancellation fee. Your coaching runs through the end of the 4-week cycle you&rsquo;ve paid for.",
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
        <p class="gl-coach-final-hook">Ten minutes on your skiing, your races and your week. I reply to each one within {REPLY_TIME}.</p>
        <a href="{APPLY_URL}" class="gl-coach-final-cta">{APPLY_CTA}</a>
      </div>
    </div>
  </section>'''


def build_mobile_sticky_cta() -> str:
    return f'''<div class="gl-coach-sticky-cta">
    <a href="{APPLY_URL}">{APPLY_CTA}</a>
  </div>'''


def build_cookie_consent() -> str:
    """Shared consent banner and Privacy choices strip (scripts/consent.py)."""
    return get_consent_banner_html()


def build_page_js() -> str:
    """FAQ accordion toggle — single-open behavior, no CSS transitions —
    and cta_click events with Gravel God's coaching-page cta_name values
    (gravel-race-automation wordpress/generate_coaching.py): hero_apply,
    tier_min / tier_mid / tier_max, final_fill_intake, sticky_cta."""
    return """
<script>
(function() {
  var ctaNames = [
    ['.gl-coach-hero-cta', 'hero_apply'],
    ['.gl-coach-final-cta', 'final_fill_intake'],
    ['.gl-coach-sticky-cta a', 'sticky_cta']
  ];
  function trackCta(el, name) {
    el.addEventListener('click', function() {
      if (typeof gtag === 'function') gtag('event', 'cta_click', { source: 'coaching', cta_name: name });
    });
  }
  ctaNames.forEach(function(pair) {
    document.querySelectorAll(pair[0]).forEach(function(el) { trackCta(el, pair[1]); });
  });
  document.querySelectorAll('.gl-coach-tier-cta').forEach(function(el) {
    var m = (el.getAttribute('href') || '').match(/[?&]tier=(min|mid|max)\\b/);
    if (m) trackCta(el, 'tier_' + m[1]);
  });

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

def generate_page(output_dir: Path = None) -> Path:
    """Generate the coaching landing page."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "coaching" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    canonical_url = f"{SITE_BASE_URL}/coaching/"
    title = "1:1 XC Ski Coaching | XC Ski Labs"
    description = (
        "Cross-country ski coaching from me, from roller-ski season to race "
        "day. Three levels, from a weekly review to every session read the "
        "day you upload it. From $199 every 4 weeks."
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
<link rel="icon" type="image/svg+xml" href="/xc-logo.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{esc(canonical_url)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  {og_tags}
  {jsonld}
  <style>{css}</style>
  {XL_GA4_HEAD}
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
