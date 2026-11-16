#!/usr/bin/env python3
"""Generate the custom ski plan questionnaire and buy button at /questionnaire/.

The page asks exactly what the ski engine's v2 intake needs
(``xc-skier-intake/v2``: athletes/scripts/ski_intake.py in
athlete-custom-training-plan-pipeline, questions from
docs/plans/XC_SKIER_QUESTIONNAIRE.md there), builds that object in the
browser, and posts it to the checkout server with
``product: race_plan_4weekly``. The server dry-runs the ski engine and bills
exactly the weeks it builds; a refusal comes back as 400 ``{error, reason}``
and the page shows the skier a plain message for that code. Nothing is
defaulted: every field the schema needs is asked, and ``null`` or ``[]`` is
only sent when the skier said "none".

Privacy: the engine intake never carries an email address, phone number or
free text. The email goes to the checkout server only as the top-level
``email``; ``athlete_id`` is random.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = PROJECT_ROOT / "output"
RACE_INDEX = PROJECT_ROOT / "web" / "race-index.json"
TOKENS_CSS = PROJECT_ROOT / "tokens" / "tokens.css"
EVENT_CATALOG = PROJECT_ROOT / "data" / "ski-event-catalog.json"

sys.path.insert(0, str(SCRIPT_DIR))
import plan_offer  # noqa: E402
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
from consent import get_consent_banner_html, get_ga4_head  # noqa: E402

SCHEMA_VERSION = "xc-skier-intake/v2"
STORAGE_KEY = "xcskilabs_ski_intake_v2"


def esc(text: Any) -> str:
    if text is None or text == "":
        return ""
    return html.escape(str(text), quote=True)


def _safe_json_for_script(obj: Any, **kwargs: Any) -> str:
    return json.dumps(obj, **kwargs).replace("</", "<\\/")


def load_tokens_css() -> str:
    return TOKENS_CSS.read_text(encoding="utf-8").strip()


def load_race_slug_map(index_path: Path = RACE_INDEX) -> dict[str, str]:
    """Load a compact slug-to-name map from web/race-index.json."""
    if not index_path.exists():
        return {}
    data = json.loads(index_path.read_text(encoding="utf-8"))
    slug_map: dict[str, str] = {}
    for race in data.get("races", []):
        slug = race.get("s")
        name = race.get("dn") or race.get("n")
        if slug and name:
            slug_map[str(slug)] = str(name)
    return dict(sorted(slug_map.items()))


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
a { color: var(--gl-swix-red); }
a:hover { color: var(--gl-carbon); }
a:focus-visible,
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible {
  outline: 3px solid var(--gl-swix-red);
  outline-offset: 2px;
}
.gl-skip-link {
  position: absolute;
  left: -999px;
  top: 8px;
  background: var(--gl-white);
  color: var(--gl-carbon);
  padding: 8px 12px;
  z-index: 10000;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
}
.gl-skip-link:focus { left: 8px; }
.gl-nav {
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--gl-carbon);
  border-bottom: 3px solid var(--gl-swix-red);
  padding: 0 20px;
}
.gl-nav-inner {
  max-width: var(--gl-measure);
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 52px;
}
.gl-nav-logo {
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--gl-white);
  text-decoration: none;
  letter-spacing: 0.1em;
}
.gl-nav-links {
  display: flex;
  gap: 18px;
  align-items: center;
}
.gl-nav-links a {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  color: var(--gl-muted);
  text-decoration: none;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.gl-nav-links a:hover,
.gl-nav-links a.active { color: var(--gl-white); }
.gl-page {
  max-width: 760px;
  margin: 0 auto;
  padding: 0 20px 80px;
}
.gl-page-header {
  padding: 48px 0 28px;
  border-bottom: 2px solid var(--gl-hairline);
  margin-bottom: 24px;
}
.gl-kicker {
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--gl-swix-red);
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 12px;
}
.gl-page-header h1 {
  font-family: var(--gl-font-display);
  font-size: clamp(2.2rem, 8vw, 4.4rem);
  font-style: italic;
  font-weight: 900;
  line-height: 0.96;
  text-transform: uppercase;
  margin: 0 0 14px;
}
.gl-page-header p {
  font-size: 1.08rem;
  color: var(--gl-muted);
  margin: 0;
  max-width: 62ch;
}
.gl-progress-wrap {
  position: sticky;
  top: 52px;
  z-index: 900;
  background: var(--gl-white);
  border: 2px solid var(--gl-carbon);
  margin-bottom: 28px;
  padding: 12px;
}
.gl-progress-inner {
  display: flex;
  align-items: center;
  gap: 12px;
}
.gl-progress-label,
.gl-progress-pct,
.gl-save-indicator {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--gl-muted);
  white-space: nowrap;
}
.gl-progress-track {
  flex: 1;
  height: 8px;
  background: var(--gl-hairline);
  border: 1px solid var(--gl-muted);
}
.gl-progress-fill {
  height: 100%;
  width: 0;
  background: var(--gl-swix-red);
  transition: width 0.2s ease;
}
.gl-save-indicator {
  opacity: 0;
  transition: opacity 0.15s ease;
}
.gl-save-indicator.show { opacity: 1; }
.gl-form { margin: 0; }
.gl-section {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  margin-bottom: 28px;
}
.gl-section-header {
  background: var(--gl-carbon);
  color: var(--gl-white);
  padding: 14px 18px;
  display: flex;
  align-items: center;
  gap: 12px;
}
.gl-section-num {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  font-weight: 700;
  background: var(--gl-swix-red);
  color: var(--gl-white);
  padding: 3px 8px;
  letter-spacing: 0.08em;
}
.gl-section-title {
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.gl-section-body { padding: 22px 18px; }
.gl-field { margin-bottom: 18px; }
.gl-field:last-child { margin-bottom: 0; }
.gl-field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.gl-field label,
.gl-label {
  display: block;
  font-family: var(--gl-font-data);
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 6px;
}
.req { color: var(--gl-swix-red); }
input[type="text"],
input[type="email"],
input[type="number"],
input[type="date"],
select,
textarea {
  width: 100%;
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  padding: 10px 12px;
}
textarea {
  min-height: 116px;
  resize: vertical;
}
.gl-hint {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  color: var(--gl-muted);
  margin-top: 4px;
}
.gl-radio-group,
.gl-checkbox-group,
.gl-scale-group {
  display: grid;
  gap: 8px;
}
.gl-radio-group,
.gl-checkbox-group {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.gl-scale-group {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}
.gl-choice {
  min-height: 44px;
  border: 1px solid var(--gl-hairline);
  padding: 9px 10px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--gl-font-data);
  font-size: 0.78rem;
  cursor: pointer;
}
.gl-choice:hover { border-color: var(--gl-swix-red); }
.gl-choice input { accent-color: var(--gl-swix-red); }
.gl-conditional {
  display: none;
  margin-top: 12px;
  padding-left: 14px;
  border-left: 3px solid var(--gl-swix-red);
}
.gl-conditional.visible { display: block; }
.gl-submit-wrap {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  padding: 22px 18px;
}
.gl-submit-btn {
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-swix-red);
  color: var(--gl-white);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--gl-font-data);
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 12px 18px;
}
.gl-submit-btn:hover { background: var(--gl-carbon); }
.gl-submit-note {
  color: var(--gl-muted);
  font-size: 0.95rem;
  margin: 12px 0 0;
}
.gl-success-message {
  border: 3px solid var(--gl-carbon);
  background: var(--gl-white);
  padding: 28px;
  margin: 36px 0;
}
.gl-success-message h2 {
  font-family: var(--gl-font-display);
  font-style: italic;
  font-weight: 900;
  text-transform: uppercase;
  line-height: 0.98;
  margin: 0 0 12px;
}
.gl-footer {
  max-width: 760px;
  margin: 0 auto;
  padding: 34px 20px 60px;
  color: var(--gl-muted);
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
@media (max-width: 700px) {
  .gl-nav-inner { align-items: flex-start; flex-direction: column; padding: 12px 0; }
  .gl-nav-links { flex-wrap: wrap; gap: 12px; }
  .gl-progress-wrap { top: 86px; }
  .gl-field-row,
  .gl-radio-group,
  .gl-checkbox-group,
  .gl-scale-group {
    grid-template-columns: 1fr;
  }
}
"""


def build_ga4() -> str:
    """The shared region-aware consent head (scripts/consent.py)."""
    return get_ga4_head()


def build_nav() -> str:
    return """<nav class="gl-nav" aria-label="Primary">
  <div class="gl-nav-inner">
    <a href="/" class="gl-nav-logo"><img class="gl-brand-mark" src="/xc-logo.svg" alt="" width="30" height="30"><span class="gl-brand-name">XC SKI <em>LABS</em></span></a>
    <div class="gl-nav-links">
      <a href="/search/">Races</a>
      <a href="/guide/">Guide</a>
      <a href="/course/">Course</a>
      <a href="/training-plans/" class="active">Plans</a>
      <a href="/coaching/">Coaching</a>
      <a href="/about/">About</a>
    </div>
  </div>
</nav>"""


