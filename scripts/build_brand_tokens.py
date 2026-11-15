#!/usr/bin/env python3
"""Build tokens/tokens.css from the Sledge Stores brand book.

Source of truth: docs/brand/sledge-stores/tokens.json (colour, type, spacing,
radius, stroke) and docs/brand/sledge-stores/components/bundle.css (the
component rules). Every page generator embeds tokens/tokens.css, and the
component previews in the book link it, so the site and the previews read the
same variables.

    python3 scripts/build_brand_tokens.py           # write tokens/tokens.css
    python3 scripts/build_brand_tokens.py --check   # exit 1 if it is stale

What it writes:
  * Book variables under their book names (--ground, --ink, --font-label,
    --space-5, --stroke-stitch ...), Wool values on :root and Fjord values
    under [data-theme="dark"]. bundle.css and the previews use these names.
  * The raw values of both themes as --xc-light-<name> / --xc-dark-<name>.
  * The legacy --gl-* names the page templates still use, each pointed at a
    book token (LEGACY below). They are pinned to Wool: the templates use
    --gl-ink both as text and as a dark fill, so they cannot follow a theme.
  * The component rules from bundle.css (its font @import removed; pages load
    the fonts with BRAND_FONT_LINKS from scripts/brand_head.py).

Not built: Fjord following prefers-color-scheme on the live site. The legacy
templates would turn half-dark, so the site stays on Wool; Fjord is reachable
only with data-theme="dark" (the previews).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOK = ROOT / "docs" / "brand" / "sledge-stores"
TOKENS_JSON = BOOK / "tokens.json"
BUNDLE_CSS = BOOK / "components" / "bundle.css"
OUT = ROOT / "tokens" / "tokens.css"
# The /learn/ course (wattgod/glide-labs-platform) vendors this file as its
# brand layer: book tokens and component rules only, without the legacy --gl-*
# names and site shims, whose .gl-* selectors would hit the course's own blocks.
COURSE_OUT = ROOT / "tokens" / "course-brand.css"
# The search page is static HTML; it carries a copy of tokens.css between
# these markers, rewritten by this script.
SEARCH_HTML = ROOT / "web" / "nordic-lab-search.html"
BEGIN = "/* BRAND TOKENS:BEGIN (scripts/build_brand_tokens.py writes this block) */\n"
END = "/* BRAND TOKENS:END */\n"

# Legacy template name -> book token. Pinned to the Wool value.
# Mapping rules (README §2, §3): ink does the work, so the old rust spot and
# its hover shades become ink; the old ochre accent sat on dark fields, so it
# becomes the strap's text colour; snow/white and paper are the wool ground;
# hairlines are oat; support inks fold into ink-2 and done.
LEGACY_COLOURS = {
    "paper": "ground",
    "ink": "ink",
    "rust": "ink",
    "rust-deep": "ink-2",
    "ochre": "on-strap",
    "slate": "ink-2",
    "pine": "done",
    "snow": "ground",
    "rule": "panel",
    "caption": "ink-2",
    "carbon": "ink",
    "swix-red": "ink",
    "red-deep": "ink-2",
    "klister": "on-strap",
    "wax-green": "done",
    "wax-blue": "ink-2",
    "wax-violet": "rule",
    "white": "ground",
    "hairline": "panel",
    "muted": "ink-2",
}
LEGACY_FONTS = {
    "font-display": "label",
    "font-data": "label",
    "font-editorial": "body",
    "font-ui": "body",
}

HEX = re.compile(r"^#[0-9a-fA-F]{6}([0-9a-fA-F]{2})?$")


def load_tokens(path: Path = TOKENS_JSON) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _colour_rows(tokens: dict) -> list[tuple[str, str, str]]:
    rows = []
    for tok in tokens["color"]["tokens"]:
        light, dark = tok["value"]["light"], tok["value"]["dark"]
        for v in (light, dark):
            if not HEX.match(v):
                raise ValueError(f"{tok['name']}: not a hex colour: {v!r}")
        rows.append((tok["name"], light.lower(), dark.lower()))
    return rows


def _type_vars(tokens: dict) -> list[str]:
    lines = []
    for key, stack in tokens["type"]["families"].items():
        lines.append(f"  --font-{key}: {stack};")
    for group in tokens["type"]["groups"]:
        for style in group["styles"]:
            n = style["name"]
            lines.append(f"  --type-{n}-family: var(--font-{group['family']});")
            lines.append(f"  --type-{n}-size: {style['fontSize']};")
            lines.append(f"  --type-{n}-line-height: {style['lineHeight']};")
            lines.append(f"  --type-{n}-weight: {style['fontWeight']};")
            if "letterSpacing" in style:
                lines.append(f"  --type-{n}-tracking: {style['letterSpacing']};")
    return lines


def _scale_vars(tokens: dict) -> list[str]:
    lines = []
    for section in ("spacing", "radius", "stroke"):
        for tok in tokens[section]["tokens"]:
            lines.append(f"  --{tok['name']}: {tok['value']};")
    return lines


def _bundle_rules() -> str:
    css = BUNDLE_CSS.read_text(encoding="utf-8")
    # The URL itself contains semicolons (wght@700;900), so match the whole
    # url("...") and its closing ");" rather than stopping at the first ";".
    css = re.sub(r'^@import\s+url\("[^"]*"\);[ \t]*\n?', "", css, flags=re.M)
    if "@import" in css or not css.lstrip().startswith("/*"):
        raise ValueError("bundle.css: could not strip the font @import cleanly")
    if HEX.search(css) or re.search(r"#[0-9a-fA-F]{3,8}\b", css):
        raise ValueError("bundle.css carries a hex literal; colours must read a token")
    return css.strip()


SITE_RULES = """\
/* Site-wide: the canvas weave on the page ground (README §2). html body
   outranks each template's own body background shorthand. */
