#!/usr/bin/env python3
"""Generate the XC Ski Labs Course sales page at /course/.

Course modules 1 and 2 of the approved course plan (Classic Technique, Skate
Technique), sold alone or as a bundle of every module, plus the shared basics
lessons every buyer gets: 13 lessons today. The course itself is the static
site from glide-labs-platform, served behind the PHP gate at /learn/.

The buy button POSTs to the pipeline's /api/create-course-checkout
(athlete-custom-training-plan-pipeline, webhook/course_access.py). The pipeline
charges on the XC Ski Labs Stripe account only, and Stripe returns the buyer
to /learn/claim. The lesson list and counts below must match
glide-labs-platform/course/content/xc-ski-technique.json;
tests/test_course_page.py pins them.

Not wired into scripts/deploy.py on purpose: this page goes live only after
Matti says yes and /learn/ is deployed.

Usage:
    python wordpress/generate_course.py [--output-dir output] [--api-base URL]
"""

import argparse
import html
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import shutil  # noqa: E402

from generate_about import build_cookie_consent, build_css, build_ga4_snippet  # noqa: E402
from scripts.brand_head import BRAND_FONT_LINKS  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
PRODUCTION_API = "https://athlete-custom-training-plan-pipeline-production.up.railway.app"
CONTACT_EMAIL = "gravelgodcoaching@gmail.com"

COURSE_NAME = "XC Ski Labs Course"
REFUND_DAYS = 14
LEGAL_ENTITY = "Gravel God Cycling LLC"
BUNDLE_PRICE_USD = 49

# Matti, 2026-11-13: modules sell alone at $29; the bundle ($49) is every
# module, including the ones added later. Product ids are the pipeline's
# (webhook/course_access.py COURSES). Counts are pinned to the course JSON by
# tests/test_course_page.py.
PRODUCTS = (
    {"id": "xc-classic", "name": "Classic Technique", "price": 29, "button": "Buy Classic",
     "dek": "Diagonal stride, double pole and kick double pole, and herringbone.",
     "lessons": ("Diagonal Stride", "Double Pole & Kick Double Pole", "Herringbone & Downhills"), "clips": 14},
    {"id": "xc-skate", "name": "Skate Technique", "price": 29, "button": "Buy Skate",
     "dek": "Free skate, V1 and its climbing variations, V2 and V2 alternate.",
     "lessons": ("Free Skate", "V1 & Climbing Variations", "V2 & V2 Alternate"), "clips": 16},
    {"id": "xc-all", "name": "Every module", "price": BUNDLE_PRICE_USD, "button": "Buy every module",
     "dek": "Classic and Skate now, and every module I add to the course later at no extra cost.",
     "lessons": (), "clips": None},
)
BASICS = ("Getting Started", "Finding Your Trails", "Athletic Foundation", "How Snow Works",
          "Downhills & Cornering", "Technique Selection", "Trail Etiquette")
VIDEO_COUNT = 31  # unique filmed clips across the course
LESSON_COUNT = len(BASICS) + sum(len(p["lessons"]) for p in PRODUCTS)


def esc(value) -> str:
    return html.escape(str(value))


def build_nav() -> str:
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


# Sledge Stores (docs/brand/sledge-stores): the crates, tags and checklist
# come from tokens/tokens.css (bundle.css). Only the hero photo and the
# checkout error line need page rules, and both read book tokens.
PAGE_CSS = """
.xc-course { font: 400 17px/1.6 var(--font-body); color: var(--ink); }
.xc-course .xc-band > .xc-wrap > p { max-width: 58ch; }
.xc-hero__photo { margin: 0; align-self: center; border: var(--stroke-stitch) solid var(--ink); }
.xc-hero__photo img { display: block; width: 100%; height: auto; }
.xc-buy-msg { margin: 18px 0 0; font-weight: 600; color: var(--danger); }
.xc-buy-msg:empty { display: none; }
.xc-buy-msg::before { content: "\\26A0\\FE0E  "; }
"""

