#!/usr/bin/env python3
"""
XC Ski Labs — Consulting Landing Page Generator

Generates the public /consulting/ landing page: a single 60-minute
consult call, sold with a coach's pre-read of the athlete's last six
months of training. Port of Gravel God's Sultanic copy v2
(gravel-race-automation/wordpress/generate_consulting.py, docs/
consulting-copy-v2.md) — same eight-beat structure and verbatim H1 /
close line, with rider/ride vocabulary swapped to skier-neutral
("training" not "riding", "sessions" not "rides", "skis" not "bike")
and the race count read live from web/race-index.json instead of
hardcoded.

Self-contained HTML matching this repo's convention (see
wordpress/generate_coaching.py): tokens.css embedded, nav/footer/GA4/
consent inline, gl- class prefix. Uses --gl-swix-red as the CTA accent
color, same as the coaching intake form (wordpress/
generate_coaching_apply.py) — this is a checkout page, not the
monochrome "still document" that /coaching/ is.

Usage:
    python wordpress/generate_consulting.py
    python wordpress/generate_consulting.py --output-dir output
"""

import html
import json
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"
RACE_INDEX_JSON = PROJECT_ROOT / "web" / "race-index.json"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.generate_race_pages import build_nav_header as build_canonical_nav_header

SITE_BASE_URL = "https://xcskilabs.com"
GA4_ID = "G-3JQLSQLPPM"

CONSULTING_PRICE_INT = 150
CONSULTING_PRICE = f"${CONSULTING_PRICE_INT}"
CONSULTING_DURATION = "60 minutes"
ADDON_PRICE_INT = 100
ADDON_PRICE = f"${ADDON_PRICE_INT}"
BOOKING_URL = "https://calendar.app.google/E282ZtBJAFBXYdYJ6"
CHECKOUT_API = "https://athlete-custom-training-plan-pipeline-production.up.railway.app/api/create-consulting-checkout"
COACHING_URL = f"{SITE_BASE_URL}/coaching/"
PRIVACY_SENTENCE = (
    "Your answers and training data are used only to prepare your consult "
    "and any plan you buy; they aren&rsquo;t shared or sold and are deleted "
    "on request."
)
QUIET_CLAUSE = (
    f'If the consult turns into &ldquo;I want this every week&rdquo; '
    f'&mdash; that&rsquo;s <a href="{COACHING_URL}">coaching</a>.'
)


def load_race_count() -> int:
    """Race count from web/race-index.json — never hardcode (repo pitfall
    #3-adjacent: stat counts drift when the DB changes and the copy doesn't)."""
    if not RACE_INDEX_JSON.exists():
        raise RuntimeError(
            f"Required race index is missing: {RACE_INDEX_JSON}. "
            "Run python scripts/generate_race_index.py before generating consulting."
        )
    data = json.loads(RACE_INDEX_JSON.read_text(encoding="utf-8"))
    return len(data["races"])


# ── Helpers ────────────────────────────────────────────────────

def esc(text) -> str:
    """HTML-escape a string. Safe for None/empty."""
    if text is None or text == "":
        return ""
    return html.escape(str(text))


def _safe_json_for_script(obj, **kwargs) -> str:
    """Serialize obj to JSON safe for embedding inside <script> tags.

    json.dumps does NOT escape '</' sequences, so a string containing
    '</script>' would prematurely close the <script> element. We
    replace '</' with '<\\/' which is valid JSON and safe in HTML.
    (Repo pitfall #4.)
    """
    raw = json.dumps(obj, **kwargs)
    return raw.replace("</", "<\\/")


def load_tokens_css() -> str:
    """Read shared Wax Bench tokens for static embedding."""
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


# ── Nav / Footer ───────────────────────────────────────────────

def build_nav() -> str:
    return build_canonical_nav_header(active="consulting") + """
<script>
(function(){
  var toggle=document.querySelector('[data-nav-toggle]');
  var links=document.querySelector('.gl-nav-links');
  if(toggle&&links){toggle.addEventListener('click',function(){var open=links.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false')});}
})();
</script>"""


def build_footer() -> str:
    return """
<footer class="gl-consult-footer">
  <div class="gl-consult-footer-brand">XC Ski Labs</div>
  <div class="gl-consult-footer-links">
    <a href="/">Home</a>
    <a href="/search/">Search</a>
    <a href="/training-plans/">Training Plans</a>
    <a href="/coaching/">Coaching</a>
    <a href="/consulting/">Consulting</a>
    <a href="/privacy/">Privacy</a>
    <a href="/terms/">Terms</a>
  </div>
  <div class="gl-consult-footer-copy">&copy; 2026 XC Ski Labs. All rights reserved.</div>
</footer>"""


# ── Section builders ─────────────────────────────────────────────

