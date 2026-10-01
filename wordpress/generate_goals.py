#!/usr/bin/env python3
"""Generate the XC Ski Labs season-goal lead page at /goals/.

Ski version of Gravel God's /goals/ funnel (gravel-race-automation
wordpress/generate_season_review.py, GOAL_2027 variant): a fifteen-minute
questionnaire that ends in a hand-drawn goal poster (canvas, drawn in the
browser) for the 2026-27 ski season, plus a step-two offer beneath the
results screen. Training numbers are never asked; there is no FTP here to
ask for in the first place.

Season framing: today (site build time) sits between seasons. "2025-26" is
the season that just ended (the loppets already skied); "2026-27" is the
season the goal is for (the one that opens in November). See docs/brand
copy rule: no exclamation marks, flat register, one clean verdict per line.

Submission goes straight to the shared, already multi-brand Cloudflare
worker (fueling-lead-intake) with brand=xcskilabs — the same worker Gravel
God's and Roadie Labs' goal pages use. Mission Control stores the answers,
mints a poster token, and renders/emails the poster
(mission_control/services/goal_poster.py, brand-aware as of this build).
There is no email backstop here (worker-only transport): XC Ski Labs has no
FormSubmit endpoint wired for this page, and Mission Control is already the
record.

Offer: XC Ski Labs has no live self-serve checkout (verified against the
current site and data/stripe-products.json — Stripe products/prices exist,
but every training-plans CTA still routes to the manual, coach-mediated
/questionnaire/ intake, same as every other purchase path on this site
today). The offer below points there rather than to a payment link that
does not exist.

Usage:
    python wordpress/generate_goals.py
    python wordpress/generate_goals.py --output-dir ./output
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"

LAST_SEASON = "2025-26"
NEXT_SEASON = "2026-27"

# The shared, already multi-brand lead-intake worker (also used by Gravel
# God and Roadie Labs). It already knows the "goal_2027" source and the
# "xcskilabs" brand; no worker change is needed for this page.
LEAD_WORKER_URL = "https://fueling-lead-intake.gravelgodcoaching.workers.dev"
LEAD_SOURCE = "goal_2027"
BRAND = "xcskilabs"
CONTACT_EMAIL = "coaching@xcskilabs.com"


def esc(text: Any) -> str:
    if text is None or text == "":
        return ""
    return html.escape(str(text), quote=True)


def _safe_json_for_script(obj: Any, **kwargs: Any) -> str:
    return json.dumps(obj, **kwargs).replace("</", "<\\/")


def load_tokens_css() -> str:
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


def _token_hex(name: str) -> str:
    """Resolve one --gl-* custom property's literal hex value out of
    tokens/tokens.css, for the one spot (a <canvas> 2D context) that can't
    reference a CSS custom property directly. Brand tokens stay the single
    source of truth for color, per CLAUDE.md's "never hardcode hex" rule."""
    import re as _re
    match = _re.search(rf"--{_re.escape(name)}:\s*(#[0-9A-Fa-f]{{3,8}})", load_tokens_css())
    if not match:
        raise ValueError(f"token --{name} not found in tokens.css")
    return match.group(1)


# ── Question set (ski version of GG's GOAL_2027 variant) ──────────────
# Six required sections, same shape and doctrine as the original: judge
# last season against the goal actually set, one measurable goal, and name
# an inner obstacle with an if-then plan. Plus the same six optional
# "go deeper" modules, for the obsessive.

AREAS = [
    ("endurance", "Aerobic base / endurance"),
    ("threshold", "Threshold and intervals"),
    ("technique_classic", "Classic technique"),
    ("technique_skate", "Skate technique"),
    ("strength", "Strength and core"),
    ("dryland", "Dryland / roller skiing"),
    ("recovery", "Recovery and sleep"),
    ("nutrition", "Fueling and nutrition"),
    ("race_execution", "Race-day execution and pacing"),
]

FAULTS = [
    "Trains through illness or injury",
    "All intensity, no easy days",
    "Skips technique work for volume",
    "Obsesses over gear instead of training",
    "Quits when it stops being fun",
    "Never tests, just assumes",
    "Overtrains when motivated, does nothing when not",
]

STRENGTHS = [
    "Shows up in bad weather",
    "Never misses a long day",
    "Recovers fast",
    "Executes the plan as written",
    "Grinds through boredom well",
    "Picks up technique quickly",
]

DEAD_HABIT_REASONS = [
    ("no_time", "No time"),
    ("forgot_why", "Forgot why it mattered"),
    ("got_boring", "Got boring"),
    ("injury", "Injury or pain"),
    ("life", "Life got in the way"),
    ("no_partner", "Lost my training partner"),
]


def _module(key: str, title: str, minutes: str, fields: list[dict]) -> dict:
    return {"key": key, "title": title, "minutes": minutes, "fields": fields}


