#!/usr/bin/env python3
"""Generate the XC Ski Labs terms of service at /terms/."""

import argparse
import html
from datetime import date
from pathlib import Path

from generate_about import build_cookie_consent, build_css, build_ga4_snippet


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
CONTACT_EMAIL = "gravelgodcoaching@gmail.com"


def esc(value: str) -> str:
    return html.escape(value)


def build_nav() -> str:
    """Load the canonical site navigation."""
    from scripts.generate_race_pages import build_nav_header

    return build_nav_header() + """
<script>
(function(){
  var toggle=document.querySelector('[data-nav-toggle]');
  var links=document.querySelector('.gl-nav-links');
  if(toggle&&links){toggle.addEventListener('click',function(){var open=links.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false')});}
})();
</script>
"""


def generate_html() -> str:
    title = "Terms of Service | XC Ski Labs"
    description = "Terms governing use of XC Ski Labs, xcskilabs.com, and its services."
    contact = esc(CONTACT_EMAIL)
    effective_date = date.today().strftime("%B %Y")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/terms/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  {build_ga4_snippet()}
  <style>{build_css()}</style>
</head>
<body>
<a href="#main" class="gl-skip-link">Skip to content</a>
{build_nav()}
<main class="gl-page" id="main">
  <section class="gl-hero">
    <p class="gl-kicker">LEGAL</p>
    <h1>Terms of Service</h1>
    <p class="gl-hero-sub">Effective date: {effective_date}</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Agreement</h2>
    <p>These terms govern your use of xcskilabs.com and the race information, training plans, coaching, consulting, and related services offered through XC Ski Labs. By using the site or purchasing a service, you agree to these terms. If you do not agree, do not use the site or services.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Race information</h2>
    <p>Race profiles, ratings, comparisons, prep kits, and course descriptions are independent editorial content based on publicly available information and community research. XC Ski Labs is not affiliated with, endorsed by, or officially connected to a race organizer or governing body unless a page expressly says otherwise.</p>
    <p>Dates, routes, entry rules, conditions, and event details change. Confirm material decisions with the official organizer before you register, travel, purchase equipment, or race.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Training and coaching</h2>
    <p>Training plans, coaching, consulting, and educational content provide general fitness guidance. They are not medical care, diagnosis, or a guarantee of performance. Exercise carries risk. Consult an appropriate medical professional before beginning or changing a program, especially if you have an injury, health condition, symptoms, or concerns about your ability to train safely.</p>
    <p>You are responsible for deciding whether to perform a workout and for adjusting or stopping when conditions, equipment, health, or safety require it.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Purchases, delivery, and refunds</h2>
    <p>Prices, billing cadence, included services, and delivery terms are shown on the applicable offer or checkout page. Payments are processed by third-party payment providers. You agree to provide accurate billing and delivery information.</p>
    <p>If a service is not delivered as described or you believe a charge is incorrect, contact <a href="mailto:{contact}">{contact}</a>. Any offer-specific cancellation or refund terms shown before purchase form part of these terms.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Acceptable use</h2>
    <p>You may use the site for personal, lawful purposes. You may not interfere with the site, attempt unauthorized access, submit malicious material, scrape the site in a way that disrupts service, or reproduce, resell, or republish substantial portions of its content without written permission.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Intellectual property</h2>
    <p>Except where otherwise noted, the site&rsquo;s original text, ratings, training materials, graphics, code, and design are owned by XC Ski Labs or its operator. Race names, organizer marks, and third-party materials remain the property of their respective owners.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Third-party services and links</h2>
    <p>The site may link to organizers, payment processors, email providers, analytics services, calendars, and other third parties. Their products, availability, policies, and content are outside our control. A link does not imply endorsement.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Disclaimers and liability</h2>
    <p>The site and services are provided on an &ldquo;as is&rdquo; and &ldquo;as available&rdquo; basis to the extent permitted by law. We do not promise that every page will be error-free, complete, or continuously available.</p>
    <p>To the extent permitted by law, XC Ski Labs and its operator are not liable for indirect, incidental, or consequential losses arising from use of the site or services, including race outcomes, travel decisions, equipment choices, or injuries. Nothing in these terms excludes liability that cannot legally be excluded.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Changes</h2>
    <p>We may update these terms as the site and services change. The effective date above identifies the current version. Continued use after an update means you accept the revised terms.</p>
  </section>

  <section class="gl-cta-band">
    <h2>Questions?</h2>
    <div class="gl-cta-links"><a class="gl-cta-link" href="mailto:{contact}">{contact}</a></div>
  </section>
  <footer class="gl-footer">XC Ski Labs &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/terms/">Terms</a></footer>
</main>
{build_cookie_consent()}
</body>
</html>"""


def generate_page(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Write output/terms/index.html and return the generated path."""
    output_path = output_dir / "terms" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(), encoding="utf-8")
    print(f"Generated {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs terms of service.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    generate_page(args.output_dir)


if __name__ == "__main__":
    main()