def build_hero() -> str:
    return f'''<section class="gl-consult-hero" id="hero">
    <div class="gl-consult-hero-inner">
      <h1 class="gl-consult-hero-title">The read you can&rsquo;t give yourself.</h1>
      <p class="gl-consult-hero-subtitle">Sixty minutes with a coach who has already been through your last six months of training &mdash; the files, not the summary &mdash; and a written plan of action within 48 hours.</p>
      <div class="gl-consult-hero-price">
        <span class="gl-consult-price-tag">{CONSULTING_PRICE}</span>
        <span class="gl-consult-price-detail">{CONSULTING_DURATION} &middot; your training reviewed before we talk</span>
      </div>
      <form id="checkout" class="gl-consult-form" novalidate>
        <div class="gl-consult-form-row">
          <label class="gl-consult-form-label" for="consult-name">Name</label>
          <input type="text" id="consult-name" name="name" required aria-required="true" placeholder="Your name" autocomplete="name">
        </div>
        <div class="gl-consult-form-row">
          <label class="gl-consult-form-label" for="consult-email">Email</label>
          <input type="email" id="consult-email" name="email" required aria-required="true" placeholder="you@example.com" autocomplete="email">
        </div>
        <div class="gl-consult-form-row gl-consult-form-checkbox-row">
          <label class="gl-consult-checkbox-label" for="consult-addon">
            <input type="checkbox" id="consult-addon" name="plan_addon">
            <span>Add a custom 12-week plan built from the consult (+{ADDON_PRICE})</span>
          </label>
        </div>
        <input type="text" name="_honeypot" style="display:none" tabindex="-1" autocomplete="off">
        <button type="submit" class="gl-consult-form-submit gl-consult-btn-primary" data-cta="hero_book">Book the consult &mdash; {CONSULTING_PRICE}</button>
        <div class="gl-consult-form-message" role="alert" aria-live="polite" style="display:none"></div>
      </form>
    </div>
  </section>'''


def build_two_futures() -> str:
    return f'''<section class="gl-consult-section" id="two-futures">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">Two futures</h2>
      <div class="gl-consult-prose">
        <p>Two ways to spend the next twelve weeks.</p>
        <p>In one, you keep doing what got you here &mdash; the plan off a forum, the intervals you like, the long session you always do &mdash; and hope it adds up by race day.</p>
        <p>In the other, someone who reads ski files for a living has already seen what your last six months actually were, and tells you the one thing that would change the most.</p>
        <p class="gl-consult-prose-emphasis">Same skis. Same hours. Different twelve weeks.</p>
      </div>
    </div>
  </section>'''


def _strip_glyph(kind: str) -> str:
    """Return the inline SVG markup for one how-it-works frame glyph.
    Decorative only — styled entirely via CSS classes (no var() in SVG attrs,
    repo pitfall: SVG attributes can't resolve var())."""
    if kind == "calendar":
        return '''<rect class="gl-consult-strip-glyph-shape" x="-16" y="-14" width="32" height="26"></rect>
      <line class="gl-consult-strip-glyph-shape" x1="-16" y1="-6" x2="16" y2="-6"></line>
      <line class="gl-consult-strip-glyph-shape" x1="-9" y1="-18" x2="-9" y2="-10"></line>
      <line class="gl-consult-strip-glyph-shape" x1="9" y1="-18" x2="9" y2="-10"></line>'''
    if kind == "link":
        return '''<circle class="gl-consult-strip-glyph-shape" cx="-7" cy="-7" r="10"></circle>
      <circle class="gl-consult-strip-glyph-shape" cx="7" cy="7" r="10"></circle>'''
    if kind == "form":
        return '''<rect class="gl-consult-strip-glyph-shape" x="-14" y="-18" width="28" height="36"></rect>
      <line class="gl-consult-strip-glyph-shape" x1="-8" y1="-9" x2="8" y2="-9"></line>
      <line class="gl-consult-strip-glyph-shape" x1="-8" y1="1" x2="8" y2="1"></line>
      <line class="gl-consult-strip-glyph-shape" x1="-8" y1="11" x2="3" y2="11"></line>'''
    if kind == "magnifier":
        return '''<polyline class="gl-consult-strip-glyph-shape" points="-18,10 -8,-6 2,6 12,-10 18,2"></polyline>
      <circle class="gl-consult-strip-glyph-shape gl-consult-strip-glyph-lens" cx="4" cy="-4" r="11"></circle>
      <line class="gl-consult-strip-glyph-shape" x1="12" y1="4" x2="20" y2="12"></line>'''
    if kind == "document":
        return '''<path class="gl-consult-strip-glyph-shape" d="M -12 -18 H 6 L 14 -10 V 18 H -12 Z"></path>
      <path class="gl-consult-strip-glyph-shape" d="M 6 -18 V -10 H 14"></path>
      <line class="gl-consult-strip-glyph-shape" x1="-6" y1="-2" x2="8" y2="-2"></line>
      <line class="gl-consult-strip-glyph-shape" x1="-6" y1="6" x2="8" y2="6"></line>'''
    return ""