SECTIONS: list[dict] = [
    {"title": "Who Are You Again", "fields": [
        {"name": "name", "kind": "text", "label": "Name", "req": True, "auto": "name"},
        {"name": "email", "kind": "email", "label": "Email", "req": True, "auto": "email"},
    ]},
    {"title": "The Highlight Reel", "sub": "Not the Strava version. The one you&#39;d tell at the wax bench.", "fields": [
        {"name": "proudest", "kind": "area", "rows": 3, "req": True,
         "label": f"What are you proudest of from the {LAST_SEASON} season?"},
        {"name": "last_goal", "kind": "text", "req": True, "label": "What did you say you&#39;d do this year?",
         "ph": "The goal you wrote down in November, not the one you&#39;ve since decided you meant"},
        {"name": "last_goal_result", "kind": "radio", "req": True, "label": "And?",
         "options": [("hit", "Nailed it"), ("close", "Close"), ("missed", "Missed"),
                     ("dropped", "Quietly abandoned"), ("none", "Never set one")],
         "lift": {"when": "none", "fields": ["last_goal", "last_goal_why"]}},
        {"name": "last_goal_why", "kind": "text", "req": True, "label": "What decided it?",
         "ph": "Bad snow only explains so much"},
    ]},
    {"title": "The Blooper Reel", "sub": "Do you double up, spiral, or quietly disappear?", "fields": [
        {"name": "hardest", "kind": "area", "rows": 3, "req": True,
         "label": "Worst moment of the season. How much of it was on you?",
         "ph": "Some of it, probably. That&#39;s the good news. It means you can fix it."},
        {"name": "missed_workout", "kind": "radio", "req": True, "label": "When you miss a planned session, you&hellip;",
         "options": [("make_up", "Make it up", "Even if it wrecks the next two days"),
                     ("move_on", "Move on", "One session won&#39;t matter"),
                     ("guilt", "Feel guilty", "Beat myself up, eventually let it go"),
                     ("spiral", "Spiral", "Start questioning the whole plan"),
                     ("disappear", "Quietly disappear", "Go dark for a week and hope nobody notices")]},
        {"name": "competing_wants", "kind": "text", "req": True,
         "label": "What do you love that&#39;s quietly making you slower?",
         "ph": "e.g., Staying out for one more loop when you needed sleep"},
    ]},
    {"title": NEXT_SEASON, "sub": "&ldquo;Ski more&rdquo; isn&#39;t a goal. It&#39;s a direction.", "fields": [
        {"name": "outcome_goal", "kind": "text", "req": True,
         "label": f"By the end of the {NEXT_SEASON} season, I will&hellip;",
         "ph": "Measurable. If it can&#39;t fail, it&#39;s not a goal, it&#39;s a vibe."},
        {"name": "outcome_measure", "kind": "text", "req": True, "label": "How will we know you did it?"},
        {"name": "outcome_scary", "kind": "radio", "label": "Say it out loud. Does it scare you?",
         "options": [("yes", "Yes"), ("a_bit", "A little"), ("no", "No (so make it bigger)")]},
        {"name": "not_yet", "kind": "text", "req": True, "label": "So why haven&#39;t you done it yet?",
         "ph": "Not the excuse. The reason."},
        {"name": "outcome_why", "kind": "whychain", "req": True,
         "label": "Why do you want it? The real answer, not the Instagram caption."},
        {"name": "goal_audience", "kind": "radio", "req": True, "label": "Who knows about this goal?",
         "options": [("public", "Everyone", "I posted it"), ("friends", "Friends and family"),
                     ("coach", "Just me and you"), ("nobody", "Nobody yet", "Including, until now, me")]},
        {"kind": "pair", "fields": [
            {"name": "a_race", "kind": "text", "label": "The race it all points at",
             "ph": "American Birkebeiner, Vasaloppet, Marcialonga, Engadin, Birkebeinerrennet…"},
            {"name": "a_race_date", "kind": "date", "label": "Date, if you know it"},
        ]},
    ]},
    {"title": "Your Biggest Obstacle Is You", "sub": "Not the snow. Not work. You.", "fields": [
        {"name": "inner_obstacle", "kind": "text", "req": True,
         "label": "What in you is most likely to screw this up?",
         "ph": "e.g., I skip rollerski sessions after a late night out"},
        {"name": "obstacle_plan", "kind": "text", "req": True, "label": "When that shows up, you&#39;ll&hellip;",
         "ph": "Specific. &ldquo;Try harder&rdquo; isn&#39;t a plan."},
    ]},
    {"title": "What Would a Fast Skier Do", "sub": "One thing. Built so it survives a bad week.", "fields": [
        {"name": "area", "kind": "select", "req": True, "label": "What&#39;s the one thing that most needs to get better?",
         "options": AREAS},
        {"name": "habit_direction", "kind": "radio", "label": "Start something, or stop something?",
         "options": [("do", "Start"), ("reduce", "Stop")]},
        {"name": "habit", "kind": "text", "req": True, "label": "One thing you&#39;ll do every day",
         "ph": "The one you&#39;ll still do on your worst Tuesday",
         "swap": {"reduce": {"label": "One thing you&#39;ll stop", "ph": "e.g., Staying out for one more loop after dark"}}},
        {"name": "habit_when", "kind": "text", "label": "When or where",
         "ph": "e.g., Right after the last email of the day"},
        {"name": "habit_min", "kind": "text", "req": True, "label": "The smallest version that still counts",
         "ph": "The one you&#39;ll still do on your worst Tuesday",
         "swap": {"reduce": {"label": "What you&#39;ll do instead",
                              "ph": "e.g., Lights out by 10, phone charging in the kitchen"}}},
        {"name": "habit_2", "kind": "text", "label": "A second daily habit, and when (optional)",
         "ph": "e.g., Mobility every night, dryland twice a week"},
    ]},
]

MODULES: list[dict] = [
    _module("ideal", "The season you want", "15 min", [
        {"name": "ideal_season", "kind": "timed", "minutes": 15, "rows": 12,
         "label": "It&#39;s March 2027 and it went perfectly. Write it like a race report: where, who, how it felt. Don&#39;t stop to edit."}]),
    _module("avoid", "The season you&#39;re scared of", "5 min", [
        {"name": "avoid_season", "kind": "timed", "minutes": 5, "rows": 7,
         "label": "Now the other one. March 2027, it went sideways. What happened, and what was your part?"}]),
    _module("best", "Your best stretch ever", "3 min", [
        {"name": "best_block", "kind": "area", "rows": 3,
         "label": "Describe the best stretch of training you&#39;ve ever had. What made it work?",
         "ph": "Those are your success conditions. We&#39;re going to rebuild them on purpose."}]),
    _module("quit", "What would make you quit", "2 min", [
        {"name": "quit_triggers", "kind": "area", "rows": 2,
         "label": "What would make you quit, or quietly stop caring?"}]),
    _module("traits", "Your faults, itemized", "5 min", [
        {"name": "fault", "kind": "select", "label": "Pick the one that cost you most",
         "options": [(t, t) for t in FAULTS]},
        {"name": "fault_when", "kind": "area", "rows": 2, "label": "When did it bite you?"},
        {"name": "strength", "kind": "select", "label": "Fine, and the one that carried you",
         "options": [(t, t) for t in STRENGTHS]}]),
    _module("dead_habit", "The habit that died", "2 min", [
        {"name": "dead_habit", "kind": "text", "label": "One you swore you&#39;d keep this year",
         "ph": "e.g., Dryland strength twice a week (lol)"},
        {"name": "dead_reasons", "kind": "checks", "label": "Cause of death", "options": DEAD_HABIT_REASONS}]),
]

RESULTS = {
    "title": f"Your {NEXT_SEASON}, on paper.",
    "lead": "Print it. Tape it where you&#39;ll see it in November, which is when it matters. A copy is on its way to your inbox.",
    "download": "Download the poster",
}

OFFER = {
    "kicker": "Step two",
    "variants": [
        {"key": "A", "h": "You&#39;ve written it down. Historically, this is where it dies.",
         "p": "Step two is a plan built around the hours you actually have, not the ones you promised."},
        {"key": "B", "h": "Goals are free. The doing is the product.",
         "p": "You&#39;ve done the thinking. The rest is a calendar and your real hours."},
        {"key": "C", "h": "That&#39;s step one. Step two is the part everyone skips.",
         "p": f"A ski plan for the {NEXT_SEASON} season, built from what you just told me."},
    ],
    # One real plan, one real destination: XC Ski Labs has no live checkout
    # (verified against data/stripe-products.json and the current
    # /training-plans/ page — every CTA there routes to this same intake
    # form). No second "season plan" button: that page does not exist here.
    "plans": [
        {"key": "race", "price": "Ski Plan: $60–$249, priced by the week from your race date",
         "cta": f"Build my {NEXT_SEASON} plan", "cta_href": "/questionnaire/?src=goals"},
    ],
    "decline": "Just the poster, thanks",
    "terms": "Every plan is coach-built. You see the price before you pay.",
}


# ── Field rendering (same grammar as GG's engine, gl- classes) ────────


def _attr(value: str) -> str:
    return html.escape(value, quote=True)


def _req(field: dict) -> str:
    return ' <span class="gl-req">*</span>' if field.get("req") else ""


def _label(field: dict, for_id: bool = True) -> str:
    if not field.get("label"):
        return ""
    swap = field.get("swap", {})
    data = "".join(f' data-lbl-{d}="{_attr(v["label"])}"' for d, v in swap.items() if "label" in v)
    target = f' for="{field["name"]}"' if for_id else ""
    return f'<label class="gl-label"{target}{data}>{field["label"]}{_req(field)}</label>'