# ── Checkout refusals: one plain message per code the server can send ──
#
# Codes come from webhook/app.py ``_create_race_plan_4weekly_checkout`` and
# ``_rp_ski_target`` (ski_intake.validate / holds, ski_engine.build_plan).
# Every message says nothing was charged, because a refusal always comes
# before Stripe. "{contact}" becomes a mailto link to Matti.

NOT_CHARGED = "Nothing was charged."
SAVED_NOTE = "Your answers are saved in this browser, so you won't have to fill them in again."

UNAVAILABLE_CODES = (
    "offer_disabled",
    "training_plan_generation_disabled",
    "rider_sender_not_configured",
    "race_plan_emails_not_built",
    "stripe_key_missing",
    "brand_stripe_account_missing",
    "live_stripe_key_refused",
    "payment_method_configuration_missing",
    "cancel_page_not_configured",
)
BUILD_ERROR_CODES = (
    "bodyweight_swap_missing",
    "strength_session_missing",
    "drill_missing",
    "safety_session_missing",
    "recovery_on_demand_unconfirmed",
    "recovery_on_demand_not_a_load_week",
)
RACE_FACT_CODES = ("event_unknown", "event_facts_stale", "event_technique_mismatch")
DRYLAND_CODES = ("no_hard_dryland_modality", "no_easy_dryland_modality")

_UNAVAILABLE = ("Sign-ups for this plan aren't open yet, so I couldn't take your order. "
                f"{NOT_CHARGED}")
_BUILD_ERROR = ("I couldn't build a plan from these answers. "
                f"{NOT_CHARGED} Email me at {{contact}} with your race and start week.")
_RACE_FACTS = ("I can't confirm that race's details right now. Choose “My race isn't "
               "listed” and enter its date, distance and technique yourself. "
               f"{NOT_CHARGED}")
_DRYLAND = ("Before you're on snow, the plan needs rollerskis, running or a SkiErg to train "
            "on, and your answers leave days with none of them. "
            f"{NOT_CHARGED}")

REFUSALS: dict[str, str] = {
    **{code: _UNAVAILABLE for code in UNAVAILABLE_CODES},
    **{code: _BUILD_ERROR for code in BUILD_ERROR_CODES},
    **{code: _RACE_FACTS for code in RACE_FACT_CODES},
    **{code: _DRYLAND for code in DRYLAND_CODES},
    "plan_start_out_of_range": (
        "Week 1 has to start this week or next week, and the start you picked no longer "
        f"fits. Pick your start week again and press the button once more. {NOT_CHARGED}"),
    "race_name_required": f"Tell me the name of your race. {NOT_CHARGED}",
    "juniors_not_built": f"I only build these plans for skiers 18 and older. {NOT_CHARGED}",
    "first_season_not_built": (
        "I build these plans for skiers with at least one full winter on skis, so I can't "
        f"build one for a first season. {NOT_CHARGED}"),
    "season_not_built": (
        "I only build plans for races from December to April. Check the date of your "
        f"race. {NOT_CHARGED}"),
    "plan_too_short": (
        "Your race is too close for a plan. I need at least two weeks, counting race "
        f"week. {NOT_CHARGED}"),
    "plan_too_long": (
        "Your race is more than 52 weeks away. I can build your plan once it's within a "
        f"year. {NOT_CHARGED}"),
    "no_test_mode": (
        "The plan sets your training zones with a test on rollerskis or a run. With no "
        f"rollerskis and no running, I can't build it. {NOT_CHARGED}"),
    "rest_days": (
        "Recreational skiers need two full days off a week, everyone else one, and "
        "your week has fewer. Mark another day as one you can't train, or pick a rest day. "
        f"{NOT_CHARGED}"),
    "ski_gate_failed": (
        "These answers build a plan that doesn't pass my own checks, so I won't sell it. "
        f"{NOT_CHARGED} Email me at {{contact}} with your race and start week."),
    "ski_intake_invalid": (
        "Some of your answers didn't go through, so I couldn't build your plan. "
        f"{NOT_CHARGED} Check your answers and try again. If it happens again, email me "
        "at {contact}."),
    # Not reason codes: what the page shows for other server answers.
    "email_invalid": f"Check your email address. {NOT_CHARGED}",
    "name_required": f"Tell me what to call you. {NOT_CHARGED}",
    "rate_limited": f"That was a lot of tries in a row. Wait a minute, then try again. {NOT_CHARGED}",
    "network": f"I couldn't reach the payment page. {NOT_CHARGED} Wait a minute and try again.",
}

# Inline messages next to a question, before anything is sent.
ERRORS: dict[str, str] = {
    "required": "Answer this question.",
    "pick_one": "Pick at least one, or the “none” answer.",
    "name": "Enter a name, up to 40 characters, without an @.",
    "email": "Enter your email address.",
    "no_at": "Leave email addresses out of this answer.",
    "age": "Enter your age in whole years.",
    "juniors": "I only build these plans for skiers 18 and older.",
    "winters": "Enter a whole number from 0 to 80.",
    "first_season": "I build these plans for skiers with at least one full winter on skis.",
    "season_hours": "Enter a number of hours above 0 and up to 1,500.",
    "week_hours": "Enter a number of hours above 0 and up to 40.",
    "distance": "Enter the distance in kilometres, above 0 and up to 90.",
    "date": "Pick a date.",
    "last_race": "Your last race has to be on or before the day week 1 starts.",
    "every_day": "Pick an answer for every day.",
    "a_day": "Pick at least one day you can train.",
    "long_day": "Pick one of the days you can train.",
    "rest_one": "Pick 1 day to take off completely.",
    "rest_two": "Pick 2 days to take off completely.",
    "snow_order": "The last snow date has to be after the first.",
    "rows_race": "Fill in the date, distance and technique for each race, or remove it.",
    "rows_date": "Pick a date for each row, or remove it.",
    "too_many_races": "List up to 10 races.",
    "bpm": "Enter a whole number from 120 to 230.",
    "hr_month": "Pick a month in the 3 years before week 1.",
}
FORM_SUMMARY_ERROR = "A few answers need fixing before I can build your plan. They're marked below."

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
DAY_CAP_OPTIONS = (
    ("0", "Can't train"), ("30", "30 min"), ("45", "45 min"), ("60", "1 hour"),
    ("90", "1 hour 30"), ("120", "2 hours"), ("150", "2 hours 30"), ("180", "3 hours"),
    ("240", "4 hours or more"),
)
TECHNIQUES = (("classic", "Classic"), ("skate", "Skate"), ("skiathlon", "Skiathlon"))
LEVELS = (
    ("recreational", "I ski for fitness and enter a race or two. I don't train for them all year."),
    ("keen_racer", "I train for my races most of the year and care about my result."),
    ("top_amateur", "I race near the front of my wave or age group and train year-round for it."),
)
GEAR = (
    ("rollerski_classic", "Classic rollerskis"),
    ("rollerski_skate", "Skate rollerskis"),
    ("ski_erg", "A SkiErg"),
    ("cycling", "A bike, indoor or outdoor"),
)
LIFTS = (
    ("goblet_squat", "Goblet squat"),
    ("romanian_deadlift", "Romanian deadlift"),
    ("supported_split_squat", "Split squat"),
    ("dumbbell_bench_press", "Dumbbell bench press"),
    ("lat_pulldown", "Lat pulldown"),
    ("seated_row", "Seated row"),
)
INJURIES = (
    ("current_injury", "An injury right now"),
    ("deep_squat", "Deep squat"),
    ("single_leg_balance", "Balancing on one leg"),
    ("push_up", "Push-ups"),
    ("hip", "Hips"),
    ("lower_back", "Lower back"),
    ("shoulder", "Shoulders"),
)


def load_event_catalog(path: Path = EVENT_CATALOG) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {"max_age_days": int(data["max_age_days"]), "events": list(data["events"])}


def _short_date(iso: str) -> str:
    from datetime import date
    d = date.fromisoformat(iso)
    return f"{d.strftime('%b')} {d.day}, {d.year}"