def build_how_it_works() -> str:
    frames = [
        ("calendar", "Book.", "Thirty seconds. You get a welcome email with three links.", False),
        ("link", "Connect your TrainingPeaks.", "One click, sign in, tap Accept &mdash; I can now see your training. No TrainingPeaks? Send me your files or a Strava link instead.", False),
        ("form", "Answer twelve questions.", "Your goal event, your hours, the one thing you most want answered. Five minutes.", False),
        ("magnifier", "Your read arrives &mdash; before we talk.", "I go through how you have actually been training, not how you meant to. Then we get on a call and skip the basics.", True),
        ("document", "Sixty minutes, then a written plan of action within 48 hours.", "Specific. Referenced to your own data. Yours to keep.", False),
    ]
    xs = [90, 270, 450, 630, 810]

    svg_frames = ""
    for (kind, _title, _desc, emphasis), x in zip(frames, xs):
        frame_class = "gl-consult-strip-frame gl-consult-strip-frame--emphasis" if emphasis else "gl-consult-strip-frame"
        svg_frames += f'''<g class="{frame_class}" transform="translate({x},50)">
      <circle class="gl-consult-strip-disc" r="26"></circle>
      {_strip_glyph(kind)}
    </g>
    '''

    captions = ""
    for _kind, title, desc, emphasis in frames:
        cap_class = "gl-consult-strip-caption gl-consult-strip-caption--emphasis" if emphasis else "gl-consult-strip-caption"
        captions += f'''<div class="{cap_class}">
      <strong>{title}</strong> {desc}
    </div>
    '''

    return f'''<section class="gl-consult-section" id="how-it-works">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">How it works</h2>
      <div class="gl-consult-strip">
        <svg class="gl-consult-strip-svg" viewBox="0 0 900 100" aria-hidden="true" focusable="false">
          <line class="gl-consult-strip-rail" x1="50" y1="50" x2="850" y2="50"></line>
          {svg_frames}
        </svg>
        <div class="gl-consult-strip-captions">
          {captions}
        </div>
      </div>
    </div>
  </section>'''


def build_what_i_look_at() -> str:
    items = [
        "<strong>How much of your hard training was actually hard.</strong> Long sustained efforts and short surges look the same in a weekly total. They train very different things. I separate them.",
        "<strong>Whether your fitness is climbing, flat, or quietly sliding</strong> &mdash; and how the last three months compare to the same stretch last year.",
        "<strong>Whether your long sessions are getting easier deep in</strong>, or whether the last hour still costs you more than the first.",
        "<strong>When you last tested yourself, and whether the numbers your zones are built on are still true.</strong> Most people&rsquo;s aren&rsquo;t.",
        "<strong>Where your training doesn&rsquo;t match the event you&rsquo;re training for.</strong>",
    ]
    list_items = "\n".join(f'      <li>{item}</li>' for item in items)
    return f'''<section class="gl-consult-section" id="look">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">What I actually look at</h2>
      <ul class="gl-consult-look-list">
{list_items}
      </ul>
      <p class="gl-consult-look-note">You&rsquo;ll get the answers in plain English, with the numbers behind them if you want them.</p>
    </div>
  </section>'''


def build_what_we_cover() -> str:
    topics = [
        "Race selection",
        "Season planning",
        "How your week should be built",
        "Fuelling",
        "Skis and gear choices",
        "Race-day execution",
        "What to do about the thing that keeps going wrong",
    ]
    items = " &middot; ".join(topics)
    return f'''<section class="gl-consult-section" id="cover">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">What we can cover</h2>
      <p class="gl-consult-cover-list">{items}</p>
      <p class="gl-consult-cover-note">Not sure your question fits? It probably does. Book it and ask.</p>
    </div>
  </section>'''


def build_plan_addon() -> str:
    return f'''<section class="gl-consult-section" id="plan">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">The plan, if you want it (+{ADDON_PRICE})</h2>
      <div class="gl-consult-prose">
        <p>Most people leave the call knowing what to change. Some want it built.</p>
        <p><strong>Custom plan add-on &mdash; {ADDON_PRICE}.</strong> A twelve-week plan built from your consult and your data &mdash; not a template with your name on it &mdash; loaded onto your TrainingPeaks calendar within a week of the call, with one round of adjustments in the first fortnight.</p>
        <p>The honest limits: one goal event, up to twelve weeks. If your race is further out, we build the last twelve before it (or the next twelve &mdash; your call). Longer than that is coaching, and I&rsquo;ll say so. Available for seven days after the call; after that it&rsquo;s the store price.</p>
      </div>
    </div>
  </section>'''


