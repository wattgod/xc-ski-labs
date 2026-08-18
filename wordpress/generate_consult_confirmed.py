#!/usr/bin/env python3
"""
XC Ski Labs — Consulting Confirmation Page Generator (/consulting/confirmed/)

Post-checkout landing page for the consulting product. Three steps:
pick a time on the booking calendar, start the intake (the checkout
session_id is passed to the intake link as a URL-fragment `ref` so the
submission can be tied back to the order — the intake AUTH token
itself only ever arrives via the welcome email), and connect
TrainingPeaks. Also carries the plan add-on reminder and the quiet
coaching clause.

Port of Gravel God's consulting confirmation content (Sultanic copy
v2, gravel-race-automation/wordpress/generate_success_pages.py::
build_consulting_success + build_success_js) — this repo has no
existing multi-product success-page framework (compare wordpress/
generate_success.py, which is a single Stripe /thanks/ page for
training-plan purchases only), so this is a dedicated single-purpose
generator rather than a port of that whole PAGES-dict architecture.

Usage:
    python wordpress/generate_consult_confirmed.py
    python wordpress/generate_consult_confirmed.py --output-dir output
"""

import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from generate_consulting import (
    SITE_BASE_URL,
    GA4_ID,
    BOOKING_URL,
    ADDON_PRICE,
    COACHING_URL,
    QUIET_CLAUSE,
    load_tokens_css,
    build_nav,
    build_footer,
    build_cookie_consent,
)

TRAININGPEAKS_ATTACH_URL = "https://home.trainingpeaks.com/attachtocoach?sharedKey=2OTEPC6BXNVQU"


# ── Page sections ─────────────────────────────────────────────

def build_hero() -> str:
    return '''<div class="gl-confirmed-hero" data-product-type="consulting">
    <div class="gl-confirmed-check">&check;</div>
    <h1>Booked. Three things, then I get to work.</h1>
    <p>Do all three and your read will be done before we talk.</p>
  </div>'''


def build_steps() -> str:
    return f'''<div class="gl-confirmed-steps">
    <h2>What happens next</h2>
    <div class="gl-confirmed-step">
      <div class="gl-confirmed-step-num">1</div>
      <div class="gl-confirmed-step-text">
        <h3>Pick Your Time</h3>
        <p><a href="{BOOKING_URL}" class="gl-confirmed-cta" target="_blank" rel="noopener" data-cta="schedule_session">Pick a Time</a></p>
      </div>
    </div>
    <div class="gl-confirmed-step">
      <div class="gl-confirmed-step-num">2</div>
      <div class="gl-confirmed-step-text">
        <h3>Start the Intake</h3>
        <p><a href="/consulting/intake/" id="consult-intake-link" class="gl-confirmed-cta" data-cta="start_intake">Start the Intake</a></p>
        <p>Five minutes; you can save and come back. If this page can&rsquo;t open it, use the link in your welcome email instead.</p>
      </div>
    </div>
    <div class="gl-confirmed-step">
      <div class="gl-confirmed-step-num">3</div>
      <div class="gl-confirmed-step-text">
        <h3>Connect Your TrainingPeaks</h3>
        <p><a href="{TRAININGPEAKS_ATTACH_URL}" class="gl-confirmed-cta" target="_blank" rel="noopener" data-cta="connect_trainingpeaks">Connect</a></p>
        <p>One click, sign in, tap Accept &mdash; or reply to the welcome email with a Strava link or ski files.</p>
      </div>
    </div>
  </div>'''


def build_crosssell() -> str:
    return f'''<div class="gl-confirmed-crosssell">
    <h2>Want the Plan Built Too?</h2>
    <p>A twelve-week plan from your consult, on your calendar within a week of the call &mdash; {ADDON_PRICE}, available for seven days after we speak. Reply to your welcome email to add it.</p>
  </div>

  <div class="gl-confirmed-crosssell">
    <p class="gl-confirmed-quiet">{QUIET_CLAUSE}</p>
  </div>'''


# ── CSS ────────────────────────────────────────────────────────

def build_css() -> str:
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
  outline: 2px solid var(--gl-swix-red);
  outline-offset: 2px;
}

/* Shared site navigation (matches wordpress/generate_consulting.py) */
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

/* ── Confirmed page ───────────────────────────── */

.gl-confirmed-hero {
  padding: 64px 24px 48px;
  text-align: center;
  background: var(--gl-paper);
  border-bottom: 3px solid var(--gl-carbon);
}
.gl-confirmed-hero h1 {
  font-family: var(--gl-font-editorial);
  font-size: clamp(24px, 5vw, 34px);
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0 0 12px;
}
.gl-confirmed-hero p {
  font-family: var(--gl-font-editorial);
  font-size: 1rem;
  color: var(--gl-muted);
  max-width: 500px;
  margin: 0 auto;
  line-height: 1.6;
}
.gl-confirmed-check {
  display: inline-block;
  width: 56px;
  height: 56px;
  border: 3px solid var(--gl-swix-red);
  color: var(--gl-swix-red);
  font-size: 1.6rem;
  line-height: 50px;
  text-align: center;
  margin-bottom: 20px;
}
.gl-confirmed-steps {
  padding: 48px 24px;
  max-width: 640px;
  margin: 0 auto;
}
.gl-confirmed-steps h2 {
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1.5px;
  color: var(--gl-muted);
  margin: 0 0 24px;
}
.gl-confirmed-step {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  align-items: flex-start;
}
.gl-confirmed-step-num {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border: 2px solid var(--gl-carbon);
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-carbon);
  text-align: center;
  line-height: 28px;
}
.gl-confirmed-step-text h3 {
  font-family: var(--gl-font-editorial);
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0 0 8px;
}
.gl-confirmed-step-text p {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-muted);
  margin: 0 0 6px;
  line-height: 1.55;
}
.gl-confirmed-cta {
  display: inline-block;
  padding: 12px 24px;
  background: var(--gl-swix-red);
  color: var(--gl-white);
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  text-decoration: none;
  border: 3px solid var(--gl-carbon);
  transition: background-color 0.15s;
}
.gl-confirmed-cta:hover {
  background: var(--gl-red-deep);
}
.gl-confirmed-crosssell {
  padding: 40px 24px;
  background: var(--gl-carbon);
  text-align: center;
  border-top: 1px solid var(--gl-hairline);
}
.gl-confirmed-crosssell h2 {
  font-family: var(--gl-font-editorial);
  font-size: 1.3rem;
  font-weight: 700;
  color: var(--gl-paper);
  margin: 0 0 12px;
}
.gl-confirmed-crosssell p {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-muted);
  max-width: 480px;
  margin: 0 auto;
  line-height: 1.6;
}
.gl-confirmed-quiet {
  font-size: 0.75rem !important;
}
.gl-confirmed-quiet a {
  color: var(--gl-swix-red);
  transition: color 0.15s;
}
.gl-confirmed-quiet a:hover {
  color: var(--gl-white);
}