EXTRA_CSS = """
[hidden] { display: none !important; }
.gl-section-header h2 { margin: 0; }
input[type="month"] {
  width: 100%;
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-paper);
  color: var(--gl-carbon);
  font-family: var(--gl-font-data);
  font-size: 0.9rem;
  padding: 10px 12px;
}
fieldset.gl-field { border: 0; padding: 0; margin: 0 0 18px; min-width: 0; }
fieldset.gl-field legend { padding: 0; }
.gl-field .gl-q-text {
  font-family: var(--gl-font-editorial);
  font-size: 1.02rem;
  font-weight: 700;
  line-height: 1.4;
  text-transform: none;
  letter-spacing: 0;
  margin-bottom: 8px;
  display: block;
}
.gl-radio-group.gl-stack,
.gl-checkbox-group.gl-stack { grid-template-columns: 1fr; }
.gl-field label.gl-choice {
  display: flex;
  margin: 0;
  font-family: var(--gl-font-editorial);
  font-size: 0.95rem;
  font-weight: 400;
  letter-spacing: 0;
  line-height: 1.35;
  text-transform: none;
}
.gl-field-error {
  display: none;
  margin-top: 6px;
  font-family: var(--gl-font-data);
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--gl-swix-red);
}
.gl-field.has-error .gl-field-error { display: block; }
.gl-field.has-error input,
.gl-field.has-error select { border-color: var(--gl-swix-red); }
.gl-days {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}
.gl-day label {
  font-family: var(--gl-font-data);
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
  display: block;
}
.gl-day select { padding: 8px 4px; font-size: 0.78rem; }
.gl-rows { display: grid; gap: 10px; margin-top: 10px; }
.gl-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 8px;
  align-items: end;
}
.gl-row--date { grid-template-columns: 1fr auto; }
.gl-row label {
  font-family: var(--gl-font-data);
  font-size: 0.68rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  display: block;
  margin-bottom: 4px;
}
.gl-link-btn {
  min-height: 44px;
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  color: var(--gl-carbon);
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  padding: 8px 12px;
  cursor: pointer;
}
.gl-link-btn:hover { border-color: var(--gl-swix-red); color: var(--gl-swix-red); }
.gl-offer {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-white);
  padding: 18px;
  margin-bottom: 28px;
}
.gl-offer-price {
  font-family: var(--gl-font-display);
  font-style: italic;
  font-weight: 900;
  text-transform: uppercase;
  font-size: 1.6rem;
  line-height: 1;
  margin: 0 0 10px;
}
.gl-offer ul { margin: 0; padding-left: 1.1em; }
.gl-offer li { margin-bottom: 4px; }
.gl-offer h2 {
  font-family: var(--gl-font-data);
  font-size: 0.76rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin: 16px 0 6px;
}
.gl-notice {
  border: 2px solid var(--gl-hairline);
  background: var(--gl-paper);
  padding: 12px 14px;
  margin-bottom: 18px;
  font-size: 0.95rem;
}
.gl-quote {
  border: 2px solid var(--gl-carbon);
  background: var(--gl-paper);
  padding: 14px;
  margin: 6px 0 18px;
  font-family: var(--gl-font-data);
  font-size: 0.85rem;
  line-height: 1.5;
}
.gl-quote strong { font-size: 1rem; }
.gl-terms { margin: 0 0 16px; padding-left: 1.1em; font-size: 0.92rem; }
.gl-terms li { margin-bottom: 4px; }
.gl-alert {
  display: none;
  border: 3px solid var(--gl-swix-red);
  background: var(--gl-white);
  padding: 14px 16px;
  margin: 0 0 16px;
  font-size: 1rem;
}
.gl-alert.show { display: block; }
.gl-alert p { margin: 0; }
.gl-alert p + p { margin-top: 8px; }
.gl-alert .gl-alert-title {
  font-family: var(--gl-font-data);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--gl-swix-red);
  margin-bottom: 6px;
}
.gl-submit-btn[disabled] { opacity: 0.6; cursor: wait; }
.gl-continue { display: inline-flex; margin-top: 12px; text-decoration: none; }
@media (max-width: 700px) {
  .gl-row { grid-template-columns: 1fr 1fr; }
}
"""


# ── Form building blocks ──

def _error(qid: str) -> str:
    return f'<div class="gl-field-error" data-error-for="{esc(qid)}"></div>'


def _hint(text: str) -> str:
    return f'<div class="gl-hint">{esc(text)}</div>' if text else ""


def choice_field(qid: str, question: str, name: str, options, *, kind: str = "radio",
                 stack: bool = False, hint: str = "", extra: str = "",
                 hidden: bool = False) -> str:
    group = "gl-checkbox-group" if kind == "checkbox" else "gl-radio-group"
    if stack:
        group += " gl-stack"
    items = "".join(
        f'<label class="gl-choice"><input type="{kind}" name="{esc(name)}" value="{esc(v)}"> '
        f'{esc(label)}</label>'
        for v, label in options
    )
    hide = " hidden" if hidden else ""
    return (f'<fieldset class="gl-field" data-q="{esc(qid)}"{hide}>'
            f'<legend class="gl-q-text">{esc(question)}</legend>'
            f'<div class="{group}">{items}</div>{extra}{_hint(hint)}{_error(qid)}</fieldset>')


def input_field(qid: str, question: str, control: str, *, hint: str = "",
                hidden: bool = False) -> str:
    hide = " hidden" if hidden else ""
    return (f'<div class="gl-field" data-q="{esc(qid)}"{hide}>'
            f'<label class="gl-q-text" for="{esc(qid)}">{esc(question)}</label>'
            f'{control}{_hint(hint)}{_error(qid)}</div>')


def yes_no(qid: str, question: str, name: str, *, hint: str = "", hidden: bool = False,
           yes: str = "Yes", no: str = "No") -> str:
    return choice_field(qid, question, name, (("yes", yes), ("no", no)), hint=hint,
                        hidden=hidden)


def section(num: int, title: str, body: str) -> str:
    return f"""<section class="gl-section" data-section="{num}">
  <div class="gl-section-header">
    <div class="gl-section-num">{num:02d}</div>
    <h2 class="gl-section-title">{esc(title)}</h2>
  </div>
  <div class="gl-section-body">{body}</div>
</section>"""


def race_options(catalog: dict[str, Any]) -> list[tuple[str, str]]:
    options = []
    for e in catalog["events"]:
        label = (f"{e['name']}, {e['technique']}, {e['distance_km']:g} km, "
                 f"{_short_date(e['event_date'])}")
        options.append((e["event_id"], label))
    options.append(("own", "My race isn't listed"))
    return options


def build_offer_box() -> str:
    fit = "".join(f"<li>{esc(line)}</li>" for line in plan_offer.FIT_LINES)
    return f"""<aside class="gl-offer" aria-label="The plan">
  <p class="gl-offer-price">{esc(plan_offer.PRICE_LINE)}</p>
  <p>{esc(plan_offer.BLOCK_LINE)} {esc(plan_offer.ENDS_LINE)}</p>
  <h2>I build this plan for</h2>
  <ul>{fit}</ul>
</aside>"""