def build_who() -> str:
    race_count = load_race_count()
    return f'''<section class="gl-consult-section" id="who">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">Who you&rsquo;ll talk to</h2>
      <div class="gl-consult-bio-text">
        <p>I&rsquo;m Matti. Twelve years at TrainingPeaks, 100+ athletes coached, 1,000+ training plans sold. I&rsquo;ve raced endurance events at a national level and paid for bad pacing enough times to know what it actually costs.</p>
        <p>I built a database of {race_count} cross-country ski races &mdash; terrain, climbing, altitude, how they tend to be won and lost. When you ask &ldquo;which race should I do?&rdquo; or &ldquo;how do I fuel for this one?&rdquo;, the answer comes from that, not from vibes.</p>
      </div>
    </div>
  </section>'''


def build_fit() -> str:
    return f'''<section class="gl-consult-section" id="fit">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">Is this for you?</h2>
      <div class="gl-consult-fit-grid">
        <div class="gl-consult-fit-col gl-consult-fit-for">
          <h3 class="gl-consult-fit-title">For you if</h3>
          <p>you have a goal event and real questions &middot; you&rsquo;ll connect your TrainingPeaks or send files &middot; you want an answer, not reassurance.</p>
        </div>
        <div class="gl-consult-fit-col gl-consult-fit-not">
          <h3 class="gl-consult-fit-title">Not for you if</h3>
          <p>you want a pep talk &middot; you want to be told the plan you&rsquo;re on is fine. (It might be. I&rsquo;ll say so &mdash; and I&rsquo;ll say what isn&rsquo;t.)</p>
        </div>
      </div>
    </div>
  </section>'''


def build_faq() -> str:
    faqs = [
        (
            "What happens after I pay?",
            "A welcome email with three links: pick your time, answer the twelve questions, connect your TrainingPeaks. Do all three and I&rsquo;ll have your read done before we talk.",
        ),
        (
            "I don&rsquo;t use TrainingPeaks.",
            "Reply to the welcome email with a Strava link or your last three months of ski files. Same read, one extra step.",
        ),
        (
            "Do I have to share data?",
            "No &mdash; the call is still worth it. But the read is what makes this different from every other hour you could buy.",
        ),
        (
            "What if I need more than one session?",
            "Book another. Each one stands alone &mdash; no packages, no subscriptions.",
        ),
        (
            "Can I add the plan later?",
            "Yes, for seven days after the call. The offer is in your plan-of-action email.",
        ),
        (
            "What happens to my data?",
            PRIVACY_SENTENCE,
        ),
    ]
    faq_html = ""
    for q, a in faqs:
        faq_html += f'''<div class="gl-consult-faq-item">
      <button class="gl-consult-faq-q" aria-expanded="false">{q}</button>
      <div class="gl-consult-faq-a">{a}</div>
    </div>
'''
    return f'''<section class="gl-consult-section" id="faq">
    <div class="gl-consult-inner">
      <h2 class="gl-consult-section-title">Questions</h2>
      <div class="gl-consult-faqs">
        {faq_html}
      </div>
    </div>
  </section>'''


def build_close() -> str:
    return f'''<section class="gl-consult-cta" id="close">
    <div class="gl-consult-cta-inner">
      <h2 class="gl-consult-cta-title">Less than a race entry. More useful than the forum.</h2>
      <p class="gl-consult-cta-context">You already know what it feels like to start a race unsure the training was right. Sixty minutes to trade that for knowing.</p>
      <p class="gl-consult-cta-desc">{CONSULTING_PRICE} &middot; {CONSULTING_DURATION} &middot; written plan of action included</p>
      <a href="#checkout" class="gl-consult-btn-primary" data-cta="final_book">Book the consult &mdash; {CONSULTING_PRICE}</a>
      <p class="gl-consult-cta-quiet">{QUIET_CLAUSE}</p>
    </div>
  </section>'''


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

a:focus-visible, button:focus-visible, input:focus-visible {
  outline: 2px solid var(--gl-swix-red);
  outline-offset: 2px;
}

/* Shared site navigation (matches wordpress/generate_coaching.py) */
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

/* ── Hero ─────────────────────────────────────── */