def _control(field: dict) -> str:
    name, kind = field["name"], field["kind"]
    req = " required" if field.get("req") else ""
    ph = f' placeholder="{field["ph"]}"' if field.get("ph") else ""
    swap = field.get("swap", {})
    ph_data = "".join(f' data-ph-{d}="{_attr(v["ph"])}"' for d, v in swap.items() if "ph" in v)
    if kind in ("text", "email", "date"):
        auto = f' autocomplete="{field["auto"]}"' if field.get("auto") else ""
        return f'<input type="{kind}" id="{name}" name="{name}"{req}{ph}{ph_data}{auto}>'
    if kind == "area":
        return f'<textarea id="{name}" name="{name}" rows="{field.get("rows", 3)}"{req}{ph}></textarea>'
    if kind == "timed":
        return f'<textarea id="{name}" name="{name}" rows="{field.get("rows", 10)}" class="gl-long"{ph}></textarea>'
    if kind == "select":
        opts = '<option value="">Select…</option>' + "".join(
            f'<option value="{_attr(v)}">{t}</option>' for v, t in field["options"])
        return f'<select id="{name}" name="{name}"{req}>{opts}</select>'
    if kind == "radio":
        lift = field.get("lift")
        lift_attr = f' data-lift-when="{lift["when"]}" data-lift="{",".join(lift["fields"])}"' if lift else ""
        opts = "".join(
            f'<label class="gl-choice gl-choice-radio"><input type="radio" name="{name}" value="{o[0]}"'
            f'{req if i == 0 else ""}><span class="gl-choice-body"><span class="gl-choice-title">{o[1]}</span>'
            + (f'<span class="gl-choice-desc">{o[2]}</span>' if len(o) > 2 else "")
            + "</span></label>"
            for i, o in enumerate(field["options"]))
        return f'<div class="gl-choice-group gl-choice-vertical" data-radio="{name}"{lift_attr}>{opts}</div>'
    if kind == "checks":
        opts = "".join(
            f'<label class="gl-choice"><input type="checkbox" name="{n}" value="yes">'
            f'<span>{t}</span></label>' for n, t in field["options"])
        return f'<div class="gl-choice-group">{opts}</div>'
    if kind == "hidden":
        return f'<input type="hidden" id="{name}" name="{name}">'
    raise ValueError(f"unknown field kind {kind!r}")


WHY_NAMES = ["outcome_why", "why_2", "why_3", "why_4", "why_5"]


def render_why_chain(field: dict) -> str:
    """Five whys. Each box appears once the one before has an answer, and
    its question quotes that answer back (filled in by the page script)."""
    groups = []
    for i, name in enumerate(WHY_NAMES):
        label = field["label"] if i == 0 else "And why does that matter?"
        req = " required" if field.get("req") and i == 0 else ""
        star = ' <span class="gl-req">*</span>' if req else ""
        hidden = " hidden" if i else ""
        groups.append(
            f'<div class="gl-field gl-why" data-q="{_attr(_strip_tags(html.unescape(label)))}" data-why="{i}"{hidden}>'
            f'<label class="gl-label" for="{name}">{label}{star}</label>'
            f'<input type="text" id="{name}" name="{name}"{req}'
            + (f' placeholder="{field["ph"]}"' if i == 0 and field.get("ph") else "")
            + "></div>")
    return f'<div class="gl-whys">{"".join(groups)}</div>'


def render_field(field: dict, context_title: str = "") -> str:
    if field["kind"] == "hidden":
        return _control(field)
    if field["kind"] == "whychain":
        return render_why_chain(field)
    if field["kind"] == "pair":
        inner = "".join(render_field(f, context_title) for f in field["fields"])
        return f'<div class="gl-field-row">{inner}</div>'
    q = field.get("label") or context_title
    head = _label(field, for_id=field["kind"] not in ("radio", "checks"))
    if field["kind"] == "timed":
        head = (f'<div class="gl-label-row">{head}'
                f'<button type="button" class="gl-timer" data-minutes="{field["minutes"]}" data-target="{field["name"]}">'
                f'Start {field["minutes"]}:00</button></div>')
    return f'<div class="gl-field" data-q="{_attr(html.unescape(_strip_tags(q)))}">{head}{_control(field)}</div>'


def _strip_tags(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s)


def render_sections() -> str:
    out = []
    for n, sec in enumerate(SECTIONS, start=1):
        fields = "".join(render_field(f, sec["title"]) for f in sec["fields"])
        sub = f'<p class="gl-section-sub">{sec["sub"]}</p>' if sec.get("sub") else ""
        out.append(f"""<section class="gl-section" data-section-n="{n}">
  <div class="gl-section-header">
    <div class="gl-section-num">{n:02d}</div>
    <div class="gl-section-title">{sec['title']}</div>
  </div>
  <div class="gl-section-body">{sub}{fields}</div>
</section>""")
    return "\n".join(out)


def render_modules() -> str:
    mods = []
    for m in MODULES:
        fields = "".join(render_field(f, m["title"]) for f in m["fields"])
        mods.append(
            f'<details class="gl-deeper" data-module="{m["key"]}">'
            f'<summary>{m["title"]} <span class="gl-optional">({m["minutes"]})</span></summary>'
            f'<div class="gl-deeper-body">{fields}</div></details>')
    return f'<div class="gl-deep-title">Extra credit &mdash; for the obsessive</div>\n' + "\n".join(mods)


# ── Page chrome (same pattern as generate_questionnaire.py) ───────────


def build_ga4() -> str:
    return """<script async src="https://www.googletagmanager.com/gtag/js?id=G-3JQLSQLPPM"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
(function(){
  var consent = (document.cookie.match(/xl_consent=([^;]+)/) || [])[1];
  gtag('consent','default',{
    'analytics_storage': consent === 'accepted' ? 'granted' : 'denied',
    'ad_storage': 'denied',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'functionality_storage': 'granted',
    'security_storage': 'granted'
  });
})();
gtag('js', new Date());
gtag('config', 'G-3JQLSQLPPM');
</script>"""


def build_nav() -> str:
    return """<nav class="gl-nav" aria-label="Primary">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo"><img class="gl-brand-mark" src="/xc-logo.svg" alt="" width="30" height="30"><span class="gl-brand-name">XC SKI <em>LABS</em></span></a>
    <div class="gl-nav-links">
      <a href="/search/">Races</a>
      <a href="/guide/">Guide</a>
      <a href="/training-plans/">Plans</a>
      <a href="/coaching/">Coaching</a>
      <a href="/about/">About</a>
    </div>
  </div>
</nav>"""


def build_cookie_banner() -> str:
    return """<div class="gl-cookie-consent" id="gl-cookie-consent">
  <div class="gl-cookie-inner">
    <div class="gl-cookie-text">We use analytics cookies to improve XC Ski Labs.</div>
    <div class="gl-cookie-actions">
      <button type="button" id="gl-cookie-accept">Accept</button>
      <button type="button" id="gl-cookie-decline">Decline</button>
    </div>
  </div>
</div>"""


def build_results() -> str:
    plans_html = "".join(
        f'<div class="gl-offer-plan">'
        f'<p class="gl-offer-plan-price">{plan["price"]}</p>'
        f'<a class="gl-offer-cta" href="{plan["cta_href"]}" data-offer-cta data-plan-type="{plan["key"]}">{plan["cta"]}</a>'
        f"</div>" for plan in OFFER["plans"])
    cards = "".join(
        f'<div class="gl-offer" data-offer-variant="{v["key"]}" hidden>'
        f'<div class="gl-offer-kicker">{OFFER["kicker"]}</div>'
        f'<h3 class="gl-offer-h">{v["h"]}</h3>'
        f'<p class="gl-offer-p">{v["p"]}</p>'
        f'<div class="gl-offer-plans">{plans_html}</div>'
        f'<p class="gl-offer-terms">{OFFER["terms"]}</p>'
        f'<a class="gl-offer-decline" href="#" data-offer-decline>{OFFER["decline"]}</a>'
        f"</div>" for v in OFFER["variants"])
    return f'''<section id="results" class="gl-results" hidden>
  <div class="gl-results-head">
    <h2>{RESULTS["title"]}</h2>
    <p>{RESULTS["lead"]}</p>
  </div>
  <canvas id="poster-canvas" width="1080" height="1440" class="gl-poster" aria-label="Your {NEXT_SEASON} goal poster"></canvas>
  <a id="poster-download" class="gl-download" href="#" download="{NEXT_SEASON}-goal-poster.png">{RESULTS["download"]}</a>
  {cards}
</section>'''