def build_form(catalog: dict[str, Any]) -> str:
    race_q = choice_field("race_choice", "Which race is this plan for?", "race_choice",
                          race_options(catalog), stack=True)
    own_race = f"""<div class="gl-conditional" id="ownRace">
      {input_field("race_name", "What's the race called?",
                   '<input id="race_name" name="race_name" type="text" maxlength="100" autocomplete="off">')}
      {input_field("race_date", "What date is the race?",
                   '<input id="race_date" name="race_date" type="date">')}
      {input_field("race_km", "How long is it, in kilometres?",
                   '<input id="race_km" name="race_km" type="number" min="0.1" max="90" step="0.1" inputmode="decimal">')}
      {choice_field("race_technique", "Classic, skate or skiathlon?", "race_technique", TECHNIQUES)}
    </div>"""
    b_races = choice_field(
        "b_races", "Are you doing any other races this season?", "b_races_answer",
        (("none", "No other races"), ("some", "Yes, I'll list them")), stack=True,
        extra='<div class="gl-conditional" id="bRacesWrap"><div class="gl-rows" id="bRaces"></div>'
              '<button type="button" class="gl-link-btn" id="addBRace">Add a race</button></div>')
    start_q = choice_field(
        "plan_start", "When should week 1 start?", "plan_start",
        (("this", "This week"), ("next", "Next week")), stack=True,
        hint="Your first payment is taken today either way.")
    last_race = input_field(
        "last_race_on", "When was your last race this past season?",
        '<input id="last_race_on" name="last_race_on" type="date">',
        hint="I ask because your plan starts in spring, and it should give you time off after that race.",
        hidden=True)

    days = "".join(
        f'<div class="gl-day"><label for="cap_{i}">{esc(day)}</label>'
        f'<select id="cap_{i}" name="cap_{i}"><option value="">Pick</option>'
        + "".join(f'<option value="{v}">{esc(label)}</option>' for v, label in DAY_CAP_OPTIONS)
        + "</select></div>"
        for i, day in enumerate(DAYS)
    )
    day_caps = (f'<fieldset class="gl-field" data-q="day_caps"><legend class="gl-q-text">'
                f'For each day, can you train? If yes, what&rsquo;s the longest session that '
                f'fits that day?</legend><div class="gl-days">{days}</div>{_error("day_caps")}</fieldset>')
    long_day = input_field(
        "long_session_day", "Which day suits your long session best?",
        '<select id="long_session_day" name="long_session_day"><option value="">Pick a day</option></select>')
    rest_days = choice_field(
        "rest_days", "Which day do you want completely off?", "rest_day",
        [(str(i), d) for i, d in enumerate(DAYS)], kind="checkbox", hidden=True,
        hint="Recreational skiers get two full days off a week, everyone else at least one. "
             "Your days above leave fewer than that.")
    rest_swap = yes_no(
        "rest_day_swap",
        "In hard weeks, would you rather do 30 easy minutes than take the day fully off?",
        "rest_day_swap", hidden=True)
    blocked = choice_field(
        "blocked_dates", "Are there dates you can't train at all, for travel, work or family?",
        "blocked_answer", (("none", "No"), ("some", "Yes, I'll list them")), stack=True,
        extra='<div class="gl-conditional" id="blockedWrap"><div class="gl-rows" id="blockedRows"></div>'
              '<button type="button" class="gl-link-btn" id="addBlocked">Add a date</button></div>')

    gear = choice_field(
        "gear", "Which of these do you have?", "gear",
        list(GEAR) + [("none", "None of these")], kind="checkbox", stack=True)
    rs_route = yes_no("rollerski_safe_route", "Do you have a safe road or path to rollerski on?",
                      "rollerski_safe_route", hidden=True)
    rs_exp = choice_field(
        "rollerski_experience", "How much have you rollerskied?", "rollerski_experience",
        (("never", "Never"), ("a_few_times", "A few times"), ("one_summer", "One summer"),
         ("several_summers", "Several summers")), hidden=True)
    running = choice_field(
        "running_tolerance", "Can you run without pain?", "running_tolerance",
        (("any", "Yes, any run"), ("short_easy_only", "Short easy runs only"),
         ("none", "No running")))

    hr_monitor = choice_field(
        "hr_monitor", "Do you train with a heart-rate monitor?", "hr_monitor",
        (("chest_strap", "Chest strap"), ("wrist_only", "Watch or arm band only"),
         ("none", "None")))
    max_hr_detail = f"""<div class="gl-conditional" id="maxHrDetail">
      {input_field("hr_bpm", "What was the number?",
                   '<input id="hr_bpm" name="hr_bpm" type="number" min="120" max="230" step="1" inputmode="numeric">',
                   hint="Beats per minute, from your chest strap.")}
      {input_field("hr_month", "Which month was it?", '<input id="hr_month" name="hr_month" type="month">')}
      {choice_field("hr_mode", "Classic or skate?", "hr_mode", (("classic", "Classic"), ("skate", "Skate")))}
      {choice_field("hr_source", "From a test or a race?", "hr_source",
                    (("test", "An all-out test"), ("race", "A hard race")))}
    </div>"""
    max_hr = choice_field(
        "ski_max_hr",
        "In the last 3 years, have you seen your max heart rate on skis or rollerskis, "
        "from an all-out test or a hard race?",
        "ski_max_hr_answer", (("no", "No"), ("yes", "Yes")), hidden=True, extra=max_hr_detail)
    hr_medicine = yes_no("hr_medicine",
                         "Do you take a medicine that changes your heart rate, such as a beta blocker?",
                         "hr_medicine")

    strength_history = choice_field(
        "strength_history", "Over the last 12 months, how have you strength trained?",
        "strength_history",
        (("none", "None"), ("on_and_off", "On and off"),
         ("summer_regular", "At least once a week through most of last summer")), stack=True)
    strength_access = choice_field(
        "strength_access", "Where can you lift?", "strength_access",
        (("gym", "Gym with machines"), ("home_dumbbells", "Home with dumbbells"),
         ("bodyweight_only", "Bodyweight only")))
    med_ball = yes_no("medicine_ball", "Do you have a medicine ball you can throw?", "medicine_ball")
    lifts = choice_field(
        "familiar_lifts", "Which of these lifts can you do with good form today?", "familiar_lifts",
        list(LIFTS) + [("none", "None yet")], kind="checkbox")
    injuries = choice_field(
        "injury_flags", "Do you have an injury right now, or movements that hurt?", "injury_flags",
        list(INJURIES) + [("none", "None")], kind="checkbox",
        hint="An injury right now means I review your answers before your plan is built.")

    fuel = choice_field(
        "fuel_practised_g_per_h",
        "On your longest sessions, how many grams of carbohydrate an hour have you taken in "
        "without stomach trouble? Check the labels on what you use.",
        "fuel_practised_g_per_h",
        (("under_30", "Under 30"), ("30_60", "30–60"), ("60_90", "60–90"),
         ("90_120", "90–120"), ("never_counted", "I've never counted")))
    fuel_sessions = choice_field(
        "fuel_practised_sessions", "How many long sessions or races have you done at that amount?",
        "fuel_practised_sessions", (("0", "None yet"), ("1_2", "1–2"), ("3_plus", "3 or more")),
        hidden=True)

    health_notice = (
        '<p class="gl-notice">I only ask yes or no here, never details. If you answer yes to '
        'any of the first three, your plan waits until I&rsquo;ve reviewed your answers. How I store '
        'them is in the <a href="/privacy/">privacy policy</a>.</p>')
    illness = yes_no("recent_illness",
                     "Are you sick right now, or did an illness stop your training in the last 2 weeks?",
                     "recent_illness")
    red_s = choice_field(
        "health_review",
        "In the last 12 months, have you had a stress fracture, periods that stopped, or "
        "weight loss you didn't plan?",
        "health_review", (("yes", "Yes"), ("no", "No"), ("rather_not_say", "I'd rather not say")))
    heart = yes_no("health_note",
                   "Is there anything about your heart or lungs I should know, such as asthma "
                   "or a heart condition?",
                   "health_note")
    # Engine AE-SKI-4.1 (heat sessions): I4 access, I5 health question.
    heat_access = choice_field(
        "heat_access", "Do you have a sauna, or a bath you can fill to your shoulders, that you "
        "could use straight after training?", "heat_access",
        (("sauna", "Sauna"), ("hot_bath", "Bath"), ("none", "Neither")), kind="checkbox")
    heat_health = yes_no("heat_health_flag",
                         "Has a doctor told you to avoid saunas or hot baths, are you pregnant, "
                         "or have you ever fainted in a sauna or hot bath?",
                         "heat_health_flag",
                         hint="A yes means your plan has no heat sessions. It doesn't hold up your plan.")

    terms = "".join(f"<li>{esc(line)}</li>" for line in (
        plan_offer.BLOCK_LINE, plan_offer.LAST_BLOCK_LINE, plan_offer.ENDS_LINE,
        plan_offer.CANCEL_LINE, plan_offer.REFUND_LINE))

    return f"""<form id="planIntake" class="gl-form" novalidate>
  {section(1, "Your race", race_q + own_race + b_races)}
  {section(2, "Your start", start_q + last_race)}
  {section(3, "About you", input_field("display_name", "What should I call you?",
      '<input id="display_name" name="display_name" type="text" maxlength="40" autocomplete="given-name">')
    + input_field("age_years", "How old are you?",
      '<input id="age_years" name="age_years" type="number" min="1" max="100" step="1" inputmode="numeric">')
    + choice_field("level", "Which sounds most like you?", "level", LEVELS, stack=True)
    + input_field("winters_on_snow", "How many winters have you skied classic or skate, not counting this one?",
      '<input id="winters_on_snow" name="winters_on_snow" type="number" min="0" max="80" step="1" inputmode="numeric">'))}
  {section(4, "Your last 12 months", input_field("last_season_hours",
      "About how many hours did you train in the last 12 months, counting skiing, rollerskiing, running, biking and strength?",
      '<input id="last_season_hours" name="last_season_hours" type="number" min="1" max="1500" step="1" inputmode="numeric">')
    + choice_field("last_season_hours_basis", "Is that from a training log or your best guess?",
      "last_season_hours_basis", (("logged", "From a training log"), ("estimate", "My best guess")))
    + choice_field("layoff", "In the last 12 months, did you have 4 weeks or more with little or no training?",
      "layoff_answer", (("no", "No"), ("yes", "Yes")),
      extra='<div class="gl-conditional" id="layoffWrap">' + input_field(
          "layoff_restart", "When did you start back?",
          '<input id="layoff_restart" name="layoff_restart" type="date">') + '</div>'))}
  {section(5, "Your week", input_field("available_hours",
      "How many hours a week can you keep up for months at a time, not only in your biggest week?",
      '<input id="available_hours" name="available_hours" type="number" min="0.5" max="40" step="0.5" inputmode="decimal">')
    + day_caps + long_day + rest_days + rest_swap + blocked)}
  {section(6, "Snow and dryland", input_field("snow_from",
      "This winter, from what date can you usually ski on snow near home?",
      '<input id="snow_from" name="snow_from" type="date">')
    + input_field("snow_until", "And until what date?", '<input id="snow_until" name="snow_until" type="date">')
    + gear + rs_route + rs_exp + running + heat_access)}
  {section(7, "Heart rate", hr_monitor + max_hr + hr_medicine)}
  {section(8, "Strength", strength_history + strength_access + med_ball + lifts + injuries)}
  {section(9, "Fueling", fuel + fuel_sessions)}
  {section(10, "Health", health_notice + illness + red_s + heart + heat_health)}
  <section class="gl-section" data-section="11">
    <div class="gl-section-header">
      <div class="gl-section-num">11</div>
      <h2 class="gl-section-title">Your plan and payment</h2>
    </div>
    <div class="gl-section-body">
      {input_field("email", "What email should I send your plan to?",
        '<input id="email" name="email" type="email" maxlength="254" autocomplete="email">')}
      <div class="gl-quote" id="quote" aria-live="polite">Pick your race and when week 1 starts to see your payments.</div>
      <ul class="gl-terms">{terms}</ul>
      <div class="gl-alert" id="formAlert" role="alert" tabindex="-1"></div>
      <button type="submit" class="gl-submit-btn" id="submitBtn">Continue to payment</button>
      <p class="gl-submit-note">You&rsquo;ll see the full terms on the payment page before you pay.</p>
    </div>
  </section>
</form>"""