.gl-consult-hero {
  padding: 64px 24px 48px;
  background: var(--gl-paper);
  border-bottom: 3px solid var(--gl-carbon);
  text-align: center;
}
.gl-consult-hero-inner {
  max-width: 640px;
  margin: 0 auto;
}
.gl-consult-hero-title {
  font-family: var(--gl-font-editorial);
  font-size: clamp(28px, 5vw, 42px);
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0 0 16px;
  line-height: 1.15;
}
.gl-consult-hero-subtitle {
  font-family: var(--gl-font-editorial);
  font-size: 1.05rem;
  line-height: 1.65;
  color: var(--gl-muted);
  margin: 0 0 24px;
}
.gl-consult-hero-price {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  margin-bottom: 24px;
}
.gl-consult-price-tag {
  font-family: var(--gl-font-data);
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--gl-carbon);
  letter-spacing: 1px;
}
.gl-consult-price-detail {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
}

/* ── Buttons ── */
.gl-consult-btn-primary {
  display: inline-block;
  padding: 15px 40px;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  text-decoration: none;
  color: var(--gl-white);
  background: var(--gl-swix-red);
  border: 3px solid var(--gl-carbon);
  transition: background-color 0.15s, border-color 0.15s;
}
.gl-consult-btn-primary:hover {
  background-color: var(--gl-red-deep);
}

/* ── Sections ── */
.gl-consult-section {
  padding: 48px 0;
  border-bottom: 1px solid var(--gl-hairline);
}
.gl-consult-section:last-of-type { border-bottom: none; }
.gl-consult-inner {
  max-width: var(--gl-prose);
  margin: 0 auto;
  padding: 0 24px;
}
.gl-consult-section-title {
  font-family: var(--gl-font-editorial);
  font-size: clamp(22px, 4vw, 28px);
  font-weight: 700;
  color: var(--gl-carbon);
  margin: 0 0 24px;
  text-align: center;
}

/* ── Prose (Two futures / Plan add-on) ── */
.gl-consult-prose p {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--gl-muted);
  margin: 0 0 16px;
}
.gl-consult-prose p:last-child { margin-bottom: 0; }
.gl-consult-prose-emphasis {
  font-weight: 700;
  color: var(--gl-carbon) !important;
}

/* ── How It Works strip ── */
.gl-consult-strip {
  display: flex;
  flex-direction: column;
  gap: 24px;
}
.gl-consult-strip-svg {
  width: 100%;
  height: auto;
  display: block;
}
.gl-consult-strip-rail {
  stroke: var(--gl-muted);
  stroke-width: 2;
}
.gl-consult-strip-disc {
  fill: var(--gl-paper);
  stroke: var(--gl-carbon);
  stroke-width: 2;
}
.gl-consult-strip-glyph-shape {
  fill: none;
  stroke: var(--gl-carbon);
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.gl-consult-strip-glyph-lens {
  fill: var(--gl-paper);
}
.gl-consult-strip-frame--emphasis .gl-consult-strip-disc {
  fill: var(--gl-klister);
  stroke-width: 3;
}
.gl-consult-strip-frame--emphasis .gl-consult-strip-glyph-shape {
  stroke-width: 3;
}
.gl-consult-strip-captions {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.gl-consult-strip-caption {
  font-family: var(--gl-font-editorial);
  font-size: 0.78rem;
  line-height: 1.5;
  color: var(--gl-muted);
  text-align: center;
}
.gl-consult-strip-caption strong {
  display: block;
  color: var(--gl-carbon);
  margin-bottom: 4px;
}
.gl-consult-strip-caption--emphasis strong {
  color: var(--gl-red-deep);
}

/* ── What I Actually Look At ── */
.gl-consult-look-list {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.gl-consult-look-list li {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--gl-carbon);
  padding-left: 16px;
  border-left: 3px solid var(--gl-swix-red);
}
.gl-consult-look-note {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-muted);
  text-align: center;
  letter-spacing: 0.5px;
  margin: 0;
}

/* ── What We Cover ── */
.gl-consult-cover-list {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--gl-carbon);
  text-align: center;
  margin: 0 0 16px;
}
.gl-consult-cover-note {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-muted);
  text-align: center;
  letter-spacing: 0.5px;
  margin: 0;
}

/* ── FAQ ── */
.gl-consult-faqs {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.gl-consult-faq-item {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-paper);
}
.gl-consult-faq-q {
  display: block;
  width: 100%;
  padding: 16px 20px;
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--gl-carbon);
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  letter-spacing: 0.5px;
}
.gl-consult-faq-a {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.15s;
  padding: 0 20px;
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--gl-muted);
}
.gl-consult-faq-item.open .gl-consult-faq-a {
  max-height: 300px;
  padding-bottom: 16px;
}

/* ── Is This For You ── */
.gl-consult-fit-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}
.gl-consult-fit-col {
  padding: 24px;
  background: var(--gl-paper);
  border-left: 3px solid var(--gl-muted);
}
.gl-consult-fit-for {
  border-left-color: var(--gl-swix-red);
}
.gl-consult-fit-not {
  border-left-color: var(--gl-muted);
}
.gl-consult-fit-title {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 1px;
  color: var(--gl-carbon);
  text-transform: uppercase;
  margin: 0 0 12px;
}
.gl-consult-fit-col p {
  font-family: var(--gl-font-editorial);
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--gl-muted);
  margin: 0;
}