/* ── Footer (matches wordpress/generate_consulting.py) ── */
.gl-consult-footer {
  background: var(--gl-carbon);
  color: var(--gl-muted);
  padding: 32px 24px;
  border-top: 1px solid var(--gl-hairline);
  text-align: center;
}
.gl-consult-footer-brand {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-white);
  text-transform: uppercase;
  letter-spacing: 2px;
}
.gl-consult-footer-links {
  margin-top: 12px;
  display: flex;
  justify-content: center;
  gap: 20px;
  flex-wrap: wrap;
}
.gl-consult-footer-links a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.gl-consult-footer-links a:hover { color: var(--gl-white); }
.gl-consult-footer-copy {
  font-family: var(--gl-font-data);
  font-size: 0.65rem;
  color: var(--gl-muted);
  margin-top: 16px;
}

/* ── Cookie Consent (matches wordpress/generate_consulting.py) ── */
.gl-consult-cookie-consent {
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
.gl-consult-cookie-consent.visible { display: block; }
.gl-consult-cookie-inner {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.gl-consult-cookie-text {
  font-family: var(--gl-font-editorial);
  font-size: 0.85rem;
  color: var(--gl-white);
  flex: 1;
  min-width: 200px;
}
.gl-consult-cookie-buttons { display: flex; gap: 10px; }
.gl-consult-cookie-btn {
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
.gl-consult-cookie-btn.accept { background: var(--gl-white); color: var(--gl-carbon); }

@media (max-width: 640px) {
  .gl-confirmed-hero { padding: 48px 16px 32px; }
  .gl-confirmed-steps { padding: 32px 16px; }
  .gl-confirmed-crosssell { padding: 32px 16px; }
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
"""


# ── JS ─────────────────────────────────────────────────────────

def build_page_js() -> str:
    """GA4 purchase event + session_id extraction. Passes the checkout
    session_id to the intake link as a fragment ref so the intake
    submission can be tied back to the order — the intake AUTH token
    itself only ever arrives via the welcome email."""
    return """<script>
(function() {
  var params = new URLSearchParams(window.location.search);
  var sessionId = params.get('session_id') || '';
  var productType = document.querySelector('[data-product-type]');
  var ptype = productType ? productType.getAttribute('data-product-type') : 'unknown';

  if (typeof gtag === 'function') {
    gtag('event', 'purchase', {
      transaction_id: sessionId,
      product_type: ptype,
    });
    gtag('event', 'success_page_view', {
      product_type: ptype,
      session_id: sessionId,
    });
  }

  if (sessionId && typeof sessionStorage !== 'undefined') {
    sessionStorage.setItem('xl_converted_' + sessionId, '1');
  }

  var intakeLink = document.getElementById('consult-intake-link');
  if (intakeLink && sessionId) {
    intakeLink.href = '/consulting/intake/#ref=' + encodeURIComponent(sessionId);
  }

  var ctas = document.querySelectorAll('[data-cta]');
  ctas.forEach(function(cta) {
    cta.addEventListener('click', function() {
      if (typeof gtag === 'function') {
        gtag('event', 'cta_click', {
          source: 'consulting_confirmed',
          cta_name: cta.getAttribute('data-cta'),
        });
      }
    });
  });
})();
</script>"""


# ── Page assembly ─────────────────────────────────────────────

def generate_page(output_dir: Path = None) -> Path:
    """Generate the consulting confirmation page."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "consulting" / "confirmed" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    canonical_url = f"{SITE_BASE_URL}/consulting/confirmed/"
    title = "Session Confirmed | XC Ski Labs"
    description = "Your consulting session is confirmed."

    nav = build_nav()
    hero = build_hero()
    steps = build_steps()
    crosssell = build_crosssell()
    footer = build_footer()
    consent = build_cookie_consent()
    css = build_css()
    page_js = build_page_js()

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="{canonical_url}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
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

<div class="gl-confirmed-page">
  {hero}
  {steps}
  {crosssell}
</div>

{footer}

{consent}

{page_js}

</body>
</html>"""

    out_path.write_text(page_html, encoding="utf-8")
    return out_path


# ── CLI ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate XC Ski Labs consulting confirmation page")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Output directory (default: project output/)")
    args = parser.parse_args()

    out = generate_page(output_dir=args.output_dir)
    print(f"Generated: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")