html body {
  background-image:
    repeating-linear-gradient(0deg, var(--weave) 0 1px, transparent 1px 4px),
    repeating-linear-gradient(90deg, var(--weave) 0 1px, transparent 1px 4px);
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { transition: none !important; animation: none !important; }
}

/* Legacy --gl-muted sits on both wool and the navy strap. Dark modules get
   the Fjord secondary-text value until the templates use book tokens. */
:where(.gl-nav, .gl-nav-header, .gl-coach-nav, .gl-hero,
       .gl-ladder, .gl-cookie-banner, .gl-cookie-consent,
       .gl-consult-cookie-consent, .gl-consult-footer, .gl-coach-footer) {
  --gl-muted: var(--xc-dark-ink-2);
  --gl-caption: var(--xc-dark-ink-2);
}

/* Content bands the old templates filled with ink. Navy belongs to the
   header and footer straps only (README §2, §4), so these become oat panels
   with navy text: inside them the legacy dark-field names point at the
   panel and ink. Straps (.gl-nav, footers, sticky CTA) are not listed. */
:where(.gl-hero, .gl-verdict, .gl-transition, .gl-ladder,
       .gl-final-cta, .gl-coach-band--dark, .gl-consult-cta,
       .gl-confirmed-crosssell, .gl-cta-band) {
  --gl-carbon: var(--xc-light-panel);
  --gl-ink: var(--xc-light-panel);
  --gl-white: var(--xc-light-ink);
  --gl-snow: var(--xc-light-ink);
  --gl-paper: var(--xc-light-ink);
  --gl-klister: var(--xc-light-ink);
  --gl-ochre: var(--xc-light-ink);
  --gl-muted: var(--xc-light-ink-2);
  --gl-caption: var(--xc-light-ink-2);
  --gl-caption-on-dark: var(--xc-light-ink-2);
  --gl-hairline: var(--xc-light-ink);
  --gl-rule: var(--xc-light-ink);
}
/* html body :is() so the 6px rules outrank each template's own band border. */
html body :is(.gl-hero, .gl-verdict, .gl-transition, .gl-ladder, .gl-final-cta,
       .gl-coach-band--dark, .gl-consult-cta,
       .gl-confirmed-crosssell, .gl-cta-band) {
  border-top: var(--stroke-band) solid var(--ink);
  border-bottom: var(--stroke-band) solid var(--ink);
}