/* ── Close ── */
.gl-consult-cta {
  padding: 64px 24px;
  text-align: center;
  background: var(--gl-carbon);
}
.gl-consult-cta-inner {
  max-width: 640px;
  margin: 0 auto;
}
.gl-consult-cta-title {
  font-family: var(--gl-font-editorial);
  font-size: clamp(22px, 4vw, 28px);
  font-weight: 700;
  color: var(--gl-paper);
  margin: 0 0 12px;
}
.gl-consult-cta-context {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  color: var(--gl-muted);
  margin: 0 0 16px;
}
.gl-consult-cta-desc {
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-muted);
  letter-spacing: 1px;
  text-transform: uppercase;
  margin: 0 0 24px;
}
.gl-consult-cta-quiet {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  color: var(--gl-muted);
  margin: 24px 0 0;
}
.gl-consult-cta-quiet a {
  color: var(--gl-swix-red);
  transition: color 0.15s;
}
.gl-consult-cta-quiet a:hover {
  color: var(--gl-white);
}

/* ── Checkout Form ── */
.gl-consult-form {
  max-width: 440px;
  margin: 24px auto 0;
  text-align: left;
}
.gl-consult-form-row {
  margin-bottom: 16px;
}
.gl-consult-form-label {
  display: block;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: var(--gl-carbon);
  margin-bottom: 6px;
}
.gl-consult-form input[type="text"],
.gl-consult-form input[type="email"] {
  display: block;
  width: 100%;
  padding: 10px 12px;
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  color: var(--gl-carbon);
  background: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  box-sizing: border-box;
}
.gl-consult-form input[type="text"]:focus,
.gl-consult-form input[type="email"]:focus {
  outline: none;
  border-color: var(--gl-swix-red);
}
.gl-consult-form-checkbox-row {
  display: flex;
}
.gl-consult-checkbox-label {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  color: var(--gl-muted);
  cursor: pointer;
}
.gl-consult-checkbox-label input[type="checkbox"] {
  margin-top: 2px;
  flex-shrink: 0;
  accent-color: var(--gl-swix-red);
}
.gl-consult-form-submit {
  width: 100%;
  cursor: pointer;
  margin-top: 8px;
}
.gl-consult-form-submit:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.gl-consult-form-message {
  margin-top: 8px;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  color: var(--gl-muted);
  text-align: center;
}
.gl-consult-form-message.error {
  color: var(--gl-carbon);
  border: 2px solid var(--gl-swix-red);
  padding: 10px 12px;
  background: var(--gl-paper);
}

/* ── Bio ── */
.gl-consult-bio-text p {
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  line-height: 1.65;
  color: var(--gl-muted);
  margin: 0 0 16px;
}
.gl-consult-bio-text p:last-child { margin-bottom: 0; }

/* ── Footer ───────────────────────────────────── */
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

/* ── Cookie Consent ───────────────────────────── */
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

/* ── Responsive ───────────────────────────────── */

