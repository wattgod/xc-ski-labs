#!/usr/bin/env python3
"""Generate the XC Ski Labs Technique Course sales page at /course/.

Course modules 1 and 2 of the approved course plan (Classic Technique, Skate
Technique) plus the shared basics: 13 lessons. The course itself is the static
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

from generate_about import build_cookie_consent, build_css, build_ga4_snippet  # noqa: E402

DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"
PRODUCTION_API = "https://athlete-custom-training-plan-pipeline-production.up.railway.app"
CONTACT_EMAIL = "gravelgodcoaching@gmail.com"

COURSE_ID = "xc-technique"
COURSE_NAME = "XC Ski Labs Technique Course"
PRICE_USD = 49
REFUND_DAYS = 14
LEGAL_ENTITY = "Gravel God Cycling LLC"
VIDEO_COUNT = 31  # unique filmed clips across the 13 lessons

SECTIONS = (
    ("Start here", ("Getting Started", "Finding Your Trails", "Athletic Foundation", "How Snow Works")),
    ("Classic", ("Diagonal Stride", "Double Pole & Kick Double Pole", "Herringbone & Downhills")),
    ("Skate", ("Free Skate", "V1 & Climbing Variations", "V2 & V2 Alternate")),
    ("On the trail", ("Downhills & Cornering", "Technique Selection", "Trail Etiquette")),
)
LESSON_COUNT = sum(len(lessons) for _, lessons in SECTIONS)


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


PAGE_CSS = """
.gl-course-buy { margin: 28px 0 8px; display: grid; gap: 10px; max-width: 420px; }
.gl-course-buy label { font-family: var(--gl-font-data); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; color: var(--gl-slate); }
.gl-course-buy input { font: inherit; padding: 10px 12px; border: 2px solid var(--gl-carbon); background: var(--gl-white); color: var(--gl-carbon); }
.gl-course-buy button { font-family: var(--gl-font-data); font-weight: 700; font-size: 0.875rem; text-transform: uppercase; letter-spacing: 0.06em; padding: 14px 18px; border: 0; background: var(--gl-swix-red); color: var(--gl-white); cursor: pointer; }
.gl-course-buy button:hover { background: var(--gl-klister); }
.gl-course-buy button[disabled] { opacity: 0.6; cursor: wait; }
.gl-course-msg { font-family: var(--gl-font-data); font-size: 0.8125rem; color: var(--gl-red-deep); min-height: 1.2em; }
.gl-course-fine { font-family: var(--gl-font-data); font-size: 0.75rem; color: var(--gl-slate); }
.gl-course-list { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 16px 0 0; }
.gl-course-list h3 { font-family: var(--gl-font-data); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; margin: 0 0 6px; color: var(--gl-slate); }
.gl-course-list ol { margin: 0; padding-left: 1.2em; }
.gl-course-list li { margin: 2px 0; }
.gl-course-stats { font-family: var(--gl-font-data); font-size: 0.8125rem; color: var(--gl-slate); }
"""


def build_lessons() -> str:
    cols = []
    for title, lessons in SECTIONS:
        items = "".join(f"<li>{esc(name)}</li>" for name in lessons)
        cols.append(f'<div><h3>{esc(title)}</h3><ol>{items}</ol></div>')
    return '<div class="gl-course-list">' + "".join(cols) + "</div>"


def generate_html(api_base: str = PRODUCTION_API) -> str:
    title = f"{COURSE_NAME} | XC Ski Labs"
    description = (f"{LESSON_COUNT} classic and skate technique lessons with {VIDEO_COUNT} "
                   f"filmed demos and drills. ${PRICE_USD}, paid once.")
    contact = esc(CONTACT_EMAIL)
    endpoint = esc(api_base.rstrip("/") + "/api/create-course-checkout")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/xc-logo.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/course/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  {build_ga4_snippet()}
  <style>{build_css()}{PAGE_CSS}</style>
</head>
<body>
<a href="#main" class="gl-skip-link">Skip to content</a>
{build_nav()}
<main class="gl-page" id="main">
  <section class="gl-hero">
    <p class="gl-kicker">TECHNIQUE COURSE</p>
    <h1>{esc(COURSE_NAME)}</h1>
    <p class="gl-hero-sub">Classic and skate technique for adult skiers, from your first hour on snow to picking the right gear on a climb. {LESSON_COUNT} lessons, {VIDEO_COUNT} filmed demos and drills, and a short quiz after twelve of them.</p>
    <form class="gl-course-buy" id="course-buy" novalidate>
      <label for="course-email">Email (optional, Stripe asks if you skip it)</label>
      <input id="course-email" name="email" type="email" autocomplete="email">
      <button type="submit">Buy the course, ${PRICE_USD}</button>
      <div class="gl-course-msg" role="alert" aria-live="polite"></div>
      <p class="gl-course-fine">One payment. Full refund within {REFUND_DAYS} days if it isn&rsquo;t for you. Sold by {esc(LEGAL_ENTITY)}; see the <a href="/terms/">terms</a>.</p>
    </form>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">How the lessons work</h2>
    <p>I spent years in tight lycra racing cross-country before I ever raced a bike, and roller skied endless miles trying to get fast. Every technique in this course gets broken into the same three parts: body position, timing, and where the power comes from. Each part has a video and a drill you can take onto the snow.</p>
    <p>Learning a new technique as an adult is humbling. You go from embarrassing to bad, bad to OK, and OK to good, and the drills are how you get through those steps faster.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">The {LESSON_COUNT} lessons</h2>
    {build_lessons()}
    <p class="gl-course-stats">It covers technique. Training plans, strength work and race tactics aren&rsquo;t in this course.</p>
  </section>

  <section class="gl-section">
    <h2 class="gl-section-title">After you pay</h2>
    <p>Stripe sends you straight into the course, and I email you a link that opens it on your phone or any other device. Lost the link? The course page has a box that sends a new one to the email you paid with.</p>
    <p>If the course isn&rsquo;t for you, email <a href="mailto:{contact}">{contact}</a> within {REFUND_DAYS} days of buying and I&rsquo;ll refund the full ${PRICE_USD}. Access ends after a refund.</p>
  </section>

  <footer class="gl-footer">XC Ski Labs &middot; <a href="/privacy/">Privacy</a> &middot; <a href="/terms/">Terms</a></footer>
</main>
<script>
(function(){{
  var form=document.getElementById('course-buy');
  var msg=form.querySelector('.gl-course-msg');
  var btn=form.querySelector('button');
  form.addEventListener('submit',function(e){{
    e.preventDefault();
    msg.textContent='';
    btn.disabled=true;
    var email=(form.email.value||'').trim();
    fetch('{endpoint}',{{method:'POST',headers:{{'Content-Type':'application/json'}},
      body:JSON.stringify({{course_id:'{COURSE_ID}',email:email}})}})
      .then(function(r){{return r.json().then(function(d){{return {{ok:r.ok,d:d}};}});}})
      .then(function(res){{
        if(res.ok&&res.d.checkout_url){{
          if(window.gtag){{gtag('event','begin_checkout',{{currency:'USD',value:{PRICE_USD},items:[{{item_id:'{COURSE_ID}',item_name:'{esc(COURSE_NAME)}'}}]}});}}
          window.location.href=res.d.checkout_url;return;
        }}
        msg.textContent=res.d.error||'Checkout did not open. Try again in a minute.';
        btn.disabled=false;
      }})
      .catch(function(){{msg.textContent='Checkout did not open. Check your connection and try again.';btn.disabled=false;}});
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