def build_css() -> str:
    return load_tokens_css() + """
*, *::before, *::after { box-sizing: border-box; border-radius: 0 !important; box-shadow: none !important; }
body { margin: 0; padding: 0; background: var(--gl-paper); color: var(--gl-carbon); font-family: var(--gl-font-editorial); line-height: 1.6; -webkit-font-smoothing: antialiased; }
a { color: var(--gl-swix-red); }
a:hover { color: var(--gl-carbon); }
a:focus-visible, button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible {
  outline: 3px solid var(--gl-swix-red); outline-offset: 2px;
}
.gl-skip-link { position: absolute; left: -999px; top: 8px; background: var(--gl-white); color: var(--gl-carbon); padding: 8px 12px; z-index: 10000; font-family: var(--gl-font-data); font-size: 0.75rem; }
.gl-skip-link:focus { left: 8px; }
.gl-nav { position: sticky; top: 0; z-index: 1000; background: var(--gl-carbon); border-bottom: 3px solid var(--gl-swix-red); padding: 0 20px; }
.gl-nav-inner { max-width: var(--gl-measure); margin: 0 auto; display: flex; align-items: center; justify-content: space-between; min-height: 52px; }
.gl-nav-links { display: flex; gap: 18px; align-items: center; }
.gl-nav-links a { font-family: var(--gl-font-data); font-size: 0.7rem; font-weight: 700; color: var(--gl-muted); text-decoration: none; text-transform: uppercase; letter-spacing: 0.06em; }
.gl-nav-links a:hover, .gl-nav-links a.active { color: var(--gl-white); }
.gl-page { max-width: 760px; margin: 0 auto; padding: 0 20px 80px; }
.gl-page-header { padding: 48px 0 28px; border-bottom: 2px solid var(--gl-hairline); margin-bottom: 24px; }
.gl-kicker { font-family: var(--gl-font-data); font-size: 0.72rem; font-weight: 700; color: var(--gl-swix-red); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 12px; }
.gl-page-header h1 { font-family: var(--gl-font-display); font-size: clamp(2.2rem, 8vw, 4.4rem); font-style: italic; font-weight: 900; line-height: 0.96; text-transform: uppercase; margin: 0 0 14px; }
.gl-page-header p { font-size: 1.08rem; color: var(--gl-muted); margin: 0; max-width: 62ch; }
.gl-progress-wrap { position: sticky; top: 52px; z-index: 900; background: var(--gl-white); border: 2px solid var(--gl-carbon); margin-bottom: 28px; padding: 12px; }
.gl-progress-inner { display: flex; align-items: center; gap: 12px; }
.gl-progress-label, .gl-progress-pct, .gl-save-indicator { font-family: var(--gl-font-data); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--gl-muted); white-space: nowrap; }
.gl-progress-track { flex: 1; height: 8px; background: var(--gl-hairline); border: 1px solid var(--gl-muted); }
.gl-progress-fill { height: 100%; width: 0; background: var(--gl-swix-red); transition: width 0.2s ease; }
.gl-save-indicator { opacity: 0; transition: opacity 0.15s ease; }
.gl-save-indicator.show { opacity: 1; }
.gl-section { border: 2px solid var(--gl-carbon); background: var(--gl-white); margin-bottom: 28px; }
.gl-section-header { background: var(--gl-carbon); color: var(--gl-white); padding: 14px 18px; display: flex; align-items: center; gap: 12px; }
.gl-section-num { font-family: var(--gl-font-data); font-size: 0.68rem; font-weight: 700; background: var(--gl-swix-red); color: var(--gl-white); padding: 3px 8px; letter-spacing: 0.08em; }
.gl-section-title { font-family: var(--gl-font-data); font-size: 0.9rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
.gl-section-body { padding: 22px 18px; }
.gl-section-sub { margin: 0 0 16px; color: var(--gl-muted); font-style: italic; }
.gl-field { margin-bottom: 18px; }
.gl-field:last-child { margin-bottom: 0; }
.gl-field-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.gl-label { display: block; font-family: var(--gl-font-data); font-size: 0.76rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; margin-bottom: 6px; }
.gl-label-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.gl-req { color: var(--gl-swix-red); }
input[type="text"], input[type="email"], input[type="date"], select, textarea {
  width: 100%; min-height: 44px; border: 2px solid var(--gl-carbon); background: var(--gl-paper); color: var(--gl-carbon); font-family: var(--gl-font-data); font-size: 0.9rem; padding: 10px 12px;
}
textarea { min-height: 100px; resize: vertical; }
textarea.gl-long { min-height: 220px; }
.gl-choice-group { display: grid; gap: 8px; }
.gl-choice-vertical { grid-template-columns: 1fr; }
.gl-choice { min-height: 44px; border: 1px solid var(--gl-hairline); padding: 9px 10px; display: flex; align-items: center; gap: 8px; font-family: var(--gl-font-data); font-size: 0.78rem; cursor: pointer; }
.gl-choice:hover { border-color: var(--gl-swix-red); }
.gl-choice.selected { border-color: var(--gl-swix-red); border-width: 2px; }
.gl-choice input { accent-color: var(--gl-swix-red); }
.gl-choice-body { display: flex; flex-direction: column; gap: 2px; }
.gl-choice-title { font-weight: 700; }
.gl-choice-desc { color: var(--gl-muted); font-weight: 400; text-transform: none; letter-spacing: 0; }
.gl-timer { min-height: 32px; border: 2px solid var(--gl-carbon); background: var(--gl-white); color: var(--gl-carbon); font-family: var(--gl-font-data); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 4px 10px; cursor: pointer; }
.gl-timer.running { background: var(--gl-swix-red); color: var(--gl-white); }
.gl-timer.done { background: var(--gl-carbon); color: var(--gl-white); }
.gl-whys { display: flex; flex-direction: column; gap: 14px; }
.gl-deep-title { font-family: var(--gl-font-data); font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; background: var(--gl-carbon); color: var(--gl-white); padding: 10px 14px; margin: 32px 0 16px; }
.gl-deeper { border: 2px solid var(--gl-carbon); background: var(--gl-white); margin-bottom: 14px; }
.gl-deeper summary { cursor: pointer; padding: 12px 16px; font-family: var(--gl-font-data); font-size: 0.82rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; }
.gl-optional { color: var(--gl-muted); font-weight: 400; text-transform: none; letter-spacing: 0; }
.gl-deeper-body { padding: 0 16px 16px; }
.gl-actions { display: flex; gap: 12px; align-items: center; padding: 18px 0; }
.gl-save-btn, .gl-submit-btn { min-height: 44px; border: 2px solid var(--gl-carbon); font-family: var(--gl-font-data); font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 12px 18px; cursor: pointer; }
.gl-save-btn { background: var(--gl-white); color: var(--gl-carbon); }
.gl-submit-btn { background: var(--gl-swix-red); color: var(--gl-white); }
.gl-submit-btn:hover { background: var(--gl-carbon); }
.gl-submit-btn:disabled { opacity: 0.6; cursor: wait; }
.gl-done { color: var(--gl-muted); font-style: italic; margin: 0 0 8px; }
.gl-message { border: 2px solid var(--gl-carbon); padding: 14px 16px; margin-bottom: 24px; font-family: var(--gl-font-data); font-size: 0.85rem; }
.gl-message.error { border-color: var(--gl-swix-red); color: var(--gl-swix-red); }
.gl-message.hidden { display: none; }
.gl-honeypot { position: absolute; left: -9999px; }
.gl-results { border: 3px solid var(--gl-carbon); background: var(--gl-white); padding: 28px 20px; margin-top: 28px; }
.gl-results-head h2 { font-family: var(--gl-font-display); font-style: italic; font-weight: 900; text-transform: uppercase; line-height: 0.98; margin: 0 0 10px; font-size: clamp(1.6rem, 5vw, 2.4rem); }
.gl-results-head p { color: var(--gl-muted); margin: 0 0 20px; }
.gl-poster { display: block; width: 100%; max-width: 420px; border: 3px solid var(--gl-carbon); margin: 0 0 10px; }
.gl-download { display: inline-block; margin-bottom: 24px; font-family: var(--gl-font-data); font-size: 0.8rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
.gl-offer { border-top: 3px solid var(--gl-swix-red); padding-top: 20px; }
.gl-offer-kicker { font-family: var(--gl-font-data); font-size: 0.68rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: var(--gl-swix-red); margin-bottom: 6px; }
.gl-offer-h { font-family: var(--gl-font-display); font-style: italic; font-weight: 900; text-transform: uppercase; margin: 0 0 8px; font-size: clamp(1.2rem, 3.4vw, 1.6rem); }
.gl-offer-p { margin: 0 0 16px; }
.gl-offer-plans { display: flex; flex-direction: column; gap: 14px; margin-bottom: 12px; }
.gl-offer-plan-price { font-family: var(--gl-font-data); font-size: 0.8rem; font-weight: 700; margin: 0 0 8px; }
.gl-offer-cta { display: inline-flex; min-height: 44px; align-items: center; border: 2px solid var(--gl-carbon); background: var(--gl-carbon); color: var(--gl-white); padding: 0 18px; font-family: var(--gl-font-data); font-size: 0.78rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; text-decoration: none; }
.gl-offer-terms { color: var(--gl-muted); font-size: 0.82rem; margin: 8px 0; }
.gl-offer-decline { font-family: var(--gl-font-data); font-size: 0.75rem; color: var(--gl-muted); text-decoration: underline; }
.gl-footer { max-width: 760px; margin: 0 auto; padding: 34px 20px 60px; color: var(--gl-muted); font-family: var(--gl-font-data); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em; }
.gl-cookie-consent { position: fixed; left: 20px; right: 20px; bottom: 20px; z-index: 2000; display: none; background: var(--gl-carbon); color: var(--gl-white); border: 2px solid var(--gl-swix-red); padding: 14px; }
.gl-cookie-consent.visible { display: block; }
.gl-cookie-inner { max-width: var(--gl-measure); margin: 0 auto; display: flex; align-items: center; gap: 16px; justify-content: space-between; }
.gl-cookie-text { font-family: var(--gl-font-data); font-size: 0.72rem; color: var(--gl-hairline); }
.gl-cookie-actions { display: flex; gap: 8px; }
.gl-cookie-actions button { min-height: 44px; border: 2px solid var(--gl-white); background: transparent; color: var(--gl-white); font-family: var(--gl-font-data); font-size: 0.7rem; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 8px 12px; cursor: pointer; }
.gl-cookie-actions button:first-child { background: var(--gl-white); color: var(--gl-carbon); }
@media (prefers-reduced-motion: reduce) {
  .gl-progress-fill { transition: none; }
  .gl-save-indicator { transition: none; }
  html { scroll-behavior: auto; }
}
@media (max-width: 700px) {
  .gl-nav-inner { align-items: flex-start; flex-direction: column; padding: 12px 0; }
  .gl-nav-links { flex-wrap: wrap; gap: 12px; }
  .gl-progress-wrap { top: 86px; }
  .gl-field-row { grid-template-columns: 1fr; }
  .gl-cookie-inner { align-items: flex-start; flex-direction: column; }
  .gl-actions { flex-wrap: wrap; }
}
"""