/* Filled objects inside those bands (the score box, primary buttons) keep
   the action pair: a navy slab with wool text. */
:where(.gl-hero, .gl-verdict, .gl-transition, .gl-ladder,
       .gl-final-cta, .gl-coach-band--dark, .gl-consult-cta,
       .gl-confirmed-crosssell, .gl-cta-band)
  :where(.gl-scorebox, .gl-rung-btn.apply, .gl-cta-btn:not(.gl-cta-btn--outline),
         .gl-capture-btn, .gl-process-num, .gl-course-buy button, .gl-consult-btn-primary) {
  --gl-carbon: var(--xc-light-action);
  --gl-ink: var(--xc-light-action);
  --gl-swix-red: var(--xc-light-action);
  --gl-rust: var(--xc-light-action);
  --gl-white: var(--xc-light-on-action);
  --gl-snow: var(--xc-light-on-action);
  --gl-paper: var(--xc-light-on-action);
  --gl-klister: var(--xc-light-on-action);
  --gl-muted: var(--xc-dark-ink-2);
}
/* Light cards that sit inside a band keep the Wool mapping. */
:where(.gl-hero, .gl-verdict, .gl-transition, .gl-ladder,
       .gl-final-cta, .gl-coach-band--dark, .gl-consult-cta,
       .gl-confirmed-crosssell, .gl-cta-band)
  :where(.gl-course-product) {
  --gl-carbon: var(--xc-light-ink);
  --gl-ink: var(--xc-light-ink);
  --gl-white: var(--xc-light-ground);
  --gl-snow: var(--xc-light-ground);
  --gl-paper: var(--xc-light-ground);
  --gl-muted: var(--xc-light-ink-2);
  --gl-caption: var(--xc-light-ink-2);
  --gl-hairline: var(--xc-light-panel);
}
/* The race page's transition band was filled with the old rust spot. */
.gl-transition { background-color: var(--panel) !important; }
/* The coaching hero sat on the page ground; the book's hero is a panel
   with an ink edge, and its one call to action is the action slab. */
.gl-coach-hero { background-color: var(--panel); border-bottom: var(--stroke-band) solid var(--ink) !important; }
.gl-coach-hero .gl-coach-hero-cta { background: var(--action); color: var(--on-action); border: var(--stroke-button) solid var(--action); text-decoration: none;
  box-shadow: inset 0 calc(-1 * var(--stroke-underline)) 0 var(--splash) !important; }
.gl-coach-hero .gl-coach-hero-cta:hover { background: var(--ground); color: var(--ink); border-color: var(--ink); }

/* Primary buttons carry the salmon underline (README §2, Button). */
/* html body :is() so it outranks each template's universal shadow reset. */
html body :is(.gl-rung-btn.apply, .gl-cta-btn:not(.gl-cta-btn--outline), .gl-course-buy button,
       .gl-consult-btn-primary) {
  box-shadow: inset 0 calc(-1 * var(--stroke-underline)) 0 var(--splash) !important;
}
/* The old poster decoration: diagonal hero shapes and tilted badges.
   Nothing rotates but shipping tags (README §5); no decoration beyond the
   objects (README §9). */
.gl-hero::after, .gl-hero::before { content: none !important; }
.gl-scorebox { transform: none !important; }

/* Focus (README §7, §12): 3px ring, 3px offset. Navy on wool and oat; the
   strap's text colour on navy straps; footers and the privacy strip use their
   own text colour, which the contrast scan holds against their ground. */
