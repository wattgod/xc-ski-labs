#!/usr/bin/env python3
"""Generate the XC Ski Labs privacy policy at /privacy/."""

import argparse
import html
from pathlib import Path

from generate_about import build_cookie_consent, build_css, build_ga4_snippet


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
CONTACT_EMAIL = "gravelgodcoaching@gmail.com"
EFFECTIVE_DATE = "July 2026"


def esc(value: str) -> str:
    return html.escape(value)


def build_nav() -> str:
    """Load the canonical nav through the About page's shared wrapper."""
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
    title = "Privacy Policy | XC Ski Labs"
    description = "Privacy policy for XC Ski Labs and xcskilabs.com."
    contact = esc(CONTACT_EMAIL)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/privacy/">
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
    <h1>Privacy Policy</h1>
    <p class="gl-hero-sub">Effective date: {EFFECTIVE_DATE}</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Scope</h2>
    <p>This Privacy Policy explains how XC Ski Labs (&ldquo;we,&rdquo; &ldquo;us,&rdquo; or &ldquo;our&rdquo;) collects, uses, and shares information when you use xcskilabs.com.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Information we collect</h2>
    <p>We collect information you choose to provide through forms, including your name, email address, race and training information, and coaching-application responses. Coaching applications may include health, injury, and other information you choose to provide for coaching purposes.</p>
    <p>We also collect limited technical information through analytics and cookies, such as pages viewed, referring pages, device or browser information, and approximate location derived from an IP address.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">How we use information</h2>
    <p>We use information to respond to enquiries, review coaching applications, provide requested services, operate and improve the site, measure site use, and meet legal obligations.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Cookies and analytics</h2>
    <p>XC Ski Labs uses cookies to remember your analytics choice and Google Analytics to understand site traffic. Analytics is active by default. You can decline analytics at any time through the site&rsquo;s consent banner; this disables analytics on subsequent page views. Declining analytics does not affect your use of the site.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Information stored in your browser</h2>
    <p>The coaching application saves all draft answers, including health, injury, and medication information, in local storage on your device. Drafts remain on your device without an expiry and are not transmitted to us until you submit the application. You can remove them by clearing this site&rsquo;s data in your browser.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Service providers and sharing</h2>
    <p>We use service providers to operate the site and process requests, including Google Analytics for analytics and FormSubmit for form delivery. If a subscription form links to Substack, Substack processes the information submitted through that form under its own privacy policy.</p>
    <p>We do not sell personal information. We may disclose information when required by law, to protect our rights or safety, or in connection with a business transfer.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Retention and security</h2>
    <p>We retain personal information only for as long as reasonably necessary for the purposes described in this policy, including service delivery, recordkeeping, and legal obligations. No online system is completely secure; please do not submit information you are not comfortable providing electronically.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Your choices</h2>
    <p>You may request access to, correction of, or deletion of personal information we hold about you, subject to applicable law and recordkeeping requirements. You may also decline analytics cookies using the consent banner.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">Changes to this policy</h2>
    <p>We may update this policy from time to time. The effective date above identifies the current version.</p>
  </section>

  <section class="gl-cta-band">
    <h2>Contact</h2>
    <div class="gl-cta-links"><a class="gl-cta-link" href="mailto:{contact}">{contact}</a></div>
  </section>
  <footer class="gl-footer">XC Ski Labs</footer>
</main>
{build_cookie_consent()}
</body>
</html>"""


def generate_page(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Write output/privacy/index.html and return the generated path."""
    output_path = output_dir / "privacy" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(), encoding="utf-8")
    print(f"Generated {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs privacy policy.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    generate_page(args.output_dir)


if __name__ == "__main__":
    main()