def build_js() -> str:
    js = r"""<script>
(function() {
  "use strict";
  var STORAGE_KEY = "__STORAGE_KEY__";
  var LEAD_WORKER_URL = "__LEAD_WORKER_URL__";
  var LEAD_SOURCE = "__LEAD_SOURCE__";
  var BRAND = "__BRAND__";
  var SUBMIT_LABEL = "__SUBMIT_LABEL__";
  var CONTACT_EMAIL = "__CONTACT_EMAIL__";
  var lastStored = false;
  var submitted = false;

  var form = document.getElementById("goals-form");
  var REDUCED_MOTION = !!(window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  var SCROLL_BEHAVIOR = REDUCED_MOTION ? "auto" : "smooth";

  var ENTRY_SRC = (function() {
    var v = "";
    try { v = new URLSearchParams(window.location.search).get("src") || ""; } catch (e) {}
    return /^[a-z_]{1,24}$/.test(v) ? v : "";
  })();
  var RACE_SLUG = (function() {
    var v = "";
    try { v = new URLSearchParams(window.location.search).get("race") || ""; } catch (e) {}
    return /^[a-z0-9-]{1,80}$/.test(v) ? v : "";
  })();
  var GOAL_TYPE = (function() {
    var v = "";
    try { v = new URLSearchParams(window.location.search).get("goal_type") || ""; } catch (e) {}
    return /^(finish|beat_time|race_it|same|bigger)$/.test(v) ? v : "";
  })();
  var POSTER_TOKEN = "";

  function ga4(name, params) {
    params = params || {};
    if (ENTRY_SRC) { params.src = ENTRY_SRC; }
    if (RACE_SLUG) { params.race_slug = RACE_SLUG; }
    if (typeof gtag === "function") { gtag("event", name, params); }
  }

  function setDirection(dir) {
    form.querySelectorAll("[data-ph-" + dir + "]").forEach(function(el) {
      el.placeholder = el.getAttribute("data-ph-" + dir);
    });
    form.querySelectorAll("[data-lbl-" + dir + "]").forEach(function(el) {
      var star = el.querySelector(".gl-req");
      el.textContent = el.getAttribute("data-lbl-" + dir);
      if (star) { el.appendChild(document.createTextNode(" ")); el.appendChild(star); }
    });
  }

  function radioChanged(input) {
    form.querySelectorAll('input[name="' + input.name + '"]').forEach(function(inp) {
      inp.closest(".gl-choice").classList.toggle("selected", inp.checked);
    });
    if (input.name === "habit_direction") { setDirection(input.value); }
    var group = input.closest("[data-lift]");
    if (group) {
      var lifted = input.value === group.getAttribute("data-lift-when");
      group.getAttribute("data-lift").split(",").forEach(function(id) {
        var el = document.getElementById(id);
        if (!el) { return; }
        el.required = !lifted;
        var star = form.querySelector('label[for="' + id + '"] .gl-req');
        if (star) { star.hidden = lifted; }
      });
    }
  }

  var timer = null, timerBtn = null;
  function resetTimer(btn) { btn.classList.remove("running", "done"); btn.textContent = "Start " + btn.getAttribute("data-minutes") + ":00"; }
  function toggleTimer(btn) {
    if (timer) {
      clearInterval(timer); timer = null;
      var same = timerBtn === btn;
      resetTimer(timerBtn);
      if (same) { return; }
    }
    timerBtn = btn;
    var endsAt = Date.now() + Number(btn.getAttribute("data-minutes")) * 60000;
    btn.classList.remove("done"); btn.classList.add("running");
    var target = document.getElementById(btn.getAttribute("data-target"));
    if (target) { target.focus(); }
    function paint() {
      var left = Math.max(0, Math.round((endsAt - Date.now()) / 1000));
      if (left === 0) {
        clearInterval(timer); timer = null;
        btn.classList.remove("running"); btn.classList.add("done"); btn.textContent = "Time";
        return;
      }
      var m = Math.floor(left / 60), s = left % 60;
      btn.textContent = m + ":" + (s < 10 ? "0" : "") + s;
    }
    paint();
    timer = setInterval(paint, 500);
  }

  form.addEventListener("click", function(e) {
    var t = e.target;
    var tb = t.closest(".gl-timer");
    if (tb) { toggleTimer(tb); return; }
    var opt = t.closest(".gl-choice");
    if (opt) {
      var input = opt.querySelector("input");
      if (input.type === "checkbox") {
        if (t !== input) { input.checked = !input.checked; e.preventDefault(); }
        opt.classList.toggle("selected", input.checked);
        queueSave();
        return;
      }
      input.checked = true;
      radioChanged(input);
      queueSave();
      updateProgress();
    }
  });

  function updateWhys() {
    var groups = form.querySelectorAll(".gl-why");
    for (var i = 1; i < groups.length; i++) {
      var prev = groups[i - 1].querySelector("input").value.trim();
      var shown = !groups[i - 1].hidden && prev.length > 0;
      var own = groups[i].querySelector("input").value.trim();
      groups[i].hidden = !(shown || own);
      if (prev) {
        var quoted = prev.length > 60 ? prev.slice(0, 57).trim() + "..." : prev;
        var lbl = "Why does “" + quoted + "” matter?";
        groups[i].querySelector("label").textContent = lbl;
        groups[i].setAttribute("data-q", lbl);
      }
    }
  }

  var OFFER_VARIANT = (function() {
    var cards = document.querySelectorAll("[data-offer-variant]");
    if (!cards.length) { return ""; }
    return cards[Math.floor(Math.random() * cards.length)].getAttribute("data-offer-variant");
  })();

  var started = false;
  function onEdit(e) {
    if (!started) { started = true; ga4("goal_start", {}); }
    if (e && e.target.type === "radio" && e.target.checked) { radioChanged(e.target); }
    if (e && e.target.closest && e.target.closest(".gl-why")) { updateWhys(); }
    queueSave();
    updateProgress();
  }
  form.addEventListener("input", onEdit);
  form.addEventListener("change", onEdit);

  function updateProgress() {
    var names = {};
    form.querySelectorAll("[required]").forEach(function(el) { names[el.name] = true; });
    var keys = Object.keys(names);
    var filled = keys.filter(function(n) {
      var el = form.querySelector('[name="' + n + '"]');
      if (!el) { return false; }
      if (el.type === "radio") { return !!form.querySelector('input[name="' + n + '"]:checked'); }
      return !!el.value.trim();
    }).length;
    var pct = keys.length ? Math.round(filled / keys.length * 100) : 0;
    var fill = document.getElementById("progress-fill");
    var text = document.getElementById("progress-text");
    if (fill) { fill.style.width = pct + "%"; }
    if (text) { text.textContent = pct + "% complete"; }
  }

  function collect() {
    var data = {};
    new FormData(form).forEach(function(value, key) {
      if (key === "website") { return; }
      if (String(value).trim()) { data[key] = String(value).trim(); }
    });
    return data;
  }

  var saveTimer = null, saveOk = true, saveWarned = false;
  function save(silent) {
    if (submitted) { return; }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(collect()));
      saveOk = true;
      if (!silent) { showMessage("info", "Saved in this browser. Close the page and come back any time."); }
    } catch (err) {
      saveOk = false;
      if (!silent || !saveWarned) {
        saveWarned = true;
        showMessage("error", "This browser won't let me save. Keep the page open until you submit.");
      }
    }
  }
  function queueSave() { clearTimeout(saveTimer); saveTimer = setTimeout(function() { save(true); }, 800); }

  var restoringDraft = false;
  function restore() {
    restoringDraft = true;
    var saved = null;
    try { saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); } catch (err) { saved = null; }
    if (saved) {
      Object.keys(saved).forEach(function(key) {
        form.querySelectorAll('[name="' + key + '"]').forEach(function(el) {
          if (el.type === "checkbox") {
            el.checked = saved[key] === el.value;
            var opt = el.closest(".gl-choice");
            if (opt) { opt.classList.toggle("selected", el.checked); }
          } else if (el.type === "radio") {
            if (el.value === saved[key]) { el.checked = true; radioChanged(el); }
          } else {
            el.value = saved[key];
          }
        });
      });
      form.querySelectorAll(".gl-deeper").forEach(function(mod) {
        var used = Array.prototype.some.call(mod.querySelectorAll("[name]"), function(el) { return !!saved[el.name]; });
        if (used) { mod.open = true; }
      });
      showMessage("info", "Picked up where you left off.");
    }
    updateWhys();
    var params = new URLSearchParams(window.location.search);
    ["name", "email"].forEach(function(k) {
      var el = document.getElementById(k);
      if (el && params.get(k) && !el.value) { el.value = params.get(k); }
    });
    if (GOAL_TYPE) {
      var goalLineTemplates = {
        finish: "Finish {race}.",
        beat_time: "Finish {race} faster than last time.",
        race_it: "Race {race}, not just ski it.",
        same: "Ski {race} again, and ski it better.",
        bigger: "Take on something bigger than {race}."
      };
      var raceLabel = RACE_SLUG
        ? RACE_SLUG.split("-").filter(Boolean).map(function(w) { return w.charAt(0).toUpperCase() + w.slice(1); }).join(" ")
        : "it";
      var goalField = document.getElementById("outcome_goal");
      if (goalField && !goalField.value.trim()) {
        goalField.value = goalLineTemplates[GOAL_TYPE].replace("{race}", raceLabel);
      }
    }
    updateProgress();
    setTimeout(function() { restoringDraft = false; }, 800);
  }

  form.querySelectorAll(".gl-save-btn").forEach(function(b) {
    b.addEventListener("click", function() { save(false); ga4("season_review_saved", {}); });
  });
  window.addEventListener("beforeunload", function() { save(true); });

  function setButtons(disabled, label) {
    form.querySelectorAll(".gl-submit-btn").forEach(function(b) { b.disabled = disabled; b.textContent = label; });
  }

  form.addEventListener("submit", function(e) {
    e.preventDefault();
    if (form.querySelector(".gl-submit-btn").disabled) { return; }
    if (form.querySelector("[name=website]").value) {
      showMessage("error", "Something filled a hidden field. Clear your browser's autofill for this page and try again.");
      return;
    }
    var d = collect();
    setButtons(true, "Submitting…");
    save(true);

    var ctrl = typeof AbortController === "function" ? new AbortController() : null;
    var killer = setTimeout(function() { if (ctrl) { ctrl.abort(); } }, 25000);

    var answers = {};
    Object.keys(d).forEach(function(k) {
      if (k !== "name" && k !== "email" && typeof d[k] === "string") { answers[k] = d[k]; }
    });
    fetch(LEAD_WORKER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify({
        source: LEAD_SOURCE, brand: BRAND, email: d.email, name: d.name || "",
        goal_answers: answers, website: "",
        offer_variant: OFFER_VARIANT, race_slug: RACE_SLUG, entry_src: ENTRY_SRC, goal_type: GOAL_TYPE
      }),
      signal: ctrl ? ctrl.signal : undefined
    }).then(function(r) {
      return r.json().then(function(body) {
        if (body && body.poster_token) { POSTER_TOKEN = body.poster_token; }
        return r.ok;
      }).catch(function() { return r.ok; });
    }).catch(function() { return false; })
      .then(function(ok) {
        clearTimeout(killer);
        if (!ok) { throw new Error("worker failed"); }
        lastStored = true;
      })
      .then(function() {
        submitted = true;
        showResults(d);
        clearTimeout(saveTimer);
        try { localStorage.removeItem(STORAGE_KEY); } catch (err) {}
        ga4("season_review_submitted", { deep_modules: form.querySelectorAll(".gl-deeper[open]").length });
        ga4("goal_submit", {});
        setButtons(true, "Submitted");
      })
      .catch(function(err) {
        clearTimeout(killer);
        showMessage("error", saveOk
          ? "That didn't go through. Your answers are saved in this browser. Try again, or email " + CONTACT_EMAIL + "."
          : "That didn't go through, and this browser can't save. Keep this page open and try again, or email " + CONTACT_EMAIL + ".");
        setButtons(false, SUBMIT_LABEL);
        ga4("season_review_error", { message: String(err.message || "unknown").slice(0, 80) });
      });
  });

  var POSTER = { ink: "__GL_INK__", paper: "__GL_PAPER__", accent: "__GL_RUST__", grey: "__GL_CAPTION__" };

  function posterClean(value, limit) { return String(value || "").split(/\s+/).join(" ").trim().slice(0, limit); }

  function wrapText(ctx, text, maxWidth) {
    var words = String(text).split(/\s+/), lines = [], line = "";
    words.forEach(function(word) {
      var next = line ? line + " " + word : word;
      if (ctx.measureText(next).width <= maxWidth || !line) { line = next; }
      else { lines.push(line); line = word; }
    });
    if (line) { lines.push(line); }
    return lines;
  }

  function drawPoster(d) {
    var canvas = document.getElementById("poster-canvas");
    var ctx = canvas.getContext("2d");
    var W = canvas.width, H = canvas.height, pad = 84, inner = W - pad * 2;
    ctx.fillStyle = POSTER.paper;
    ctx.fillRect(0, 0, W, H);
    ctx.textBaseline = "top";

    ctx.font = "700 26px 'Sometype Mono', monospace";
    ctx.fillStyle = POSTER.accent;
    ctx.fillText("__NEXT_SEASON__ · GOAL FILE", pad, pad);
    ctx.fillStyle = POSTER.ink;
    ctx.textAlign = "right";
    ctx.fillText("XC SKI LABS", W - pad, pad);
    ctx.textAlign = "left";
    ctx.font = "22px 'Sometype Mono', monospace";
    ctx.fillStyle = POSTER.grey;
    ctx.fillText("XCSKILABS.COM", pad, H - pad - 20);

    var habit = posterClean(d.habit, 120);
    if (habit && d.habit_when) { habit += " — " + posterClean(d.habit_when, 120); }
    var rows = [[d.habit_direction === "reduce" ? "STOPPING" : "EVERY DAY", habit],
                ["ALSO EVERY DAY", posterClean(d.habit_2, 150)],
                ["WATCH FOR", posterClean(d.inner_obstacle, 150)]]
      .filter(function(r) { return r[1]; })
      .map(function(r) {
        ctx.font = "30px 'Sometype Mono', monospace";
        return [r[0], wrapText(ctx, r[1], inner).slice(0, 2)];
      });
    var framed = rows.reduce(function(h, r) { return h + 56 + r[1].length * 38; }, 0);
    var frameTop = H - pad - 60 - framed;
    var y = frameTop;
    rows.forEach(function(row) {
      ctx.font = "700 24px 'Sometype Mono', monospace";
      ctx.fillStyle = POSTER.accent;
      ctx.fillText(row[0], pad, y);
      ctx.font = "30px 'Sometype Mono', monospace";
      ctx.fillStyle = POSTER.ink;
      row[1].forEach(function(line, i) { ctx.fillText(line, pad, y + 34 + i * 38); });
      y += 56 + row[1].length * 38;
    });

    ctx.font = "italic 38px 'Source Serif 4', Georgia, serif";
    var why = posterClean([d.why_5, d.why_4, d.why_3, d.why_2, d.outcome_why]
      .filter(function(w) { return w && String(w).trim(); })[0], 200);
    var whyLines = why ? wrapText(ctx, "“" + why + "”", inner).slice(0, 3) : [];
    var whyHeight = whyLines.length * 50 + (whyLines.length ? 30 : 0);

    var labelY = pad + 200;
    var available = frameTop - whyHeight - labelY - 120;
    var goal = posterClean(d.outcome_goal, 180) || "[your goal]";
    if (!/[.!?]$/.test(goal)) { goal += "."; }
    var size = 104, goalLines = [];
    [104, 92, 80, 68, 58, 48].forEach(function(candidate) {
      if (goalLines.length && goalLines.length * Math.round(size * 1.06) <= available) { return; }
      size = candidate;
      ctx.font = "700 " + size + "px 'Source Serif 4', Georgia, serif";
      goalLines = wrapText(ctx, goal, inner);
    });

    ctx.font = "26px 'Sometype Mono', monospace";
    ctx.fillStyle = POSTER.grey;
    ctx.fillText("BY THE END OF __NEXT_SEASON__, " + (posterClean(d.name, 40) || "I").toUpperCase() + " WILL", pad, labelY);

    ctx.font = "700 " + size + "px 'Source Serif 4', Georgia, serif";
    ctx.fillStyle = POSTER.ink;
    y = labelY + 60;
    goalLines.slice(0, 6).forEach(function(line) { ctx.fillText(line, pad, y); y += Math.round(size * 1.06); });
    ctx.fillStyle = POSTER.accent;
    ctx.fillRect(pad, y + 24, 150, 6);

    ctx.font = "italic 38px 'Source Serif 4', Georgia, serif";
    ctx.fillStyle = POSTER.grey;
    y = frameTop - whyHeight;
    whyLines.forEach(function(line) { ctx.fillText(line, pad, y); y += 50; });
  }

  function showResults(d) {
    var results = document.getElementById("results");
    var message = document.getElementById("message");
    if (message) { message.classList.add("hidden"); }
    form.hidden = true;
    results.hidden = false;
    try { drawPoster(d); } catch (err) {}
    var link = document.getElementById("poster-download");
    try { link.href = document.getElementById("poster-canvas").toDataURL("image/png"); }
    catch (err) { link.hidden = true; }
    link.addEventListener("click", function() { ga4("goal_poster_download", {}); });

    var pick = results.querySelector('[data-offer-variant="' + OFFER_VARIANT + '"]');
    if (pick) {
      pick.hidden = false;
      var key = OFFER_VARIANT;
      pick.querySelectorAll("[data-offer-cta]").forEach(function(cta) {
        var planType = cta.getAttribute("data-plan-type") || "race";
        try {
          var ctaUrl = new URL(cta.getAttribute("href"), window.location.href);
          ctaUrl.searchParams.set("offer_variant", key);
          if (RACE_SLUG) { ctaUrl.searchParams.set("race", RACE_SLUG); }
          if (ENTRY_SRC) { ctaUrl.searchParams.set("entry_src", ENTRY_SRC); }
          if (POSTER_TOKEN) { ctaUrl.searchParams.set("t", POSTER_TOKEN); }
          cta.href = ctaUrl.pathname + ctaUrl.search;
        } catch (err) {}
        ga4("goal_offer_view", { offer_variant: key, plan_type: planType });
        cta.addEventListener("click", function() { ga4("goal_offer_click", { offer_variant: key, plan_type: planType }); });
      });
      var decline = pick.querySelector("[data-offer-decline]");
      if (decline) {
        decline.addEventListener("click", function(e) {
          e.preventDefault();
          pick.hidden = true;
          ga4("goal_offer_declined", { offer_variant: key });
        });
      }
    }
    ga4("goal_results_view", {});
    results.scrollIntoView({ behavior: SCROLL_BEHAVIOR, block: "start" });
  }

  function showMessage(type, text) {
    var m = document.getElementById("message");
    m.className = "gl-message " + type;
    m.textContent = text;
    m.classList.remove("hidden");
    m.scrollIntoView({ behavior: SCROLL_BEHAVIOR, block: "center" });
  }

  function watchGoalSections() {
    if (typeof IntersectionObserver !== "function") { return; }
    var targets = Array.prototype.slice.call(form.querySelectorAll("[data-section-n]"));
    if (!targets.length) { return; }
    var seen = {};
    var observer = new IntersectionObserver(function(entries) {
      entries.forEach(function(entry) {
        if (!entry.isIntersecting) { return; }
        var n = entry.target.getAttribute("data-section-n");
        if (!n || seen[n]) { return; }
        seen[n] = true;
        ga4("goal_section", { number: Number(n) });
      });
    }, { threshold: 0.5 });
    targets.forEach(function(t) { observer.observe(t); });
  }
  var goalSectionsStarted = false;
  function startWatchingGoalSectionsOnce() {
    if (goalSectionsStarted || restoringDraft) { return; }
    goalSectionsStarted = true;
    watchGoalSections();
  }
  ["pointerdown", "keydown", "wheel", "touchstart"].forEach(function(evt) {
    window.addEventListener(evt, startWatchingGoalSectionsOnce, { once: true, passive: true });
  });

  restore();
  ga4("season_review_view", {});

  var cookieBanner = document.getElementById("gl-cookie-consent");
  if (cookieBanner && !/xl_consent=/.test(document.cookie)) { cookieBanner.classList.add("visible"); }
  var cookieAccept = document.getElementById("gl-cookie-accept");
  var cookieDecline = document.getElementById("gl-cookie-decline");
  if (cookieAccept) {
    cookieAccept.addEventListener("click", function() {
      document.cookie = "xl_consent=accepted;path=/;max-age=31536000;SameSite=Lax";
      cookieBanner.classList.remove("visible");
      if (typeof gtag === "function") { gtag("consent", "update", { analytics_storage: "granted" }); }
    });
  }
  if (cookieDecline) {
    cookieDecline.addEventListener("click", function() {
      document.cookie = "xl_consent=declined;path=/;max-age=31536000;SameSite=Lax";
      cookieBanner.classList.remove("visible");
      if (typeof gtag === "function") { gtag("consent", "update", { analytics_storage: "denied" }); }
    });
  }
})();
</script>"""
    return (js.replace("__STORAGE_KEY__", "xcskilabs_goal_2026_27_v1")
              .replace("__LEAD_WORKER_URL__", LEAD_WORKER_URL)
              .replace("__LEAD_SOURCE__", LEAD_SOURCE)
              .replace("__BRAND__", BRAND)
              .replace("__SUBMIT_LABEL__", "Make My Poster")
              .replace("__CONTACT_EMAIL__", CONTACT_EMAIL)
              .replace("__NEXT_SEASON__", NEXT_SEASON)
              .replace("__GL_INK__", _token_hex("gl-ink"))
              .replace("__GL_PAPER__", _token_hex("gl-paper"))
              .replace("__GL_RUST__", _token_hex("gl-rust"))
              .replace("__GL_CAPTION__", _token_hex("gl-caption")))


