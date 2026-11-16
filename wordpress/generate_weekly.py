#!/usr/bin/env python3
"""XC Ski Labs — Weekly sign-up page.

Generates output/weekly/index.html: what the XC Ski Labs Weekly is and the
sign-up form (scripts/newsletter_signup.py). Shares the About page's layout
CSS so the two stay in step.
"""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.consent import get_consent_banner_html, get_ga4_head  # noqa: E402
from scripts.generate_race_pages import build_nav_header as build_canonical_nav_header  # noqa: E402
from scripts.newsletter_signup import newsletter_css, newsletter_form_html  # noqa: E402
from wordpress.generate_about import build_css as about_css  # noqa: E402

PAGE_URL = "https://xcskilabs.com/weekly/"
TITLE = "XC Ski Labs Weekly | XC Ski Labs"
DESCRIPTION = (
    "A once-a-week round-up of cross-country ski news from Norway, Sweden, "
    "Germany and North America, the ski podcast episodes worth hearing, and "
    "a short take from me."
)

# Customer copy, Matti in first person (docs/AI_WRITING_POLICY.md).
H1 = "XC Ski Labs Weekly"
SUB = ("Once a week: the cross-country news worth knowing, the podcast episodes "
       "worth the drive to the trailhead, and a paragraph or two of what I make of it.")
WHATS_IN_IT = (
    "The week&rsquo;s racing, team and federation news from Langrenn.com, NRK, TV 2, "
    "FasterSkier, L&auml;ngd.se and xc-ski.de, translated where needed and boiled down "
    "to a few lines each.",
    "New episodes from ski podcasts like the Devon Kershaw Show and L&aring;ngloppspodden.",
    "My take on the week, kept short.",
    "Every item links to the original story. Read the whole thing there.",
)
FIRST_EMAIL = ("The first email after you sign up asks which race you&rsquo;re training "
               "for. Reply, and I&rsquo;ll write back.")


def build_css() -> str:
    return about_css() + newsletter_css() + """
.xc-weekly-list { margin: 0 0 8px; padding-left: 1.2em; max-width: 62ch; }
.xc-weekly-list li { margin: 0 0 10px; }
.xc-weekly-signup { margin-top: 8px; }
"""


def build_nav_header() -> str:
    return build_canonical_nav_header(active="") + """
<script>
(function(){
  var toggle=document.querySelector('[data-nav-toggle]');
  var links=document.querySelector('.gl-nav-links');
  if(toggle&&links){toggle.addEventListener('click',function(){var open=links.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false')});}
})();
</script>
"""


def generate_html() -> str:
    items = "\n".join(f"      <li>{item}</li>" for item in WHATS_IN_IT)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{TITLE}</title>
  <meta name="description" content="{DESCRIPTION}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{PAGE_URL}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Stencil+Display:wght@700;900&family=Big+Shoulders+Text:wght@600;800&family=Libre+Franklin:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <meta property="og:title" content="{H1}">
  <meta property="og:description" content="{DESCRIPTION}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{PAGE_URL}">
  <meta property="og:site_name" content="XC Ski Labs">
  {get_ga4_head()}
  <style>{build_css()}</style>
</head>
<body>
<a href="#main" class="gl-skip-link">Skip to content</a>
{build_nav_header()}
<main class="gl-page" id="main">
  <section class="gl-hero">
    <p class="gl-kicker">THE WEEKLY</p>
    <h1>{H1}</h1>
    <p class="gl-hero-sub">{SUB}</p>
  </section>

  <section class="gl-section xc-weekly-signup" aria-labelledby="sign-up">
    <h2 class="gl-section-title" id="sign-up">Get it by email</h2>
    {newsletter_form_html("weekly_page")}
    <p>{FIRST_EMAIL}</p>
  </section>

  <section class="gl-section" aria-labelledby="whats-in-it">
    <h2 class="gl-section-title" id="whats-in-it">What&rsquo;s in it</h2>
    <ul class="xc-weekly-list">
{items}
    </ul>
  </section>

  <footer class="gl-footer">XC Ski Labs &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/terms/">Terms</a></footer>
</main>
{get_consent_banner_html()}
</body>
</html>"""


def generate_page(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    output_path = output_dir / "weekly" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(), encoding="utf-8")
    print(f"Generated {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs Weekly sign-up page.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    generate_page(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