html body :focus-visible { outline: var(--stroke-button) solid var(--focus) !important; outline-offset: 3px !important; }
html body :is(.xc-strap, .gl-nav, .gl-nav-header, .gl-coach-nav, [class~="pk-nav"], .gl-sticky-cta,
              .gl-coach-sticky-cta, [class~="xl-consent-banner"]) :focus-visible { outline-color: var(--on-strap) !important; }
html body :is(footer, .gl-footer, .gl-coach-footer, .gl-consult-footer) :focus-visible,
html body [class~="xl-privacy-choices"]:focus-visible { outline-color: currentColor !important; }
html body .xc-crate--splash :focus-visible { outline-color: var(--on-splash) !important; }

/* Controls take the page's faces instead of the browser's default
   (README §3); zero specificity, so any template font rule still wins. */
:where(button, input, select, textarea) { font-family: inherit; }

/* Boxed CTA links keep their box on hover, not a prose underline. */
html body .gl-cta-link:hover { text-decoration: none; }

/* Lockup in the old nav markup: mark 44px, XC SKI LABS in Big Shoulders
   Text 800, 22px, tracked .2em, 12px gap (README §8). */
/* Every nav sits on a strap: the wordmark is on-strap. */
:is(.gl-nav, .gl-nav-header, .gl-coach-nav) .gl-nav-logo,
:is(.gl-nav, .gl-nav-header, .gl-coach-nav) .gl-nav-logo:hover { color: var(--on-strap); }
.gl-nav-logo { display: inline-flex; align-items: center; gap: 12px; white-space: nowrap; }
.gl-nav-logo .gl-brand-mark { display: block; width: 44px; height: 44px; flex: none; }
.gl-nav-logo .gl-brand-mark svg { display: block; width: 100%; height: 100%; }
.gl-nav-logo .gl-brand-name { font-family: var(--font-label); font-weight: 800; font-style: normal; font-size: 22px; letter-spacing: .2em; line-height: 1; text-transform: uppercase; }
.gl-nav-logo .gl-brand-name em { color: inherit; font-style: normal; }
@media (max-width: 520px) {
  .gl-nav-logo .gl-brand-name { font-size: 19px; }
  .gl-nav-logo .gl-brand-mark { width: 36px; height: 36px; }
}"""


def _root_blocks(tokens: dict, rows: list, legacy: list[str]) -> list[str]:
    out = [":root {", "  color-scheme: light;", "  /* Raw theme values */"]
    for name, light, dark in rows:
        out.append(f"  --xc-light-{name}: {light};")
        out.append(f"  --xc-dark-{name}: {dark};")
    out.append("  /* Book tokens, Wool */")
    for name, _, _ in rows:
        out.append(f"  --{name}: var(--xc-light-{name});")
    out += _type_vars(tokens)
    out += _scale_vars(tokens)
    out += legacy
    out += ["}", "", '/* Fjord. Only on data-theme="dark"; see the module docstring. */',
            ':root[data-theme="dark"] {', "  color-scheme: dark;"]
    for name, _, _ in rows:
        out.append(f"  --{name}: var(--xc-dark-{name});")
    out.append("}")
    return out


def build_course_css(tokens: dict | None = None) -> str:
    """Book tokens and bundle.css for the /learn/ course: no legacy names, no site rules."""
    tokens = tokens or load_tokens()
    out = [
        "/* XC Ski Labs brand layer for the /learn/ course: Sledge Stores · Splash on wool.",
        "   GENERATED by xc-ski-labs scripts/build_brand_tokens.py from",
        "   docs/brand/sledge-stores/tokens.json and components/bundle.css.",
        "   Do not edit by hand; edit the book, rebuild, and copy it into the course. */",
    ]
    out += _root_blocks(tokens, _colour_rows(tokens), [])
    out += ["", "/* Components: docs/brand/sledge-stores/components/bundle.css */", _bundle_rules(), ""]
    return "\n".join(out)


def build_css(tokens: dict | None = None) -> str:
    tokens = tokens or load_tokens()
    rows = _colour_rows(tokens)
    names = {name for name, _, _ in rows}
    for legacy, target in LEGACY_COLOURS.items():
        if target not in names:
            raise ValueError(f"legacy --gl-{legacy} points at unknown token {target!r}")
    families = tokens["type"]["families"]
    for legacy, target in LEGACY_FONTS.items():
        if target not in families:
            raise ValueError(f"legacy --gl-{legacy} points at unknown family {target!r}")

    out = [
        "/* XC Ski Labs design tokens: Sledge Stores · Splash on wool.",
        "   GENERATED by scripts/build_brand_tokens.py from",
        "   docs/brand/sledge-stores/tokens.json and components/bundle.css.",
        "   Do not edit by hand; edit the book and rebuild. */",
        ":root {",
        "  color-scheme: light;",
        "  /* Raw theme values */",
    ]
    for name, light, dark in rows:
        out.append(f"  --xc-light-{name}: {light};")
        out.append(f"  --xc-dark-{name}: {dark};")
    out.append("  /* Book tokens, Wool */")
    for name, _, _ in rows:
        out.append(f"  --{name}: var(--xc-light-{name});")
    out += _type_vars(tokens)
    out += _scale_vars(tokens)
    out.append("  /* Legacy template names, pinned to Wool */")
    for legacy, target in LEGACY_COLOURS.items():
        out.append(f"  --gl-{legacy}: var(--xc-light-{target});")
    out.append("  --gl-caption-on-dark: var(--xc-dark-ink-2);")
    for legacy, target in LEGACY_FONTS.items():
        out.append(f"  --gl-{legacy}: var(--font-{target});")
    out += [
        "  --gl-measure: 1200px;",
        "  --gl-prose: 58ch;",
    ]
    for i, tok in enumerate(tokens["spacing"]["tokens"], start=1):
        out.append(f"  --gl-space-{i}: {tok['value']};")
    out += [
        "  --gl-rule-width: 3px;",
        "  --gl-motion-quick: 150ms;",
        "  --gl-motion-normal: 200ms;",
        "  --gl-motion-ease: ease-out;",
        "}",
        "",
        '/* Fjord. Only on data-theme="dark"; see the module docstring. */',
        ':root[data-theme="dark"] {',
        "  color-scheme: dark;",
    ]
    for name, _, _ in rows:
        out.append(f"  --{name}: var(--xc-dark-{name});")
    out += ["}", "", SITE_RULES, "", "/* Components: docs/brand/sledge-stores/components/bundle.css */", _bundle_rules(), ""]
    return "\n".join(out)


def with_search_block(html: str, css: str) -> str:
    start = html.index(BEGIN) + len(BEGIN)
    end = html.index(END, start)
    return html[:start] + css + html[end:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if tokens/tokens.css is stale")
    args = parser.parse_args(argv)
    css = build_css()
    course_css = build_course_css()
    search = SEARCH_HTML.read_text(encoding="utf-8")
    new_search = with_search_block(search, css)
    if args.check:
        stale = [p.relative_to(ROOT).as_posix() for p, ok in (
            (OUT, OUT.read_text(encoding="utf-8") == css),
            (COURSE_OUT, COURSE_OUT.exists() and COURSE_OUT.read_text(encoding="utf-8") == course_css),
            (SEARCH_HTML, search == new_search),
        ) if not ok]
        if stale:
            print(f"stale: {', '.join(stale)}; run python3 scripts/build_brand_tokens.py", file=sys.stderr)
            return 1
        print("tokens/tokens.css, tokens/course-brand.css and the search page token block are current")
        return 0
    OUT.write_text(css, encoding="utf-8")
    COURSE_OUT.write_text(course_css, encoding="utf-8")
    SEARCH_HTML.write_text(new_search, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}, {COURSE_OUT.relative_to(ROOT)} and the token block in {SEARCH_HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