def build_cookie_banner() -> str:
    """The shared consent banner and Privacy choices link (scripts/consent.py)."""
    return get_consent_banner_html()


def page_config(slug_map: dict[str, str], catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "endpoint": plan_offer.CHECKOUT_ENDPOINT,
        "product": plan_offer.PRODUCT,
        "schemaVersion": SCHEMA_VERSION,
        "storageKey": STORAGE_KEY,
        "contact": plan_offer.CONTACT_EMAIL,
        "blockWeeks": plan_offer.BLOCK_WEEKS,
        "blockCents": plan_offer.BLOCK_PRICE_CENTS,
        "weekCents": plan_offer.WEEK_PRICE_CENTS,
        "catalog": catalog,
        "races": slug_map,
        "refusals": REFUSALS,
        "unavailable": list(UNAVAILABLE_CODES),
        "errors": ERRORS,
        "summaryError": FORM_SUMMARY_ERROR,
        "savedNote": SAVED_NOTE,
        "days": list(DAYS),
    }


QUESTIONNAIRE_JS = r"""
(function() {
  'use strict';
  var CFG = JSON.parse(document.getElementById('xc-plan-config').textContent);
  var form = document.getElementById('planIntake');
  if (!form) return;
  var params = new URLSearchParams(window.location.search);
  var races = CFG.races;
  var alertBox = document.getElementById('formAlert');
  var submitBtn = document.getElementById('submitBtn');
  var quoteEl = document.getElementById('quote');
  var busy = false;

  // ── Goals funnel token (read before GA4 by the head script) ──
  var goalsMode = params.get('src') === 'goals';
  var goalToken = goalsMode ? ((window.history.state && window.history.state.goalToken) || '') : '';
  if (goalsMode && !goalToken) {
    try {
      goalToken = sessionStorage.getItem('xc_goal_prefill_token') || '';
      sessionStorage.removeItem('xc_goal_prefill_token');
    } catch (e) {}
  }
  if (!/^[A-Za-z0-9_-]{16,64}$/.test(goalToken)) goalToken = '';
  var storageKey = goalsMode ? (goalToken ? 'xc_goal_draft_' + goalToken : '') : CFG.storageKey;
  var store = null;
  try { store = goalsMode ? window.sessionStorage : window.localStorage; } catch (e) { store = null; }

  // ── Dates (local calendar days; ISO strings) ──
  function pad(n) { return (n < 10 ? '0' : '') + n; }
  function iso(d) { return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()); }
  function parseIso(s) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s || '')) return null;
    var p = s.split('-');
    var d = new Date(+p[0], +p[1] - 1, +p[2]);
    return d.getMonth() === +p[1] - 1 ? d : null;
  }
  function mondayOf(d) {
    var x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
    x.setDate(x.getDate() - (x.getDay() + 6) % 7);
    return x;
  }
  function addDays(d, n) { var x = new Date(d.getTime()); x.setDate(x.getDate() + n); return x; }
  function daysBetween(a, b) { return Math.round((b - a) / 86400000); }
  function nice(d) {
    return d.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' });
  }
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var startDates = { 'this': mondayOf(today), 'next': addDays(mondayOf(today), 7) };
  Array.prototype.forEach.call(form.querySelectorAll('input[name="plan_start"]'), function(input) {
    var d = startDates[input.value];
    input.parentNode.lastChild.textContent = ' ' + (input.value === 'this' ? 'This week' : 'Next week') +
      ', from ' + nice(d);
  });

  // ── Verified races: only offered while their facts are fresh ──
  var catalog = {};
  CFG.catalog.events.forEach(function(e) {
    var verified = parseIso(e.verified_on);
    var input = form.querySelector('input[name="race_choice"][value="' + e.event_id + '"]');
    if (!input) return;
    if (!verified || daysBetween(verified, today) > CFG.catalog.max_age_days) {
      input.parentNode.parentNode.removeChild(input.parentNode);
    } else {
      catalog[e.event_id] = e;
    }
  });

  // ── Small helpers ──
  function el(id) { return document.getElementById(id); }
  function radio(name) {
    var c = form.querySelector('input[name="' + name + '"]:checked');
    return c ? c.value : '';
  }
  function checked(name) {
    return Array.prototype.map.call(form.querySelectorAll('input[name="' + name + '"]:checked'),
      function(c) { return c.value; });
  }
  function text(id) { var f = el(id); return f ? String(f.value || '').trim() : ''; }
  function show(id, on) {
    // The question's wrapper first: a question whose input has the same id
    // (last_race_on) starts hidden in its wrapper, and showing the input
    // alone left the required question invisible.
    var node = form.querySelector('[data-q="' + id + '"]') || el(id);
    if (!node) return;
    if (node.classList.contains('gl-conditional')) node.classList.toggle('visible', !!on);
    else node.hidden = !on;
  }
  function wholeNumber(s) { return /^\d+$/.test(s) ? parseInt(s, 10) : null; }
  function number(s) {
    if (!/^\d+(\.\d+)?$/.test(s)) return null;
    var n = parseFloat(s);
    return isFinite(n) ? n : null;
  }

  // ── Repeating rows: other races and blocked dates ──
  function techniqueSelect() {
    return '<select data-k="technique"><option value="">Pick</option>' +
      '<option value="classic">Classic</option><option value="skate">Skate</option>' +
      '<option value="skiathlon">Skiathlon</option></select>';
  }
  function addRow(containerId, kind, values) {
    var box = el(containerId);
    if (!box) return;
    if (kind === 'race' && box.children.length >= 10) return;
    var row = document.createElement('div');
    row.className = 'gl-row' + (kind === 'date' ? ' gl-row--date' : '');
    if (kind === 'race') {
      row.innerHTML = '<div><label>Date</label><input type="date" data-k="date"></div>' +
        '<div><label>Km</label><input type="number" min="0.1" max="90" step="0.1" data-k="distance_km"></div>' +
        '<div><label>Technique</label>' + techniqueSelect() + '</div>' +
        '<button type="button" class="gl-link-btn" data-remove>Remove</button>';
    } else {
      row.innerHTML = '<div><label>Date</label><input type="date" data-k="date"></div>' +
        '<button type="button" class="gl-link-btn" data-remove>Remove</button>';
    }
    if (values) {
      Array.prototype.forEach.call(row.querySelectorAll('[data-k]'), function(f) {
        var v = values[f.getAttribute('data-k')];
        if (v !== undefined && v !== null) f.value = v;
      });
    }
    box.appendChild(row);
  }
  function rows(containerId) {
    var box = el(containerId);
    if (!box) return [];
    return Array.prototype.map.call(box.children, function(row) {
      var out = {};
      Array.prototype.forEach.call(row.querySelectorAll('[data-k]'), function(f) {
        out[f.getAttribute('data-k')] = String(f.value || '').trim();
      });
      return out;
    });
  }
  form.addEventListener('click', function(ev) {
    var t = ev.target;
    if (t && t.hasAttribute && t.hasAttribute('data-remove')) {
      t.parentNode.parentNode.removeChild(t.parentNode);
      changed();
    }
  });
  el('addBRace').addEventListener('click', function() { addRow('bRaces', 'race'); changed(); });
  el('addBlocked').addEventListener('click', function() { addRow('blockedRows', 'date'); changed(); });

  // "None" answers are exclusive in a checkbox group.
  form.addEventListener('change', function(ev) {
    var t = ev.target;
    if (!t || t.type !== 'checkbox' || !t.checked) return;
    var group = form.querySelectorAll('input[type="checkbox"][name="' + t.name + '"]');
    Array.prototype.forEach.call(group, function(c) {
      if (c === t) return;
      if (t.value === 'none' || c.value === 'none') c.checked = false;
    });
  });

  // ── Week: day caps → long day, rest days ──
  function caps() {
    var out = {};
    for (var i = 0; i < 7; i++) out[i] = el('cap_' + i).value;
    return out;
  }
  function restNeeded() {
    var c = caps(), off = 0;
    for (var i = 0; i < 7; i++) if (c[i] === '0') off += 1;
    var need = radio('level') === 'recreational' ? 2 : 1;
    return Math.max(0, need - off);
  }
  function refreshWeek() {
    var c = caps();
    var longSel = el('long_session_day');
    var current = longSel.value;
    longSel.innerHTML = '<option value="">Pick a day</option>';
    for (var i = 0; i < 7; i++) {
      if (c[i] && c[i] !== '0') {
        var o = document.createElement('option');
        o.value = String(i); o.textContent = CFG.days[i];
        longSel.appendChild(o);
      }
    }
    longSel.value = current;
    if (longSel.value !== current) longSel.value = '';
    var allAnswered = true;
    for (var j = 0; j < 7; j++) if (c[j] === '') allAnswered = false;
    var need = restNeeded();
    var restQ = form.querySelector('[data-q="rest_days"]');
    restQ.hidden = !(allAnswered && need > 0);
    restQ.querySelector('legend').textContent = need > 1 ?
      'Which two days do you want completely off?' : 'Which day do you want completely off?';
    Array.prototype.forEach.call(restQ.querySelectorAll('input[name="rest_day"]'), function(box) {
      var d = box.value;
      var usable = c[d] && c[d] !== '0' && d !== longSel.value;
      box.parentNode.hidden = !usable;
      if (!usable) box.checked = false;
    });
    if (restQ.hidden) Array.prototype.forEach.call(restQ.querySelectorAll('input'), function(b) { b.checked = false; });
    show('rest_day_swap', radio('level') === 'top_amateur');
  }

  // ── Conditionals ──
  function refresh() {
    var choice = radio('race_choice');
    show('ownRace', choice === 'own');
    show('bRacesWrap', radio('b_races_answer') === 'some');
    if (radio('b_races_answer') === 'some' && !el('bRaces').children.length) addRow('bRaces', 'race');
    show('blockedWrap', radio('blocked_answer') === 'some');
    if (radio('blocked_answer') === 'some' && !el('blockedRows').children.length) addRow('blockedRows', 'date');
    show('layoffWrap', radio('layoff_answer') === 'yes');
    var start = startDates[radio('plan_start')];
    show('last_race_on', !!start && [2, 3, 4].indexOf(start.getMonth()) !== -1);
    var gear = checked('gear');
    var rs = gear.indexOf('rollerski_classic') !== -1 || gear.indexOf('rollerski_skate') !== -1;
    show('rollerski_safe_route', rs);
    show('rollerski_experience', rs);
    show('ski_max_hr', radio('hr_monitor') === 'chest_strap');
    show('maxHrDetail', radio('hr_monitor') === 'chest_strap' && radio('ski_max_hr_answer') === 'yes');
    var fuel = radio('fuel_practised_g_per_h');
    show('fuel_practised_sessions', !!fuel && fuel !== 'never_counted');
    refreshWeek();
    updateQuote();
  }

  // ── Race and the price quote (the server's payment_plan math) ──
  function race() {
    var choice = radio('race_choice');
    if (catalog[choice]) {
      var e = catalog[choice];
      return { name: e.name, date: e.event_date, km: e.distance_km, technique: e.technique, eventId: e.event_id };
    }
    if (choice === 'own') {
      return { name: text('race_name'), date: text('race_date'), km: text('race_km'),
               technique: radio('race_technique'), eventId: null };
    }
    return null;
  }
  function money(c) {
    c = Math.round(c);
    var d = Math.floor(c / 100), r = c % 100;
    return '$' + d.toLocaleString('en-US') + '.' + (r < 10 ? '0' : '') + r;
  }
  function quote() {
    var r = race(), start = startDates[radio('plan_start')];
    var raceDay = r ? parseIso(r.date) : null;
    if (!raceDay || !start) return null;
    var weeks = Math.round(daysBetween(start, mondayOf(raceDay)) / 7) + 1;
    if (weeks < 1) return null;
    var full = Math.floor(weeks / CFG.blockWeeks), left = weeks % CFG.blockWeeks;
    var payments = full + (left ? 1 : 0);
    var total = full * CFG.blockCents + left * CFG.weekCents;
    var first = full ? CFG.blockCents : left * CFG.weekCents;
    return { weeks: weeks, payments: payments, totalCents: total, firstCents: first, start: start };
  }
  function quoteText(weeks, payments, totalCents, firstCents, start) {
    return 'Your plan: ' + weeks + (weeks === 1 ? ' week' : ' weeks') + ', from ' + nice(start) +
      ' through race week. ' + payments + (payments === 1 ? ' payment, ' : ' payments, ') +
      money(totalCents) + ' in all. ' + money(firstCents) + ' today.';
  }
  function updateQuote() {
    var q = quote();
    if (!q) {
      quoteEl.textContent = 'Pick your race and when week 1 starts to see your payments.';
      submitBtn.textContent = 'Continue to payment';
      return;
    }
    quoteEl.textContent = quoteText(q.weeks, q.payments, q.totalCents, q.firstCents, q.start);
    submitBtn.textContent = 'Continue to payment: ' + money(q.firstCents) + ' today';
  }

  // ── Collect and check every answer; build the v2 intake ──
  function collect() {
    var errors = [];
    function err(q, key) { errors.push([q, CFG.errors[key] || key]); }
    function hasAt(s) { return String(s).indexOf('@') !== -1; }
    function bool(name, q) {
      var v = radio(name);
      if (v !== 'yes' && v !== 'no') { err(q || name, 'required'); return null; }
      return v === 'yes';
    }
    function pick(name, q) { var v = radio(name); if (!v) err(q || name, 'required'); return v || null; }

    var r = race();
    var technique = null, eventId = null, ownEvent = null, raceName = '';
    if (!r) { err('race_choice', 'required'); }
    else if (r.eventId) { technique = r.technique; eventId = r.eventId; raceName = r.name; }
    else {
      raceName = r.name;
      if (!raceName) err('race_name', 'required');
      else if (hasAt(raceName)) err('race_name', 'no_at');
      if (!parseIso(r.date)) err('race_date', 'date');
      var km = number(r.km);
      if (km === null || km <= 0 || km > 90) err('race_km', 'distance');
      if (!r.technique) err('race_technique', 'required');
      technique = r.technique || null;
      ownEvent = { date: r.date, distance_km: km, technique: technique };
    }

    var bRaces = [];
    var bAnswer = radio('b_races_answer');
    if (!bAnswer) err('b_races', 'required');
    else if (bAnswer === 'some') {
      var list = rows('bRaces');
      if (!list.length) err('b_races', 'rows_race');
      if (list.length > 10) err('b_races', 'too_many_races');
      list.forEach(function(row) {
        var km = number(row.distance_km);
        if (!parseIso(row.date) || km === null || km <= 0 || km > 90 || !row.technique) {
          if (errors.every(function(e) { return e[0] !== 'b_races'; })) err('b_races', 'rows_race');
        } else {
          bRaces.push({ date: row.date, distance_km: km, technique: row.technique });
        }
      });
    }

    var startKey = radio('plan_start');
    var start = startDates[startKey] || null;
    if (!start) err('plan_start', 'required');
    var lastRaceOn = null;
    if (start && [2, 3, 4].indexOf(start.getMonth()) !== -1) {
      var lr = parseIso(text('last_race_on'));
      if (!lr) err('last_race_on', 'date');
      else if (lr > start) err('last_race_on', 'last_race');
      else lastRaceOn = iso(lr);
    }

    var name = text('display_name');
    if (!name || name.length > 40 || hasAt(name)) err('display_name', 'name');
    var age = wholeNumber(text('age_years'));
    if (age === null || age < 1 || age > 100) err('age_years', 'age');
    else if (age < 18) err('age_years', 'juniors');
    var level = pick('level');
    var winters = wholeNumber(text('winters_on_snow'));
    if (winters === null || winters > 80) err('winters_on_snow', 'winters');
    else if (winters === 0) err('winters_on_snow', 'first_season');

    var seasonHours = number(text('last_season_hours'));
    if (seasonHours === null || seasonHours <= 0 || seasonHours > 1500) err('last_season_hours', 'season_hours');
    var basis = pick('last_season_hours_basis');
    var layoff = null;
    var layoffAnswer = radio('layoff_answer');
    if (!layoffAnswer) err('layoff', 'required');
    else if (layoffAnswer === 'yes') {
      if (!parseIso(text('layoff_restart'))) err('layoff_restart', 'date');
      else layoff = { restart_on: text('layoff_restart') };
    }

    var weekHours = number(text('available_hours'));
    if (weekHours === null || weekHours <= 0 || weekHours > 40) err('available_hours', 'week_hours');
    var c = caps(), dayCaps = {}, anyDay = false, allDays = true;
    for (var i = 0; i < 7; i++) {
      if (c[i] === '') allDays = false;
      else { dayCaps[String(i)] = parseInt(c[i], 10); if (c[i] !== '0') anyDay = true; }
    }
    if (!allDays) err('day_caps', 'every_day');
    else if (!anyDay) err('day_caps', 'a_day');
    var longDay = el('long_session_day').value;
    if (longDay === '' || !dayCaps[longDay]) err('long_session_day', 'long_day');
    var restDays = [];
    var need = restNeeded();
    if (allDays && need > 0) {
      restDays = checked('rest_day').map(function(d) { return parseInt(d, 10); });
      if (restDays.length !== need) err('rest_days', need > 1 ? 'rest_two' : 'rest_one');
    }
    var restSwap = null;
    if (level === 'top_amateur') restSwap = bool('rest_day_swap');
    var blocked = [];
    var blockedAnswer = radio('blocked_answer');
    if (!blockedAnswer) err('blocked_dates', 'required');
    else if (blockedAnswer === 'some') {
      var dates = rows('blockedRows');
      if (!dates.length) err('blocked_dates', 'rows_date');
      dates.forEach(function(row) {
        if (!parseIso(row.date)) {
          if (errors.every(function(e) { return e[0] !== 'blocked_dates'; })) err('blocked_dates', 'rows_date');
        } else blocked.push(row.date);
      });
    }

    var snowFrom = parseIso(text('snow_from')), snowUntil = parseIso(text('snow_until'));
    if (!snowFrom) err('snow_from', 'date');
    if (!snowUntil) err('snow_until', 'date');
    else if (snowFrom && snowFrom >= snowUntil) err('snow_until', 'snow_order');
    var gear = checked('gear');
    if (!gear.length) err('gear', 'pick_one');
    var hasRs = gear.indexOf('rollerski_classic') !== -1 || gear.indexOf('rollerski_skate') !== -1;
    var rsRoute = null, rsExp = null;
    if (hasRs) { rsRoute = bool('rollerski_safe_route'); rsExp = pick('rollerski_experience'); }
    var running = pick('running_tolerance');
    var modalities = ['rollerski_classic', 'rollerski_skate', 'ski_erg', 'running', 'cycling'].filter(function(m) {
      return m === 'running' ? (running && running !== 'none') : gear.indexOf(m) !== -1;
    });

    var monitor = pick('hr_monitor');
    var maxHr = null;
    if (monitor === 'chest_strap') {
      var mh = radio('ski_max_hr_answer');
      if (!mh) err('ski_max_hr', 'required');
      else if (mh === 'yes') {
        var bpm = wholeNumber(text('hr_bpm'));
        if (bpm === null || bpm < 120 || bpm > 230) err('hr_bpm', 'bpm');
        var month = text('hr_month');
        var monthOk = /^\d{4}-\d{2}$/.test(month);
        if (monthOk && start) {
          var tested = new Date(+month.slice(0, 4), +month.slice(5, 7) - 1, 1);
          monthOk = tested <= start && daysBetween(tested, start) <= 3 * 366;
        }
        if (!monthOk) err('hr_month', 'hr_month');
        var mode = pick('hr_mode'), src = pick('hr_source');
        maxHr = { bpm: bpm, tested_month: month, mode: mode, source: src };
      }
    }
    var hrMedicine = bool('hr_medicine');

    var strengthHistory = pick('strength_history');
    var strengthAccess = pick('strength_access');
    var medBall = bool('medicine_ball');
    var lifts = checked('familiar_lifts');
    if (!lifts.length) err('familiar_lifts', 'pick_one');
    var injuries = checked('injury_flags');
    if (!injuries.length) err('injury_flags', 'pick_one');

    var fuel = pick('fuel_practised_g_per_h');
    var fuelSessions = null;
    if (fuel && fuel !== 'never_counted') fuelSessions = pick('fuel_practised_sessions');

    var illness = bool('recent_illness');
    var redS = radio('health_review');
    if (!redS) err('health_review', 'required');
    var heart = bool('health_note');
    var heat = checked('heat_access');
    if (!heat.length) err('heat_access', 'pick_one');
    var heatHealth = bool('heat_health_flag');

    var email = text('email');
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) err('email', 'email');

    var intake = {
      schema_version: CFG.schemaVersion,
      athlete_id: athleteId(),
      display_name: name,
      age_years: age,
      level: level,
      winters_on_snow: winters,
      technique: technique,
      event_id: eventId,
      own_event: ownEvent,
      b_races: bRaces,
      plan_start: start ? iso(start) : null,
      last_race_on: lastRaceOn,
      last_season_hours: seasonHours,
      last_season_hours_basis: basis,
      layoff: layoff,
      available_hours: weekHours,
      day_caps: dayCaps,
      long_session_day: longDay === '' ? null : parseInt(longDay, 10),
      rest_days: restDays,
      rest_day_swap: restSwap,
      blocked_dates: blocked,
      snow_from: text('snow_from'),
      snow_until: text('snow_until'),
      available_modalities: modalities,
      rollerski_safe_route: rsRoute,
      rollerski_experience: rsExp,
      running_tolerance: running,
      hr_monitor: monitor,
      ski_max_hr: maxHr,
      hr_medicine: hrMedicine,
      strength_history: strengthHistory,
      strength_access: strengthAccess,
      medicine_ball: medBall,
      familiar_lifts: lifts.filter(function(v) { return v !== 'none'; }),
      injury_flags: injuries.filter(function(v) { return v !== 'none'; }),
      fuel_practised_g_per_h: fuel,
      fuel_practised_sessions: fuelSessions,
      recent_illness: illness,
      health_review: redS ? redS !== 'no' : null,
      health_note: heart,
      heat_access: heat.filter(function(v) { return v !== 'none'; }),
      heat_health_flag: heatHealth
    };
    return { errors: errors, intake: intake, name: name, email: email, raceName: raceName };
  }

  function athleteId() {
    var bytes = new Uint8Array(8);
    crypto.getRandomValues(bytes);
    return 'xc-' + Array.prototype.map.call(bytes, function(b) { return (b < 16 ? '0' : '') + b.toString(16); }).join('');
  }

  // ── Messages ──
  function clearErrors() {
    Array.prototype.forEach.call(form.querySelectorAll('.gl-field.has-error'), function(f) {
      f.classList.remove('has-error');
    });
    alertBox.classList.remove('show');
    alertBox.textContent = '';
  }
  function markErrors(errors) {
    var first = null;
    errors.forEach(function(e) {
      var field = form.querySelector('[data-q="' + e[0] + '"]');
      if (!field) return;
      field.classList.add('has-error');
      var slot = field.querySelector('[data-error-for="' + e[0] + '"]');
      if (slot) slot.textContent = e[1];
      if (!first) first = field;
    });
    return first;
  }
  function showAlert(title, message, saved, kind) {
    alertBox.innerHTML = '';
    alertBox.setAttribute('data-kind', kind || 'refusal');
    var t = document.createElement('p');
    t.className = 'gl-alert-title';
    t.textContent = title;
    alertBox.appendChild(t);
    var p = document.createElement('p');
    var parts = String(message).split('{contact}');
    parts.forEach(function(part, i) {
      p.appendChild(document.createTextNode(part));
      if (i < parts.length - 1) {
        var a = document.createElement('a');
        a.href = 'mailto:' + CFG.contact;
        a.textContent = CFG.contact;
        p.appendChild(a);
      }
    });
    alertBox.appendChild(p);
    if (saved) {
      var s = document.createElement('p');
      s.textContent = CFG.savedNote;
      alertBox.appendChild(s);
    }
    alertBox.classList.add('show');
    alertBox.focus();
  }
  function refusalKey(status, body) {
    var reason = body && typeof body.reason === 'string' ? body.reason : '';
    if (reason && CFG.refusals[reason]) return reason;
    if (status === 429) return 'rate_limited';
    if (status >= 500 || status === 0) return 'network';
    var error = body && typeof body.error === 'string' ? body.error : '';
    if (/email/i.test(error)) return 'email_invalid';
    if (/name is required/i.test(error)) return 'name_required';
    return 'ski_intake_invalid';
  }
  function refuse(key) {
    var saved = save();
    showAlert('I couldn’t take your order', CFG.refusals[key] || CFG.refusals.ski_intake_invalid, saved);
    if (typeof gtag === 'function') gtag('event', 'plan_checkout_refused', { reason: key });
  }
  function resetButton() {
    busy = false;
    submitBtn.disabled = false;
    updateQuote();
  }

  // ── Save and restore (this browser only) ──
  function snapshot() {
    var data = { fields: {}, bRaces: rows('bRaces'), blocked: rows('blockedRows') };
    Array.prototype.forEach.call(form.elements, function(f) {
      if (!f.name) return;
      if (f.type === 'checkbox') {
        if (!data.fields[f.name]) data.fields[f.name] = [];
        if (f.checked) data.fields[f.name].push(f.value);
      } else if (f.type === 'radio') {
        if (f.checked) data.fields[f.name] = f.value;
      } else {
        data.fields[f.name] = f.value;
      }
    });
    return data;
  }
  function save() {
    if (!store || !storageKey) return false;
    try { store.setItem(storageKey, JSON.stringify(snapshot())); return true; } catch (e) { return false; }
  }
  function restore() {
    if (!store || !storageKey) return;
    var data;
    try { data = JSON.parse(store.getItem(storageKey) || 'null'); } catch (e) { return; }
    if (!data || !data.fields) return;
    (data.bRaces || []).forEach(function(r) { addRow('bRaces', 'race', r); });
    (data.blocked || []).forEach(function(r) { addRow('blockedRows', 'date', r); });
    for (var i = 0; i < 7; i++) {
      var cap = data.fields['cap_' + i];
      if (cap !== undefined) el('cap_' + i).value = cap;
    }
    refreshWeek();
    Array.prototype.forEach.call(form.elements, function(f) {
      if (!f.name || !(f.name in data.fields)) return;
      var v = data.fields[f.name];
      if (f.type === 'checkbox') f.checked = Array.isArray(v) && v.indexOf(f.value) !== -1;
      else if (f.type === 'radio') f.checked = v === f.value;
      else f.value = v;
    });
  }
  function changed(ev) {
    var field = ev && ev.target && ev.target.closest ? ev.target.closest('.gl-field.has-error') : null;
    if (field) field.classList.remove('has-error');
    if (alertBox.getAttribute('data-kind') === 'check' && !form.querySelector('.gl-field.has-error')) {
      alertBox.classList.remove('show');
    }
    refresh();
    save();
  }

  // ── Prefill: ?race=slug (race page links) and the goals funnel ──
  var raceSlug = params.get('race') || '';
  if (!/^[a-z0-9-]{1,80}$/.test(raceSlug) || !races[raceSlug]) raceSlug = '';
  if (!goalsMode || storageKey) restore();
  var raceInput = el('race_name');
  if (raceSlug && !raceInput.value) {
    var listed = CFG.catalog.events.some(function(e) { return e.site_slug === raceSlug && catalog[e.event_id]; });
    if (!listed) {
      raceInput.value = races[raceSlug];
      var own = form.querySelector('input[name="race_choice"][value="own"]');
      if (own && !radio('race_choice')) own.checked = true;
    }
  }
  var reviewEmail = '', hashedRef = '';
  if (goalsMode && goalToken) {
    fetch('https://athlete-profiles-production.up.railway.app/api/season-plan/prefill/' + encodeURIComponent(goalToken), {
      headers: { 'Accept': 'application/json' }
    }).then(function(r) { return r.ok ? r.json() : null; }).then(function(data) {
      if (!data) return;
      var emailField = el('email');
      if (emailField && !emailField.value && data.email) emailField.value = data.email;
      reviewEmail = String(data.email || '').trim().toLowerCase();
      if (data.a_race_name && !raceInput.value) raceInput.value = String(data.a_race_name).slice(0, 100);
      if (data.a_race_date && !el('race_date').value && parseIso(data.a_race_date)) el('race_date').value = data.a_race_date;
      changed();
    }).catch(function() {});
    if (window.crypto && crypto.subtle && window.TextEncoder) {
      crypto.subtle.digest('SHA-256', new TextEncoder().encode(goalToken)).then(function(hash) {
        hashedRef = Array.prototype.map.call(new Uint8Array(hash), function(b) {
          return (b < 16 ? '0' : '') + b.toString(16);
        }).join('');
      }).catch(function() {});
    }
  }
  refresh();
  form.addEventListener('input', changed);
  form.addEventListener('change', changed);

  // ── Submit: check, post, then go to Stripe or explain the refusal ──
  form.addEventListener('submit', function(ev) {
    ev.preventDefault();
    if (busy) return;
    clearErrors();
    var c = collect();
    if (c.errors.length) {
      var first = markErrors(c.errors);
      showAlert('Check your answers', CFG.summaryError, false, 'check');
      if (first && first.scrollIntoView) first.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    var q = quote();
    var payload = {
      product: CFG.product,
      name: c.name,
      email: c.email,
      race_name: c.raceName,
      ski_intake: c.intake
    };
    if (raceSlug) payload.race_slug = raceSlug;
    if (goalsMode && hashedRef && reviewEmail && c.email.toLowerCase() === reviewEmail) {
      payload.goal_ref = hashedRef;
      payload.entry_src = 'goals';
    }
    busy = true;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Checking your plan…';
    save();
    fetch(CFG.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    }).then(function(r) {
      return r.json().catch(function() { return {}; }).then(function(body) {
        return { status: r.status, body: body || {} };
      });
    }).then(function(res) {
      var url = res.body.checkout_url;
      if (res.status === 200 && typeof url === 'string' && /^https:\/\/checkout\.stripe\.com\//.test(url)) {
        var plan = res.body.payment_plan || {};
        if (typeof gtag === 'function') {
          gtag('event', 'begin_checkout', {
            currency: 'USD',
            value: (plan.first_payment_cents || 0) / 100,
            items: [{ item_name: 'Custom ski plan, every 4 weeks', item_category: CFG.product }]
          });
        }
        if (q && plan.weeks === q.weeks) {
          window.location.assign(url);
          return;
        }
        // The server's numbers differ from the ones shown: show them first.
        alertBox.innerHTML = '';
        alertBox.setAttribute('data-kind', 'payments');
        var t = document.createElement('p');
        t.className = 'gl-alert-title';
        t.textContent = 'Your payments changed';
        var p = document.createElement('p');
        p.textContent = 'When I built your plan it came out at ' + plan.weeks + ' weeks, not the ' +
          (q ? q.weeks : '') + ' shown above. ' + quoteText(plan.weeks, plan.payment_count, plan.total_cents,
          plan.first_payment_cents, startDates[radio('plan_start')]);
        var a = document.createElement('a');
        a.className = 'gl-submit-btn gl-continue';
        a.href = url;
        a.textContent = 'Continue to payment';
        alertBox.appendChild(t); alertBox.appendChild(p); alertBox.appendChild(a);
        alertBox.classList.add('show');
        alertBox.focus();
        resetButton();
        return;
      }
      if (res.status === 200) { refuse('network'); resetButton(); return; }
      refuse(refusalKey(res.status, res.body));
      resetButton();
    }).catch(function() {
      refuse('network');
      resetButton();
    });
  });

})();
"""