def generate_page() -> str:
    title = f"Your {NEXT_SEASON} Goal, On Paper | XC Ski Labs"
    description = (f"Fifteen minutes on the season you had and the one you want. You leave "
                    f"with a {NEXT_SEASON} goal poster and the one thing most likely to wreck it.")
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/xc-logo.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/goals/">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="https://xcskilabs.com/goals/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Sometype+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,700&display=swap" rel="stylesheet">
  {build_ga4()}
  <style>{build_css()}</style>
</head>
<body>
<a href="#goals-form" class="gl-skip-link">Skip to questionnaire</a>
{build_nav()}
<main class="gl-page" id="goals-form-anchor">
  <header class="gl-page-header">
    <div class="gl-kicker">The {NEXT_SEASON} Goal Autopsy</div>
    <h1>So. {LAST_SEASON}.</h1>
    <p>Fifteen minutes. Don&#39;t write what you&#39;d post. Write what you&#39;d admit after the second beer. You leave with a {NEXT_SEASON} goal poster and the one thing most likely to wreck it. It saves as you go.</p>
  </header>
  <div class="gl-progress-wrap" aria-live="polite">
    <div class="gl-progress-inner">
      <div class="gl-progress-label">Progress</div>
      <div class="gl-progress-track"><div class="gl-progress-fill" id="progress-fill"></div></div>
      <div class="gl-progress-pct" id="progress-text">0% complete</div>
    </div>
  </div>
  <div id="message" class="gl-message hidden"></div>
  <form id="goals-form">
    <input type="text" name="website" class="gl-honeypot" tabindex="-1" autocomplete="off">
    {render_sections()}
    <p class="gl-done">That&#39;s it. Hit submit and your poster is on its way &mdash; or keep digging first.</p>
    <div class="gl-actions">
      <button type="button" class="gl-save-btn">Save Progress</button>
      <button type="submit" class="gl-submit-btn" id="submit-btn">Make My Poster</button>
    </div>
    {render_modules()}
    <div class="gl-actions">
      <button type="submit" class="gl-submit-btn" id="submit-btn-2">Make My Poster</button>
    </div>
  </form>
  {build_results()}
</main>
<footer class="gl-footer">
  <p>Your answers are stored so I can make your poster and email it to you, and I&#39;ll send one short check-in a week later. Unsubscribe from either with the link in the email. Nothing is sold or shared; the <a href="/privacy/">Privacy Policy</a> has the detail. Your draft stays in this browser until you submit. Questions? Email {esc(CONTACT_EMAIL)}</p>
  <a href="/training-plans/">Back to training plans</a> &middot;
  <a href="/privacy/">Privacy</a> &middot;
  <a href="/terms/">Terms</a>
</footer>
{build_cookie_banner()}
{build_js()}
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs /goals/ page")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_path = out_dir / "goals" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_content = generate_page()
    out_path.write_text(html_content, encoding="utf-8")
    print(f"Generated: {out_path} ({len(html_content):,} bytes) -> /goals/")


if __name__ == "__main__":
    main()
