#!/usr/bin/env python3
"""Generate the XC Ski Labs not-found page at /404.html.

web/.htaccess points ErrorDocument 404 at it, so a dead link lands on a
branded page with a way back instead of the host's stock 404.
"""

import argparse
from pathlib import Path

from generate_about import build_cookie_consent, build_css, build_ga4_snippet
from generate_terms import build_nav

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

LINKS = (
    ("/search/", "Search the races"),
    ("/guide/", "Read the guide"),
    ("/training-plans/", "Training plans"),
    ("/", "Home"),
)


def generate_html() -> str:
    links = "".join(f'<a class="gl-cta-link" href="{href}">{label}</a>' for href, label in LINKS)
    # Absolute asset and link paths only: the server returns this page for
    # any missing URL, at any depth.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/xc-logo.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page not found | XC Ski Labs</title>
  <meta name="robots" content="noindex">
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
    <p class="gl-kicker">404</p>
    <h1>That page isn&rsquo;t here</h1>
    <p class="gl-hero-sub">The link may be old, or the race may have moved. Every race I rate is in the search.</p>
  </section>
  <section class="gl-cta-band">
    <h2>Where to next</h2>
    <div class="gl-cta-links">{links}</div>
  </section>
  <footer class="gl-footer">XC Ski Labs &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/terms/">Terms</a></footer>
</main>
{build_cookie_consent()}
</body>
</html>"""


def generate_page(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Write output/404.html and return its path."""
    output_path = output_dir / "404.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(), encoding="utf-8")
    print(f"Generated {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs 404 page.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    generate_page(parser.parse_args().output_dir)


if __name__ == "__main__":
    main()
