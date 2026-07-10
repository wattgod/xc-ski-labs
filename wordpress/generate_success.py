#!/usr/bin/env python3
"""Generate the quiet Stripe success page at /thanks/."""

from __future__ import annotations

import argparse
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"


def load_tokens_css() -> str:
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


def build_page() -> str:
    css = load_tokens_css() + """
*, *::before, *::after {
  box-sizing: border-box;
  border-radius: 0 !important;
  box-shadow: none !important;
}
body {
  margin: 0;
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-editorial);
  line-height: 1.6;
}
.gl-nav {
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-swix-red);
  padding: 14px 24px;
}
.gl-nav a {
  font-family: var(--gl-font-data);
  color: var(--gl-white);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-weight: 700;
  font-size: 0.85rem;
}
.gl-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 72px 20px;
}
.gl-kicker {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-swix-red);
  letter-spacing: 0.12em;
  text-transform: uppercase;
  margin-bottom: 14px;
}
h1 {
  font-family: var(--gl-font-display);
  font-size: clamp(2.4rem, 8vw, 5rem);
  font-style: italic;
  font-weight: 900;
  line-height: 0.96;
  text-transform: uppercase;
  margin: 0 0 24px;
}
p {
  max-width: 54ch;
  font-size: 1.15rem;
  margin: 0 0 28px;
}
.gl-button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  background: var(--gl-carbon);
  color: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  padding: 12px 18px;
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-decoration: none;
}
"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Payment Received | XC Ski Labs</title>
  <meta name="robots" content="noindex, follow">
  <link rel="canonical" href="https://xcskilabs.com/thanks/">
  <style>{css}</style>
</head>
<body>
  <nav class="gl-nav"><a href="/">XC SKI LABS</a></nav>
  <main class="gl-page">
    <div class="gl-kicker">Wax Bench</div>
    <h1>Payment received.</h1>
    <p>Check your email — plan details usually within a day.</p>
    <a class="gl-button" href="/training-plans/">Back to plans</a>
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate XC Ski Labs success page")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()
    out_dir = Path(args.output_dir) / "thanks"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "index.html"
    out_file.write_text(build_page(), encoding="utf-8")
    print(f"Generated: {out_file}")


if __name__ == "__main__":
    main()