TOKEN_SCRUB_JS = """(function(){
    try {
      var u = new URL(location.href);
      var t = u.searchParams.get('t') || new URLSearchParams(u.hash.slice(1)).get('t') || '';
      var hasToken = u.searchParams.has('t') || new URLSearchParams(u.hash.slice(1)).has('t');
      var valid = u.searchParams.get('src') === 'goals' && /^[A-Za-z0-9_-]{16,64}$/.test(t);
      try {
        sessionStorage.removeItem('xc_goal_prefill_token');
        if (valid) sessionStorage.setItem('xc_goal_prefill_token', t);
      } catch (e) {}
      if (hasToken) {
        u.searchParams.delete('t');
        if (new URLSearchParams(u.hash.slice(1)).has('t')) u.hash = '';
        history.replaceState(valid ? { goalToken: t } : history.state,
          '', u.pathname + u.search + u.hash);
      }
    } catch (e) {}
  })();"""


def render_page(slug_map: dict[str, str], catalog: dict[str, Any]) -> str:
    config = _safe_json_for_script(page_config(slug_map, catalog), separators=(",", ":"))
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Custom Ski Plan Questionnaire | XC Ski Labs</title>
  <meta name="description" content="Answer the questions your custom XC ski plan is built from, then pay {esc(plan_offer.PRICE_LINE)} until race week.">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://xcskilabs.com/questionnaire/">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Big+Shoulders+Stencil+Display:wght@700;900&family=Big+Shoulders+Text:wght@600;800&family=Libre+Franklin:ital,wght@0,400;0,600;1,400&display=swap" rel="stylesheet">
  <script>{TOKEN_SCRUB_JS}</script>
  {build_ga4()}
  <style>{build_css()}{EXTRA_CSS}</style>
