#!/usr/bin/env python3
"""XC Ski Labs — About Page Generator.

Generates the static /about/ page into output/about/index.html.
"""

import argparse
import html
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "race-data"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"


def esc(text: Any) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


def count_race_profiles(data_dir: Path = DEFAULT_DATA_DIR) -> int:
    """Count race JSON files, excluding the schema file."""
    return len([f for f in data_dir.glob("*.json") if f.name != "_schema.json"])


def load_tokens_css() -> str:
    """Read shared Wax Bench tokens for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


def build_css() -> str:
    """Build CSS using the race-page design tokens."""
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

.gl-skip-link {
  position: absolute;
  top: -80px;
  left: 16px;
  z-index: 10000;
  padding: 10px 14px;
  background: var(--gl-swix-red);
  color: var(--gl-white);
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  text-decoration: none;
  letter-spacing: 0.06em;
}
.gl-skip-link:focus { top: 16px; }

.gl-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 20px 80px;
}

/* Nav */
.gl-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-swix-red);
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
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-logo:hover { color: var(--gl-hairline); }
.gl-nav-links {
  display: flex;
  align-items: center;
  gap: 0;
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
.gl-nav-item > a:hover,
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
.gl-nav-dropdown a:hover {
  color: var(--gl-white);
  background: var(--gl-swix-red);
}
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

/* Page */
.gl-hero {
  background: var(--gl-carbon);
  color: var(--gl-paper);
  padding: 64px 32px 56px;
  border-bottom: 3px solid var(--gl-swix-red);
}
.gl-kicker {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--gl-swix-red);
  margin: 0 0 16px;
}
.gl-hero h1 {
  font-family: var(--gl-font-editorial);
  font-size: 2.6rem;
  font-weight: 700;
  line-height: 1.1;
  margin: 0 0 20px;
  max-width: 720px;
}
.gl-hero-sub {
  font-size: 1.08rem;
  color: var(--gl-muted);
  max-width: 680px;
  margin: 0;
}
.gl-section {
  padding: 48px 0;
  border-bottom: 1px solid var(--gl-hairline);
}
.gl-section-title {
  font-family: var(--gl-font-editorial);
  font-size: 1.55rem;
  font-weight: 700;
  line-height: 1.25;
  margin: 0 0 16px;
}
.gl-section p {
  font-size: 1rem;
  color: var(--gl-muted);
  max-width: 680px;
  margin: 0 0 14px;
}
.gl-data-line {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--gl-carbon);
  text-transform: uppercase;
}
.gl-text-link {
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.gl-cta-band {
  background: var(--gl-carbon);
  color: var(--gl-paper);
  padding: 32px;
  border-top: 3px solid var(--gl-swix-red);
}
.gl-cta-band h2 {
  font-family: var(--gl-font-editorial);
  font-size: 1.55rem;
  margin: 0 0 18px;
}
.gl-cta-links {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.gl-cta-link {
  display: inline-flex;
  align-items: center;
  min-height: 44px;
  padding: 10px 18px;
  border: 2px solid var(--gl-white);
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.gl-cta-link:hover {
  background: var(--gl-white);
  color: var(--gl-carbon);
}
.gl-footer {
  padding: 28px 0 0;
  text-align: center;
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

/* Cookie Consent */
.gl-cookie-consent {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: var(--gl-carbon);
  border-top: 3px solid var(--gl-swix-red);
  padding: 20px;
  display: none;
}
.gl-cookie-consent.visible { display: block; }
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
  color: var(--gl-white);
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
  border: 2px solid var(--gl-white);
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  min-width: 44px;
  min-height: 44px;
}
.gl-cookie-btn.accept {
  background: var(--gl-swix-red);
  color: var(--gl-white);
}
.gl-cookie-btn.decline {
  background: transparent;
  color: var(--gl-white);
}

@media (max-width: 640px) {
  .gl-hero {
    padding: 44px 20px 40px;
  }
  .gl-hero h1 {
    font-size: 1.9rem;
  }
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
  .gl-nav-hamburger { display: block; }
  .gl-nav-dropdown {
    position: static;
    border: none;
    padding: 0 0 0 16px;
    display: block;
  }
  .gl-nav-item > a { padding: 12px 0; }
  .gl-cta-band { padding: 28px 20px; }
}
"""


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