@media (max-width: 768px) {
  .gl-consult-fit-grid { grid-template-columns: 1fr; }
  .gl-consult-strip-captions { grid-template-columns: 1fr; }
  .gl-consult-hero { padding: 40px 20px; }
  .gl-consult-inner { padding: 0 20px; }
  .gl-consult-cta { padding: 40px 20px; }
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

@media (max-width: 400px) {
  .gl-consult-hero-title { font-size: 1.5rem; }
}
"""


# ── JS ─────────────────────────────────────────────────────────

def build_cookie_consent() -> str:
    """Cookie consent banner — matches the repo's standard pattern."""
    return """
<div class="gl-consult-cookie-consent" id="gl-consult-cookie-consent">
  <div class="gl-consult-cookie-inner">
    <p class="gl-consult-cookie-text">We use cookies for analytics to improve your experience. You can accept or decline.</p>
    <div class="gl-consult-cookie-buttons">
      <button class="gl-consult-cookie-btn accept" id="gl-consult-cookie-accept">Accept</button>
      <button class="gl-consult-cookie-btn" id="gl-consult-cookie-decline">Decline</button>
    </div>
  </div>
</div>
<script>
(function(){
  var banner=document.getElementById('gl-consult-cookie-consent');
  if(!banner)return;
  if(document.cookie.match(/xl_consent=/)){return;}
  banner.classList.add('visible');
  document.getElementById('gl-consult-cookie-accept').addEventListener('click',function(){
    document.cookie='xl_consent=accepted;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'granted'});gtag('js',new Date());gtag('config','""" + GA4_ID + """');}
  });
  document.getElementById('gl-consult-cookie-decline').addEventListener('click',function(){
    document.cookie='xl_consent=declined;path=/;max-age=31536000;SameSite=Lax';
    banner.classList.remove('visible');
    if(typeof gtag==='function'){gtag('consent','update',{'analytics_storage':'denied'});}
  });
})();
</script>
"""


def build_page_js() -> str:
    """FAQ accordion, CTA/scroll-depth tracking, and the checkout form's
    fetch-based Stripe Checkout handoff. Origin (xcskilabs.com) drives
    backend brand routing on the Railway pipeline — no brand param sent."""
    return f'''
<script>
(function(){{
  /* FAQ accordion */
  document.querySelectorAll('.gl-consult-faq-q').forEach(function(btn){{
    btn.addEventListener('click',function(){{
      var item=btn.parentElement;
      var isOpen=item.classList.contains('open');
      document.querySelectorAll('.gl-consult-faq-item').forEach(function(el){{el.classList.remove('open');el.querySelector('.gl-consult-faq-q').setAttribute('aria-expanded','false')}});
      if(!isOpen){{item.classList.add('open');btn.setAttribute('aria-expanded','true')}}
      if(typeof gtag==='function'){{gtag('event','consulting_faq_open',{{'question':btn.textContent.slice(0,60)}})}}
    }});
  }});
  /* CTA click tracking */
  document.querySelectorAll('[data-cta]').forEach(function(el){{
    el.addEventListener('click',function(){{
      if(typeof gtag==='function'){{gtag('event','cta_click',{{source:'consulting',cta_name:el.getAttribute('data-cta')}})}}
    }});
  }});
  /* Scroll depth */
  if('IntersectionObserver' in window){{
    var fired={{}};
    var map={{'hero':'0_hero','two-futures':'12_two_futures','how-it-works':'25_how_it_works','look':'37_look','cover':'50_cover','plan':'62_plan','who':'75_who','fit':'87_fit','faq':'93_faq','close':'100_close'}};
    var obs=new IntersectionObserver(function(entries){{
      if(!entries.length)return;
      entries.forEach(function(e){{
        if(e.isIntersecting&&!fired[e.target.id]){{
          fired[e.target.id]=true;
          if(typeof gtag==='function'){{gtag('event','consulting_scroll_depth',{{'section':map[e.target.id]||e.target.id}})}}
        }}
      }});
    }},{{'threshold':0.3}});
    Object.keys(map).forEach(function(id){{var el=document.getElementById(id);if(el)obs.observe(el)}});
  }}
  /* Page view */
  if(typeof gtag==='function'){{gtag('event','consulting_page_view')}}

  /* ── Checkout form ── */
  var CHECKOUT_API='{CHECKOUT_API}';
  var CHECKOUT_PRICE={CONSULTING_PRICE_INT};
  var ADDON_PRICE={ADDON_PRICE_INT};
  var CHECKOUT_BTN_LABEL='Book the consult — ${CONSULTING_PRICE_INT}';
  var checkoutForm=document.getElementById('checkout');
  var checkoutMsg=checkoutForm?checkoutForm.querySelector('.gl-consult-form-message'):null;
  var checkoutBtn=checkoutForm?checkoutForm.querySelector('.gl-consult-form-submit'):null;
  var checkoutSubmitting=false;

  function showCheckoutError(msg){{
    checkoutMsg.className='gl-consult-form-message error';
    checkoutMsg.textContent=msg;
    checkoutMsg.style.display='block';
    checkoutBtn.disabled=false;
    checkoutBtn.textContent=CHECKOUT_BTN_LABEL;
    checkoutSubmitting=false;
    if(typeof gtag==='function'){{gtag('event','consulting_checkout_error',{{error:msg}})}}
  }}

  if(checkoutForm){{
    checkoutForm.addEventListener('submit',function(e){{
      e.preventDefault();
      if(checkoutSubmitting)return;
      var nameVal=checkoutForm.querySelector('input[name="name"]').value.trim();
      var emailVal=checkoutForm.querySelector('input[name="email"]').value.trim();
      var honeypot=checkoutForm.querySelector('input[name="_honeypot"]').value;
      var addonInput=checkoutForm.querySelector('input[name="plan_addon"]');
      var planAddon=addonInput?addonInput.checked:false;
      if(honeypot)return;
      if(!nameVal||!emailVal){{
        showCheckoutError('Please fill in your name and email.');
        return;
      }}
      if(!/^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/.test(emailVal)){{
        showCheckoutError('Please enter a valid email address.');
        return;
      }}
      checkoutSubmitting=true;
      checkoutBtn.disabled=true;
      checkoutBtn.textContent='Preparing checkout...';
      checkoutMsg.style.display='none';

      if(typeof gtag==='function'){{gtag('event','begin_checkout',{{currency:'USD',value:planAddon?CHECKOUT_PRICE+ADDON_PRICE:CHECKOUT_PRICE,items:[{{item_name:'Consulting Session'}}],plan_addon:planAddon}})}}

      fetch(CHECKOUT_API,{{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify({{name:nameVal,email:emailVal,hours:1,plan_addon:planAddon}})
      }})
      .then(function(r){{
        if(!r.ok)throw new Error('Server error ('+r.status+'). Please try again.');
        return r.json();
      }})
      .then(function(result){{
        if(result.checkout_url){{
          window.location.href=result.checkout_url;
        }}else{{
          throw new Error(result.error||'Failed to create checkout session');
        }}
      }})
      .catch(function(err){{
        showCheckoutError(err.message||'Something went wrong. Please try again.');
      }});
    }});
  }}

  /* Smooth scroll for #checkout links */
  document.querySelectorAll('a[href="#checkout"]').forEach(function(link){{
    link.addEventListener('click',function(e){{
      e.preventDefault();
      var target=document.getElementById('checkout');
      if(target){{target.scrollIntoView({{behavior:'smooth',block:'center'}});target.querySelector('input[name="name"]').focus()}}
    }});
  }});
}})();
</script>'''


def build_jsonld() -> str:
    """WebPage + Service JSON-LD, serialized via the safe-json helper."""
    webpage = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": "Consulting | XC Ski Labs",
        "description": "Sixty minutes with a coach who has already read your last six months of training, plus a written plan of action.",
        "url": f"{SITE_BASE_URL}/consulting/",
        "isPartOf": {
            "@type": "WebSite",
            "name": "XC Ski Labs",
            "url": SITE_BASE_URL,
        },
    }
    service = {
        "@context": "https://schema.org",
        "@type": "Service",
        "name": "XC Ski Consulting",
        "provider": {
            "@type": "Organization",
            "name": "XC Ski Labs",
            "url": SITE_BASE_URL,
        },
        "description": "One-on-one cross-country ski consulting: a coach's read of your last six months of training, plus a written plan of action.",
        "offers": {
            "@type": "Offer",
            "price": str(CONSULTING_PRICE_INT),
            "priceCurrency": "USD",
            "description": "60-minute 1-on-1 video consultation with written plan of action",
        },
        "url": f"{SITE_BASE_URL}/consulting/",
    }
    wp_tag = f'<script type="application/ld+json">{_safe_json_for_script(webpage, separators=(",", ":"))}</script>'
    svc_tag = f'<script type="application/ld+json">{_safe_json_for_script(service, separators=(",", ":"))}</script>'
    return f'{wp_tag}\n  {svc_tag}'