HERO_PHOTO = "diagonal-stride.jpg"  # a frame of Matti's own diagonal stride clip
HERO_PHOTO_SRC = Path.home() / "glide-labs-platform" / "output" / "learn" / "static" / "img" / "diagonal-stride-hero.jpg"
HERO_PHOTO_FILE = SCRIPT_DIR / "course_media" / HERO_PHOTO


def build_lessons() -> str:
    cols = [("Every buyer gets", BASICS, "")] + [
        (p["name"] + " module", p["lessons"], " xc-list--module") for p in PRODUCTS if p["lessons"]]
    out = []
    for title, lessons, mod in cols:
        items = "".join(f"<li>{esc(name)}</li>" for name in lessons)
        out.append(f'<div class="xc-list{mod}"><h3>{esc(title)}</h3><ul>{items}</ul></div>')
    return '<div class="xc-lists">' + "".join(out) + "</div>"


def stat_line(p: dict) -> str:
    if p["lessons"]:
        return f'{len(p["lessons"])} lessons, {p["clips"]} clips, plus the basics.'
    return "Everything on this page, plus what comes next."


def build_products() -> str:
    """The bundle is the one splash crate (Recommended) and comes first in the source."""
    ordered = sorted(PRODUCTS, key=lambda p: p["lessons"] != ())
    crates = []
    for p in ordered:
        splash = not p["lessons"]
        crates.append(
            f'<li class="xc-crate{" xc-crate--splash" if splash else ""}" id="{esc(p["id"])}">'
            + ('<span class="xc-ribbon">Recommended</span>' if splash else "")
            + f'<div class="xc-crate__in"><h3>{esc(p["name"])}</h3><p class="xc-price">${p["price"]}</p>'
            f'<p class="xc-crate__d">{esc(p["dek"])}</p><span class="xc-tag">{esc(stat_line(p))}</span>'
            f'<button class="xc-btn" type="submit" name="product" value="{esc(p["id"])}" data-price="{p["price"]}" '
            f'data-name="{esc(COURSE_NAME + ": " + p["name"])}">{esc(p["button"])}, ${p["price"]}</button></div></li>')
    return '<ul class="xc-crates">' + "".join(crates) + "</ul>"


def generate_html(api_base: str = PRODUCTION_API) -> str:
    title = f"{COURSE_NAME} | XC Ski Labs"
    description = (f"Classic and skate technique lessons with {VIDEO_COUNT} filmed demos and drills. "
                   f"$29 a module or ${BUNDLE_PRICE_USD} for every module.")
    contact = esc(CONTACT_EMAIL)
    endpoint = esc(api_base.rstrip("/") + "/api/create-course-checkout")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/course/">
  {BRAND_FONT_LINKS}
  {build_ga4_snippet()}
  <style>{build_css()}{PAGE_CSS}</style>