</head>
<body>
<a href="#questionnaire" class="gl-skip-link">Skip to questionnaire</a>
{build_nav()}
<main class="gl-page" id="questionnaire">
  <header class="gl-page-header">
    <div class="gl-kicker">Custom ski plan</div>
    <h1>Tell me about your race.</h1>
    <p>I build your plan from these answers, so every question needs one. Your race, your week, your snow and your gear decide what goes in it.</p>
  </header>
  {build_offer_box()}
  {build_form(catalog)}
</main>
<footer class="gl-footer">
  <a href="/training-plans/">Back to training plans</a> &middot;
  <a href="/privacy/">Privacy</a> &middot;
  <a href="/terms/">Terms</a>
</footer>
{build_cookie_banner()}
<script type="application/json" id="xc-plan-config">{config}</script>
<script>{QUESTIONNAIRE_JS}</script>
</body>
</html>
"""


def generate_page(output_dir: Path = OUTPUT_DIR, race_index: Path = RACE_INDEX,
                  catalog_path: Path = EVENT_CATALOG) -> Path:
    page = render_page(load_race_slug_map(race_index), load_event_catalog(catalog_path))
    out_path = output_dir / "questionnaire" / "index.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    print(f"Generated: {out_path}")
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the XC Ski Labs ski plan questionnaire")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--race-index", default=str(RACE_INDEX))
    parser.add_argument("--event-catalog", default=str(EVENT_CATALOG))
    args = parser.parse_args()
    generate_page(Path(args.output_dir), Path(args.race_index), Path(args.event_catalog))


if __name__ == "__main__":
    main()