# ── Page assembly ─────────────────────────────────────────────

def generate_page(output_dir: Path = None) -> Path:
    """Generate the consulting landing page."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    out_path = output_dir / "consulting" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    canonical_url = f"{SITE_BASE_URL}/consulting/"
    title = "Consulting | XC Ski Labs"
    description = (
        "Sixty minutes with a coach who has already read your last six "
        f"months of training. {CONSULTING_PRICE} with a written plan of "
        "action within 48 hours."
    )

    nav = build_nav()
    hero = build_hero()
    two_futures = build_two_futures()
    how = build_how_it_works()
    look = build_what_i_look_at()
    cover = build_what_we_cover()
    plan = build_plan_addon()
    who = build_who()
    fit = build_fit()
    faq = build_faq()
    close = build_close()
    footer = build_footer()
    consent = build_cookie_consent()
    page_js = build_page_js()
    jsonld = build_jsonld()
    css = build_css()

    og_tags = f'''<meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{esc(canonical_url)}">
  <meta property="og:site_name" content="XC Ski Labs">
  <meta name="twitter:card" content="summary">
  <meta name="twitter:title" content="{esc(title)}">
  <meta name="twitter:description" content="{esc(description)}">'''

    page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{esc(canonical_url)}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600;8..60,700&display=swap" rel="stylesheet">
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' fill='%23141414'/><text x='16' y='24' text-anchor='middle' font-family='monospace' font-size='22' font-weight='700' fill='%23f2f0eb'>GL</text></svg>">
  {og_tags}
  {jsonld}
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

<div class="gl-consult-page">

  {hero}

  {two_futures}

  {how}

  {look}

  {cover}

  {plan}

  {who}

  {fit}

  {faq}

  {close}

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

    parser = argparse.ArgumentParser(description="Generate XC Ski Labs consulting landing page")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Output directory (default: project output/)")
    args = parser.parse_args()

    out = generate_page(output_dir=args.output_dir)
    print(f"Generated: {out}")
    print(f"  Size: {out.stat().st_size:,} bytes")