</head>
<body>
<a href="#main" class="gl-skip-link">Skip to content</a>
{build_nav()}
<main class="xc-course" id="main">
  <section class="xc-hero"><div class="xc-hero__in">
    <div><p class="xc-kicker">COURSE</p>
      <h1 class="xc-title">XC Ski Labs <span>Course</span></h1>
      <p class="xc-lede">Cross-country ski lessons for adult skiers, with {VIDEO_COUNT} filmed demos and drills. Buy the module you need or every module. The basics lessons come with any purchase.</p></div>
    <figure class="xc-hero__photo"><img src="{HERO_PHOTO}" alt="Me skiing diagonal stride in the classic tracks" width="1600" height="899" fetchpriority="high"></figure>
  </div></section>

  <section class="xc-band" aria-labelledby="buy-head"><div class="xc-wrap">
    <div class="xc-head"><h2 id="buy-head">Modules</h2></div>
    <form id="course-buy" novalidate>
      {build_products()}
      <p class="xc-buy-msg" role="alert" aria-live="polite"></p>
    </form>
    <p class="xc-fine">One payment each. Full refund within {REFUND_DAYS} days if it isn&rsquo;t for you. Sold by {esc(LEGAL_ENTITY)}; see the <a class="xc-link" href="/terms/">terms</a>.</p>
  </div></section>

  <section class="xc-band xc-band--panel" aria-labelledby="how-head"><div class="xc-wrap">
    <div class="xc-head"><h2 id="how-head">How the lessons work</h2></div>
    <p>I spent years in tight lycra racing cross-country before I ever raced a bike, and roller skied endless miles trying to get fast. Every technique lesson covers body position and timing, with filmed demos, drills you can take onto the snow, and a short quiz at the end.</p>
    <p class="xc-pull">Learning a new technique as an adult is humbling.</p>
    <p>You go from embarrassing to bad, bad to OK, and OK to good, and the drills are how you get through those steps faster.</p>
  </div></section>

  <section class="xc-band" aria-labelledby="lessons-head"><div class="xc-wrap">
    <div class="xc-head"><h2 id="lessons-head">The {LESSON_COUNT} lessons</h2></div>
    {build_lessons()}
    <p class="xc-note">A short quiz follows twelve of the lessons.</p>
  </div></section>

  <section class="xc-band xc-band--panel" aria-labelledby="after-head"><div class="xc-wrap">
    <div class="xc-head"><h2 id="after-head">After you pay</h2></div>
    <ul class="xc-tags">
      <li class="xc-ship"><p>Stripe sends you straight into the course, and I email you a link that opens it on your phone or any other device. If you lose the link, the course page has a box that sends a new one to the email you paid with.</p></li>
      <li class="xc-ship"><p>If you bought one module and want the rest, open a lesson you don&rsquo;t have yet, and you can get every module for ${BUNDLE_PRICE_USD} minus what you already paid.</p></li>
      <li class="xc-ship"><p>If it isn&rsquo;t for you, email {contact} within {REFUND_DAYS} days of buying and I&rsquo;ll refund that purchase in full. Access to what you bought ends after a refund.</p></li>
    </ul>
  </div></section>

  <footer class="gl-footer">XC Ski Labs &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/terms/">Terms</a></footer>
</main>
<script>
(function(){{
  var form=document.getElementById('course-buy');
  var msg=form.querySelector('.xc-buy-msg');
  var btns=form.querySelectorAll('button[name=product]');
  form.addEventListener('submit',function(e){{
    e.preventDefault();
    var btn=e.submitter&&e.submitter.name==='product'?e.submitter:null;
    if(!btn){{msg.textContent='Pick a module or every module.';return;}}
    msg.textContent='';
    btns.forEach(function(b){{b.disabled=true;}});
    fetch('{endpoint}',{{method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{course_id:btn.value}})}})
      .then(function(r){{return r.json().then(function(d){{return {{ok:r.ok,d:d}};}});}})
      .then(function(res){{
        if(res.ok&&res.d.checkout_url){{
          if(window.gtag){{gtag('event','begin_checkout',{{currency:'USD',value:Number(btn.dataset.price),items:[{{item_id:btn.value,item_name:btn.dataset.name}}]}});}}
          window.location.href=res.d.checkout_url;return;
        }}
        msg.textContent=res.d.error||'Checkout did not open. Try again in a minute.';
        btns.forEach(function(b){{b.disabled=false;}});
      }})
      .catch(function(){{msg.textContent='Checkout did not open. Check your connection and try again.';btns.forEach(function(b){{b.disabled=false;}});}});
  }});
}})();
</script>
{build_cookie_consent()}
</body>
</html>"""


def generate_page(output_dir: Path = DEFAULT_OUTPUT_DIR, api_base: str = PRODUCTION_API) -> Path:
    output_path = output_dir / "course" / "index.html"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_html(api_base), encoding="utf-8")
    if not HERO_PHOTO_FILE.exists():
        raise SystemExit(f"{HERO_PHOTO_FILE} is missing; the hero has no photo. Copy it from {HERO_PHOTO_SRC}.")
    shutil.copyfile(HERO_PHOTO_FILE, output_path.parent / HERO_PHOTO)
    print(f"Generated {output_path}")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs course sales page.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--api-base", default=PRODUCTION_API,
                        help="Pipeline base URL (a local pipeline for test-mode runs)")
    args = parser.parse_args()
    generate_page(args.output_dir, args.api_base)


if __name__ == "__main__":
    main()