def build_nav_header() -> str:
    """Sticky top nav bar with About marked active."""
    return """
<nav class="gl-nav">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo">XC SKI LABS</a>
    <button class="gl-nav-hamburger" aria-label="Toggle navigation" onclick="document.querySelector('.gl-nav-links').classList.toggle('open')">&#9776;</button>
    <ul class="gl-nav-links">
      <li class="gl-nav-item">
        <a href="/search/">Races</a>
        <div class="gl-nav-dropdown">
          <a href="/search/">All XC Ski Races</a>
        </div>
      </li>
      <li class="gl-nav-item">
        <a href="/training-plans/">Products</a>
        <div class="gl-nav-dropdown">
          <a href="/training-plans/">Training Plans</a>
        </div>
      </li>
      <li class="gl-nav-item">
        <a href="/coaching/apply/">Services</a>
        <div class="gl-nav-dropdown">
          <a href="/coaching/apply/">Coaching</a>
        </div>
      </li>
      <li class="gl-nav-item">
        <a href="/about/" class="active">About</a>
      </li>
    </ul>
  </div>
</nav>
"""


def generate_html(race_count: int) -> str:
    """Generate the complete About page HTML."""
    title = "About | XC Ski Labs"
    description = (
        "XC Ski Labs is an independent database of cross-country ski race "
        "reviews, scored by hand across consistent criteria."
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/about/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://xcskilabs.com/about/">
  <meta property="og:site_name" content="XC Ski Labs">
  {build_ga4_snippet()}
  <style>{build_css()}</style>
</head>
<body>
<a href="#main" class="gl-skip-link">Skip to content</a>
{build_nav_header()}
<main class="gl-page" id="main">
  <section class="gl-hero">
    <p class="gl-kicker">ABOUT</p>
    <h1>Race intel for a sport that deserves it.</h1>
    <p class="gl-hero-sub">XC ski race information is scattered across organizer pages, registration sites, local forums, and old results PDFs. Organizer marketing is useful, but it is not a review.</p>
  </section>

  <section class="gl-section" aria-labelledby="what-this-is">
    <h2 class="gl-section-title" id="what-this-is">What this is</h2>
    <p class="gl-data-line">{esc(race_count)} races scored on 14 criteria, ranked into four tiers, by hand.</p>
  </section>

  <section class="gl-section" aria-labelledby="how-scored">
    <h2 class="gl-section-title" id="how-scored">How it's scored</h2>
    <p>Each race is scored across 14 criteria on a 1-5 scale, then converted to a 100-point overall score. Tiers follow the scoring system used across the race database: T1 at 80 and above, T2 at 60 and above, T3 at 45 and above, and T4 below 45, with prestige adjustments where the scoring rules support them.</p>
    <a class="gl-text-link" href="/search/">Search the database</a>
  </section>

  <section class="gl-section" aria-labelledby="behind-it">
    <h2 class="gl-section-title" id="behind-it">Who's behind it</h2>
    <p>XC Ski Labs is built by Matti Rowe, a National-level racer with 12 years at TrainingPeaks who coaches endurance athletes across gravel, road, and ski.</p>
    <p>The work carries over from <a href="https://gravelgodcycling.com/">Gravel God Cycling</a>: independent race pages, practical context, and a preference for useful detail over event copy.</p>
  </section>

  <section class="gl-cta-band" aria-labelledby="next">
    <h2 id="next">Work with the same system.</h2>
    <div class="gl-cta-links">
      <a class="gl-cta-link" href="/training-plans/">Training plans</a>
      <a class="gl-cta-link" href="/coaching/apply/">Coaching application</a>
    </div>
  </section>

  <footer class="gl-footer">XC Ski Labs</footer>
</main>
{build_cookie_consent()}
</body>
</html>"""


def generate_page(data_dir: Path = DEFAULT_DATA_DIR, output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Write output/about/index.html and return the generated path."""
    race_count = count_race_profiles(data_dir)
    output_path = output_dir / "about" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(race_count), encoding="utf-8")
    print(f"Generated {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs about page.")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    generate_page(args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()
